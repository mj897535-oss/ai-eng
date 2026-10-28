#!/bin/sh
set -e

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

# 2. Wait briefly for backend to initialize
sleep 3

# 3. Start Next.js frontend on 127.0.0.1:3000
echo "==> Launching Next.js frontend on 127.0.0.1:3000..."
cd /app/apps/web
PORT=3000 HOSTNAME="127.0.0.1" npm start &
FRONTEND_PID=$!

# 4. Configure and run Nginx reverse proxy
echo "==> Configuring Nginx reverse proxy on port $PORT..."
envsubst '$PORT' < /app/nginx.conf.template > /etc/nginx/nginx.conf

# Trap termination signals to stop child processes gracefully
trap 'kill $BACKEND_PID $FRONTEND_PID; exit' SIGTERM SIGINT

echo "==> Starting Nginx router..."
nginx -g "daemon off;" &
NGINX_PID=$!

# Wait on Nginx process
wait $NGINX_PID
