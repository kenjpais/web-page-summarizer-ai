"""
Test module for LLM integration with both local and Gemini providers.
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from clients.llm_factory import get_llm
from config.settings import get_settings


class TestLLMIntegration(unittest.TestCase):
    """Test cases for LLM provider integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.settings = get_settings()

    def test_settings_configuration(self):
        """Test that LLM settings are properly configured."""
        settings = get_settings()

        # Test that provider is valid
        self.assertIn(
            settings.api.llm_provider,
            ["local", "gemini"],
            "LLM provider should be 'local' or 'gemini'",
        )

        # Test that required settings exist
        self.assertIsNotNone(
            settings.api.llm_api_url, "LLM API URL should be configured"
        )
        self.assertIsNotNone(settings.api.llm_model, "LLM model should be configured")
        self.assertIsNotNone(
            settings.api.gemini_model, "Gemini model should be configured"
        )

    def test_llm_factory_returns_client(self):
        """Test that LLM factory returns a valid client."""
        try:
            llm_client = get_llm()
            self.assertIsNotNone(llm_client, "LLM factory should return a client")
            self.assertTrue(
                hasattr(llm_client, "invoke"), "LLM client should have invoke method"
            )
            self.assertTrue(
                hasattr(llm_client, "test_llm_connection"),
                "LLM client should have test_llm_connection method",
            )
        except ValueError as e:
            if "GOOGLE_API_KEY" in str(e):
                self.skipTest("Skipping Gemini test - GOOGLE_API_KEY not set")
            elif "langchain-google-genai" in str(e):
                self.skipTest(
                    "Skipping Gemini test - langchain-google-genai not installed"
                )
            else:
                raise

    @patch.dict(os.environ, {"LLM_PROVIDER": "local"})
    def test_local_provider_selection(self):
        """Test that local provider is correctly selected."""
        # Need to reload settings after changing environment
        from config.settings import get_settings

        settings = get_settings()

        # Clear any cached settings
        get_settings.cache_clear()

        # Test that factory can handle local provider
        try:
            llm_client = get_llm()
            # Check that we get a client (don't test actual connection as Ollama may not be running)
            self.assertIsNotNone(llm_client)
        except Exception as e:
            # Connection errors are expected if Ollama is not running
            if "Connection refused" in str(e) or "Failed to connect" in str(e):
                self.skipTest("Skipping local LLM test - Ollama server not running")
            else:
                raise

    @patch.dict(os.environ, {"LLM_PROVIDER": "gemini", "GOOGLE_API_KEY": "test-key"})
    def test_gemini_provider_selection(self):
        """Test that Gemini provider is correctly selected."""
        # Clear any cached settings
        from config.settings import get_settings

        get_settings.cache_clear()

        try:
            llm_client = get_llm()
            self.assertIsNotNone(llm_client)
            # We can't test actual connection without a real API key
        except ValueError as e:
            if "langchain-google-genai" in str(e):
                self.skipTest(
                    "Skipping Gemini test - langchain-google-genai not installed"
                )
            elif "API key" in str(e) or "authentication" in str(e).lower():
                pass  # Expected with fake API key
            else:
                raise
        except Exception as e:
            # Other errors might be connection-related
            if "API key" in str(e) or "authentication" in str(e).lower():
                pass  # Expected with fake API key
            else:
                raise

    def test_gemini_requires_api_key(self):
        """Test that Gemini provider requires API key."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "gemini"}, clear=False):
            # Remove GOOGLE_API_KEY if it exists
            if "GOOGLE_API_KEY" in os.environ:
                del os.environ["GOOGLE_API_KEY"]

            # Clear cached settings
            from config.settings import get_settings

            get_settings.cache_clear()

            with self.assertRaises(ValueError) as context:
                get_llm()

            self.assertIn("GOOGLE_API_KEY", str(context.exception))

    def test_invalid_provider_raises_error(self):
        """Test that invalid provider raises appropriate error."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "invalid"}, clear=False):
            # Clear cached settings
            from config.settings import get_settings

            get_settings.cache_clear()

            with self.assertRaises(ValueError) as context:
                get_llm()

            self.assertIn("Unsupported LLM provider", str(context.exception))

    def test_mock_llm_connection(self):
        """Test LLM connection with mocked client."""
        # Create a mock LLM client
        mock_client = MagicMock()
        mock_client.test_llm_connection.return_value = True
        mock_client.invoke.return_value = "4"

        # Test the mock works as expected
        self.assertTrue(mock_client.test_llm_connection("test"))
        response = mock_client.invoke("What is 2+2?")
        self.assertEqual(response, "4")

    def test_configuration_values(self):
        """Test that configuration values are reasonable."""
        settings = get_settings()

        # Test URL format for local LLM
        self.assertTrue(
            settings.api.llm_api_url.startswith(("http://", "https://")),
            "LLM API URL should be a valid HTTP(S) URL",
        )

        # Test model names are not empty
        self.assertGreater(
            len(settings.api.llm_model), 0, "LLM model name should not be empty"
        )
        self.assertGreater(
            len(settings.api.gemini_model), 0, "Gemini model name should not be empty"
        )

    def tearDown(self):
        """Clean up after tests."""
        # Clear any cached settings to avoid test interference
        from config.settings import get_settings

        get_settings.cache_clear()


if __name__ == "__main__":
    unittest.main()
