import argparse
from typing import Any
from pathlib import Path

from config.settings import get_settings
from utils.utils import validate_cs_input_str
from utils.file_utils import validate_file_path

settings = get_settings()
data_dir = settings.directories.data_dir


def add_jira_cli(parser: argparse.ArgumentParser):
    parser.add_argument("--jira-server", type=str, help="JIRA server")
    parser.add_argument("--jira-username", type=str, help="JIRA username")
    parser.add_argument("--jira-password", type=str, help="JIRA password")
    parser.add_argument(
        "--issue-ids",
        type=str,
        help="Comma separated list of JIRA issue IDs to be scraped.",
    )
    parser.add_argument(
        "--issue-ids-file",
        type=str,
        help="JIRA issue IDs file for bulk fetch(comma separated list of JIRA issue IDs).",
    )
    parser.add_argument(
        "--usernames",
        type=str,
        help="Fetch data for the given comma separated list of JIRA usernames.",
    )
    parser.add_argument(
        "--username-file",
        type=str,
        help="Username file to bulk fetch data for the given comma separated list of usernames in GITHUB and JIRA.",
    )


def parse_jira_cli_args(args: argparse.Namespace) -> dict[str, Any]:
    """Parse and validate Jira CLI arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        Dictionary containing Jira configuration

    Raises:
        FileNotFoundError: If specified files don't exist
        ValueError: If file contents are invalid
    """
    issue_ids = []
    usernames = []

    if args.usernames:
        usernames.extend(validate_cs_input_str(args.usernames, "usernames"))

    if args.issue_ids:
        issue_ids.extend(validate_cs_input_str(args.issue_ids, "issue_ids"))

    if args.issue_ids_file:
        file_path = Path(args.issue_ids_file)
        validate_file_path(file_path, "Issue IDs file")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                file_issues = [line.strip() for line in f if line.strip()]
                issue_ids.extend(file_issues)
        except IOError as e:
            raise IOError(f"Failed to read issue IDs file: {e}")

    if args.username_file:
        file_path = Path(args.username_file)
        validate_file_path(file_path, "Username file")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                file_usernames = [line.strip() for line in f if line.strip()]
                usernames.extend(file_usernames)
        except IOError as e:
            raise IOError(f"Failed to read username file: {e}")

    return {
        "jira": {
            "issue_ids": issue_ids,
            "usernames": usernames,
            "jira_server": args.jira_server or "",
            "jira_username": args.jira_username or "",
            "jira_password": args.jira_password or "",
        },
    }
