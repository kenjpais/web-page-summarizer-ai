import json
from utils.utils import get_env, json_to_markdown
from clients.llm_client import LLMClient

data_dir = get_env("DATA_DIR")
config_dir = get_env("CONFIG_DIR")
correlated_file = f"{data_dir}/correlated.json"


def summarize_():
    print("\n[*] Summarizing...")
    prompt_payload = f"{data_dir}/prompt_payload.txt"
    summary_file = f"{data_dir}/summary.txt"

    def build_prompt_payload():
        summarize_prompt_template = f"{config_dir}/summarize_prompt_template.txt"
        example_summary_file_path = f"{config_dir}/example_summary.txt"

        with open(correlated_file, "r") as cor_file, open(
            summarize_prompt_template, "r"
        ) as template_file, open(example_summary_file_path, "r") as example_file:

            example_summary = example_file.read()
            release_notes = json_to_markdown(cor_file.read())
            prompt_payload_str = template_file.read()

            prompt_payload_str = prompt_payload_str.replace(
                "{summary-example}", f"\n{example_summary}"
            )
            prompt_payload_str = prompt_payload_str.replace(
                "{release-notes}", f"\n{release_notes}"
            )

        with open(prompt_payload, "w") as out:
            out.write(prompt_payload_str)

        return prompt_payload_str

    result = LLMClient().prompt_llm(build_prompt_payload())
    with open(summary_file, "w") as summary:
        summary.write(result)


def summarize_projects():
    print("\n[*] Summarizing each project...")
    with open(correlated_file, "r") as corfile:
        correlated_data = json.load(corfile)

    llm = LLMClient()
    summarized_projects = ""
    for k, v in correlated_data.items():
        project_md = json_to_markdown({k: v})
        summarized_projects += f"\n{
            llm.prompt_llm(
                f"You are a technical writer. Summarize the below information.\n{project_md}"
            )}"

    return summarized_projects


def summarize():
    print("\n[*] Summarizing...")
    prompt_payload = f"{data_dir}/prompt_payload.txt"
    summary_file = f"{data_dir}/summary.txt"
    summarized_projects = summarize_projects()

    print(f"KDEBUG: summarized_projects: {summarized_projects}")

    def build_prompt_payload(release_notes):
        summarize_prompt_template = f"{config_dir}/summarize_prompt_template.txt"
        example_summary_file_path = f"{config_dir}/example_summary.txt"

        with open(summarize_prompt_template, "r") as template_file, open(
            example_summary_file_path, "r"
        ) as example_file:
            example_summary = example_file.read()
            prompt_payload_str = template_file.read()

            prompt_payload_str = prompt_payload_str.replace(
                "{summary-example}", f"\n{example_summary}"
            )
            prompt_payload_str = prompt_payload_str.replace(
                "{release-notes}", f"\n{release_notes}"
            )

        with open(prompt_payload, "w") as out:
            out.write(prompt_payload_str)

        return prompt_payload_str

    result = LLMClient().prompt_llm(build_prompt_payload(summarized_projects))
    with open(summary_file, "w") as summary:
        summary.write(result)
