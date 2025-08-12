import json
from typing import List, Any
from itertools import islice
from config.settings import AppSettings

from jira import JIRAError, Issue, JIRA
from clients.jira_client import JiraClient
from models.jira_model import create_jira_issue_dict
from scrapers.exceptions import raise_scraper_exception
from utils.utils import contains_valid_keywords
from utils.file_utils import read_pickle_file, write_pickle_file
from config.settings import get_config_loader
from utils.logging_config import get_logger

logger = get_logger(__name__)

FEATURE_FILTER_ON = False
KEYWORD_MATCHING_ON = False


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

    def __init__(
        self,
        settings: AppSettings,
        filter_on: bool = True,
        jira_server: str = None,
        jira_username: str = None,
        jira_password: str = None,
        usernames: List[str] = None,
        issue_ids: List[str] = None,
        urls: List[str] = None,
    ) -> None:
        """
        Initialize JIRA scraper with connection and caching.

        Args:
            filter_on: Whether to apply issue filtering based on configuration
            jira_server: JIRA server URL (overrides default from settings)
            jira_username: JIRA username for authentication
            jira_password: JIRA password for authentication
            usernames: List of usernames to filter by
            issue_ids: List of specific issue IDs to scrape
            urls: List of URLs to scrape from
        """
        self.settings = settings

        def init_jira_client():
            try:
                self.jira_client: JiraClient = JiraClient(
                    jira_server=jira_server or self.settings.api.jira_server,
                    jira_username=self.jira_username or "",
                    jira_password=self.jira_password or "",
                    debug_enabled=self.settings.processing.debug,
                )
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

        def init_caches():
            # Issue cache: prevents re-fetching the same issue multiple times
            # Project cache: stores project metadata for hierarchy building

            # Load project cache using utility function
            self.project_result_cache = (
                read_pickle_file(
                    self.settings.file_paths.project_result_cache_file_path
                )
                or {}
            )

            # Load issue cache using utility function
            self.issue_result_cache = (
                read_pickle_file(self.settings.file_paths.issue_result_cache_file_path)
                or {}
            )

        def init_filtering():
            # Load filtering configuration from JSON files
            # These define which issue types and projects to include/exclude
            self.filter = self.config_loader.get_jira_filter()
            self.filter_out = self.config_loader.get_jira_filter_out()

        self.filter_on = filter_on
        self.jira_server = jira_server
        self.jira_username = jira_username
        self.jira_password = jira_password
        self.usernames = usernames or []
        self.issue_ids = issue_ids or []
        self.urls = urls or []
        self.config_loader = get_config_loader()

        init_jira_client()
        init_caches()
        init_filtering()

        try:
            unauth_keys = self.config_loader.load_json_config(
                "unauthorized_jira_keys.json"
            )
        except (FileNotFoundError, ValueError):
            unauth_keys = []

        self.unauthorized_keys = set(unauth_keys)

        if self.usernames:
            logger.info(f"Extracting issue IDs from {len(self.usernames)} usernames")
            logger.debug(f"Usernames: {self.usernames}")
            found_ids = self.get_issues_assigned_to_usernames(self.usernames)
            logger.debug(f"Found {len(found_ids)} issues for usernames")
            self.issue_ids.extend(found_ids)

        if self.urls:
            logger.info(f"Extracting issue IDs from {len(self.urls)} URLs")
            self.issue_ids.extend(self.get_issue_ids_from_urls(self.urls))

        self.issue_ids = list(set(self.issue_ids))
        logger.debug(f"Total unique issue IDs found: {len(self.issue_ids)}")

    def get_config(self) -> dict[str, Any]:
        """
        Get the configuration for the JIRA scraper.
        """
        return {
            "filter_on": self.filter_on,
            "jira_client": self.jira_client.get_config(),
            "usernames": self.usernames,
            "issue_ids": self.issue_ids,
            "urls": self.urls,
        }

    def validate_jira_url(self, url: str) -> bool:
        """Validate that URL is a proper JIRA issue browse URL."""
        return "browse/" in url

    def get_issues_assigned_to_usernames(self, usernames: List[str]) -> List[str]:
        """
        Fetch JIRA issues assigned to a list of usernames.
        """
        if not usernames:
            logger.error("[!][ERROR] No usernames provided")
            return []

        usernames = list(set(u for u in usernames if u))
        issue_ids = set()

        # For Red Hat Jira, we need to search in both assignee and reporter fields
        # Using single quotes for JQL values
        quoted_usernames = ",".join(f"'{u}'" for u in usernames)
        jql_query = (
            f"assignee IN ({quoted_usernames}) OR reporter IN ({quoted_usernames})"
        )

        start_at = 0
        max_results = 50

        while True:
            try:
                logger.debug(
                    f"Searching with startAt={start_at}, maxResults={max_results}"
                )
                logger.debug(f"JQL Query: {jql_query}")
                issues = self.jira.search_issues(
                    jql_str=jql_query,
                    startAt=start_at,
                    maxResults=max_results,
                    fields="key,issuetype",
                )
                logger.debug(f"Found {len(issues)} issues at offset {start_at}")
                for issue in issues:
                    logger.debug(
                        f"Found issue {issue.key} of type {issue.fields.issuetype.name}"
                    )
                    issue_ids.add(issue.key)

                if not issues:
                    logger.debug("No more issues found")
                    break

                if len(issues) < max_results:
                    logger.debug("Got less results than max, stopping pagination")
                    break

                start_at += max_results
            except JIRAError as e:
                logger.error(f"JIRA Error searching issues: {e}")
                logger.error(f"Status code: {getattr(e, 'status_code', 'N/A')}")
                logger.error(f"Error text: {getattr(e, 'text', str(e))}")
                logger.error(f"JQL Query that failed: {jql_query}")
                break
            except Exception as e:
                logger.error(f"Error searching issues: {e}")
                logger.error(f"Full error details: {str(e)}")
                logger.error(f"JQL Query that failed: {jql_query}")
                break

            issue_ids.update(issue.key for issue in issues)
            if len(issues) < max_results:
                break
            start_at += max_results

        return list(issue_ids)

    def get_issue_ids_from_urls(self, urls: List[str]) -> List[str]:
        """
        Extract JIRA issue IDs from a list of URLs.
        """
        issue_ids = set()
        for url in urls:
            if self.validate_jira_url(url):
                parts = url.strip().split("browse/")
                if len(parts) > 1 and parts[1]:
                    # Extract issue ID and handle potential suffixes
                    issue_id = parts[1].split("_")[0]
                    if issue_id:
                        issue_ids.add(issue_id)
        return list(issue_ids)

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
                self.project_result_cache[project_key] = self.jira.project(project_key)
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
                        self.issue_result_cache[issue_id] = [self.jira.issue(issue_id)]
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

    def extract(self) -> None:
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
                    vars(fields).values(), invalid_keywords=self.invalid_keywords
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

        logger.info(f"[*] Extracting {len(self.issue_ids)} JIRA tickets")
        logger.debug(f"FILTER IS {'ON' if self.filter_on else 'OFF'}")

        issue_ids = self.issue_ids
        if not issue_ids and not self.usernames and not self.urls:
            logger.debug("No issue IDs, usernames, or URLs provided")
            raise_scraper_exception(
                "[!][ERROR] No input provided - please specify issue IDs, usernames, or URLs"
            )
        elif not issue_ids and self.urls:
            logger.debug("No issues found for the provided URLs")
            logger.debug(f"URLs that returned no results: {self.urls}")
            raise_scraper_exception("[!][ERROR] Invalid JIRA issue IDs")
        elif not issue_ids and self.usernames:
            logger.debug("No issues found for the provided usernames")
            logger.debug(f"Usernames that returned no results: {self.usernames}")
            raise_scraper_exception(
                "[!][ERROR] No issues found for the provided usernames"
            )

        project_ids = [id.split("-")[0] for id in issue_ids]
        self.populate_project_result_cache(project_ids)

        issues = self.search_issues(issue_ids)
        if not issues:
            raise_scraper_exception("[!][ERROR] No JIRA issues found")

        logger.debug(f"\nFetched {len(issues)}/{len(issue_ids)} JIRA issues")

        # Report any issues that failed to fetch (permissions, deleted, etc.)
        if len(issues) < len(issue_ids):
            failed_issue_ids = set(issue_ids) - set(issue.key for issue in issues)
            logger.warning(
                f"{len(failed_issue_ids)} Issue IDs failed fetched: {failed_issue_ids}"
            )

        # Build the hierarchical structure
        hierarchy = organize_issues(issues, self.jira_client.epic_link_field_id)
        if not hierarchy:
            raise_scraper_exception("[!][ERROR] JIRA Hierarchy construction failed")

        with open(self.settings.file_paths.unauthorized_jira_keys_file_path, "w") as f:
            json.dump(list(self.unauthorized_keys), f, indent=2)
        with open(self.settings.file_paths.jira_json_file_path, "w") as f:
            json.dump(hierarchy, f, indent=2)
        with open(self.settings.file_paths.jira_md_file_path, "w") as f:
            f.write(render_to_markdown(hierarchy))
        write_pickle_file(
            self.settings.file_paths.project_result_cache_file_path,
            self.project_result_cache,
        )
        write_pickle_file(
            self.settings.file_paths.issue_result_cache_file_path,
            self.issue_result_cache,
        )


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


def extract_jira_ids(md):
    import re

    return re.findall(r"\b[A-Z][A-Z0-9]+-\d+\b", md)
