import argparse
from typing import Any


def add_github_cli(parser: argparse.ArgumentParser):
    parser.add_argument("--github-server", type=str, help="github server")
    parser.add_argument("--github-username", type=str, help="github username")
    parser.add_argument("--github-password", type=str, help="github password")
    parser.add_argument("--github-token", type=str, help="github api token")


def parse_github_cli_args(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "github": {
            "github_server": args.github_server or "",
            "github_username": args.github_username or "",
            "github_password": args.github_password or "",
            "github_token": args.github_token or "",
        },
    }
