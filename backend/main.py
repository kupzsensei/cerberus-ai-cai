import uuid
import json
from fastapi.responses import FileResponse

# main.py
import os
import httpx
import logging
from datetime import datetime
import pytz
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import List
import utils
import database
import research
import scheduler_service

from fastapi.middleware.cors import CORSMiddleware

ADELAIDE_TZ = pytz.timezone('Australia/Adelaide')
app = FastAPI()

# Read CORS origins from config, with a fallback for safety
origins = utils.config.get("cors_origins", [])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a persistent client for making requests to Ollama
client = httpx.AsyncClient()

@app.on_event("startup")
async def startup_event():
    """On startup, configure and initialize the database and start the scheduler."""
    db_file = utils.config.get("database_file", "tasks.db")
    database.configure_database(db_file)
    await database.initialize_db()
    await database.initialize_research_db()
    await database.initialize_local_storage_db()
    await database.initialize_email_scheduler_db()
    
    # Start the scheduled research executor
    import asyncio
    asyncio.create_task(scheduler_service.scheduler_executor.run_scheduler())

@app.on_event("shutdown")
async def shutdown_event():
    """On shutdown, close the httpx client and stop the scheduler."""
    await client.aclose()
    scheduler_service.scheduler_executor.stop_scheduler()

async def process_and_update_task(file_name: str, user_prompt: str, model_name: str, server_name: str, server_type: str):
    """
    The actual background task logic, now with processing time recording.
    """
    file_path = os.path.join(utils.PDF_DIRECTORY, file_name)
    
    # Record the actual start time of processing
    start_time = datetime.now(ADELAIDE_TZ)
    
    try:
        # Set status to 'in_progress', clearing any previous result
        await database.update_task(file_name, 'in_progress')
        
        with open(file_path, "rb") as f:
            pdf_content = f.read()

        server_details = None
        if server_type == "ollama":
            server_details = await database.get_ollama_server_by_name(server_name)
            server_url_or_key = server_details['url'] if server_details else None
        elif server_type == "gemini":
            server_details = await database.get_external_ai_server_by_name(server_name)
            server_url_or_key = server_details['api_key'] if server_details else None
        
        if not server_details:
            raise Exception(f"AI server '{server_name}' of type '{server_type}' not found.")
        
        processed_text = await utils.process_pdf_content(pdf_content, user_prompt, client, model_name, server_type, server_url_or_key)
        
        # Record end time and calculate duration
        end_time = datetime.now(ADELAIDE_TZ)
        duration = (end_time - start_time).total_seconds()
        
        result_data = {"processed_text": processed_text}
        # Update with 'completed' status and the calculated processing time
        await database.update_task(file_name, 'completed', result=result_data, processing_time=duration)

    except Exception as e:
        # Also record duration even if it fails
        end_time = datetime.now(ADELAIDE_TZ)
        duration = (end_time - start_time).total_seconds()
        
        logging.error(f"Background task failed for {file_name}. Error: {e}", exc_info=True)
        error_data = {"error": str(e)}
        # Update with 'failed' status and the calculated processing time
        await database.update_task(file_name, 'failed', result=error_data, processing_time=duration)

# --- Endpoints ---

@app.post("/process-pdfs/", status_code=202)
async def process_pdfs_background(
    background_tasks: BackgroundTasks,
    user_prompt: str = Form(...),
    model_name: str = Form(...),
    server_name: str = Form(...),
    server_type: str = Form(...),
    files: List[UploadFile] = File(...)
):
    """
    Uploads multiple PDFs and processes them in the background using a specified model and server.
    """
    if not user_prompt:
        raise HTTPException(status_code=400, detail="A user_prompt is required.")
        
    task_ids = []
    for file in files:
        if file.content_type != "application/pdf":
            logging.warning(f"Skipping non-PDF file: {file.filename}")
            continue

        try:
            file_path = os.path.join(utils.PDF_DIRECTORY, file.filename)
            file_content = await file.read()
            with open(file_path, "wb") as buffer:
                buffer.write(file_content)
        except Exception as e:
            logging.error(f"Failed to save uploaded file {file.filename}. Error: {e}")
            continue

        task_ids.append(file.filename)
        await database.add_or_update_task(file.filename, user_prompt, model_name, server_name)
        # Pass the server name and type to the background task
        background_tasks.add_task(process_and_update_task, file.filename, user_prompt, model_name, server_name, server_type)

    if not task_ids:
        raise HTTPException(status_code=400, detail="No valid PDF files were processed.")

    return {"message": "PDF processing started in the background.", "tasks": task_ids, "model_scheduled": model_name}


