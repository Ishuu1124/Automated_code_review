#!/bin/bash

export PYTHONPATH=$(pwd)
echo $(pwd)
echo "[$(date)] Initiating start..."

celery -A app.celery_app.worker.celery_app worker --loglevel=info --pool=threads --concurrency=10 &

sleep 30

python -m http.server 8080