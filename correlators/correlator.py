import json
import pandas as pd
from collections import defaultdict
from utils.logging_config import get_logger
from summarizers.summarizer import Summarizer
from scrapers.jira_scraper import extract_jira_ids
from filters.filter_enabled_feature_gates import filter_enabled_feature_gates
from config.settings import AppSettings, FilePathSettings
from utils.file_utils import write_pickle_file, read_pickle_file

logger = get_logger(__name__)


def build_github_item_index(github_file_path: str):
    """
    Build an index mapping JIRA issue IDs to related GitHub items.

    Args:
        data_directory: Optional override for data directory path

    Returns:
        Dictionary mapping JIRA issue IDs to lists of related GitHub items.
    """
    index = {}
    with open(github_file_path, "r") as srcfile:
        github = json.load(srcfile)

    for item in github:
        title = item.get("title", "")
        # Extract JIRA IDs from GitHub titles using regex pattern matching
        jira_ids = extract_jira_ids(title)
        if jira_ids:
            # Use the first JIRA ID found as the primary correlation key
            # This handles cases like "Fix OCPBUGS-123 and STOR-456"
            first_key = jira_ids[0]
            index.setdefault(first_key, []).append(item)
    return index


class Correlator:
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.sources = settings.api.sources
        self.file_path_settings = settings.file_paths

    def validate(self):
        if not self.sources:
            err = "No sources provided."
            logger.error(err)
            raise ValueError(err)

    def correlate_with_jira_issue_id(self):
        """
        Correlate JIRA issues with related items from other sources using issue IDs.

        Process:

        1. Load JIRA hierarchy structure
        2. Build index mappings for all configured sources
        3. For each JIRA issue, find related items in other sources
        4. Attach related items to the JIRA issue structure
        5. Track items that couldn't be correlated for analysis
        """
        logger.info("[*] Correlating items by JIRA 'id'")
        file_path_settings = self.file_path_settings
        sources = self.sources

        # Load the JIRA hierarchy structure
        with open(file_path_settings.jira_json_file_path, "r") as jira_file:
            jira = json.load(jira_file)

        non_correlated = []

        src_index_map = {
            "GITHUB": build_github_item_index(file_path_settings.github_json_file_path)
        }

        for project in jira.values():
            for jira_artifact in project.values():
                if not isinstance(jira_artifact, dict):
                    # Skip summary, description fields
                    continue
                for jira_key, jira_item in jira_artifact.items():
                    matched = False

                    # Check each source for items referencing this JIRA issue
                    # Skip JIRA itself as we don't correlate JIRA with JIRA
                    for src in sources:
                        if src == "JIRA":
                            continue
                        if matched_items := src_index_map[src].get(jira_key, []):
                            matched = True
                            # Add the matched items to the JIRA issue structure
                            if src not in jira_item:
                                jira_item[src] = []
                            if isinstance(matched_items, list):
                                jira_item[src].extend(matched_items)
                            else:
                                jira_item[src].append(matched_items)

                    # Track issues that couldn't be correlated for analysis
                    if not matched:
                        non_correlated.append(jira_item)

        with open(file_path_settings.non_correlated_file_path, "w") as file:
            json.dump(non_correlated, file, indent=4)

        with open(file_path_settings.correlated_file_path, "w") as file:
            json.dump(jira, file, indent=4)

    def correlate_table(self):
        """
        Correlate feature gate information with JIRA/GitHub data.

        The correlation finds feature gate references
        in issue summaries, descriptions, and commit messages.

        Process:
        1. Load feature gate table and extract enabled gates
        2. Search correlated JIRA/GitHub data for feature gate mentions
        3. Create mappings between feature gates and related work items
        4. Handle unknown feature gates by searching raw source data
        5. Generate final correlation results
        """
        logger.info("[*] Correlating table information with JIRA/GitHub data")
        file_path_settings = self.file_path_settings
        sources = self.sources

        # Load and process feature gate data
        df = pd.read_pickle(file_path_settings.feature_gate_table_file_path)

        # Handle case where pickle contains a Series instead of DataFrame
        if isinstance(df, pd.Series):
            df = df.to_frame()

        # Extract the list of enabled feature gates for correlation
        feature_gates = set(filter_enabled_feature_gates(df))

        logger.debug(
            f"Identified feature_gates: {json.dumps(list(feature_gates), indent=4)}"
        )

        # Load the correlated JIRA/GitHub data
        with open(file_path_settings.correlated_file_path, "r") as f:
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

        def match_other_sources(unmatched_feature_gates, sources):
            logger.info(
                f"""
            Searching raw source data for unmatched feature gates: {json.dumps(list(unmatched_feature_gates), indent=4)}
            """
            )
            sources = [s for s in sources if s != "JIRA"]

            for fg in unmatched_feature_gates:
                for src in sources:
                    src = src.lower()
                    # Read the JSON data file for this source
                    json_file_path = getattr(
                        file_path_settings, f"{src}_json_file_path"
                    )
                    with open(json_file_path) as f:
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
            match_other_sources(unmatched_feature_gates, sources)

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

        write_pickle_file(
            file_path_settings.feature_gate_project_map_file_path,
            feature_gate_project_map,
        )
        with open(file_path_settings.correlated_feature_gate_table_file_path, "w") as f:
            json.dump(feature_gate_artifacts, f, indent=4)

    def correlate_features(self):
        logger.info("[*] Correlating features with JIRA/GitHub data")
        with open(
            self.file_path_settings.correlated_feature_gate_table_file_path, "r"
        ) as f:
            correlated_feature_gate_table = json.load(f)
        with open(self.file_path_settings.correlated_file_path, "r") as f:
            correlated = json.load(f)
        feature_gate_project_map = read_pickle_file(
            self.file_path_settings.feature_gate_project_map_file_path
        )

        def add_enabled_feature(correlated, project_name, feature_name, artifacts):
            if project_name not in correlated:
                correlated[project_name] = {}
            if "enabledFeatures" not in correlated[project_name]:
                correlated[project_name]["enabledFeatures"] = {}
            correlated[project_name]["enabledFeatures"][feature_name] = artifacts

        for feature_name, artifacts in correlated_feature_gate_table.items():
            if project_name := feature_gate_project_map.get(feature_name, ""):
                add_enabled_feature(correlated, project_name, feature_name, artifacts)

        with open(self.file_path_settings.correlated_file_path, "w") as f:
            json.dump(correlated, f)

    def correlate_summarized_features(self):
        logger.info("[*] Correlating summarized features with JIRA/GitHub data")
        with open(self.file_path_settings.summarized_features_file_path, "r") as f:
            summarized_features = json.load(f)
        with open(self.file_path_settings.correlated_file_path, "r") as f:
            correlated = json.load(f)
        feature_gate_project_map = read_pickle_file(
            self.file_path_settings.feature_gate_project_map_file_path
        )

        def add_enabled_feature(correlated, project_name, feature_name, summary):
            if project_name not in correlated:
                correlated[project_name] = {}
            if "enabledFeatures" not in correlated[project_name]:
                correlated[project_name]["enabledFeatures"] = {}
            correlated[project_name]["enabledFeatures"][feature_name] = summary

        for feature_name, summary in summarized_features.items():
            if project_name := feature_gate_project_map.get(feature_name, ""):
                add_enabled_feature(correlated, project_name, feature_name, summary)

        with open(self.file_path_settings.correlated_file_path, "w") as f:
            json.dump(correlated, f)

    def correlate(self):
        """
        Execute the complete correlation pipeline.

        This orchestrates all correlation steps:
        1. JIRA-to-source correlation (GitHub items referencing JIRA issues)
        2. Feature gate correlation (development work related to feature flags)

        Args:
            data_directory: Optional Path object for data directory. Defaults to global data_dir.
            output_correlated_file: Optional Path object for correlated output file. Defaults to global correlated_file.
            output_non_correlated_file: Optional Path object for non-correlated output file. Defaults to global non_correlated_file.
        """
        logger.info("[*] Correlating scraped data...")

        # Step 1: Correlate JIRA issues with GitHub items
        self.correlate_with_jira_issue_id()

        # Step 2: Correlate with feature gate information
        self.correlate_table()

        # Step 3: Match enabled feature gates with JIRA issues
        self.correlate_features()
