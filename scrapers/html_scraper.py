import pandas as pd
from pathlib import Path
from typing import Set, List, cast
from bs4 import BeautifulSoup, Tag
from utils.parser_utils import parse_tables
from utils.utils import is_valid_url, contains_valid_keywords
from utils.parser_utils import parse_html
from utils.logging_config import get_logger
from config.settings import AppSettings, ConfigFileSettings, ConfigLoader

logger = get_logger(__name__)


class HtmlScraper:
    """
    HTML scraper for extracting URLs and structured data from OpenShift release pages.

    The scraper applies content filtering to focus on relevant links and
    preserves tabular data for downstream correlation analysis.
    """

    def __init__(self, url: str, settings: AppSettings) -> None:
        """
        Initialize scraper with target URL.

        Args:
            url: URL of the release page to scrape (can be local file or web URL)
        """
        self.url: str = url
        self.settings: AppSettings = settings
        self.file_settings: ConfigFileSettings = settings.config_files

    def extract(self) -> None:
        """
        Execute the complete scraping process for the release page.

        This orchestrates both URL extraction and table parsing in the
        correct order, ensuring all relevant data is captured from the page.
        """
        logger.info(f"Scraping {self.url}...")
        logger.info(f"Parsing HTML...")
        # Parse the HTML content (handles both local files and web URLs)
        html: BeautifulSoup = parse_html(self.url)

        # Extract and filter relevant URLs for downstream processing
        self.scrape_valid_urls(html, self.settings.file_paths.urls_file_path)

        # Extract structured data from tables (primarily feature gates)
        self.scrape_table_info(
            html, self.settings.file_paths.feature_gate_table_file_path
        )

    def scrape_valid_urls(self, soup: BeautifulSoup, urls_file_path: Path) -> None:
        """
        Extract and filter URLs from the HTML content.

        This method finds all anchor tags and applies multiple filtering criteria:
        1. URL format validation (proper HTTP/HTTPS URLs)
        2. Keyword filtering (exclude irrelevant content)
        3. Deduplication (avoid processing the same URL multiple times)

        The filtering ensures that only URLs pointing to relevant development
        artifacts (JIRA issues, GitHub PRs/commits) are passed to downstream
        scrapers, improving efficiency and data quality.

        Args:
            soup: Parsed BeautifulSoup object of the HTML content

        Output: Creates urls.txt with all validated and filtered URLs
        """
        logger.info("Extracting URLs...")
        seen: Set[str] = set()

        config_loader = ConfigLoader(self.settings)
        invalid_keywords = config_loader.get_filter_file()

        with open(urls_file_path, "w") as file:
            for a_tag in soup.find_all("a", href=True):
                tag = cast(Tag, a_tag)

                # Extract text content and URL, handling potential None values
                text, url = tag.get_text(strip=True), str(tag.get("href", "")).strip()

                if (
                    url
                    and url not in seen
                    and is_valid_url(url)
                    and contains_valid_keywords([text, url], invalid_keywords)
                ):
                    file.write(url + "\n")
                    seen.add(url)

        logger.debug(f"Extracted {len(seen)} URL(s).")

    def scrape_table_info(
        self, html: BeautifulSoup, feature_gate_table_file_path
    ) -> None:
        """
        Extract structured data from HTML tables.

        The data is stored in pickle format for efficient loading by other
        components that need to analyze feature gate states and correlate
        them with development work.

        Args:
            html: Parsed BeautifulSoup object of the HTML content

        Output: Creates feature_gate_table.pkl with extracted table data
        """
        logger.info("Extracting table data...")

        # Parse all tables found in the HTML
        dataframes: List[pd.DataFrame] = parse_tables(html)

        # Store as pickle for efficient loading by correlation components
        # Pickle preserves DataFrame structure and data types
        pd.to_pickle(dataframes, feature_gate_table_file_path)

        logger.debug(f"Extracted {len(dataframes)} table(s).")
