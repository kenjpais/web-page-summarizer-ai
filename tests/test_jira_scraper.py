import json
import unittest
from typing import Dict
from scrapers.jira_scraper import JiraScraper, render_to_markdown
from scrapers.exceptions import ScraperException
from config.settings import get_settings
from utils.logging_config import setup_logging
from utils.file_utils import copy_file

# Set up logging for tests
setup_logging()

settings = get_settings()

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
        settings.directories.data_dir.mkdir(parents=True, exist_ok=True)
        # Mock data
        copy_file(
            src_path=settings.directories.test_data_dir / "issue_result_cache.pkl",
            dest_dir=settings.directories.data_dir,
        )
        copy_file(
            src_path=settings.directories.test_data_dir / "project_result_cache.pkl",
            dest_dir=settings.directories.data_dir,
        )

    def test_extract_urls_invalid(self):
        urls = [
            "https://example.com/this/is/invalid",
            "https://example.com/invalid/this/is",
        ]
        jf = JiraScraper(settings=settings, urls=urls)
        with self.assertRaises(ScraperException) as cm:
            jf.extract()
        self.assertIn("Invalid JIRA issue IDs", str(cm.exception))

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
        jf = JiraScraper(settings=settings, urls=urls, filter_on=True)
        jf.extract()

        result, result_md = load_jira_files()

        self.assert_hierarchy_valid(result)

        result_json_str = json.dumps(result)

        for issue_id in expected_ids:
            self.assertIn(issue_id, result_json_str)
            self.assertIn(issue_id, result_md)

    def test_extract_urls_valid_filter_off(self):
        jf = JiraScraper(settings=settings, urls=urls, filter_on=False)
        jf.extract()

        result, result_md = load_jira_files()

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

    def _test_filter_issue_keys(self, jf):
        irrelevant_jira_issue_keys = ["TRT-2005", "TRT-2188"]
        jf.filter_out["issuetype"]["id"] = irrelevant_jira_issue_keys
        jf.extract()

        result, result_md = load_jira_files()
        self.assert_hierarchy_valid(result)

        result_json_str = json.dumps(result)

        for issue_id in expected_ids:
            self.assertIn(issue_id, result_json_str)
            self.assertIn(issue_id, result_md)

        for issue_id in irrelevant_jira_issue_keys:
            if jf.filter_on:
                self.assertNotIn(issue_id, result_json_str)
                self.assertNotIn(issue_id, result_md)
            else:
                self.assertIn(issue_id, result_json_str)
                self.assertIn(issue_id, result_md)

    def test_filter_issue_keys_on(self):
        jf = JiraScraper(settings=settings, urls=urls, filter_on=True)
        self._test_filter_issue_keys(jf)

    def test_filter_issue_keys_off(self):
        jf = JiraScraper(settings=settings, urls=urls, filter_on=False)
        self._test_filter_issue_keys(jf)

    def _test_filter_project_keys(self, jf):
        irrelevant_project_keys = ["TRT"]
        jf.filter_out["project"]["key"] = irrelevant_project_keys

        jf.extract()

        result, result_md = load_jira_files()
        self.assert_hierarchy_valid(result)

        result_json_str = json.dumps(result)

        for issue_id in expected_ids:
            self.assertIn(issue_id, result_json_str)
            self.assertIn(issue_id, result_md)

        for project_key in irrelevant_project_keys:
            if jf.filter_on:
                self.assertNotIn(f"{project_key}-", result_json_str)
                self.assertNotIn(f"{project_key}-", result_md)
            else:
                self.assertIn(f"{project_key}-", result_json_str)
                self.assertIn(f"{project_key}-", result_md)

    def test_filter_project_keys_on(self):
        jf = JiraScraper(settings=settings, urls=urls, filter_on=True)
        self._test_filter_project_keys(jf)

    def test_filter_project_keys_off(self):
        jf = JiraScraper(settings=settings, urls=urls, filter_on=False)
        self._test_filter_project_keys(jf)

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

        jf = JiraScraper(settings=settings, issue_ids=issue_ids)
        issues = jf.search_issues(issue_ids)
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

    def test_extract_empty_usernames(self):
        """Test that empty username list returns empty results without error"""
        jf = JiraScraper(filter_on=False, settings=settings, usernames=[])
        found_ids = jf.get_issues_assigned_to_usernames([])
        self.assertEqual(
            len(found_ids), 0, "Empty username list should return no issues"
        )

    def test_extract_invalid_username(self):
        """Test that invalid usernames return empty results without error"""
        invalid_username = "this-user-does-not-exist"
        jf = JiraScraper(settings=settings, usernames=[invalid_username])
        found_ids = jf.get_issues_assigned_to_usernames([invalid_username])
        self.assertEqual(len(found_ids), 0, "Invalid username should return no issues")

    def test_extract_usernames(self):
        """Test fetching issues by username"""
        test_username = "rhn-support-ngirard"
        expected_issue_ids = {
            "SPLAT-2418",
            "SPLAT-2405",
            "SPLAT-2404",  # Sample issue IDs we expect
            "SPLAT-2403",
            "SPLAT-2398",
            "SPLAT-2396",
        }

        # Test with username - disable filtering since we want all issues
        jf = JiraScraper(settings=settings, usernames=[test_username], filter_on=False)
        found_ids = jf.get_issues_assigned_to_usernames([test_username])
        self.assertGreater(len(found_ids), 0, "Should find issues for username")
        self.assertTrue(
            expected_issue_ids.issubset(set(found_ids)),
            f"Expected issues {expected_issue_ids} not found in {found_ids}",
        )

        # Test full extraction - disable filtering since we want all issues
        jf = JiraScraper(settings=settings, usernames=[test_username], filter_on=False)
        jf.extract()
        result, result_md = load_jira_files()

        # Verify the hierarchy is valid
        self.assert_hierarchy_valid(result)

        # Verify issues are in the output
        result_json_str = json.dumps(result)
        for issue_id in expected_issue_ids:
            self.assertIn(issue_id, result_json_str)
            self.assertIn(issue_id, result_md)

    def test_extract_issue_ids(self):
        jf = JiraScraper(
            settings=settings,
            issue_ids=[
                "SPLAT-1800",
                "SPLAT-1809",
            ],
        )
        jf.extract()

        result, result_md = load_jira_files()
        self.assert_hierarchy_valid(result)


def load_jira_files():
    with open(settings.file_paths.jira_json_file_path) as f:
        result = json.load(f)

    with open(settings.file_paths.jira_md_file_path) as f:
        result_md = f.read()

    return result, result_md


if __name__ == "__main__":
    unittest.main()
