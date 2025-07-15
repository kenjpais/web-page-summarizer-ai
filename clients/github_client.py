import requests
from typing import List, Dict, Any
from config.settings import get_settings
from utils.logging_config import get_logger

logger = get_logger(__name__)

settings = get_settings()


class GithubGraphQLClient:
    def __init__(self) -> None:
        self.api_url: str = settings.api.github_api_url
        if not self.api_url:
            raise ValueError("GITHUB_API_URL environment variable not set")
        self.token: str = settings.api.github_token
        if not self.token:
            raise ValueError("GH_API_TOKEN environment variable not set")

    def build_graphql_query(self, parsed_items: List[Dict[str, str]]) -> str:
        """Constructs a single GraphQL query with aliases for PRs and commits."""
        query_parts = []
        for i, item in enumerate(parsed_items):
            alias = f"item{i}"
            if item["type"] == "pr":
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
        """Makes POST request with GraphQL query."""
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            response: requests.Response = requests.post(
                self.api_url, json={"query": query}, headers=headers
            )
            response.raise_for_status()
            data = response.json()
            if "errors" in data:
                error_msg = f"GraphQL Errors: {data['errors']}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            return data
        except requests.RequestException as e:
            error_msg = f"[!][ERROR] Request failed: {e}"
            logger.error(error_msg)
            raise requests.RequestException(error_msg)
