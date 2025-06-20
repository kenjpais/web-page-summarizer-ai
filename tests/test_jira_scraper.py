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
            "https://issues.redhat.com/browse/ART-13079",  # Should be excluded
            "https://issues.redhat.com/browse/CONSOLE-3905",
            "https://issues.redhat.com/browse/NETOBSERV-2023",
            "https://issues.redhat.com/browse/STOR-2251",
            "https://issues.redhat.com/browse/OCPBUILD-174",
            "https://issues.redhat.com/browse/IR-522",
            "https://issues.redhat.com/browse/ETCD-726",
        ]

        expected_categories = {
            "IR": ["IR-522"],
            "ETCD": ["ETCD-726"],
        }

        allowed_issuetypes = {"Epic", "Story"}
        disallowed_ids = {"ART"}

        result_ = {}
        result = self.jf.extract(urls)
        
        self.assertGreater(len(result), 0)
        for category, issue_objs in result.items():
            self.assertIsNotNone(category)
            if category in disallowed_ids:
                continue
            if category not in result_:
                result_[category] = []
            result_[category].extend([issue_obj["id"] for issue_obj in issue_objs])

            for issue_obj in issue_objs:
                self.assertIn("id", issue_obj)
                self.assertIn("summary", issue_obj)
                self.assertIn("description", issue_obj)
                self.assertIn("parent", issue_obj)
                self.assertIn("issuelinks", issue_obj)
                self.assertIn(issue_obj["issuetype"], allowed_issuetypes)
                self.assertFalse(
                    issue_obj["id"].startswith("ART"),
                    f"{issue_obj['id']} is disallowed",
                )

        self.assertIsInstance(result_, dict)
        self.assertGreater(len(result_), 0)
        self.assertDictEqual(expected_categories, result_)


if __name__ == "__main__":
    unittest.main()
