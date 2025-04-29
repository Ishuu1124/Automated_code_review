import json
import redis

from celery_app.worker import app, settings
from github_utils import get_variables_code, connect_repo
from db.indexer import index_docs

from ghub import evaluate

redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

@app.task(
    # Name needs to be the same as defined in webhook receiver.
    name="tasks.process_tf"
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
    
    code = get_variables_code(repository, pull)
    if code is None:
        issue.get_comment(comment_id).edit("No content found in variables.tf")
        return {
            "status": "processed",
            "result": "No content."
        }
    
    # Checking Redis cache
    cache_value = redis_client.hget("Tf cache", redis_key)
    if cache_value is None:
        index_docs("guide")
        result = evaluate(code)
        
        # Populating cache
        redis_client.hset("Tf cache", redis_key, json.dumps(result))
        # Setting cache expiry time (TTL)
        redis_client.expire("Tf cache", 300)
        
        # Can be an issue if second request is submitted before first request is resolved.
        
    else:
        result = json.loads(cache_value)

    final_output = result.get("final_review", str(result))
    
    # Editing the placeholder comment
    issue.get_comment(comment_id).edit(final_output)
    
    return {"status": "processed", "result": final_output}