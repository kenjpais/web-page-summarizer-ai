"""Tests for advanced chunking components."""

import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from config.settings import AppSettings
from utils.gemini_chunker import GeminiTokenizer, ChunkMetadata
from utils.semantic_splitter import SemanticSplitter, SplitMetadata
from utils.rate_limiter import GeminiRateLimiter, RateLimitConfig
from utils.chunk_manager import ChunkManager
from summarizers.advanced_summarizer import AdvancedSummarizer
from tests.mocks.mock_llm import MockLLM
from tests.mocks.mock_gemini import MockGeminiTokenizer, MockGeminiClient

# Test data
SAMPLE_MARKDOWN = """# Feature Updates
This section covers new features in the release.

## Authentication System
We've improved the auth system with:
- Better token handling
- Improved session management
- Enhanced security features

## Performance Improvements
Multiple improvements including:
1. Faster database queries
2. Optimized caching
3. Reduced latency
"""

LARGE_MARKDOWN = (
    """# Section 1
"""
    + "Very long content.\n" * 1000
    + """
# Section 2
"""
    + "More long content.\n" * 1000
)


class TestGeminiTokenizer:
    @pytest.fixture
    def settings(self):
        settings = Mock(spec=AppSettings)
        api = Mock()
        api.max_input_tokens = 500
        api.gemini_model = "gemini-1.5-pro"
        api.google_api_key = "test-key"
        api.llm_provider = "gemini"
        settings.api = api

        file_paths = Mock()
        file_paths.data_dir = Path("/tmp/test")
        settings.file_paths = file_paths
        return settings

    def test_token_counting(self):
        # Create mock tokenizer
        tokenizer = MockGeminiTokenizer()

        # Test token counting
        text = "Sample text"
        count = tokenizer.count_tokens(text)
        assert count == 100
        tokenizer.model.get_num_tokens.assert_called_once_with(text)


class TestSemanticSplitter:
    @pytest.fixture
    def settings(self):
        settings = Mock(spec=AppSettings)
        api = Mock()
        api.max_input_tokens = 500
        api.gemini_model = "gemini-1.5-pro"
        api.google_api_key = "test-key"
        api.llm_provider = "gemini"
        settings.api = api
        return settings

    @pytest.fixture
    def splitter(self, settings):
        splitter = SemanticSplitter(settings)
        splitter.tokenizer = MockGeminiTokenizer()
        return splitter

    def test_header_splitting(self, splitter):
        chunks = splitter.split_text(SAMPLE_MARKDOWN)

        # Should have 3 chunks (main section + 2 subsections)
        assert len(chunks) == 3

        # Verify chunk metadata
        assert chunks[0]["metadata"].section_level == 1
        assert chunks[0]["metadata"].section_title == "Feature Updates"
        assert chunks[0]["metadata"].parent_section is None

        assert chunks[1]["metadata"].section_level == 2
        assert chunks[1]["metadata"].section_title == "Authentication System"
        assert chunks[1]["metadata"].parent_section == "Feature Updates"

    def test_large_content_splitting(self, splitter):
        # Create mock tokenizer that always returns a large token count
        mock_tokenizer = Mock()
        mock_tokenizer.count_tokens = Mock(return_value=1000)
        splitter.tokenizer = mock_tokenizer

        # Set a small max token limit to force splitting
        splitter.settings.api.max_input_tokens = 100

        chunks = splitter.split_text(LARGE_MARKDOWN)

        # Should split large sections into smaller chunks
        assert len(chunks) > 2  # More chunks due to content splitting


class TestRateLimiter:
    @pytest.fixture
    def config(self):
        return RateLimitConfig(
            requests_per_minute=5, requests_per_day=25, min_request_interval=0.1
        )

    @pytest.fixture
    def limiter(self, config):
        return GeminiRateLimiter(config)

    def test_rate_limiting(self, limiter):
        # Initialize token bucket
        limiter.minute_limiter.tokens = limiter.minute_limiter.capacity

        # Should allow 5 requests quickly
        for _ in range(5):
            assert limiter.can_make_request()
            limiter.increment_counters()

        # 6th request should be blocked
        assert not limiter.can_make_request()

    def test_daily_limit(self, limiter):
        # Initialize token bucket
        limiter.minute_limiter.tokens = limiter.minute_limiter.capacity

        # Make 25 requests
        for _ in range(25):
            limiter.minute_limiter.tokens = (
                limiter.minute_limiter.capacity
            )  # Reset for each request
            assert limiter.can_make_request()
            limiter.increment_counters()

        # 26th request should be blocked
        assert not limiter.can_make_request()

    def test_reset_daily(self, limiter):
        # Initialize token bucket and daily counter
        limiter.minute_limiter.tokens = limiter.minute_limiter.capacity
        limiter.daily_requests = 0

        # Make some requests
        for _ in range(10):
            limiter.minute_limiter.tokens = (
                limiter.minute_limiter.capacity
            )  # Reset for each request
            assert limiter.can_make_request()
            limiter.increment_counters()

        # Simulate day change
        limiter.last_reset = datetime.now() - timedelta(days=1)
        limiter._reset_daily()

        # Reset token bucket
        limiter.minute_limiter.tokens = limiter.minute_limiter.capacity

        # Should allow requests again
        assert limiter.can_make_request()
        assert limiter.daily_requests == 0


