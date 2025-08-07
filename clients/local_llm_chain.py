from typing import Any, Dict, Optional, Union
from utils.logging_config import log_prompt
from langchain_ollama import OllamaLLM
from langchain_core.runnables import Runnable
from config.settings import APISettings


class LLMClient(Runnable):
    def __init__(
        self, llm: OllamaLLM, domain: str = "localhost", port: int = 11434
    ) -> None:
        super().__init__()
        self.llm: OllamaLLM = llm
        self.domain: str = domain
        self.port: int = port
        self.prompt: Optional[Union[str, Dict[str, Any]]] = None

    @log_prompt
    def test_llm_connection(self, prompt: str = "Say hello") -> bool:
        self.prompt = prompt
        response = self.llm.invoke(prompt)
        assert isinstance(response, str)
        assert len(response) > 0
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
        return result


def _create_local_llm(api_settings: APISettings):
    """Create local LLM client with current settings."""
    llm_base_url = api_settings.llm_api_url.replace("/api/generate", "")
    return LLMClient(OllamaLLM(model=api_settings.llm_model, base_url=llm_base_url))


class LazyLocalLLM:
    """Lazy wrapper for local LLM that only initializes when first accessed."""

    def __init__(self, api_settings: APISettings):
        self._client = None
        self.api_settings = api_settings

    def _get_client(self):
        if self._client is None:
            self._client = _create_local_llm(self.api_settings)
        return self._client

    def invoke(self, *args, **kwargs):
        return self._get_client().invoke(*args, **kwargs)

    def __getattr__(self, name):
        # Delegate all other attributes to the actual client
        return getattr(self._get_client(), name)


def create_local_llm(api_settings: APISettings):
    return LazyLocalLLM(api_settings)
