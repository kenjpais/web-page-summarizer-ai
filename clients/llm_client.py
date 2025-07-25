import requests
from utils.logging_config import log_prompt
from config.settings import get_settings


class LLMClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.api_url: str = settings.api.llm_api_url
        if not self.api_url:
            raise ValueError("LLM_API_URL environment variable not set")

    @log_prompt
    def prompt_llm(self, prompt: str) -> str:
        """Makes POST request with prompt payload to LLM API."""
        self.prompt = prompt
        try:
            response = requests.post(
                self.api_url,
                json={"model": "mistral", "prompt": prompt, "stream": False},
            )
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            return f"LLM request failed: {e}"

    @log_prompt
    def test_llm_connection(self, prompt: str = "Test") -> bool:
        """Tests LLM API."""
        if "LLM request failed:" in self.prompt_llm(prompt):
            return False
        return True
