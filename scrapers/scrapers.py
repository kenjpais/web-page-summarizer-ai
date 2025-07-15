import json
from typing import List, Dict, Type, Any
from utils.utils import get_env, get_urls
from scrapers.jira_scraper import JiraScraper
from scrapers.github_scraper import GithubScraper
from utils.logging_config import get_logger

logger = get_logger(__name__)

SOURCE_SCRAPERS_MAP: Dict[str, Type[Any]] = {
    "JIRA": JiraScraper,
    "GITHUB": GithubScraper,
}


def scrape_sources() -> None:
    sources: List[str] = json.loads(get_env("SOURCES"))

    for src in sources:
        logger.info(f"Scraping {src} links...")
        urls = get_urls(src)
        if not urls:
            logger.warning(f"No URLs found for {src}, skipping.")
            continue
        filter_instance = SOURCE_SCRAPERS_MAP.get(src)
        if not filter_instance:
            logger.error(f"No scraper defined for source: {src}")
            continue
        filter_instance().extract(urls)


def scrape_all() -> None:
    scrape_sources()
