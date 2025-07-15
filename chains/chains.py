from pathlib import Path
from clients.local_llm_chain import local_llm
from langchain_core.runnables import Runnable
from langchain_core.prompts import PromptTemplate
from config.settings import get_settings

settings = get_settings()
config_dir = Path(settings.directories.data_dir)
if not config_dir:
    raise ValueError(f"Invalid CONFIG_DIR {config_dir}")

summary_prompt_text = settings.config_files.summarize_prompt_template

summary_example_prompt_text = settings.config_files.example_summary_file

classify_prompt_text = settings.config_files.classify_prompt_template

project_summary_prompt_text = settings.config_files.project_summary_template

summary_prompt_text = summary_prompt_text.replace(
    "{summary-example}", summary_example_prompt_text
)

summary_prompt = PromptTemplate.from_template(summary_prompt_text)
classify_prompt = PromptTemplate.from_template(classify_prompt_text)
project_summary_prompt = PromptTemplate.from_template(project_summary_prompt_text)

summary_chain: Runnable = summary_prompt | local_llm
classify_chain: Runnable = classify_prompt | local_llm
project_summary_chain: Runnable = project_summary_prompt | local_llm
