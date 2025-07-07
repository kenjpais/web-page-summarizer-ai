import unittest
import os
from clients.jira_client import JiraClient  # Replace with actual module path


class TestJiraClientIntegration(unittest.TestCase):

    def setUp(self):
        self.jira_server = os.getenv("JIRA_SERVER")
        if not self.jira_server:
            self.skipTest("JIRA_SERVER environment variable not set.")

        self.client = JiraClient()

    def test_epic_link_field_id(self):
        # Assumes JIRA has an "Epic Link" field
        field_id = self.client.get_epic_link_field_id()
        self.assertTrue(field_id.startswith("customfield_"))


if __name__ == "__main__":
    unittest.main()
