import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from clients.github_client import GithubGraphQLClient
from models.github_model import GithubModel
from scrapers.exceptions import raise_scraper_exception
from config.settings import get_settings
from utils.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()

data_dir = Path(settings.directories.data_dir)
BATCH_SCRAPE_SIZE = settings.processing.github_batch_size


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

    def __init__(self, batch_size: int = BATCH_SCRAPE_SIZE) -> None:
        """
        Initialize GitHub scraper with GraphQL client and batching configuration.

        Args:
            batch_size: Number of items to include in each GraphQL batch request.
                       Larger batches are more efficient but may hit query complexity limits.
        """
        import os
        logger.info("BEFORE INIT GITHUBCLIENT ENV[GITHUB_API_URL] =", os.getenv("GITHUB_API_URL"))
        self.client: GithubGraphQLClient = GithubGraphQLClient()
        self.batch_size: int = batch_size

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

    def extract(self, urls: List[str]) -> None:
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

            # Type assertion: data is guaranteed to be not None after the check above
            assert data is not None

            # Process each item in the batch response
            for i, parsed in enumerate(batch):
                item_content = data.get(f"item{i}")

                if not item_content:
                    raise_scraper_exception(
                        f"[!][ERROR] Missing item{i} content in GraphQL response for {parsed}"
                    )

                # Extract data based on item type
                if pr := item_content.get("pullRequest"):
                    # Pull Request data extraction
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

        # Write all results to file for downstream processing
        write_json_file(results)


def write_json_file(results: List[Dict[str, Any]]) -> None:
    """
    Write GitHub extraction results to JSON file.

    Creates a structured JSON file that can be consumed by the correlation
    and summarization steps in the pipeline.

    Args:
        results: List of dictionaries containing GitHub data
    """
    with open(data_dir / "github.json", "w") as f:
        json.dump(results, f, indent=2)
