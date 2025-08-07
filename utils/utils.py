from operator import inv
import re
import json
from typing import Callable, Dict, List, Any, Optional
from urllib.parse import urlparse
from pathlib import Path
from utils.logging_config import get_logger

logger = get_logger(__name__)

ALLOWED_PROTOCOLS = ("http", "https")

# Keyword lists for content classification and filtering
# These are used to determine if content represents new features vs. bug fixes

# Keywords that typically indicate maintenance work rather than new features
NON_FEATURE_KEYWORDS = [
    "bug",
    "fix",
    "error",
    "typo",
    "crash",
    "broken",
    "regression",
    "refactor",
    "test",
    "qa",
    "chore",
]

# Keywords that typically indicate new feature development
FEATURE_KEYWORDS = [
    "feature",
    "add",
    "new",
    "enhancement",
    "implement",
    "introduce",
    "support",
    "improve",
]


def is_valid_url(url):
    """
    Validate URL format and security requirements.

    Ensures URLs use allowed protocols (http/https) and have valid structure.
    This prevents security issues from malformed or malicious URLs.
    Also accepts local file paths.

    Args:
        url: URL string to validate

    Returns:
        Boolean indicating if URL is valid and safe to use
    """
    # Check if it's a local file
    if Path(url).is_file():
        return True

    # Check if it's a valid URL
    try:
        result = urlparse(url)
        return all([result.scheme in ALLOWED_PROTOCOLS, result.netloc])
    except ValueError:
        return False


def contains_valid_keywords(fields, invalid_keywords: List[str]) -> bool:
    """
    Check if content contains any invalid/blacklisted keywords.

    This function helps filter out irrelevant content by checking for
    keywords that indicate the content should be excluded from analysis.
    Used primarily for JIRA issue filtering.

    Args:
        fields: Collection of text fields to check (from JIRA issue)

    Returns:
        Boolean indicating if content passes keyword validation (True = valid)
    """
    invalid_keywords = [kw.lower() for kw in invalid_keywords]
    for field in fields:
        if field is None or not isinstance(field, str):
            continue
        field_str = field.lower()
        # If any invalid keyword is found, reject the content
        if any(keyword in field_str for keyword in invalid_keywords):
            return False
    return True


def get_urls(
    urls_file_path: Path,
    src: Optional[str] = None,
    get_source_urls_file_path: Optional[Callable] = None,
) -> List[str]:
    """
    Load URLs for a specific source type from the filtered URL files.

    This function reads the source-specific URL files created by the URL
    filtering step and returns them as a list for scraping. It includes
    comprehensive error handling for missing files or configuration issues.

    Args:
        src: Source name (e.g., "GITHUB", "JIRA")

    Returns:
        List of URLs for the specified source, empty list if none found

    The URL files are created by the filter_urls step and have names like:
    - github_urls.txt (for GitHub URLs)
    - jira_urls.txt (for JIRA URLs)
    """
    if src and get_source_urls_file_path:
        file_path = get_source_urls_file_path(src)
    else:
        file_path = urls_file_path

    if not file_path.is_file():
        logger.error(f"[!][ERROR] URL file {file_path} not found for source: {src}")
        return []

    try:
        with open(file_path, "r") as f:
            # Filter out empty lines and strip whitespace
            return [line.strip() for line in f if line.strip()]
    except IOError as e:
        logger.error(f"[!][ERROR] Failed to read URL file: {e}")
        return []


def add_urls_to_file(urls: list[str], file_path: str, mode: str = "a"):
    with open(file_path, mode) as f:
        for url in urls:
            f.write(url + "\n")


def json_to_markdown(data, heading_level=1):
    """
    Convert JSON data to human-readable Markdown format.

    This utility function recursively transforms JSON structures into
    well-formatted Markdown documents with proper heading hierarchy
    and structured presentation of data.

    Args:
        data: JSON data (dict, list, or JSON string) to convert
        heading_level: Starting heading level for hierarchical structure

    Returns:
        Formatted Markdown string

    Features:
    - Recursive processing of nested structures
    - Automatic heading level management
    - Clean formatting for different data types
    - Handles both objects and arrays appropriately
    """
    if isinstance(data, str):
        data = json.loads(data)

    markdown = ""
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                # Create heading for complex nested structures
                markdown += f"{'#' * heading_level} {key.capitalize()}\n\n"
                markdown += json_to_markdown(value, heading_level + 1)
            else:
                # Format simple key-value pairs as bold key with value
                markdown += f"**{key.capitalize()}:** {value}\n\n"
    elif isinstance(data, list):
        for idx, item in enumerate(data, 1):
            if isinstance(item, (dict, list)):
                # Recursively process complex list items
                markdown += json_to_markdown(item, heading_level)
            else:
                # Format simple list items as numbered list
                markdown += f"{idx}. {item}\n"
    return markdown


def remove_urls(text):
    # Regex pattern to match URLs (http, https, www)
    url_pattern = r"(https?://\S+|www\.\S+)"
    return re.sub(url_pattern, "", text)


def strings_to_list(s: str) -> list:
    # Convert single issue_ids string to list (split by comma if multiple)
    return [item.strip() for item in s.split(",")]


def validate_cs_input_str(input_str: str, field_name: str) -> list[str]:
    """Validate and parse comma-separated input string.

    Args:
        input_str: Comma-separated string to parse
        field_name: Name of field for error messages

    Returns:
        List of parsed and validated strings

    Raises:
        ValueError: If input contains invalid characters
    """
    if not input_str or not input_str.strip():
        return []

    items = strings_to_list(input_str)
    validated_items = []

    for item in items:
        item = item.strip()
        if not item:
            continue
        # Basic validation - no control characters
        if any(ord(c) < 32 for c in item if c not in "\t\n\r"):
            raise ValueError(
                f"Invalid {field_name} contains control characters: {item}"
            )
        validated_items.append(item)

    return validated_items
