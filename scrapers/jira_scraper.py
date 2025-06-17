import os
import json
from jira import JIRA, JIRAError
from models.jira_model import JiraModel
from utils.utils import contains_valid_keywords, get_env
from scrapers.exceptions import raise_scraper_exception


class JiraScraper:
    def __init__(self):
        try:
            server = os.getenv("JIRA_SERVER")
            self.jira = JIRA(options={"server": server})
            debug_enabled = get_env("DEBUG")
            if debug_enabled:
                print(
                    f"Connected to JIRA Server: {self.jira.server_info()['serverTitle']}"
                )
        except JIRAError as e:
            self.jira = None
            raise_scraper_exception(
                f'Failed to connect to JIRA Server "{server}": {e.status_code} - {e.text}'
            )
        except Exception as e:
            self.jira = None
            raise_scraper_exception(f"Unexpected error: {e}")

        with open("config/jira_filter.json", "r") as f:
            self.filter = json.load(f)

    def extract(self, urls):
        issue_ids = [
            url.strip().split("browse/")[1] for url in urls if "browse/" in url
        ]
        if not issue_ids:
            raise_scraper_exception("[!] Invalid JIRA URLs")

        try:
            jql = f"issuekey in ({','.join(issue_ids)})"
            issues = self.jira.search_issues(jql, maxResults=len(issue_ids))
            results = []
            for issue in issues:
                issue.fields.id = issue.key
                issue.fields.url = f"{self.jira._options['server']}/browse/{issue.key}"
                model = JiraModel(issue.fields)
                if self.is_model_valid(model) and contains_valid_keywords(
                    vars(model).values()
                ):
                    results.append(model.to_dict())
            return results
        except JIRAError as je:
            raise_scraper_exception(f"[JIRAError] Failed bulk fetch: {je}")
        except Exception as e:
            raise_scraper_exception(f"[ERROR] Failed bulk fetch: {e}")

    def is_model_valid(self, model):
        return model.issuetype.name in self.filter["issuetype"]["name"]
