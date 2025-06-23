import json
from utils.utils import get_env
from filters.filter_required_fields import remove_irrelevant_fields_from_correlated


def correlate_with_jira_issue_id():
    print("\n[*] Correlating feature-related items by JIRA 'id' ...")
    data_dir = get_env("DATA_DIR")
    sources = json.loads(get_env("SOURCES"))
    if "JIRA" in sources:
        sources.remove("JIRA")

    correlated_data = {}
    non_correlated_data = []

    jira_file_path = f"{data_dir}/jira.json"
    correlated_file = f"{data_dir}/correlated.json"
    non_correlated_file = f"{data_dir}/non_correlated.json"

    with open(jira_file_path, "r") as jira_file:
        jira_data = json.load(jira_file)

    for category, issues in jira_data.items():
        if category not in correlated_data:
            correlated_data[category] = {}

        for issue in issues:
            issue_id = issue.get("id")
            if not issue_id:
                continue

            if issue_id not in correlated_data[category]:
                correlated_data[category][issue_id] = {}

            correlated_data[category][issue_id]["JIRA"] = issue

            for src in sources:
                src_path = f"{data_dir}/{src}.json"
                try:
                    with open(src_path, "r") as srcfile:
                            try:
                                obj_list = json.load(srcfile)
                            except json.JSONDecodeError:
                                continue
                            for obj in obj_list:
                                if issue_id in obj.get("title", ""):
                                    if src not in correlated_data[category][issue_id]:
                                        correlated_data[category][issue_id][src] = []
                                    correlated_data[category][issue_id][src].append(obj)
                                else:
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
