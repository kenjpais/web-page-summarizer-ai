import unittest
from pathlib import Path
from controllers.summarize_url_controller import summarize_release_page_from_url
from config.settings import get_settings

settings = get_settings()

data_dir = Path(settings.directories.data_dir)


class TestSummarizeUrlController(unittest.TestCase):
    def setUp(self):
        self.url = "https://amd64.origin.releases.ci.openshift.org/releasestream/4-scos-stable/release/4.19.0-okd-scos.0"
        self.release_name = self.url.strip().split("/release/")[1]
        self.summary_dir = data_dir / "summaries" / self.release_name
        self.summary_file_path = self.summary_dir / "summary.txt"

    def test_summarize_release_page_from_url(self):
        summarize_release_page_from_url(self.url)
        self.assertTrue(
            self.summary_file_path.exists(),
            "summary.txt was not copied to the expected location",
        )

        with open(self.summary_file_path, "r") as f:
            summary_content = f.read()

        self.assertTrue(f"Release Notes {self.release_name}" in summary_content)
        self.assertGreater(len(summary_content.strip()), 0, "summary.txt is empty")
