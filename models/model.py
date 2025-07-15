"""
models package

Holds schema for fields fetched from each source.
"""

from models.github_model import GithubModel

SOURCE_MODELS_MAP = {
    "GITHUB": GithubModel,
}
