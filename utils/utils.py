import os
import json
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()


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
    "docs",
    "documentation",
    "test",
    "qa",
    "chore",
    "ci",
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

    with open(os.getenv("CONFIG_FILE_PATH"), "r") as f:
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
    print(f"Environment variable {env_name} missing.")


def get_urls(src):
    data_dir = get_env("DATA_DIR")
    file_path = f"{data_dir}/{src}_urls.txt"
    if os.path.isdir(f"{data_dir}"):
        print(f"KDEBUG: {data_dir} exists")
    if not os.path.isfile(file_path):
        print(f"[!] Warning: URL file not found for source: {src}")
        return []
    with open(file_path, "r") as f:
        return [line.strip() for line in f if line.strip()]

