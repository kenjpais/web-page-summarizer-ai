import re
import os
import json
from typing import List, Dict, Any
from collections import defaultdict
from jira import JIRAError

from clients.jira_client import JiraClient
from clients.local_llm_chain import local_llm
from models.jira_model import create_jira_issue_dict
from scrapers.exceptions import raise_scraper_exception
from chains.chains import classify_chain
from utils.utils import get_env, contains_valid_keywords
from filters.jira_fuzzy_matching import fuzzy_match_features_to_jira
from filters.filter_enabled_feature_gates import filter_enabled_feature_gates

llm = local_llm

FILTER_ON = False
KEYWORD_MATCHING_ON = False

data_dir = get_env("DATA_DIR")
config_dir = get_env("CONFIG_DIR")

with open(f"{config_dir}/jira_filter.json", "r") as f:
    jira_filter = json.load(f)
with open(f"{config_dir}/jira_filter_out.json", "r") as f:
    jira_filter_out = json.load(f)


class JiraScraper:
    def __init__(self, max_results=200):
        try:
            llm.test_llm_connection()
        except Exception as e:
            raise_scraper_exception(f"Unable to connect to LLM: {e}")

        os.makedirs(data_dir, exist_ok=True)
        try:
            self.jira_client = JiraClient()
            self.jira = self.jira_client.jira
            self.feature_field_id = ""
            for field in self.jira.fields():
                if "feature" in field["name"].lower():
                    self.feature_field_id = field["id"]
            self.max_results = max_results
            self.project_result_cache = {}
        except JIRAError as e:
            self.jira = None
            raise_scraper_exception(
                f'Failed to connect to JIRA Server: {getattr(e, "status_code", "N/A")} - {getattr(e, "text", str(e))}'
            )
        except Exception as e:
            self.jira = None
            raise_scraper_exception(f"Unexpected error: {e}")

        self.filter = jira_filter
        self.filter_out = jira_filter_out

    def validate_jira_url(self, url):
        return "browse/" in url

    def is_jira_issue_valid(self, jira_issue):
        return (
            jira_issue.issuetype.name in self.filter["issuetype"]["name"]
            and jira_issue.issuetype.id not in self.filter_out["issuetype"]["id"]
        )

    def is_relevant(self, fields):
        if (FILTER_ON and not self.is_jira_issue_valid(fields)) or (
            KEYWORD_MATCHING_ON and not contains_valid_keywords(vars(fields).values())
        ):
            print("KDEBUG: Irrelevant issue")
            return False
        return True

    def search_project(self, project_key):
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

    def search_issues(self, issue_ids: List) -> List:
        if not issue_ids:
            raise_scraper_exception(
                f"[!][ERROR] Failed JIRA fetch: Empty issue_ids list"
            )
        try:
            if len(issue_ids) == 1:
                return [self.jira_client.jira.issue(issue_ids[0])]
            return self.jira.search_issues(
                f"issuekey in ({','.join(issue_ids)})",
                fields=f"summary,description,issuetype,parent,project,issuelinks,{self.jira_client.epic_link_field_id}",
                use_post=True,
            )
        except JIRAError as je:
            # raise_scraper_exception(f"[JIRAError] Failed JIRA fetch: {je}")
            print(f"[JIRAError] Failed JIRA fetch: {je}")
            return []
        except Exception as e:
            raise_scraper_exception(f"[ERROR] Failed JIRA fetch: {e}")

    def extract(self, urls):
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
                        if hasattr(feature_issue, "key"):
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

                def add_project(project_key, project_name, hierarchy):
                    """
                    Helper function to add JIRA project to issue hierarchy structure.
                    """
                    if project_name not in hierarchy:
                        hierarchy[project_name] = {}

                    if project_obj := self.search_project(project_key):
                        summary = getattr(project_obj, "summary", None)
                        description = getattr(project_obj, "description", None)
                        if summary:
                            hierarchy[project_name]["summary"] = summary
                        if description:
                            hierarchy[project_name]["description"] = description

                # Check if key already visited
                if issue.key in visited_keys:
                    return
                visited_keys.add(issue.key)

                if not self.is_relevant(fields):
                    return

                project_key = getattr(fields.project, "key", "")
                project_name = getattr(fields.project, "name", "")
                if not project_name or not project_key:
                    return

                add_project(project_key, project_name, hierarchy)

                if issue_type := getattr(fields.issuetype, "name", "").lower():
                    issue_type_key = (
                        "stories" if issue_type == "story" else f"{issue_type}s"
                    )
                    if issue_dict := create_jira_issue_dict(issue):
                        hierarchy[project_name][issue_type_key] = {
                            issue.key: issue_dict
                        }

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

        issue_ids = set()
        for url in urls:
            if self.validate_jira_url(url):
                parts = url.strip().split("browse/")
                if len(parts) > 1 and parts[1]:
                    issue_id = parts[1].split("_")[0]
                    if issue_id:
                        issue_ids.add(issue_id)

        if not issue_ids:
            raise_scraper_exception("[!] Invalid JIRA URLs")

        issues = self.search_issues(list(issue_ids))
        if not issues:
            raise_scraper_exception("[ERROR] No JIRA issues found")
        if isinstance(issues, dict):
            issues = [issues]
        hierarchy = organize_issues(issues, self.jira_client.epic_link_field_id)
        if not hierarchy:
            raise_scraper_exception("[ERROR] JIRA Hierarchy construction failed")
        if FILTER_ON:
            hierarchy = filter_hierarchy_by_jira_id(
                ask_llm_to_filter_features(render_to_markdown(hierarchy))
            )
        write_json_file(hierarchy)
        write_md_file(render_to_markdown(hierarchy))
        # df = pd.read_pickle(f"{data_dir}/feature_gate_table.pkl")
        # extract_jira_info_from_table(df)


