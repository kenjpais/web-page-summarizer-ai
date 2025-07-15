import re
import json
import pandas as pd
from pathlib import Path
from scrapers.jira_scraper import extract_jira_ids
from filters.filter_enabled_feature_gates import filter_enabled_feature_gates
from config.settings import get_settings
from utils.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Configuration
data_dir = Path(settings.directories.data_dir)
correlated_file = data_dir / "correlated.json"
non_correlated_file = data_dir / "non_correlated.json"
jira_file_path = data_dir / "jira.json"
github_file_path = data_dir / "github.json"
table_file = data_dir / "feature_gate_table.pkl"
correlated_table_file = data_dir / "correlated_feature_gate_table.json"
correlated_table_md_file = data_dir / "correlated_feature_gate_table.md"


def build_github_item_index(data_directory=None):
    if data_directory is None:
        data_directory = data_dir

    index = {}
    src_path = data_directory / "github.json"
    with open(src_path, "r") as srcfile:
        github = json.load(srcfile)

    for item in github:
        title = item.get("title", "")
        jira_ids = extract_jira_ids(title)
        if jira_ids:
            first_key = jira_ids[0]
            index.setdefault(first_key, []).append(item)
    return index


def get_src_index_builder_map(data_directory=None):
    return {"GITHUB": lambda: build_github_item_index(data_directory)}


def correlate_with_jira_issue_id(
    data_directory=None, output_correlated_file=None, output_non_correlated_file=None
):
    logger.info("\n[*] Correlating feature-related items by JIRA 'id' ...")

    if data_directory is None:
        data_directory = data_dir
    if output_correlated_file is None:
        output_correlated_file = correlated_file
    if output_non_correlated_file is None:
        output_non_correlated_file = non_correlated_file

    all_sources = settings.processing.sources
    sources = [
        src
        for src in all_sources
        if src != "JIRA" and src in get_src_index_builder_map(data_directory)
    ]

    jira_path = data_directory / "jira.json"
    with open(jira_path, "r") as jira_file:
        jira = json.load(jira_file)

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
                for src in sources:
                    matched_items = src_index_map[src].get(jira_key, [])
                    if matched_items:
                        matched = True
                        if src not in jira_item:
                            jira_item[src] = []
                        if isinstance(matched_items, list):
                            jira_item[src].extend(matched_items)
                        else:
                            jira_item[src].append(matched_items)
                if not matched:
                    non_correlated.append(jira_item)

    with open(output_non_correlated_file, "w") as file:
        json.dump(non_correlated, file, indent=4)

    with open(output_correlated_file, "w") as file:
        json.dump(jira, file, indent=4)


def correlate_table():
    df = pd.read_pickle(table_file)

    if isinstance(df, pd.Series):
        df = df.to_frame()

    feature_gates = set(filter_enabled_feature_gates(df))

    logger.debug(
        f"Identified feature_gates: {json.dumps(list(feature_gates), indent=4)}"
    )

    with open(correlated_file, "r") as f:
        correlated = json.load(f)

    result = {}

    def match_feature_gate(feature_gate: str, value):
        return isinstance(value, str) and feature_gate.lower() in value.lower()

    def update_result(result, feature_gate, value, issue):
        if match_feature_gate(feature_gate, value):
            result.setdefault(feature_gate, []).append(issue)

    for feature_gate in feature_gates:
        for project in correlated.values():
            for issue_type_dict in project.values():
                if not isinstance(issue_type_dict, dict):
                    continue
                for issue in issue_type_dict.values():
                    for issue_value in issue.values():
                        if isinstance(issue_value, list):
                            for src_dict in issue_value:
                                if isinstance(src_dict, dict):
                                    for src_value in src_dict.values():
                                        update_result(
                                            result, feature_gate, src_value, issue
                                        )
                        else:
                            update_result(result, feature_gate, issue_value, issue)

    known_feature_gates = set(result.keys())
    unknown_feature_gates = feature_gates.difference(known_feature_gates)
    logger.debug(f"Identified unknown_feature_gates: {unknown_feature_gates}")

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

    known_feature_gates = set(result.keys())
    unknown_feature_gates = feature_gates.difference(known_feature_gates)
    logger.debug(f"Identified: unknown_feature_gates: {unknown_feature_gates}")

    with open(correlated_table_file, "w") as f:
        json.dump(result, f, indent=4)


def convert_json_to_markdown(data: dict) -> str:
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
            if "epic_key" in issue:
                lines.append(f"**Epic**: `{issue['epic_key']}`\n")
            if "description" in issue:
                lines.append(
                    f"**Description:**\n\n{format_description(issue['description'])}\n"
                )

            for src, entries in issue.items():
                if src == "GITHUB":
                    lines.append(f"**GitHub Items:**\n")
                    for entry in entries:
                        lines.append(
                            f"- **[{entry.get('title')}]** (ID: {entry.get('id')})\n"
                        )
                        if entry.get("body"):
                            lines.append(f"  - {entry['body'].strip()}\n")
        lines.append("\n---\n")

    return "\n".join(lines)


def correlate_all(
    data_directory=None, output_correlated_file=None, output_non_correlated_file=None
):
    """
    Run all correlation steps.

    Args:
        data_directory: Optional Path object for data directory. Defaults to global data_dir.
        output_correlated_file: Optional Path object for correlated output file. Defaults to global correlated_file.
        output_non_correlated_file: Optional Path object for non-correlated output file. Defaults to global non_correlated_file.
    """
    correlate_with_jira_issue_id(
        data_directory, output_correlated_file, output_non_correlated_file
    )
    # remove_irrelevant_fields_from_correlated()
    # filter_jira_issue_ids(correlated_file)
    correlate_table()


# Maintain backward compatibility
src_index_builder_map = get_src_index_builder_map()
