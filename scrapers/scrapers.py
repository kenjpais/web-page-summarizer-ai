from typing import List, Dict, Type, Any
from utils.utils import get_urls
from scrapers.html_scraper import HtmlScraper
from scrapers.jira_scraper import JiraScraper
from scrapers.github_scraper import GithubScraper
from config.settings import get_settings
from utils.utils import add_urls_to_file
from utils.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()
data_dir = settings.directories.data_dir

# Registry mapping source names to their corresponding scraper classes
# This extensible pattern allows adding new sources without modifying core logic
# Each scraper must implement the extract(urls) method interface
SOURCE_SCRAPERS_MAP: Dict[str, Type[Any]] = {
    "jira": JiraScraper,
    "github": GithubScraper,
}


def scrape_sources(src_kwargs: dict[str, Any]) -> None:
    """
    Orchestrate scraping across all configured sources.

    This function iterates through each configured source type (GitHub, JIRA, etc.),
    loads the URLs specific to that source, and executes the appropriate scraper.
    If there are URLs that don't have a scraper, it will scrape them with the HtmlScraper.
    It will continue to scrape until all URLs are processed.

    Process:
    1. Load source configuration from environment
    2. For each source, load its filtered URLs
    3. Instantiate and execute the appropriate scraper
    4. Handle missing URLs or scraper implementations gracefully
    """
    # Load the list of configured sources from environment settings
    sources: List[str] = settings.processing.sources
    if not sources:
        logger.error("No sources configured, skipping scraping.")
        return

    fetch_by_username = False
    for src in sources:
        if "usernames" in src_kwargs.get(src, {}):
            fetch_by_username = True
            break

    while True:
        urls = set(get_urls())
        if not urls and not fetch_by_username:
            break

        for src in sources:
            logger.info(f"Scraping {src} links...")

            src = src.lower()
            # Load URLs that were filtered for this specific source type
            # These come from the filter_urls step that categorized URLs by domain
            src_urls = get_urls(src)
            if not src_urls and "usernames" not in src_kwargs.get(src, {}):
                logger.warning(f"No URLs found for {src}, skipping.")
                continue

            # Get the scraper class for this source type
            scraper_class = SOURCE_SCRAPERS_MAP.get(src)
            if not scraper_class:
                logger.error(f"No scraper defined for source: {src}")
                continue

            scraper_class(urls=src_urls, **src_kwargs.get(src, {})).extract()

            urls -= set(src_urls)
            add_urls_to_file(urls, data_dir / "urls.txt", mode="w")

        for url in urls:
            HtmlScraper(url).scrape()


def scrape_all() -> None:
    """
    Entry point for the scraping phase of the pipeline.
    """
    scrape_sources()
