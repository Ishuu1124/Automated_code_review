from celery import Celery

celery_app = Celery('automated_code_review')
celery_app.config_from_object('celery_config')
celery_app.autodiscover_tasks(['app.tasks'])
celery_app.conf.broker_connection_retry_on_startup = True
celery_app.conf.task_routes={"tasks.process_tf": {"queue": "webhooks"}}