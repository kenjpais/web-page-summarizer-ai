"""Mock Gemini client for testing."""

from unittest.mock import Mock
from typing import Any, Dict, Optional, Union


class MockGeminiClient:
    """Mock Gemini client that returns predefined responses."""

    def __init__(self):
        self.get_num_tokens = Mock(return_value=100)
        self.count_tokens = Mock(return_value={"totalTokens": 100})
        self.invoke = Mock(return_value="Mock summary")
        self.ainvoke = Mock(return_value="Mock async summary")

    def __call__(self, *args, **kwargs):
        return self


class MockGeminiTokenizer:
    """Mock tokenizer that returns predefined token counts."""

    def __init__(self, settings=None):
        self.model = Mock()
        self.model.get_num_tokens = Mock(return_value=100)

    def count_tokens(self, text: str) -> int:
        """Return fixed token count for testing."""
        return self.model.get_num_tokens(text)
