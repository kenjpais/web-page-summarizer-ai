import requests
from utils.utils import get_env


class GithubGraphQLClient:
    def __init__(self):
        self.api_url = get_env("GITHUB_API_URL")
        self.token = get_env("GH_API_TOKEN")

    def build_graphql_query(self, parsed_items):
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

    def post_query(self, query):
        """Makes POST request with GraphQL query."""
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            response = requests.post(
                self.api_url, json={"query": query}, headers=headers
            )
            response.raise_for_status()
            data = response.json()
            if "errors" in data:
                print(f"GraphQL Errors: {data['errors']}")
            return data
        except requests.RequestException as e:
            print(f"[!] Request failed: {e}")
            return None
