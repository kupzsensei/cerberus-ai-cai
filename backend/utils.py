# utils.py
import os
import fitz  # PyMuPDF
import logging
import json
import httpx
from typing import List, Dict, Any
from PIL import Image
import pytesseract
import io

# --- Configuration Loading ---
def load_config(config_file='config.json'):
    with open(config_file, 'r') as f:
        return json.load(f)

config = load_config()

PDF_DIRECTORY = config['pdf_directory']
OUTPUT_DIRECTORY = config['output_directory']
LOG_DIRECTORY = config['log_directory']
#  
CHUNK_SIZE = config['chunk_size']

os.makedirs(PDF_DIRECTORY, exist_ok=True)
os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)
os.makedirs(LOG_DIRECTORY, exist_ok=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# If a Tesseract path is provided in the config, set it
TESSERACT_PATH = config.get('tesseract_path')
if TESSERACT_PATH:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
    logging.info(f"Using Tesseract executable at: {TESSERACT_PATH}")
else:
    logging.warning("Tesseract path not configured in config.json. OCR will fail if Tesseract is not in the system's PATH.")

# --- Core Logic ---
async def process_with_ollama_api(client: httpx.AsyncClient, text_chunk: str, user_prompt: str, model_name: str, ollama_api_url: str) -> str:
    """Sends a text chunk to the Ollama API for processing using a specific model."""
    combined_prompt = f"{user_prompt}\n\n---\n\n{text_chunk}"
    # The 'model' in the payload is now dynamic
    payload = {
        "model": model_name,
        "prompt": combined_prompt,
        "stream": False # We want the full response at once
    }
    try:
        logging.info(f"Sending request to Ollama with model: {model_name}")
        # Ensure the URL ends with /api/generate
        full_url = f"{ollama_api_url.rstrip('/')}/api/generate"
        logging.info(f"Sending request to Ollama URL: {full_url}")
        response = await client.post(full_url, json=payload, timeout=180.0)
        response.raise_for_status()  # Raises an exception for 4xx or 5xx status codes
        api_response = response.json()
        return api_response.get('response', '')
    except httpx.ReadTimeout:
        logging.error(f"Ollama API timed out with model: {model_name}!")
        return f"[Error: Ollama processing timed out with model: {model_name}]"
    except httpx.HTTPStatusError as e:
        logging.error(f"Ollama API request with model {model_name} failed with status {e.response.status_code}: {e.response.text}")
        return f"[Error: Ollama API failed with status {e.response.status_code}]"
    except Exception as e:
        logging.error(f"An unexpected error occurred while contacting Ollama API with model {model_name}: {e}")
        return "[Error: An unexpected error occurred]"

async def process_with_gemini_api(client: httpx.AsyncClient, text_chunk: str, user_prompt: str, model_name: str, api_key: str) -> str:
    """Sends a text chunk to the Gemini API for processing using a specific model."""
    combined_prompt = f"{user_prompt}\n\n---\n\n{text_chunk}"
    payload = {
        "contents": [{
            "parts": [{
                "text": combined_prompt
            }]
        }]
    }
    try:
        logging.info(f"Sending request to Gemini with model: {model_name}")
        full_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        logging.info(f"Sending request to Gemini URL: {full_url}")
        response = await client.post(full_url, json=payload, timeout=180.0)
        response.raise_for_status()  # Raises an exception for 4xx or 5xx status codes
        api_response = response.json()
        return api_response.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
    except httpx.ReadTimeout:
        logging.error(f"Gemini API timed out with model: {model_name}!")
        return f"[Error: Gemini processing timed out with model: {model_name}]"
    except httpx.HTTPStatusError as e:
        logging.error(f"Gemini API request with model {model_name} failed with status {e.response.status_code}: {e.response.text}")
        return f"[Error: Gemini API failed with status {e.response.status_code}]"
    except Exception as e:
        logging.error(f"An unexpected error occurred while contacting Gemini API with model {model_name}: {e}")
        return "[Error: An unexpected error occurred]"

def perform_ocr_on_pdf_bytes(file_content: bytes) -> str:
    """
    Performs OCR on each page of a PDF and returns the combined text.
    """
    # The Tesseract path is now configured globally at startup.
    text = ""
    logging.info("Performing OCR on PDF...")
    try:
        pdf_document = fitz.open(stream=file_content, filetype="pdf")
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_bytes))
            
            # Use pytesseract to do OCR on the image
            page_text = pytesseract.image_to_string(image)
            text += page_text + "\n"
        
        pdf_document.close()
        logging.info("OCR completed successfully.")
        return text
    
    except pytesseract.TesseractNotFoundError:
        error_msg = "TesseractNotFoundError: The Tesseract executable was not found. Please make sure it is installed and the path is correct in utils.py."
        logging.error(error_msg)
        return f"[Error: {error_msg}]"
    except Exception as e:
        # Catch any other exception during OCR
        error_msg = f"An unexpected error occurred during OCR: {e}"
        logging.error(error_msg, exc_info=True) # exc_info=True will log the full traceback
        return f"[Error: {error_msg}]"


