from dotenv import load_dotenv
from urllib.parse import urlparse
from github import Github
import os
from retriever.simple_rag import run_simple_rag
from evaluator.scorer import score_response, answer_length, keyword_overlap


load_dotenv()

VALID_NETLOCS = [
    "github.com",
    "www.github.com",
    ]

def parse_github_url(url: str):
    try:
        if not url.startswith(("http://","https://")):
            url = "https://" + url.lstrip("/")
        parsed_url = urlparse(url)

        # Checking if valid GitHub URL
        if parsed_url.netloc not in VALID_NETLOCS:
            raise ValueError("Not a valid GitHub URL!")
        
        # Extracting URL components
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

    simple_answer = run_simple_rag(tf_text=content)

    print("\n--- Simple RAG ---")
    print(simple_answer)

    print("\n--- Metrics ---")
    print(f"Score: {score_response(content, simple_answer):.2f}")
    print(f"Length: {answer_length(simple_answer)} tokens")