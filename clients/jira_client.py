import requests
from jira import JIRA, JIRAError
from config.settings import get_settings
from utils.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


class JiraClient:
    def __init__(self) -> None:
        self.server: str = settings.api.jira_server
        if not self.server:
            raise JIRAError(
                f"Invalid JIRA_SERVER environment variable is {self.server}"
            )
        self.base_url = f"{self.server}/rest/api/2"
        try:
            self.jira = JIRA(options={"server": self.server})
        except JIRAError as e:
            raise JIRAError(f"Failed to connect to JIRA server {self.server}: {e}")
        debug_enabled = settings.processing.debug
        if debug_enabled:
            logger.debug(
                f"Connected to JIRA Server: {self.jira.server_info()['serverTitle']}"
            )
        self.epic_link_field_id = self.get_epic_link_field_id()

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
