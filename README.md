# PDF Processing and Analysis with Ollama

This project provides a full-stack web application for processing and analyzing PDF documents using large language models via the Ollama API. It features a FastAPI backend for robust, asynchronous processing and a React frontend for a user-friendly interface. The entire application is containerized with Docker for easy deployment and scalability.

## Key Features

- **Dual Processing Modes**:
    
    - **Synchronous**: Upload a single PDF for immediate, real-time processing and results.
        
    - **Asynchronous**: Upload multiple PDFs for background processing, ideal for large files or long-running jobs.
        
- **Robust Text Extraction**: Automatically uses direct text extraction and falls back to Tesseract OCR for image-based or scanned PDFs.
    
- **Dynamic Model Selection**: Choose which Ollama model (e.g., `gemma3`, `llama2`, `mistral`) to use for each request directly from the frontend.
    
- **Task Management**:
    
    - View the status of all background tasks (`pending`, `in_progress`, `completed`, `failed`).
        
    - Track processing time and the model used for each task.
        
    - Delete tasks and their associated PDF files to free up space.
        
- **Containerized**: Fully configured with Docker and Docker Compose for one-command setup and deployment.
    
- **Persistent Storage**: Uses Docker volumes to persist uploaded PDFs, the task database, and logs across container restarts.
    

## Project Structure

```
/
├── backend/
│   ├── main.py             # FastAPI application
│   ├── utils.py            # PDF/Ollama processing logic
│   ├── database.py         # SQLite database operations
│   ├── config.json         # Backend configuration
│   ├── requirements.txt    # Python dependencies
│   └── Dockerfile          # Dockerfile for the backend
│
├── frontend/
│   ├── src/                # React source code
│   ├── package.json        # Frontend dependencies
│   ├── Dockerfile          # Multi-stage Dockerfile for the frontend
│   └── nginx.conf          # Nginx config for serving React app
│
├── .dockerignore           # Specifies files to ignore in Docker builds
└── docker-compose.yml      # Orchestrates all services
```

## Prerequisites

Before you begin, ensure you have the following installed on your system:

1.  **Docker**: [Download and install Docker](https://www.docker.com/products/docker-desktop/ "null")
    
2.  **Docker Compose**: Included with Docker Desktop.
    
3.  **Ollama**: A running instance of Ollama that is accessible from your Docker environment. [Download Ollama](https://ollama.com/ "null").
    

## Setup & Configuration

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd <your-project-directory>
```

### 2. Configure the Backend

The backend needs to know where to find your Ollama instance.

- **Edit `backend/config.json`**:
    
    ```json
    {
      "pdf_directory": "uploaded_pdfs",
      "output_directory": "processed_output",
      "log_directory": "logs",
      "database_file": "tasks.db",
      "ollama_api_url": "http://host.docker.internal:11434/api/generate",
      "ollama_model": "gemma3",
      "chunk_size": 4096
    }
    ```
    
- **Important `ollama_api_url` Notes**:
    
    - If Ollama is running on your **host machine** (with Docker Desktop for Mac/Windows), use `http://host.docker.internal:11434/api/generate`.
        
    - If Ollama is running in another Docker container on the same network, use its service name (e.g., `http://ollama:11434/api/generate`).
        
    - If Ollama is on a different machine on your network, use its IP address (e.g., `http://192.168.1.100:11434/api/generate`).
        

## Running the Application with Docker

Once configured, you can launch the entire application with a single command from the project root directory.

```bash
docker-compose up --build
```

- `--build`: This flag tells Docker Compose to build the images from your `Dockerfile`s the first time you run it or whenever you make changes to them.

After the build process is complete and the containers are running:

- Access the **Frontend Web Application** at: `http://localhost:3500`
    
- The **Backend API** is accessible at: `http://localhost:8001`
    

To stop the application, press `CTRL+C` in the terminal, and then run:

```bash
docker-compose down
```

## API Endpoints

You can interact with the backend API directly.

#### 1. Process PDFs (Async Background Task)

- **URL**: `/process-pdfs/`
    
- **Method**: `POST`
    
- **Form Data**:
    
    - `user_prompt` (string, required)
        
    - `ollama_model` (string, optional, defaults to `gemma3`)
        
    - `files` (file, required): One or more PDF files.
        
- **Example `curl`**:
    
    ```bash
    curl -X POST "http://localhost:8001/process-pdfs/" \
      -F "user_prompt=Summarize these documents" \
      -F "ollama_model=mistral" \
      -F "files=@/path/to/doc1.pdf" \
      -F "files=@/path/to/doc2.pdf"
    ```
    

#### 2. Get Status for All Tasks

- **URL**: `/status`
    
- **Method**: `GET`
    

#### 3. Get Status for a Specific Task

- **URL**: `/status/{task_id}`
    
- **Method**: `GET`
    

#### 4. Delete a Task

- **URL**: `/task/{task_id}`
    
- **Method**: `DELETE`
    
- **Example `curl`**:
    
    ```bash
    curl -X DELETE "http://localhost:8001/task/doc1.pdf"
    ```