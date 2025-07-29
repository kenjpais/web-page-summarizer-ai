import re
import json
from urllib.parse import urlparse
from config.settings import get_settings
from utils.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()

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

    Args:
        url: URL string to validate

    Returns:
        Boolean indicating if URL is valid and safe to use
    """
    try:
        result = urlparse(url)
        return all([result.scheme in ALLOWED_PROTOCOLS, result.netloc])
    except ValueError:
        return False


def get_invalid_keywords():
    """
    Load keyword blacklist from configuration file.

    These keywords help filter out irrelevant content during processing.
    The configuration-based approach allows updating filters without code changes.

    Returns:
        List of lowercase keywords to exclude from processing
    """
    invalid_keywords = []
    with open(settings.config_files.config_file_path, "r") as f:
        data = json.load(f)
        invalid_keywords = data.get("invalid_keywords", [])
        # Normalize to lowercase for case-insensitive matching
        invalid_keywords.extend([k.lower() for k in invalid_keywords])

    return invalid_keywords


def contains_valid_keywords(fields):
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
    invalid_keywords = [kw.lower() for kw in get_invalid_keywords()]
    for field in fields:
        if field is None or not isinstance(field, str):
            continue
        field_str = field.lower()
        # If any invalid keyword is found, reject the content
        if any(keyword in field_str for keyword in invalid_keywords):
            return False
    return True


def get_urls(src):
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
    data_dir = settings.directories.data_dir
    if not data_dir:
        logger.error(f"[!][ERROR] DATA_DIR not configured")
        return []

    file_path = data_dir / f"{src}_urls.txt"
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
