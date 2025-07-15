import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from clients.github_client import GithubGraphQLClient
from models.github_model import GithubModel
from scrapers.exceptions import raise_scraper_exception
from config.settings import get_settings

settings = get_settings()

data_dir = Path(settings.directories.data_dir)
BATCH_SCRAPE_SIZE = settings.processing.github_batch_size


class GithubScraper:
    PR_REGEX = re.compile(r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)")
    COMMIT_REGEX = re.compile(
        r"https://github\.com/([^/]+)/([^/]+)/commit/([a-fA-F0-9]+)"
    )

    def __init__(self, batch_size: int = BATCH_SCRAPE_SIZE) -> None:
        self.client: GithubGraphQLClient = GithubGraphQLClient()
        self.batch_size: int = batch_size

    def parse_github_url(self, url: str) -> Optional[Dict[str, str]]:
        """Parses a single GitHub PR or commit URL into a structured dict."""
        if match := self.PR_REGEX.match(url):
            owner, repo, pr_id = match.groups()
            return {"type": "pr", "owner": owner, "repo": repo, "id": pr_id}
        if match := self.COMMIT_REGEX.match(url):
            owner, repo, sha = match.groups()
            return {"type": "commit", "owner": owner, "repo": repo, "id": sha}
        return None

    def extract(self, urls: List[str]) -> None:
        """Parses multiple GitHub URLs and fetches their details using GraphQL."""
        results = []
        parsed_items = [
            parsed for url in urls if (parsed := self.parse_github_url(url))
        ]
        if not parsed_items:
            raise_scraper_exception(
                f"""[!][ERROR] Unsupported or invalid GitHub URL. 
                No valid GitHub PR/commit URLs found in {len(urls)} URLs.
                GitHub scraper only supports PR and commit URLs (e.g., /pull/123 or /commit/abc123)"""
            )

        for batch_start in range(0, len(parsed_items), self.batch_size):
            batch = parsed_items[batch_start : batch_start + self.batch_size]
            try:
                gql_query = self.client.build_graphql_query(batch)
                raw_response = self.client.post_query(gql_query)
            except Exception as e:
                raise_scraper_exception(f"[!][ERROR] Fetching GitHub data failed: {e}")

            if not raw_response:
                raise_scraper_exception(
                    f"[!][ERROR] Empty response from GraphQL for batch starting at {batch_start}"
                )

            data = raw_response.get("data")
            if not data:
                error_msg = f"[!][ERROR] No 'data' key found in GraphQL response for batch starting at {batch_start}. Raw response: {raw_response}"
                if "errors" in raw_response:
                    error_msg += f" GraphQL Errors: {raw_response['errors']}"
                raise_scraper_exception(error_msg)

            # Type assertion: data is guaranteed to be not None after the check above
            assert data is not None

            for i, parsed in enumerate(batch):
                item_content = data.get(f"item{i}")

                if not item_content:
                    raise_scraper_exception(
                        f"[!][ERROR] Missing item{i} content in GraphQL response for {parsed}"
                    )

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


def write_json_file(results: List[Dict[str, Any]]) -> None:
    with open(data_dir / "github.json", "w") as f:
        json.dump(results, f, indent=2)
