broker_url=os.getenv('CELERY_BROKER_URL','redis://localhost:6379/0')
result_backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')

task_serializer="json"
result_serializer="json"
accept_content=["json"]

task_default_queue="default"
task_default_exchange="default"
task_default_routing_key="default"

result_expires=300

task_acks_late=True
worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s"
worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(task_name)s - %(message)s"