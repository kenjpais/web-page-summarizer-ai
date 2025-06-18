import json
from utils.utils import get_env


def remove_irrelavant_fields_from_correlated():
    sources = json.loads(get_env("SOURCES"))
    data_dir = get_env("DATA_DIR")
    config_dir = get_env("CONFIG_DIR")
    correlated_file = f"{data_dir}/correlated.json"

    # Load and normalize input
    with open(correlated_file, "r") as f:
        raw_data = json.load(f)

    if isinstance(raw_data, dict):
        correlated_data = list(raw_data.values())  # Convert to list for processing
    else:
        correlated_data = raw_data

    for src in sources:
        req_fields = []
        req_field_file = f"{config_dir}/required_{src.lower()}_fields.json"
        with open(req_field_file, "r") as f:
            req_fields = json.load(f)

        for entry in correlated_data:
            src_data = entry.get(src)
            if isinstance(src_data, list):
                new_list = []
                for item in src_data:
                    if all(field in item for field in req_fields):
                        new_list.append({field: item[field] for field in req_fields})
                entry[src] = new_list
            elif isinstance(src_data, dict):
                if all(field in src_data for field in req_fields):
                    entry[src] = {field: src_data[field] for field in req_fields}
                else:
                    entry[src] = {}

    # Write back as list (new contract)
    with open(correlated_file, "w") as f:
        json.dump(correlated_data, f, indent=4)
