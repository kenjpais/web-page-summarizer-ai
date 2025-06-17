import requests
from utils.utils import get_env
from utils.logging_config import log_prompt


class LLMClient:
    def __init__(self):
        self.api_url = get_env("LLM_API_URL")

    @log_prompt
    def prompt_llm(self, prompt):
        try:
            response = requests.post(
                self.api_url,
                json={"model": "mistral", "prompt": prompt, "stream": False},
            )
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            return f"LLM request failed: {e}"


def build_prompt(text):
    try:
        with open("summarize_prompt_template.txt", "r") as file:
            return f"{file.read()}\n\n{text}"
    except FileNotFoundError:
        return f"Summarize:\n\n{text}"
