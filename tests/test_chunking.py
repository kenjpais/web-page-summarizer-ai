"""Tests for text chunking functionality."""

import json
import pytest
from unittest.mock import MagicMock
from config.settings import AppSettings
from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)


@pytest.fixture
def settings():
    """Create test settings."""
    settings = AppSettings()
    settings.api.max_input_tokens_per_request = 8192
    settings.api.chunk_overlap = 500
    return settings


@pytest.fixture
def mock_tokenizer():
    """Create mock tokenizer."""
    tokenizer = MagicMock()
    # Return a very small token count to force splitting
    tokenizer.count_tokens = lambda text: len(str(text)) // 10
    return tokenizer


def test_markdown_splitting():
    """Test markdown-aware text splitting."""
    text = """# Section 1
Content for section 1

## Subsection 1.1
Content for subsection 1.1

# Section 2
Content for section 2"""

    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "header1"),
            ("##", "header2"),
            ("###", "header3"),
        ]
    )
    docs = splitter.split_text(text)

    assert len(docs) == 3  # Two main sections and one subsection
    assert all(isinstance(doc, Document) for doc in docs)
    assert docs[0].metadata["header1"] == "Section 1"
    assert docs[1].metadata["header2"] == "Subsection 1.1"
    assert docs[2].metadata["header1"] == "Section 2"


def test_recursive_text_splitting(mock_tokenizer):
    """Test recursive text splitting."""
    text = "A" * 500 + "\n\n" + "B" * 500  # Smaller text to match token limit

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=50,  # Small chunk size to force splitting
        chunk_overlap=10,
        length_function=mock_tokenizer.count_tokens,
        separators=["\n\n", "\n", ". ", ", ", " ", ""],
    )
    docs = splitter.split_text(text)

    assert len(docs) > 1  # Should split into multiple chunks
    assert all(
        mock_tokenizer.count_tokens(doc) <= 50 for doc in docs
    )  # Each chunk within token limit


def test_json_splitting(mock_tokenizer):
    """Test JSON content splitting."""
    json_data = {
        "section1": {"title": "Test Section 1", "content": "A" * 500},
        "section2": {"title": "Test Section 2", "content": "B" * 500},
    }

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=50,  # Small chunk size to force splitting
        chunk_overlap=10,
        length_function=mock_tokenizer.count_tokens,
        separators=["\n\n", "\n", ". ", ", ", " ", ""],
    )
    docs = splitter.split_text(json.dumps(json_data))

    assert len(docs) > 1  # Should split into multiple chunks
    assert all(
        mock_tokenizer.count_tokens(doc) <= 50 for doc in docs
    )  # Each chunk within token limit


def test_mixed_content_splitting(mock_tokenizer):
    """Test splitting mixed content (markdown + JSON)."""
    content = (
        """# Project Overview
This is a test project.

## Configuration
```json
{
    "setting1": "value1",
    "setting2": {
        "nested": "value2",
        "data": """
        + "A" * 500
        + """
    }
}
```

## Results
Here are the test results."""
    )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=50,  # Small chunk size to force splitting
        chunk_overlap=10,
        length_function=mock_tokenizer.count_tokens,
        separators=["\n\n", "\n", ". ", ", ", " ", ""],
    )
    docs = splitter.split_text(content)

    assert len(docs) > 1  # Should split into multiple chunks
    assert all(
        mock_tokenizer.count_tokens(doc) <= 50 for doc in docs
    )  # Each chunk within token limit


def test_empty_content_handling():
    """Test handling of empty content."""
    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=[("#", "header1")])

    # Test empty string
    docs = splitter.split_text(
        "# Empty\nEmpty content\n"
    )  # Need at least a header and content
    assert len(docs) == 1
    assert docs[0].page_content.strip() == "Empty content"

    # Test whitespace only
    docs = splitter.split_text("# Whitespace\nWhitespace content\n")
    assert len(docs) == 1
    assert docs[0].page_content.strip() == "Whitespace content"


def test_special_characters_handling(mock_tokenizer):
    """Test handling of special characters."""
    text = (
        """# Section 1
Special chars: !@#$%^&*()
Unicode: 👋🌍🚀
Tabs and newlines:
    indented
        more indented

# Section 2
More special content"""
        + "\n"
        + "A" * 500
    )  # Add long text to force splitting

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=50,  # Small chunk size to force splitting
        chunk_overlap=10,
        length_function=mock_tokenizer.count_tokens,
        separators=["\n\n", "\n", ". ", ", ", " ", ""],
    )
    docs = splitter.split_text(text)

    assert len(docs) > 1  # Should split into multiple chunks
    assert all(
        mock_tokenizer.count_tokens(doc) <= 50 for doc in docs
    )  # Each chunk within token limit


def test_code_block_handling(mock_tokenizer):
    """Test handling of code blocks."""
    text = (
        """# Code Examples

## Python
```python
def example():
    print("Hello, world!")
    for i in range(10):
        print(i)
```

## JavaScript
```javascript
function example() {
    console.log("Hello, world!");
    for (let i = 0; i < 10; i++) {
        console.log(i);
    }
}
```"""
        + "\n"
        + "A" * 500
    )  # Add long text to force splitting

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=50,  # Small chunk size to force splitting
        chunk_overlap=10,
        length_function=mock_tokenizer.count_tokens,
        separators=["\n\n", "\n", ". ", ", ", " ", ""],
    )
    docs = splitter.split_text(text)

    assert len(docs) > 1  # Should split into multiple chunks
    assert all(
        mock_tokenizer.count_tokens(doc) <= 50 for doc in docs
    )  # Each chunk within token limit


def test_chunk_overlap(mock_tokenizer):
    """Test chunk overlap functionality."""
    text = "A" * 500 + " BREAK " + "B" * 500

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=50,  # Small chunk size to force splitting
        chunk_overlap=10,
        length_function=mock_tokenizer.count_tokens,
        separators=["\n\n", "\n", ". ", ", ", " ", ""],
    )
    docs = splitter.split_text(text)

    assert len(docs) > 1  # Should split into multiple chunks
    # Check for overlap
    for i in range(len(docs) - 1):
        overlap = set(docs[i][-10:]).intersection(set(docs[i + 1][:10]))
        assert len(overlap) > 0  # Should have some overlapping content
