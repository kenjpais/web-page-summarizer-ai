import re
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
        pr_match = self.PR_REGEX.match(url)
        if pr_match:
            owner, repo, pr_id = pr_match.groups()
            return {"type": "pr", "owner": owner, "repo": repo, "id": pr_id}

        commit_match = self.COMMIT_REGEX.match(url)
        if commit_match:
            owner, repo, sha = commit_match.groups()
            return {"type": "commit", "owner": owner, "repo": repo, "id": sha}

        return None

    def extract(self, urls):
        """Parses multiple GitHub URLs and fetches their details using GraphQL."""
        parsed_items = []
        for url in urls:
            parsed = self.parse_github_url(url)
            if parsed:
                parsed_items.append(parsed)

        if not parsed_items:
            raise_scraper_exception("[!] No valid GitHub items to process.")

        try:
            gql_query = self.client.build_graphql_query(parsed_items)
            result = self.client.run_query(gql_query)
        except Exception as e:
            raise_scraper_exception(f"[!] Error fetching GitHub data: {e}")

        data = result.get("data", {})
        results = []

        for i in range(len(parsed_items)):
            item = data.get(f"item{i}")
            if not item:
                print(f"[!] Missing item{i} in GraphQL response.")
                continue

            if "pullRequest" in item:
                pr = item["pullRequest"]
                results.append(
                    GithubModel(
                        id=pr.get("number"),
                        title=pr.get("title"),
                        body=pr.get("body"),
                    ).to_dict()
                )
            elif "object" in item:
                obj = item["object"]
                if not obj:
                    continue
                results.append(
                    GithubModel(
                        id=obj.get("oid"),
                        message=obj.get("message"),
                    ).to_dict()
                )

        return results
