import os
import json
import asyncio
import logging
import aiofiles
from concurrent.futures import ThreadPoolExecutor
from utils.utils import get_env
from utils.parser_utils import parse_html
from utils.utils import extract_valid_urls, get_urls
from utils.file_utils import MultiFileManager, read_jsonl_async
from scrapers.scrapers import SOURCE_SCRAPERS_MAP
from scrapers.exceptions import ScraperException
from summarizers import summarizer
from dotenv import load_dotenv
from utils.logging_config import setup_logging

load_dotenv(override=True)

setup_logging()
logger = logging.getLogger(__name__)


MAX_WORKERS, MAX_SCRAPE_SIZE, BATCH_SIZE = 3, 400, 50
os.makedirs(get_env("DATA_DIR"), exist_ok=True)


def run(source):
    extract_valid_urls(parse_html(source))
    filter_urls()
    asyncio.run(filter_srcs())
    asyncio.run(correlate_all())
    build_prompt_payload()
    summarize()


def filter_urls():
    print("\n[*] Filtering relevant URLs...")

    fm = MultiFileManager()
    sources = json.loads(get_env("SOURCES"))
    servers = {src: get_env(f"{src.upper()}_SERVER") for src in sources}
    data_dir = get_env("DATA_DIR")
    with fm:
        with open(f"{data_dir}/urls.txt") as f:
            for url in f:
                url = url.strip()
                for src, server in servers.items():
                    if server in url:
                        fm.write(f"{data_dir}/{src.lower()}_urls.txt", url + "\n")


async def filter_srcs():
    print("\n[*] Filtering feature-related items...")

    sources = json.loads(get_env("SOURCES"))
    loop = asyncio.get_running_loop()
    data_dir = get_env("DATA_DIR")
    for src in sources:
        print(f"\n[*] Scraping {src} links...")
        urls = get_urls(src)
        filter_instance = SOURCE_SCRAPERS_MAP[src]()

        try:
            result = await loop.run_in_executor(
                ThreadPoolExecutor(max_workers=MAX_WORKERS),
                lambda: filter_instance.extract(urls),
            )
        except ScraperException as e:
            print(f"[!] Error scraping {src}: {e}")
            result = []

        async with aiofiles.open(f"{data_dir}/{src}.json", "w") as out:
            for item in result:
                await out.write(json.dumps(item) + "\n")


async def correlate_all():
    print("\n[*] Correlating feature-related items...")

    sources = json.loads(get_env("SOURCES"))
    correlated_data = {}
    non_correlated_lines = []
    data_dir = get_env("DATA_DIR")
    for src in sources:
        async for line, obj in read_jsonl_async(f"{data_dir}/{src}.json"):
            id_ = obj.get("id")
            if not id_:
                non_correlated_lines.append(line)
                continue
            if id_ not in correlated_data:
                correlated_data[id_] = {}
            del obj["id"]
            correlated_data[id_][src] = obj

    async with aiofiles.open(f"{data_dir}/non_correlated.json", "w") as out:
        for line in non_correlated_lines:
            await out.write(line)

    with open(f"{data_dir}/correlated.json", "w") as out:
        json.dump(list(correlated_data.values()), out, indent=4)


def summarize():
    print("\n[*] Summarizing...")
    result = summarizer.summarize()
    data_dir = get_env("DATA_DIR")
    with open(f"{data_dir}/summary.txt", "w") as summary:
        summary.write(result)


def build_prompt_payload():
    data_dir = get_env("DATA_DIR")
    with open(f"{data_dir}/correlated.json", "r") as cor, open(
        f"{data_dir}/non_correlated.json", "r"
    ) as ncor, open(f"{data_dir}/prompt_payload.txt", "w") as out:
        out.write(
            f"""
            {cor.read()}\nMiscellaneous information:\n\n{ncor.read()}
        """
        )
