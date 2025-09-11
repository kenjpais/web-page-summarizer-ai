"""Tests for MapReduceChainManager."""

import json
import pytest
from unittest.mock import patch, MagicMock
from config.settings import AppSettings
from summarizers.summarizer import MapReduceSummarizer
from langchain_core.documents import Document
from chains.chains import Chains


@pytest.fixture
def settings():
    """Create test settings."""
    settings = AppSettings()
    settings.api.llm_provider = "local"
    settings.api.llm_model = "mistral"
    settings.api.max_input_tokens_per_request = 8192
    settings.api.chunk_overlap = 500
    settings.processing.reduce_enabled = True
    return settings


@pytest.fixture
def gemini_settings():
    """Create test settings for Gemini."""
    settings = AppSettings()
    settings.api.llm_provider = "gemini"
    settings.api.llm_model = "gemini-pro"
    settings.api.max_input_tokens_per_request = 1_048_576
    settings.api.chunk_overlap = 1000
    settings.processing.reduce_enabled = True
    return settings


class MockTokenizer:
    """Mock tokenizer for testing."""

    def count_tokens(self, text: str) -> int:
        """Mock token counting."""
        if isinstance(text, (dict, list)):
            text = json.dumps(text)
        return len(str(text)) // 4  # Simple approximation


class MockChain:
    """Mock chain for testing."""

    def invoke(self, inputs: dict) -> str:
        """Mock invoke method."""
        key = inputs.get("key", "")
        value = inputs.get("value", "")
        if not value:
            return ""
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        return f"Summary of {key}: {str(value)[:50]}..."


@pytest.fixture
def mock_chains(settings):
    """Create mock chains."""
    chains = MagicMock(spec=Chains)
    chains.map_chain = MockChain()
    chains.reduce_chain = MockChain()
    return chains


def test_initialization(settings, mock_chains):
    """Test MapReduceSummarizer initialization."""
    manager = MapReduceSummarizer(
        map_chain=mock_chains.map_chain,
        reduce_chain=mock_chains.reduce_chain,
        tokenizer=MockTokenizer(),
        settings=settings,
    )
    assert manager.settings == settings
    assert manager.chunk_size == int(settings.api.max_input_tokens_per_request * 0.1)
    assert manager.chunk_overlap == settings.api.chunk_overlap


def test_split_content_text(settings, mock_chains):
    """Test text content splitting functionality."""
    text = """# Section 1
Content for section 1

## Subsection 1.1
Content for subsection 1.1

# Section 2
Content for section 2"""

    manager = MapReduceSummarizer(
        map_chain=mock_chains.map_chain,
        reduce_chain=mock_chains.reduce_chain,
        tokenizer=MockTokenizer(),
        settings=settings,
    )
    docs = manager.split_content(text)

    assert len(docs) > 0
    assert all(isinstance(doc, Document) for doc in docs)
    assert all("content_type" in doc.metadata for doc in docs)
    assert all("token_count" in doc.metadata for doc in docs)
    assert all("chunk_index" in doc.metadata for doc in docs)
    assert all("total_chunks" in doc.metadata for doc in docs)


def test_split_content_json(settings, mock_chains):
    """Test JSON content splitting functionality."""
    json_data = {
        "section1": {"title": "Test Section 1", "content": "A" * 5000},
        "section2": {"title": "Test Section 2", "content": "B" * 5000},
    }

    manager = MapReduceSummarizer(
        map_chain=mock_chains.map_chain,
        reduce_chain=mock_chains.reduce_chain,
        tokenizer=MockTokenizer(),
        settings=settings,
    )
    docs = manager.split_content(json_data)

    assert len(docs) > 0
    assert all(isinstance(doc, Document) for doc in docs)
    assert all("content_type" in doc.metadata for doc in docs)
    assert all(doc.metadata["content_type"] == "json" for doc in docs)
    assert all("token_count" in doc.metadata for doc in docs)


def test_process_text_with_reduce(settings, mock_chains):
    """Test text processing with full MapReduce pattern."""
    text = """# Project A
Description of project A

# Project B
Description of project B"""

    manager = MapReduceSummarizer(
        map_chain=mock_chains.map_chain,
        reduce_chain=mock_chains.reduce_chain,
        tokenizer=MockTokenizer(),
        settings=settings,
    )
    result = manager.process_text("test", text)

    assert "final_summary" in result
    assert "section_summaries" in result
    assert "chunk_summaries" in result
    assert "metadata" in result
    assert result["metadata"]["reduce_enabled"] is True
    assert result["metadata"]["total_chunks"] > 0
    assert len(result["chunk_summaries"]) > 0


