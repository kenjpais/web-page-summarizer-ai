import re
import json
import pickle
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

# Feature flags for different processing modes
FILTER_ON = settings.processing.filter_on  # Enable/disable issue filtering
FEATURE_FILTER_ON = False  # Feature-specific filtering (currently disabled)
KEYWORD_MATCHING_ON = False  # Content-based keyword filtering (currently disabled)

data_dir = settings.directories.data_dir


class JiraScraper:
    """
    JIRA scraper that extracts, filters, and organizes JIRA issues into a hierarchical structure.

    Key Features:
    - Multi-level caching for performance (issues and projects)
    - Configurable filtering based on issue types and projects
    - Hierarchical organization (Project -> Issue Type -> Individual Issues)
    - Recursive linking of related issues (epics, features, etc.)
    - Batched API calls to handle rate limits
    - Markdown generation for readable reports
    """

    def __init__(self, filter_on: bool = FILTER_ON) -> None:
        """
        Initialize JIRA scraper with connection and caching.

        Args:
            filter_on: Whether to apply issue filtering based on configuration
        """
        data_dir.mkdir(exist_ok=True)
        self.filter_on = filter_on

        try:
            # Initialize JIRA client with error handling
            self.jira_client: JiraClient = JiraClient()
            if not self.jira_client:
                raise_scraper_exception(
                    f"[!][ERROR] JiraClient() is {self.jira_client}"
                )

            self.jira: JIRA = self.jira_client.jira

            # Find the custom "feature" field by scanning all available fields
            # This field links issues to features and varies by JIRA instance
            self.feature_field_id: str = ""
            for field in self.jira.fields():
                if "feature" in field["name"].lower():
                    self.feature_field_id = field["id"]

        except JIRAError as e:
            raise_scraper_exception(
                f'[!][ERROR] Failed to connect to JIRA Server: {getattr(e, "status_code", "N/A")} - {getattr(e, "text", str(e))}'
            )
        except Exception as e:
            raise_scraper_exception(f"[!][ERROR] Unexpected error: {e}")

        # Load filtering configuration from JSON files
        # These define which issue types and projects to include/exclude
        self.filter = config_loader.get_jira_filter()
        self.filter_out = config_loader.get_jira_filter_out()

        # Initialize caches for performance
        # Issue cache: prevents re-fetching the same issue multiple times
        # Project cache: stores project metadata for hierarchy building
        self.issue_result_cache = {}
        self.project_result_cache = {}

        try:
            with open(data_dir / "project_result_cache.pkl", "rb") as f:
                self.project_result_cache = pickle.load(f)
            with open(data_dir / "issue_result_cache.pkl", "rb") as f:
                self.issue_result_cache = pickle.load(f)
        except FileNotFoundError:
            pass

        try:
            unauth_keys = config_loader.load_json_config("unauthorized_jira_keys.json")
        except (FileNotFoundError, ValueError):
            unauth_keys = []

        self.unauthorized_keys = set(unauth_keys)

    def validate_jira_url(self, url: str) -> bool:
        """Validate that URL is a proper JIRA issue browse URL."""
        return "browse/" in url

    def filter_pass(self, jira_issue: Issue) -> bool:
        """
        Determine if a JIRA issue passes the configured filters.

        Filtering criteria:
        1. Issue type must be in the allowed list (e.g., Epic, Story, Bug)
        2. Issue type ID must not be in the blocked list
        3. Project key must not be in the blocked projects list

        This helps focus on relevant issues and exclude test/internal projects.

        Args:
            jira_issue: JIRA Issue object to evaluate

        Returns:
            True if issue passes all filters, False otherwise
        """
        return (
            jira_issue.issuetype.name in self.filter["issuetype"]["name"]
            and jira_issue.issuetype.name not in self.filter_out["issuetype"]["name"]
            and jira_issue.issuetype.id not in self.filter_out["issuetype"]["id"]
            and getattr(jira_issue.project, "key", "")
            not in self.filter_out["project"]["key"]
        )

    def search_project(self, project_key: str) -> Any:
        """
        Fetch JIRA project information with caching.

        Projects contain metadata like summary and description that provide
        context for the issues within them.

        Args:
            project_key: JIRA project key (e.g., "OCPBUGS")

        Returns:
            JIRA Project object
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
        Pre-populate project cache for efficiency.

        Fetches all needed projects in one batch operation rather than
        making individual API calls during hierarchy building.

        Args:
            project_keys: List of project keys to cache
        """
        desired_keys = set(project_keys)
        projects = self.jira.projects()
        self.project_result_cache = {
            p.key: p for p in projects if p.key in desired_keys
        }

    def search_issues(self, issue_ids: List[str]) -> List[Issue]:
        """
        Fetch JIRA issues using batched queries for performance.

        JIRA API has limitations on query complexity and result size,
        so this implementation:
        1. Handles single vs. multiple issue queries differently
        2. Uses caching to avoid re-fetching
        3. Batches large requests to stay within API limits
        4. Gracefully handles API errors

        Args:
            issue_ids: List of JIRA issue keys (e.g., ["OCPBUGS-123", "STOR-456"])

        Returns:
            List of JIRA Issue objects that were successfully fetched
        """

        def run_query(issue_ids):
            """
            Execute a JQL query to fetch issue details.

            For single issues, uses the simpler issue() API.
            For multiple issues, uses search_issues() with JQL.
            """
            if len(issue_ids) == 1 and issue_ids[0] in self.unauthorized_keys:
                return []

            try:
                if len(issue_ids) == 1:
                    issue_id = issue_ids[0]
                    if issue_id not in self.issue_result_cache:
                        self.issue_result_cache[issue_id] = [
                            self.jira_client.jira.issue(issue_id)
                        ]
                    return self.issue_result_cache[issue_id]

                # For multiple issues, use JQL search
                return list(
                    self.jira.search_issues(
                        f"issuekey in ({','.join(issue_ids)})",
                        fields=f"summary,description,issuetype,parent,project,issuelinks,{self.jira_client.epic_link_field_id}",
                        use_post=True,  # Use POST for large query strings
                        maxResults=len(issue_ids),
                    )
                )
            except JIRAError as je:
                logger.error(f"[JIRAError] Failed JIRA fetch: {je}")
                if len(issue_ids) == 1 and int(je.status_code) in (401, 403, 407):
                    self.unauthorized_keys.add(issue_ids[0])
                    logger.error(f"Unauthorized JIRA key: {issue_ids[0]}")
                return []
            except Exception as e:
                logger.error(f"[!][ERROR] Failed JIRA fetch: {e}")
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
        batch_size = 500  # JIRA API limit for batch operations
        issue_id_iter = iter(issue_ids)

        # Process issues in batches to stay within API limits
        for i, chunk in enumerate(chunked(issue_id_iter, batch_size)):
            issue_chunk = run_query(chunk)
            issues.extend(issue_chunk)
            if len(issue_ids) > 1:
                logger.debug(f"Chunk[{i}]: Fetched: {len(issue_chunk)}")

        return issues

    def extract(self, urls):
        """
        Main extraction method that orchestrates the entire JIRA scraping process.

        Process:
        1. Parse URLs to extract JIRA issue IDs
        2. Validate URLs and filter valid ones
        3. Fetch issues and related data via API
        4. Organize issues into hierarchical structure
        5. Write results to JSON and Markdown files

        Args:
            urls: List of JIRA browse URLs to process
        """

        def organize_issues(issues, epic_link_field_id):
            """
            Organize JIRA issues into a hierarchical structure for analysis.

            Creates a nested structure:
            Project -> Issue Type (epics/stories/bugs/etc.) -> Individual Issues

            This organization reflects the natural JIRA hierarchy and makes it easier
            to understand relationships between different types of work items.

            The function also handles:
            - Recursive linking (epics link to stories, features link to issues)
            - Filtering based on configuration
            - Keyword matching for relevance
            - Duplicate detection via visited_keys tracking

            Args:
                issues: List of JIRA Issue objects to organize
                epic_link_field_id: Custom field ID for epic links

            Returns:
                Nested dictionary representing the issue hierarchy
            """
            hierarchy = {}
            visited_keys = set()  # Prevent processing the same issue multiple times

            def add_issue(issue, hierarchy):
                """
                Recursively add a JIRA issue and its linked issues to the hierarchy.

                This function is the core of the organization logic. It:
                1. Validates the issue structure
                2. Handles project setup
                3. Applies filtering rules
                4. Places issues in the correct hierarchy level
                5. Recursively processes linked issues (epics, features)
                """
                if not issue or not hasattr(issue, "fields"):
                    raise ValueError("[!][ERROR] Invalid issue")

                fields = issue.fields

                def add_project(project_key, project_name, hierarchy):
                    """
                    Add project metadata to hierarchy if not already present.

                    Projects provide important context (summary, description)
                    that helps understand the overall scope of work.
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
                    Find and recursively add feature-linked issues.

                    Features can be linked via:
                    1. Custom feature fields (varies by JIRA instance)
                    2. Issue links with specific relationship types

                    This ensures we capture the full feature scope, not just
                    the directly mentioned issues.
                    """
                    feature_issue_keys = set()

                    # Get valid feature link types from configuration
                    if self.filter:
                        issuelinks_types = self.filter.get("issuelinks", {}).get(
                            "type", {}
                        )
                        inward_link_types = issuelinks_types.get("inward", {})
                        outward_link_types = issuelinks_types.get("outward", {})
                        feature_link_types = set(inward_link_types).union(
                            outward_link_types
                        )

                    # Check custom feature field
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

                    # Check issue links for feature relationships
                    for link in getattr(fields, "issuelinks", []):
                        if (
                            hasattr(link, "type")
                            and link.type.name.lower() in feature_link_types
                        ):
                            if hasattr(link, "inwardIssue"):
                                feature_issue_keys.add(link.inwardIssue.key)
                            elif hasattr(link, "outwardIssue"):
                                feature_issue_keys.add(link.outwardIssue.key)

                    # Recursively process feature issues
                    if feature_issue_keys and (
                        feature_issues := self.search_issues(list(feature_issue_keys))
                    ):
                        for feature_issue in feature_issues:
                            add_issue(feature_issue, hierarchy)

                # Prevent infinite recursion and duplicate processing
                if issue.key in visited_keys:
                    return
                visited_keys.add(issue.key)

                # Extract project information
                project_key = getattr(fields.project, "key", "")
                project_name = getattr(fields.project, "name", "")
                if not project_name or not project_key:
                    return

                # Apply filtering if enabled
                if self.filter_on and not self.filter_pass(fields):
                    logger.debug(f"Issue [{issue.key}] failed filter pass")
                    return

                # Apply keyword matching if enabled (currently disabled)
                if KEYWORD_MATCHING_ON and not contains_valid_keywords(
                    vars(fields).values()
                ):
                    logger.debug(f"Issue [{issue.key}] failed keyword match")
                    return

                # Set up project in hierarchy
                add_project(project_key, project_name, hierarchy)

                if issue_type := getattr(fields.issuetype, "name", "").lower():
                    issue_type_key = (
                        "stories" if issue_type == "story" else f"{issue_type}s"
                    )
                    if issue_type_key not in hierarchy[project_name]:
                        hierarchy[project_name][issue_type_key] = {}

                    # Add the issue to the hierarchy
                    if issue_dict := create_jira_issue_dict(issue):
                        hierarchy[project_name][issue_type_key][issue.key] = issue_dict

                    # Handle epic-story relationships
                    if epic_link_field_id and (
                        epic_key := getattr(fields, epic_link_field_id, None)
                    ):
                        hierarchy[project_name][issue_type_key][issue.key][
                            "epic_key"
                        ] = epic_key
                        # Recursively fetch and add the linked epic
                        if epic := self.search_issues([epic_key]):
                            add_issue(epic[0], hierarchy)

                    # Recursively add feature-linked issues
                    add_feature_issues(fields, hierarchy)

            # Process all issues through the hierarchy builder
            for issue in issues:
                add_issue(issue, hierarchy)

            return hierarchy

        logger.debug(f"FILTER IS {'ON' if self.filter_on else 'OFF'}")

        # Parse JIRA issue IDs from URLs
        issue_ids = set()
        for url in urls:
            if self.validate_jira_url(url):
                parts = url.strip().split("browse/")
                if len(parts) > 1 and parts[1]:
                    # Extract issue ID and handle potential suffixes
                    issue_id = parts[1].split("_")[0]
                    if issue_id:
                        issue_ids.add(issue_id)

        if not issue_ids:
            raise_scraper_exception("[!][ERROR] Invalid JIRA URLs")

        logger.info(f"[*] Extracted {len(issue_ids)} Issue IDs")

        # Pre-populate project cache for efficiency
        self.populate_project_result_cache([id.split("-")[0] for id in issue_ids])

        # Fetch all issues via API
        issues = self.search_issues(list(issue_ids))
        if not issues:
            raise_scraper_exception("[!][ERROR] No JIRA issues found")

        logger.debug(f"\nFetched {len(issues)} JIRA issues")

        # Report any issues that failed to fetch (permissions, deleted, etc.)
        if len(issues) < len(issue_ids):
            failed_issue_ids = issue_ids - set(issue.key for issue in issues)
            logger.warning(
                f"{len(failed_issue_ids)} Issue IDs failed fetched: {failed_issue_ids}"
            )

        # Build the hierarchical structure
        hierarchy = organize_issues(issues, self.jira_client.epic_link_field_id)
        if not hierarchy:
            raise_scraper_exception("[!][ERROR] JIRA Hierarchy construction failed")

        save_unauthorized_keys(self.unauthorized_keys)
        save_project_result_cache(self.project_result_cache)
        save_issue_result_cache(self.issue_result_cache)

        # Write results in both JSON (for processing) and Markdown (for humans)
        write_json_file(hierarchy)
        write_md_file(render_to_markdown(hierarchy))


