import argparse
from typing import Dict, Any


def add_url_cli(parser: argparse.ArgumentParser):
    parser.add_argument(
        "--url",
        type=str,
        help="URL to be scraped.",
    )


def parse_url_cli_args(args: argparse.Namespace) -> Dict[str, Any]:
    """Parse and validate URL CLI arguments."""
    return {
        "url": args.url,
    }
