import argparse


def add_default_cli(parser: argparse.ArgumentParser):
    parser.add_argument("--filter-on", action="store_true", help="Enable Filtering")


def parse_default_cli_args(args: argparse.Namespace):
    return (
        {
            "filter_on": args.filter_on,
        }
        if args.filter_on
        else {}
    )