def write_json_file(hierarchy):
    data_dir = get_env(f"DATA_DIR")
    json_file = f"{data_dir}/jira.json"
    with open(json_file, "w") as f:
        json.dump(hierarchy, f, indent=2)


def write_md_file(md):
    if not md:
        return
    data_dir = get_env("DATA_DIR")
    md_file = f"{data_dir}/jira.md"
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

        # Add epics
        epics = project_data.get("epics", {})
        for epic_key, epic in epics.items():
            if not isinstance(epic, dict):
                print(f"[!] Skipping epic {epic_key} — Invalid structure")
                continue
            md += f"## Epic: {epic_key} — {epic.get('summary', '')}\n"
            md += f"**Description:**\n{epic.get('description', '')}\n\n"
            comments = epic.get("comments", [])
            if comments:
                md += "**Comments:**\n"
                for comment in comments:
                    md += f"- {comment}\n"
                md += "\n"

        # Add stories
        stories = project_data.get("stories", {})
        for story_key, story in stories.items():
            if not isinstance(story, dict):
                print(f"[!] Skipping story {story_key} — Invalid structure")
                continue
            md += f"### Story: {story_key} — {story.get('summary', '')}\n"
            md += f"**Description:**\n{story.get('description', '')}\n\n"
            if "epic_key" in story:
                md += f"**Linked Epic:** {story['epic_key']}\n\n"

        md += "---\n\n"
    return md


