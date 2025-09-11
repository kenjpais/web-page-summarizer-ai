"""Tests for GeminiTokenizer."""

import pytest
from unittest.mock import patch, MagicMock
from config.settings import AppSettings
from utils.gemini_tokenizer import GeminiTokenizer


@pytest.fixture
def settings():
    """Create test settings."""
    settings = AppSettings()
    settings.api.llm_provider = "gemini"
    settings.api.gemini_model = "gemini-1.5-pro"
    settings.api.google_api_key = "test_key"
    return settings


@pytest.fixture
def mock_gemini_model():
    """Create mock Gemini model."""
    model = MagicMock()
    model.get_num_tokens = MagicMock(return_value=10)  # Default token count
    return model


def test_initialization(settings):
    """Test tokenizer initialization."""
    with patch("utils.gemini_tokenizer.ChatGoogleGenerativeAI") as mock_chat:
        mock_chat.return_value = MagicMock()
        tokenizer = GeminiTokenizer(settings)

        mock_chat.assert_called_once_with(
            model=settings.api.gemini_model,
            google_api_key=settings.api.google_api_key,
            temperature=0.0,
        )
        assert tokenizer.model == mock_chat.return_value


def test_count_tokens(settings, mock_gemini_model):
    """Test token counting functionality."""
    with patch("utils.gemini_tokenizer.ChatGoogleGenerativeAI") as mock_chat:
        mock_chat.return_value = mock_gemini_model
        tokenizer = GeminiTokenizer(settings)

        # Test with simple text
        text = "Hello, world!"
        mock_gemini_model.get_num_tokens.return_value = 3
        assert tokenizer.count_tokens(text) == 3
        mock_gemini_model.get_num_tokens.assert_called_with(text)

        # Test with empty text
        mock_gemini_model.get_num_tokens.return_value = 0
        assert tokenizer.count_tokens("") == 0

        # Test with long text
        long_text = "A" * 1000
        mock_gemini_model.get_num_tokens.return_value = 250
        assert tokenizer.count_tokens(long_text) == 250


def test_error_handling(settings, mock_gemini_model):
    """Test error handling during token counting."""
    with patch("utils.gemini_tokenizer.ChatGoogleGenerativeAI") as mock_chat:
        mock_chat.return_value = mock_gemini_model
        tokenizer = GeminiTokenizer(settings)

        # Test with API error
        mock_gemini_model.get_num_tokens.side_effect = Exception("API Error")
        with pytest.raises(Exception) as exc_info:
            tokenizer.count_tokens("test")
        assert "API Error" in str(exc_info.value)


def test_special_characters(settings, mock_gemini_model):
    """Test token counting with special characters."""
    with patch("utils.gemini_tokenizer.ChatGoogleGenerativeAI") as mock_chat:
        mock_chat.return_value = mock_gemini_model
        tokenizer = GeminiTokenizer(settings)

        # Test with newlines
        text = "Hello\nworld\n!"
        mock_gemini_model.get_num_tokens.return_value = 4
        assert tokenizer.count_tokens(text) == 4

        # Test with tabs
        text = "Hello\tworld\t!"
        mock_gemini_model.get_num_tokens.return_value = 4
        assert tokenizer.count_tokens(text) == 4

        # Test with unicode
        text = "Hello 👋 world! 🌍"
        mock_gemini_model.get_num_tokens.return_value = 6
        assert tokenizer.count_tokens(text) == 6


def test_code_snippets(settings, mock_gemini_model):
    """Test token counting with code snippets."""
    with patch("utils.gemini_tokenizer.ChatGoogleGenerativeAI") as mock_chat:
        mock_chat.return_value = mock_gemini_model
        tokenizer = GeminiTokenizer(settings)

        # Test with Python code
        code = """def hello():
            print("Hello, world!")
            return True"""
        mock_gemini_model.get_num_tokens.return_value = 15
        assert tokenizer.count_tokens(code) == 15

        # Test with JSON
        json_text = '{"key": "value", "numbers": [1, 2, 3]}'
        mock_gemini_model.get_num_tokens.return_value = 12
        assert tokenizer.count_tokens(json_text) == 12


def test_markdown_text(settings, mock_gemini_model):
    """Test token counting with markdown text."""
    with patch("utils.gemini_tokenizer.ChatGoogleGenerativeAI") as mock_chat:
        mock_chat.return_value = mock_gemini_model
        tokenizer = GeminiTokenizer(settings)

        # Test with markdown formatting
        markdown = """# Heading
        
        Some **bold** and *italic* text.
        
        - List item 1
        - List item 2
        
        ```python
        print("Hello")
        ```"""
        mock_gemini_model.get_num_tokens.return_value = 30
        assert tokenizer.count_tokens(markdown) == 30
