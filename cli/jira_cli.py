import argparse
from typing import Any
from utils.utils import validate_cs_input_str
from utils.logging_config import get_logger

logger = get_logger(__name__)


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
        "--usernames",
        type=str,
        help="Fetch data for the given comma separated list of JIRA usernames.",
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
    # Parse and validate inputs
    issue_ids = validate_cs_input_str(args.issue_ids, "issue_ids") or []
    usernames = validate_cs_input_str(args.usernames, "usernames") or []

    logger.debug(f"Parsed issue_ids: {issue_ids}")
    logger.debug(f"Parsed usernames: {usernames}")

    return {
        "jira": {
            "issue_ids": issue_ids,
            "usernames": usernames,
            "jira_server": args.jira_server or "",
            "jira_username": args.jira_username or "",
            "jira_password": args.jira_password or "",
        },
    }
