import json
import pickle
import pandas as pd
from pathlib import Path
from collections import defaultdict
from summarizers.summarizer import summarize_feature_gates
from filters.filter_enabled_feature_gates import filter_enabled_feature_gates
from config.settings import get_settings
from utils.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Configuration paths for input and output files
data_dir = Path(settings.directories.data_dir)

# Pickle file paths
table_file = data_dir / "feature_gate_table.pkl"
feature_gate_project_map_file = data_dir / "feature_gate_project_map.pkl"

# JSON file paths
correlated_file = data_dir / "correlated.json"
correlated_feature_gate_table_file = data_dir / "correlated_feature_gate_table.json"
summarized_features_file = data_dir / "summarized_features.json"

# Markdown file paths
correlated_table_md_file = data_dir / "correlated_feature_gate_table.md"


def correlate_table():
    """
    Correlate feature gate information with JIRA/GitHub data.

    This secondary correlation links OpenShift feature gates with related
    development work. Feature gates are configuration flags that enable/disable
    features, and this correlation helps understand what development work
    relates to specific features.

    Process:
    1. Load feature gate table and extract enabled gates
    2. Search correlated JIRA/GitHub data for feature gate mentions
    3. Create mappings between feature gates and related work items
    4. Handle unknown feature gates by searching raw source data
    5. Generate final correlation results

    The correlation finds feature gate references
    in issue summaries, descriptions, and commit messages.
    """
    # Load and process feature gate data
    df = pd.read_pickle(table_file)

    # Handle case where pickle contains a Series instead of DataFrame
    if isinstance(df, pd.Series):
        df = df.to_frame()

    # Extract the list of enabled feature gates for correlation
    feature_gates = set(filter_enabled_feature_gates(df))

    logger.debug(
        f"Identified feature_gates: {json.dumps(list(feature_gates), indent=4)}"
    )

    # Load the correlated JIRA/GitHub data
    with open(correlated_file, "r") as f:
        correlated = json.load(f)

    feature_gate_artifacts = {}
    feature_gate_project_map = defaultdict(str)

    def match_feature_gate(feature_gate: str, value: str):
        """
        Check if a feature gate is mentioned in a text value.

        Uses case-insensitive substring matching to find feature gate
        references in various text fields.
        """
        return isinstance(value, str) and feature_gate.lower() in value.lower()

    def update_feature_gate_artifacts(feature_gate, artifact, project_name):
        """
        Helper to add feature gate matches to results.
        """
        feature_gate_project_map[feature_gate] = project_name
        feature_gate_artifacts.setdefault(feature_gate, []).append(artifact)

    def get_artifact_key(artifact):
        """
        Generate a unique key for an issue to detect duplicates.
        Uses summary and epic_key (if present) as the unique identifier.
        """
        summary = artifact.get("summary", "")
        epic_key = artifact.get("epic_key", "")
        return f"{summary}|{epic_key}"

    for feature_gate in feature_gates:
        # Track which artifact we've already added for this feature gate to prevent duplicates
        added_artifacts = set()

        for project_name, project in correlated.items():
            for jira_artifact in project.values():
                if not isinstance(jira_artifact, dict):
                    # Skip summary, description fields
                    continue
                for artifact in jira_artifact.values():
                    artifact_key = get_artifact_key(artifact)
                    if artifact_key and artifact_key in added_artifacts:
                        continue

                    # Search for feature gate mentions in any field of the artifact
                    artifact_matches = False
                    for artifact_value in artifact.values():
                        if isinstance(artifact_value, list):
                            # Handle GitHub items attached to JIRA issues
                            for src_dict in artifact_value:
                                if not isinstance(src_dict, dict):
                                    continue
                                for src_value in src_dict.values():
                                    if match_feature_gate(feature_gate, src_value):
                                        artifact_matches = True
                                        break
                                if artifact_matches:
                                    break
                        else:
                            # Handle direct JIRA artifact fields
                            if match_feature_gate(feature_gate, artifact_value):
                                artifact_matches = True
                                break
                        if artifact_matches:
                            break

                    if artifact_matches:
                        update_feature_gate_artifacts(
                            feature_gate, artifact, project_name
                        )
                        added_artifacts.add(artifact_key)

    # Identify feature gates that weren't found in correlated data
    matched_feature_gates = set(feature_gate_artifacts.keys())
    unmatched_feature_gates = feature_gates.difference(matched_feature_gates)

    def match_other_sources(unmatched_feature_gates):
        logger.info(
            f"""
        Searching raw source data for unmatched feature gates: {json.dumps(list(unmatched_feature_gates), indent=4)}
        This catches cases where feature gates are mentioned in items that weren't correlated with JIRA issues.
        """
        )
        sources = settings.processing.sources
        sources = [s for s in sources if s != "JIRA"]

        for fg in unmatched_feature_gates:
            for src in sources:
                with open(data_dir / f"{src}.json") as f:
                    src_data = json.load(f)
                if isinstance(src_data, list):
                    for data in src_data:
                        if isinstance(data, dict):
                            for value in data.values():
                                if match_feature_gate(fg, value):
                                    update_feature_gate_artifacts(
                                        fg, data, "NO-PROJECT"
                                    )

    if unmatched_feature_gates:
        match_other_sources(unmatched_feature_gates)

        # Final check for remaining unknown feature gates
        matched_feature_gates = set(feature_gate_artifacts.keys())
        unmatched_feature_gates = feature_gates.difference(matched_feature_gates)

    if matched_feature_gates:
        logger.debug(
            f"Matched {len(matched_feature_gates)}/{len(feature_gates)} feature gates to artifacts"
        )
    if unmatched_feature_gates:
        logger.debug(
            f"Unmatched feature gates: {json.dumps(list(unmatched_feature_gates), indent=4)}"
        )

    with open(feature_gate_project_map_file, "wb") as f:
        pickle.dump(feature_gate_project_map, f)
    with open(correlated_feature_gate_table_file, "w") as f:
        json.dump(feature_gate_artifacts, f, indent=4)
