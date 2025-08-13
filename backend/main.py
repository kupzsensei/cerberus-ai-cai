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
    """On startup, configure and initialize the database."""
    db_file = utils.config.get("database_file", "tasks.db")
    database.configure_database(db_file)
    await database.initialize_db()
    await database.initialize_research_db()
    await database.initialize_local_storage_db()

@app.on_event("shutdown")
async def shutdown_event():
    """On shutdown, close the httpx client."""
    await client.aclose()

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