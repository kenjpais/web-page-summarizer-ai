"""Mock response for HTML scraper tests."""


class MockResponse:
    """Mock response object that mimics requests.Response."""

    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        """Raise an HTTPError for bad status codes."""
        if self.status_code >= 400:
            from requests.exceptions import HTTPError

            raise HTTPError(f"{self.status_code} Error", response=self)
