import json
from utils.utils import get_env
from scrapers.jira_scraper import extract_jira_ids
from filters.filter_required_fields import remove_irrelevant_fields_from_correlated
from filters.filter_jira_issue_ids import filter_jira_issue_ids

data_dir = get_env("DATA_DIR")
correlated_file = f"{data_dir}/correlated.json"
non_correlated_file = f"{data_dir}/non_correlated.json"


def build_github_item_index():
    """
    Build an index mapping the first JIRA key found in each GitHub item title to the item(s).
    """
    index = {}
    src_path = f"{data_dir}/github.json"
    with open(src_path, "r") as srcfile:
        github = json.load(srcfile)

    for item in github:
        title = item.get("title", "")
        jira_ids = extract_jira_ids(title)
        if jira_ids:
            first_key = jira_ids[0]
            index.setdefault(first_key, []).append(item)
    return index


src_index_builder_map = {"GITHUB": build_github_item_index}


def correlate_with_jira_issue_id():
    print("\n[*] Correlating feature-related items by JIRA 'id' ...")

    sources = json.loads(get_env("SOURCES"))
    if "JIRA" in sources:
        sources.remove("JIRA")

    jira_file_path = f"{data_dir}/jira.json"
    with open(jira_file_path, "r") as jira_file:
        jira = json.load(jira_file)

    # Build source-specific indexes once
    src_index_map = {src: src_index_builder_map[src]() for src in sources}

    non_correlated = []

    for _, project in jira.items():
        jira_artifacts = []
        if stories := project.get("stories"):
            jira_artifacts.append(stories)
        if epics := project.get("epics"):
            jira_artifacts.append(epics)

        for jira_artifact in jira_artifacts:
            for jira_key, jira_item in jira_artifact.items():
                matched = False
                for src in sources:
                    matched_items = src_index_map[src].get(jira_key, [])
                    for matched_item in matched_items:
                        if gh_type := matched_item.get("type"):
                            jira_item.setdefault(src, {}).setdefault(
                                gh_type, []
                            ).append(matched_item)
                            matched = True
                if not matched:
                    non_correlated.append(jira_item)

    with open(non_correlated_file, "w") as file:
        json.dump(non_correlated, file, indent=4)

    with open(correlated_file, "w") as file:
        json.dump(jira, file, indent=4)


def correlate_all():
    correlate_with_jira_issue_id()
    #remove_irrelevant_fields_from_correlated()
    #filter_jira_issue_ids(correlated_file)
