import json
import os
import asyncio
import aiofiles
from concurrent.futures import ThreadPoolExecutor
from utils.utils import get_env, get_urls
from scrapers.exceptions import ScraperException
from scrapers.jira_scraper import JiraScraper
from scrapers.github_scraper import GithubScraper

MAX_WORKERS, MAX_SCRAPE_SIZE, BATCH_SIZE = 3, 400, 50

SOURCE_SCRAPERS_MAP = {
    "JIRA": JiraScraper,
    "GITHUB": GithubScraper,
}


async def scrape_sources():
    sources = json.loads(get_env("SOURCES"))
    data_dir = get_env("DATA_DIR")
    loop = asyncio.get_running_loop()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
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

            try:
                result = await loop.run_in_executor(
                    executor, filter_instance().extract, urls
                )
            except ScraperException as e:
                print(f"[!] Error scraping {src}: {e}")
                result = []
            except Exception as e:
                print(f"[!] Unexpected error scraping {src}: {e}")
                result = []

            output_path = os.path.join(data_dir, f"{src}.json")
            async with aiofiles.open(output_path, "w") as out:
                for item in result:
                    await out.write(json.dumps(item) + "\n")


def scrape_all():
    asyncio.run(scrape_sources())
