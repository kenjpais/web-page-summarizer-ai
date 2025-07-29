import json
from scrapers.jira_scraper import extract_jira_ids
from config.settings import get_settings
from utils.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Configuration paths for input and output files
data_dir = settings.directories.data_dir


def build_github_item_index(data_directory=None):
    """
    Build an index mapping JIRA issue IDs to related GitHub items.

    Args:
        data_directory: Optional override for data directory path

    Returns:
        Dictionary mapping JIRA issue IDs to lists of related GitHub items.
    """
    if data_directory is None:
        data_directory = data_dir

    github_file_path = data_directory / "github.json"

    index = {}
    with open(github_file_path, "r") as srcfile:
        github = json.load(srcfile)

    for item in github:
        title = item.get("title", "")
        # Extract JIRA IDs from GitHub titles using regex pattern matching
        jira_ids = extract_jira_ids(title)
        if jira_ids:
            # Use the first JIRA ID found as the primary correlation key
            # This handles cases like "Fix OCPBUGS-123 and STOR-456"
            first_key = jira_ids[0]
            index.setdefault(first_key, []).append(item)
    return index


def get_src_index_builder_map(data_directory=None):
    """
    Registry of index builders for different source types.

    This extensible pattern allows adding new source types (e.g., GitLab, Bitbucket)
    without modifying the core correlation logic.

    Args:
        data_directory: Optional override for data directory path

    Returns:
        Dictionary mapping source names to their index builder functions
    """
    return {"GITHUB": lambda: build_github_item_index(data_directory)}


src_index_builder_map = get_src_index_builder_map()


def correlate_with_jira_issue_id(
    data_directory=None, output_correlated_file=None, output_non_correlated_file=None
):
    """
    Correlate JIRA issues with related items from other sources using issue IDs.

    This is the core correlation process that links JIRA issues with GitHub
    items based on JIRA issue IDs mentioned in GitHub titles. The process:

    1. Load JIRA hierarchy structure
    2. Build index mappings for all configured sources
    3. For each JIRA issue, find related items in other sources
    4. Attach related items to the JIRA issue structure
    5. Track items that couldn't be correlated for analysis

    The correlation creates an enriched JIRA structure where each issue may
    contain additional data from GitHub (PRs, commits) that reference it.

    Args:
        data_directory: Optional override for data directory path
        output_correlated_file: Output path for correlated data
        output_non_correlated_file: Output path for items that couldn't be linked
    """
    logger.info("\n[*] Correlating feature-related items by JIRA 'id' ...")

    if data_directory is None:
        data_directory = data_dir

    if output_correlated_file is None:
        output_correlated_file = data_directory / "correlated.json"
    if output_non_correlated_file is None:
        output_non_correlated_file = data_directory / "non_correlated.json"

    jira_file_path = data_directory / "jira.json"

    all_sources = settings.processing.sources
    sources = [
        src
        for src in all_sources
        if src != "JIRA" and src in get_src_index_builder_map(data_directory)
    ]

    # Load the JIRA hierarchy structure
    with open(jira_file_path, "r") as jira_file:
        jira = json.load(jira_file)

    # Build index mappings for fast lookups
    src_index_map = {
        src: get_src_index_builder_map(data_directory)[src]() for src in sources
    }

    non_correlated = []

    for project in jira.values():
        for jira_artifact in project.values():
            if not isinstance(jira_artifact, dict):
                # Skip summary, description fields
                continue
            for jira_key, jira_item in jira_artifact.items():
                matched = False

                # Check each source for items referencing this JIRA issue
                for src in sources:
                    if matched_items := src_index_map[src].get(jira_key, []):
                        matched = True
                        # Add the matched items to the JIRA issue structure
                        if src not in jira_item:
                            jira_item[src] = []
                        if isinstance(matched_items, list):
                            jira_item[src].extend(matched_items)
                        else:
                            jira_item[src].append(matched_items)

                # Track issues that couldn't be correlated for analysis
                if not matched:
                    non_correlated.append(jira_item)

    with open(output_non_correlated_file, "w") as file:
        json.dump(non_correlated, file, indent=4)

    with open(output_correlated_file, "w") as file:
        json.dump(jira, file, indent=4)
