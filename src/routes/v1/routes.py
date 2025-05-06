from fastapi import APIRouter
from celery.result import AsyncResult

from src.constants import urls
from src.celery_app.tasks import process_webhook

router = APIRouter(prefix=urls.PR_VERSION_1)

@router.get(urls.HEALTH)
def healthcheck():
    return {'status': 'ok'}

@router.post(urls.GET_SUMMARY)
def summary(payload: dict):
    task=process_webhook.delay(payload)
    return {'task_id': task.id}

@router.get("/status/{task_id}")
def get_task_status(task_id: str):
    result = AsyncResult(task_id)
    return {
        'id': task_id,
        'status': result.status,
        'result': result.result
    }