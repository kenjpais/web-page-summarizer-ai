import os
import shutil
import runner
from utils.utils import get_env, is_valid_url
from urllib.error import URLError

data_dir = get_env("DATA_DIR")
SUMMARY_FILE_PATH = os.path.join(data_dir, "summaries")


def summarize_release_page_from_url(url):
    if not is_valid_url(url) or "/release/" not in url:
        raise URLError("Invalid Release Page URL")

    release_name = url.strip().split("/release/")[1]

    runner.run(url)

    summary_dir = os.path.join(SUMMARY_FILE_PATH, release_name)
    os.makedirs(summary_dir, exist_ok=True)

    src_summary = os.path.join(data_dir, "summary.txt")
    dest_summary = os.path.join(summary_dir, "summary.txt")
    print(f"KDEBUG: {src_summary} {dest_summary}")
    shutil.copy(src_summary, dest_summary)
