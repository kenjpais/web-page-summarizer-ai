"""
Advanced summarizer implementation using improved chunking and rate limiting.
Optimized for Gemini 1.5 Pro API limits.
"""

import json
import asyncio
from typing import Dict, Any, Optional
from utils.utils import json_to_markdown
from utils.parser_utils import convert_json_text_to_dict
from chains.chains import Chains
from config.settings import get_config_loader, AppSettings
from utils.logging_config import get_logger
from utils.chunk_manager import ChunkManager
from utils.rate_limiter import rate_limited

logger = get_logger(__name__)


class AdvancedSummarizer:
    """
    Advanced summarizer with optimized chunking and rate limiting
    - Uses semantic chunking
    - Implements rate limiting
    - Handles dependencies between sections
    - Optimizes for Gemini API limits
    """

    def __init__(self, settings: AppSettings, chains=None):
        self.settings = settings
        if chains is None:
            self.chains = Chains(settings)
        else:
            self.chains = chains

        self.chunk_manager = ChunkManager(settings)

    async def summarize_projects(self) -> str:
        """
        Generate summary for projects using semantic chunking

        Returns:
            Project summary text
        """
        logger.info("\n[*] Generating summary for projects...")

        data_dir = self.settings.file_paths.data_dir
        projects_summary_file = data_dir / "projects_summary.txt"

        # Read correlated data
        with open(self.settings.file_paths.correlated_file_path, "r") as cor_file:
            release_notes = json_to_markdown(cor_file.read())

        # Get project summary prompt template
        config_loader = get_config_loader(self.settings)
        prompt_template = config_loader.get_project_summary_template()

        # Process through chunk manager
        result = await self.chunk_manager.process_text(
            release_notes, self.chains.project_summary_chain, prompt_template
        )

        # Save result
        with open(projects_summary_file, "w") as summary:
            summary.write(result)

        return result

    @rate_limited
    async def _process_feature_gate(
        self, feature_gate: str, artifacts: Dict[str, Any]
    ) -> Optional[str]:
        """Process a single feature gate with rate limiting"""
        try:
            feature = {feature_gate: artifacts}
            summary = await self.chains.single_feature_gate_summary_chain.ainvoke(
                {"feature-gate": str(feature)}
            )
            return summary if isinstance(summary, str) else None
        except Exception as e:
            logger.error(f"Failed to process feature gate {feature_gate}: {e}")
            return None

    async def summarize_feature_gates(self):
        """Summarize feature gates with rate limiting"""
        logger.info("[*] Summarizing feature gates...")

        # Read feature gate data
        with open(
            self.settings.file_paths.correlated_feature_gate_table_file_path, "r"
        ) as f:
            feature_gate_artifacts = json.load(f)

        # Process feature gates
        feature_gate_summaries = {}
        tasks = []

        for feature_gate, artifacts in feature_gate_artifacts.items():
            if feature_gate not in feature_gate_summaries:
                task = self._process_feature_gate(feature_gate, artifacts)
                tasks.append((feature_gate, task))

        # Wait for all tasks to complete
        for feature_gate, task in tasks:
            summary = await task
            if summary:
                feature_gate_summaries[feature_gate] = summary

        if not feature_gate_summaries:
            logger.error("No feature gate summaries generated")
            return

        # Save results
        with open(self.settings.file_paths.summarized_features_file_path, "w") as f:
            json.dump(feature_gate_summaries, f)

    async def summarize_correlated_info(self) -> str:
        """
        Summarize correlated information using semantic chunking

        Returns:
            Final summary text
        """
        # Read correlated data
        with open(self.settings.file_paths.correlated_file_path, "r") as cor_file:
            correlated_info_md = json_to_markdown(cor_file.read())

        release_notes = f"""Release information:\n{correlated_info_md}"""

        # Save full payload for debugging
        with open(self.settings.file_paths.release_notes_payload_file_path, "w") as f:
            f.write(release_notes)

        # Get summarization prompt template
        config_loader = get_config_loader(self.settings)
        prompt_template = config_loader.get_summarize_prompt_template()

        # Process through chunk manager
        result = await self.chunk_manager.process_text(
            release_notes, self.chains.summary_chain, prompt_template
        )

        # Save final summary
        with open(self.settings.file_paths.summary_file_path, "w") as summary:
            summary.write(result)

        return result

    async def summarize(self):
        """Main summarize method"""
        if not self.settings.processing.summarize_enabled:
            logger.info("Summarize is disabled, skipping...")
            return

        logger.info("\n[*] Summarizing...")
        logger.info(
            f"Using {self.settings.api.llm_provider} {self.settings.api.llm_model} model"
        )

        if self.settings.processing.summarize_enabled:
            await self.summarize_correlated_info()

        # Clean up the summary
        self._clean_summary(self.settings.file_paths.summary_file_path)

    def update_summary_with_release_version(
        self, summary_file_path: str, release_version_name: str
    ):
        """Update summary file with release version name"""
        with open(summary_file_path, "r") as rf:
            content = rf.read()
        updated_content = f"Release Notes {release_version_name}\n{content}"
        with open(summary_file_path, "w") as wf:
            wf.write(updated_content)

    def _clean_summary(self, summary_file_path: str):
        """Clean up the summary file"""
        with open(summary_file_path, "r") as f:
            content = f.read()

        # Remove any remaining chunk markers
        cleaned_content = content.replace("## Part ", "")

        with open(summary_file_path, "w") as f:
            f.write(cleaned_content)
