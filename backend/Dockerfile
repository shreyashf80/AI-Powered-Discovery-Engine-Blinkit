FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Ensure data directory exists
RUN mkdir -p /data

# Expose port
EXPOSE 8000

# Run FastAPI app via uvicorn (Shell form to allow $PORT evaluation)
CMD uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
