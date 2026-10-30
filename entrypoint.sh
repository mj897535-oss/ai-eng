#!/bin/sh

PORT="${PORT:-10000}"

if [ "$SERVICE_TYPE" = "api" ]; then
    echo "==> Starting API-only mode on port $PORT..."
    cd /app/apps/api
    exec /bin/sh /app/apps/api/start.sh
fi

if [ "$SERVICE_TYPE" = "web" ]; then
    echo "==> Starting Web-only mode on port $PORT..."
    cd /app/apps/web
    exec npm start
fi

echo "=========================================================="
echo " Starting SyntaxLens Full-Stack (Backend + Frontend)"
echo " Listening on Render Port: $PORT"
echo "=========================================================="

# 1. Start backend service in background
echo "==> Launching FastAPI backend on 127.0.0.1:8000..."
cd /app/apps/api
PORT=8000 /bin/sh /app/apps/api/start.sh &
BACKEND_PID=$!

# 2. Start Next.js frontend in background
echo "==> Launching Next.js frontend on 127.0.0.1:3000..."
cd /app/apps/web
PORT=3000 HOSTNAME="127.0.0.1" npm start &
FRONTEND_PID=$!

# 3. Wait for FastAPI backend upstream to be ready
echo "==> Waiting for FastAPI backend (127.0.0.1:8000) to initialize..."
RETRIES=0
while [ $RETRIES -lt 30 ]; do
    if curl -s -o /dev/null http://127.0.0.1:8000/api/v1/health; then
        echo "✓ FastAPI backend is ready and listening on port 8000."
        break
    fi
    sleep 1
    RETRIES=$((RETRIES + 1))
done

# 4. Wait for Next.js frontend upstream to be ready
echo "==> Waiting for Next.js frontend (127.0.0.1:3000) to initialize..."
RETRIES=0
while [ $RETRIES -lt 30 ]; do
    if curl -s -o /dev/null http://127.0.0.1:3000/; then
        echo "✓ Next.js frontend is ready and listening on port 3000."
        break
    fi
    sleep 1
    RETRIES=$((RETRIES + 1))
done

# 5. Configure Nginx reverse proxy
echo "==> Configuring Nginx reverse proxy on port $PORT..."
envsubst '$PORT' < /app/nginx.conf.template > /etc/nginx/nginx.conf

# Trap termination signals to stop child processes gracefully
trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0' TERM INT

echo "==> Starting Nginx router on port $PORT (all upstreams ready)..."
nginx -g "daemon off;"
