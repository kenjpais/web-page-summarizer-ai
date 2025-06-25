import os
import requests
from jira import JIRA, JIRAError
from utils.utils import get_env


class JiraClient:
    def __init__(self):
        self.server = os.getenv("JIRA_SERVER")
        self.base_url = f"{self.server}/rest/api/2"
        self.jira = JIRA(options={"server": self.server})
        debug_enabled = get_env("DEBUG")
        if debug_enabled:
            print(f"Connected to JIRA Server: {self.jira.server_info()['serverTitle']}")
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
