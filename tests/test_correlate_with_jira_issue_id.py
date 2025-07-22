import os
import json
import unittest
from pathlib import Path

from utils.file_utils import delete_all_in_directory
from scrapers.scrapers import scrape_all
from scrapers.html_scraper import scrape_html
from scrapers.jira_scraper import JiraScraper
from filters.filter_urls import filter_urls
from correlators.correlator import correlate_with_jira_issue_id
from config.settings import get_settings
from utils.logging_config import get_logger, setup_logging

setup_logging()

logger = get_logger(__name__)

settings = get_settings()


class TestCorrelateWithJiraIssueId(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data_dir = Path(settings.directories.data_dir)
        cls.config_dir = Path(settings.directories.data_dir)
        cls.jira_file = cls.data_dir / "jira.json"
        cls.github_file = cls.data_dir / "github.json"
        cls.correlated_file = cls.data_dir / "correlated.json"
        cls.correlated_table_file = cls.data_dir / "correlated_table_file.json"
        cls.required_github_fields_file = (
            settings.config_files.required_github_fields_file
        )

        os.environ["FILTER_ON"] = "False"

        url = "https://amd64.origin.releases.ci.openshift.org/releasestream/4-scos-stable/release/4.19.0-okd-scos.0"

        with open(cls.required_github_fields_file, "w") as f:
            json.dump(["title", "body"], f)

        cls.jira_scraper = JiraScraper()

        def run_pipeline():
            delete_all_in_directory(cls.data_dir)
            scrape_html(url)
            filter_urls()
            scrape_all()
            correlate_with_jira_issue_id()

        run_pipeline()

    def test_correlate_with_jira_issue_id(self):
        sources = settings.processing.sources

        with open(self.correlated_file) as f:
            result = json.load(f)

        for _, project in result.items():
            for _, issue_dict in project.items():
                if isinstance(issue_dict, dict):
                    for issue_id, issue in issue_dict.items():
                        for src in sources:
                            src_matched_issues = issue.get(src, [])
                            for src_matched_issue in src_matched_issues:
                                if title := src_matched_issue.get("title", ""):
                                    self.assertIn(
                                        issue_id,
                                        title,
                                        msg=f"Issue ID [{issue_id}] not in title: '{title}'",
                                    )
