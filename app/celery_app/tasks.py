import json
import redis
from app.celery_app.worker import celery_app, settings
from app.github_utils import get_variables_code, connect_repo
from app.db.indexer import index_docs
from app.ghub import evaluate

redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

@celery_app.task(
    name="tasks.process_tf"
)
def process_webhook(owner: str, repo_name: str, pr_num: int, command: str):
    # data = json.loads(payload_json)
    # owner = data['repository']['owner']['login']
    # repo_name = data['repository']['name']
    # pr_num = data["issue"]["number"]
    repository = connect_repo(owner=owner, repo_name=repo_name)
    pull = repository.get_pull(pr_num)
    commit_id = pull.head.sha
    issue = repository.get_issue(pr_num)
    redis_key = commit_id + command[1:]
    # Create a placeholder comment
    comment_id = issue.create_comment("Request received, processing...").id
    code_to_review = get_variables_code(repository, pull)
    code = code_to_review[0]
    if code is None:
        issue.get_comment(comment_id).edit("No content found in variables.tf")
        return {
            "status": "processed",
            "result": "No content."
        }
    # Check Redis cache
    cache_value = redis_client.hget("Tf cache", redis_key)
    if cache_value is None:
        index_docs("src/guide")
        result = evaluate(code)
        # Populate cache
        redis_client.hset("Tf cache", redis_key, json.dumps(result))
        # Setting cache expiry time (TTL) for the entire "Tf cache" hash
        redis_client.expire("Tf cache", 300)
    else:
        result = json.loads(cache_value)
    # Prepare final output for GitHub comment
    final_review = result.get("final_review", "")
    corrected_code = result.get("corrected_code", "")
    final_output = ""
    if final_review:
        final_output += f"## Review\n\n{final_review}\n\n"
    if corrected_code:
        final_output += f"## Corrected variables.tf\n\n```hcl\n{corrected_code}\n```"
    if not final_output:
        final_output = "No meaningful review or corrected code was generated."
    # Edit the placeholder comment with the final output
    issue.get_comment(comment_id).edit(final_output)
    return {"status": "processed", "result": final_output}