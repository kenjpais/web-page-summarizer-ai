"""
Advanced text chunking utilities optimized for Gemini 1.5 Pro API.
Implements accurate token counting, rate limiting, and semantic chunking.
"""

import time
from typing import List, Dict, Optional
from dataclasses import dataclass
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
    MarkdownHeaderTextSplitter,
)
from langchain.docstore.document import Document
from config.settings import AppSettings


@dataclass
class ChunkMetadata:
    """Metadata for a text chunk"""

    token_count: int
    chunk_index: int
    total_chunks: int
    semantic_section: str


class GeminiTokenizer:
    """Accurate token counter for Gemini models using the official tokenizer"""

    def __init__(self, settings: AppSettings):
        # Initialize Gemini model for token counting
        self.model = ChatGoogleGenerativeAI(
            model=settings.api.gemini_model,
            google_api_key=settings.api.google_api_key,
            temperature=0.0,
        )

    def count_tokens(self, text: str) -> int:
        """
        Get accurate token count for text using Gemini's tokenizer

        Args:
            text: Input text to count tokens for

        Returns:
            Number of tokens in the text
        """
        return self.model.get_num_tokens(text)


class GeminiChunkManager:
    """
    Manages text chunking optimized for Gemini 1.5 Pro limits
    - Implements semantic chunking
    - Handles rate limits
    - Tracks token counts accurately
    """

    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.tokenizer = GeminiTokenizer()
        self.last_request_time = 0
        self.requests_in_current_minute = 0
        self.requests_today = 0

        # Gemini 1.5 Pro limits
        self.MAX_INPUT_TOKENS = 1_048_576
        self.MAX_OUTPUT_TOKENS = 65_536
        self.REQUESTS_PER_MINUTE = 5
        self.REQUESTS_PER_DAY = 25

        # Configure chunking parameters
        self.chunk_size = int(self.MAX_INPUT_TOKENS * 0.8)  # 80% of max tokens
        self.chunk_overlap = 1000  # tokens

    def _create_markdown_splitter(self) -> MarkdownHeaderTextSplitter:
        """Create a markdown-aware text splitter"""
        headers_to_split_on = [
            ("#", "header1"),
            ("##", "header2"),
            ("###", "header3"),
        ]
        return MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)

    def _create_semantic_splitter(self) -> RecursiveCharacterTextSplitter:
        """Create a semantic-aware text splitter"""
        return RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=self.tokenizer.count_tokens,
            separators=[
                "\n\n",  # Paragraphs
                "\n",  # Lines
                ". ",  # Sentences
                ", ",  # Phrases
                " ",  # Words
                "",  # Characters
            ],
        )

    def can_make_request(self) -> bool:
        """Check if we can make a request within rate limits"""
        current_time = time.time()

        # Reset counters if a minute has passed
        if current_time - self.last_request_time >= 60:
            self.requests_in_current_minute = 0
            self.last_request_time = current_time

        # Reset daily counter at midnight
        if (
            time.localtime(current_time).tm_mday
            != time.localtime(self.last_request_time).tm_mday
        ):
            self.requests_today = 0

        return (
            self.requests_in_current_minute < self.REQUESTS_PER_MINUTE
            and self.requests_today < self.REQUESTS_PER_DAY
        )

    def wait_for_rate_limit(self):
        """Wait until we can make another request"""
        while not self.can_make_request():
            time.sleep(1)  # Wait 1 second and check again

        # Update request counters
        self.requests_in_current_minute += 1
        self.requests_today += 1
        self.last_request_time = time.time()

    def chunk_text(self, text: str, prompt_template: str = "") -> List[Dict[str, str]]:
        """
        Split text into optimal chunks for Gemini processing

        Args:
            text: Text to chunk
            prompt_template: Optional prompt template to account for in token counts

        Returns:
            List of chunks with metadata
        """
        # Account for prompt template tokens
        template_tokens = self.tokenizer.count_tokens(
            prompt_template.replace("{release-notes}", "")
        )
        available_tokens = (
            self.MAX_INPUT_TOKENS - template_tokens - 1000
        )  # Safety margin

        # First try markdown-aware splitting
        md_splitter = self._create_markdown_splitter()
        md_docs = md_splitter.split_text(text)

        # Then apply semantic splitting to any large sections
        semantic_splitter = self._create_semantic_splitter()
        chunks = []

        for doc in md_docs:
            if self.tokenizer.count_tokens(doc.page_content) > available_tokens:
                # Split large sections further
                sub_chunks = semantic_splitter.split_text(doc.page_content)
                for sub_chunk in sub_chunks:
                    chunks.append(
                        {
                            "content": sub_chunk,
                            "metadata": ChunkMetadata(
                                token_count=self.tokenizer.count_tokens(sub_chunk),
                                chunk_index=len(chunks),
                                total_chunks=len(sub_chunks),
                                semantic_section=doc.metadata.get("header1", ""),
                            ),
                        }
                    )
            else:
                chunks.append(
                    {
                        "content": doc.page_content,
                        "metadata": ChunkMetadata(
                            token_count=self.tokenizer.count_tokens(doc.page_content),
                            chunk_index=len(chunks),
                            total_chunks=len(md_docs),
                            semantic_section=doc.metadata.get("header1", ""),
                        ),
                    }
                )

        return chunks

    def combine_summaries(
        self, summaries: List[str], metadata_list: List[ChunkMetadata]
    ) -> str:
        """
        Combine chunk summaries into a coherent final summary

        Args:
            summaries: List of summary strings from different chunks
            metadata_list: List of chunk metadata

        Returns:
            Combined summary with proper formatting
        """
        if not summaries:
            return ""

        if len(summaries) == 1:
            return summaries[0]

        # Group summaries by semantic section
        sections = {}
        for summary, metadata in zip(summaries, metadata_list):
            section = metadata.semantic_section or "General"
            if section not in sections:
                sections[section] = []
            sections[section].append(summary)

        # Combine with semantic structure
        combined = "# Release Summary\n\n"

        for section, section_summaries in sections.items():
            if section != "General":
                combined += f"## {section}\n\n"

            for summary in section_summaries:
                # Clean any conflicting headers
                cleaned_summary = summary.strip()
                if cleaned_summary:
                    combined += cleaned_summary + "\n\n"

        return combined.strip()
