import os
import json
import unittest
from correlators.correlator import correlate_with_jira_issue_id
from config.settings import get_settings
from utils.logging_config import get_logger, setup_logging

setup_logging()

logger = get_logger(__name__)

settings = get_settings()
data_dir = settings.directories.data_dir
test_data_dir = settings.directories.test_data_dir


class TestCorrelateWithJiraIssueId(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["FILTER_ON"] = "False"

        cls.correlated_file = data_dir / "correlated.json"

        with open(settings.config_files.required_github_fields_file, "w") as f:
            json.dump(["title", "body"], f)

        def run_pipeline():
            correlate_with_jira_issue_id(data_directory=test_data_dir)

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
