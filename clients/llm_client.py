import requests
from utils.utils import get_env
from utils.logging_config import log_prompt


class LLMClient:
    def __init__(self):
        self.api_url = get_env("LLM_API_URL")

    @log_prompt
    def prompt_llm(self, prompt):
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
    def test_llm_connection(self, prompt="Test"):
        """Tests LLM API."""
        if "LLM request failed:" in self.prompt_llm(prompt):
            return False
        return True
