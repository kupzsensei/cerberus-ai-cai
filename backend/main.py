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

@app.on_event("shutdown")
async def shutdown_event():
    """On shutdown, close the httpx client."""
    await client.aclose()

async def process_and_update_task(file_name: str, user_prompt: str, model_name: str):
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
        
        processed_text = await utils.process_pdf_content(pdf_content, user_prompt, client, model_name)
        
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
    ollama_model: str = Form(default=utils.OLLAMA_MODEL_DEFAULT),
    files: List[UploadFile] = File(...)
):
    """
    Uploads multiple PDFs and processes them in the background using a specified model.
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
        await database.add_or_update_task(file.filename, user_prompt, ollama_model) 
        background_tasks.add_task(process_and_update_task, file.filename, user_prompt, ollama_model)

    if not task_ids:
        raise HTTPException(status_code=400, detail="No valid PDF files were processed.")

    return {"message": "PDF processing started in the background.", "tasks": task_ids, "model_scheduled": ollama_model}


@app.post("/pdfprofessor")
async def pdf_professor_direct(
    prompt: str = Form(...),
    ollama_model: str = Form(default=utils.OLLAMA_MODEL_DEFAULT),
    file: UploadFile = File(...)
):
    """
    Processes a single PDF synchronously using a specified model and returns the result.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF.")

    pdf_content = await file.read()
    
    processed_text = await utils.process_pdf_content(pdf_content, prompt, client, ollama_model)
    
    if "[Error:" in processed_text:
         raise HTTPException(status_code=500, detail=f"Failed to process PDF. Reason: {processed_text}")

    return {"processed_text": processed_text, "model_used": ollama_model}


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
async def research_endpoint(query: str = Form(...)):
    """
    Performs a research query and returns the results.
    """
    if not query:
        raise HTTPException(status_code=400, detail="A query is required.")
    
    result = await research.perform_search(query)
    
    return {"result": result}

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