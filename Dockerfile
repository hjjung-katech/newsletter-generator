FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
COPY web/requirements.txt ./web/

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install -r web/requirements.txt

# Copy application code
COPY . .

# Set Python path
ENV PYTHONPATH=/app:/app/web

# Create storage directory
RUN mkdir -p /app/web/storage

# Expose port
EXPOSE $PORT

# Default command (can be overridden)
CMD ["sh", "-c", "cd web && gunicorn --bind 0.0.0.0:$PORT app:app"]
