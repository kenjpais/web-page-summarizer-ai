import re
import json
import pandas as pd
from pathlib import Path
from scrapers.jira_scraper import extract_jira_ids
from filters.filter_enabled_feature_gates import filter_enabled_feature_gates
from summarizers.summarizer import summarize_feature_gates
from config.settings import get_settings
from utils.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Configuration paths for input and output files
data_dir = Path(settings.directories.data_dir)
correlated_file = data_dir / "correlated.json"
non_correlated_file = data_dir / "non_correlated.json"
jira_file_path = data_dir / "jira.json"
github_file_path = data_dir / "github.json"
table_file = data_dir / "feature_gate_table.pkl"
correlated_table_file = data_dir / "correlated_feature_gate_table.json"
correlated_table_md_file = data_dir / "correlated_feature_gate_table.md"


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

    index = {}
    src_path = data_directory / "github.json"
    with open(src_path, "r") as srcfile:
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
        output_correlated_file = correlated_file
    if output_non_correlated_file is None:
        output_non_correlated_file = non_correlated_file

    # Determine which sources to correlate (exclude JIRA since it's the base)
    all_sources = settings.processing.sources
    sources = [
        src
        for src in all_sources
        if src != "JIRA" and src in get_src_index_builder_map(data_directory)
    ]

    # Load the JIRA hierarchy structure
    jira_path = data_directory / "jira.json"
    with open(jira_path, "r") as jira_file:
        jira = json.load(jira_file)

    # Build index mappings for fast lookups
    src_index_map = {
        src: get_src_index_builder_map(data_directory)[src]() for src in sources
    }

    non_correlated = []

    for _, project in jira.items():
        jira_artifacts = []
        for key in ("epics", "features", "stories"):
            issues = project.get(key)
            if issues:
                jira_artifacts.append(issues)

        for jira_artifact in jira_artifacts:
            for jira_key, jira_item in jira_artifact.items():
                matched = False

                # Check each source for items referencing this JIRA issue
                for src in sources:
                    matched_items = src_index_map[src].get(jira_key, [])
                    if matched_items:
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

    # Write outputs for analysis and downstream processing
    with open(output_non_correlated_file, "w") as file:
        json.dump(non_correlated, file, indent=4)

    with open(output_correlated_file, "w") as file:
        json.dump(jira, file, indent=4)


def correlate_table():
    """
    Correlate feature gate information with JIRA/GitHub data.

    This secondary correlation links OpenShift feature gates with related
    development work. Feature gates are configuration flags that enable/disable
    features, and this correlation helps understand what development work
    relates to specific features.

    Process:
    1. Load feature gate table and extract enabled gates
    2. Search correlated JIRA/GitHub data for feature gate mentions
    3. Create mappings between feature gates and related work items
    4. Handle unknown feature gates by searching raw source data
    5. Generate final correlation results

    The correlation finds feature gate references
    in issue summaries, descriptions, and commit messages.
    """
    # Load and process feature gate data
    df = pd.read_pickle(table_file)

    # Handle case where pickle contains a Series instead of DataFrame
    if isinstance(df, pd.Series):
        df = df.to_frame()

    # Extract the list of enabled feature gates for correlation
    feature_gates = set(filter_enabled_feature_gates(df))

    logger.debug(
        f"Identified feature_gates: {json.dumps(list(feature_gates), indent=4)}"
    )

    # Load the correlated JIRA/GitHub data
    with open(correlated_file, "r") as f:
        correlated = json.load(f)

    result = {}

    def match_feature_gate(feature_gate: str, value):
        """
        Check if a feature gate is mentioned in a text value.

        Uses case-insensitive substring matching to find feature gate
        references in various text fields.
        """
        return isinstance(value, str) and feature_gate.lower() in value.lower()

    def update_result(result, feature_gate, value, issue):
        """
        Helper to add feature gate matches to results.
        """
        if match_feature_gate(feature_gate, value):
            result.setdefault(feature_gate, []).append(issue)

    # Search through correlated data for feature gate mentions
    for feature_gate in feature_gates:
        for project in correlated.values():
            for issue_type_dict in project.values():
                if not isinstance(issue_type_dict, dict):
                    continue
                for issue in issue_type_dict.values():
                    # Search JIRA issue content for feature gate mentions
                    for issue_value in issue.values():
                        if isinstance(issue_value, list):
                            # Handle GitHub items attached to JIRA issues
                            for src_dict in issue_value:
                                if isinstance(src_dict, dict):
                                    for src_value in src_dict.values():
                                        update_result(
                                            result, feature_gate, src_value, issue
                                        )
                        else:
                            # Handle direct JIRA issue fields
                            update_result(result, feature_gate, issue_value, issue)

    # Identify feature gates that weren't found in correlated data
    known_feature_gates = set(result.keys())
    unknown_feature_gates = feature_gates.difference(known_feature_gates)
    logger.debug(f"Identified unknown_feature_gates: {unknown_feature_gates}")

    # Search raw source data for unknown feature gates
    # This catches cases where feature gates are mentioned in items
    # that weren't correlated with JIRA issues
    sources = settings.processing.sources
    sources = [s for s in sources if s != "JIRA"]

    for fg in unknown_feature_gates:
        for src in sources:
            with open(data_dir / f"{src}.json") as f:
                src_data = json.load(f)
            for data in src_data:
                if isinstance(data, dict):
                    for value in data.values():
                        if match_feature_gate(fg, value):
                            result.setdefault(fg, []).append(data)

    # Final check for remaining unknown feature gates
    known_feature_gates = set(result.keys())
    unknown_feature_gates = feature_gates.difference(known_feature_gates)
    logger.debug(f"Identified: unknown_feature_gates: {unknown_feature_gates}")

    with open(correlated_table_file, "w") as f:
        json.dump(result, f, indent=4)

    summarized_features = json.loads(summarize_feature_gates(result))

    print(f"KDEBUG: {summarized_features}")

    for feature_name, summary in summarized_features.items():
        project_names = result.get(feature_name, {}).get("projects", [])
        for project_name in project_names:
            if "feature_summaries" not in correlated[project_name]:
                correlated[project_name]["feature_summaries"][feature_name] = summary

    with open(correlated_file, "w") as f:
        json.dump(correlated, f)


