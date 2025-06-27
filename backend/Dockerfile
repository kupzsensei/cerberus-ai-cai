# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# --- Install System Dependencies ---
# Update package lists and install tesseract-ocr. This is crucial for OCR functionality.
RUN apt-get update && apt-get install -y tesseract-ocr && \
    # Clean up the apt cache to reduce image size
    rm -rf /var/lib/apt/lists/*

# Copy the dependencies file to the working directory
COPY requirements.txt .

# --- Install Python Dependencies ---
# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
COPY . .

# Make port 8000 available to the world outside this container
EXPOSE 8000

# --- Run the Application ---
# Command to run the uvicorn server. 0.0.0.0 is essential to accept connections from outside the container.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]