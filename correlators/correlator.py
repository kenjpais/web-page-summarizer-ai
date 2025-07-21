from config.settings import get_settings
from utils.logging_config import get_logger
from correlators.correlate_with_jira_issue_id import correlate_with_jira_issue_id
from correlators.correlate_feature_gate_table import correlate_table
from correlators.correlate_summarized_features import correlate_summarized_features
from summarizers.summarizer import summarize_feature_gates

logger = get_logger(__name__)
settings = get_settings()


def correlate_all(
    data_directory=None, output_correlated_file=None, output_non_correlated_file=None
):
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
    # Step 1: Correlate JIRA issues with GitHub items
    correlate_with_jira_issue_id(
        data_directory, output_correlated_file, output_non_correlated_file
    )

    # Note: These steps are currently disabled but preserved for future use:
    # remove_irrelevant_fields_from_correlated() - Clean up unnecessary data
    # filter_jira_issue_ids(correlated_file) - Apply additional filtering

    # Step 2: Correlate with feature gate information
    correlate_table()
    summarize_feature_gates()
    correlate_summarized_features()
