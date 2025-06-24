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

        jira_file = f"{data_dir}/jira.json"
        github_file = f"{data_dir}/GITHUB.json"
        correlated_file = f"{data_dir}/correlated.json"
        required_github_fields_file = f"{config_dir}/required_github_fields.json"

        # Set required fields
        with open(required_github_fields_file, "w") as f:
            json.dump(["title", "body"], f)

        # New format: Epic with nested story
        jira_data = {
            "AGENT": {
                "AGENT-EPIC-1": {
                    "summary": "Epic Summary AGENT",
                    "description": "Epic Description AGENT",
                    "stories": {
                        "AGENT-997": {
                            "summary": "Story Summary",
                            "description": "Story Description",
                            "related": [],
                        }
                    },
                }
            },
            "OTA": {
                "OTA-EPIC-1": {
                    "summary": "Epic Summary OTA",
                    "description": "Epic Description OTA",
                    "stories": {
                        "OTA-1539": {
                            "summary": "Story Summary",
                            "description": "Story Description",
                            "related": [],
                        }
                    },
                }
            },
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
                    "JIRA": {
                        "key": "AGENT-997",
                        "summary": "Story Summary",
                        "description": "Story Description",
                        "related": [],
                    },
                    "GITHUB": [
                        {
                            "title": "AGENT-997: Add auth support",
                            "body": "Implements new feature AGENT-997",
                        }
                    ],
                },
                "AGENT-EPIC-1": {
                    "JIRA": {
                        "key": "AGENT-EPIC-1",
                        "summary": "Epic Summary AGENT",
                        "description": "Epic Description AGENT",
                        "stories": {
                            "AGENT-997": {
                                "summary": "Story Summary",
                                "description": "Story Description",
                                "related": [],
                            }
                        },
                    }
                },
            },
            "OTA": {
                "OTA-1539": {
                    "JIRA": {
                        "key": "OTA-1539",
                        "summary": "Story Summary",
                        "description": "Story Description",
                        "related": [],
                    },
                    "GITHUB": [
                        {
                            "title": "OTA-1539: Quiet flag for admin upgrade",
                            "body": "Adds --quiet option for OTA-1539",
                        }
                    ],
                },
                "OTA-EPIC-1": {
                    "JIRA": {
                        "key": "OTA-EPIC-1",
                        "summary": "Epic Summary OTA",
                        "description": "Epic Description OTA",
                        "stories": {
                            "OTA-1539": {
                                "summary": "Story Summary",
                                "description": "Story Description",
                                "related": [],
                            }
                        },
                    }
                },
            },
        }

        with open(jira_file, "w") as f:
            json.dump(jira_data, f)

        with open(github_file, "w") as f:
            json.dump(github_dicts, f)

        correlate_with_jira_issue_id()
        remove_irrelevant_fields_from_correlated()

        with open(correlated_file, "r") as f:
            correlated_data = json.load(f)

        # Check nested dictionary structure
        for category in ["AGENT", "OTA"]:
            self.assertIn(category, correlated_data)
            for issue_key in test_filtered_data[category]:
                self.assertIn(issue_key, correlated_data[category])
                expected_entry = test_filtered_data[category][issue_key]
                actual_entry = correlated_data[category][issue_key]

                self.assertIn("JIRA", actual_entry)
                self.assertEqual(
                    expected_entry["JIRA"]["summary"], actual_entry["JIRA"]["summary"]
                )
                self.assertEqual(
                    expected_entry["JIRA"]["description"],
                    actual_entry["JIRA"]["description"],
                )

                if "GITHUB" in expected_entry:
                    self.assertIn("GITHUB", actual_entry)
                    self.assertListEqual(
                        expected_entry["GITHUB"], actual_entry["GITHUB"]
                    )

        with open(correlated_file, "r") as f:
            filtered_data = json.load(f)

        self.assertIsInstance(filtered_data, dict)
        self.assertGreater(len(filtered_data), 0)
