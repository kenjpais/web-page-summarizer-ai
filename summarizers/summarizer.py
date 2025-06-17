from utils.utils import get_env
from clients.llm_client import LLMClient, build_prompt


def summarize():
    print("\n[*] Summarizing...")

    def build_prompt_payload():
        data_dir = get_env("DATA_DIR")
        with open(f"{data_dir}/correlated.json", "r") as cor, open(
            f"{data_dir}/non_correlated.json", "r"
        ) as ncor, open(f"{data_dir}/prompt_payload.txt", "w") as out:
            out.write(
                f"""
                {cor.read()}\nMiscellaneous information:\n\n{ncor.read()}
            """
            )

    def prompt_llm():
        data_dir = get_env("DATA_DIR")
        with open(f"{data_dir}/prompt_payload.txt", "r") as prompt_payload:
            text = prompt_payload.read()
        return LLMClient().prompt_llm(build_prompt(text))

    build_prompt_payload()
    result = prompt_llm()
    data_dir = get_env("DATA_DIR")
    with open(f"{data_dir}/summary.txt", "w") as summary:
        summary.write(result)
