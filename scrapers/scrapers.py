import json
from utils.utils import get_env, get_urls
from scrapers.exceptions import ScraperException
from scrapers.jira_scraper import JiraScraper
from scrapers.github_scraper import GithubScraper

MAX_WORKERS, MAX_SCRAPE_SIZE, BATCH_SIZE = 3, 400, 50

SOURCE_SCRAPERS_MAP = {
    "JIRA": JiraScraper,
    "GITHUB": GithubScraper,
}


def scrape_sources():
    sources = json.loads(get_env("SOURCES"))

    for src in sources:
        print(f"\n[*] Scraping {src} links...")
        urls = get_urls(src)
        if not urls:
            print(f"[!] No URLs found for {src}, skipping.")
            continue
        filter_instance = SOURCE_SCRAPERS_MAP.get(src)
        if not filter_instance:
            print(f"[!] No scraper defined for source: {src}")
            continue
        filter_instance().extract(urls)


def scrape_all():
    scrape_sources()
