import json
from pathlib import Path
from config.settings import get_settings

settings = get_settings()


def remove_irrelevant_fields_from_correlated():
    sources = settings.processing.sources
    data_dir = Path(settings.directories.data_dir)
    config_dir = Path(settings.directories.config_dir)
    correlated_file = data_dir / "correlated.json"

    # Load nested correlated data (dict of dict of dicts)
    with open(correlated_file, "r") as f:
        correlated_data = json.load(f)

    for src in sources:
        req_fields = []
        req_field_file = config_dir / f"required_{src.lower()}_fields.json"
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
                            filtered_item = {
                                field: item[field]
                                for field in req_fields
                                if field in item
                            }
                            new_list.append(filtered_item)
                    entry[src] = new_list
                elif isinstance(src_data, dict):
                    if any(field in src_data for field in req_fields):
                        filtered_dict = {
                            field: src_data[field]
                            for field in req_fields
                            if field in src_data
                        }
                        entry[src] = filtered_dict
                    else:
                        entry[src] = {}

    # Write back the nested filtered structure
    with open(correlated_file, "w") as f:
        json.dump(correlated_data, f, indent=4)
