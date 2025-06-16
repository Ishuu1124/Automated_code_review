#!/bin/bash

export PYTHONPATH=$(pwd)
echo $(pwd)
echo "[$(date)] Initiating start..."

celery -A app.celery_app.worker.celery_app worker --loglevel=info --pool=threads --concurrency=10 &
echo "[$(date)] Celery worker started." &
uvicorn app.api.app:app --host 0.0.0.0 --port 8000 --reload