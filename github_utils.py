import os
import yaml
from github.Repository import Repository
from github.PullRequest import PullRequest
from github import Auth, Github, GithubIntegration
from pydantic_settings import BaseSettings, SettingsConfigDict

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

def get_variables_code(
    repository: Repository,
    pull: PullRequest
    ):
    """
    """
    
    changed_files = pull.get_files()
    head_sha = pull.head.sha
    
    for changed_file in changed_files:
        print(changed_file.filename)
        if changed_file.filename == "variables.tf":
            try:
                code = repository.get_contents(changed_file.filename, ref=head_sha)
                code = code.decoded_content.decode("utf-8")
                return code
            except Exception as e:
                return None
    return None
