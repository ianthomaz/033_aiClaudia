# ☁️👜 aiClaudia - API Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the essential files that need to be in the image
COPY api_server.py .

# Create directories for volume mounts
RUN mkdir -p /app/front /app/deploy

# Make scripts executable
RUN chmod +x *.py

# Expose port
EXPOSE 5000

# Run the API server
CMD ["python3", "api_server.py"]
