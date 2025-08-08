from os import makedirs
from scrapers.scrapers import Scraper
from correlators.correlator import Correlator
from summarizers.summarizer import Summarizer
from config.settings import get_settings
from utils.logging_config import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)


def run(kwargs: dict) -> None:
    """
    Entry point to run the full release page analysis pipeline.

    This orchestrates a multi-step process to extract, analyze, and summarize
    release information from OpenShift release pages and related resources.

    Pipeline Steps:
    1. HTML scraping - Extract URLs from the main release page
    2. URL filtering - Categorize URLs by source type (GitHub, JIRA)
    3. Data scraping - Fetch detailed information from each source
    4. Correlation - Link related items across sources using JIRA IDs
    6. Summarization - Generate final reports using LLM analysis

    Args:
        source: Either a file path to an HTML file or a URL to scrape

    Note: The order of operations is critical - each step depends on
    outputs from the previous step. Correlation requires both JIRA and
    GitHub data to be scraped first.
    """
    settings = get_settings()
    makedirs(settings.directories.data_dir, exist_ok=True)
    # Scrape the data from the sources
    scraper = Scraper(kwargs, settings)
    scraper.scrape()

    # Correlates the data across sources using JIRA IDs
    correlator = Correlator(settings)
    correlator.correlate()

    # Summarize the correlated data using dependency injection
    summarizer = Summarizer(settings)
    summarizer.summarize()
