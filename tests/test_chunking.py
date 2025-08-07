"""
Test module for text chunking functionality.
This ensures large payloads are handled correctly to avoid API quota limits.
"""

import unittest
from utils.text_chunker import (
    estimate_token_count,
    chunk_text_for_llm,
    get_chunk_info,
    combine_chunked_summaries,
)
from config.settings import get_settings, get_config_loader

# Clear settings cache to pick up new environment variables
get_settings.cache_clear()
settings = get_settings()


class TestTextChunking(unittest.TestCase):
    """Test cases for text chunking functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.config_loader = get_config_loader()
        self.prompt_template = self.config_loader.get_summarize_prompt_template()
        self.settings = get_settings()

    def create_large_test_text(self, target_tokens: int = 60000) -> str:
        """Create a large text for testing chunking."""
        base_content = """
## JIRA Issue: EXAMPLE-123
**Summary:** Sample issue that demonstrates how release notes can become very large.

**Description:** This issue involves multiple components and has extensive details about 
implementation, testing, and deployment considerations. It includes technical specifications,
API changes, configuration updates, and various other details.

The implementation touches several areas:
- Core functionality changes
- API modifications  
- Database schema updates
- Configuration file changes
- Documentation updates
- Testing procedures
- Deployment scripts

**Related Issues:** EXAMPLE-124, EXAMPLE-125, EXAMPLE-126

---

## GitHub PR: #456
**Title:** Implement new feature with comprehensive changes

**Changes:**
- Modified 15 files across the codebase
- Added new API endpoints
- Updated database migrations
- Enhanced error handling
- Improved logging and monitoring
- Updated unit tests and integration tests
- Added performance optimizations

---
"""

        # Repeat content until we reach target token count
        text = ""
        while estimate_token_count(text) < target_tokens:
            text += base_content

        return text

    def test_token_estimation(self):
        """Test token counting accuracy."""
        test_cases = [
            ("Hello world", 3, "Short text"),
            (
                "This is a longer sentence with more words to test token counting.",
                18,
                "Medium text",
            ),
            ("A" * 1000, 285, "Long repetitive text"),
        ]

        for text, expected_tokens, description in test_cases:
            with self.subTest(description=description):
                tokens = estimate_token_count(text)
                # Allow some variance in token estimation (±20%)
                self.assertAlmostEqual(
                    tokens,
                    expected_tokens,
                    delta=expected_tokens * 0.2,
                    msg=f"{description}: expected ~{expected_tokens}, got {tokens}",
                )

    def test_small_text_no_chunking(self):
        """Test that small text doesn't get chunked."""
        small_text = "This is a small piece of text that should not need chunking."
        chunks = chunk_text_for_llm(settings, small_text, self.prompt_template)

        self.assertEqual(len(chunks), 1, "Small text should result in single chunk")
        self.assertEqual(
            chunks[0], small_text, "Single chunk should contain original text"
        )

    def test_large_text_chunking(self):
        """Test that large text gets properly chunked."""
        large_text = self.create_large_test_text(target_tokens=80000)

        # Test chunk info
        chunk_info = get_chunk_info(settings, large_text, self.prompt_template)

        self.assertGreater(
            chunk_info["total_tokens"], 50000, "Large text should exceed token limit"
        )
        self.assertTrue(chunk_info["needs_chunking"], "Large text should need chunking")
        self.assertGreater(chunk_info["num_chunks"], 1, "Should create multiple chunks")

        # Test actual chunking
        chunks = chunk_text_for_llm(settings, large_text, self.prompt_template)

        self.assertEqual(
            len(chunks), chunk_info["num_chunks"], "Chunk count should match prediction"
        )

        # Verify all chunks are within limits
        max_tokens = self.settings.api.max_input_tokens - 2000  # safety margin
        for i, chunk in enumerate(chunks):
            chunk_tokens = estimate_token_count(chunk)
            self.assertLessEqual(
                chunk_tokens,
                max_tokens,
                f"Chunk {i+1} exceeds token limit: {chunk_tokens} > {max_tokens}",
            )

    def test_summary_combination(self):
        """Test combining multiple summaries."""
        test_summaries = [
            "# New Features\nAdded new API endpoints and improved user interface.",
            "# Bug Fixes\nFixed critical issues and improved system stability.",
            "# Performance\nOptimized database queries and reduced memory usage.",
        ]

        combined = combine_chunked_summaries(test_summaries)

        self.assertIsInstance(combined, str, "Combined result should be a string")
        self.assertGreater(len(combined), 0, "Combined result should not be empty")

        # Check that all sections are present
        for summary in test_summaries:
            key_words = summary.split("\n")[0]  # Get the header
            self.assertIn(
                key_words.replace("#", "").strip(),
                combined,
                f"Combined summary should contain content from: {key_words}",
            )

    def test_empty_input_handling(self):
        """Test handling of empty or invalid inputs."""
        # Test empty text
        chunks = chunk_text_for_llm(settings, "", self.prompt_template)
        self.assertEqual(len(chunks), 1, "Empty text should result in single chunk")

        # Test empty summaries list
        combined = combine_chunked_summaries([])
        self.assertEqual(combined, "", "Empty summaries should result in empty string")

        # Test single summary
        single_summary = "# Single Section\nThis is a single summary."
        combined = combine_chunked_summaries([single_summary])
        self.assertEqual(
            combined, single_summary, "Single summary should be returned as-is"
        )

    def test_configuration_values(self):
        """Test that configuration values are reasonable."""
        settings = get_settings()

        self.assertGreater(
            settings.api.max_input_tokens, 0, "Max input tokens should be positive"
        )
        self.assertGreater(settings.api.chunk_size, 0, "Chunk size should be positive")
        self.assertGreaterEqual(
            settings.api.chunk_overlap, 0, "Chunk overlap should be non-negative"
        )
        self.assertLess(
            settings.api.chunk_size,
            settings.api.max_input_tokens,
            "Chunk size should be less than max input tokens",
        )


if __name__ == "__main__":
    unittest.main()