@app.post("/pdfprofessor")
async def pdf_professor_direct(
    prompt: str = Form(...),
    model_name: str = Form(...),
    server_name: str = Form(...),
    server_type: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Processes a single PDF synchronously using a specified model and returns the result.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF.")

    pdf_content = await file.read()
    
    server_details = None
    if server_type == "ollama":
        server_details = await database.get_ollama_server_by_name(server_name)
        server_url_or_key = server_details['url'] if server_details else None
    elif server_type == "gemini":
        server_details = await database.get_external_ai_server_by_name(server_name)
        server_url_or_key = server_details['api_key'] if server_details else None
    
    if not server_details:
        raise HTTPException(status_code=404, detail=f"AI server '{server_name}' of type '{server_type}' not found.")

    processed_text = await utils.process_pdf_content(pdf_content, prompt, client, model_name, server_type, server_url_or_key)
    
    if "[Error:" in processed_text:
         raise HTTPException(status_code=500, detail=f"Failed to process PDF. Reason: {processed_text}")

    return {"processed_text": processed_text, "model_used": model_name}


@app.get("/status")
async def get_all_statuses():
    """Retrieves the status of all tasks."""
    tasks = await database.get_all_tasks()
    return tasks

@app.get("/status/{task_id}")
async def get_status(task_id: str):
    """Checks the processing status of a specific task."""
    task = await database.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task

@app.delete("/task/{task_id}", status_code=200)
async def delete_task_endpoint(task_id: str):
    """
    Deletes a task record and its associated PDF file.
    """
    # 1. Check if the task exists in the DB to avoid errors
    task = await database.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    # 2. Delete the associated file from the disk
    file_path = os.path.join(utils.PDF_DIRECTORY, task_id)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logging.info(f"Successfully deleted file: {file_path}")
    except OSError as e:
        # If file deletion fails, we still proceed to delete the DB record but warn the user.
        logging.error(f"Error deleting file {file_path}: {e}")
        await database.delete_task(task_id) # Delete DB record anyway
        raise HTTPException(status_code=500, detail=f"Task record deleted, but failed to delete file '{task_id}'. Error: {e}")

    # 3. Delete the task from the database
    await database.delete_task(task_id)

    return {"message": f"Task '{task_id}' and associated file were successfully deleted."}

@app.post("/research")
async def research_endpoint(query: str = Form(...), server_name: str = Form(...), model_name: str = Form(...), server_type: str = Form(...)):
    """
    Performs a research query and returns the results.
    """
    if not query:
        raise HTTPException(status_code=400, detail="A query is required.")
    
    result, generation_time = await research.perform_search(query, server_name, model_name, server_type)
    
    return {"result": result, "generation_time": generation_time}

@app.get("/ollama-servers")
async def get_ollama_servers_endpoint():
    """Retrieves the list of configured Ollama servers."""
    servers = await database.get_ollama_servers()
    return {"servers": servers}

@app.post("/ollama-servers", status_code=201)
async def add_ollama_server_endpoint(name: str = Form(...), url: str = Form(...)):
    """Adds a new Ollama server configuration."""
    await database.add_ollama_server(name, url)
    return {"message": f"Ollama server '{name}' added successfully."}

@app.delete("/ollama-servers/{name}", status_code=200)
async def delete_ollama_server_endpoint(name: str):
    """Deletes an Ollama server configuration."""
    server = await database.get_ollama_server_by_name(name)
    if not server:
        raise HTTPException(status_code=404, detail=f"Ollama server '{name}' not found.")
    await database.delete_ollama_server(name)
    return {"message": f"Ollama server '{name}' deleted successfully."}

@app.get("/ollama-servers/{server_name}")
async def get_ollama_server_by_name_endpoint(server_name: str):
    """Retrieves a single Ollama server from the database by name."""
    server = await database.get_ollama_server_by_name(server_name)
    if not server:
        raise HTTPException(status_code=404, detail="Ollama server not found.")
    return server

@app.get("/ollama-models")
async def get_ollama_models_endpoint(url: str):
    """Retrieves the list of models available from a given Ollama server URL."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{url.replace('/api/generate', '')}/api/tags", timeout=10.0)
            response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes
            models_data = response.json()
            return [model['name'] for model in models_data.get('models', [])]
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Could not connect to Ollama server: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching models from Ollama server: {e}")

# --- External AI Server Endpoints ---

@app.get("/external-ai-servers")
async def get_external_ai_servers_endpoint():
    """Retrieves the list of configured external AI servers."""
    servers = await database.get_external_ai_servers()
    return {"servers": servers}

@app.post("/external-ai-servers", status_code=201)
async def add_external_ai_server_endpoint(name: str = Form(...), type: str = Form(...), api_key: str = Form(...)):
    """Adds a new external AI server configuration."""
    await database.add_external_ai_server(name, type, api_key)
    return {"message": f"External AI server '{name}' added successfully."}

@app.delete("/external-ai-servers/{name}", status_code=200)
async def delete_external_ai_server_endpoint(name: str):
    """Deletes an external AI server configuration."""
    server = await database.get_external_ai_server_by_name(name)
    if not server:
        raise HTTPException(status_code=404, detail=f"External AI server '{name}' not found.")
    await database.delete_external_ai_server(name)
    return {"message": f"External AI server '{name}' deleted successfully."}

@app.get("/external-ai-servers/{server_name}")
async def get_external_ai_server_by_name_endpoint(server_name: str):
    """Retrieves a single external AI server from the database by name."""
    server = await database.get_external_ai_server_by_name(server_name)
    if not server:
        raise HTTPException(status_code=404, detail="External AI server not found.")
    return server

@app.get("/external-ai/models")
async def get_external_ai_models_endpoint(server_type: str):
    """Retrieves the list of models available for a given external AI server type."""
    if server_type == "gemini":
        return ["flash 2.5"]
    raise HTTPException(status_code=400, detail=f"Unsupported external AI server type: {server_type}")

@app.get("/research")
async def get_research_list():
    """Retrieves the list of all research queries."""
    research_list = await database.get_all_research()
    return research_list

@app.get("/research/{research_id}")
async def get_research_by_id_endpoint(research_id: int):
    """Retrieves a single research entry by ID."""
    research_entry = await database.get_research_by_id(research_id)
    if not research_entry:
        raise HTTPException(status_code=404, detail="Research entry not found.")
    return research_entry

@app.delete("/research/{research_id}", status_code=200)
async def delete_research_endpoint(research_id: int):
    """
    Deletes a research entry by ID.
    """
    research_entry = await database.get_research_by_id(research_id)
    if not research_entry:
        raise HTTPException(status_code=404, detail=f"Research entry with ID {research_id} not found.")
    
    await database.delete_research(research_id)
    return {"message": f"Research entry with ID {research_id} successfully deleted."}

@app.post("/investigate")
async def investigate_endpoint(query: str = Form(...), server_name: str = Form(None), model_name: str = Form(None), server_type: str = Form(...)):
    """
    Performs an investigation query and returns the results.
    """
    if not query:
        raise HTTPException(status_code=400, detail="A query is required.")
    
    result, generation_time = await research.investigate(f"investigation: {query}", server_name, model_name, server_type)
    
    return {"result": result, "generation_time": generation_time}

# --- LocalStorage Endpoints ---

LOCAL_STORAGE_DIR = "backend/local_storage"

@app.get("/local-storage/files")
async def get_local_storage_files():
    """Retrieves the list of files in the local storage."""
    if not os.path.exists(LOCAL_STORAGE_DIR):
        return []
    return os.listdir(LOCAL_STORAGE_DIR)

@app.post("/local-storage/upload")
async def upload_to_local_storage(files: List[UploadFile] = File(...)):
    """Uploads files to the local storage."""
    os.makedirs(LOCAL_STORAGE_DIR, exist_ok=True)
    for file in files:
        file_path = os.path.join(LOCAL_STORAGE_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
    return {"message": "Files uploaded successfully."}

@app.delete("/local-storage/files/{filename}")
async def delete_local_storage_file(filename: str):
    """Deletes a file from the local storage."""
    file_path = os.path.join(LOCAL_STORAGE_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"message": f"File '{filename}' deleted successfully."}
    raise HTTPException(status_code=404, detail="File not found.")

@app.get("/local-storage/files/{filename}")
async def download_local_storage_file(filename: str):
    """Downloads a file from the local storage."""
    file_path = os.path.join(LOCAL_STORAGE_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found.")

@app.post("/local-storage/query")
async def query_local_storage_files(
    background_tasks: BackgroundTasks,
    prompt: str = Form(...),
    filenames: str = Form(...),
    model_name: str = Form(...),
    server_name: str = Form(...),
    server_type: str = Form(...)
):
    """Queries selected files in the local storage."""
    filenames_list = json.loads(filenames)
    job_id = str(uuid.uuid4())
    await database.add_local_storage_job(job_id, prompt, model_name, server_name, server_type, filenames_list)
    background_tasks.add_task(process_local_storage_query, job_id, prompt, model_name, server_name, server_type, filenames_list)
    return {"message": "Query started in the background.", "job_id": job_id}

@app.get("/local-storage/status/{job_id}")
async def get_local_storage_job_status(job_id: str):
    """Checks the status of a local storage job."""
    job = await database.get_local_storage_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job

@app.get("/local-storage/jobs")
async def get_all_local_storage_jobs():
    """Retrieves all local storage jobs."""
    jobs = await database.get_all_local_storage_jobs()
    return jobs

@app.delete("/local-storage/jobs/{job_id}", status_code=200)
async def delete_local_storage_job_endpoint(job_id: str):
    """
    Deletes a local storage job record.
    """
    job = await database.get_local_storage_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    await database.delete_local_storage_job(job_id)

    return {"message": f"Job '{job_id}' was successfully deleted."}

@app.post("/chat")
async def chat_with_ai_endpoint(
    messages: str = Form(...),
    model_name: str = Form(...),
    server_name: str = Form(...),
    server_type: str = Form(...)
):
    """
    Handles chat messages and routes them to the appropriate AI model.
    """
    messages_list = json.loads(messages)
    user_message_content = messages_list[-1]['content'] # Get the last message from the user

    server_details = None
    server_url_or_key = None

    if server_type == "ollama":
        server_details = await database.get_ollama_server_by_name(server_name)
        server_url_or_key = server_details['url'] if server_details else None
    elif server_type == "gemini":
        server_details = await database.get_external_ai_server_by_name(server_name)
        server_url_or_key = server_details['api_key'] if server_details else None
    
    if not server_details:
        raise HTTPException(status_code=404, detail=f"AI server '{server_name}' of type '{server_type}' not found.")

    try:
        async with httpx.AsyncClient() as client:
            if server_type == "ollama":
                # For Ollama, we need to reconstruct the messages in the format it expects
                ollama_messages = []
                for msg in messages_list:
                    ollama_messages.append({"role": msg['role'], "content": msg['content']})
                
                response = await client.post(f"{server_url_or_key.rstrip('/')}/api/chat", json={
                    "model": model_name,
                    "messages": ollama_messages,
                    "stream": False
                }, timeout=180.0)
                response.raise_for_status()
                api_response = response.json()
                processed_text = api_response.get('message', {}).get('content', '')

            elif server_type == "gemini":
                # For Gemini, we need to send the prompt in its specific format
                payload = {
                    "contents": [{
                        "parts": [{
                            "text": user_message_content
                        }]
                    }]
                }
                response = await client.post(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={server_url_or_key}", json=payload, timeout=180.0)
                response.raise_for_status()
                api_response = response.json()
                processed_text = api_response.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported server type: {server_type}")

        return {"message": {"content": processed_text}}

    except httpx.RequestError as e:
        logging.error(f"Chatbot API request failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Could not connect to AI server: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred during chat processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

async def process_local_storage_query(job_id: str, prompt: str, model_name: str, server_name: str, server_type: str, filenames: list):
    """The actual background task logic for local storage queries."""
    start_time = datetime.now(ADELAIDE_TZ)
    try:
        await database.update_local_storage_job(job_id, 'in_progress')
        
        combined_content = ""
        for filename in filenames:
            file_path = os.path.join(LOCAL_STORAGE_DIR, filename)
            with open(file_path, "rb") as f:
                content = f.read()
                # Force OCR on PDF bytes using utils.perform_ocr_on_pdf_bytes
                extracted_text = utils.perform_ocr_on_pdf_bytes(content)
                if extracted_text.startswith("[Error:"):
                    logging.error(f"Error performing OCR on {filename}: {extracted_text}")
                    # Decide how to handle: skip file, raise error, or include error message
                    # For now, we'll include the error message in combined_content
                    combined_content += f"[Error performing OCR on {filename}: {extracted_text}]\n\n---\n\n"
                else:
                    combined_content += extracted_text
                    combined_content += "\n\n---\n\n"

        server_details = None
        if server_type == "ollama":
            server_details = await database.get_ollama_server_by_name(server_name)
            server_url_or_key = server_details['url'] if server_details else None
        elif server_type == "gemini":
            server_details = await database.get_external_ai_server_by_name(server_name)
            server_url_or_key = server_details['api_key'] if server_details else None
        
        if not server_details:
            raise Exception(f"AI server '{server_name}' of type '{server_type}' not found.")
        
        processed_text = await utils.process_text_content(combined_content, prompt, client, model_name, server_type, server_url_or_key)
        
        end_time = datetime.now(ADELAIDE_TZ)
        duration = (end_time - start_time).total_seconds()
        
        result_data = {"processed_text": processed_text}
        await database.update_local_storage_job(job_id, 'completed', result=result_data, processing_time=duration)

    except Exception as e:
        end_time = datetime.now(ADELAIDE_TZ)
        duration = (end_time - start_time).total_seconds()
        logging.error(f"Background task failed for job {job_id}. Error: {e}", exc_info=True)
        error_data = {"error": str(e)}
        await database.update_local_storage_job(job_id, 'failed', result=error_data, processing_time=duration)

# --- Email Scheduler Endpoints ---

@app.post("/email-config", status_code=201)
async def add_email_config_endpoint(
    smtp_server: str = Form(...),
    smtp_port: int = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    sender_email: str = Form(...),
    sender_name: str = Form(None),
    use_tls: bool = Form(True),
    use_ssl: bool = Form(False)
):
    """Adds a new email configuration."""
    await database.add_email_config(smtp_server, smtp_port, username, password, sender_email, sender_name, use_tls, use_ssl)
    return {"message": "Email configuration added successfully."}

@app.get("/email-configs")
async def get_email_configs_endpoint():
    """Retrieves all email configurations."""
    configs = await database.get_email_configs()
    return {"configs": configs}

@app.get("/email-configs/{config_id}")
async def get_email_config_endpoint(config_id: int):
    """Retrieves a single email configuration by ID."""
    config = await database.get_email_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Email configuration not found.")
    return config

@app.put("/email-configs/{config_id}")
async def update_email_config_endpoint(
    config_id: int,
    smtp_server: str = Form(None),
    smtp_port: int = Form(None),
    username: str = Form(None),
    password: str = Form(None),
    sender_email: str = Form(None),
    sender_name: str = Form(None),
    use_tls: bool = Form(None),
    use_ssl: bool = Form(None)
):
    """Updates an email configuration."""
    config = await database.get_email_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Email configuration not found.")
    
    await database.update_email_config(config_id, smtp_server, smtp_port, username, password, sender_email, sender_name, use_tls, use_ssl)
    return {"message": "Email configuration updated successfully."}

@app.delete("/email-configs/{config_id}", status_code=200)
async def delete_email_config_endpoint(config_id: int):
    """Deletes an email configuration."""
    config = await database.get_email_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Email configuration not found.")
    
    await database.delete_email_config(config_id)
    return {"message": "Email configuration deleted successfully."}

# --- Email Recipient Group Endpoints ---

@app.post("/email-recipient-groups", status_code=201)
async def add_email_recipient_group_endpoint(name: str = Form(...), description: str = Form(None)):
    """Adds a new email recipient group."""
    # Check if group with this name already exists
    groups = await database.get_email_recipient_groups()
    if any(group['name'].lower() == name.lower() for group in groups):
        raise HTTPException(status_code=400, detail="A group with this name already exists.")
    
    await database.add_email_recipient_group(name, description)
    return {"message": "Email recipient group added successfully."}

@app.get("/email-recipient-groups")
async def get_email_recipient_groups_endpoint():
    """Retrieves all email recipient groups."""
    groups = await database.get_email_recipient_groups()
    return {"groups": groups}

@app.get("/email-recipient-groups/{group_id}")
async def get_email_recipient_group_endpoint(group_id: int):
    """Retrieves a single email recipient group by ID."""
    group = await database.get_email_recipient_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Email recipient group not found.")
    return group

@app.put("/email-recipient-groups/{group_id}")
async def update_email_recipient_group_endpoint(group_id: int, name: str = Form(None), description: str = Form(None)):
    """Updates an email recipient group."""
    group = await database.get_email_recipient_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Email recipient group not found.")
    
    await database.update_email_recipient_group(group_id, name, description)
    return {"message": "Email recipient group updated successfully."}

@app.delete("/email-recipient-groups/{group_id}", status_code=200)
async def delete_email_recipient_group_endpoint(group_id: int):
    """Deletes an email recipient group."""
    group = await database.get_email_recipient_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Email recipient group not found.")
    
    await database.delete_email_recipient_group(group_id)
    return {"message": "Email recipient group deleted successfully."}

# --- Email Recipient Endpoints ---

@app.post("/email-recipients", status_code=201)
async def add_email_recipient_endpoint(group_id: int = Form(...), email: str = Form(...), name: str = Form(None)):
    """Adds a new email recipient to a group."""
    # Check if group exists
    group = await database.get_email_recipient_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Email recipient group not found.")
    
    await database.add_email_recipient(group_id, email, name)
    return {"message": "Email recipient added successfully."}

@app.get("/email-recipients/{group_id}")
async def get_email_recipients_endpoint(group_id: int):
    """Retrieves all email recipients for a group."""
    # Check if group exists
    group = await database.get_email_recipient_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Email recipient group not found.")
    
    recipients = await database.get_email_recipients(group_id)
    return {"recipients": recipients}

@app.get("/email-recipient/{recipient_id}")
async def get_email_recipient_endpoint(recipient_id: int):
    """Retrieves a single email recipient by ID."""
    recipient = await database.get_email_recipient(recipient_id)
    if not recipient:
        raise HTTPException(status_code=404, detail="Email recipient not found.")
    return recipient

@app.put("/email-recipients/{recipient_id}")
async def update_email_recipient_endpoint(recipient_id: int, email: str = Form(None), name: str = Form(None)):
    """Updates an email recipient."""
    recipient = await database.get_email_recipient(recipient_id)
    if not recipient:
        raise HTTPException(status_code=404, detail="Email recipient not found.")
    
    await database.update_email_recipient(recipient_id, email, name)
    return {"message": "Email recipient updated successfully."}

@app.delete("/email-recipients/{recipient_id}", status_code=200)
async def delete_email_recipient_endpoint(recipient_id: int):
    """Deletes an email recipient."""
    recipient = await database.get_email_recipient(recipient_id)
    if not recipient:
        raise HTTPException(status_code=404, detail="Email recipient not found.")
    
    await database.delete_email_recipient(recipient_id)
    return {"message": "Email recipient deleted successfully."}

# --- Scheduled Research Endpoints ---

@app.post("/scheduled-research")
async def add_scheduled_research_endpoint(
    name: str = Form(...),
    frequency: str = Form(...),  # daily, weekly, monthly
    hour: int = Form(...),
    minute: int = Form(...),
    recipient_group_id: int = Form(...),
    date_range_days: int = Form(...),
    description: str = Form(None),
    day_of_week: int = Form(None),  # 0-6 (Monday-Sunday), required for weekly
    day_of_month: int = Form(None),  # 1-31, required for monthly
    start_date: str = Form(None),
    end_date: str = Form(None),
    model_name: str = Form(None),
    server_name: str = Form(None),
    server_type: str = Form(None),
    email_config_id: int = Form(None)  # New parameter
):
    """Adds a new scheduled research configuration."""
    # Validate frequency and required fields
    if frequency == "weekly" and day_of_week is None:
        raise HTTPException(status_code=400, detail="day_of_week is required for weekly frequency.")
    if frequency == "monthly" and day_of_month is None:
        raise HTTPException(status_code=400, detail="day_of_month is required for monthly frequency.")
    
    # Check if recipient group exists
    group = await database.get_email_recipient_group(recipient_group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Email recipient group not found.")
    
    await database.add_scheduled_research(
        name, frequency, hour, minute, recipient_group_id, date_range_days,
        description, day_of_week, day_of_month, start_date, end_date,
        model_name, server_name, server_type, email_config_id  # Include email_config_id
    )
    return {"message": "Scheduled research configuration added successfully."}

@app.get("/scheduled-research")
async def get_scheduled_research_list_endpoint():
    """Retrieves all scheduled research configurations."""
    research_list = await database.get_scheduled_research_list()
    return {"scheduled_research": research_list}

@app.get("/scheduled-research/{research_id}")
async def get_scheduled_research_endpoint(research_id: int):
    """Retrieves a single scheduled research configuration by ID."""
    research = await database.get_scheduled_research(research_id)
    if not research:
        raise HTTPException(status_code=404, detail="Scheduled research configuration not found.")
    return research

@app.put("/scheduled-research/{research_id}")
async def update_scheduled_research_endpoint(
    research_id: int,
    name: str = Form(None),
    description: str = Form(None),
    frequency: str = Form(None),
    day_of_week: int = Form(None),
    day_of_month: int = Form(None),
    hour: int = Form(None),
    minute: int = Form(None),
    start_date: str = Form(None),
    end_date: str = Form(None),
    is_active: bool = Form(None),
    recipient_group_id: int = Form(None),
    date_range_days: int = Form(None),
    model_name: str = Form(None),
    server_name: str = Form(None),
    server_type: str = Form(None),
    email_config_id: int = Form(None)  # New parameter
):
    """Updates a scheduled research configuration."""
    research = await database.get_scheduled_research(research_id)
    if not research:
        raise HTTPException(status_code=404, detail="Scheduled research configuration not found.")
    
    # Validate frequency and required fields if they are being updated
    if frequency is not None:
        if frequency == "weekly" and day_of_week is None and research.get('day_of_week') is None:
            raise HTTPException(status_code=400, detail="day_of_week is required for weekly frequency.")
        if frequency == "monthly" and day_of_month is None and research.get('day_of_month') is None:
            raise HTTPException(status_code=400, detail="day_of_month is required for monthly frequency.")
    
    # Check if recipient group exists (if being updated)
    if recipient_group_id is not None:
        group = await database.get_email_recipient_group(recipient_group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Email recipient group not found.")
    
    await database.update_scheduled_research(
        research_id, name, description, frequency, day_of_week, day_of_month,
        hour, minute, start_date, end_date, is_active, recipient_group_id,
        date_range_days, model_name, server_name, server_type, email_config_id  # Include email_config_id
    )
    return {"message": "Scheduled research configuration updated successfully."}

@app.delete("/scheduled-research/{research_id}", status_code=200)
async def delete_scheduled_research_endpoint(research_id: int):
    """Deletes a scheduled research configuration."""
    research = await database.get_scheduled_research(research_id)
    if not research:
        raise HTTPException(status_code=404, detail="Scheduled research configuration not found.")
    
    await database.delete_scheduled_research(research_id)
    return {"message": "Scheduled research configuration deleted successfully."}

# --- Email Delivery Log Endpoints ---

@app.get("/email-delivery-logs")
async def get_email_delivery_logs_endpoint(scheduled_research_id: int = None):
    """Retrieves email delivery logs."""
    logs = await database.get_email_delivery_logs(scheduled_research_id)
    return {"logs": logs}

# --- Test Email Endpoint ---

@app.post("/test-email")
async def test_email_endpoint(
    smtp_server: str = Form(...),
    smtp_port: int = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    sender_email: str = Form(...),
    sender_name: str = Form(None),
    use_tls: bool = Form(True),
    use_ssl: bool = Form(False),
    is_test: str = Form(None),
    config_id: int = Form(None)
):
    """Sends a test email using the provided configuration."""
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    import smtplib
    
    try:
        # If config_id is provided and is_test is true, we might want to get the config from DB
        # But for a live test with potentially new credentials, we'll use the form data
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = f"{sender_name or 'Cerberus AI'} <{sender_email}>"
        msg['To'] = sender_email  # Send to the same address for testing
        msg['Subject'] = "Cerberus AI - Email Configuration Test"
        
        # Create test email body
        test_body = """
        <html>
        <body>
            <h2>Test Email from Cerberus AI</h2>
            <p>Your email configuration is working correctly!</p>
            <p>This is a test email to confirm that your SMTP settings are properly configured.</p>
            <hr>
            <p><em>This is an automated test message from Cerberus AI.</em></p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(test_body, 'html'))
        
        # Create SMTP session based on configuration
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)
            if use_tls:
                server.starttls()
        
        # Login and send email
        server.login(username, password)
        text = msg.as_string()
        server.sendmail(sender_email, [sender_email], text)
        server.quit()
        
        return {"success": True, "message": "Test email sent successfully!"}
        
    except Exception as e:
        logging.error(f"Failed to send test email: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send test email: {str(e)}")

