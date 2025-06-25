from utils.utils import get_env, json_to_markdown
from clients.llm_client import LLMClient, build_prompt


def summarize():
    print("\n[*] Summarizing...")
    data_dir = get_env("DATA_DIR")
    config_dir = get_env("CONFIG_DIR")
    prompt_payload = f"{data_dir}/prompt_payload.txt"
    summary_file = f"{data_dir}/summary.txt"

    def build_prompt_payload():
        correlated_file = f"{data_dir}/correlated.json"
        summarize_prompt_template = f"{config_dir}/summarize_prompt_template.txt"
        with open(correlated_file, "r") as cor, open(
            summarize_prompt_template, "r"
        ) as prompt_template, open(prompt_payload, "w") as out:
            out.write(f"{prompt_template.read()}\n{json_to_markdown(cor.read())}")

    def prompt_llm():
        with open(prompt_payload, "r") as f:
            text = f.read()
        return LLMClient().prompt_llm(build_prompt(text))

    build_prompt_payload()
    result = prompt_llm()
    with open(summary_file, "w") as summary:
        summary.write(result)
