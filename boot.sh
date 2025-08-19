#!/usr/bin/env bash
set -e
# Ingest sample docs into the vector DB on every start (safe & idempotent)
python ingest.py || true
# Start the API
uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}
