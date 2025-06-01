from celery import Celery
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class CeleryRedisSettings(BaseSettings):
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    REDIS_URL: str
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def load_settings()-> CeleryRedisSettings:
    return CeleryRedisSettings()

settings = load_settings()

celery_app = Celery(
    "tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# celery_app = Celery('automated_code_review')
celery_app.config_from_object('celery_config')
celery_app.autodiscover_tasks(['app.tasks'])
celery_app.conf.broker_connection_retry_on_startup = True
celery_app.conf.task_routes={"tasks.process_tf": {"queue": "webhooks"}}