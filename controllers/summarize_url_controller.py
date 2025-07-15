import shutil
import runner
from pathlib import Path
from utils.utils import get_env, is_valid_url
from urllib.error import URLError

data_dir = Path(get_env("DATA_DIR"))
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
