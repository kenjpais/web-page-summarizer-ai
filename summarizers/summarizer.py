import re
import json
import time
from utils.utils import json_to_markdown
from utils.parser_utils import convert_json_text_to_dict
from chains.chains import Chains
from config.settings import get_config_loader, AppSettings
from utils.logging_config import get_logger
from utils.text_chunker import (
    chunk_text_for_llm,
    combine_chunked_summaries,
    get_chunk_info,
)

logger = get_logger(__name__)


class Summarizer:
    def __init__(self, settings: AppSettings, chains=None):
        self.settings = settings
        if chains is None:
            self.chains = Chains(settings)
        else:
            self.chains = chains

    def summarize_projects(self):
        logger.info("\n[*] Generating summary for projects...")

        data_dir = self.settings.file_paths.data_dir
        llm_provider = self.settings.api.llm_provider
        llm_model = self.settings.api.llm_model
        projects_summary_file = data_dir / "projects_summary.txt"

        with open(self.settings.file_paths.correlated_file_path, "r") as cor_file:
            release_notes = json_to_markdown(cor_file.read())

        # Get the project summary prompt template for chunking
        config_loader = get_config_loader(self.settings)
        prompt_template = config_loader.get_project_summary_template()
        chunk_info = get_chunk_info(self.settings, release_notes, prompt_template)

        logger.info(
            f"Project summary analysis: {chunk_info['total_tokens']} tokens, "
            f"needs chunking: {chunk_info['needs_chunking']}"
        )

        if (
            not chunk_info["needs_chunking"]
            or llm_provider == "local"
            or llm_model == "mistral"
        ):
            # Small payload - process normally
            logger.info("Processing project summary as single payload")
            result = self.chains.project_summary_chain.invoke(
                {"correlated_info": release_notes}
            )
        else:
            # Large payload - use chunking
            logger.info(
                f"Chunking project summary into {chunk_info['num_chunks']} parts"
            )
            chunks = chunk_text_for_llm(release_notes, prompt_template)

            summaries = []
            current_provider = self.settings.api.llm_provider

            for i, chunk in enumerate(chunks, 1):
                logger.info(
                    f"Processing project chunk {i}/{len(chunks)} "
                    f"({get_chunk_info(self.settings, chunk)['total_tokens']} tokens)"
                )

                # Add rate limiting for Gemini API
                if current_provider == "gemini" and i > 1:
                    logger.info(
                        "Rate limiting: waiting 2 seconds between Gemini requests..."
                    )
                    time.sleep(2)

                try:
                    chunk_summary = self.chains.project_summary_chain.invoke(
                        {"correlated_info": chunk}
                    )
                    summaries.append(chunk_summary)

                    # Save individual chunk summaries for debugging
                    chunk_file = data_dir / f"project_chunk_summary_{i}.txt"
                    with open(chunk_file, "w") as f:
                        f.write(chunk_summary)

                except Exception as e:
                    logger.error(f"Failed to process project chunk {i}: {e}")
                    summaries.append(f"[Error processing chunk {i}: {str(e)}]")

            # Combine all chunk summaries
            result = combine_chunked_summaries(summaries)
            logger.info(
                f"Combined {len(summaries)} project chunk summaries into final result"
            )

        with open(projects_summary_file, "w") as summary:
            summary.write(result)
        return result

    def summarize_feature_gates(self):
        logger.info("[*] Summarizing feature gates...")
        llm_provider = self.settings.api.llm_provider
        llm_model = self.settings.api.llm_model
        if llm_model == "mistral" or llm_provider == "local":
            self.summarize_feature_gates_individually()
            return

        with open(
            self.settings.file_paths.correlated_feature_gate_table_file_path, "r"
        ) as f:
            feature_gate_artifacts = json.load(f)

        try:
            summarized_feature_gates = convert_json_text_to_dict(
                self.chains.feature_gate_summary_chain.invoke(
                    {"feature-gates": f"""Feature Gates:\n{feature_gate_artifacts}"""}
                )
            )

            assert isinstance(summarized_feature_gates, dict)
            assert len(summarized_feature_gates) > 0
            assert all(isinstance(k, str) for k in summarized_feature_gates.keys())
            assert all(isinstance(v, str) for v in summarized_feature_gates.values())

            with open(self.settings.file_paths.summarized_features_file_path, "w") as f:
                json.dump(summarized_feature_gates, f)
        except Exception as e:
            logger.error(
                f"Failed to summarize feature gates: Invalid JSON format received from LLM: {e}"
            )

    def summarize_feature_gates_individually(self):
        with open(
            self.settings.file_paths.correlated_feature_gate_table_file_path, "r"
        ) as f:
            feature_gate_artifacts = json.load(f)
        feature_gate_summaries = {}
        for feature_gate, artifacts in feature_gate_artifacts.items():
            feature = {feature_gate: artifacts}
            if feature_gate not in feature_gate_summaries:
                summary = self.chains.single_feature_gate_summary_chain.invoke(
                    {"feature-gate": f"""{feature}"""}
                )
                if isinstance(summary, str):
                    feature_gate_summaries[feature_gate] = summary
            else:
                logger.error(
                    f"Feature gate {feature_gate} already exists in feature_gate_summaries"
                )
                continue

        if len(feature_gate_summaries) == 0:
            logger.error("No feature gate summaries found")
            return

        with open(self.settings.file_paths.summarized_features_file_path, "w") as f:
            json.dump(feature_gate_summaries, f)

    def summarize(self):
        """Main summarize method for the Summarizer class."""
        if not self.settings.processing.summarize_enabled:
            logger.info("Summarize is disabled, skipping...")
            return
        logger.info("\n[*] Summarizing...")
        logger.info(
            f"Using {self.settings.api.llm_provider} {self.settings.api.llm_model} model"
        )
        if self.settings.processing.summarize_enabled:
            self.summarize_correlated_info()
        self.clean_summary(self.settings.file_paths.summary_file_path)

    def summarize_correlated_info(self):
        """
        Summarize correlated information with intelligent chunking for large payloads.

        This function handles large release notes by:
        1. Checking payload size against LLM limits
        2. Splitting into chunks if necessary
        3. Processing chunks with rate limiting
        4. Combining results into final summary
        """
        with open(self.settings.file_paths.correlated_file_path, "r") as cor_file:
            correlated_info_md = json_to_markdown(cor_file.read())

        release_notes = f"""Release information:\n{correlated_info_md}"""

        # Save the full payload for debugging
        with open(self.settings.file_paths.release_notes_payload_file_path, "w") as f:
            f.write(release_notes)

        # Get the prompt template for proper chunking
        config_loader = get_config_loader(self.settings)
        prompt_template = config_loader.get_summarize_prompt_template()

        # Check if chunking is needed
        chunk_info = get_chunk_info(self.settings, release_notes, prompt_template)
        logger.info(
            f"Release notes analysis: {chunk_info['total_tokens']} tokens, "
            f"needs chunking: {chunk_info['needs_chunking']}"
        )

        if (
            not chunk_info["needs_chunking"]
            or self.settings.api.llm_provider == "local"
            or self.settings.api.llm_model == "mistral"
        ):
            # Small payload - process normally
            logger.info("Processing release notes as single payload")
            try:
                result = self.chains.summary_chain.invoke(
                    {"release-notes": release_notes}
                )
            except Exception as e:
                logger.error(f"[!][ERROR] Failed to process release notes: {e}")
                if "429" in str(e):
                    logger.error(f"[!][ERROR] Rate Limit exceeded: {e}")
                raise
        else:
            # Large payload - use chunking
            logger.info(f"Chunking release notes into {chunk_info['num_chunks']} parts")
            chunks = chunk_text_for_llm(self.settings, release_notes, prompt_template)

            summaries = []
            current_provider = self.settings.api.llm_provider

            for i, chunk in enumerate(chunks, 1):
                logger.info(
                    f"Processing chunk {i}/{len(chunks)} "
                    f"({get_chunk_info(self.settings, chunk)['total_tokens']} tokens)"
                )

                # Add rate limiting for Gemini API to avoid quota exhaustion
                if current_provider == "gemini" and i > 1:
                    logger.info(
                        "Rate limiting: waiting 2 seconds between Gemini requests..."
                    )
                    time.sleep(2)

                try:
                    chunk_summary = self.chains.summary_chain.invoke(
                        {"release-notes": chunk}
                    )
                    summaries.append(chunk_summary)

                    if self.settings.processing.debug:
                        # Save individual chunk summaries for debugging
                        chunk_file = (
                            self.settings.file_paths.data_dir / f"chunk_summary_{i}.txt"
                        )
                        with open(chunk_file, "w") as f:
                            f.write(chunk_summary)

                except Exception as e:
                    logger.error(f"[!][ERROR] Failed to process chunk {i}: {e}")
                    if "429" in str(e):
                        logger.error(f"[!][ERROR] Rate Limit exceeded: {e}")
                        break
                    # Continue with other chunks rather than failing completely
                    summaries.append(
                        f"[!][ERROR] error processing chunk {i}: {str(e)}]"
                    )

            # Combine all chunk summaries
            result = combine_chunked_summaries(summaries)
            logger.info(f"Combined {len(summaries)} chunk summaries into final result")

        # Save final summary
        with open(self.settings.file_paths.summary_file_path, "w") as summary:
            summary.write(result)

    def update_summary_with_release_version(
        self, summary_file_path, release_version_name
    ):
        """Update summary file with release version name."""
        with open(summary_file_path, "r") as rf:
            content = rf.read()
        updated_content = f"Release Notes {release_version_name}\n{content}"
        with open(summary_file_path, "w") as wf:
            wf.write(updated_content)

    def clean_summary(self, dest_summary):
        """Remove mentions of Part <i>"""
        pattern = re.compile(r"^## Part ([1-9][0-9]?|100)\s*$")
        with open(dest_summary, "r") as f:
            summary_lines = f.readlines()

        new_lines = [line for line in summary_lines if not pattern.match(line.strip())]

        with open(dest_summary, "w") as file:
            file.writelines(new_lines)
