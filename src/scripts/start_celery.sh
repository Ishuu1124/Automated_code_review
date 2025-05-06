#!/bin/bash

export PYTHONPATH=$(pwd)
cd src
echo $(pwd)
echo "[$(date)] Initiating start..."

celery -A celery_app.worker.app worker --loglevel=info