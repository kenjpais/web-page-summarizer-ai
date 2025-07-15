import runner
from utils.logging_config import setup_logging, get_logger

if __name__ == "__main__":
    import sys

    # Setup logging
    setup_logging()
    logger = get_logger(__name__)

    if len(sys.argv) < 2:
        logger.error(
            "Usage: python script.py <release_page_html_file> or \npython script.py <url>"
        )
        sys.exit(1)
    else:
        runner.run(sys.argv[1])
