import unittest
from clients.jira_client import JiraClient
from config.settings import get_settings

settings = get_settings()


class TestJiraClientIntegration(unittest.TestCase):

    def setUp(self):
        self.client = JiraClient(
            jira_server=settings.api.jira_server,
            debug_enabled=settings.processing.debug,
        )

    def test_epic_link_field_id(self):
        # Assumes JIRA has an "Epic Link" field
        field_id = self.client.get_epic_link_field_id()
        self.assertTrue(field_id.startswith("customfield_"))


if __name__ == "__main__":
    unittest.main()
