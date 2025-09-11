"""Mock implementations for Gemini-related classes for testing."""


class MockGeminiTokenizer:
    """Mock implementation of GeminiTokenizer for testing."""

    def __init__(self, settings=None):
        self.settings = settings
        self.max_input_tokens = 1_048_576  # Gemini's limit
        self.max_output_tokens = 65_536
        self.chunk_size = int(self.max_input_tokens * 0.8)  # 80% of max tokens
        self.chunk_overlap = 1000  # tokens

    def count_tokens(self, text: str) -> int:
        """Mock token counting that forces chunking for test data."""
        if isinstance(text, (int, float)):
            return int(text)
        if not isinstance(text, str):
            text = str(text)

        # Handle test patterns for JSON and text content
        if any(
            pattern in text
            for pattern in ["A" * 5000, "B" * 1000, "C" * 3000, "D" * 500]
        ):
            # Return a large number for our test data to force chunking
            return self.max_input_tokens + 500

        # Handle large JSON objects
        if text.count("{") > 3 and len(text) > 1000:  # Complex nested JSON
            return self.max_input_tokens + 200

        if len(text) > 5000:  # Large text content
            return self.max_input_tokens + 100

        return len(text) // 4  # Normal approximation for other text
