"""
models package

Holds schema for fields fetched from each source.
"""

from models.jira_model import JiraModel
from models.github_model import GithubModel

SOURCE_MODELS_MAP = {
    "JIRA": JiraModel,
    "GITHUB": GithubModel,
}
