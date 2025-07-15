from typing import Any, Dict, Optional, Union
from utils.logging_config import log_prompt
from langchain_community.llms import Ollama
from langchain_core.runnables import Runnable


class LLMClient(Runnable):
    def __init__(
        self, llm: Ollama, domain: str = "localhost", port: int = 11434
    ) -> None:
        super().__init__()
        self.llm: Ollama = llm
        self.domain: str = domain
        self.port: int = port
        self.prompt: Optional[Union[str, Dict[str, Any]]] = None

    @log_prompt
    def test_llm_connection(self, prompt: str = "Say hello") -> bool:
        """Tests LLM API."""
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


local_llm = LLMClient(Ollama(model="mistral"))
