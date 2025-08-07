import re
import json
from typing import List, Dict, Any, Optional
from clients.github_client import GithubGraphQLClient
from models.github_model import GithubModel
from scrapers.exceptions import raise_scraper_exception
from config.settings import AppSettings, get_config_loader
from utils.logging_config import get_logger

logger = get_logger(__name__)


class GithubScraper:
    """
    GitHub scraper that extracts PR and commit information using GraphQL batching.

    Key Features:
    - URL parsing for both PRs and commits
    - Batched GraphQL queries for efficient API usage
    - Error handling for rate limits and API failures
    - Structured data extraction and normalization

    The scraper is designed to handle GitHub's API rate limits by batching
    multiple requests into single GraphQL queries, significantly reducing
    the number of API calls needed.
    """

    # Regex patterns for parsing GitHub URLs
    # These handle the standard GitHub URL patterns for PRs and commits
    PR_REGEX = re.compile(r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)")
    COMMIT_REGEX = re.compile(
        r"https://github\.com/([^/]+)/([^/]+)/commit/([a-fA-F0-9]+)"
    )

    def __init__(
        self,
        settings: AppSettings,
        urls: List[str] = [],
        batch_size: int = 300,
        github_server: str = None,
        github_username: str = None,
        github_password: str = None,
        github_token: str = None,
    ) -> None:
        """
        Initialize GitHub scraper with GraphQL client and batching configuration.

        Args:
            batch_size: Number of items to include in each GraphQL batch request.
                       Larger batches are more efficient but may hit query complexity limits.
        """

        self.settings = settings
        self.urls = urls or []
        self.batch_size = batch_size or self.settings.api.github_batch_size
        self.github_server = github_server
        self.github_username = github_username
        self.github_password = github_password
        self.github_token = github_token
        self.config_loader = get_config_loader()

        self.client: GithubGraphQLClient = GithubGraphQLClient(
            github_graphql_api_url=self.settings.api.github_graphql_api_url,
            github_server=self.github_server or self.settings.api.github_server,
            github_token=self.github_token or self.settings.api.github_token,
            github_username=self.github_username or "",
            github_password=self.github_password or "",
            github_timeout=self.settings.api.github_timeout,
        )

    def get_config(self) -> dict[str, Any]:
        """
        Get the configuration for the GitHub scraper.
        """
        return {
            "github_server": self.client.get_config(),
        }

    def parse_github_url(self, url: str) -> Optional[Dict[str, str]]:
        """
        Parse a GitHub URL to extract repository and item information.

        Supports two URL types:
        1. Pull Requests: https://github.com/owner/repo/pull/123
        2. Commits: https://github.com/owner/repo/commit/abc123...

        Args:
            url: GitHub URL to parse

        Returns:
            Dictionary with parsed components (type, owner, repo, id) or None if invalid

        Example:
            parse_github_url("https://github.com/openshift/console/pull/123")
            Returns: {"type": "pr", "owner": "openshift", "repo": "console", "id": "123"}
        """
        if match := self.PR_REGEX.match(url):
            owner, repo, pr_id = match.groups()
            return {"type": "pr", "owner": owner, "repo": repo, "id": pr_id}
        if match := self.COMMIT_REGEX.match(url):
            owner, repo, sha = match.groups()
            return {"type": "commit", "owner": owner, "repo": repo, "id": sha}
        return None

    def extract(self) -> None:
        """
        Extract GitHub data from multiple URLs using batched GraphQL queries.

        Process:
        1. Parse all URLs to identify valid GitHub resources
        2. Group parsed items into batches for efficient API usage
        3. Execute GraphQL queries for each batch
        4. Transform responses into standardized format
        5. Write results to JSON file for downstream processing

        The batching strategy is critical for performance - instead of making
        N individual API calls, this makes N/batch_size calls, significantly
        reducing API usage and improving speed.

        Args:
            urls: List of GitHub URLs to process

        Raises:
            ScraperException: If no valid URLs found or API errors occur
        """
        results = []

        urls = self.urls
        if not urls:
            raise_scraper_exception(f"""[!][ERROR] No GITHUB URLs provided.""")

        # Parse and validate all URLs first
        parsed_items = [
            parsed for url in urls if (parsed := self.parse_github_url(url))
        ]

        if not parsed_items:
            raise_scraper_exception(
                f"""[!][ERROR] Unsupported or invalid GitHub URL. 
                No valid GitHub PR/commit URLs found in {len(urls)} URLs.
                GitHub scraper only supports PR and commit URLs (e.g., /pull/123 or /commit/abc123)"""
            )

        # Process items in batches to optimize API usage
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

        with open(self.settings.file_paths.github_json_file_path, "w") as f:
            json.dump(results, f, indent=2)
