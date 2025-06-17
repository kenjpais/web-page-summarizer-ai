import sys
import logging
import time
from functools import wraps
from utils.utils import get_env


def setup_logging(level="INFO"):
    if level == "DEBUG" or get_env("DEBUG"):
        log_level = logging.DEBUG
    elif level == "INFO":
        log_level = logging.INFO
    elif level == "TEST":
        log_level = logging.ERROR

    log_file = "logs/app.log"
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    ch.setFormatter(ch_formatter)

    # File handler
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(ch_formatter)

    # Avoid duplicate handlers when re-running
    if not logger.handlers:
        logger.addHandler(ch)
        logger.addHandler(fh)


def log_prompt(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        with open(f"logs/{timestamp}_prompt.log", "w") as log:
            log.write(f"Prompt:\n{args[0]}\n\nResult:\n{result}")
        return result

    return wrapper
