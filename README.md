# Cerberus AI - PDF Processing and Chatbot Application

Cerberus AI is a full-stack application designed to process PDF documents using an Ollama-powered backend and provide a user-friendly interface for document analysis and chatbot interactions. The application leverages Docker for containerization, making it easy to set up and deploy.

## Features

*   **PDF Upload and Processing**: Upload single or multiple PDF files for analysis.
*   **Ollama Integration**: Utilizes a local Ollama instance for advanced language model processing of PDF content.
*   **Background Processing**: Handles large PDF processing tasks in the background to prevent timeouts.
*   **Status Tracking**: Monitor the status of PDF processing tasks.
*   **Chatbot Interface**: (Assumed, based on `chat-bot/index.jsx`) An interface for interacting with a language model.
*   **Cybersecurity Research**: A dedicated page for performing cybersecurity threat and risk research.
*   **Containerized Deployment**: Easy setup and deployment using Docker and Docker Compose.

## Technologies Used

*   **Frontend**:
    *   React.js (with Vite)
    *   Nginx (for serving static files and proxying API requests)
    *   Tailwind CSS (for styling, inferred from `index.css` and `PdfProfessor.css` usage)
*   **Backend**:
    *   FastAPI (Python)
    *   Uvicorn (ASGI server)
    *   `python-multipart`, `pypdf`, `python-magic`, `python-dotenv`, `httpx`, `tesseract-ocr` (for PDF handling, OCR, and API calls)
    *   SQLite (for task management)
*   **Containerization**:
    *   Docker
    *   Docker Compose
*   **Language Model**:
    *   Ollama (external service)

## Prerequisites

Before you begin, ensure you have the following installed on your system:

