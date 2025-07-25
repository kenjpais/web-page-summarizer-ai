import unittest
from pathlib import Path
from scrapers.html_scraper import HtmlScraper
from config.settings import get_settings

settings = get_settings()
data_dir = Path(settings.directories.data_dir)
url = "https://amd64.origin.releases.ci.openshift.org/releasestream/4-scos-stable/release/4.19.0-okd-scos.0"
scraper = HtmlScraper(url)


class TestHtmlScraper(unittest.TestCase):
    def test_scrape_valid_urls(self):
        scraper.scrape()
        with open(data_dir / "urls.txt", "r") as f:
            result = f.read()
        self.assertGreater(len(result), 0)
