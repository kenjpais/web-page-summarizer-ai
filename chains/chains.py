from clients.llm_factory import llm_client
from langchain_core.runnables import Runnable
from langchain_core.prompts import PromptTemplate
from config.settings import get_settings, get_config_loader

settings = get_settings()
config_loader = get_config_loader()
config_dir = settings.directories.data_dir
if not config_dir:
    raise ValueError(f"Invalid CONFIG_DIR {config_dir}")

# Load prompt template file names from configuration
# These templates define how the LLM should process different types of content
summary_prompt_text = config_loader.get_summarize_prompt_template()
summary_example_prompt_text = config_loader.get_example_summary()
project_summary_prompt_text = config_loader.get_project_summary_template()
feature_gate_summary_prompt_text = (
    config_loader.get_feature_gate_summarize_prompt_template()
)
single_feature_gate_summary_prompt_text = (
    config_loader.get_single_feature_gate_summarize_prompt_template()
)
# classify_prompt_text = settings.config_files.classify_prompt_template

# Inject example summary into the main summary prompt template
# This provides the LLM with concrete examples of the expected output format
summary_prompt_text = summary_prompt_text.replace(
    "{summary-example}", summary_example_prompt_text
)

# Create LangChain prompt templates from the loaded text
# These templates handle variable substitution and formatting for LLM inputs
summary_prompt = PromptTemplate.from_template(summary_prompt_text)
project_summary_prompt = PromptTemplate.from_template(project_summary_prompt_text)
feature_gate_summary_prompt = PromptTemplate.from_template(
    feature_gate_summary_prompt_text
)
single_feature_gate_summary_prompt = PromptTemplate.from_template(
    single_feature_gate_summary_prompt_text
)
# classify_prompt = PromptTemplate.from_template(classify_prompt_text)

# Chains
# Summary chain: Generates detailed summaries of release data
# Input: Correlated JIRA/GitHub data, Output: Human-readable summary
summary_chain: Runnable = summary_prompt | llm_client

# Classify chain: Categorizes and filters content by relevance
# Input: Raw content, Output: Classification/filtering decisions
# classify_chain: Runnable = classify_prompt | llm_client

# Project summary chain: Creates high-level project overviews
# Input: Project-level data, Output: Executive summary
project_summary_chain: Runnable = project_summary_prompt | llm_client

# Feature gate summary chain: Creates high-level feature overviews
# Input: Feature data, Output: Executive summary
feature_gate_summary_chain: Runnable = feature_gate_summary_prompt | llm_client

# Single Feature gate summary chain: Creates high-level feature overviews for a single feature gate
# Input: Feature data, Output: Executive summary
feature_gate_summary_chain: Runnable = feature_gate_summary_prompt | llm_client
single_feature_gate_summary_chain: Runnable = (
    single_feature_gate_summary_prompt | llm_client
)
