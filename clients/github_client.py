import requests
from typing import List, Dict, Any
from config.settings import get_settings
from utils.logging_config import get_logger

logger = get_logger(__name__)

settings = get_settings()


class GithubGraphQLClient:
    """
    GitHub GraphQL API client optimized for batch operations.

    This client is designed to efficiently fetch multiple GitHub resources
    (PRs and commits) in single GraphQL queries rather than making individual
    REST API calls. This approach significantly reduces API usage and improves
    performance when processing many GitHub URLs.

    Key Features:
    - Batched GraphQL queries with aliases
    - Automatic authentication handling
    - Support for both Pull Requests and commits
    - Error handling and rate limit awareness

    The client uses GraphQL aliases to fetch multiple items in one query:
    ```
    query {
      item0: repository(...) { pullRequest(...) { ... } }
      item1: repository(...) { object(...) { ... } }
    }
    ```
    """

    def __init__(self) -> None:
        """
        Initialize GitHub client with API configuration and authentication.

        Validates that required environment variables are set and configures
        the client for API access.

        Raises:
            ValueError: If required environment variables are missing
        """
        self.api_url: str = settings.api.github_api_url
        if not self.api_url:
            raise ValueError("GITHUB_API_URL environment variable not set")
        
        import os
        logger.info(f"ENV[GITHUB_API_URL]: {os.getenv('GITHUB_API_URL')}")
        logger.info(f"ENV[GH_API_TOKEN]: {os.getenv('GH_API_TOKEN')}")
        
        self.token: str = settings.api.github_token
        if not self.token:
            raise ValueError("GH_API_TOKEN environment variable not set")

    def build_graphql_query(self, parsed_items: List[Dict[str, str]]) -> str:
        """
        Construct a batched GraphQL query for multiple GitHub items.

        This method creates a single GraphQL query that can fetch multiple
        GitHub resources at once using aliases. Each item gets a unique alias
        (item0, item1, etc.) and the appropriate GraphQL fragment based on
        whether it's a PR or commit.

        Args:
            parsed_items: List of dictionaries with GitHub item metadata.
                         Each dict should have: type, owner, repo, id

        Returns:
            Complete GraphQL query string ready for execution

        The query structure handles two types of GitHub resources:
        1. Pull Requests: Fetches PR metadata (title, body, author, labels)
        2. Commits: Fetches commit metadata (message, author, date)

        Example query result for mixed items:
        ```
        query {
          item0: repository(owner: "org", name: "repo") {
            pullRequest(number: 123) { title body ... }
          }
          item1: repository(owner: "org", name: "repo") {
            object(expression: "abc123") { ... on Commit { message ... } }
          }
        }
        ```
        """
        query_parts = []
        for i, item in enumerate(parsed_items):
            alias = f"item{i}"
            if item["type"] == "pr":
                # GraphQL fragment for Pull Request data
                query_parts.append(
                    f"""
                    {alias}: repository(owner: "{item['owner']}", name: "{item['repo']}") {{
                        pullRequest(number: {item['id']}) {{
                            number
                            title
                            body
                            author {{ login }}
                            labels(first: 10) {{
                                nodes {{ name }}
                            }}
                        }}
                    }}
                    """
                )
            elif item["type"] == "commit":
                # GraphQL fragment for commit data
                query_parts.append(
                    f"""
                    {alias}: repository(owner: "{item['owner']}", name: "{item['repo']}") {{
                        object(expression: "{item['id']}") {{
                            ... on Commit {{
                                oid
                                message
                                author {{ name email }}
                                committedDate
                            }}
                        }}
                    }}
                    """
                )
        return f"query {{ {''.join(query_parts)} }}"

    def post_query(self, query: str) -> Dict[str, Any]:
        """
        Execute a GraphQL query against the GitHub API.

        This method handles the HTTP communication with GitHub's GraphQL API,
        including authentication, error handling, and response validation.

        Args:
            query: GraphQL query string to execute

        Returns:
            Parsed JSON response containing the requested data

        Raises:
            ValueError: If the GraphQL response contains errors
            requests.RequestException: If the HTTP request fails

        The method includes comprehensive error handling for:
        - HTTP errors (network issues, authentication failures)
        - GraphQL errors (invalid queries, permission issues)
        - Rate limiting and API quota issues
        """
        # Set up authentication headers for GitHub API access
        headers = {"Authorization": f"Bearer {self.token}"}

        try:
            # Execute the GraphQL query via HTTP POST
            response: requests.Response = requests.post(
                self.api_url, json={"query": query}, headers=headers
            )
            # Raise exception for HTTP error status codes
            response.raise_for_status()

            # Parse JSON response
            data = response.json()

            # Check for GraphQL-specific errors in the response
            if "errors" in data:
                error_msg = f"GraphQL Errors: {data['errors']}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            return data

        except requests.RequestException as e:
            error_msg = f"[!][ERROR] Request failed: {e}"
            logger.error(error_msg)
            raise requests.RequestException(error_msg)
