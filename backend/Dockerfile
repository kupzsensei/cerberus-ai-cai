# backend/Dockerfile

# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install System Dependencies
RUN apt-get update && apt-get install -y tesseract-ocr && \
    rm -rf /var/lib/apt/lists/*

# Create a non-root user to run the application
RUN groupadd -r appgroup && useradd --no-log-init -r -g appgroup appuser

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application's code
COPY . .

# --- Create directories for volumes and set permissions ---
# Create the directories that our volumes will mount to
RUN mkdir -p logs uploaded_pdfs database && \
    # Give ownership of these directories and all app files to our user
    chown -R appuser:appgroup /app

# Switch to the non-root user
USER appuser

# Make port 8000 available
EXPOSE 8000

# Run the Application as 'appuser'
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