def test_process_text_without_reduce(settings, mock_chains):
    """Test text processing with Map-only pattern."""
    settings.processing.reduce_enabled = False
    text = """# Project A
Description of project A

# Project B
Description of project B"""

    manager = MapReduceSummarizer(
        map_chain=mock_chains.map_chain,
        reduce_chain=mock_chains.reduce_chain,
        tokenizer=MockTokenizer(),
        settings=settings,
    )
    result = manager.process_text("test", text)

    assert "final_summary" in result
    assert "section_summaries" in result
    assert "chunk_summaries" in result
    assert "metadata" in result
    assert result["metadata"]["reduce_enabled"] is False
    assert result["metadata"]["total_chunks"] > 0
    assert len(result["chunk_summaries"]) > 0


def test_process_text_with_large_sections(settings, mock_chains):
    """Test processing text with sections that need further splitting."""
    large_text = (
        """# Large Section
"""
        + "A" * 10000
        + """

# Small Section
Small content"""
    )

    manager = MapReduceSummarizer(
        map_chain=mock_chains.map_chain,
        reduce_chain=mock_chains.reduce_chain,
        tokenizer=MockTokenizer(),
        settings=settings,
    )
    result = manager.process_text("test", large_text)

    assert result["metadata"]["total_chunks"] >= 2  # Should have at least 2 sections
    assert len(result["section_summaries"]) == 2  # Two main sections


def test_process_text_with_json(settings, mock_chains):
    """Test processing JSON content."""
    json_data = {
        "project": "Test Project",
        "sections": [
            {"title": "Section 1", "content": "A" * 5000},
            {"title": "Section 2", "content": "B" * 5000},
        ],
    }

    manager = MapReduceSummarizer(
        map_chain=mock_chains.map_chain,
        reduce_chain=mock_chains.reduce_chain,
        tokenizer=MockTokenizer(),
        settings=settings,
    )
    result = manager.process_text("test", json_data)

    assert "final_summary" in result
    assert "section_summaries" in result
    assert "chunk_summaries" in result
    assert "metadata" in result
    assert result["metadata"]["total_chunks"] > 0
    assert len(result["chunk_summaries"]) > 0


def test_error_handling_map_chain(settings, mock_chains):
    """Test error handling during map phase."""
    text = "Test content"
    mock_chains.map_chain.invoke = MagicMock(side_effect=Exception("Map chain error"))

    manager = MapReduceSummarizer(
        map_chain=mock_chains.map_chain,
        reduce_chain=mock_chains.reduce_chain,
        tokenizer=MockTokenizer(),
        settings=settings,
    )
    result = manager.process_text("test", text)

    assert "Error" in result["chunk_summaries"][0]["content"]
    assert result["metadata"]["total_chunks"] > 0


def test_error_handling_reduce_chain(settings, mock_chains):
    """Test error handling during reduce phase."""
    text = """# Section 1
Content 1

# Section 2
Content 2"""
    mock_chains.reduce_chain.invoke = MagicMock(
        side_effect=Exception("Reduce chain error")
    )

    manager = MapReduceSummarizer(
        map_chain=mock_chains.map_chain,
        reduce_chain=mock_chains.reduce_chain,
        tokenizer=MockTokenizer(),
        settings=settings,
    )
    result = manager.process_text("test", text)

    assert "Error" in result["final_summary"]
    assert result["metadata"]["total_chunks"] > 0


def test_empty_content_handling(settings, mock_chains):
    """Test handling of empty or None content."""
    manager = MapReduceSummarizer(
        map_chain=mock_chains.map_chain,
        reduce_chain=mock_chains.reduce_chain,
        tokenizer=MockTokenizer(),
        settings=settings,
    )

    # Test with None
    result = manager.process_text("test", None)
    assert result["final_summary"] == ""
    assert len(result["chunk_summaries"]) == 0
    assert result["metadata"]["total_chunks"] == 0
    assert result["metadata"]["total_tokens"] == 0

    # Test with empty string
    result = manager.process_text("test", "")
    assert result["final_summary"] == ""
    assert len(result["chunk_summaries"]) == 0
    assert result["metadata"]["total_chunks"] == 0
    assert result["metadata"]["total_tokens"] == 0

    # Test with empty dict
    result = manager.process_text("test", {})
    assert result["final_summary"] == ""
    assert len(result["chunk_summaries"]) == 0
    assert result["metadata"]["total_chunks"] == 0
    assert result["metadata"]["total_tokens"] == 0


def test_combine_summaries_simple(settings, mock_chains):
    """Test simple summary combination without reduce chain."""
    manager = MapReduceSummarizer(
        map_chain=mock_chains.map_chain,
        reduce_chain=mock_chains.reduce_chain,
        tokenizer=MockTokenizer(),
        settings=settings,
    )

    summaries = ["Summary 1", "Summary 2"]
    sections = ["Section 1", "Section 2"]
    combined = manager.combine_summaries_simple(summaries, sections)

    assert "## Section 1\nSummary 1" in combined
    assert "## Section 2\nSummary 2" in combined
