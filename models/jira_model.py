def create_jira_issue_dict(issue):
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
    if parent := getattr(fields, "parent", None):
        issue_dict["parent_key"] = parent.key

    raw_comments = issue.raw.get("fields", {}).get("comment", {}).get("comments", [])
    if raw_comments:
        issue_dict["comments"] = [
            body for comment in raw_comments if (body := comment.get("body"))
        ]

    return issue_dict
