# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# --- Install System Dependencies ---
RUN apt-get update && apt-get install -y tesseract-ocr && \
    rm -rf /var/lib/apt/lists/*

# --- Create a non-root user to run the application ---
# Create a new group named 'appgroup' and a new user named 'appuser'
RUN groupadd -r appgroup && useradd --no-log-init -r -g appgroup appuser

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install Python Dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code
# We change the ownership of the copied files to our new user
COPY --chown=appuser:appgroup . .

# --- Set Correct Permissions ---
# Ensure the 'appuser' owns the entire /app directory, including where volumes will be mounted
RUN chown -R appuser:appgroup /app

# Switch to the non-root user
USER appuser

# Make port 8000 available
EXPOSE 8000

# Run the Application as 'appuser'
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
