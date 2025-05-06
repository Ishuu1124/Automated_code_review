#!/bin/bash
HOST=${HOST:-"0.0.0.0"}
PORT=${PORT:-"8000"}
export PYTHONPATH=$(pwd)
cd src
echo $(pwd)
echo "[$(date)] Initiating start..."

uvicorn app:app --host ${HOST} --port ${PORT} --reload --log-level debug