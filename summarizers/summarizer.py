import json
import os
import time
from utils.utils import json_to_markdown
from utils.parser_utils import convert_json_text_to_dict
from clients.llm_client import LLMClient
from chains.chains import (
    project_summary_chain,
    summary_chain,
    feature_gate_summary_chain,
    single_feature_gate_summary_chain,
)
from config.settings import get_settings, get_config_loader
from utils.logging_config import get_logger
from utils.text_chunker import (
    chunk_text_for_llm,
    combine_chunked_summaries,
    get_chunk_info,
)

logger = get_logger(__name__)

settings = get_settings()
llm_provider = settings.api.llm_provider
llm_model = settings.api.llm_model

# Configuration paths for summarization pipeline
data_dir = settings.directories.data_dir
config_dir = settings.directories.config_dir

correlated_file = data_dir / "correlated.json"
correlated_feature_gate_table_file = data_dir / "correlated_feature_gate_table.json"
summarized_features_file = data_dir / "summarized_features.json"
prompt_payload = data_dir / "prompt_payload.txt"
summary_file = data_dir / "summary.txt"


# Without langchain
def summarize_():
    """
    Generate a comprehensive summary of release data using LLM processing.

    This function orchestrates the summarization process by:
    1. Loading correlated JIRA/GitHub data
    2. Converting data to human-readable Markdown format
    3. Building a structured prompt with examples
    4. Processing through the LLM to generate final summary
    5. Writing the summary to output file

    Output: Creates summary.txt with the final release summary
    """
    logger.info("\n[*] Summarizing...")

    # Output files for the summarization process
    prompt_payload = data_dir / "prompt_payload.txt"  # Intermediate prompt file
    summary_file = data_dir / "summary.txt"  # Final summary output

    def build_prompt_payload():
        """
        Construct the complete prompt for LLM summarization.

        This function assembles the prompt by combining:
        - Template structure (defines output format)
        - Example summary (shows desired style and content)
        - Actual release data (converted to Markdown)

        Returns:
            Complete prompt string ready for LLM processing
        """
        # Load prompt components from configuration files
        summarize_prompt_template = config_dir / "summarize_prompt_template.txt"
        example_summary_file_path = config_dir / "example_summary.txt"

        with open(correlated_file, "r") as cor_file, open(
            summarize_prompt_template, "r"
        ) as template_file, open(example_summary_file_path, "r") as example_file:

            # Load the example summary for few-shot learning
            example_summary = example_file.read()

            # Convert JSON data to readable Markdown format
            release_notes = json_to_markdown(cor_file.read())

            # Load the prompt template with placeholders
            prompt_payload_str = template_file.read()

            # Inject the example summary into the template
            # This provides the LLM with a concrete example of desired output
            prompt_payload_str = prompt_payload_str.replace(
                "{summary-example}", f"\n{example_summary}"
            )

            # Inject the actual release data to be summarized
            prompt_payload_str = prompt_payload_str.replace(
                "{release-notes}", f"\n{release_notes}"
            )

        # Save the complete prompt for debugging and review
        with open(prompt_payload, "w") as out:
            out.write(prompt_payload_str)

        return prompt_payload_str

    # Generate the summary using the LLM client
    result = LLMClient().prompt_llm(build_prompt_payload())

    # Write the final summary to output file
    with open(summary_file, "w") as summary:
        summary.write(result)


def summarize_projects():
    """
    Generate project-level summaries using LangChain processing with chunking support.

    This function creates higher-level summaries focused on project
    organization and strategic overview rather than detailed technical
    changes. It uses the project_summary_chain for structured processing.
    """
    logger.info("\n[*] Generating summary for projects...")
    projects_summary_file = data_dir / "projects_summary.txt"

    with open(correlated_file, "r") as cor_file:
        release_notes = json_to_markdown(cor_file.read())

    # Get the project summary prompt template for chunking
    config_loader = get_config_loader()
    prompt_template = config_loader.get_project_summary_template()

    # Check if chunking is needed
    chunk_info = get_chunk_info(release_notes, prompt_template)

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
        result = project_summary_chain.invoke({"correlated_info": release_notes})
    else:
        # Large payload - use chunking
        logger.info(f"Chunking project summary into {chunk_info['num_chunks']} parts")
        chunks = chunk_text_for_llm(release_notes, prompt_template)

        summaries = []
        current_provider = settings.api.llm_provider

        for i, chunk in enumerate(chunks, 1):
            logger.info(
                f"Processing project chunk {i}/{len(chunks)} "
                f"({get_chunk_info(chunk)['total_tokens']} tokens)"
            )

            # Add rate limiting for Gemini API
            if current_provider == "gemini" and i > 1:
                logger.info(
                    "Rate limiting: waiting 2 seconds between Gemini requests..."
                )
                time.sleep(2)

            try:
                chunk_summary = project_summary_chain.invoke({"correlated_info": chunk})
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


