import requests
from typing import Any
from jira import JIRA, JIRAError
from config.settings import get_settings
from utils.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


class JiraClient:
    def __init__(
        self,
        jira_server: str = None,
        jira_username: str = None,
        jira_password: str = None,
    ) -> None:
        # Use provided server or fall back to settings
        self.server: str = jira_server or settings.api.jira_server
        if not self.server:
            raise JIRAError(
                f"Invalid JIRA_SERVER: {self.server}. Provide jira_server parameter or set JIRA_SERVER environment variable."
            )

        self.base_url = f"{self.server}/rest/api/2"
        self.jira_username = jira_username
        self.jira_password = jira_password

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

        debug_enabled = settings.processing.debug
        if debug_enabled:
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

    def get_epic_link_field_id(self):
        headers = {"Accept": "application/json"}
        url = f"{self.base_url}/field"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        fields = response.json()
        for field in fields:
            if field.get("name", "").lower() == "epic link":
                return field["id"]
        raise JIRAError("Epic Link field not found")
