#!/bin/bash

export PYTHONPATH=$(pwd)
echo $(pwd)
echo "[$(date)] Initiating start..."

celery -A celery_app.worker.app worker --loglevel=info --pool threads