import unittest
from unittest.mock import MagicMock, patch
from clients.jira_client import JiraClient, JIRAError
from config.settings import get_settings

settings = get_settings()


class TestJiraClient(unittest.TestCase):

    def setUp(self):
        self.jira_server = "https://jira.example.com"
        self.mock_jira_patcher = patch("clients.jira_client.JIRA")
        self.mock_jira = self.mock_jira_patcher.start()

        # Setup mock JIRA instance
        self.mock_jira_instance = MagicMock()
        self.mock_jira.return_value = self.mock_jira_instance

        # Mock server info for debug logging
        self.mock_jira_instance.server_info.return_value = {"serverTitle": "Mock JIRA"}

        # Mock fields() response
        self.mock_fields = [
            {"id": "customfield_10014", "name": "Epic Link"},
            {"id": "summary", "name": "Summary"},
        ]
        self.mock_jira_instance.fields.return_value = self.mock_fields

        # Create client with mocked JIRA
        self.client = JiraClient(jira_server=self.jira_server, debug_enabled=False)

    def tearDown(self):
        self.mock_jira_patcher.stop()

    def test_epic_link_field_id_success(self):
        # Mock the fields response
        mock_fields = [
            {"id": "customfield_10014", "name": "Epic Link"},
            {"id": "summary", "name": "Summary"},
        ]
        self.mock_jira_instance.fields.return_value = mock_fields

        # Test successful case
        field_id = self.client.get_epic_link_field_id()
        self.assertEqual(field_id, "customfield_10014")

    def test_epic_link_field_id_not_found(self):
        # Mock fields without Epic Link
        mock_fields = [{"id": "summary", "name": "Summary"}]
        self.mock_jira_instance.fields.return_value = mock_fields

        # Test field not found case
        with self.assertRaises(JIRAError) as context:
            self.client.get_epic_link_field_id()
        self.assertIn("Epic Link field not found", str(context.exception))


if __name__ == "__main__":
    unittest.main()