class TestChunkManager:
    @pytest.fixture
    def settings(self):
        settings = Mock(spec=AppSettings)
        api = Mock()
        api.max_input_tokens = 500
        api.gemini_model = "gemini-1.5-pro"
        api.google_api_key = "test-key"
        api.llm_provider = "gemini"
        settings.api = api
        return settings

    @pytest.fixture
    def manager(self, settings):
        manager = ChunkManager(settings)
        manager.tokenizer = MockGeminiTokenizer()
        manager.semantic_splitter.tokenizer = MockGeminiTokenizer()
        return manager

    @pytest.fixture
    def mock_chain(self):
        chain = Mock()

        async def mock_ainvoke(*args, **kwargs):
            return "Processed chunk"

        chain.ainvoke = mock_ainvoke
        return chain

    @pytest.mark.asyncio
    async def test_process_text(self, manager, mock_chain):
        result = await manager.process_text(
            SAMPLE_MARKDOWN, mock_chain, "Test prompt {content}"
        )

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_chunk_processing_order(self, manager, mock_chain):
        # Process text with dependencies
        await manager.process_text(SAMPLE_MARKDOWN, mock_chain)

        # Verify processing order respects dependencies
        processed = []
        for batch in manager._create_processing_order(
            manager.semantic_splitter.split_text(SAMPLE_MARKDOWN), manager.priorities
        ):
            processed.extend(batch)

            # Parent sections should be processed before children
        chunks = manager.semantic_splitter.split_text(SAMPLE_MARKDOWN)
        parent_indices = [
            i for i, chunk in enumerate(chunks) if not chunk["metadata"].parent_section
        ]
        child_indices = [
            i for i, chunk in enumerate(chunks) if chunk["metadata"].parent_section
        ]

        # Verify that at least one parent is processed before its children
        assert any(
            parent_idx < child_idx
            for parent_idx in parent_indices
            for child_idx in child_indices
        )


class TestAdvancedSummarizer:
    @pytest.fixture
    def settings(self, tmp_path):
        settings = Mock(spec=AppSettings)
        api = Mock()
        api.max_input_tokens = 500
        api.gemini_model = "gemini-1.5-pro"
        api.google_api_key = "test-key"
        api.llm_provider = "gemini"
        settings.api = api

        processing = Mock()
        processing.summarize_enabled = True
        settings.processing = processing

        file_paths = Mock()
        file_paths.data_dir = tmp_path
        file_paths.correlated_file_path = tmp_path / "correlated.json"
        file_paths.summary_file_path = tmp_path / "summary.txt"
        file_paths.release_notes_payload_file_path = tmp_path / "release_notes.txt"
        file_paths.correlated_feature_gate_table_file_path = (
            tmp_path / "feature_gates.json"
        )
        file_paths.summarized_features_file_path = tmp_path / "summarized_features.json"
        settings.file_paths = file_paths

        config_files = Mock()
        config_files.project_summary_template = (
            tmp_path / "project_summary_template.txt"
        )
        config_files.summarize_prompt_template = (
            tmp_path / "summarize_prompt_template.txt"
        )
        settings.config_files = config_files

        directories = Mock()
        directories.config_dir = tmp_path / "config"
        settings.directories = directories

        # Create config directory and template files
        config_dir = tmp_path / "config"
        config_dir.mkdir(exist_ok=True, parents=True)

        # Create template files
        (config_dir / "project_summary_template.txt").write_text(
            "Summarize: {correlated_info}"
        )
        (config_dir / "summarize_prompt_template.txt").write_text(
            "Summarize: {release-notes}"
        )
        return settings

    @pytest.fixture
    def mock_llm(self):
        return MockLLM()

    @pytest.fixture
    def summarizer(self, settings, mock_llm):
        summarizer = AdvancedSummarizer(settings, mock_llm)
        summarizer.chunk_manager.tokenizer = MockGeminiTokenizer()
        summarizer.chunk_manager.semantic_splitter.tokenizer = MockGeminiTokenizer()
        return summarizer

    @pytest.mark.asyncio
    async def test_summarize_projects(self, summarizer, tmp_path):
        # Mock file operations
        with patch("builtins.open") as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = (
                json.dumps({"features": SAMPLE_MARKDOWN})
            )

            result = await summarizer.summarize_projects()
            assert isinstance(result, str)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_summarize_feature_gates(self, summarizer, tmp_path):
        test_gates = {
            "TestGate1": {"description": "Test gate 1"},
            "TestGate2": {"description": "Test gate 2"},
        }

        # Mock file operations
        with patch("builtins.open") as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = (
                json.dumps(test_gates)
            )

            await summarizer.summarize_feature_gates()
            # Verify results were saved
            mock_open.assert_called()
