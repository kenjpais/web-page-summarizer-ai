from utils.parser_utils import clean_md_text


def create_jira_issue_dict(issue):
    """
    Transform a JIRA Issue object into a standardized dictionary format.

    This function extracts key fields from JIRA's complex API response structure
    and creates a dictionary that can be easily processed by
    downstream components.

    Args:
        issue: JIRA Issue object from the JIRA Python library

    Returns:
        Dictionary containing extracted JIRA issue data with keys:
        - summary: Issue title/summary text (cleaned of markdown artifacts)
        - description: Detailed issue description (cleaned of markdown artifacts)
        - parent_key: Key of parent issue (for sub-tasks)
        - comments: List of comment text from the issue

    The function uses safe attribute access to handle cases where fields
    may not be present or accessible due to permissions or JIRA configuration.
    """
    fields = issue.fields
    issue_dict = {}
    if summary := getattr(fields, "summary", ""):
        issue_dict["summary"] = clean_md_text(summary)
    if description := getattr(fields, "description", ""):
        issue_dict["description"] = clean_md_text(description)

    # Handle parent-child relationships (e.g., Epic -> Story, Story -> Sub-task)
    if parent := getattr(fields, "parent", None):
        issue_dict["parent_key"] = parent.key

    return issue_dict
