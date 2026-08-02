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

# (EXPOSE removed to avoid Railway port mapping conflicts)
# Copy and use startup script
COPY start.sh .
RUN chmod +x start.sh

ENTRYPOINT ["/bin/sh", "./start.sh"]
