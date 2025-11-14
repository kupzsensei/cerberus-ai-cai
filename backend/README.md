# PDF Processing API with Ollama

This FastAPI application provides a robust API for processing PDF files using an Ollama model via its REST API. It supports both text-based and image-based (scanned) PDFs by using an OCR fallback mechanism.

It allows users to upload PDFs for either immediate (synchronous) processing or long-running (asynchronous) background processing with persistent task tracking via a SQLite database.

## Project Structure


├── uploaded_pdfs/ # Directory where uploaded PDFs are stored for background tasks

├── logs/ # Directory for log files

├── tasks.db # SQLite database for tracking task status

├── main.py # The main FastAPI application
├── utils.py # Utility functions for PDF processing (including OCR) and Ollama API interaction
├── database.py # Module for all SQLite database operations

├── config.json # Configuration file

├── requirements.txt # Python dependencies

└── README.md # This file

## Setup

1.  **Prerequisite: Install Tesseract OCR Engine**

    This application uses the Tesseract engine to read text from scanned/image-based PDFs. You **must** install it on your system before running the application.

    - **On Debian/Ubuntu:**

      ```bash
      sudo apt update
      sudo apt install tesseract-ocr
      ```

    - **On macOS (using Homebrew):**

      ```bash
      brew install tesseract
      ```

    - **On Windows:**
      Download and run the installer from the official [Tesseract at UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) page. Make sure to add the Tesseract installation directory to your system's `PATH` environment variable.

2.  **Clone the repository:**

    ```bash
    git clone <your-repo-url>
    cd <your-repo-name>
    ```

3.  **Create and activate a virtual environment (recommended):**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

4.  **Install Python dependencies:**
    This will install FastAPI, PyMuPDF, pytesseract, and other required libraries.

    ```bash
    pip install -r requirements.txt
    ```

5.  **Configure the application:**
    Edit the `config.json` file to set the correct paths and your Ollama API URL. The application will create necessary directories and the `tasks.db` file on its first run.

## Running the Application

To run the FastAPI server, use uvicorn:

```bash
uvicorn main:app --reload
```

`The server will be available at http://127.0.0.1:8000`

## API Endpoints

1. **Process PDFs (Async Background Task)**
   Uploads one or more PDFs for background processing. Ideal for large files or long-running jobs.

- **URL**: `/process-pdfs/`
- **Method**: `POST`
- **Form Data**:
  - user_prompt (string, required): The prompt to be used with the Ollama model.
  - files (file, required): One or more PDF files to be processed.
- **Response** (202 Accepted):

```json
{
  "message": "PDF processing started in the background.",
  "tasks": ["file1.pdf", "file2.pdf"]
}
```

2. **Process a Single PDF (Sync)**
   Uploads a single PDF, processes it immediately, and returns the result in the response.

- **URL**: `/pdfprofessor`
- **Method**: `POST`
- **Form Data**:
  - prompt (string, required): The prompt for the Ollama model.
  - file (file, required): A single PDF file.
- **Response** (200 OK):

```json
{
  "processed_text": "This is the text from the PDF, processed by Ollama..."
}
```

- Example `curl` :

```bash
curl -X POST "[http://127.0.0.1:8000/pdfprofessor](http://127.0.0.1:8000/pdfprofessor)" \
  -F "prompt=Extract all names from this document" \
  -F "file=@/path/to/your/document.pdf"
```

3. **Get Status for All Tasks**
   Retrieves the status of all tasks submitted for background processing.

- **URL**: `/status`
- **Method**: `GET`
- **Response:**: An array of task objects.

```json
[
  {
    "task_id": "document-A.pdf",
    "status": "completed",
    "result": { "processed_text": "..." },
    "created_at": "2024-06-20T12:01:00.123Z",
    "updated_at": "2024-06-20T12:05:30.456Z"
  },
  {
    "task_id": "document-B.pdf",
    "status": "pending",
    "result": null,
    "created_at": "2024-06-20T12:02:00.789Z",
    "updated_at": "2024-06-20T12:02:00.789Z"
  }
]
```

4. **Get Status for a specific Task**

- **URL**: `/status/{task_id}`
- **Method**: `GET`
- **Path Parameter**:
  - `task_id (string, required): The filename used as the task ID.`
- **Response**: A single task object.

5. **Cybersecurity Research**

- **URL**: `/research`
- **Method**: `POST`
- **Form Data**:
 - `query (string, required): The research query.`
- **Response**: A JSON object containing the research results.

```json
{
  "task_id": "document-A.pdf",
  "status": "completed",
  "result": { "processed_text": "..." },
  "created_at": "2024-06-20T12:01:00.123Z",
  "updated_at": "2024-06-20T12:05:30.456Z"
}
```

### Summary of Changes and Benefits

- **Dual Capability:** Your application can now handle both PDFs with selectable text and scanned PDFs that are just images.
- **Efficient Design:** It uses a "fallback" mechanism. It first tries the extremely fast direct text extraction. Only if that fails does it engage the slower, more CPU-intensive OCR process.
- **Robustness:** This significantly increases the number of real-world PDFs your application can successfully process, making it far more useful.
- **Clear Documentation:** The updated `README.md` now correctly informs users about the crucial Tesseract dependency, preventing setup failures.

Your application is now significantly more powerful and versatile.

## Research Pipeline Tuning

The draft-first research pipeline powers `/research/jobs/*` and scheduled research. It now supports relevance scoring, stricter incident extraction, and a summary section in final reports. You can tune behavior via `backend/config.json` under `research_pipeline`:

- `page_size` (default 30): Search page size per pass.
- `max_candidates` (default 150): Upper bound of candidates to consider.
- `min_score` (default 3.0): Minimum relevance score to accept an incident.
- `concurrency` (default 6): Parallel fetch/analysis concurrency per page.
- `scheduled_target_count` (default 10): Target incidents when run by the scheduler.

Scoring favors Australian relevance (.au TLD, AU mentions), curated domains, incident keywords, and CVE presence; it downranks obvious aggregators/opinion pieces.

## Inbound Folder Ingest (scp/watch)

You can enable a lightweight watcher that monitors a folder for new files pushed via scp (or dropped via a mounted SMB/NFS share) and either:

- Moves PDFs into the background PDF Professor pipeline for automatic processing, or
- Moves any files into Local Storage for manual selection in the UI.

Configure it in `backend/config.json` under `inbound`:

```
"inbound": {
  "enabled": true,
  "folder": "backend/inbox",        // absolute or relative
  "poll_seconds": 5,
  "stable_seconds": 2,
  "action": "pdf_professor",        // or "local_storage"
  "server_type": "ollama",          // for auto processing
  "server_name": null,               // optional: auto-pick first if null
  "model_name": "gemma:7b",
  "prompt": "Summarize key points."
}
```

Usage examples:
- scp push: `scp report.pdf user@server:/path/to/repo/backend/inbox/`
- network share: mount a network PC folder at `/srv/inbox` and set `folder` to `/srv/inbox`.

Notes:
- `action=pdf_professor` picks up only `.pdf` files, moves them to `uploaded_pdfs/`, and schedules processing so they appear under Status.
- `action=local_storage` moves files to `backend/local_storage/` so they appear on the Local Storage page for manual querying.
