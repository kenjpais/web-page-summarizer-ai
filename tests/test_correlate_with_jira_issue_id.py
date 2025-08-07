import os
import json
import unittest

os.environ["LLM_PROVIDER"] = "local"
os.environ["LLM_MODEL"] = "mistral"
from correlators.correlator import Correlator
from config.settings import get_settings
from utils.logging_config import get_logger, setup_logging
from utils.file_utils import copy_file

setup_logging()

logger = get_logger(__name__)

settings = get_settings()

test_data_dir = settings.directories.test_data_dir


class TestCorrelateWithJiraIssueId(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["FILTER_ON"] = "False"

        # Ensure data directory exists
        settings.directories.data_dir.mkdir(parents=True, exist_ok=True)

        # Copy required files from test mocks to data directory
        required_files = [
            "jira.json",
            "github.json",
            "correlated.json",
            "non_correlated.json",
        ]
        for file in required_files:
            mock_file = test_data_dir / file
            if mock_file.exists():
                copy_file(src_path=mock_file, dest_dir=settings.directories.data_dir)

        cls.correlated_file = test_data_dir / "correlated.json"

        with open(settings.config_files.required_github_fields_file, "w") as f:
            json.dump(["title", "body"], f)

        correlator = Correlator(settings)
        correlator.correlate_with_jira_issue_id()

    def test_correlate_with_jira_issue_id(self):
        sources = settings.api.sources

        with open(self.correlated_file) as f:
            result = json.load(f)

        for _, project in result.items():
            for _, issue_dict in project.items():
                if isinstance(issue_dict, dict):
                    for issue_id, issue in issue_dict.items():
                        for src in sources:
                            if isinstance(issue, dict):
                                src_matched_issues = issue.get(src, [])
                                for src_matched_issue in src_matched_issues:
                                    if title := src_matched_issue.get("title", ""):
                                        self.assertIn(
                                            issue_id,
                                            title,
                                            msg=f"Issue ID [{issue_id}] not in title: '{title}'",
                                        )
