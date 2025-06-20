import json
from jira import JIRAError
from clients.jira_client import JiraClient
from models.jira_model import JiraModel
from utils.utils import contains_valid_keywords, get_env
from scrapers.exceptions import raise_scraper_exception


class JiraScraper:
    def __init__(self, max_results=200):
        try:
            self.jira_client = JiraClient()
            self.jira = self.jira_client.jira
            self.max_results = max_results
        except JIRAError as e:
            self.jira = None
            raise_scraper_exception(
                f'Failed to connect to JIRA Server: {getattr(e, "status_code", "N/A")} - {getattr(e, "text", str(e))}'
            )
        except Exception as e:
            self.jira = None
            raise_scraper_exception(f"Unexpected error: {e}")

        with open("config/jira_filter.json", "r") as f:
            self.filter = json.load(f)
        with open("config/jira_filter_out.json", "r") as f:
            self.filter_out = json.load(f)

    def validate_jira_url(self, url):
        return "browse/" in url

    def extract(self, urls):
        """Extracts JIRA information relevant for summarization."""
        issue_ids = set()
        for url in urls:
            if not self.validate_jira_url(url):
                continue
            issue_id = url.strip().split("browse/")[1]
            if not issue_id.split("-")[0]:
                continue
            issue_ids.add(issue_id)

        if not issue_ids:
            raise_scraper_exception("[!] Invalid JIRA URLs")
        try:
            jql = f"issuekey in ({','.join(issue_ids)})"
            issues = self.jira.search_issues(
                jql,
                maxResults=len(issue_ids),
                fields=f"summary,description,issuetype,parent,project,issuelinks,{self.jira_client.epic_link_field_id}",
            )
            results = {}
            for issue in issues:
                issue.fields.id = issue.key
                issue.fields.url = f"{self.jira._options['server']}/browse/{issue.key}"
                model = JiraModel(issue.fields)
                if not self.is_model_valid(model) or not contains_valid_keywords(
                    vars(model).values()
                ):
                    continue
                category = model.id.split("-")[0]
                if category not in results:
                    results[category] = []
                results[category].append(model.to_dict())
            return results
        except JIRAError as je:
            raise_scraper_exception(f"[JIRAError] Failed bulk fetch: {je}")
        except Exception as e:
            raise_scraper_exception(f"[ERROR] Failed bulk fetch: {e}")

    def is_model_valid(self, model):
        """Validates if model fits relevant filter criteria."""
        return (
            model.issuetype in self.filter["issuetype"]["name"]
            and model.id not in self.filter_out["issuetype"]["id"]
        )
