import os
import logging
from utils.utils import get_env
from filters.filter_urls import filter_urls
from scrapers.html_scraper import scrape_html
from scrapers.scrapers import scrape_all
from correlators.correlator import correlate_all
from summarizers.summarizer import summarize
from dotenv import load_dotenv
from utils.logging_config import setup_logging

load_dotenv(override=True)

setup_logging()
logger = logging.getLogger(__name__)

os.makedirs(get_env("DATA_DIR"), exist_ok=True)


def run(source):
    """
    Entry point to run the full pipeline.
    - Parses the input HTML source
    - Extracts and filters relevant URLs
    - Scrapes structured data from sources
    - Correlates and summarizes the results
    """
    scrape_html(source)
    filter_urls()
    scrape_all()
    correlate_all()
    summarize()
