from typing import Dict, Type, Any
from scrapers.html_scraper import HtmlScraper
from scrapers.jira_scraper import JiraScraper
from scrapers.github_scraper import GithubScraper
from config.settings import AppSettings
from utils.utils import is_valid_url
from utils.logging_config import get_logger

logger = get_logger(__name__)


class Scraper:
    SOURCE_SCRAPERS_MAP: Dict[str, Type[Any]] = {
        "default": HtmlScraper,
        "jira": JiraScraper,
        "github": GithubScraper,
    }

    def __init__(self, kwargs: dict, settings: AppSettings):
        self.kwargs = kwargs
        self.url = self.kwargs.get("url", "") if self.kwargs else ""
        self.settings = settings
        self.validate()

    def validate(self) -> None:
        """Validate that all sources are supported by the scraper."""
        if self.url:
            if not is_valid_url(self.url):
                err = f"Invalid URL provided {self.url}"
                logger.error(err)
                raise ValueError(err)
        else:
            if self.kwargs:
                if {k: v for k, v in self.kwargs.items() if k != "filter_on"}:
                    return
            err = "No URL or sources provided."
            logger.error(err)
            raise ValueError(err)

        sources = self.settings.api.sources
        if not sources:
            err = "No sources provided."
            logger.error(err)
            raise ValueError(err)

        for src in sources:
            if src.lower() not in self.SOURCE_SCRAPERS_MAP:
                err = f"Source {src} is not supported"
                logger.error(err)
                raise ValueError(err)

    def filter_urls_by_source(self) -> dict[str, list[str]]:
        """Filter and categorize URLs by source type based on domain matching."""
        logger.info("[*] Filtering relevant URLs...")

        source_servers = self.settings.api.source_server_map
        urls_file_path = self.settings.file_paths.urls_file_path
        get_urls_file_path = self.settings.file_paths.get_urls_file_path

        urls_dict = {}
        servers = source_servers
        with open(urls_file_path) as f:
            for url in f:
                url = url.strip()
                for src, server in servers.items():
                    if server in url:
                        if src.lower() not in urls_dict:
                            urls_dict[src.lower()] = []
                        if url not in urls_dict[src.lower()]:
                            urls_dict[src.lower()].append(url)

        for src, urls in urls_dict.items():
            with open(get_urls_file_path(src), "w") as f:
                f.writelines(url + "\n" for url in urls)

        return urls_dict

    def scrape(self) -> None:
        """Orchestrate scraping across all configured sources."""
        if self.url:
            self.SOURCE_SCRAPERS_MAP.get("default")(
                url=self.url, settings=self.settings
            ).extract()
            logger.info(f"Successfully completed scraping {self.url}.")

        # Check if we have direct source-specific requests (issue IDs, usernames, etc.)
        direct_requests = {}
        for src in ["jira", "github"]:
            src_kwargs = self.kwargs.get(src, {})
            if src_kwargs and any(
                v for k, v in src_kwargs.items() if k != "filter_on" and v
            ):
                direct_requests[src.upper()] = []

        # If we have direct requests, use those; otherwise filter URLs
        if direct_requests:
            urls_dict = direct_requests
        else:
            urls_dict = self.filter_urls_by_source()

        for src, src_urls in urls_dict.items():
            logger.info(f"Scraping {src} links...")

            # Check if we have source-specific kwargs that don't require URLs
            src_kwargs = self.kwargs.get(src.lower(), {})
            has_direct_request = src_kwargs and any(
                v for k, v in src_kwargs.items() if k != "filter_on" and v
            )

            if not src_urls and not has_direct_request:
                logger.warning(f"No URLs found for {src}, skipping...")
                continue

            # Get the scraper class for this source type
            scraper_class = self.SOURCE_SCRAPERS_MAP.get(src.lower())
            if not scraper_class:
                logger.error(f"No scraper defined for source: {src}")
                continue

            try:
                scraper_kwargs = self.kwargs.get(src.lower(), {})
                logger.debug(
                    f"Initializing {src} scraper with kwargs: {scraper_kwargs}"
                )
                obj = scraper_class(
                    settings=self.settings, urls=src_urls, **scraper_kwargs
                )
                obj.extract()
                logger.info(f"Successfully completed scraping {src}.")
            except Exception as e:
                logger.error(f"Failed to scrape {src}: {str(e)}")
                continue
