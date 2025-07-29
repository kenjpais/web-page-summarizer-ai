import re
import json
import unittest
from urllib.parse import urlparse
from pathlib import Path
from scrapers.html_scraper import scrape_html
from filters.filter_urls import filter_urls
from scrapers.github_scraper import GithubScraper
from scrapers.exceptions import ScraperException
from utils.utils import get_urls
from config.settings import get_settings
from utils.logging_config import setup_logging

setup_logging()
settings = get_settings()
data_dir = settings.directories.data_dir
github_file_path = data_dir / "github.json"


class TestGithubScraper(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.gf = GithubScraper()

    def test_parse_github_url_pr(self):
        url = "https://github.com/octocat/Hello-World/pull/1347"
        expected = {
            "type": "pr",
            "owner": "octocat",
            "repo": "Hello-World",
            "id": "1347",
        }
        self.assertEqual(self.gf.parse_github_url(url), expected)

    def test_parse_github_url_commit(self):
        url = "https://github.com/octocat/Hello-World/commit/7fd1a60b01f91b314f59951d5e0c6b2b2fefaa99"
        expected = {
            "type": "commit",
            "owner": "octocat",
            "repo": "Hello-World",
            "id": "7fd1a60b01f91b314f59951d5e0c6b2b2fefaa99",
        }
        self.assertEqual(self.gf.parse_github_url(url), expected)

    def test_parse_github_url_invalid(self):
        invalid_urls = [
            "https://example.com/invalid-url",
            "https://github.com/octocat/Hello-World/issues/1347",
            "https://github.com/octocat/Hello-World/blame/main/file.txt",
        ]
        for url in invalid_urls:
            self.assertIsNone(self.gf.parse_github_url(url), msg=f"Failed on: {url}")

    def test_extract_relevant_info_from_urls_valid(self):
        urls = ["https://github.com/octocat/Hello-World/pull/1"]
        self.gf.extract(urls)
        result = load_github_file()
        self.assertGreater(len(result), 0)
        self.assertIn("id", result[0])

    def test_extract_relevant_info_from_urls_all_invalid(self):
        urls = [
            "https://example.com/this/is/invalid",
            "https://github.com/octocat/Hello-World/tree/main",
        ]
        with self.assertRaises(ScraperException) as cm:
            self.gf.extract(urls)
            self.assertIn("Unsupported or invalid GitHub URL", str(cm.exception))

    def test_multiple_valid_urls(self):
        urls = [
            "https://github.com/openshift/vmware-vsphere-csi-driver-operator/pull/276",
            "https://github.com/openshift/cloud-provider-kubevirt/commit/3f4542ecd17fb0e47da4c6d9bceb076b98fb314b",
        ]
        self.gf.extract(urls)

        result = load_github_file()

        self.assertEqual(len(result), 2)
        for item in result:
            self.assertIn("id", item)

    def test_end_2_end(self):
        url = "https://amd64.origin.releases.ci.openshift.org/releasestream/4-scos-stable/release/4.19.0-okd-scos.0"

        # Run the pipeline
        scrape_html(url)
        filter_urls()

        src = "github"
        urls = get_urls(src)
        if not urls:
            self.fail(f"[!] No URLs found for {src}.")

        expected_ids = sorted(id for url in urls if (id := extract_github_id(url)))

        self.gf.extract(urls)

        result = load_github_file()

        for item in result:
            self.assertIn("id", item)

        result_ids = sorted([item["id"] for item in result])
        self.assertEqual(len(result_ids), len(expected_ids))
        self.assertListEqual(expected_ids, result_ids)


def load_github_file():
    with open(github_file_path, "r") as f:
        return json.load(f)


def extract_github_id(url: str) -> str | None:
    """
    Extract the pull request number or commit SHA from a GitHub URL.

    Returns:
        - Pull request number as string (e.g., "123")
        - Commit SHA as string (e.g., "abcd1234...")
        - None if no ID found
    """
    parsed = urlparse(url)
    path = parsed.path

    pr_match = re.search(r"/pull/(\d+)", path)
    if pr_match:
        return pr_match.group(1)

    commit_match = re.search(r"/commit/([a-fA-F0-9]+)", path)
    if commit_match:
        return commit_match.group(1)


if __name__ == "__main__":
    unittest.main()
