# Cerberus AI - Advanced PDF Processing, Chatbot, and Cybersecurity Intelligence Platform

Cerberus AI is a comprehensive full-stack application designed to empower users with advanced PDF document processing, intelligent chatbot interactions, and robust cybersecurity threat intelligence capabilities. Leveraging containerization with Docker, Cerberus AI offers a seamless setup and deployment experience.

## Key Features

*   **Advanced PDF Analysis & Professional Export**: Upload single or multiple PDF documents for in-depth analysis. The system intelligently extracts and processes content, providing actionable insights. Export reports to professional, high-quality PDFs with selectable text, proper formatting, and pagination.
*   **Enhanced User Interface (UI/UX)**: Enjoy a clean, consistent, and intuitive user experience across all features, with polished styling and improved readability.
*   **Dynamic Ollama Integration**: Effortlessly manage and switch between various Ollama servers and their available language models directly from the intuitive frontend UI. This flexibility ensures optimal performance and model selection for diverse tasks.
*   **Asynchronous Background Processing**: Handles large-scale PDF processing tasks efficiently in the background, preventing timeouts and ensuring a smooth user experience.
*   **Real-time Task Monitoring**: Keep track of all PDF processing tasks with real-time status updates.
*   **Interactive Chatbot Interface**: Engage with a powerful language model through a user-friendly chat interface for quick queries and dynamic conversations.
*   **Threats and Risks Research**: A dedicated module for performing targeted cybersecurity threat and risk research based on specified date ranges, providing a structured overview of incidents.
*   **Incident & Company Investigation**: Conduct in-depth investigations into specific cybersecurity incidents or gather comprehensive information about companies. The AI collates and summarizes findings from various sources.
*   **Research & Investigation History**: Access and manage a detailed history of all past research queries and investigations, allowing for easy review and deletion of entries.
*   **Containerized Deployment**: Simplified setup and deployment across various environments using Docker and Docker Compose, ensuring consistency and portability.

## Technologies Utilized

*   **Frontend**:
    *   React.js (with Vite) - A modern JavaScript library for building user interfaces.
    *   Nginx - High-performance web server for serving static files and API proxying.
    *   Tailwind CSS - A utility-first CSS framework for rapid UI development.
    *   `react-icons` - A library for popular icon packs.
    *   `remark`, `strip-markdown` - Libraries for parsing and stripping Markdown.
    *   `postcss-preset-env` - A PostCSS plugin to transform modern CSS into something most browsers can understand.
*   **Backend**:
    *   FastAPI (Python) - A fast, modern, web framework for building APIs with Python 3.7+.
    *   Uvicorn - An ASGI server for FastAPI applications.
    *   `python-multipart`, `pypdf`, `python-magic`, `python-dotenv`, `httpx`, `tesseract-ocr` - Essential Python libraries for file handling, PDF processing, environment management, HTTP requests, and OCR.
    *   SQLite - A lightweight, file-based database for efficient data storage.
*   **Containerization**:
    *   Docker - Platform for developing, shipping, and running applications in containers.
    *   Docker Compose - Tool for defining and running multi-container Docker applications.
*   **Language Model Integration**:
    *   Ollama (external service) - Facilitates running large language models locally.
    *   LangChain - Framework for developing applications powered by language models.
    *   Tavily Search API - For enhanced search capabilities in research and investigation modules.

## Prerequisites

Before you begin, ensure you have the following installed:

*   **Docker**: [Install Docker](https://docs.docker.com/get-docker/)
*   **Docker Compose**: Included with Docker Desktop. For Linux, [install separately](https://docs.docker.com/compose/install/linux/).
*   **Ollama**: A running Ollama instance with your desired models pulled (e.g., `ollama pull gemma3:4b`). You will configure the Ollama server URL within the application's UI.
    *   [Download Ollama](https://ollama.com/download)

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
    This command builds and starts both the `backend` and `frontend` services in detached mode.

## Usage Guide

1.  **Access the Application**:
    Open your web browser and navigate to `http://localhost:3500`.

2.  **Configure Ollama Servers (First-time Setup)**:
    *   Click the gear icon (⚙️) in the sidebar.
    *   Add a new Ollama server by providing a descriptive name (e.g., "My Local Ollama") and its URL (e.g., `http://host.docker.internal:11434` if Ollama is running on your host machine).

3.  **Select Active Server and Model**:
    *   Use the dropdown menus in the sidebar to select your active Ollama server and the specific model you wish to use for interactions.

4.  **PDF Analysis (PDF Professor)**:
    *   Go to the "PDF Professor" section.
    *   Drag and drop your PDF files into the designated area.
    *   Enter a specific prompt for analysis.
    *   Click "Process" and monitor the task status on the "Task Status" page.

5.  **Threats and Risks Research**:
    *   Navigate to the "Threats and Risks" section.
    *   Select a desired date range.
    *   Click "Start Research" to find cybersecurity incidents within that period.

6.  **Incident & Company Investigation**:
    *   Go to the "Investigate" section.
    *   Enter a query, such as an incident name (e.g., "Allianz Life Data Breach") or a company name (e.g., "Cecuri").
    *   The AI will perform a broad search and provide a summarized overview.

7.  **Manage Research & Investigation History**:
    *   The "Research List" page displays all past date-range based research queries.
    *   The "Investigation List" page shows all past incident/company investigations.
    *   You can view detailed results or delete entries from these lists.

## Troubleshooting Common Issues

*   **`413 Request Entity Too Large`**: This error indicates that the uploaded file size exceeds the server's limit. To resolve this, increase the `client_max_body_size` in `frontend/nginx.conf` and then rebuild the frontend service: `docker-compose up -d --build frontend`.
*   **Ollama Connectivity Problems**:
    1.  Verify that your Ollama instance is running and accessible from your Docker environment.
    2.  Ensure the Ollama server URL configured in the application's UI is correct (e.g., `http://host.docker.internal:11434` for a local Ollama instance on your host).
    3.  Check the backend service logs for connection errors: `docker-compose logs backend`.
    4.  If you have modified the database schema, you might need to recreate the database by running `docker-compose down -v && docker-compose up -d --build`. **Warning**: This action will permanently delete all existing data.
*   **Containers Failing to Start**: Inspect the logs of the problematic service for detailed error messages: `docker-compose logs <service_name>`.

## Stopping the Application

To stop and remove all running containers, associated networks, and volumes, execute:
```bash
docker-compose down -v
```
To preserve your data (e.g., database entries), omit the `-v` flag: `docker-compose down`.