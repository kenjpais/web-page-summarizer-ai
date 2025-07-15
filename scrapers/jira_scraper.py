import re
import json
from pathlib import Path
from typing import List, Any
from itertools import islice

from jira import JIRAError, Issue, JIRA
from clients.jira_client import JiraClient
from models.jira_model import create_jira_issue_dict
from scrapers.exceptions import raise_scraper_exception
from utils.utils import contains_valid_keywords
from config.settings import get_settings, get_config_loader
from utils.logging_config import get_logger

logger = get_logger(__name__)

settings = get_settings()
config_loader = get_config_loader()

FILTER_ON = settings.processing.filter_on
FEATURE_FILTER_ON = False
KEYWORD_MATCHING_ON = False

data_dir = Path(settings.directories.data_dir)


class JiraScraper:
    def __init__(self, filter_on: bool = FILTER_ON) -> None:
        data_dir.mkdir(exist_ok=True)
        self.filter_on = filter_on
        try:
            self.jira_client: JiraClient = JiraClient()
            if not self.jira_client:
                raise_scraper_exception(f"JiraClient() is {self.jira_client}")

            self.jira: JIRA = self.jira_client.jira
            self.feature_field_id: str = ""

            for field in self.jira.fields():
                if "feature" in field["name"].lower():
                    self.feature_field_id = field["id"]

            self.issue_result_cache = {}
            self.project_result_cache = {}
        except JIRAError as e:
            raise_scraper_exception(
                f'Failed to connect to JIRA Server: {getattr(e, "status_code", "N/A")} - {getattr(e, "text", str(e))}'
            )
        except Exception as e:
            raise_scraper_exception(f"Unexpected error: {e}")

        self.filter = config_loader.get_jira_filter()
        self.filter_out = config_loader.get_jira_filter_out()

    def validate_jira_url(self, url: str) -> bool:
        return "browse/" in url

    def filter_pass(self, jira_issue: Issue) -> bool:
        """
        if jira_issue.issuetype.name not in self.filter["issuetype"]["name"]:
            logger.debug(
                f"\nKDEBUG: {jira_issue.issuetype.name} not in valid issuetypes {self.filter["issuetype"]["name"]}"
            )
            return False
        if jira_issue.issuetype.id in self.filter_out["issuetype"]["id"]:
            logger.debug(
                f"\nKDEBUG: {jira_issue.issuetype.id} in invalid issue_ids {self.filter["issuetype"]["id"]}"
            )
            return False
        if (
            getattr(jira_issue.project, "key", "")
            in self.filter_out["project"]["key"]
        ):
            logger.debug(
                f"\nKDEBUG: {getattr(jira_issue.project, "key", "")} in invalid project_keys {self.filter_out["project"]["key"]}"
            )
            return False
        return True
        """
        return (
            jira_issue.issuetype.name in self.filter["issuetype"]["name"]
            and jira_issue.issuetype.id not in self.filter_out["issuetype"]["id"]
            and getattr(jira_issue.project, "key", "")
            not in self.filter_out["project"]["key"]
        )

    def search_project(self, project_key: str) -> Any:
        """
        Fetches JIRA project information using the JIRA python library.
        """
        if project_key not in self.project_result_cache:
            try:
                self.project_result_cache[project_key] = self.jira_client.jira.project(
                    project_key
                )
            except JIRAError as je:
                raise_scraper_exception(f"[JIRAError] Failed JIRA fetch: {je}")
            except Exception as e:
                raise_scraper_exception(f"[ERROR] Failed JIRA fetch: {e}")

        return self.project_result_cache[project_key]

    def populate_project_result_cache(self, project_keys: List[str]) -> None:
        """
        Fetches JIRA project information using the JIRA python library.
        Populates self.project_result_cache to be used later by organize_issues()
        """
        desired_keys = set(project_keys)
        projects = self.jira.projects()
        self.project_result_cache = {
            p.key: p for p in projects if p.key in desired_keys
        }

    def search_issues(self, issue_ids: List[str]) -> List[Issue]:
        """
        Fetches JIRA information using the JIRA python library.
        Performs pagination.
        Returns a list of JIRA Issue objects.
        """

        def run_query(issue_ids):
            """
            Runs a JQL query.
            Returns a list of JIRA Issue objects.
            """
            try:
                if len(issue_ids) == 1:
                    issue_id = issue_ids[0]
                    if issue_id not in self.issue_result_cache:
                        self.issue_result_cache[issue_id] = [
                            self.jira_client.jira.issue(issue_id)
                        ]
                    return self.issue_result_cache[issue_id]
                return list(
                    self.jira.search_issues(
                        f"issuekey in ({','.join(issue_ids)})",
                        fields=f"summary,description,issuetype,parent,project,issuelinks,{self.jira_client.epic_link_field_id}",
                        use_post=True,
                        maxResults=len(issue_ids),
                    )
                )
            except JIRAError as je:
                logger.error(f"[JIRAError] Failed JIRA fetch: {je}")
                return []
            except Exception as e:
                logger.error(f"[ERROR] Failed JIRA fetch: {e}")
                return []

        def chunked(iterator, size):
            """Yield successive chunks of given size from iterable."""
            while True:
                chunk = list(islice(iterator, size))
                if not chunk:
                    break
                yield chunk

        if not issue_ids:
            raise_scraper_exception(
                f"[!][ERROR] Failed JIRA fetch: Empty issue_ids list"
            )

        issues = []
        batch_size = 500
        issue_id_iter = iter(issue_ids)

        for i, chunk in enumerate(chunked(issue_id_iter, batch_size)):
            issue_chunk = run_query(chunk)
            issues.extend(issue_chunk)
            if len(issue_ids) > 1:
                logger.debug(f"Chunk[{i}]: Fetched: {len(issue_chunk)}")

        return issues

    def extract(self, urls):
        """
        Extracts the JIRA information from each URL.
        """

        def organize_issues(issues, epic_link_field_id):
            """
            Organizes the JIRA issues in a hierarchical structure.
            """
            hierarchy = {}
            visited_keys = set()

            def add_issue(issue, hierarchy):
                """
                Adds JIRA issues recursively by scraping the attached links eg. feature link, epic link etc.
                """
                if not issue or not hasattr(issue, "fields"):
                    raise ValueError("[ERROR] Invalid issue")

                fields = issue.fields

                def add_project(project_key, project_name, hierarchy):
                    """
                    Helper function to add JIRA project to issue hierarchy structure.
                    """
                    if project_name in hierarchy:
                        return

                    hierarchy[project_name] = {}

                    if project_obj := self.search_project(project_key):
                        summary = getattr(project_obj, "summary", None)
                        description = getattr(project_obj, "description", None)
                        if summary:
                            hierarchy[project_name]["summary"] = summary
                        if description:
                            hierarchy[project_name]["description"] = description

                def add_feature_issues(fields, hierarchy):
                    """
                    Helper function to add JIRA feature issues.
                    """
                    feature_issue_keys = set()
                    if self.filter:
                        issuelinks_types = self.filter.get("issuelinks", {}).get(
                            "type", {}
                        )
                        inward_link_types = issuelinks_types.get("inward", {})
                        outward_link_types = issuelinks_types.get("outward", {})
                        feature_link_types = set(inward_link_types).union(
                            outward_link_types
                        )

                    if self.feature_field_id and hasattr(
                        issue.fields, self.feature_field_id
                    ):
                        feature_issue = getattr(
                            issue.fields, self.feature_field_id, None
                        )
                        if (
                            feature_issue
                            and hasattr(feature_issue, "key")
                            and feature_issue.key
                        ):
                            feature_issue_keys.add(feature_issue.key)

                    for link in getattr(fields, "issuelinks", []):
                        if (
                            hasattr(link, "type")
                            and link.type.name.lower() in feature_link_types
                        ):
                            if hasattr(link, "inwardIssue"):
                                feature_issue_keys.add(link.inwardIssue.key)
                            elif hasattr(link, "outwardIssue"):
                                feature_issue_keys.add(link.outwardIssue.key)

                    if feature_issue_keys and (
                        feature_issues := self.search_issues(list(feature_issue_keys))
                    ):
                        for feature_issue in feature_issues:
                            add_issue(feature_issue, hierarchy)

                # Check if key already visited
                if issue.key in visited_keys:
                    return
                visited_keys.add(issue.key)

                project_key = getattr(fields.project, "key", "")
                project_name = getattr(fields.project, "name", "")
                if not project_name or not project_key:
                    return

                if self.filter_on and not self.filter_pass(fields):
                    logger.debug(f"Issue [{issue.key}] failed filter pass")
                    return

                if KEYWORD_MATCHING_ON and not contains_valid_keywords(
                    vars(fields).values()
                ):
                    logger.debug(f"Issue [{issue.key}] failed keyword match")
                    return

                add_project(project_key, project_name, hierarchy)

                if issue_type := getattr(fields.issuetype, "name", "").lower():
                    issue_type_key = (
                        "stories" if issue_type == "story" else f"{issue_type}s"
                    )
                    if issue_type_key not in hierarchy[project_name]:
                        hierarchy[project_name][issue_type_key] = {}
                    if issue_dict := create_jira_issue_dict(issue):
                        hierarchy[project_name][issue_type_key][issue.key] = issue_dict

                    if epic_link_field_id and (
                        epic_key := getattr(fields, epic_link_field_id, None)
                    ):
                        hierarchy[project_name][issue_type_key][issue.key][
                            "epic_key"
                        ] = epic_key
                        if epic := self.search_issues([epic_key]):
                            add_issue(epic[0], hierarchy)

                    add_feature_issues(fields, hierarchy)

            for issue in issues:
                add_issue(issue, hierarchy)

            return hierarchy

        logger.debug(f"FILTER IS {"ON" if self.filter_on else "OFF"}")

        issue_ids = set()
        for url in urls:
            if self.validate_jira_url(url):
                parts = url.strip().split("browse/")
                if len(parts) > 1 and parts[1]:
                    issue_id = parts[1].split("_")[0]
                    if issue_id:
                        issue_ids.add(issue_id)

        if not issue_ids:
            raise_scraper_exception("[!][ERROR] Invalid JIRA URLs")

        logger.info(f"[*] Extracted {len(issue_ids)} Issue IDs")

        self.populate_project_result_cache([id.split("-")[0] for id in issue_ids])

        issues = self.search_issues(list(issue_ids))
        if not issues:
            raise_scraper_exception("[!][ERROR] No JIRA issues found")

        logger.debug(f"\nFetched {len(issues)} JIRA issues")
        if len(issues) < len(issue_ids):
            failed_issue_ids = issue_ids - set(issue.key for issue in issues)
            logger.warning(
                f"{len(failed_issue_ids)} Issue IDs failed fetched: {failed_issue_ids}"
            )

        hierarchy = organize_issues(issues, self.jira_client.epic_link_field_id)
        if not hierarchy:
            raise_scraper_exception("[ERROR] JIRA Hierarchy construction failed")
        write_json_file(hierarchy)
        write_md_file(render_to_markdown(hierarchy))


