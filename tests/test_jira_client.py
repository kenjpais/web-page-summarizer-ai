import unittest
from clients.jira_client import JiraClient


class TestJiraClientIntegration(unittest.TestCase):

    def setUp(self):
        self.client = JiraClient()

    def test_epic_link_field_id(self):
        # Assumes JIRA has an "Epic Link" field
        field_id = self.client.get_epic_link_field_id()
        self.assertTrue(field_id.startswith("customfield_"))


if __name__ == "__main__":
    unittest.main()
