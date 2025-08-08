"""
CLI module for the AI Summarizer.
"""

import sys
import argparse
from typing import Optional, Dict, Any

import runner
from scrapers.scrapers import Scraper
from correlators.correlator import Correlator
from cli.url_cli import add_url_cli, parse_url_cli_args
from cli.jira_cli import add_jira_cli, parse_jira_cli_args
from cli.github_cli import add_github_cli, parse_github_cli_args
from cli.default_cli import add_default_cli, parse_default_cli_args
from utils.logging_config import get_logger
from config.settings import AppSettings, get_settings

logger = get_logger(__name__)


class CLI:
    """Main CLI class."""

    def __init__(
        self,
        settings: Optional[AppSettings] = None,
    ):
        """Initialize CLI with optional dependencies."""
        self.settings = settings or get_settings()
        self.parser = self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create and configure argument parser."""
        parser = argparse.ArgumentParser(description="AI Summarizer CLI")

        # Add subcommands
        subparsers = parser.add_subparsers(
            dest="command", help="Commands", required=True
        )

        # Add scrape command
        scrape_parser = subparsers.add_parser("scrape", help="Scrape data from sources")
        add_default_cli(scrape_parser)
        add_url_cli(scrape_parser)
        add_jira_cli(scrape_parser)
        add_github_cli(scrape_parser)

        # Add correlate command
        correlate_parser = subparsers.add_parser(
            "correlate", help="Correlate data across sources"
        )
        add_default_cli(correlate_parser)

        # Add summarize command
        summarize_parser = subparsers.add_parser(
            "summarize", help="Generate summaries from correlated data"
        )
        add_default_cli(summarize_parser)
        add_url_cli(summarize_parser)
        add_jira_cli(summarize_parser)
        add_github_cli(summarize_parser)

        return parser

    def parse_args(self, args_list: Optional[list] = None) -> Dict[str, Any]:
        """Parse command line arguments into kwargs dictionary."""
        args = self.parser.parse_args(args_list)

        # Build kwargs dictionary
        kwargs = {"command": args.command} if args.command else {}
        kwargs.update(parse_default_cli_args(args))

        # Add source-specific args for relevant commands
        if not args.command or args.command not in ["correlate"]:
            kwargs.update(parse_url_cli_args(args))
            kwargs.update(parse_jira_cli_args(args))
            kwargs.update(parse_github_cli_args(args))

        return kwargs

    def execute(self, kwargs: Dict[str, Any]) -> None:
        """Execute command based on parsed arguments."""
        try:
            logger.debug(f"Configuration: {kwargs}")
            command = kwargs.get("command")

            if command == "scrape":
                scraper = Scraper(kwargs, self.settings)
                scraper.scrape()
            elif command == "correlate":
                correlator = Correlator(self.settings)
                correlator.correlate()
            else:
                runner.run(kwargs)

            logger.info("Completed successfully!")

        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            logger.debug("Workflow error details:", exc_info=True)
            sys.exit(1)

    def run(self, args_list: Optional[list] = None) -> None:
        """Run the CLI with the given arguments."""
        kwargs = self.parse_args(args_list)
        self.execute(kwargs)
