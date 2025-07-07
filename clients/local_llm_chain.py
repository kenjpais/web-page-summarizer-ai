from utils.logging_config import log_prompt
from langchain_community.llms import Ollama
from langchain_core.runnables import Runnable


class LLMClient(Runnable):
    def __init__(self, llm, domain="localhost", port=11434):
        super().__init__()
        self.llm = llm
        self.domain = domain
        self.port = port
        self.prompt = None

    @log_prompt
    def test_llm_connection(self, prompt="Say hello"):
        """Tests LLM API."""
        self.prompt = prompt
        response = self.llm.invoke(prompt)
        assert isinstance(response, str)
        assert len(response) > 0
        return True

    @log_prompt
    def invoke(self, input, config=None, **kwargs):
        self.prompt = input
        result = self.llm.invoke(input, config=config, **kwargs)
        return result


local_llm = LLMClient(Ollama(model="mistral"))
