"""
LLM Factory to choose between different LLM providers based on configuration.
"""

from langchain_core.runnables import Runnable
from config.settings import APISettings, AppSettings
from utils.rate_limiter import RateLimiter
from utils.logging_config import get_logger

logger = get_logger(__name__)


def get_llm(api_settings: APISettings) -> Runnable:
    """
    Factory function to get the appropriate LLM client based on configuration.

    Returns:
        Runnable: Either local_llm or gemini_llm based on LLM_PROVIDER setting

    Raises:
        ValueError: If the LLM provider is not supported or if required environment variables are missing
    """
    provider = api_settings.llm_provider.lower()

    if provider == "local":
        from clients.local_llm_client import create_local_llm

        return create_local_llm(api_settings)
    elif provider == "gemini":
        if not api_settings.google_api_key:
            raise ValueError(
                "GOOGLE_API_KEY environment variable is required when using Gemini provider. "
                "Get your API key from: https://makersuite.google.com/app/apikey"
            )

        try:
            from clients.gemini_llm_client import create_gemini_llm

            return create_gemini_llm(api_settings)
        except ImportError as e:
            if "langchain_google_genai" in str(e):
                raise ValueError(
                    "Gemini provider requires langchain-google-genai package. "
                    "Install it with: pip install langchain-google-genai"
                ) from e
            else:
                raise
    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider}. "
            f"Set LLM_PROVIDER to 'local' or 'gemini'"
        )


class LLMClient(Runnable):
    """Lazy wrapper for LLM client that initializes only when first accessed."""

    def __init__(self, api_settings: APISettings):
        super().__init__()
        self._client = None
        self.api_settings = api_settings
        # Create settings instance for rate limiter
        settings = AppSettings()
        settings.api = api_settings
        self.rate_limiter = RateLimiter(settings)

    def _get_client(self) -> Runnable:
        if self._client is None:
            self._client = get_llm(self.api_settings)
        return self._client

    def invoke(self, *args, **kwargs):
        # Apply rate limiting to the invoke method
        rate_limited_invoke = self.rate_limiter.check_rate_limit(
            self._get_client().invoke
        )
        return rate_limited_invoke(*args, **kwargs)

    def __getattr__(self, name):
        # Delegate all other attributes to the actual client
        return getattr(self._get_client(), name)
