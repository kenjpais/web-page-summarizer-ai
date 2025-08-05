import re
import shutil
import runner
from utils.utils import is_valid_url
from urllib.error import URLError
from config.settings import get_settings

settings = get_settings()
data_dir = settings.directories.data_dir

SUMMARY_FILE_PATH = data_dir / "summaries"


def summarize_release_page_from_url(url):
    """Fetches data from url and summarizes all relevant information."""
    if not is_valid_url(url) or "/release/" not in url:
        raise URLError("Invalid Release Page URL")

    release_name = url.strip().split("/release/")[1]
    if not release_name:
        raise URLError("Invalid Release Page URL")

    runner.run(url)

    summary_dir = SUMMARY_FILE_PATH / release_name
    summary_dir.mkdir(parents=True, exist_ok=True)

    src_summary = data_dir / "summary.txt"

    def update_summary_with_release_version(summary_file_path, release_version_name):
        with open(summary_file_path, "r") as rf:
            content = rf.read()
        updated_content = f"Release Notes {release_version_name}\n{content}"
        with open(summary_file_path, "w") as wf:
            wf.write(updated_content)

    update_summary_with_release_version(src_summary, release_name)

    dest_summary = summary_dir / "summary.txt"
    shutil.copy(src_summary, dest_summary)

    clean_summary(dest_summary)


def clean_summary(dest_summary):
    """
    Remove mentions of Part <i>
    """
    pattern = re.compile(r"^## Part ([1-9][0-9]?|100)\s*$")
    with open(dest_summary, "r") as f:
        summary_lines = f.readlines()

    new_lines = [line for line in summary_lines if not pattern.match(line.strip())]

    with open(dest_summary, "w") as file:
        file.writelines(new_lines)
