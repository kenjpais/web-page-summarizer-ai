import os
import json
import unittest
import pandas as pd
from typing import Dict
from pathlib import Path
from utils.file_utils import delete_all_in_directory
from scrapers.jira_scraper import JiraScraper, render_to_markdown
from scrapers.html_scraper import HtmlScraper
from scrapers.exceptions import ScraperException
from filters.filter_enabled_feature_gates import filter_enabled_feature_gates
from config.settings import get_settings
from utils.logging_config import setup_logging

# Set up logging for tests
setup_logging()

settings = get_settings()
data_dir = Path(settings.directories.data_dir)

urls = [
    "https://issues.redhat.com/browse/ODC-7710",
    "https://issues.redhat.com/browse/TRT-2188",
    "https://issues.redhat.com/browse/CONSOLE-3905",
    "https://issues.redhat.com/browse/NETOBSERV-2023",
    "https://issues.redhat.com/browse/STOR-2251",
    "https://issues.redhat.com/browse/OCPBUILD-174",
    "https://issues.redhat.com/browse/IR-522",
    "https://issues.redhat.com/browse/ETCD-726",
    "https://issues.redhat.com/browse/NE-2017",
    "https://issues.redhat.com/browse/TRT-2005",
    "https://issues.redhat.com/browse/OTA-923",
]


expected_ids = {
    "STOR-2251",
    "ODC-7710",
    "NETOBSERV-2023",
    "IR-522",
    "ETCD-726",
    "CONSOLE-3905",
}


