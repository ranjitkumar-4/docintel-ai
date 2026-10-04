#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "=================================================="
echo "    DocIntel AI — Intelligent Document Investigator"
echo "=================================================="

trap 'echo "Stopping DocIntel AI services..."; kill $(jobs -p) 2>/dev/null' EXIT

# Start Backend
./run_backend.sh &
BACKEND_PID=$!

# Wait briefly for backend to initialize
sleep 2

# Start Frontend
./run_frontend.sh &
FRONTEND_PID=$!

echo ""
echo "DocIntel AI is live!"
echo "Backend:  http://127.0.0.1:8000"
echo "API Docs: http://127.0.0.1:8000/docs"
echo "Frontend: http://localhost:5173"
echo "Press Ctrl+C to terminate all services."
echo ""

wait
