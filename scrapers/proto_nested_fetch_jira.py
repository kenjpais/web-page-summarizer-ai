import requests
from requests.auth import HTTPBasicAuth
from collections import defaultdict

# --- Configuration ---
JIRA_DOMAIN = "your-domain.atlassian.net"  # Replace with your JIRA domain
EMAIL = "your-email@example.com"           # Replace with your JIRA email
API_TOKEN = "your-api-token"               # Replace with your JIRA API token
PROJECT_KEY = "PROJ"                       # Replace with your JIRA project key
FIX_VERSION = "1.2.0"                      # Optional: restrict to a specific fix version

# --- Globals ---
BASE_URL = f"https://{JIRA_DOMAIN}/rest/api/2"
AUTH = HTTPBasicAuth(EMAIL, API_TOKEN)
HEADERS = {"Accept": "application/json"}

def get_epic_link_field_id():
    response = requests.get(f"{BASE_URL}/field", auth=AUTH, headers=HEADERS)
    response.raise_for_status()
    for field in response.json():
        if field["name"].lower() == "epic link":
            return field["id"]
    raise Exception("Epic Link field not found")

def fetch_all_issues(epic_link_field_id):
    jql = f'project = {PROJECT_KEY}'
    if FIX_VERSION:
        jql += f' AND fixVersion = "{FIX_VERSION}"'
    max_results = 100
    start_at = 0
    all_issues = []

    while True:
        params = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
            "fields": f"summary,description,issuetype,parent,project,issuelinks,{epic_link_field_id}"
        }
        response = requests.get(f"{BASE_URL}/search", headers=HEADERS, auth=AUTH, params=params)
        response.raise_for_status()
        data = response.json()
        all_issues.extend(data["issues"])
        if start_at + max_results >= data["total"]:
            break
        start_at += max_results

    return all_issues

def organize_issues(issues, epic_link_field_id):
    issue_map = {issue["key"]: issue for issue in issues}
    hierarchy = defaultdict(lambda: defaultdict(lambda: {"summary": "", "description": "", "stories": {}}))

    for issue in issues:
        fields = issue["fields"]
        issue_type = fields["issuetype"]["name"]

        project_name = fields["project"]["name"]
        issue_key = issue["key"]
        summary = fields.get("summary", "")
        description = fields.get("description", "") or ""

        if issue_type.lower() == "epic":
            hierarchy[project_name][issue_key]["summary"] = summary
            hierarchy[project_name][issue_key]["description"] = description

    for issue in issues:
        fields = issue["fields"]
        issue_type = fields["issuetype"]["name"]
        epic_key = fields.get(epic_link_field_id)
        issue_key = issue["key"]
        summary = fields.get("summary", "")
        description = fields.get("description", "") or ""

        if issue_type.lower() in ["story", "task"] and epic_key:
            project_name = fields["project"]["name"]
            story_data = {
                "summary": summary,
                "description": description,
                "related": []
            }

            for link in fields.get("issuelinks", []):
                linked = link.get("outwardIssue") or link.get("inwardIssue")
                if linked and "fields" in linked:
                    linked_type = linked["fields"]["issuetype"]["name"]
                    linked_summary = linked["fields"].get("summary", "")
                    story_data["related"].append({
                        "key": linked["key"],
                        "type": linked_type,
                        "summary": linked_summary
                    })

            hierarchy[project_name][epic_key]["stories"][issue_key] = story_data

    return hierarchy

def render_to_markdown(hierarchy):
    md = ""
    for project, epics in hierarchy.items():
        md += f"# Project: {project}\n\n"
        for epic_key, epic in epics.items():
            md += f"## Epic: {epic_key} — {epic['summary']}\n"
            md += f"**Description:**\n{epic['description']}\n\n"
            for story_key, story in epic["stories"].items():
                md += f"### Story: {story_key} — {story['summary']}\n"
                md += f"**Description:**\n{story['description']}\n\n"
                if story["related"]:
                    md += f"#### Related Issues:\n"
                    for rel in story["related"]:
                        md += f"- **{rel['key']}** ({rel['type']}): {rel['summary']}\n"
                    md += "\n"
            md += "---\n\n"
    return md

def main():
    epic_link_field_id = get_epic_link_field_id()
    issues = fetch_all_issues(epic_link_field_id)
    hierarchy = organize_issues(issues, epic_link_field_id)
    markdown = render_to_markdown(hierarchy)

    with open("release_notes.md", "w", encoding="utf-8") as f:
        f.write(markdown)

    print("✅ Markdown release notes saved to 'release_notes.md'")

if __name__ == "__main__":
    main()
