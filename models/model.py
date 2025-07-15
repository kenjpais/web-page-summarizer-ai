"""
Data Models Package

This package defines standardized data structures for content extracted from
different sources (GitHub, JIRA, etc.). The models provide:

1. **Consistent Interfaces**: Each source has different API response formats,
   but the models normalize them into consistent structures for processing.

2. **Type Safety**: Using dataclasses and type hints ensures data integrity
   and helps catch errors early in the pipeline.

3. **Extensibility**: New sources can be added by creating new model classes
   and registering them in the SOURCE_MODELS_MAP.

4. **Validation**: Models can include validation logic to ensure data quality
   from external APIs.
"""

from models.github_model import GithubModel

# Registry mapping source names to their corresponding data model classes
# This enables dynamic model selection based on the source type being processed
# Each model must implement a consistent interface (typically to_dict() method)
SOURCE_MODELS_MAP = {
    "GITHUB": GithubModel,
    # Future sources can be added here:
    # "JIRA": JiraModel,  # When implemented
    # "GITLAB": GitLabModel,  # Future enhancement
}
