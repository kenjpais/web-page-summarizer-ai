import shutil
import json
from pathlib import Path
from config.settings import get_settings

settings = get_settings()
data_dir = Path(settings.directories.data_dir)


class MultiFileManager:
    """
    Context manager for efficient handling of multiple file operations.

    This class optimizes scenarios where multiple files need to be read from
    or written to by keeping file handles open and reusing them. This is
    particularly useful for batch operations where the same files are
    accessed repeatedly.

    Features:
    - Automatic file handle management
    - Context manager support for clean resource handling
    - Separate tracking of read and write file handles
    - UTF-8 encoding by default for proper text handling

    Usage:
        with MultiFileManager() as fm:
            fm.write(file1, data1)
            fm.write(file1, more_data)  # Reuses same file handle
            content = fm.read(file2)
    """

    def __init__(self):
        """Initialize empty file handle dictionaries."""
        self.read_files = {}
        self.write_files = {}

    def readline(self, fname):
        """
        Read a single line from a file, opening it if necessary.

        Args:
            fname: Path to file to read from

        Returns:
            Single line from the file
        """
        if fname not in self.read_files:
            self.read_files[fname] = open(fname, "r", encoding="utf-8")
        return self.read_files[fname].readline()

    def read(self, fname):
        """
        Read entire contents of a file, opening it if necessary.

        Args:
            fname: Path to file to read from

        Returns:
            Complete file contents as string
        """
        if fname not in self.read_files:
            self.read_files[fname] = open(fname, "r", encoding="utf-8")
        return self.read_files[fname].read()

    def write(self, fname, data):
        """
        Write data to a file, opening it if necessary.

        Args:
            fname: Path to file to write to
            data: String data to write

        Returns:
            Number of characters written
        """
        if fname not in self.write_files:
            self.write_files[fname] = open(fname, "w", encoding="utf-8")
        return self.write_files[fname].write(data)

    def close_all(self):
        """
        Close all open file handles.

        This should be called when done with the file operations to ensure
        proper resource cleanup and data flushing.
        """
        for f in self.read_files.values():
            f.close()
        for f in self.write_files.values():
            f.close()

    def __enter__(self):
        """Context manager entry - returns self for use in with statement."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures all files are properly closed."""
        self.close_all()


async def read_jsonl_async(filepath):
    """
    Asynchronously read JSON Lines format files.

    JSON Lines format has one JSON object per line, commonly used for
    streaming data or large datasets. This function yields both the
    raw line and parsed JSON object.

    Args:
        filepath: Path to JSONL file to read

    Yields:
        Tuple of (raw_line, parsed_json_object)

    Note: Requires aiofiles import to be available for async file operations.
    Invalid JSON lines are silently skipped to handle malformed data gracefully.
    """
    # Note: aiofiles import is missing but function is preserved for future use
    async with aiofiles.open(filepath, "r") as f:
        async for line in f:
            try:
                yield line, json.loads(line)
            except json.JSONDecodeError:
                # Skip malformed JSON lines rather than failing completely
                continue


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
