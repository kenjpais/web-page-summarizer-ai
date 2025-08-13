import requests
from typing import Any
from jira import JIRA, JIRAError
from utils.logging_config import get_logger

logger = get_logger(__name__)


class JiraClient:
    def __init__(
        self,
        jira_server: str,
        jira_username: str = None,
        jira_password: str = None,
        debug_enabled: bool = False,
    ) -> None:
        self.server = jira_server
        if not self.server:
            raise JIRAError(
                f"Invalid JIRA_SERVER: {self.server}. Provide jira_server parameter or set JIRA_SERVER environment variable."
            )

        self.base_url = f"{self.server}/rest/api/2"
        self.jira_username = jira_username
        self.jira_password = jira_password
        self.debug_enabled = debug_enabled

        # Create JIRA connection with or without authentication
        jira_options = {"server": self.server}
        try:
            if jira_username and jira_password:
                self.jira = JIRA(
                    options=jira_options, basic_auth=(jira_username, jira_password)
                )
            else:
                self.jira = JIRA(options=jira_options)
        except JIRAError as e:
            raise JIRAError(f"Failed to connect to JIRA server {self.server}: {e}")

        if self.debug_enabled:
            logger.debug(
                f"Connected to JIRA Server: {self.jira.server_info()['serverTitle']}"
            )
        self.epic_link_field_id = self.get_epic_link_field_id()

    def get_config(self) -> dict[str, Any]:
        """
        Get the configuration for the JIRA client.
        """
        return {
            "jira_server": self.server,
            "jira_username": self.jira_username,
            "jira_password": self.jira_password,
            "jira_base_url": self.base_url,
        }

    def get_epic_link_field_id(self, timeout=30):
        """Get the field ID for Epic Link.

        Args:
            timeout (int): Timeout in seconds for the request. Defaults to 30.

        Returns:
            str: The field ID for Epic Link (e.g. 'customfield_10014')

        Raises:
            JIRAError: If Epic Link field is not found or request fails
        """
        try:
            fields = self.jira.fields()
            for field in fields:
                if field.get("name", "").lower() == "epic link":
                    return field["id"]
            raise JIRAError("Epic Link field not found")
        except Exception as e:
            raise JIRAError(f"Failed to get Epic Link field ID: {str(e)}")
