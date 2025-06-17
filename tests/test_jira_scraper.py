import unittest
from scrapers.jira_scraper import JiraScraper
from scrapers.exceptions import ScraperException


class TestJiraScraper(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jf = JiraScraper()

    def test_extract_urls_invalid(self):
        urls = [
            "https://example.com/this/is/invalid",
            "https://example.com/invalid/this/is",
        ]
        with self.assertRaises(ScraperException) as cm:
            self.jf.extract(urls)
        self.assertIn("[!] Invalid JIRA URLs", str(cm.exception))

    def test_extract_urls_valid(self):
        urls = [
            "https://issues.redhat.com/browse/ODC-7710",
            "https://issues.redhat.com/browse/CONSOLE-3905",
            "https://issues.redhat.com/browse/NETOBSERV-2023",
            "https://issues.redhat.com/browse/STOR-2251",
            "https://issues.redhat.com/browse/OCPBUILD-174",
            "https://issues.redhat.com/browse/IR-522",
            "https://issues.redhat.com/browse/ETCD-726",
        ]
        result = self.jf.extract(urls)
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        for val in result:
            self.assertIn("id", val)
            self.assertIn("description", val)
            self.assertIn("summary", val)


if __name__ == "__main__":
    unittest.main()
