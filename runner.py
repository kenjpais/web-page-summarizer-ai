from pathlib import Path
from utils.file_utils import delete_all_in_directory
from filters.filter_urls import filter_urls
from scrapers.html_scraper import scrape_html
from scrapers.scrapers import scrape_all
from correlators.correlator import correlate_all
from summarizers.summarizer import summarize
from config.settings import get_settings
from utils.logging_config import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)
settings = get_settings()
data_dir = settings.directories.data_dir
Path(data_dir).mkdir(exist_ok=True)


def run(source: str) -> None:
    """
    Entry point to run the full release page analysis pipeline.

    This orchestrates a multi-step process to extract, analyze, and summarize
    release information from OpenShift release pages and related resources.

    Pipeline Steps:
    1. Clean workspace - Remove any previous run artifacts
    2. HTML scraping - Extract URLs from the main release page
    3. URL filtering - Categorize URLs by source type (GitHub, JIRA)
    4. Data scraping - Fetch detailed information from each source
    5. Correlation - Link related items across sources using JIRA IDs
    6. Summarization - Generate final reports using LLM analysis

    Args:
        source: Either a file path to an HTML file or a URL to scrape

    Note: The order of operations is critical - each step depends on
    outputs from the previous step. Correlation requires both JIRA and
    GitHub data to be scraped first.
    """
    # Step 1: Clean workspace to ensure fresh start
    delete_all_in_directory(data_dir)

    # Step 2: Extract URLs from the main release page
    # This creates urls.txt with all discovered links
    scrape_html(source)

    # Step 3: Filter URLs by source type
    # Creates separate files like github_urls.txt, jira_urls.txt
    # based on domain matching and source configuration
    filter_urls()

    # Step 4: Scrape detailed data from each source
    # Fetches full content from GitHub PRs/commits and JIRA issues
    # Creates source-specific JSON files with structured data
    scrape_all()

    # Step 5: Correlate data across sources
    # Links JIRA issues with related GitHub items using issue IDs
    # Also correlates with feature gate information if available
    correlate_all()

    # Step 6: Generate final summaries
    # Uses LLM to create human-readable reports from correlated data
    summarize()