def write_json_file(hierarchy):
    json_file = data_dir / "jira.json"
    with open(json_file, "w") as f:
        json.dump(hierarchy, f, indent=2)


def write_md_file(md):
    if not md:
        return
    md_file = data_dir / "jira.md"
    with open(md_file, "w") as f:
        f.write(md)


def extract_jira_ids(md):
    return re.findall(r"\b[A-Z][A-Z0-9]+-\d+\b", md)


def render_to_markdown(hierarchy):
    md = ""
    for project, project_data in hierarchy.items():
        md += f"# Project: {project}\n\n"
        md += f"**Summary**: {project_data.get('summary', '')}\n\n"
        md += f"**Description**: {project_data.get('description', '')}\n\n"

        # Process all issue types dynamically
        issue_types = [
            "epics",
            "stories",
            "bugs",
            "features",
            "enhancements",
            "tasks",
            "improvements",
            "sub-tasks",
        ]

        for issue_type in issue_types:
            issues = project_data.get(issue_type, {})
            if not issues:
                continue

            for issue_key, issue in issues.items():
                if not isinstance(issue, dict):
                    logger.warning(
                        f"[!] Skipping {issue_type[:-1]} {issue_key} — Invalid structure"
                    )
                    continue

                # Format header based on issue type
                if issue_type == "epics":
                    md += f"## Epic: {issue_key} — {issue.get('summary', '')}\n"
                elif issue_type == "stories":
                    md += f"### Story: {issue_key} — {issue.get('summary', '')}\n"
                else:
                    # For bugs, features, enhancements, etc., use the singular form
                    issue_type_singular = (
                        issue_type.rstrip("s")
                        if issue_type.endswith("s")
                        else issue_type
                    )
                    md += f"### {issue_type_singular.title()}: {issue_key} — {issue.get('summary', '')}\n"

                md += f"**Description:**\n{issue.get('description', '')}\n\n"

                # Add comments if available
                comments = issue.get("comments", [])
                if comments:
                    md += "**Comments:**\n"
                    for comment in comments:
                        md += f"- {comment}\n"
                    md += "\n"

                # Add epic link if available (for non-epic issues)
                if issue_type != "epics" and "epic_key" in issue:
                    md += f"**Linked Epic:** {issue['epic_key']}\n\n"

        md += "---\n\n"
    return md


"""
def ask_llm_to_filter_features(md):
    features = classify_chain.invoke({"correlated_info": md})
    jira_ids = extract_jira_ids(features)
    return jira_ids

    with open(f"config/is_feature_prompt_template.txt") as f:
        q = f.read()
    prompt = f"{q}\n{md}"
    resp = llm.prompt_llm(prompt)
    feature_jira_ids = extract_jira_ids(resp)
    return feature_jira_ids


def filter_hierarchy_by_jira_id(jira_ids) -> defaultdict:
    filtered_hierarchy = defaultdict(
        lambda: {"summary": "", "description": "", "epics": {}, "stories": {}}
    )

    for project, project_data in hierarchy.items():
        for epic_key, epic_data in project_data.get("epics", {}).items():
            if epic_key in jira_ids:
                filtered_hierarchy[project]["epics"][epic_key] = epic_data
            else:
                filtered_stories = {
                    k: v
                    for k, v in epic_data.get("stories", {}).items()
                    if k in jira_ids
                }
                if filtered_stories:
                    filtered_hierarchy[project]["epics"][epic_key] = {
                        "summary": epic_data.get("summary", ""),
                        "description": epic_data.get("description", ""),
                        "stories": filtered_stories,
                    }

    return filtered_hierarchy
"""
