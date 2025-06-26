import unittest
from utils.utils import get_env
from scrapers.html_scraper import scrape_html
from filters.filter_urls import filter_urls
from scrapers.scrapers import scrape_all
from correlators.correlator import correlate_all
from utils.parser_utils import is_valid_markdown
from summarizers.summarizer import summarize_projects
from runner import run

data_dir = get_env("DATA_DIR")


class TestSummarizer(unittest.TestCase):
    def test_valid_summary(self):
        source = get_env("SOURCE_PAGE")
        run(source)
        with open(f"{data_dir}/summary.txt", "r") as f:
            summary = f.read()

        self.assertGreater(len(summary), 0)
        self.assertTrue(is_valid_markdown(summary))

    def test_summarize_projects(self):
        filter_urls()
        scrape_all()
        correlate_all()
        projects = summarize_projects()
        self.assertTrue(is_valid_markdown(projects))
        self.assertGreater(len(projects), 0)


if __name__ == "__main__":
    unittest.main()
