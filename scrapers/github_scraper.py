import re
import json
from utils.utils import get_env
from clients.github_client import GithubGraphQLClient
from models.github_model import GithubModel
from scrapers.exceptions import raise_scraper_exception

BATCH_SCRAPE_SIZE = 300


class GithubScraper:
    PR_REGEX = re.compile(r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)")
    COMMIT_REGEX = re.compile(
        r"https://github\.com/([^/]+)/([^/]+)/commit/([a-fA-F0-9]+)"
    )

    def __init__(self, batch_size=BATCH_SCRAPE_SIZE):
        self.client = GithubGraphQLClient()
        self.batch_size = batch_size

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
        results = []
        parsed_items = [
            parsed for url in urls if (parsed := self.parse_github_url(url))
        ]
        if not parsed_items:
            raise_scraper_exception(
                f"""[!] Unsupported or invalid GitHub URL. 
                No valid GitHub PR/commit URLs found in {len(urls)} URLs.
                GitHub scraper only supports PR and commit URLs (e.g., /pull/123 or /commit/abc123)"""
            )

        for batch_start in range(0, len(parsed_items), self.batch_size):
            batch = parsed_items[batch_start : batch_start + self.batch_size]
            try:
                gql_query = self.client.build_graphql_query(batch)
                raw_response = self.client.post_query(gql_query)
            except Exception as e:
                raise_scraper_exception(f"[!] Error fetching GitHub data: {e}")

            if not raw_response:
                raise_scraper_exception(
                    f"[!] Empty response from GraphQL for batch starting at {batch_start}"
                )
                continue

            data = raw_response.get("data")
            if not data:
                error_msg = f"[!] No 'data' key found in GraphQL response for batch starting at {batch_start}. Raw response: {raw_response}"
                if "errors" in raw_response:
                    error_msg += f" GraphQL Errors: {raw_response['errors']}"
                raise_scraper_exception(error_msg)
                continue

            for i, parsed in enumerate(batch):
                item_content = data.get(f"item{i}")

                if not item_content:
                    raise_scraper_exception(
                        f"[!] Missing item{i} content in GraphQL response for {parsed}"
                    )
                    continue

                if pr := item_content.get("pullRequest"):
                    results.append(
                        GithubModel(
                            id=str(pr.get("number")),
                            type="pullRequest",
                            title=pr.get("title"),
                            body=pr.get("body"),
                        ).to_dict()
                    )

                elif obj := item_content.get("object"):
                    results.append(
                        GithubModel(
                            id=obj.get("oid"),
                            type="commit",
                            message=obj.get("message"),
                        ).to_dict()
                    )
        write_json_file(results)


def write_json_file(data):
    if data_dir := get_env("DATA_DIR"):
        with open(f"{data_dir}/github.json", "w") as f:
            json.dump(data, f, indent=2)
