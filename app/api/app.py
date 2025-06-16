from fastapi import FastAPI, Request, HTTPException
# from celery_app.tasks import process_webhook
# from celery_app.worker import celery_app
from celery import Celery
from app.celery_app.worker import settings

celery_app = Celery(
    "tasks",
    broker=settings.REDIS_URL
)

app = FastAPI()

@app.get('/health')
async def healthcheck():
    return {"status": "ok"}

@app.post('/queue')
async def queue_task(
    request: Request
):
    payload_dict = await request.json()
    data = payload_dict.get('payload')
    command = payload_dict.get('command')
    arguments = payload_dict.get('arguments')
    if data is None or command is None:
        raise HTTPException(status_code=400, detail='Details not found for request')
    try:
        owner = data['repository']['owner']['login']
        repo_name = data['repository']['name']
        pr_num = data["issue"]["number"]
    except KeyError:
        raise HTTPException(status_code=400, detail='Invalid GitHub payload')
    celery_app.send_task('tasks.process_tf', args=[owner, repo_name, pr_num, command, arguments])
    return {
        'status': 'queued'
    }
    
    