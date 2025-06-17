import json
import asyncio
import aiofiles
from utils.utils import get_env
from utils.file_utils import read_jsonl_async


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


def correlate_all():
    asyncio.run(correlate_by_jira_issue_id())
