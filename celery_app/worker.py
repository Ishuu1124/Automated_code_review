import yaml
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

app = Celery(
    "tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

app.autodiscover_tasks(['celery_app'])
app.conf.broker_connection_retry_on_startup = True
app.conf.task_routes={"tasks.process_tf": {"queue": "webhooks"}}