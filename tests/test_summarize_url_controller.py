import os
import unittest
import shutil
from utils.utils import get_env
from controllers.summarize_url_controller import summarize_release_page_from_url


class TestSummarizeUrlController(unittest.TestCase):
    def setUp(self):
        self.data_dir = get_env("DATA_DIR")
        self.url = "https://amd64.origin.releases.ci.openshift.org/releasestream/4-scos-next/release/4.20.0-okd-scos.ec.3"
        self.release_name = self.url.strip().split("/release/")[1]
        self.summary_dir = os.path.join(self.data_dir, "summaries", self.release_name)
        self.summary_file_path = os.path.join(self.summary_dir, "summary.txt")

        # Clean up any existing directory from previous runs
        if os.path.exists(self.summary_dir):
            shutil.rmtree(self.summary_dir)

        summary_txt_in_root = os.path.join(self.data_dir, "summary.txt")
        if os.path.exists(summary_txt_in_root):
            os.remove(summary_txt_in_root)

    def test_summarize_release_page_from_url(self):
        summarize_release_page_from_url(self.url)
        self.assertTrue(
            os.path.exists(self.summary_file_path),
            "summary.txt was not copied to the expected location",
        )

        with open(self.summary_file_path, "r") as f:
            summary_content = f.read()

        self.assertGreater(len(summary_content.strip()), 0, "summary.txt is empty")

    """
    def tearDown(self):
        if os.path.exists(self.summary_dir):
            shutil.rmtree(self.summary_dir)

        summary_txt_in_root = os.path.join(self.data_dir, "summary.txt")
        if os.path.exists(summary_txt_in_root):
            os.remove(summary_txt_in_root)
    """
