import re
import json
from utils.utils import get_env
from clients.github_client import GithubGraphQLClient
from models.github_model import GithubModel
from scrapers.exceptions import raise_scraper_exception


class GithubScraper:
    PR_REGEX = re.compile(r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)")
    COMMIT_REGEX = re.compile(
        r"https://github\.com/([^/]+)/([^/]+)/commit/([a-fA-F0-9]+)"
    )

    def __init__(self):
        self.client = GithubGraphQLClient()

    def parse_github_url(self, url):
        """Parses a single GitHub PR or commit URL into a structured dict."""
        if match := self.PR_REGEX.match(url):
            owner, repo, pr_id = match.groups()
            return {"type": "pr", "owner": owner, "repo": repo, "id": pr_id}
        if match := self.COMMIT_REGEX.match(url):
            owner, repo, sha = match.groups()
            return {"type": "commit", "owner": owner, "repo": repo, "id": sha}
        return None

    def extract(self, urls):
        """Parses multiple GitHub URLs and fetches their details using GraphQL."""
        parsed_items = [
            parsed for url in urls if (parsed := self.parse_github_url(url))
        ]
        if not parsed_items:
            raise_scraper_exception("[!] No valid GitHub items to process.")

        try:
            gql_query = self.client.build_graphql_query(parsed_items)
            response = self.client.post_query(gql_query)
        except Exception as e:
            raise_scraper_exception(f"[!] Error fetching GitHub data: {e}")

        data = response.get("data", {})
        results = []

        for i, parsed in enumerate(parsed_items):
            item_data = data.get(f"item{i}")
            if not item_data:
                print(f"[!] Missing item{i} in GraphQL response.")
                continue

            if pr := item_data.get("pullRequest"):
                results.append(
                    GithubModel(
                        id=pr.get("number"),
                        type="pullRequest",
                        title=pr.get("title"),
                        body=pr.get("body"),
                    ).to_dict()
                )

            elif obj := item_data.get("object"):
                results.append(
                    GithubModel(
                        id=obj.get("oid"), type="commit", message=obj.get("message")
                    ).to_dict()
                )

        write_json_file(results)


def write_json_file(data):
    if data_dir := get_env("DATA_DIR"):
        with open(f"{data_dir}/github.json", "w") as f:
            json.dump(data, f)
