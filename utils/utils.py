import os
import json
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv
from config.settings import get_settings
from utils.logging_config import get_logger

logger = get_logger(__name__)
load_dotenv()
settings = get_settings()

ALLOWED_PROTOCOLS = ("http", "https")
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
    try:
        result = urlparse(url)
        return all([result.scheme in ALLOWED_PROTOCOLS, result.netloc])
    except ValueError:
        return False


def get_invalid_keywords():
    invalid_keywords = []
    with open(settings.config_files.config_file_path, "r") as f:
        data = json.load(f)
        invalid_keywords = data.get("invalid_keywords", [])
        invalid_keywords.extend([k.lower() for k in invalid_keywords])

    return invalid_keywords


def contains_valid_keywords(fields):
    invalid_keywords = [kw.lower() for kw in get_invalid_keywords()]
    for field in fields:
        if field is None or not isinstance(field, str):
            continue
        field_str = field.lower()
        if any(keyword in field_str for keyword in invalid_keywords):
            return False
    return True


def get_env(env_name):
    env_var = os.getenv(env_name)
    if env_var:
        return env_var
    raise ValueError(f"Environment variable {env_name} missing.")


def get_urls(src):
    data_dir = Path(settings.directories.data_dir)
    if not data_dir:
        logger.error(f"[!][ERROR] DATA_DIR not configured")
        return []
    file_path = data_dir / f"{src}_urls.txt"
    if not file_path.is_file():
        logger.error(f"[!][ERROR] URL file not found for source: {src}")
        return []
    try:
        with open(file_path, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except IOError as e:
        logger.error(f"[!][ERROR] Failed to read URL file: {e}")
        return []


def json_to_markdown(data, heading_level=1):
    if isinstance(data, str):
        data = json.loads(data)

    markdown = ""
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                markdown += f"{'#' * heading_level} {key.capitalize()}\n\n"
                markdown += json_to_markdown(value, heading_level + 1)
            else:
                markdown += f"**{key.capitalize()}:** {value}\n\n"
    elif isinstance(data, list):
        for idx, item in enumerate(data, 1):
            if isinstance(item, (dict, list)):
                markdown += json_to_markdown(item, heading_level)
            else:
                markdown += f"{idx}. {item}\n"
    return markdown
