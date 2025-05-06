import json
import redis

from src.celery_app.worker import app, settings
from src.common.utils import get_title_and_diff, connect_repo
from src.ai.graph import run_graph

redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

@app.task(
    # Name needs to be the same as defined in webhook receiver.
    name="tasks.process_webhook"
)
def process_webhook(payload_json, command):
    data = json.loads(payload_json)
    # data = payload['data']
    owner = data['repository']['owner']['login']
    repo_name = data['repository']['name']
    pr_num = data["issue"]["number"]
    repository = connect_repo(owner=owner, repo_name=repo_name)
    pull = repository.get_pull(pr_num)
    commit_id = pull.head.sha
    issue = repository.get_issue(pr_num)
    redis_key = commit_id+command[1:]
    
    # Creating placeholder comment
    comment_id = issue.create_comment("Request received, processing...").id
    
    # Checking Redis cache
    cache_value = redis_client.hget("Task cache", redis_key)
    if cache_value is None:
        title, diff = get_title_and_diff(repository=repository, pull=pull)
        result = run_graph(title=title, diff=diff, mode=command[1:])
        
        # Populating cache
        redis_client.hset("Task cache", redis_key, result)
        # Setting cache expiry time (TTL)
        redis_client.hexpire("Task cache", 300, redis_key)
        
        # Can be an issue if second request is submitted before first request is resolved.
        
    else:
        result = str(cache_value)
    
    # Editing the placeholder comment
    issue.get_comment(comment_id).edit(result)
    
    return {"status": "processed", "result": result}