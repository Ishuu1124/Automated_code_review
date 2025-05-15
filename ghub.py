from dotenv import load_dotenv
from urllib.parse import urlparse
from github import Github
import os
from retriever.simple_rag import run_simple_rag
from evaluator.scorer import score_response, answer_length

load_dotenv()
VALID_NETLOCS = [
    "github.com",
    "www.github.com",
]

def parse_github_url(url: str):
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url.lstrip("/")
        parsed_url = urlparse(url)
        if parsed_url.netloc not in VALID_NETLOCS:
            raise ValueError("Not a valid GitHub URL!")
        path_parts = parsed_url.path.strip("/").split("/")
        owner, repository_name = path_parts[0], path_parts[1]
        return (owner, repository_name)
    except Exception as e:
        raise ValueError(f"Error parsing GitHub PR URL!")
    
def evaluate_tf_from_github(repo_url: str):
    (owner, repo_name) = parse_github_url(repo_url)
    g = Github(os.getenv("GITHUB_TOKEN"))
    try:
        repo = g.get_repo(f"{owner}/{repo_name}")
    except:
        repo = g.get_organization(owner).get_repo(repo_name)
    f = repo.get_contents('variables.tf')
    content = f.decoded_content.decode()
    print(f"\nEvaluating variables.tf file from: {repo_url}")
    print("=" * 60)
    result = run_simple_rag(tf_text=content)

    print("\n--- Review ---")  # Updated title from "Final Review"

    print(result["final_review"])
    print("\n--- Corrected variables.tf ---")
    print(result["corrected_code"])
    print("\n--- Metrics ---")
    print(f"Score: {score_response(content, result['final_review']):.2f}")
    print(f"Length: {answer_length(result['final_review'])} tokens")

def evaluate(code: str):
    print(f"\nEvaluating...")
    print("=" * 60)
    try:
        result = run_simple_rag(tf_text=code)
    except Exception as e:
        print(f"Evaluation failed: {e}")
        result = None
    if not isinstance(result, dict):
        result = {}
    final_review = result.get("final_review", "No review generated.")
    corrected_code = result.get("corrected_code", "")

    print("\n--- Review ---")  # Updated title from "Final Review"

    print(final_review)
    print("\n--- Corrected variables.tf ---")
    print(corrected_code)
    print("\n--- Metrics ---")
    print(f"Score: {score_response(code, final_review):.2f}")
    print(f"Length: {answer_length(final_review)} tokens")
    return {
        "final_review": final_review,
        "corrected_code": corrected_code
    }
