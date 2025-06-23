import re
import os
import json
from jira import JIRAError
from collections import defaultdict
from clients.jira_client import JiraClient
from clients.llm_client import LLMClient
from scrapers.exceptions import raise_scraper_exception
from utils.utils import get_env, contains_valid_keywords


class JiraScraper:
    def __init__(self, max_results=200):
        data_dir = get_env(f"DATA_DIR")
        os.makedirs(data_dir, exist_ok=True)
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
        def organize_issues(issues, epic_link_field_id):
            hierarchy = defaultdict(
                lambda: defaultdict(
                    lambda: {"summary": "", "description": "", "stories": {}}
                )
            )

            for issue in issues:
                fields = issue.fields
                if not self.is_jira_issue_valid(fields):
                    continue
                issue_type = fields.issuetype.name
                project_name = fields.project.name
                issue_key = issue.key
                summary = getattr(fields, "summary", "")
                description = getattr(fields, "description", "") or ""

                if issue_type.lower() == "epic":
                    hierarchy[project_name][issue_key]["summary"] = summary
                    hierarchy[project_name][issue_key]["description"] = description

            # populate linked issues
            for issue in issues:
                fields = issue.fields
                issue_type = fields.issuetype.name
                epic_key = getattr(fields, epic_link_field_id, None)
                issue_key = issue.key
                summary = getattr(fields, "summary", "")
                description = getattr(fields, "description", "") or ""

                if issue_type.lower() in ["story", "task"] and epic_key:
                    project_name = fields.project.name
                    story_data = {
                        "summary": summary,
                        "description": description,
                        "related": [],
                    }

                    for link in getattr(fields, "issuelinks", []):
                        linked = (
                            link.outwardIssue
                            if hasattr(link, "outwardIssue")
                            else getattr(link, "inwardIssue", None)
                        )
                        if linked and hasattr(linked, "fields"):
                            if not self.is_jira_issue_valid(linked.fields):
                                continue
                            linked_type = linked.fields.issuetype.name
                            linked_summary = getattr(linked.fields, "summary", "")
                            linked_description = getattr(
                                linked.fields, "description", ""
                            )
                            story_data["related"].append(
                                {
                                    "key": linked.key,
                                    "type": linked_type,
                                    "summary": linked_summary,
                                    "description": linked_description,
                                }
                            )

                    hierarchy[project_name][epic_key]["stories"][issue_key] = story_data

            return hierarchy

        def filter_hierarchy_by_jira_id(jira_ids):
            filtered_hierarchy = defaultdict(dict)
            for project, epics in hierarchy.items():
                for epic_key, epic_data in epics.items():
                    if epic_key in jira_ids:
                        filtered_hierarchy[project][epic_key] = epic_data
                    else:
                        filtered_stories = {
                            k: v
                            for k, v in epic_data["stories"].items()
                            if k in jira_ids
                        }
                        if filtered_stories:
                            filtered_hierarchy[project][epic_key] = {
                                "summary": epic_data["summary"],
                                "description": epic_data["description"],
                                "stories": filtered_stories,
                            }

            return filtered_hierarchy

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
            hierarchy = organize_issues(issues, self.jira_client.epic_link_field_id)
            md = render_to_markdown(hierarchy)
            jira_feature_ids = ask_llm_to_filter_features(md)
            hierarchy = filter_hierarchy_by_jira_id(jira_feature_ids)
            write_json_file(hierarchy)
            md = render_to_markdown(hierarchy)
            write_md_file(md)
            return md
        except JIRAError as je:
            raise_scraper_exception(f"[JIRAError] Failed bulk fetch: {je}")
        except Exception as e:
            raise_scraper_exception(f"[ERROR] Failed bulk fetch: {e}")

    def is_jira_issue_valid(self, jira_issue):
        return (
            jira_issue.issuetype.name in self.filter["issuetype"]["name"]
            and jira_issue.issuetype.id not in self.filter_out["issuetype"]["id"]
            and contains_valid_keywords(vars(jira_issue).values())
        )


def ask_llm_to_filter_features(md):
    llm = LLMClient()
    q = ""
    with open(f"config/is_feature_prompt_template.txt") as f:
        q = f.read()
    prompt = f"{q}\n{md}"
    resp = llm.prompt_llm(prompt)
    feature_jira_ids = extract_jira_ids(resp)
    return feature_jira_ids


def write_json_file(hierarchy):
    data_dir = get_env(f"DATA_DIR")
    json_file = f"{data_dir}/jira.json"
    with open(json_file, "w") as f:
        json.dump(hierarchy, f)


def write_md_file(md):
    data_dir = get_env(f"DATA_DIR")
    md_file = f"{data_dir}/jira.md"
    with open(md_file, "w") as f:
        f.write(md)


def extract_jira_ids(md):
    return re.findall(r"\b[A-Z][A-Z0-9]+-\d+\b", md)


def render_to_markdown(hierarchy):
    md = ""
    for project, epics in hierarchy.items():
        md += f"# Project: {project}\n\n"
        for epic_key, epic in epics.items():
            md += f"## Epic: {epic_key} — {epic['summary']}\n"
            md += f"**Description:**\n{epic['description']}\n\n"
            for story_key, story in epic["stories"].items():
                md += f"### Story: {story_key} — {story['summary']}\n"
                md += f"**Description:**\n{story['description']}\n\n"
                if story["related"]:
                    md += f"#### Related Issues:\n"
                    for rel in story["related"]:
                        md += f"- **{rel['key']}** ({rel['type']}): {rel['summary']}\n"
                    md += "\n"
            md += "---\n\n"
    return md