def read_pdf_from_bytes(file_content: bytes) -> str:
    """
    Extracts text content from PDF bytes, falling back to OCR if needed.
    """
    content = ""
    try:
        # 1. First, try the fast direct text extraction
        doc = fitz.open(stream=file_content, filetype="pdf")
        content = "".join(page.get_text() for page in doc)
        doc.close()

    except Exception as e:
        # This can happen if the PDF is malformed
        logging.error(f"Error during initial text extraction with PyMuPDF: {e}", exc_info=True)
        # We can still attempt OCR as a last resort
        content = "" # Ensure content is empty to trigger OCR

    try:
        # 2. If content is empty or just whitespace, fall back to OCR.
        if not content.strip():
            logging.warning("No embedded text found in PDF or initial extraction failed. Falling back to OCR.")
            return perform_ocr_on_pdf_bytes(file_content)

        logging.info("Successfully extracted embedded text from PDF.")
        return content
    except Exception as e:
        # Catch-all for any other unexpected error
        logging.error(f"A fatal error occurred in read_pdf_from_bytes: {e}", exc_info=True)
        return f"[Error: Could not read PDF file. Reason: {e}]"


async def process_pdf_content(
    file_content: bytes, 
    user_prompt: str, 
    client: httpx.AsyncClient,
    model_name: str,  # Pass the model name to be used
    server_type: str, # New: Pass the server type
    server_url_or_key: str # New: Pass either URL (for Ollama) or API Key (for Gemini)
) -> str:
    """
    Processes the content of a PDF file asynchronously using the specified AI API.
    """
    content = read_pdf_from_bytes(file_content)
    if not content or content.startswith("[Error:"):
        logging.error(f"Failed to extract content from PDF. Result: {content}")
        return content if content else "Could not extract any text from the provided PDF."

    chunks = [content[i:i + CHUNK_SIZE] for i in range(0, len(content), CHUNK_SIZE)]
    processed_content_parts = []
    
    for chunk in chunks:
        if server_type == "ollama":
            processed_chunk = await process_with_ollama_api(client, chunk, user_prompt, model_name, server_url_or_key)
        elif server_type == "gemini":
            processed_chunk = await process_with_gemini_api(client, chunk, user_prompt, model_name, server_url_or_key)
        else:
            return f"[Error: Unsupported server type: {server_type}]"
        processed_content_parts.append(processed_chunk)
    
    return "".join(processed_content_parts)

async def process_text_content(
    text_content: str, 
    user_prompt: str, 
    client: httpx.AsyncClient,
    model_name: str,  # Pass the model name to be used
    server_type: str, # New: Pass the server type
    server_url_or_key: str # New: Pass either URL (for Ollama) or API Key (for Gemini)
) -> str:
    """
    Processes a string of text asynchronously using the specified AI API.
    """
    if not text_content or text_content.startswith("[Error:"):
        logging.error(f"Invalid text content provided. Content: {text_content}")
        return text_content if text_content else "Could not process empty text."

    chunks = [text_content[i:i + CHUNK_SIZE] for i in range(0, len(text_content), CHUNK_SIZE)]
    processed_content_parts = []
    
    for chunk in chunks:
        if server_type == "ollama":
            processed_chunk = await process_with_ollama_api(client, chunk, user_prompt, model_name, server_url_or_key)
        elif server_type == "gemini":
            processed_chunk = await process_with_gemini_api(client, chunk, user_prompt, model_name, server_url_or_key)
        else:
            return f"[Error: Unsupported server type: {server_type}]"
        processed_content_parts.append(processed_chunk)
    
    return "".join(processed_content_parts)
