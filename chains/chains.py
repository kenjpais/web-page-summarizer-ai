from clients.llm_factory import LLMClient
from langchain_core.runnables import Runnable
from langchain_core.prompts import PromptTemplate
from config.settings import AppSettings, ConfigLoader


class Chains:
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.llm_client = LLMClient(settings.api)

        # Load prompt template file names from configuration
        config_loader = ConfigLoader(self.settings)

        # Summary chain: Generates detailed summaries of a key and value
        # Input: Key and value, Output: summary of key
        self.summary_chain: Runnable = (
            PromptTemplate.from_template(config_loader.get_summarize_prompt_template())
            | self.llm_client
        )

        # Single Feature gate summary chain: Creates high-level feature summary of a single feature gate
        # Input: Feature data, Output: summary
        self.single_feature_gate_summary_chain: Runnable = (
            PromptTemplate.from_template(
                config_loader.get_single_feature_gate_summarize_prompt_template()
            )
            | self.llm_client
        )

        self.map_chain: Runnable = self.summary_chain
        self.reduce_chain: Runnable = (
            PromptTemplate.from_template(config_loader.get_reduce_prompt_template())
            | self.llm_client
        )