def summarize_feature_gates_individually():
    with open(correlated_feature_gate_table_file, "r") as f:
        feature_gate_artifacts = json.load(f)

    feature_gate_summaries = {}
    for feature_gate, artifacts in feature_gate_artifacts.items():
        feature = {feature_gate: artifacts}
        if feature_gate not in feature_gate_summaries:
            feature_gate_summaries[feature_gate] = (
                single_feature_gate_summary_chain.invoke(
                    {"feature-gate": f"""{feature}"""}
                )
            )
        else:
            logger.error(
                f"Feature gate {feature_gate} already exists in feature_gate_summaries"
            )
            continue

    if len(feature_gate_summaries) == 0:
        logger.error("No feature gate summaries found")
        return

    with open(summarized_features_file, "w") as f:
        json.dump(
            feature_gate_summaries,
            f,
        )


def summarize_feature_gates():
    if llm_model == "mistral" or llm_provider == "local":
        summarize_feature_gates_individually()
        return

    with open(correlated_feature_gate_table_file, "r") as f:
        feature_gate_artifacts = json.load(f)
    summarized_feature_gates = convert_json_text_to_dict(
        feature_gate_summary_chain.invoke(
            {"feature-gates": f"""Feature Gates:\n{feature_gate_artifacts}"""}
        )
    )

    try:
        assert isinstance(summarized_feature_gates, dict)
        assert len(summarized_feature_gates) > 0
        assert all(isinstance(k, str) for k in summarized_feature_gates.keys())
        assert all(isinstance(v, str) for v in summarized_feature_gates.values())
    except Exception as e:
        logger.error(
            f"Failed to summarize feature gates: Invalid JSON format received from LLM: {e}"
        )
        return

    with open(summarized_features_file, "w") as f:
        json.dump(
            summarized_feature_gates,
            f,
        )


def summarize():
    current_settings = get_settings()
    if not current_settings.processing.summarize_enabled:
        logger.info("Summarize is disabled, skipping...")
        return
    logger.info("\n[*] Summarizing...")
    logger.info(f"Using {llm_provider} {llm_model} model")
    if current_settings.processing.summarize_enabled:
        summarize_correlated_info()


