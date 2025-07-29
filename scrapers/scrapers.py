from typing import List, Dict, Type, Any
from utils.utils import get_urls
from scrapers.jira_scraper import JiraScraper
from scrapers.github_scraper import GithubScraper
from config.settings import get_settings
from utils.logging_config import get_logger

logger = get_logger(__name__)

# Registry mapping source names to their corresponding scraper classes
# This extensible pattern allows adding new sources without modifying core logic
# Each scraper must implement the extract(urls) method interface
SOURCE_SCRAPERS_MAP: Dict[str, Type[Any]] = {
    "JIRA": JiraScraper,
    "GITHUB": GithubScraper,
}


def scrape_sources() -> None:
    """
    Orchestrate scraping across all configured sources.

    This function iterates through each configured source type (GitHub, JIRA, etc.),
    loads the URLs specific to that source, and executes the appropriate scraper.

    Process:
    1. Load source configuration from environment
    2. For each source, load its filtered URLs
    3. Instantiate and execute the appropriate scraper
    4. Handle missing URLs or scraper implementations gracefully
    """
    # Load the list of configured sources from environment settings
    settings = get_settings()
    sources: List[str] = settings.processing.sources

    for src in sources:
        logger.info(f"Scraping {src} links...")

        # Load URLs that were filtered for this specific source type
        # These come from the filter_urls step that categorized URLs by domain
        urls = get_urls(src)
        if not urls:
            logger.warning(f"No URLs found for {src}, skipping.")
            continue

        # Get the scraper class for this source type
        scraper_class = SOURCE_SCRAPERS_MAP.get(src)
        if not scraper_class:
            logger.error(f"No scraper defined for source: {src}")
            continue

        # Instantiate and execute the scraper with source-specific URLs
        # Each scraper handles its own API authentication, rate limiting, etc.
        scraper_class().extract(urls)


def scrape_all() -> None:
    """
    Entry point for the scraping phase of the pipeline.
    """
    scrape_sources()
