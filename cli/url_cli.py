import argparse
from typing import Dict, Any
from pathlib import Path
from utils.utils import add_urls_to_file
from config.settings import get_settings
from utils.utils import strings_to_list

settings = get_settings()
data_dir = settings.directories.data_dir


def add_url_cli(parser: argparse.ArgumentParser):
    parser.add_argument(
        "--urls",
        type=str,
        help="URLs to be scraped(comma separated list of URLs).",
    )
    parser.add_argument("--urls-file", type=str, help="Source URLs file path.")


def parse_url_cli_args(args: argparse.Namespace) -> Dict[str, Any]:
    """Parse and validate URL CLI arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        Empty dictionary (URLs are written to file)

    Raises:
        FileNotFoundError: If specified URLs file doesn't exist
        ValueError: If URLs are invalid
    """
    urls = []

    if args.urls:
        urls.extend(strings_to_list(args.urls))

    if args.urls_file:
        file_path = Path(args.urls_file)
        _validate_file_path(file_path, "URLs file")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                file_urls = [line.strip() for line in f if line.strip()]
                urls.extend(file_urls)
        except IOError as e:
            raise IOError(f"Failed to read URLs file: {e}")

    # Ensure output directory exists
    data_dir.mkdir(parents=True, exist_ok=True)
    add_urls_to_file(urls, data_dir / "urls.txt")

    return {}


def _validate_file_path(file_path: Path, file_type: str) -> None:
    """Validate that a file path exists and is readable."""
    if not file_path.exists():
        raise FileNotFoundError(f"{file_type} not found: {file_path}")
    if not file_path.is_file():
        raise ValueError(f"{file_type} is not a regular file: {file_path}")
    if not file_path.stat().st_size < 10 * 1024 * 1024:  # 10MB limit
        raise ValueError(f"{file_type} is too large (>10MB): {file_path}")
