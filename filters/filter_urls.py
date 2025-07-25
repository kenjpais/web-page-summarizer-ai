from pathlib import Path
from config.settings import get_settings
from utils.logging_config import get_logger

logger = get_logger(__name__)

settings = get_settings()
data_dir = Path(settings.directories.data_dir)


def filter_urls():
    """
    Filter and categorize URLs by source type based on domain matching.

    This function takes the raw list of URLs extracted from the release page
    and categorizes them by source type (GitHub, JIRA, etc.) based on domain
    matching. The categorization enables specialized scrapers to process
    URLs appropriate for their source type.

    Process:
    1. Load the configured source servers (GitHub, JIRA, etc.)
    2. Read all URLs from the master urls.txt file
    3. Match each URL against configured server domains
    4. Write matching URLs to source-specific files (e.g., github_urls.txt)

    Input: data/urls.txt (all discovered URLs)
    Output: data/{source}_urls.txt files (e.g., github_urls.txt, jira_urls.txt)
    """
    logger.info("[*] Filtering relevant URLs...")

    # Get the configured source servers for URL matching
    # Example: {"GITHUB": "https://github.com", "JIRA": "https://issues.redhat.com"}
    servers = settings.processing.get_sources_dict()
    urls_dict = {}
    with open(data_dir / "urls.txt") as f:
        for url in f:
            url = url.strip()
            # Check if URL matches any configured source server
            for src, server in servers.items():
                if server in url:
                    # Write matching URL to source-specific file
                    # Example: GITHUB URLs go to github_urls.txt
                    urls_dict.setdefault(src.lower(), set()).add(url)

    for src, urls in urls_dict.items():
        with open(data_dir / f"{src}_urls.txt", "w") as f:
            for url in urls:
                f.write(url + "\n")
