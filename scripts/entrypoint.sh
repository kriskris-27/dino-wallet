#!/bin/bash
set -e
echo "Starting Database Initialization..."
python scripts/init_db.py
echo "Starting FastAPI Application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
