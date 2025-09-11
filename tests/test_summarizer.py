"""Tests for the Summarizer class."""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from summarizers.summarizer import Summarizer, MapReduceSummarizer
from utils.logging_config import get_logger, setup_logging
from utils.file_utils import delete_all_in_directory, copy_file
from tests.mocks.mock_llm import create_mock_llm
from tests.mocks.mock_chains import MockChains
from tests.mocks.mock_gemini_tokenizer import MockGeminiTokenizer
from tests.mocks.mock_rate_limiter import MockRateLimiter
from config.settings import get_settings

setup_logging()
logger = get_logger(__name__)

# Clear settings cache to pick up new environment variables
get_settings.cache_clear()
settings = get_settings()
data_dir = settings.directories.data_dir
test_data_dir = settings.directories.test_data_dir
mock_correlated_file = test_data_dir / "correlated.json"
dummy_correlated_file = data_dir / "correlated.json"


@pytest.fixture(autouse=True)
def mock_dependencies():
    """Mock all external dependencies."""
    mock_tokenizer = MockGeminiTokenizer()
    with patch(
        "clients.local_llm_client.create_local_llm", side_effect=create_mock_llm
    ), patch(
        "clients.gemini_llm_client.create_gemini_llm", side_effect=create_mock_llm
    ), patch(
        "utils.gemini_tokenizer.GeminiTokenizer", return_value=mock_tokenizer
    ):
        yield


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment before each test."""
    settings.processing.summarize_enabled = True
    settings.api.llm_provider = "local"  # Use local mock LLM
    delete_all_in_directory(data_dir)
    copy_file(src_path=mock_correlated_file, dest_dir=data_dir)
    yield


class TestSummarizer:
    """Test cases for Summarizer class."""

    def test_summarize_disabled(self):
        """Test that summarization is skipped when disabled."""
        settings.processing.summarize_enabled = False
        summarizer = Summarizer(settings)
        summarizer.summarize()
        assert not os.path.exists(data_dir / "summaries")

    def test_summarize_enabled(self):
        """Test that summarization works when enabled."""
        setup_dummy_test_data()
        summarizer = Summarizer(settings)
        summarizer.summarize()

        # Check that summary.txt was created in data directory
        summary_file_path = data_dir / "summary.txt"
        assert os.path.exists(summary_file_path), "summary.txt was not created"

    def test_summarize(self):
        """Test basic summarization functionality."""
        summarizer = Summarizer(settings)
        summarizer.summarize()

        # Check that summary.txt was created in data directory
        summary_file_path = data_dir / "summary.txt"
        assert os.path.exists(summary_file_path), "summary.txt was not created"

        with open(summary_file_path, "r") as f:
            summary_content = f.read()

        assert len(summary_content.strip()) > 10, "summary.txt is empty"


class TestMapReduceSummarizer:
    """Test cases for MapReduce summarizer functionality."""

    def test_summarizer_initialization(self):
        """Test that MapReduceChainManager is properly initialized."""
        summarizer = Summarizer(settings)
        assert isinstance(summarizer.map_reducer, MapReduceSummarizer)

    def test_summarization_with_reduce(self):
        """Test summarization with reduce enabled."""
        settings.processing.reduce_enabled = True
        test_data = {
            "Project1": {
                "Epic1": {"description": "A" * 10000},
                "Story1": {"description": "Story description"},
            },
            "Project2": {"Epic2": {"description": "B" * 10000}},
        }
        with open(dummy_correlated_file, "w") as f:
            json.dump(test_data, f)

        summarizer = Summarizer(settings)
        summarizer.summarize()

        # Verify the summary was created with proper structure
        summary_file_path = data_dir / "summary.txt"
        assert os.path.exists(summary_file_path)

        with open(summary_file_path, "r") as f:
            content = f.read()

        assert "Mock summary" in content

    def test_summarization_without_reduce(self):
        """Test summarization with reduce disabled."""
        settings.processing.reduce_enabled = False
        test_data = {
            "Project1": {
                "Epic1": {"description": "A" * 10000},
                "Story1": {"description": "Story description"},
            },
            "Project2": {"Epic2": {"description": "B" * 10000}},
        }
        with open(dummy_correlated_file, "w") as f:
            json.dump(test_data, f)

        summarizer = Summarizer(settings)
        summarizer.summarize()

        # Verify the summary was created with proper structure
        summary_file_path = data_dir / "summary.txt"
        assert os.path.exists(summary_file_path)

        with open(summary_file_path, "r") as f:
            content = f.read()

        assert "Mock summary" in content

    def test_error_handling(self):
        """Test error handling during summarization."""
        # Create a failing mock chain
        failing_chain = MockChains(settings)
        failing_chain.parameterized_summarize_chain.invoke = lambda x: (
            _ for _ in ()
        ).throw(Exception("Test error"))

        summarizer = Summarizer(settings, chains=failing_chain)
        with pytest.raises(RuntimeError):
            summarizer.summarize()

    def test_debug_output(self):
        """Test debug output generation."""
        settings.processing.debug = True
        test_data = {"test": "data"}
        with open(dummy_correlated_file, "w") as f:
            json.dump(test_data, f)

        summarizer = Summarizer(settings)
        summarizer.summarize()

        # Verify summary file was created
        summary_file_path = data_dir / "summary.txt"
        assert os.path.exists(summary_file_path)

        with open(summary_file_path, "r") as f:
            content = f.read()

        assert "Mock summary" in content

    def test_json_splitting(self):
        """Test JSON object splitting functionality."""
        settings.processing.reduce_enabled = True
        # Test data with various JSON patterns
        test_data = {
            "large_object": {
                "field1": "A" * 5000,  # Large text field
                "field2": ["B" * 1000] * 5,  # Large array
                "field3": {  # Nested object
                    "nested1": "C" * 3000,
                    "nested2": ["D" * 500] * 6,
                },
            },
            "small_object": {"field1": "Small text", "field2": [1, 2, 3]},
        }

        summarizer = Summarizer(settings)
        # Mock the tokenizer to avoid API calls
        mock_tokenizer = MockGeminiTokenizer()
        summarizer.map_reducer.tokenizer = mock_tokenizer
        result = summarizer.map_reducer.process_text("test", test_data)

        # Verify the structure of the result
        assert "final_summary" in result
        assert "chunk_summaries" in result
        assert "metadata" in result

        # Verify chunks were created
        assert len(result["chunk_summaries"]) > 1

        # Verify metadata
        assert result["metadata"]["reduce_enabled"] is True
        assert result["metadata"]["total_chunks"] > 1

    def test_markdown_formatting(self):
        """Test proper markdown formatting in summaries."""
        settings.processing.reduce_enabled = True
        settings.api.jira_server = "https://jira.example.com"
        test_data = {
            "Project1": {
                "epics": [
                    {
                        "key": "EPIC-1",
                        "title": "Epic 1",
                        "description": "Description 1",
                        "epic_key": "EPIC-2",
                    },
                    {
                        "key": "EPIC-2",
                        "title": "Epic 2",
                        "description": "Description 2",
                    },
                ],
                "stories": [
                    {
                        "key": "STORY-1",
                        "title": "Story 1",
                        "description": "Story details",
                        "epic_key": "EPIC-1",
                    }
                ],
            }
        }

        summarizer = Summarizer(settings)
        result = summarizer.summarize_projects(test_data)

        # Verify markdown structure
        lines = result.split("\n")

        # Check project header
        assert any(line.startswith("## Project1") for line in lines)

        # Check JIRA links in headers
        assert any(
            "[EPIC-1](https://jira.example.com/browse/EPIC-1)" in line for line in lines
        )
        assert any(
            "[EPIC-2](https://jira.example.com/browse/EPIC-2)" in line for line in lines
        )
        assert any(
            "[STORY-1](https://jira.example.com/browse/STORY-1)" in line
            for line in lines
        )

        # Check epic links
        assert any(
            "[EPIC-2](https://jira.example.com/browse/EPIC-2)" in line for line in lines
        )
        assert any(
            "[EPIC-1](https://jira.example.com/browse/EPIC-1)" in line for line in lines
        )

        # Check spacing
        for i in range(len(lines) - 1):
            if lines[i].startswith("#"):
                # Headers should be followed by blank line
                assert (
                    lines[i + 1].strip() == ""
                ), f"Header not followed by blank line: {lines[i]}"

    def test_mixed_content_handling(self):
        """Test handling of mixed JSON and text content."""
        settings.processing.reduce_enabled = True
        test_data = {
            "text_field": "Regular text content",
            "json_field": {"nested": {"description": "A" * 5000}},  # Large text in JSON
            "array_field": ["B" * 1000] * 5,  # Large array
        }

        summarizer = Summarizer(settings)
        # Mock the tokenizer to avoid API calls
        mock_tokenizer = MockGeminiTokenizer()
        summarizer.map_reducer.tokenizer = mock_tokenizer
        result = summarizer.map_reducer.process_text("test", test_data)

        # Verify proper handling of different content types
        for summary in result["chunk_summaries"]:
            assert "content_type" in summary["metadata"]
            assert "token_count" in summary["metadata"]
            assert "chunk_index" in summary["metadata"]
            assert "total_chunks" in summary["metadata"]

    def test_empty_content_handling(self):
        """Test handling of empty or None content."""
        summarizer = Summarizer(settings)

        # Test with None
        result = summarizer.map_reducer.process_text("test", None)
        assert result["final_summary"] == ""
        assert len(result["chunk_summaries"]) == 0

        # Test with empty dict
        result = summarizer.map_reducer.process_text("test", {})
        assert isinstance(result["final_summary"], str)
        assert isinstance(result["chunk_summaries"], list)

        # Test with empty string
        result = summarizer.map_reducer.process_text("test", "")
        assert result["final_summary"] == ""
        assert len(result["chunk_summaries"]) == 0

    def test_reduce_chain_error_handling(self):
        """Test error handling in reduce chain."""
        settings.processing.reduce_enabled = True
        failing_chains = MockChains(settings)

        # Make reduce chain fail
        def failing_invoke(*args, **kwargs):
            raise Exception("Reduce chain error")

        failing_chains.reduce_chain.invoke = failing_invoke

        summarizer = Summarizer(settings, chains=failing_chains)
        test_data = {"field": "A" * 5000}  # Force chunking

        # Mock the tokenizer to avoid API calls
        mock_tokenizer = MockGeminiTokenizer()
        summarizer.map_reducer.tokenizer = mock_tokenizer

        result = summarizer.map_reducer.process_text("test", test_data)
        assert "Error" in result["final_summary"]

    def test_map_chain_error_handling(self):
        """Test error handling in map chain."""
        failing_chains = MockChains(settings)

        # Make map chain fail
        def failing_invoke(*args, **kwargs):
            raise Exception("Map chain error")

        failing_chains.map_chain.invoke = failing_invoke

        summarizer = Summarizer(settings, chains=failing_chains)
        test_data = {"field": "A" * 5000}  # Force chunking

        # Mock the tokenizer to avoid API calls
        mock_tokenizer = MockGeminiTokenizer()
        summarizer.map_reducer.tokenizer = mock_tokenizer

        result = summarizer.map_reducer.process_text("test", test_data)
        assert any(
            "Error" in summary["content"] for summary in result["chunk_summaries"]
        )


class TestRateLimiting:
    """Test cases for rate limiting functionality."""

    @pytest.fixture(autouse=True)
    def setup_rate_limiting(self):
        """Set up rate limiting test environment."""
        settings.api.max_requests_per_day = 2  # Set low limit for testing
        delete_all_in_directory(data_dir)
        copy_file(src_path=mock_correlated_file, dest_dir=data_dir)
        self.mock_chains = MockChains(settings)
        self.rate_limiter = MockRateLimiter(settings)
        yield

    def test_rate_limit_counter(self):
        """Test that rate limit counter increments correctly."""
        # Set up mock rate limiter for all chains
        self.mock_chains.set_rate_limiter(self.rate_limiter)
        summarizer = Summarizer(settings, chains=self.mock_chains)

        # First call should work
        result1 = summarizer._summarize("test1", "value1")
        assert self.rate_limiter.rpd_counter == 1
        assert "Mock summary for: test1" in result1

        # Second call should work
        result2 = summarizer._summarize("test2", "value2")
        assert self.rate_limiter.rpd_counter == 2
        assert "Mock summary for: test2" in result2

        # Third call should raise error
        with pytest.raises(RuntimeError) as exc_info:
            summarizer._summarize("test3", "value3")
        assert "Daily API request limit exceeded" in str(exc_info.value)
        assert self.rate_limiter.rpd_counter == 2  # Counter shouldn't increment

    def test_rate_limit_on_failure(self):
        """Test that rate limit counter doesn't increment on failure."""
        failing_chains = MockChains(settings)
        failing_chains.llm_client.rate_limiter = self.rate_limiter
        failing_chains.llm_client.rate_limiter.should_fail = True

        summarizer = Summarizer(settings, chains=failing_chains)
        assert self.rate_limiter.rpd_counter == 0  # Start with 0

        # Call should fail but not increment counter
        with pytest.raises(RuntimeError, match="Test rate limit error"):
            summarizer._summarize("test", "value")
        assert self.rate_limiter.rpd_counter == 0  # Should still be 0

    def test_rate_limit_across_methods(self):
        """Test that rate limit applies across different methods."""
        self.mock_chains.llm_client.rate_limiter = self.rate_limiter
        summarizer = Summarizer(settings, chains=self.mock_chains)

        # Use up limit with first call
        summarizer._summarize("test1", "value1")
        assert self.rate_limiter.rpd_counter == 1

        # Use up remaining limit with second call
        summarizer._summarize("test2", "value2")
        assert self.rate_limiter.rpd_counter == 2

        # Both subsequent calls should fail
        with pytest.raises(RuntimeError):
            summarizer._summarize("test3", "value3")
        with pytest.raises(RuntimeError):
            summarizer._summarize("test4", "value4")


def setup_dummy_test_data():
    """Set up dummy test data."""
    test_data = {"test": "data"}
    with open(dummy_correlated_file, "w") as f:
        json.dump(test_data, f)
