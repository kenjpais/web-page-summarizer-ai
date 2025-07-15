from pathlib import Path
from utils.utils import get_env, json_to_markdown
from clients.llm_client import LLMClient
from chains.chains import project_summary_chain
from chains.chains import summary_chain
from utils.logging_config import get_logger

logger = get_logger(__name__)

data_dir = Path(get_env("DATA_DIR"))
config_dir = Path(get_env("CONFIG_DIR"))
correlated_file = data_dir / "correlated.json"


def summarize_():
    logger.info("\n[*] Summarizing...")
    prompt_payload = data_dir / "prompt_payload.txt"
    summary_file = data_dir / "summary.txt"

    def build_prompt_payload():
        summarize_prompt_template = config_dir / "summarize_prompt_template.txt"
        example_summary_file_path = config_dir / "example_summary.txt"

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
    logger.info("\n[*] Generating summary for projects...")
    projects_summary_file = data_dir / "projects_summary.txt"

    with open(correlated_file, "r") as cor_file:
        release_notes = json_to_markdown(cor_file.read())

    result = project_summary_chain.invoke({"correlated_info": release_notes})
    with open(projects_summary_file, "w") as summary:
        summary.write(result)
    return result


def summarize():
    logger.info("\n[*] Summarizing...")
    prompt_payload = data_dir / "prompt_payload.txt"
    summary_file = data_dir / "summary.txt"
    correlated_table_file = data_dir / "correlated_feature_gate_table.json"

    with open(correlated_table_file, "r") as f:
        feature_gate_info_md = json_to_markdown(f.read())
    with open(correlated_file, "r") as cor_file:
        correlated_info_md = json_to_markdown(cor_file.read())

    release_notes = f"""FeatureGates:\n{feature_gate_info_md}\nRelease information:\n{correlated_info_md}"""

    with open(data_dir / "release_notes_payload.txt", "w") as f:
        f.write(release_notes)

    result = summary_chain.invoke({"release-notes": release_notes})
    with open(summary_file, "w") as summary:
        summary.write(result)

    return

    def build_prompt_payload(release_notes):
        summarize_prompt_template = config_dir / "summarize_prompt_template.txt"
        example_summary_file_path = config_dir / "example_summary.txt"

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
