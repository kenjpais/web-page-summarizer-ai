import pandas as pd
from pathlib import Path
from typing import Set, List, cast
from bs4 import BeautifulSoup, Tag
from utils.parser_utils import parse_tables
from utils.utils import is_valid_url, contains_valid_keywords
from utils.parser_utils import parse_html
from config.settings import get_settings
from utils.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()
data_dir = Path(settings.directories.data_dir)
feature_gate_table_file = data_dir / "feature_gate_table.pkl"


class HtmlScraper:
    """
    HTML scraper for extracting URLs and structured data from OpenShift release pages.

    The scraper applies content filtering to focus on relevant links and
    preserves tabular data for downstream correlation analysis.
    """

    def __init__(self, url: str) -> None:
        """
        Initialize scraper with target URL.

        Args:
            url: URL of the release page to scrape (can be local file or web URL)
        """
        self.url: str = url

    def scrape(self) -> None:
        """
        Execute the complete scraping process for the release page.

        This orchestrates both URL extraction and table parsing in the
        correct order, ensuring all relevant data is captured from the page.
        """
        # Parse the HTML content (handles both local files and web URLs)
        html: BeautifulSoup = parse_html(self.url)

        # Extract and filter relevant URLs for downstream processing
        self.scrape_valid_urls(html)

        # Extract structured data from tables (primarily feature gates)
        self.scrape_table_info(html)

    def scrape_valid_urls(self, soup: BeautifulSoup) -> None:
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
        seen: Set[str] = set()  # Track URLs to prevent duplicates

        with open(data_dir / "urls.txt", "w") as file:
            # Process all anchor tags with href attributes
            for a_tag in soup.find_all("a", href=True):
                tag = cast(Tag, a_tag)

                # Extract text content and URL, handling potential None values
                text, url = tag.get_text(strip=True), str(tag.get("href", "")).strip()

                # Apply comprehensive filtering criteria
                if (
                    url  # URL must not be empty
                    and url not in seen  # Must be unique
                    and is_valid_url(url)  # Must be valid HTTP/HTTPS URL
                    and contains_valid_keywords(
                        [text, url]
                    )  # Must pass keyword filters
                ):
                    file.write(url + "\n")
                    seen.add(url)

        logger.debug(f"Extracted {len(seen)} unique URLs")

    def scrape_table_info(self, html: BeautifulSoup) -> None:
        """
        Extract structured data from HTML tables.

        The data is stored in pickle format for efficient loading by other
        components that need to analyze feature gate states and correlate
        them with development work.

        Args:
            html: Parsed BeautifulSoup object of the HTML content

        Output: Creates feature_gate_table.pkl with extracted table data
        """
        # Parse all tables found in the HTML
        dataframes: List[pd.DataFrame] = parse_tables(html)

        # Store as pickle for efficient loading by correlation components
        # Pickle preserves DataFrame structure and data types
        pd.to_pickle(dataframes, feature_gate_table_file)


def scrape_html(url: str) -> None:
    """
    Entry point for HTML scraping operations.

    Args:
        url: URL or file path to scrape

    The function supports both:
    - Web URLs (http/https) for live scraping
    - Local file paths for processing saved HTML files
    """
    logger.info("Parsing HTML...")
    HtmlScraper(url).scrape()
