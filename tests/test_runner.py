import unittest
from unittest.mock import patch, MagicMock
from runner import run


class TestRunner(unittest.TestCase):
    @patch("runner.Scraper")
    @patch("runner.Correlator")
    @patch("runner.Summarizer")
    @patch("runner.get_settings")
    def test_run_executes_pipeline(
        self, mock_get_settings, mock_summarizer, mock_correlator, mock_scraper
    ):
        """Test that run executes the full pipeline in correct order."""
        # Setup mocks
        mock_settings = MagicMock()
        mock_get_settings.return_value = mock_settings

        mock_scraper_instance = MagicMock()
        mock_scraper.return_value = mock_scraper_instance

        mock_correlator_instance = MagicMock()
        mock_correlator.return_value = mock_correlator_instance

        mock_summarizer_instance = MagicMock()
        mock_summarizer.return_value = mock_summarizer_instance

        # Run the pipeline
        kwargs = {"url": "https://example.com"}
        run(kwargs)

        # Verify pipeline execution order
        mock_get_settings.assert_called_once()
        mock_scraper.assert_called_once_with(kwargs, mock_settings)
        mock_scraper_instance.scrape.assert_called_once()

        mock_correlator.assert_called_once_with(mock_settings)
        mock_correlator_instance.correlate.assert_called_once()

        mock_summarizer.assert_called_once_with(mock_settings)
        mock_summarizer_instance.summarize.assert_called_once()

    @patch("runner.get_settings")
    def test_run_handles_scraper_error(self, mock_get_settings):
        """Test that run handles scraper errors gracefully."""
        mock_settings = MagicMock()
        mock_get_settings.return_value = mock_settings

        with patch("runner.Scraper") as mock_scraper:
            mock_scraper_instance = MagicMock()
            mock_scraper_instance.scrape.side_effect = Exception("Scraper error")
            mock_scraper.return_value = mock_scraper_instance

            with self.assertRaises(Exception) as context:
                run({"url": "https://example.com"})

            self.assertEqual(str(context.exception), "Scraper error")

    @patch("runner.get_settings")
    def test_run_handles_correlator_error(self, mock_get_settings):
        """Test that run handles correlator errors gracefully."""
        mock_settings = MagicMock()
        mock_get_settings.return_value = mock_settings

        with patch("runner.Scraper") as mock_scraper, patch(
            "runner.Correlator"
        ) as mock_correlator:
            mock_scraper_instance = MagicMock()
            mock_scraper.return_value = mock_scraper_instance

            mock_correlator_instance = MagicMock()
            mock_correlator_instance.correlate.side_effect = Exception(
                "Correlator error"
            )
            mock_correlator.return_value = mock_correlator_instance

            with self.assertRaises(Exception) as context:
                run({"url": "https://example.com"})

            self.assertEqual(str(context.exception), "Correlator error")

    @patch("runner.get_settings")
    def test_run_handles_summarizer_error(self, mock_get_settings):
        """Test that run handles summarizer errors gracefully."""
        mock_settings = MagicMock()
        mock_get_settings.return_value = mock_settings

        with patch("runner.Scraper") as mock_scraper, patch(
            "runner.Correlator"
        ) as mock_correlator, patch("runner.Summarizer") as mock_summarizer:
            mock_scraper_instance = MagicMock()
            mock_scraper.return_value = mock_scraper_instance

            mock_correlator_instance = MagicMock()
            mock_correlator.return_value = mock_correlator_instance

            mock_summarizer_instance = MagicMock()
            mock_summarizer_instance.summarize.side_effect = Exception(
                "Summarizer error"
            )
            mock_summarizer.return_value = mock_summarizer_instance

            with self.assertRaises(Exception) as context:
                run({"url": "https://example.com"})

            self.assertEqual(str(context.exception), "Summarizer error")
