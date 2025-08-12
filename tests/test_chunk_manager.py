import re
import pytest
from utils.chunk_manager import ChunkManager, ProcessedChunk, ChunkPriority
from utils.gemini_chunker import ChunkMetadata
from config.settings import AppSettings
from dataclasses import dataclass


@pytest.fixture
def settings():
    return AppSettings()


@pytest.fixture
def chunk_manager(settings):
    return ChunkManager(settings)


def create_test_chunk(
    content: str, section: str = "General", importance: float = 0.5
) -> ProcessedChunk:
    """Helper function to create test chunks"""
    metadata = ChunkMetadata(
        token_count=100, chunk_index=0, total_chunks=1, semantic_section=section
    )
    priority = ChunkPriority(importance=importance, dependencies=[], dependents=[])
    return ProcessedChunk(
        content=content,
        summary=content,  # Using content as summary for testing
        metadata=metadata,
        priority=priority,
    )


def test_remove_duplicate_intro(chunk_manager):
    """Test removal of duplicate introductory text"""
    test_text = """
This document summarizes the user-facing changes included in this software release.
Feature A is new.

Section 2
This document summarizes the user-facing changes included in this software release.
Feature B is updated.

This document details the user-facing changes included in OpenShift.
Feature C is deprecated.
"""
    cleaned_text = chunk_manager._remove_duplicate_intro(test_text)

    # The intro text should appear only once
    assert cleaned_text.count("This document summarizes") == 1
    assert cleaned_text.count("This document details") == 1

    # Content should be preserved
    assert "Feature A is new" in cleaned_text
    assert "Feature B is updated" in cleaned_text
    assert "Feature C is deprecated" in cleaned_text


def test_remove_duplicate_intro_case_insensitive(chunk_manager):
    """Test case-insensitive removal of duplicate intros"""
    test_text = """
This Document Summarizes the user-facing changes included in this software release.
Feature A.

this document summarizes the user-facing changes included in this software release.
Feature B.
"""
    cleaned_text = chunk_manager._remove_duplicate_intro(test_text)
    # Count occurrences case-insensitively
    assert sum(1 for _ in re.finditer(r"summarizes", cleaned_text.lower())) == 1
    assert "Feature A" in cleaned_text
    assert "Feature B" in cleaned_text


def test_merge_chunks_with_duplicates(chunk_manager):
    """Test merging chunks containing duplicate introductory text"""
    chunks = [
        create_test_chunk(
            "This document summarizes the user-facing changes included in this software release.\n"
            "Feature A is new.",
            "Section 1",
            0.8,
        ),
        create_test_chunk(
            "This document summarizes the user-facing changes included in this software release.\n"
            "Feature B is updated.",
            "Section 1",
            0.6,
        ),
        create_test_chunk(
            "Release Documentation\n" "Feature C is added.", "Section 2", 0.7
        ),
        create_test_chunk(
            "Release Documentation\n" "Feature D is modified.", "Section 2", 0.5
        ),
    ]

    merged_text = chunk_manager._merge_chunks(chunks)

    # Verify intro text appears only once per type
    assert merged_text.count("This document summarizes") == 1
    assert merged_text.count("Release Documentation") == 1

    # Verify all features are preserved
    assert "Feature A is new" in merged_text
    assert "Feature B is updated" in merged_text
    assert "Feature C is added" in merged_text
    assert "Feature D is modified" in merged_text


def test_merge_chunks_preserves_structure(chunk_manager):
    """Test that merging preserves section structure and ordering"""
    chunks = [
        create_test_chunk(
            "This document summarizes changes.\nFeature A.", "High Priority", 0.9
        ),
        create_test_chunk(
            "This document summarizes changes.\nFeature B.", "High Priority", 0.8
        ),
        create_test_chunk("Release Documentation\nFeature C.", "Low Priority", 0.4),
    ]

    merged_text = chunk_manager._merge_chunks(chunks)

    # Verify sections are preserved
    assert "# High Priority" in merged_text
    assert "# Low Priority" in merged_text

    # Verify content order
    high_priority_idx = merged_text.find("# High Priority")
    low_priority_idx = merged_text.find("# Low Priority")
    assert high_priority_idx < low_priority_idx

    # Verify features are preserved
    assert "Feature A" in merged_text
    assert "Feature B" in merged_text
    assert "Feature C" in merged_text


def test_merge_chunks_empty_sections(chunk_manager):
    """Test merging with empty sections"""
    chunks = [
        create_test_chunk("", "Empty Section", 0.5),
        create_test_chunk(
            "This document summarizes changes.\nFeature A.", "Content Section", 0.8
        ),
    ]

    merged_text = chunk_manager._merge_chunks(chunks)

    # Empty sections should be handled gracefully
    assert "Empty Section" not in merged_text
    assert "Feature A" in merged_text


def test_merge_chunks_with_varying_intro_patterns(chunk_manager):
    """Test handling of different intro text patterns"""
    chunks = [
        create_test_chunk(
            "This document summarizes the user-facing changes.\nFeature A.",
            "Section 1",
            0.8,
        ),
        create_test_chunk(
            "This document details the user-facing changes.\nFeature B.",
            "Section 1",
            0.7,
        ),
        create_test_chunk("Release Notes\nFeature C.", "Section 2", 0.6),
        create_test_chunk("Release Documentation\nFeature D.", "Section 2", 0.5),
    ]

    merged_text = chunk_manager._merge_chunks(chunks)

    # Each type of intro should appear only once
    assert merged_text.count("This document summarizes") == 1
    assert merged_text.count("This document details") == 1
    assert merged_text.count("Release Notes") == 1
    assert merged_text.count("Release Documentation") == 1

    # All features should be preserved
    assert "Feature A" in merged_text
    assert "Feature B" in merged_text
    assert "Feature C" in merged_text
    assert "Feature D" in merged_text