def extract_jira_info_from_table(table):
    jira = JiraClient().jira
    projects = set(proj.key for proj in jira.projects())

    if FILTER_ON and filter_out:
        projects = projects.difference(set(filter_out["project"]["key"]))

    feature_gates = filter_enabled_feature_gates(table)
    feature_gates = [fg.split("(", 1)[0].strip() for fg in feature_gates]

    print(f"\n[*] Extracted {len(feature_gates)} feature gates")

    project_clause = ",".join(f"'{p}'" for p in projects)
    start = 0
    maxResults = 1000
    issue_keys, issue_objs = set(), []

    for fg in feature_gates:
        print(
            f"\n[*] Fetching {fg} information in JIRA issues from {len(projects)} projects..."
        )
        jql = f'text ~ "{fg}" AND project in ({project_clause})'
        while True:
            print(f"Running query: {jql}")
            issues = jira.search_issues(
                jql,
                startAt=start,
                maxResults=maxResults,
                fields=[
                    "summary",
                    "key",
                    "description",
                    "issuetype",
                    "project",
                    "parent",
                    "issuelinks",
                ],
            )

            for issue in issues:
                issue_key = str(issue.key)
                if issue_key not in issue_keys:
                    issue_keys.add(issue_key)
                    issue_dict = {
                        "key": issue_key,
                        "summary": str(getattr(issue.fields, "summary", "")),
                        "description": str(
                            getattr(issue.fields, "description", "") or ""
                        ),
                        "issuetype": str(getattr(issue.fields.issuetype, "name", "")),
                        "project": str(getattr(issue.fields.project, "key", "")),
                        "project_name": str(getattr(issue.fields.project, "name", "")),
                    }
                    if issue_dict["issuetype"] not in filter["issuetype"]["name"]:
                        continue
                    issue_objs.append(issue_dict)
            if len(issues) < maxResults:
                break
            start += maxResults

    print(f"[*] Found {len(issue_objs)} JIRA issues")

    print(f"KDEBUG: {issue_objs}")

    matches = fuzzy_match_features_to_jira(feature_gates, jira_issues=issue_objs)

    print(f"[*] Found {len(matches)} matches between feature gates and JIRA issues")

    # Update existing jira.json with new matches
    update_jira_json_with_matches(matches)

    return matches


def update_jira_json_with_matches(matches: List[Dict[str, Any]]) -> None:
    """Update existing jira.json file with fuzzy matching results without losing existing data."""
    import logging

    logger = logging.getLogger(__name__)
    data_dir = get_env("DATA_DIR")
    jira_file = f"{data_dir}/jira.json"

    # Load existing data
    try:
        with open(jira_file, "r") as f:
            existing_data = json.load(f)
    except FileNotFoundError:
        logger.warning(f"JIRA file {jira_file} not found, creating new one")
        existing_data = {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {jira_file}: {e}")
        raise

    logger.info(f"Loaded existing JIRA data with {len(existing_data)} projects")

    # Process matches and merge data
    for match in matches:
        jira_issue = match.get("jira_issue", {})
        issue_key = match.get("jira_key", "")
        project = jira_issue.get("project_name", "Unknown")

        if not issue_key:
            logger.warning(f"Skipping match with empty issue key: {match}")
            continue

        # Ensure project exists in existing data
        if project not in existing_data:
            existing_data[project] = {}

        # Merge issue data without overwriting existing values
        if issue_key in existing_data[project]:
            # Issue exists, merge data without overwriting
            existing_issue = existing_data[project][issue_key]

            # Only add summary if not already present or empty
            if not existing_issue.get("summary"):
                existing_issue["summary"] = jira_issue.get("summary", "")

            # Only add description if not already present or empty
            if not existing_issue.get("description"):
                existing_issue["description"] = jira_issue.get("description", "")

            # Preserve existing stories structure
            if "stories" not in existing_issue:
                existing_issue["stories"] = {}

            logger.debug(f"Merged additional data for existing issue {issue_key}")
        else:
            # New issue, add it with proper structure
            existing_data[project][issue_key] = {
                "summary": jira_issue.get("summary", ""),
                "description": jira_issue.get("description", ""),
                "stories": {},
            }
            logger.debug(f"Added new issue {issue_key} to project {project}")

    # Write updated data back to file
    try:
        with open(jira_file, "w") as f:
            json.dump(existing_data, f, indent=4)
        logger.info(f"Successfully updated {jira_file} with {len(matches)} matches")
    except Exception as e:
        logger.error(f"Failed to write updated JIRA data: {e}")
        raise


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
