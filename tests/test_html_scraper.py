"""Test HTML scraper functionality."""

import unittest
from unittest.mock import patch
from scrapers.html_scraper import HtmlScraper
from config.settings import get_settings
from tests.mocks.mock_html_response import MockResponse

settings = get_settings()
data_dir = settings.directories.data_dir
url = "https://amd64.origin.releases.ci.openshift.org/releasestream/4-scos-next/release/4.20.0-okd-scos.ec.13"
scraper = HtmlScraper(url, settings)


def get_mock_html_response(url, *args, **kwargs):
    """Return a mock response with test HTML content.

    Args:
        url: The URL being requested (ignored in mock)
        *args: Variable length argument list (ignored in mock)
        **kwargs: Arbitrary keyword arguments (ignored in mock)
    """
    with open(settings.directories.test_data_dir / "release_page.html", "r") as f:
        html_content = f.read()
    return MockResponse(html_content)


class TestHtmlScraper(unittest.TestCase):
    @patch("requests.get", side_effect=get_mock_html_response)
    def test_scrape_valid_urls(self, mock_get):
        """Test that valid URLs are extracted from the HTML content."""
        scraper.extract()
        with open(data_dir / "urls.txt", "r") as f:
            result = f.read()
        self.assertGreater(len(result), 0)
        # Verify we have the expected URLs from release_page.html
        self.assertIn("https://github.com/openshift/api/pull/1234", result)
        self.assertIn("https://issues.redhat.com/browse/OCPBUGS-123", result)
        self.assertIn("https://github.com/openshift/enhancements/pull/567", result)
        self.assertIn("https://issues.redhat.com/browse/SPLAT-456", result)
