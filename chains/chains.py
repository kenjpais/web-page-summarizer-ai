from utils.file_utils import read_file_str
from utils.utils import get_env
from clients.local_llm_chain import local_llm
from langchain_core.runnables import Runnable
from langchain_core.prompts import PromptTemplate


summary_prompt_text = read_file_str(
    f"{get_env('CONFIG_DIR')}/summarize_prompt_template.txt"
)
summary_example_prompt_text = read_file_str(
    f"{get_env('CONFIG_DIR')}/example_summary.txt"
)
classify_prompt_text = read_file_str(
    f"{get_env('CONFIG_DIR')}/classify_prompt_template.txt"
)
project_summary_prompt_text = read_file_str(
    f"{get_env('CONFIG_DIR')}/summarize_project_prompt_template.txt"
)
summary_prompt_text = summary_prompt_text.replace(
    "{summary-example}", summary_example_prompt_text
)

summary_prompt = PromptTemplate.from_template(summary_prompt_text)
classify_prompt = PromptTemplate.from_template(classify_prompt_text)
project_summary_prompt = PromptTemplate.from_template(project_summary_prompt_text)

summary_chain: Runnable = summary_prompt | local_llm
classify_chain: Runnable = classify_prompt | local_llm
project_summary_chain: Runnable = project_summary_prompt | local_llm