def save_unauthorized_keys(keys):
    with open(
        Path(settings.directories.config_dir) / "unauthorized_jira_keys.json", "w"
    ) as f:
        json.dump(list(keys), f)


def save_issue_result_cache(cache):
    with open(data_dir / "issue_result_cache.pkl", "wb") as f:
        pickle.dump(cache, f)


def save_project_result_cache(cache):
    with open(data_dir / "project_result_cache.pkl", "wb") as f:
        pickle.dump(cache, f)


def write_json_file(hierarchy):
    """Write JIRA hierarchy to JSON file for downstream processing."""
    json_file = data_dir / "jira.json"
    with open(json_file, "w") as f:
        json.dump(hierarchy, f, indent=2)


def write_md_file(md):
    """Write JIRA data to Markdown file for human readability."""
    if not md:
        return
    md_file = data_dir / "jira.md"
    with open(md_file, "w") as f:
        f.write(md)


def extract_jira_ids(md):
    """Extract JIRA issue IDs from text using regex pattern matching."""
    return re.findall(r"\b[A-Z][A-Z0-9]+-\d+\b", md)


def render_to_markdown(hierarchy):
    """
    Convert JIRA hierarchy to human-readable Markdown format.

    Creates a structured document with:
    - Project-level organization
    - Issue type groupings (Epics, Stories, Bugs, etc.)
    - Proper hierarchical headers
    - Issue metadata (summaries, descriptions, comments)
    - Cross-references between linked issues

    Args:
        hierarchy: Nested dictionary representing JIRA issue organization

    Returns:
        String containing formatted Markdown document
    """
    md = ""
    for project, project_data in hierarchy.items():
        md += f"# Project: {project}\n\n"
        md += f"**Summary**: {project_data.get('summary', '')}\n\n"
        md += f"**Description**: {project_data.get('description', '')}\n\n"

        # Process all issue types dynamically to handle various JIRA configurations
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

                # Format headers based on issue type hierarchy
                # Epics are primary (##), others are secondary (###)
                if issue_type == "epics":
                    md += f"## Epic: {issue_key} — {issue.get('summary', '')}\n"
                elif issue_type == "stories":
                    md += f"### Story: {issue_key} — {issue.get('summary', '')}\n"
                else:
                    # Handle plural to singular conversion for clean headers
                    issue_type_singular = (
                        issue_type.rstrip("s")
                        if issue_type.endswith("s")
                        else issue_type
                    )
                    md += f"### {issue_type_singular.title()}: {issue_key} — {issue.get('summary', '')}\n"

                md += f"**Description:**\n{issue.get('description', '')}\n\n"

                # Add comments if available for additional context
                comments = issue.get("comments", [])
                if comments:
                    md += "**Comments:**\n"
                    for comment in comments:
                        md += f"- {comment}\n"
                    md += "\n"

                # Show epic relationships for non-epic issues
                if issue_type != "epics" and "epic_key" in issue:
                    md += f"**Linked Epic:** {issue['epic_key']}\n\n"

        md += "---\n\n"  # Project separator
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
