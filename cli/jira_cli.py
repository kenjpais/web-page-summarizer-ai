import argparse
from typing import Any
from utils.utils import validate_cs_input_str
from utils.logging_config import get_logger

logger = get_logger(__name__)


def add_jira_cli(parser: argparse.ArgumentParser):
    parser.add_argument("--jira-server", type=str, help="JIRA server")
    parser.add_argument(
        "--issue-ids",
        type=str,
        help="Comma separated list of JIRA issue IDs to be scraped.",
    )
    parser.add_argument(
        "--jira-usernames",
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
    jira_usernames = validate_cs_input_str(args.jira_usernames, "jira_usernames") or []

    logger.debug(f"Parsed JIRA issue_ids: {issue_ids}")
    logger.debug(f"Parsed JIRA jira_usernames: {jira_usernames}")

    return {
        "jira": {
            "issue_ids": issue_ids,
            "jira_usernames": jira_usernames,
            "jira_server": args.jira_server or "",
        },
    }
