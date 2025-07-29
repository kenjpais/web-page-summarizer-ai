import json
import pickle
from config.settings import get_settings

settings = get_settings()

# Configuration paths for input and output files
data_dir = settings.directories.data_dir

# Pickle file paths
feature_gate_project_map_file = data_dir / "feature_gate_project_map.pkl"

# JSON file paths
correlated_file = data_dir / "correlated.json"
summarized_features_file = data_dir / "summarized_features.json"


def correlate_summarized_features():
    with open(summarized_features_file, "r") as f:
        summarized_features = json.load(f)
    with open(correlated_file, "r") as f:
        correlated = json.load(f)
    with open(feature_gate_project_map_file, "rb") as f:
        feature_gate_project_map = pickle.load(f)

    def add_enabled_feature(correlated, project_name, feature_name, summary):
        if project_name not in correlated:
            correlated[project_name] = {}
        if "enabledFeatures" not in correlated[project_name]:
            correlated[project_name]["enabledFeatures"] = {}
        correlated[project_name]["enabledFeatures"][feature_name] = summary

    for feature_name, summary in summarized_features.items():
        if project_name := feature_gate_project_map.get(feature_name, ""):
            add_enabled_feature(correlated, project_name, feature_name, summary)

    with open(correlated_file, "w") as f:
        json.dump(correlated, f)
