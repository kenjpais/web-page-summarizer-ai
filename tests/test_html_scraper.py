import unittest
from scrapers.html_scraper import HtmlScraper
from utils.utils import get_env

url = "https://amd64.origin.releases.ci.openshift.org/releasestream/4-scos-stable/release/4.19.0-okd-scos.0"
scraper = HtmlScraper(url)


class TestHtmlScraper(unittest.TestCase):
    def test_scrape_valid_urls(self):
        urls_txt = f"{get_env("DATA_DIR")}/urls.txt"
        scraper.scrape()
        with open(urls_txt, "r") as f:
            result = f.read()
        self.assertGreater(len(result), 0)

    def test_parse_tables(self):
        df = scraper.scrape_table_info()
        self.assertFalse(df.empty)

    def test_extract_jira_info_from_table(self):
        df = scraper.scrape_table_info()

