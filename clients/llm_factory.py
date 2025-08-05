"""
LLM Factory to choose between different LLM providers based on configuration.
"""

from langchain_core.runnables import Runnable
from config.settings import get_settings


def get_llm() -> Runnable:
    """
    Factory function to get the appropriate LLM client based on configuration.

    Returns:
        Runnable: Either local_llm or gemini_llm based on LLM_PROVIDER setting

    Raises:
        ValueError: If the LLM provider is not supported or if required environment variables are missing
    """
    settings = get_settings()
    provider = settings.api.llm_provider.lower()

    if provider == "local":
        from clients.local_llm_chain import local_llm

        return local_llm
    elif provider == "gemini":
        if not settings.api.google_api_key:
            raise ValueError(
                "GOOGLE_API_KEY environment variable is required when using Gemini provider. "
                "Get your API key from: https://makersuite.google.com/app/apikey"
            )

        try:
            from clients.gemini_llm_chain import gemini_llm

            return gemini_llm
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


class LazyLLMClient(Runnable):
    """Lazy wrapper for LLM client that initializes only when first accessed."""

    def __init__(self):
        super().__init__()
        self._client = None

    def _get_client(self) -> Runnable:
        if self._client is None:
            self._client = get_llm()
        return self._client

    def invoke(self, *args, **kwargs):
        return self._get_client().invoke(*args, **kwargs)

    def __getattr__(self, name):
        # Delegate all other attributes to the actual client
        return getattr(self._get_client(), name)


# Create lazy client instance
llm_client = LazyLLMClient()
