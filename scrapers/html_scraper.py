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
    def __init__(self, url: str) -> None:
        self.url: str = url

    def scrape(self) -> None:
        html: BeautifulSoup = parse_html(self.url)
        self.scrape_valid_urls(html)
        self.scrape_table_info(html)

    def scrape_valid_urls(self, soup: BeautifulSoup) -> None:
        logger.info("Extracting URLs...")
        seen: Set[str] = set()
        with open(data_dir / "urls.txt", "w") as file:
            for a_tag in soup.find_all("a", href=True):
                tag = cast(Tag, a_tag)
                text, url = tag.get_text(strip=True), str(tag.get("href", "")).strip()
                if (
                    url
                    and url not in seen
                    and is_valid_url(url)
                    and contains_valid_keywords([text, url])
                ):
                    file.write(url + "\n")
                    seen.add(url)
        logger.debug(f"Extracted {len(seen)} unique URLs")

    def scrape_table_info(self, html: BeautifulSoup) -> None:
        dataframes: List[pd.DataFrame] = parse_tables(html)
        pd.to_pickle(dataframes, feature_gate_table_file)


def scrape_html(url: str) -> None:
    logger.info("Parsing HTML...")
    HtmlScraper(url).scrape()
