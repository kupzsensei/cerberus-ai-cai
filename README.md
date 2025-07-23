# Cerberus AI - PDF Processing and Chatbot Application

Cerberus AI is a full-stack application designed to process PDF documents using an Ollama-powered backend and provide a user-friendly interface for document analysis and chatbot interactions. The application leverages Docker for containerization, making it easy to set up and deploy.

## Features

*   **PDF Upload and Processing**: Upload single or multiple PDF files for analysis.
*   **Dynamic Ollama Integration**: Add, delete, and select different Ollama servers and their available models directly from the frontend UI.
*   **Background Processing**: Handles large PDF processing tasks in the background to prevent timeouts.
*   **Status Tracking**: Monitor the status of PDF processing tasks.
*   **Chatbot Interface**: An interface for interacting with a language model.
*   **Cybersecurity Research**: A dedicated page for performing cybersecurity threat and risk research.
*   **Containerized Deployment**: Easy setup and deployment using Docker and Docker Compose.

## Technologies Used

*   **Frontend**:
    *   React.js (with Vite)
    *   Nginx (for serving static files and proxying API requests)
    *   Tailwind CSS
    *   `react-icons`
*   **Backend**:
    *   FastAPI (Python)
    *   Uvicorn (ASGI server)
    *   `python-multipart`, `pypdf`, `python-magic`, `python-dotenv`, `httpx`, `tesseract-ocr`
    *   SQLite
*   **Containerization**:
    *   Docker
    *   Docker Compose
*   **Language Model**:
    *   Ollama (external service)

## Prerequisites

*   **Docker**: [Install Docker](https://docs.docker.com/get-docker/)
*   **Docker Compose**: Included with Docker Desktop. For Linux, [install separately](https://docs.docker.com/compose/install/linux/).
*   **Ollama**: A running Ollama instance with desired models pulled. You will configure the server URL in the application's UI.
    *   [Download Ollama](https://ollama.com/download)
    *   Pull a model: `ollama pull gemma3:4b`

## Setup and Installation

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/kupzsensei/cerberus-ai-cai.git
    cd cerberus-ai-cai
    ```

2.  **Build and Run with Docker Compose**:
    ```bash
    docker-compose up -d --build
    ```
    This command builds and starts the `backend` and `frontend` services in detached mode.

## Usage

1.  **Access the Application**:
    Open your browser and go to `http://localhost:3500`.

2.  **Configure Ollama Servers (First Time)**:
    *   Click the gear icon in the sidebar.
    *   Add a new server by providing a name (e.g., "My Local Ollama") and the URL (e.g., `http://host.docker.internal:11434` if Ollama is on your host).

3.  **Select Server and Model**:
    *   Use the dropdowns in the sidebar to select the active server and model.

4.  **Upload and Process PDFs**:
    *   Go to the "PDF Professor" section.
    *   Drag and drop your PDF files.
    *   Enter a prompt.
    *   Click "Process" and monitor the status on the "Task Status" page.

5.  **Perform Cybersecurity Research**:
    *   Navigate to the "Cybersecurity Research" section.
    *   Select a date range and click "Start Research".

6.  **Manage Research History**:
    *   The "Research List" page shows all past research queries. You can view or delete them.

## Troubleshooting

*   **`413 Request Entity Too Large`**: Increase `client_max_body_size` in `frontend/nginx.conf` and rebuild the frontend: `docker-compose up -d --build frontend`.
*   **Ollama Connectivity Issues**:
    1.  Verify your Ollama instance is running and accessible.
    2.  Ensure the server URL in the UI is correct (use `http://host.docker.internal:11434` for a local Ollama instance).
    3.  Check backend logs for connection errors: `docker-compose logs backend`.
    4.  If you changed the database schema, you may need to recreate the database by running `docker-compose down -v && docker-compose up -d --build`. **Warning**: This deletes all data.
*   **Containers Not Starting**: Check logs with `docker-compose logs <service_name>`.

## Stopping the Application

To stop and remove all containers, networks, and volumes, run:
```bash
docker-compose down -v
```
Omit the `-v` flag to preserve your data.