def convert_json_to_markdown(data: dict) -> str:
    """
    Convert feature gate correlation data to readable Markdown.

    Args:
        data: Dictionary mapping feature gates to related work items

    Returns:
        Formatted Markdown string with hierarchical organization
    """

    def format_description(text):
        # Convert wiki-style formatting to markdown
        text = re.sub(r"\{\{(.*?)\}\}", r"`\1`", text)  # {{feature}} → `feature`
        text = re.sub(r"\*(.*?)\*", r"**\1**", text)  # *bold* → **bold**
        text = re.sub(
            r"\[([^\|]+)\|([^\]]+)\]", r"[\1](\2)", text
        )  # [text|url] → [text](url)
        return text.strip()

    lines = []
    for feature_gate, issues in data.items():
        lines.append(f"## {feature_gate}\n")
        for idx, issue in enumerate(issues, 1):
            lines.append(f"### {idx}. {issue.get('summary', 'No summary')}\n")

            # Show epic relationships for context
            if "epic_key" in issue:
                lines.append(f"**Epic**: `{issue['epic_key']}`\n")

            # Include formatted descriptions
            if "description" in issue:
                lines.append(
                    f"**Description:**\n\n{format_description(issue['description'])}\n"
                )

            # Show related GitHub items
            for src, entries in issue.items():
                if src == "GITHUB":
                    lines.append(f"**GitHub Items:**\n")
                    for entry in entries:
                        lines.append(
                            f"- **[{entry.get('title')}]** (ID: {entry.get('id')})\n"
                        )
                        if entry.get("body"):
                            lines.append(f"  - {entry['body'].strip()}\n")
        lines.append("\n---\n")  # Feature gate separator

    return "\n".join(lines)


def correlate_all(
    data_directory=None, output_correlated_file=None, output_non_correlated_file=None
):
    """
    Execute the complete correlation pipeline.

    This orchestrates all correlation steps:
    1. JIRA-to-source correlation (GitHub items referencing JIRA issues)
    2. Feature gate correlation (development work related to feature flags)

    Args:
        data_directory: Optional Path object for data directory. Defaults to global data_dir.
        output_correlated_file: Optional Path object for correlated output file. Defaults to global correlated_file.
        output_non_correlated_file: Optional Path object for non-correlated output file. Defaults to global non_correlated_file.
    """
    # Step 1: Correlate JIRA issues with GitHub items
    correlate_with_jira_issue_id(
        data_directory, output_correlated_file, output_non_correlated_file
    )

    # Note: These steps are currently disabled but preserved for future use:
    # remove_irrelevant_fields_from_correlated() - Clean up unnecessary data
    # filter_jira_issue_ids(correlated_file) - Apply additional filtering

    # Step 2: Correlate with feature gate information
    correlate_table()


src_index_builder_map = get_src_index_builder_map()
