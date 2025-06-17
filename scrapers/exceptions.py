import logging

logger = logging.getLogger(__name__)


class ScraperException(Exception):
    """Custom exception for filter errors."""

    pass


def raise_scraper_exception(exc):
    logger.error(exc)
    raise ScraperException(exc)
