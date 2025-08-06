import sys
import argparse
from scrapers.scrapers import scrape_sources
from correlators.correlator import correlate_all
from summarizers.summarizer import summarize
from cli.url_cli import add_url_cli, parse_url_cli_args
from cli.jira_cli import add_jira_cli, parse_jira_cli_args
from cli.github_cli import add_github_cli, parse_github_cli_args
from cli.default_cli import add_default_cli, parse_default_cli_args
from utils.logging_config import get_logger

logger = get_logger(__name__)


def main_cli():
    parser = argparse.ArgumentParser(description="Main CLI")

    add_default_cli(parser)
    add_url_cli(parser)
    add_jira_cli(parser)
    add_github_cli(parser)

    args = parser.parse_args()

    kwargs = {}
    kwargs.update(parse_default_cli_args(args))
    kwargs.update(parse_url_cli_args(args))
    kwargs.update(parse_jira_cli_args(args))
    kwargs.update(parse_github_cli_args(args))

    run_workflow(kwargs)


def run_workflow(kwargs: dict):
    """Execute the complete workflow pipeline.

    Args:
        kwargs: Dictionary containing configuration from CLI parsers

    Raises:
        SystemExit: On any workflow error
    """
    try:
        logger.info("Starting workflow execution...")
        logger.debug(f"Workflow configuration: {kwargs}")

        scrape_sources(kwargs)
        correlate_all()
        summarize()

        logger.info("Workflow completed successfully")

    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        logger.debug("Workflow error details:", exc_info=True)
        sys.exit(1)