# --- Test Scheduled Research Endpoint ---

@app.post("/test-scheduled-research")
async def test_scheduled_research_endpoint(
    name: str = Form(...),
    description: str = Form(None),
    recipient_group_id: int = Form(None),
    date_range_days: int = Form(...),
    model_name: str = Form(None),
    server_name: str = Form(None),
    server_type: str = Form(...),
    test_email: str = Form(None),  # Optional: if provided, send to this email instead of group
    email_config_id: int = Form(None)  # Optional: specific email configuration to use
):
    """Tests scheduled research functionality by running it immediately."""
    try:
        from datetime import timedelta
        import pytz
        from research import perform_search
        import email_service
        
        ADELAIDE_TZ = pytz.timezone('Australia/Adelaide')
        
        # Either recipient_group_id or test_email must be provided
        if not recipient_group_id and not test_email:
            raise HTTPException(status_code=400, detail="Either recipient_group_id or test_email must be provided")
        
        # Calculate date range for research
        date_range_days = int(date_range_days)
        end_date = datetime.now(ADELAIDE_TZ)
        start_date = end_date - timedelta(days=date_range_days)
        
        # Format dates for query
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        # Create query
        query = f"cybersecurity incidents in Australia from {start_date_str} to {end_date_str}"
        
        # Perform research
        result, generation_time = await perform_search(
            query, server_name, model_name, server_type
        )
        
        if not result:
            raise HTTPException(status_code=400, detail="No research results found for the specified date range")
        
        # Create a mock research config for the test
        research_config = {
            'id': 0,  # Using 0 as a mock ID for test
            'name': name,
            'description': description,
            'recipient_group_id': int(recipient_group_id) if recipient_group_id else 0,
            'model_name': model_name,
            'server_name': server_name,
            'server_type': server_type
        }
        
        # Send email with test_email parameter (can be None)
        success = await email_service.send_scheduled_research_email(research_config, result, test_email, email_config_id)
        
        if success:
            return {"success": True, "message": "Test research completed and email sent successfully!"}
        else:
            raise HTTPException(status_code=500, detail="Research completed but failed to send email")
            
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logging.error(f"Failed to test scheduled research: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to test scheduled research: {str(e)}")