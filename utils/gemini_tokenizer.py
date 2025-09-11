"""
Advanced text chunking utilities optimized for Gemini 1.5 Pro API.
Implements accurate token counting, rate limiting, and semantic chunking using MapReduce.
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from utils.logging_config import get_logger
from config.settings import AppSettings

logger = get_logger(__name__)


class GeminiTokenizer:
    """Accurate token counter for Gemini models using the official tokenizer"""

    def __init__(self, settings: AppSettings):
        # Initialize Gemini model for token counting
        self.model = ChatGoogleGenerativeAI(
            model=settings.api.gemini_model,
            google_api_key=settings.api.google_api_key,
            temperature=0.0,
        )

    def count_tokens(self, text: str) -> int:
        """
        Get accurate token count for text using Gemini's tokenizer

        Args:
            text: Input text to count tokens for

        Returns:
            Number of tokens in the text
        """
        return self.model.get_num_tokens(text)
