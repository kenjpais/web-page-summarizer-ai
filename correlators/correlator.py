import json
import aiofiles
from utils.utils import get_env
from utils.file_utils import read_jsonl_async
from filters.filter_required_fields import remove_irrelevant_fields_from_correlated


async def correlate_by_jira_issue_id():
    """Use JIRA id as matching criteria to correlate different source information together."""
    print("\n[*] Correlating feature-related items by JIRA 'id' ...")

    sources = json.loads(get_env("SOURCES"))
    correlated_data = {}
    non_correlated_lines = []
    data_dir = get_env("DATA_DIR")
    for src in sources:
        async for line, obj in read_jsonl_async(f"{data_dir}/{src}.json"):
            id_ = obj.get("id")
            if not id_:
                non_correlated_lines.append(line)
                continue
            if id_ not in correlated_data:
                correlated_data[id_] = {}
            del obj["id"]
            correlated_data[id_][src] = obj

    async with aiofiles.open(f"{data_dir}/non_correlated.json", "w") as out:
        for line in non_correlated_lines:
            await out.write(line)

    with open(f"{data_dir}/correlated.json", "w") as out:
        json.dump(list(correlated_data.values()), out, indent=4)


def correlate_with_jira_issue_id():
    """Use JIRA id as matching criteria to correlate different source information together."""
    print("\n[*] Correlating feature-related items by JIRA 'id' ...")
    data_dir = get_env("DATA_DIR")
    sources = json.loads(get_env("SOURCES"))
    if "JIRA" in sources:
        sources.remove("JIRA")

    correlated_data = {}
    non_correlated_data = []

    jira_file_path = f"{data_dir}/JIRA.json"
    correlated_file = f"{data_dir}/correlated.json"
    non_correlated_file = f"{data_dir}/non_correlated.json"

    with open(jira_file_path, "r") as jira_file:
        for line in jira_file:
            jira_dict = json.loads(line)
            issue_id = jira_dict.get("id")
            if not issue_id:
                continue

            if issue_id not in correlated_data:
                correlated_data[issue_id] = {}
            correlated_data[issue_id]["JIRA"] = jira_dict

            for src in sources:
                src_path = f"{data_dir}/{src}.json"
                with open(src_path, "r") as srcfile:
                    for srcline in srcfile:
                        try:
                            obj = json.loads(srcline)
                        except json.JSONDecodeError:
                            continue
                        if issue_id in obj.get("title", ""):
                            if src not in correlated_data[issue_id]:
                                correlated_data[issue_id][src] = []
                            correlated_data[issue_id][src].append(obj)
                        else:
                            non_correlated_data.append(srcline)

    with open(non_correlated_file, "w") as file:
        for line in non_correlated_data:
            file.write(line)

    with open(correlated_file, "w") as file:
        json.dump(correlated_data, file, indent=4)


def correlate_all():
    correlate_with_jira_issue_id()
    remove_irrelevant_fields_from_correlated()
