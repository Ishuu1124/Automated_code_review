import os
import yaml
from github.Repository import Repository
from github.PullRequest import PullRequest
from github import Auth, Github, GithubIntegration
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.models.models import DiffModel

class GithubSettings(BaseSettings):
    GITHUB_BOT_ID: str
    GITHUB_BOT_SECRET: str
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

def connect_repo(
    owner: str,
    repo_name: str
):
    settings = GithubSettings()
    auth = Auth.AppAuth(settings.GITHUB_BOT_ID, private_key=settings.GITHUB_BOT_SECRET)
    github_integration = GithubIntegration(auth=auth)
    installation_id = github_integration.get_repo_installation(owner, repo_name).id
    access_token = github_integration.get_access_token(installation_id).token
    connection = Github(login_or_token=access_token)
    return connection.get_repo(f"{owner}/{repo_name}")

def get_title_and_diff(
    repository: Repository,
    pull: PullRequest
    ):
    """Gets the pull request information (title and code changes) using the GitHub API.

    Parameters:
    - repository (github.Repository) - Repository object corresponding to the pull request's repository.
    - pull (github.PullRequest) - Pull request object corresponding to the pull request.
    
    Returns:
    - title (str) - Title of the PR.
    - diff (List[DiffModel]) - List of files with their code changes.
    """
    
    title = pull.title
    changed_files = pull.get_files()
    diff = []
    base_sha = pull.base.sha
    head_sha = pull.head.sha
    
    # Storing changed files' contents before and after the changes
    for changed_file in changed_files:
        filename = changed_file.filename
        try:
            base_file = repository.get_contents(filename, ref=base_sha)
            base_code = base_file.decoded_content.decode("utf-8")
        #TODO: check which exception is raised specifically for files not being present.
        except Exception:
            base_code = None   # probably new file created, so doesn't exist in base commit
        try:
            head_file = repository.get_contents(filename, ref=head_sha)
            head_code = head_file.decoded_content.decode("utf-8")
        except Exception:
            head_code = None   # probably file deleted, so doesn't exist in head commit
        d = {
            "filename": filename,
            "diff_url": changed_file.blob_url,
            "initial_code": base_code,
            "changed_code": head_code
        }
        diff.append(DiffModel(**d))
    return title, diff