def summarize_correlated_info():
    """
    Summarize correlated information with intelligent chunking for large payloads.

    This function handles large release notes by:
    1. Checking payload size against LLM limits
    2. Splitting into chunks if necessary
    3. Processing chunks with rate limiting
    4. Combining results into final summary
    """
    with open(correlated_file, "r") as cor_file:
        correlated_info_md = json_to_markdown(cor_file.read())

    release_notes = f"""Release information:\n{correlated_info_md}"""

    # Save the full payload for debugging
    with open(data_dir / "release_notes_payload.txt", "w") as f:
        f.write(release_notes)

    # Get the prompt template for proper chunking
    config_loader = get_config_loader()
    prompt_template = config_loader.get_summarize_prompt_template()

    # Check if chunking is needed
    chunk_info = get_chunk_info(release_notes, prompt_template)
    logger.info(
        f"Release notes analysis: {chunk_info['total_tokens']} tokens, "
        f"needs chunking: {chunk_info['needs_chunking']}"
    )

    if (
        not chunk_info["needs_chunking"]
        or llm_provider == "local"
        or llm_model == "mistral"
    ):
        # Small payload - process normally
        logger.info("Processing release notes as single payload")
        result = summary_chain.invoke({"release-notes": release_notes})
    else:
        # Large payload - use chunking
        logger.info(f"Chunking release notes into {chunk_info['num_chunks']} parts")
        chunks = chunk_text_for_llm(release_notes, prompt_template)

        summaries = []
        current_provider = settings.api.llm_provider

        for i, chunk in enumerate(chunks, 1):
            logger.info(
                f"Processing chunk {i}/{len(chunks)} "
                f"({get_chunk_info(chunk)['total_tokens']} tokens)"
            )

            # Add rate limiting for Gemini API to avoid quota exhaustion
            if current_provider == "gemini" and i > 1:
                logger.info(
                    "Rate limiting: waiting 2 seconds between Gemini requests..."
                )
                time.sleep(2)

            try:
                chunk_summary = summary_chain.invoke({"release-notes": chunk})
                summaries.append(chunk_summary)

                # Save individual chunk summaries for debugging
                chunk_file = data_dir / f"chunk_summary_{i}.txt"
                with open(chunk_file, "w") as f:
                    f.write(chunk_summary)

            except Exception as e:
                logger.error(f"[!][ERROR] Failed to process chunk {i}: {e}")
                if "429" in str(e):
                    logger.error(f"[!][ERROR] Rate Limit exceeded: {e}")
                    break
                # Continue with other chunks rather than failing completely
                summaries.append(f"[!][ERROR] error processing chunk {i}: {str(e)}]")

        # Combine all chunk summaries
        result = combine_chunked_summaries(summaries)
        logger.info(f"Combined {len(summaries)} chunk summaries into final result")

    # Save final summary
    with open(summary_file, "w") as summary:
        summary.write(result)


def raw_summarize():
    """
    Feature gates are structured in a separate section for better highlighting.
    Includes chunking support for large payloads.
    """
    with open(correlated_feature_gate_table_file, "r") as f:
        feature_gate_info_md = json_to_markdown(f.read())
    with open(correlated_file, "r") as cor_file:
        correlated_info_md = json_to_markdown(cor_file.read())

    release_notes = f"""FeatureGates:\n{feature_gate_info_md}\nRelease information:\n{correlated_info_md}"""

    # Save the full payload for debugging
    with open(data_dir / "release_notes_payload.txt", "w") as f:
        f.write(release_notes)

    # Get the prompt template for proper chunking
    config_loader = get_config_loader()
    prompt_template = config_loader.get_summarize_prompt_template()

    # Check if chunking is needed
    chunk_info = get_chunk_info(release_notes, prompt_template)
    logger.info(
        f"Raw summarize analysis: {chunk_info['total_tokens']} tokens, "
        f"needs chunking: {chunk_info['needs_chunking']}"
    )

    if not chunk_info["needs_chunking"]:
        # Small payload - process normally
        logger.info("Processing raw summary as single payload")
        result = summary_chain.invoke({"release-notes": release_notes})
    else:
        # Large payload - use chunking
        logger.info(f"Chunking raw summary into {chunk_info['num_chunks']} parts")
        chunks = chunk_text_for_llm(release_notes, prompt_template)

        summaries = []
        current_provider = settings.api.llm_provider

        for i, chunk in enumerate(chunks, 1):
            logger.info(
                f"Processing raw chunk {i}/{len(chunks)} "
                f"({get_chunk_info(chunk)['total_tokens']} tokens)"
            )

            # Add rate limiting for Gemini API
            if current_provider == "gemini" and i > 1:
                logger.info(
                    "Rate limiting: waiting 2 seconds between Gemini requests..."
                )
                time.sleep(2)

            try:
                chunk_summary = summary_chain.invoke({"release-notes": chunk})
                summaries.append(chunk_summary)

                # Save individual chunk summaries for debugging
                chunk_file = data_dir / f"raw_chunk_summary_{i}.txt"
                with open(chunk_file, "w") as f:
                    f.write(chunk_summary)

            except Exception as e:
                if "429" in str(e):
                    logger.error(f"[!][ERROR] Rate Limit exceeded: {e}")
                    break
                logger.error(f"[!][ERROR] Failed to process raw chunk {i}: {e}")
                summaries.append(f"[!][ERROR] Error processing chunk {i}: {str(e)}")

        # Combine all chunk summaries
        result = combine_chunked_summaries(summaries)
        logger.info(f"Combined {len(summaries)} raw chunk summaries into final result")

    # Save final summary
    with open(summary_file, "w") as summary:
        summary.write(result)

    return
