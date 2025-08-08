from typing import Any, Dict, Optional, Union
from utils.logging_config import log_prompt
from langchain_core.runnables import Runnable
from config.settings import APISettings


class GeminiLLMClient(Runnable):
    def __init__(self, llm) -> None:
        super().__init__()
        self.llm = llm
        self.prompt: Optional[Union[str, Dict[str, Any]]] = None

    @log_prompt
    def test_llm_connection(self, prompt: str = "Say hello") -> bool:
        self.prompt = prompt
        response = self.llm.invoke(prompt)
        response_text = (
            response.content if hasattr(response, "content") else str(response)
        )
        assert isinstance(response_text, str)
        assert len(response_text) > 0
        return True

    @log_prompt
    def invoke(
        self,
        input: Union[str, Dict[str, Any]],
        config: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> str:
        self.prompt = input
        result = self.llm.invoke(input, config=config, **kwargs)
        return result.content if hasattr(result, "content") else str(result)


def _create_gemini_llm(api_settings: APISettings):
    """Create Gemini LLM client with lazy import to avoid dependency issues."""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError:
        raise ImportError(
            "langchain-google-genai package is required for Gemini provider. "
            "Install it with: pip install langchain-google-genai"
        )
    return GeminiLLMClient(
        ChatGoogleGenerativeAI(
            model=api_settings.gemini_model,
            google_api_key=api_settings.google_api_key,
            temperature=0.0,
        )
    )


class LazyGeminiLLM:
    """Lazy wrapper for Gemini LLM that only initializes when first accessed."""

    def __init__(self, api_settings: APISettings):
        self._client = None
        self.api_settings = api_settings

    def _get_client(self):
        if self._client is None:
            self._client = _create_gemini_llm(self.api_settings)
        return self._client

    def invoke(self, *args, **kwargs):
        return self._get_client().invoke(*args, **kwargs)

    def __getattr__(self, name):
        # Delegate all other attributes to the actual client
        return getattr(self._get_client(), name)


def create_gemini_llm(api_settings: APISettings):
    return LazyGeminiLLM(api_settings)
