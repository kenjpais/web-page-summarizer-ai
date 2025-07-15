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
        - summary: Issue title/summary text
        - description: Detailed issue description  
        - parent_key: Key of parent issue (for sub-tasks)
        - comments: List of comment text from the issue
        
    The function uses safe attribute access to handle cases where fields
    may not be present or accessible due to permissions or JIRA configuration.
    """
    fields = issue.fields
    issue_dict = {}
    # if issue_type := getattr(fields.issuetype, "name", ""):
    #    issue_dict["issue_type"] = issue_type
    # if project_name := getattr(fields.project, "name", ""):
    #    issue_dict["project_name"] = project_name
    if summary := getattr(fields, "summary", ""):
        issue_dict["summary"] = summary
    if description := getattr(fields, "description", ""):
        issue_dict["description"] = description
        
    # Handle parent-child relationships (e.g., Epic -> Story, Story -> Sub-task)
    if parent := getattr(fields, "parent", None):
        issue_dict["parent_key"] = parent.key

    return issue_dict
    raw_comments = issue.raw.get("fields", {}).get("comment", {}).get("comments", [])
    if raw_comments:
        issue_dict["comments"] = [
            body for comment in raw_comments if (body := comment.get("body"))
        ]

    return issue_dict
