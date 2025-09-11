import json
from dataclasses import dataclass
from typing import Any, List, Dict
from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
    RecursiveJsonSplitter,
)
from utils.utils import convert_jira_ids_to_links, json_to_markdown
from chains.chains import Chains
from config.settings import get_config_loader, AppSettings
from utils.logging_config import get_logger, setup_logging
from utils.gemini_tokenizer import GeminiTokenizer

logger = get_logger(__name__)


@dataclass
class ChunkMetadata:
    """Metadata for a text chunk"""

    token_count: int
    chunk_index: int
    total_chunks: int
    semantic_section: str


class MapReduceSummarizer:
    """
    Manages text chunking and summarization using MapReduce pattern.
    """

    def __init__(self, map_chain, reduce_chain, tokenizer, settings):
        """Initialize the manager with settings."""
        self.map_chain = map_chain
        self.reduce_chain = reduce_chain
        self.tokenizer = tokenizer
        self.settings = settings
        self.chunk_size = int(self.settings.api.max_input_tokens_per_request * 0.1)
        self.chunk_overlap = int(self.settings.api.chunk_overlap)
        self.reduce_enabled = self.settings.processing.reduce_enabled

    def split_content(self, content: Any) -> List[Document]:
        """
        Split content into chunks using appropriate splitters based on content type.

        Args:
            content: Content to split (can be JSON object or text)

        Returns:
            List of Document objects with content and metadata
        """
        if isinstance(content, (dict, list)):
            # Handle JSON content
            json_splitter = RecursiveJsonSplitter(
                max_chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                length_function=self.tokenizer.count_tokens,
                separators=["\n\n", "\n", ". ", ", ", " ", ""],
            )
            return json_splitter.split_documents(
                [
                    Document(
                        page_content=json.dumps(content),
                        metadata={"content_type": "json"},
                    )
                ]
            )
        else:
            # Handle text content
            text = content if isinstance(content, str) else str(content)

            # First try markdown-aware splitting
            md_splitter = MarkdownHeaderTextSplitter(
                headers_to_split_on=[
                    ("#", "header1"),
                    ("##", "header2"),
                    ("###", "header3"),
                ]
            )
            md_docs = md_splitter.split_text(text)

            # Then apply semantic splitting to large sections
            semantic_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                length_function=self.tokenizer.count_tokens,
                separators=["\n\n", "\n", ". ", ", ", " ", ""],
            )

            final_docs = []
            for doc in md_docs:
                if self.tokenizer.count_tokens(doc.page_content) > self.chunk_size:
                    # Split large sections further
                    sub_chunks = semantic_splitter.split_text(doc.page_content)
                    for i, chunk in enumerate(sub_chunks):
                        final_docs.append(
                            Document(
                                page_content=chunk,
                                metadata={
                                    **doc.metadata,
                                    "content_type": "text",
                                    "chunk_index": i,
                                    "total_chunks": len(sub_chunks),
                                    "token_count": self.tokenizer.count_tokens(chunk),
                                },
                            )
                        )
                else:
                    doc.metadata.update(
                        {
                            "content_type": "text",
                            "chunk_index": len(final_docs),
                            "total_chunks": len(md_docs),
                            "token_count": self.tokenizer.count_tokens(
                                doc.page_content
                            ),
                        }
                    )
                    final_docs.append(doc)

            return final_docs

    def combine_summaries_simple(
        self, summaries: List[str], sections: List[str]
    ) -> str:
        """
        Combine summaries without using reduce chain.

        Args:
            summaries: List of summaries to combine
            sections: List of section names

        Returns:
            Combined summary with proper structure
        """
        combined = ""
        for section, summary in zip(sections, summaries):
            combined += f"## {section}\n{summary}\n\n"
        return combined.strip()

    def process_text(self, key: str, content: Any) -> Dict[str, Any]:
        """
        Process content using either full MapReduce or Map-only pattern.

        Args:
            key: The key/identifier for this content
            content: Content to process (can be JSON object or text)

        Returns:
            Dictionary containing:
            - final_summary: The combined summary
            - chunk_summaries: Individual chunk summaries
            - metadata: Processing metadata
        """
        if not key or content is None:
            return {
                "final_summary": "",
                "section_summaries": {},
                "chunk_summaries": [],
                "metadata": {},
            }

        # Split content into chunks using appropriate splitter
        docs = self.split_content(content)

        # Create map chain
        map_chain = self.map_chain

        # Map phase - process each chunk
        chunk_summaries = []
        for doc in docs:
            logger.info(
                f"Processing chunk {doc.metadata['chunk_index'] + 1}/{doc.metadata['total_chunks']} "
                f"({doc.metadata['token_count']} tokens)"
            )

            try:
                summary = map_chain.invoke({"key": key, "value": doc.page_content})
                chunk_summaries.append({"content": summary, "metadata": doc.metadata})
            except Exception as e:
                logger.error(f"Failed to process chunk: {e}")
                chunk_summaries.append(
                    {
                        "content": f"[Error processing chunk: {str(e)}]",
                        "metadata": doc.metadata,
                    }
                )

        # Group summaries by section
        sections = {}
        for summary in chunk_summaries:
            section = summary["metadata"].get("header1", "General")
            if section not in sections:
                sections[section] = []
            sections[section].append(summary["content"])

        # Process summaries based on reduce_enabled setting
        if self.reduce_enabled:
            # Create reduce chain
            reduce_chain = self.reduce_chain

            # Reduce phase - combine summaries
            section_summaries = {}
            for section, summaries in sections.items():
                try:
                    section_summary = reduce_chain.invoke(
                        {"value": "\n\n".join(summaries)}
                    )
                    section_summaries[section] = section_summary
                except Exception as e:
                    logger.error(f"Failed to combine section {section}: {e}")
                    section_summaries[section] = f"[Error combining section: {str(e)}]"

            # Final reduce - combine sections
            try:
                final_summary = reduce_chain.invoke(
                    {"value": "\n\n".join(section_summaries.values())}
                )
            except Exception as e:
                logger.error(f"Failed to create final summary: {e}")
                final_summary = "[Error creating final summary]"
        else:
            # Simple combination without reduce chain
            section_summaries = {}
            for section, summaries in sections.items():
                section_summaries[section] = "\n\n".join(summaries)

            final_summary = self.combine_summaries_simple(
                list(section_summaries.values()), list(sections.keys())
            )

        return {
            "final_summary": final_summary,
            "section_summaries": section_summaries,
            "chunk_summaries": chunk_summaries,
            "metadata": {
                "total_chunks": len(docs),
                "total_tokens": sum(doc.metadata["token_count"] for doc in docs),
                "sections": list(sections.keys()),
                "reduce_enabled": self.reduce_enabled,
            },
        }


