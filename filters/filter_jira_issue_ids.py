import re
import json


def filter_jira_issue_ids(correlated_file):
    data = {}
    with open(correlated_file, "r") as corfile:
        data = json.load(corfile)

    def filter(data):
        def is_jira_key(key):
            return bool(re.match(r"^[A-Z]+-\d+$", key))

        if isinstance(data, dict):
            cleaned = {}
            for k, v in data.items():
                cleaned_value = filter(v)

                if is_jira_key(k):
                    # Flatten this level (i.e., drop the JIRA ID key)
                    if isinstance(cleaned_value, dict):
                        for inner_k, inner_v in cleaned_value.items():
                            if inner_v not in ("", None, [], {}, {}):
                                if inner_k in cleaned:
                                    # Merge if key already exists
                                    if isinstance(
                                        cleaned[inner_k], list
                                    ) and isinstance(inner_v, list):
                                        cleaned[inner_k].extend(inner_v)
                                    elif isinstance(
                                        cleaned[inner_k], dict
                                    ) and isinstance(inner_v, dict):
                                        cleaned[inner_k].update(inner_v)
                                    else:
                                        # Overwrite on conflict
                                        cleaned[inner_k] = inner_v
                                else:
                                    cleaned[inner_k] = inner_v
                    continue

                if cleaned_value not in ("", None, [], {}) and cleaned_value != {}:
                    cleaned[k] = cleaned_value

            return cleaned

        elif isinstance(data, list):
            cleaned_list = [filter(item) for item in data]
            return [item for item in cleaned_list if item not in ("", None, [], {})]

        else:
            return data

    data = filter(data)
    with open(correlated_file, "w") as corfile:
        json.dump(data, corfile)
