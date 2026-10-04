#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

if [ ! -x ".venv/bin/python" ]; then
    echo "Creating virtual environment..."
    python3.11 -m venv .venv
    .venv/bin/python -m pip install -r backend/requirements.txt
fi

echo "Starting DocIntel AI Backend on http://127.0.0.1:8000..."
export PYTHONPATH=backend
exec .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
