import os
import json
import unittest
from correlators.correlator import correlate_with_jira_issue_id
from filters.filter_required_fields import remove_irrelevant_fields_from_correlated
from utils.utils import get_env


class TestCorrelateWithJiraIssueId(unittest.TestCase):
    def test_correlate_with_jira_issue_id(self):
        data_dir = get_env("DATA_DIR")
        config_dir = get_env("CONFIG_DIR")
        os.makedirs(data_dir, exist_ok=True)

        jira_file = f"{data_dir}/JIRA.json"
        github_file = f"{data_dir}/GITHUB.json"
        correlated_file = f"{data_dir}/correlated.json"
        required_github_fields_file = f"{config_dir}/required_github_fields.json"

        # Set required fields
        with open(required_github_fields_file, "w") as f:
            json.dump(["title", "body"], f)

        issue_ids = {
            "AGENT": [
                {
                    "id": "AGENT-997",
                    "issuetype": "Story",
                    "description": "",
                    "summary": "test",
                    "labels": [],
                }
            ],
            "OTA": [
                {
                    "id": "OTA-1539",
                    "issuetype": "Story",
                    "description": "",
                    "summary": "test",
                    "labels": [],
                }
            ],
        }

        github_dicts = [
            {
                "id": 1,
                "title": "AGENT-997: Add auth support",
                "body": "Implements new feature AGENT-997",
            },
            {
                "id": 2,
                "title": "OTA-1539: Quiet flag for admin upgrade",
                "body": "Adds --quiet option for OTA-1539",
            },
        ]

        test_filtered_data = {
            "AGENT": {
                "AGENT-997": {
                    "JIRA": {"description": "", "summary": "test"},
                    "GITHUB": [
                        {
                            "title": "AGENT-997: Add auth support",
                            "body": "Implements new feature AGENT-997",
                        }
                    ],
                }
            },
            "OTA": {
                "OTA-1539": {
                    "JIRA": {"description": "", "summary": "test"},
                    "GITHUB": [
                        {
                            "title": "OTA-1539: Quiet flag for admin upgrade",
                            "body": "Adds --quiet option for OTA-1539",
                        }
                    ],
                }
            },
        }

        with open(jira_file, "w") as jirafile:
            json.dump(issue_ids, jirafile)
        with open(github_file, "w") as ghfile:
            for entry in github_dicts:
                ghfile.write(json.dumps(entry) + "\n")

        correlate_with_jira_issue_id()

        with open(correlated_file, "r") as f:
            correlated_data = json.load(f)

        # Check nested dictionary format
        for category, issues in issue_ids.items():
            self.assertIn(category, correlated_data)
            for issue in issues:
                issue_id = issue["id"]
                self.assertIn(issue_id, correlated_data[category])
                entry = correlated_data[category][issue_id]
                self.assertIn("JIRA", entry)
                self.assertIn("GITHUB", entry)
                self.assertIsInstance(entry["GITHUB"], list)

        remove_irrelevant_fields_from_correlated()

        with open(correlated_file, "r") as f:
            filtered_data = json.load(f)

        self.assertIsInstance(filtered_data, dict)
        self.assertGreater(len(filtered_data), 0)
        self.assertDictEqual(
            filtered_data, test_filtered_data
        )
