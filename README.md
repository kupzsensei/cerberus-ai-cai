# Cerberus AI - Advanced PDF Processing, Chatbot, and Cybersecurity Intelligence Platform

Cerberus AI is a comprehensive full-stack application designed to empower users with advanced PDF document processing, intelligent chatbot interactions, and robust cybersecurity threat intelligence capabilities. Leveraging containerization with Docker, Cerberus AI offers a seamless setup and deployment experience.

## Key Features

*   **Advanced PDF Analysis & Professional Export**: Upload single or multiple PDF documents for in-depth analysis. The system intelligently extracts and processes content, providing actionable insights. Export reports to professional, high-quality PDFs with selectable text, proper formatting, and pagination.
*   **Enhanced User Interface (UI/UX)**: Enjoy a clean, consistent, and intuitive user experience across all features, with polished styling and improved readability.
*   **Dynamic AI Server Integration**: Effortlessly manage and switch between various Ollama and Gemini servers and their available language models directly from the intuitive frontend UI. This flexibility ensures optimal performance and model selection for diverse tasks.
*   **Asynchronous Background Processing**: Handles large-scale PDF processing tasks efficiently in the background, preventing timeouts and ensuring a smooth user experience.
*   **Real-time Task Monitoring**: Keep track of all PDF processing tasks with real-time status updates.
*   **Interactive Chatbot Interface**: Engage with a powerful language model through a user-friendly chat interface for quick queries and dynamic conversations.
*   **Threats and Risks Research**: A dedicated module for performing targeted cybersecurity threat and risk research based on specified date ranges, providing a structured overview of incidents.
*   **Incident & Company Investigation**: Conduct in-depth investigations into specific cybersecurity incidents or gather comprehensive information about companies. The AI collates and summarizes findings from various sources.
*   **Research & Investigation History**: Access and manage a detailed history of all past research queries and investigations, allowing for easy review and deletion of entries.
*   **Enhanced Local File Storage**: Manage your files with an improved interface featuring group delete and download operations, and a streamlined file upload process through a dedicated modal.
*   **Automated Email Reports**: Schedule and automatically send cybersecurity threat research reports via email. Configure SMTP settings, manage recipient lists, and set up recurring research tasks with flexible scheduling options.
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
    *   `apscheduler` - A library for scheduling tasks in Python applications.
    *   SQLite - A lightweight, file-based database for efficient data storage.
*   **Containerization**:
    *   Docker - Platform for developing, shipping, and running applications in containers.
    *   Docker Compose - Tool for defining and running multi-container Docker applications.
*   **Language Model Integration**:
    *   Ollama (external service) - Facilitates running large language models locally.
    *   Gemini (external service) - Google's family of generative AI models.
    *   LangChain - Framework for developing applications powered by language models.
    *   Tavily Search API - For enhanced search capabilities in research and investigation modules.

## Prerequisites

Before you begin, ensure you have the following installed:

*   **Docker**: [Install Docker](https://docs.docker.com/get-docker/)
*   **Docker Compose**: Included with Docker Desktop. For Linux, [install separately](https://docs.docker.com/compose/install/linux/).
*   **Ollama (Optional)**: A running Ollama instance with your desired models pulled (e.g., `ollama pull gemma3:4b`). You will configure the Ollama server URL within the application's UI.
    *   [Download Ollama](https://ollama.com/download)
*   **Gemini API Key (Optional)**: A Google AI Gemini API key.
*   **SMTP Server Access (Optional)**: Access to an SMTP server for sending automated email reports (e.g., Gmail SMTP, Outlook SMTP, or your organization's SMTP server).

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

2.  **Configure AI Servers (First-time Setup)**:
    *   Click the gear icon (⚙️) in the sidebar.
    *   Add a new Ollama or Gemini server by providing a descriptive name and its URL or API key.

3.  **Select Active Server and Model**:
    *   Use the dropdown menus in the sidebar to select your active AI server and the specific model you wish to use for interactions.

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

8.  **Local File Storage Management**:
    *   Navigate to the \"My Files\" section in the LocalStorage menu.
    *   Upload files using the \"Upload Files\" button which opens a dedicated modal with drag and drop functionality.
    *   Select multiple files using checkboxes to perform group operations:
        *   Delete multiple files at once
        *   Download multiple files at once
    *   View or download individual files using the action buttons on each file card.
    *   Query selected files using the prompt area at the bottom of the page.

9.  **Automated Email Reports (Email Scheduler)**:
    *   Navigate to the \"Email Scheduler\" section in the sidebar.
    *   Configure your SMTP email settings in the \"Email Configuration\" tab.
    *   Create recipient groups and add email addresses in the \"Recipient Groups\" tab.
    *   Set up scheduled research tasks in the \"Scheduled Research\" tab:
        *   Choose a frequency (daily, weekly, or monthly)
        *   Set the time for the reports to be generated
        *   Select a recipient group to receive the reports
        *   Configure the date range for research (e.g., last 7 days)
        *   Optionally specify which AI model and server to use
    *   Monitor email delivery status in the \"Delivery Logs\" tab.
    *   Reports will be automatically generated and sent according to your schedule.

## Troubleshooting Common Issues

*   **`413 Request Entity Too Large`**: This error indicates that the uploaded file size exceeds the server's limit. To resolve this, increase the `client_max_body_size` in `frontend/nginx.conf` and then rebuild the frontend service: `docker-compose up -d --build frontend`.
*   **AI Server Connectivity Problems**:
    1.  Verify that your Ollama or Gemini instance is running and accessible from your Docker environment.
    2.  Ensure the AI server URL or API key configured in the application's UI is correct.
    3.  Check the backend service logs for connection errors: `docker-compose logs backend`.
    4.  If you have modified the database schema, you might need to recreate the database by running `docker-compose down -v && docker-compose up -d --build`. **Warning**: This action will permanently delete all existing data.
*   **Email Sending Issues**:
    1.  Verify that your SMTP server settings are correct in the Email Scheduler configuration.
    2.  Ensure that your SMTP credentials are valid and have the necessary permissions.
    3.  Check that your SMTP server is accessible from the Docker environment.
    4.  Review the email delivery logs in the Email Scheduler's "Delivery Logs" tab for specific error messages.
*   **Containers Failing to Start**: Inspect the logs of the problematic service for detailed error messages: `docker-compose logs <service_name>`.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue to discuss your ideas.

## Stopping the Application

To stop and remove all running containers, associated networks, and volumes, execute:
```bash
docker-compose down -v
```
To preserve your data (e.g., database entries), omit the `-v` flag: `docker-compose down`.
