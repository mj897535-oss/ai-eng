FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Ensure start script has executable permissions and unix line endings
RUN chmod +x /app/start.sh 2>/dev/null || true

# Expose port
EXPOSE 8000

ENV PORT=8000

# Default command runs migrations and starts uvicorn on $PORT
CMD ["/bin/sh", "/app/start.sh"]
