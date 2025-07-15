import sys
import logging
import time
from pathlib import Path
from functools import wraps
from config.settings import get_settings

settings = get_settings()


def get_logger(name=None):
    """Get a logger for the given name/module."""
    return logging.getLogger(name)


def setup_logging(level="INFO"):
    # Check DEBUG environment variable first

    debug_enabled = settings.processing.debug

    if level == "DEBUG" or debug_enabled:
        log_level = logging.DEBUG
    elif level == "INFO":
        log_level = logging.INFO
    elif level == "TEST":
        log_level = logging.ERROR
    else:
        log_level = logging.INFO

    log_file = Path("logs") / "app.log"
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Console handler - only show DEBUG level on console if DEBUG is enabled
    ch = logging.StreamHandler(sys.stdout)
    console_level = logging.DEBUG if debug_enabled else logging.INFO
    ch.setLevel(console_level)
    ch_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    ch.setFormatter(ch_formatter)

    # File handler - always log DEBUG level to file
    log_file.parent.mkdir(exist_ok=True)
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(ch_formatter)

    # Avoid duplicate handlers when re-running
    if not logger.handlers:
        logger.addHandler(ch)
        logger.addHandler(fh)


def clean_escape_characters(text):
    """Clean up escape characters and formatting issues to make text more readable."""
    if not isinstance(text, str):
        text = str(text)

    # Replace carriage return + line feed with just line feed
    text = text.replace("\r\n", "\n")

    # Replace standalone carriage returns with line feeds
    text = text.replace("\r", "\n")

    # Replace common escape sequences
    text = text.replace("\\n", "\n")
    text = text.replace("\\r", "\n")
    text = text.replace("\\t", "\t")

    # Clean up excessive whitespace but preserve intentional formatting
    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        # Remove excessive spaces but keep some formatting
        cleaned_line = " ".join(line.split())
        cleaned_lines.append(cleaned_line)

    # Join lines back together
    cleaned_text = "\n".join(cleaned_lines)

    # Remove any remaining problematic characters
    cleaned_text = cleaned_text.replace("\x00", "")  # null characters
    cleaned_text = cleaned_text.replace("\x1b", "")  # escape characters

    return cleaned_text


def format_content_for_log(content):
    """Format content for better readability in log files."""
    if not isinstance(content, str):
        content = str(content)

    # Clean escape characters first
    content = clean_escape_characters(content)

    # Split into lines for processing
    lines = content.split("\n")
    formatted_lines = []

    for line in lines:
        # Skip empty lines to reduce clutter
        if not line.strip():
            continue

        # Break very long lines at reasonable points
        if len(line) > 120:
            words = line.split()
            current_line = ""

            for word in words:
                if len(current_line + word) > 120:
                    if current_line:
                        formatted_lines.append(current_line.strip())
                    current_line = word + " "
                else:
                    current_line += word + " "

            if current_line:
                formatted_lines.append(current_line.strip())
        else:
            formatted_lines.append(line)

    return "\n".join(formatted_lines)


def log_prompt(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        prompt = (
            kwargs.get("prompt") or getattr(args[0], "prompt", None) or args[1]
            if len(args) > 1
            else "N/A"
        )
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        # Create a readable log file with proper formatting
        log_filename = logs_dir / f"{timestamp}_prompt.log"

        with open(log_filename, "w", encoding="utf-8") as log:
            log.write(f"{'='*80}\n")
            log.write(f"PROMPT LOG - {timestamp}\n")
            log.write(f"{'='*80}\n\n")

            log.write("PROMPT:\n")
            log.write("-" * 40 + "\n")

            # Format and clean the prompt content
            formatted_prompt = format_content_for_log(prompt)
            log.write(formatted_prompt)

            log.write("\n\n")
            log.write("RESULT:\n")
            log.write("-" * 40 + "\n")

            # Format and clean the result content
            formatted_result = format_content_for_log(result)
            log.write(formatted_result)

            log.write("\n\n")
            log.write(f"{'='*80}\n")
            log.write("END OF LOG\n")
            log.write(f"{'='*80}\n")

        return result

    return wrapper
