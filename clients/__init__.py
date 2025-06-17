"""
clients package

This module provides client interfaces to external systems and APIs
used in the release summarization pipeline.

Available clients:
- JiraClient: Interface for interacting with JIRA APIs
- GithubClient: Interface for querying GitHub release information
"""

from .github_client import GithubGraphQLClient

__all__ = ["GithubGraphQLClient"]
