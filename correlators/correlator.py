import json
from utils.utils import get_env
from filters.filter_required_fields import remove_irrelevant_fields_from_correlated
from filters.filter_jira_issue_ids import filter_jira_issue_ids

data_dir = get_env("DATA_DIR")
correlated_file = f"{data_dir}/correlated.json"


def correlate_with_jira_issue_id():
    print("\n[*] Correlating feature-related items by JIRA 'id' ...")
    sources = json.loads(get_env("SOURCES"))
    if "JIRA" in sources:
        sources.remove("JIRA")

    correlated_data = {}
    non_correlated_data = []

    jira_file_path = f"{data_dir}/jira.json"
    non_correlated_file = f"{data_dir}/non_correlated.json"

    with open(jira_file_path, "r") as jira_file:
        jira_data = json.load(jira_file)

    for category, epics in jira_data.items():
        if category not in correlated_data:
            correlated_data[category] = {}

        for epic_key, epic_data in epics.items():
            # Correlate epic
            correlated_data[category][epic_key] = {
                "JIRA": {"key": epic_key, **epic_data}
            }

            # Correlate stories under the epic
            for story_key, story_data in epic_data.get("stories", {}).items():
                correlated_data[category][story_key] = {
                    "JIRA": {"key": story_key, **story_data}
                }

    # Match with other sources
    for src in sources:
        src_path = f"{data_dir}/{src}.json"
        try:
            with open(src_path, "r") as srcfile:
                try:
                    obj_list = json.load(srcfile)
                except json.JSONDecodeError:
                    continue

                for obj in obj_list:
                    matched = False
                    for category in correlated_data:
                        for jira_id in correlated_data[category]:
                            if jira_id in obj.get("title", ""):
                                matched = True
                                if src not in correlated_data[category][jira_id]:
                                    correlated_data[category][jira_id][src] = []
                                correlated_data[category][jira_id][src].append(obj)
                    if not matched:
                        non_correlated_data.append(obj)

        except FileNotFoundError:
            continue

    with open(non_correlated_file, "w") as file:
        json.dump(non_correlated_data, file, indent=4)

    with open(correlated_file, "w") as file:
        json.dump(correlated_data, file, indent=4)


def correlate_all():
    correlate_with_jira_issue_id()
    remove_irrelevant_fields_from_correlated()
    filter_jira_issue_ids(correlated_file)