*   **Docker**: [Install Docker](https://docs.docker.com/get-docker/)
*   **Docker Compose**: Docker Desktop includes Docker Compose. If you're on Linux, you might need to [install it separately](https://docs.docker.com/compose/install/linux/).
*   **Ollama**: You need a running Ollama instance with the desired models (e.g., `gemma3:4b`) pulled.
    *   [Download Ollama](https://ollama.com/download)
    *   Pull models: `ollama pull gemma3:4b` (or your preferred model)

## Setup and Installation

Follow these steps to get the Cerberus AI application up and running:

1.  **Clone the Repository**:
    ```bash
    git clone https://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@github.com/kupzsensei/cerberus-ai-cai.git
    cd cerberus-ai-cai
    ```
    

2.  **Configure Backend (Ollama API URL)**:
    The backend needs to know where your Ollama instance is running.
    Edit the `backend/config.json` file. The `ollama_api_url` should point to your Ollama server's API endpoint.

    Example `backend/config.json`:
    ```json
    {
      "ollama_api_url": "http://10.254.10.25:11434/api/generate",
      "ollama_model": "gemma3:4b",
      "uploaded_pdfs_dir": "uploaded_pdfs",
      "logs_dir": "logs",
      "database_path": "tasks.db"
    }
    ```
    **Important**: Ensure `ollama_api_url` matches the IP address and port where your Ollama instance is accessible from within the Docker network. If Ollama is running on the same host as Docker, `host.docker.internal` can sometimes be used, but a direct IP is more reliable if you know it.

3.  **Build and Run with Docker Compose**:
    Navigate to the root directory of the cloned repository (where `docker-compose.yml` is located) and run:
    ```bash
    docker-compose up -d --build
    ```
    *   `docker-compose up`: Creates and starts containers.
    *   `-d`: Runs containers in detached mode (in the background).
    *   `--build`: Builds (or rebuilds) images before starting containers. This is crucial for applying any changes made to Dockerfiles or configuration files.

    This command will:
    *   Build the `backend` Docker image (based on `backend/Dockerfile`).
    *   Build the `frontend` Docker image (based on `frontend/Dockerfile`).
    *   Start the `pdf_backend` container, exposing port `8001` on your host to port `8000` in the container.
    *   Start the `pdf_frontend` container, exposing port `3500` on your host to port `80` (Nginx) in the container.
    *   Create Docker volumes for `uploaded_pdfs`, `logs`, and `database` to persist data.

## Usage

1.  **Access the Application**:
    Once the containers are running, open your web browser and navigate to:
    ```
    http://localhost:3500
    ```
    (Replace `localhost` with your server's IP address if accessing remotely.)

2.  **Upload and Process PDFs**:
    *   Go to the "PDF Professor" section.
    *   Drag and drop your PDF files or click to select them.
    *   Enter a prompt for the Ollama model (e.g., "Summarize this document," "Extract key findings," etc.).
    *   Click "Process" to start background processing.
    *   Monitor the status on the "Task Status" page.

3.  **Perform Cybersecurity Research**:
    *   Navigate to the "Cybersecurity Research" section.
    *   Select a "Start Date" and "End Date" for your research query.
    *   Click "Start Research" to generate a report based on the specified date range.
    *   View the formatted results directly on the page.

4.  **Manage Research History**:
    *   Go to the "Research List" page.
    *   View a list of all your past research queries.
    *   Click "View" to see the full report for a specific query.
    *   Click "Delete" to remove a research entry from the database.

## Configuration Details

*   **`docker-compose.yml`**: Defines the services (`backend`, `frontend`), their build contexts, port mappings, volumes, and network configuration.
    *   `backend` is mapped from container port `8000` to host port `8001`.
    *   `frontend` (Nginx) is mapped from container port `80` to host port `3500`.
    *   `VITE_API_URL` in the frontend is set to `http://backend:8000`, allowing the frontend to communicate with the backend service within the Docker network.

*   **`backend/Dockerfile`**:
    *   Uses `python:3.11-slim` as the base image.
    *   Installs `tesseract-ocr` for image-based PDF processing.
    *   Installs Python dependencies from `requirements.txt`.
    *   Runs the FastAPI application using Uvicorn.

*   **`frontend/Dockerfile`**:
    *   A multi-stage build:
        *   **Stage 1 (`builder`)**: Builds the React application using Node.js.
        *   **Stage 2 (`nginx`)**: Serves the static React build files using Nginx.
    *   Copies `nginx.conf` to configure Nginx.

*   **`frontend/nginx.conf`**:
    *   Configures Nginx to serve the React static files.
    *   Includes a `location /api/` block to proxy API requests to the `backend` service (`http://backend:8000/`).
    *   **`client_max_body_size 50M;`**: This line is crucial for allowing larger PDF file uploads. It sets the maximum allowed size of the client request body.

## Troubleshooting

*   **`413 Request Entity Too Large` Error**:
    This error occurs when the uploaded file size exceeds the Nginx `client_max_body_size` limit.
    **Solution**: Ensure `client_max_body_size 50M;` (or a larger value if needed) is present in your `frontend/nginx.conf` within the `server` block. After modifying, you *must* rebuild and restart the `frontend` service:
    ```bash
    docker-compose up -d --build frontend
    ```

*   **`[Errno -2] Name or service not known` (Ollama Connectivity)**:
    This indicates the backend cannot reach your Ollama instance.
    **Solution**:
    1.  Verify your Ollama instance is running and accessible at the IP address and port specified in `backend/config.json` (e.g., `http://10.254.10.25:11434`).
    2.  Ensure the `ollama_api_url` in `backend/config.json` is correct.
    3.  After modifying `backend/config.json`, you *must* rebuild and restart the `backend` service:
        ```bash
        docker-compose up -d --build backend
        ```
    4.  Check firewall rules on your server to ensure that the backend container can reach the Ollama port.

*   **Containers Not Starting or Crashing**:
    *   Use `docker-compose logs` to view the logs of all services.
    *   Use `docker-compose logs <service_name>` (e.g., `docker-compose logs pdf_backend`) to view logs for a specific service.
    *   Check for error messages in the logs that indicate why a container failed to start or crashed.

*   **Application Not Accessible**:
    *   Verify that Docker containers are running: `docker-compose ps`.
    *   Check port mappings in `docker-compose.yml` and ensure no other services are using the same host ports (`3500`, `8001`).
    *   Check your server's firewall settings to ensure ports `3500` and `8001` are open for incoming connections.

## Stopping the Application

To stop and remove the running containers, networks, and volumes created by `docker-compose`, run:
```bash
docker-compose down -v
```
*   `-v`: Removes the named volumes declared in the `volumes` section of the `docker-compose.yml` file. This will delete your uploaded PDFs, logs, and database. Omit `-v` if you want to keep the data.
