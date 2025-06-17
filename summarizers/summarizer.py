from utils.utils import get_env
from clients.llm_client import LLMClient, build_prompt


def summarize():
    data_dir = get_env("DATA_DIR")
    with open(f"{data_dir}/prompt_payload.txt", "r") as prompt_payload:
        text = prompt_payload.read()
    return LLMClient().prompt_llm(build_prompt(text))