class Summarizer:
    def __init__(self, settings: AppSettings, chains=None):
        self.settings = settings
        self.chains = chains or Chains(settings)
        self.tokenizer = GeminiTokenizer(settings)
        self.max_request_tokens = self.settings.api.max_input_tokens_per_request
        self.chunk_size = int(self.max_request_tokens * 0.3)
        self.map_reducer = MapReduceSummarizer(
            map_chain=self.chains.map_chain,
            reduce_chain=self.chains.reduce_chain,
            tokenizer=self.tokenizer,
            settings=self.settings,
        )
        jira_filter = get_config_loader(self.settings).get_jira_filter()
        self.valid_issue_types = [
            t.lower()[:-1] + "ies" if t.lower().endswith("y") else t.lower() + "s"
            for t in jira_filter.get("issuetype", {}).get("name", [])
            if t
        ]

    def is_chunk_size_valid(self, text: str) -> bool:
        """
        Check if text is smaller than chunk size
        """
        return self.tokenizer.count_tokens(text) < self.chunk_size

    def summarize(self) -> str:
        """
        Summarize correlated information using MapReduce pattern.

        This function handles release notes by:
        1. Implementing hierarchical chunking based on document structure
        2. Processing chunks with appropriate rate limiting
        3. Combining results into a semantically structured summary

        Raises:
            FileNotFoundError: If correlated file doesn't exist
            json.JSONDecodeError: If correlated file contains invalid JSON
            ValueError: If correlated data is empty or invalid
        """
        try:
            with open(self.settings.file_paths.correlated_file_path, "r") as cor_file:
                correlated_data = json.load(cor_file)

            if not correlated_data:
                raise ValueError("Correlated data file is empty")

            if not isinstance(correlated_data, dict):
                raise ValueError(
                    "Invalid correlated data structure: expected dictionary"
                )

            summary = self.summarize_projects(correlated_data)
            summary = convert_jira_ids_to_links(summary, self.settings.api.jira_server)
            with open(self.settings.file_paths.summary_file_path, "w") as f:
                f.write(summary)
            return summary

        except FileNotFoundError as e:
            logger.error(f"Correlated file not found: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in correlated file: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during summarization: {e}")
            raise

    def summarize_projects(self, correlated_data: dict) -> str:
        """
        Summarize projects using the map-reduce pattern.

        Args:
            correlated_data: Dictionary of project data to summarize

        Returns:
            Formatted string containing all project summaries

        Raises:
            ValueError: If project data is invalid
            RuntimeError: If API rate limit is exceeded
        """
        logger.info(f"\n[*] Summarizing {len(correlated_data)} projects...")
        logger.info(
            f"Using LLM Provider: {self.settings.api.llm_provider} and Model: {self.settings.api.llm_model}"
        )

        all_summaries = []
        for i, (project_name, project_data) in enumerate(correlated_data.items()):
            try:
                if not isinstance(project_data, dict):
                    raise ValueError(f"Invalid project data for {project_name}")

                # Normalize project name
                display_name = (
                    "MISCELLANEOUS" if project_name == "NO-PROJECT" else project_name
                )

                # Process project data based on size and type
                if self.is_chunk_size_valid(json.dumps(project_data)):
                    logger.debug(f"Summarizing project: {display_name}")
                    project_summary = self._summarize(display_name, project_data)
                else:
                    logger.debug(f"Chunking project: {display_name}")
                    project_summary = self.chunk_summarize_project(project_data)

                all_summaries.append(f"## {display_name}\n{project_summary}\n")
                logger.info(
                    f"Summarized {i+1}/{len(correlated_data)} projects: {display_name}"
                )

            except Exception as e:
                logger.error(f"Failed to summarize project {project_name}: {e}")

        if not all_summaries:
            raise ValueError("No projects were successfully summarized")

        return "\n".join(all_summaries)

    def summarize_feature_gates(self):
        """Summarize feature gates."""
        logger.info("[*] Summarizing feature gates...")

        with open(
            self.settings.file_paths.correlated_feature_gate_table_file_path, "r"
        ) as f:
            feature_gate_artifacts = json.load(f)

        feature_gate_summaries = {}

        for feature_gate, artifacts in feature_gate_artifacts.items():
            if feature_gate not in feature_gate_summaries:
                try:
                    summary = self.chains.single_feature_gate_summary_chain.invoke(
                        {"feature-gate": json_to_markdown({feature_gate: artifacts})}
                    )
                    feature_gate_summaries[feature_gate] = (
                        summary if isinstance(summary, str) else None
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to summarize feature gate {feature_gate}: {e}"
                    )
                    feature_gate_summaries[feature_gate] = None

        if not feature_gate_summaries:
            logger.error("No feature gate summaries generated")
            return

        with open(self.settings.file_paths.summarized_features_file_path, "w") as f:
            json.dump(feature_gate_summaries, f)

    def chunk_summarize_project(self, project_data: dict) -> str:
        """
        Chunk and summarize the project data.

        Args:
            project_data: Dictionary containing issue type data eg.(epics, stories, features)

        Returns:
            Combined summary of all valid issue types

        Raises:
            ValueError: If project data is invalid or empty
        """
        if not isinstance(project_data, dict):
            raise ValueError("Project data must be a dictionary")

        if not project_data:
            raise ValueError("Project data is empty")

        return self.map_reduce("project", project_data)
        all_summaries = []
        for issue_type, value in project_data.items():
            try:
                if issue_type not in self.valid_issue_types:
                    logger.warning(
                        f"Skipping issue type: {issue_type} because it is not in the valid issue types"
                    )
                    continue

                if not value:
                    logger.warning(f"Skipping empty value for issue type: {issue_type}")
                    continue

                issue_summary = self.map_reduce(issue_type, value)
                if issue_summary:
                    logger.info(f"Generated summary for issue type {issue_type}")
                    logger.debug(f"Summary content: {issue_summary}")
                    all_summaries.append(f"\n{issue_summary}\n")
                else:
                    logger.warning(
                        f"Empty summary generated for issue type: {issue_type}"
                    )

            except Exception as e:
                logger.error(f"Failed to summarize issue type {issue_type}: {e}")

        if not all_summaries:
            logger.warning("No valid summaries generated for any issue type")
            return "No valid content found to summarize."

        return "\n".join(all_summaries)

    def _summarize(self, key: str, value: Any) -> str:
        """
        Summarize the data using the map-reduce pattern.

        Args:
            key: The key/identifier for this data chunk
            value: The data to summarize

        Returns:
            Summarized string

        Raises:
            ValueError: If key or value is invalid
            RuntimeError: If API limit exceeded
        """
        if not key:
            raise ValueError("Key cannot be empty")

        if value is None:
            raise ValueError("Value cannot be None")

        if not isinstance(value, str):
            value = json_to_markdown(json.dumps(value))

        return self.chains.summary_chain.invoke({"key": key, "value": value})

    def map_reduce(self, key: str, value: Any) -> str:
        """
        Summarize the data using the map-reduce pattern.

        This method handles large data chunks by:
        1. Converting the data to text format
        2. Using MapReduceChainManager to split and process chunks
        3. Returning the reduced combined summary

        Args:
            key: The key/identifier for this data chunk
            value: The data to summarize (can be dict, list, or string)

        Returns:
            A summarized string combining all processed chunks

        Raises:
            ValueError: If key or value is invalid
            RuntimeError: If processing fails or API limit exceeded
        """
        if not key:
            raise ValueError("Key cannot be empty")

        if value is None:
            raise ValueError("Value cannot be None")

        try:
            if not isinstance(value, str):
                value = json_to_markdown(
                    json.dumps(value), jira_server=self.settings.api.jira_server
                )

            result = self.map_reducer.process_text(key, value)

            if not isinstance(result, dict) or "final_summary" not in result:
                raise RuntimeError("Invalid response from map_reduce_manager")

            return result["final_summary"]

        except Exception as e:
            logger.error(f"Failed to process chunk {key}: {e}")
            raise RuntimeError(f"Failed to process chunk: {str(e)}")


if __name__ == "__main__":
    # Set up logging before any operations
    setup_logging()

    settings = AppSettings()
    summarizer = Summarizer(settings)
    summary = summarizer.summarize()
