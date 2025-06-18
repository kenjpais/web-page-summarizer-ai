import unittest
from scrapers.github_scraper import GithubScraper
from scrapers.exceptions import ScraperException
from utils.logging_config import setup_logging

setup_logging()


class TestGithubFilter(unittest.TestCase):

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
        result = self.gf.extract(urls)

        self.assertIsInstance(result, list)
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
        result = self.gf.extract(urls)
        print(f"KDEBUG: {result}")
        self.assertEqual(len(result), 2)
        for item in result:
            self.assertIn("id", item)


if __name__ == "__main__":
    unittest.main()
