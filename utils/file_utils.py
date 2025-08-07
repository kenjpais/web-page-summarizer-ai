import shutil
import pickle
from pathlib import Path
from typing import Any, Optional
from utils.logging_config import get_logger

logger = get_logger(__name__)


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


def copy_file(src_path: Path, dest_dir: Path) -> Path:
    """
    Copies a file from src_path to dest_dir.

    Parameters:
        src_path (Path): The path to the source file.
        dest_dir (Path): The path to the destination directory.

    Returns:
        Path: The path to the copied file in the destination directory.
    """
    if not src_path.is_file():
        raise FileNotFoundError(f"Source file not found: {src_path}")

    if not dest_dir.exists():
        dest_dir.mkdir(parents=True, exist_ok=True)

    dest_path = dest_dir / src_path.name
    shutil.copy2(src_path, dest_path)
    return dest_path


def validate_file_path(file_path: Path, file_type: str) -> None:
    """Validate that a file path exists and is readable.

    Args:
        file_path: Path to validate
        file_type: Human-readable description of file type

    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file is not readable
    """
    if not file_path.exists():
        raise FileNotFoundError(f"{file_type} not found: {file_path}")
    if not file_path.is_file():
        raise ValueError(f"{file_type} is not a regular file: {file_path}")
    if not file_path.stat().st_size < 10 * 1024 * 1024:  # 10MB limit
        raise ValueError(f"{file_type} is too large (>10MB): {file_path}")


def read_pickle_file(file_path: Path) -> Optional[Any]:
    """
    Safely read a pickle file with comprehensive error handling.

    This function provides robust pickle file loading that handles common
    failure scenarios gracefully, making it safe to use for cache files
    that may not exist or be corrupted.

    Args:
        file_path: Path to the pickle file to read

    Returns:
        The unpickled object if successful, None if file doesn't exist
        or is corrupted

    The function handles:
    - FileNotFoundError: File doesn't exist (returns None)
    - EOFError: File exists but is empty (returns None)
    - pickle.PickleError: File is corrupted or invalid (returns None)
    - Other exceptions: Logged and returns None
    """
    try:
        with open(file_path, "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        logger.debug(f"Pickle file not found: {file_path}")
        return None
    except EOFError:
        logger.debug(f"Pickle file is empty: {file_path}")
        return None
    except pickle.PickleError as e:
        logger.debug(f"Pickle file is corrupted: {file_path} - {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error reading pickle file {file_path}: {e}")
        return None


def write_pickle_file(file_path: Path, data: Any) -> bool:
    """
    Safely write data to a pickle file with error handling.

    Args:
        file_path: Path where to write the pickle file
        data: Data to pickle and save

    Returns:
        True if successful, False if an error occurred

    The function handles:
    - Directory creation if needed
    - Pickle serialization errors
    - File writing errors
    """
    try:
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "wb") as f:
            pickle.dump(data, f)
        logger.debug(f"Successfully wrote pickle file: {file_path}")
        return True
    except pickle.PickleError as e:
        logger.error(f"Failed to pickle data for {file_path}: {e}")
        return False
    except OSError as e:
        logger.error(f"Failed to write pickle file {file_path}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error writing pickle file {file_path}: {e}")
        return False
