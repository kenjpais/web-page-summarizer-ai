from pathlib import Path
from clients.local_llm_chain import local_llm
from langchain_core.runnables import Runnable
from langchain_core.prompts import PromptTemplate
from config.settings import get_settings

settings = get_settings()
config_dir = Path(settings.directories.data_dir)
if not config_dir:
    raise ValueError(f"Invalid CONFIG_DIR {config_dir}")

# Load prompt template file names from configuration
# These templates define how the LLM should process different types of content
summary_prompt_text = settings.config_files.summarize_prompt_template
summary_example_prompt_text = settings.config_files.example_summary_file
classify_prompt_text = settings.config_files.classify_prompt_template
project_summary_prompt_text = settings.config_files.project_summary_template

# Inject example summary into the main summary prompt template
# This provides the LLM with concrete examples of the expected output format
summary_prompt_text = summary_prompt_text.replace(
    "{summary-example}", summary_example_prompt_text
)

# Create LangChain prompt templates from the loaded text
# These templates handle variable substitution and formatting for LLM inputs
summary_prompt = PromptTemplate.from_template(summary_prompt_text)
classify_prompt = PromptTemplate.from_template(classify_prompt_text)
project_summary_prompt = PromptTemplate.from_template(project_summary_prompt_text)

# Build executable LLM chains by combining prompts with the local LLM
# Each chain serves a specific purpose in the analysis pipeline:

# Summary chain: Generates detailed summaries of release data
# Input: Correlated JIRA/GitHub data, Output: Human-readable summary
summary_chain: Runnable = summary_prompt | local_llm

# Classify chain: Categorizes and filters content by relevance
# Input: Raw content, Output: Classification/filtering decisions  
classify_chain: Runnable = classify_prompt | local_llm

# Project summary chain: Creates high-level project overviews
# Input: Project-level data, Output: Executive summary
project_summary_chain: Runnable = project_summary_prompt | local_llm
