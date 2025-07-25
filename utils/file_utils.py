import shutil
from pathlib import Path
from config.settings import get_settings

settings = get_settings()
data_dir = Path(settings.directories.data_dir)


def read_file_str(file_path):
    """
    Simple utility to read entire file contents as a string.

    Args:
        file_path: Path to file to read

    Returns:
        Complete file contents as string
    """
    with open(file_path, "r") as f:
        return f.read()


def delete_src_files(src: str):
    """
    Delete source-specific output files from previous runs.

    Removes both JSON and Markdown files for a specific source to ensure
    clean state before processing. This prevents old data from contaminating
    new results.

    Args:
        src: Source name (e.g., "github", "jira")

    Files removed:
    - {src}.json (structured data)
    - {src}.md (human-readable output)
    """
    for filename in [f"{src}.json", f"{src}.md"]:
        filepath = data_dir / filename
        if filepath.exists():
            filepath.unlink()


def delete_all_in_directory(dir_path):
    """
    Recursively delete all contents of a directory.

    This function provides a clean slate by removing all files and
    subdirectories within the specified directory. Used to clear
    the data directory before starting a new pipeline run.

    Args:
        dir_path: Path to directory to clean (string or Path object)

    Handles:
    - Regular files and symbolic links (unlink)
    - Directories (recursive removal)
    - Preserves the directory itself, only removes contents
    """
    dir_path = Path(dir_path)
    for item in dir_path.iterdir():
        if item.is_file() or item.is_symlink():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)
