import json
from utils.utils import get_env


def remove_irrelevant_fields_from_correlated():
    sources = json.loads(get_env("SOURCES"))
    data_dir = get_env("DATA_DIR")
    config_dir = get_env("CONFIG_DIR")
    correlated_file = f"{data_dir}/correlated.json"

    # Load nested correlated data (dict of dict of dicts)
    with open(correlated_file, "r") as f:
        correlated_data = json.load(f)

    for src in sources:
        req_fields = []
        req_field_file = f"{config_dir}/required_{src.lower()}_fields.json"
        with open(req_field_file, "r") as f:
            req_fields = json.load(f)

        # Iterate nested structure: category -> issue_id -> entry
        for category, issues in correlated_data.items():
            for issue_id, entry in issues.items():
                src_data = entry.get(src)
                if isinstance(src_data, list):
                    new_list = []
                    for item in src_data:
                        if any(field in item for field in req_fields):
                            filtered_item = {field: item[field] for field in req_fields if field in item}
                            new_list.append(filtered_item)
                    entry[src] = new_list
                elif isinstance(src_data, dict):
                    if any(field in src_data for field in req_fields):
                        filtered_dict = {field: src_data[field] for field in req_fields if field in src_data}
                        entry[src] = filtered_dict
                    else:
                        entry[src] = {}

    # Write back the nested filtered structure
    with open(correlated_file, "w") as f:
        json.dump(correlated_data, f, indent=4)
