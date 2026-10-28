FROM python:3.12-slim

WORKDIR /app

# Install system dependencies, Node.js 20, nginx, gettext (for envsubst)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    nginx \
    gettext-base \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Python backend dependencies
COPY apps/api/requirements.txt ./apps/api/requirements.txt
RUN pip install --no-cache-dir -r ./apps/api/requirements.txt

# Install Node.js frontend dependencies
COPY apps/web/package.json apps/web/package-lock.json* ./apps/web/
RUN cd apps/web && npm install

# Copy monorepo source code
COPY . .

# Build Next.js application (defaults to relative /api/v1 so reverse proxy handles it seamlessly)
ENV NEXT_PUBLIC_API_URL=/api/v1
RUN cd apps/web && npm run build

# Make startup scripts executable
RUN chmod +x /app/apps/api/start.sh /app/entrypoint.sh 2>/dev/null || true

EXPOSE 8000 3000 10000

ENV PORT=10000
ENV SERVICE_TYPE=all

CMD ["/bin/sh", "/app/entrypoint.sh"]