class TestJiraScraper(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jf = JiraScraper(filter_on=False)
        delete_all_in_directory(data_dir)

    def load_jira_files(self):
        with open(data_dir / "jira.json") as f:
            result = json.load(f)

        with open(data_dir / "jira.md") as f:
            result_md = f.read()

        return result, result_md

    def test_extract_urls_invalid(self):
        urls = [
            "https://example.com/this/is/invalid",
            "https://example.com/invalid/this/is",
        ]
        with self.assertRaises(ScraperException) as cm:
            self.jf.extract(urls)
        self.assertIn("Invalid JIRA URLs", str(cm.exception))

    def assert_hierarchy_valid(self, result: Dict):
        issue_types = ("epics", "stories", "features", "bugs")
        items = ("summary", "description")

        self.assertGreater(len(result), 0, "Result JSON is empty or missing projects")

        for project_name, project in result.items():
            has_issue_type = any(key in project for key in issue_types)
            if not has_issue_type:
                self.fail(
                    f"Project '{project_name}' does not contain any of the expected issue types: {issue_types}. "
                    f"Found keys: {list(project.keys())}"
                )

            for issue_type in issue_types:
                if issue_type in project:
                    self.assertGreater(
                        len(project[issue_type]),
                        0,
                        f"{issue_type} in {project_name} is empty",
                    )
                    for issue_id, issue in project[issue_type].items():
                        self.assertTrue(
                            any(item in issue for item in items),
                            f"Issue {issue_id} is missing summary/description",
                        )
                        for item in items:
                            if item in issue:
                                self.assertGreater(
                                    len(issue[item]),
                                    0,
                                    f"Issue {issue_id} has empty {item}",
                                )

    def test_extract_urls_valid_filter_on(self):
        os.environ["FILTER_ON"] = "True"

        self.jf.extract(urls)

        result, result_md = self.load_jira_files()

        self.assert_hierarchy_valid(result)

        result_json_str = json.dumps(result)

        for issue_id in expected_ids:
            self.assertIn(issue_id, result_json_str)
            self.assertIn(issue_id, result_md)

    def test_extract_urls_valid_filter_off(self):
        os.environ["FILTER_ON"] = "False"

        self.jf.extract(urls)

        result, result_md = self.load_jira_files()

        self.assert_hierarchy_valid(result)

        result_json_str = json.dumps(result)

        expected_ids.remove("STOR-2251")
        for issue_id in expected_ids:
            self.assertIn(issue_id, result_json_str)
            self.assertIn(issue_id, result_md)

    def test_render_to_markdown_all_issue_types(self):
        """Test that render_to_markdown handles all issue types correctly"""
        # Create test hierarchy with all issue types
        test_hierarchy = {
            "Test Project": {
                "summary": "Test project summary",
                "description": "Test project description",
                "epics": {
                    "EPIC-1": {
                        "summary": "Test Epic Summary",
                        "description": "Test Epic Description",
                        "comments": ["Epic comment 1", "Epic comment 2"],
                    }
                },
                "stories": {
                    "STORY-1": {
                        "summary": "Test Story Summary",
                        "description": "Test Story Description",
                        "epic_key": "EPIC-1",
                    }
                },
                "bugs": {
                    "BUG-1": {
                        "summary": "Test Bug Summary",
                        "description": "Test Bug Description",
                    }
                },
                "features": {
                    "FEATURE-1": {
                        "summary": "Test Feature Summary",
                        "description": "Test Feature Description",
                    }
                },
                "enhancements": {
                    "ENHANCEMENT-1": {
                        "summary": "Test Enhancement Summary",
                        "description": "Test Enhancement Description",
                    }
                },
                "tasks": {
                    "TASK-1": {
                        "summary": "Test Task Summary",
                        "description": "Test Task Description",
                    }
                },
            }
        }

        # Generate markdown
        markdown = render_to_markdown(test_hierarchy)

        # Verify all issue types appear in markdown
        self.assertIn("## Epic: EPIC-1", markdown)
        self.assertIn("### Story: STORY-1", markdown)
        self.assertIn("### Bug: BUG-1", markdown)
        self.assertIn("### Feature: FEATURE-1", markdown)
        self.assertIn("### Enhancement: ENHANCEMENT-1", markdown)
        self.assertIn("### Task: TASK-1", markdown)

        # Verify all summaries appear
        self.assertIn("Test Epic Summary", markdown)
        self.assertIn("Test Story Summary", markdown)
        self.assertIn("Test Bug Summary", markdown)
        self.assertIn("Test Feature Summary", markdown)
        self.assertIn("Test Enhancement Summary", markdown)
        self.assertIn("Test Task Summary", markdown)

        # Verify epic link appears for story
        self.assertIn("**Linked Epic:** EPIC-1", markdown)

        # Verify comments appear for epic
        self.assertIn("Epic comment 1", markdown)
        self.assertIn("Epic comment 2", markdown)

    def _test_filter_issue_keys(self):
        irrelevant_jira_issue_keys = ["TRT-2005", "TRT-2188"]
        self.jf.filter_out["issuetype"]["id"] = irrelevant_jira_issue_keys

        self.jf.extract(urls)

        result, result_md = self.load_jira_files()
        self.assert_hierarchy_valid(result)

        result_json_str = json.dumps(result)

        for issue_id in expected_ids:
            self.assertIn(issue_id, result_json_str)
            self.assertIn(issue_id, result_md)

        for issue_id in irrelevant_jira_issue_keys:
            if self.jf.filter_on:
                self.assertNotIn(issue_id, result_json_str)
                self.assertNotIn(issue_id, result_md)
            else:
                self.assertIn(issue_id, result_json_str)
                self.assertIn(issue_id, result_md)

    def test_filter_issue_keys_on(self):
        self.jf.filter_on = True
        self._test_filter_issue_keys()

    def test_filter_issue_keys_off(self):
        self.jf.filter_on = False
        self._test_filter_issue_keys()

    def _test_filter_project_keys(self):
        irrelevant_project_keys = ["TRT"]
        self.jf.filter_out["project"]["key"] = irrelevant_project_keys

        self.jf.extract(urls)

        result, result_md = self.load_jira_files()
        self.assert_hierarchy_valid(result)

        result_json_str = json.dumps(result)

        for issue_id in expected_ids:
            self.assertIn(issue_id, result_json_str)
            self.assertIn(issue_id, result_md)

        for project_key in irrelevant_project_keys:
            if self.jf.filter_on:
                self.assertNotIn(f"{project_key}-", result_json_str)
                self.assertNotIn(f"{project_key}-", result_md)
            else:
                self.assertIn(f"{project_key}-", result_json_str)
                self.assertIn(f"{project_key}-", result_md)

    def test_filter_project_keys_on(self):
        self.jf = JiraScraper(filter_on=True)
        self._test_filter_project_keys()

    def test_filter_project_keys_off(self):
        self.jf = JiraScraper(filter_on=False)
        self._test_filter_project_keys()

    def test_search_unauthorized_issues_handling(self):
        unauthorized_keys = {"SDN-5772", "STOR-1880", "STOR-1881"}
        expected_keys = {
            "SPLAT-1800",
            "SPLAT-1809",
            "SPLAT-1742",
            "STOR-2285",
            "STOR-2263",
            "STOR-2249",
        }

        issue_ids = list(unauthorized_keys | expected_keys)

        issues = self.jf.search_issues(issue_ids)
        returned_keys = {issue.key for issue in issues}

        self.assertLess(
            len(issues),
            len(issue_ids),
            "Some issues should be missing due to unauthorized access",
        )
        self.assertTrue(
            unauthorized_keys.isdisjoint(returned_keys),
            "Unauthorized keys should not be present in the results",
        )
        self.assertTrue(
            expected_keys.issubset(returned_keys),
            "Expected accessible issues should be returned",
        )


if __name__ == "__main__":
    unittest.main()
