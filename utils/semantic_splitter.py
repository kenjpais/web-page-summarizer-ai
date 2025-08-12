"""
Markdown-focused semantic text splitting utilities using LangChain.
Optimized for splitting markdown release notes and documentation.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from langchain.text_splitter import MarkdownHeaderTextSplitter
from config.settings import AppSettings
from utils.gemini_chunker import GeminiTokenizer


@dataclass
class SplitMetadata:
    """Metadata for a semantic split"""

    section_level: int  # header level (1-6)
    section_title: str  # header title
    parent_section: Optional[str]  # parent section title
    section_type: str = "markdown"  # type of section (always markdown in this case)
    semantic_section: str = ""  # semantic section name


class SemanticSplitter:
    """
    Markdown-focused text splitter that preserves document structure
    - Splits on markdown headers
    - Maintains document hierarchy
    - Preserves section relationships
    """

    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.tokenizer = GeminiTokenizer(settings)

        # Configure splitting parameters
        self.chunk_overlap = 200  # tokens
        self.min_chunk_size = 100  # tokens

    def _create_markdown_splitter(self) -> MarkdownHeaderTextSplitter:
        """Create a markdown-aware splitter"""
        headers_to_split_on = [
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
            ("####", "h4"),
        ]
        return MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)

    def split_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Split markdown text while preserving semantic structure

        Args:
            text: Markdown text to split

        Returns:
            List of chunks with metadata
        """
        md_splitter = self._create_markdown_splitter()
        chunks = []

        # First split by headers
        md_chunks = md_splitter.split_text(text)

        for chunk in md_chunks:
            # Get header level and title
            header_level = 0
            header_title = ""
            parent_header = None

            # Extract header info from metadata
            for key, value in chunk.metadata.items():
                if key.startswith("h") and value:
                    level = int(key[1])
                    if level > header_level:
                        header_level = level
                        header_title = value

            # Find parent header
            for key, value in chunk.metadata.items():
                if key.startswith("h") and value and int(key[1]) < header_level:
                    parent_header = value

            # Calculate token count
            token_count = self.tokenizer.count_tokens(chunk.page_content)

            # If chunk is too large, split it further by paragraphs
            if token_count > self.settings.api.max_input_tokens:
                paragraphs = chunk.page_content.split("\n\n")
                current_chunk = []
                current_tokens = 0

                for paragraph in paragraphs:
                    paragraph_tokens = self.tokenizer.count_tokens(paragraph)

                    # If this paragraph alone is too large, split it into sentences
                    if paragraph_tokens > self.settings.api.max_input_tokens:
                        sentences = paragraph.split(". ")
                        for sentence in sentences:
                            sentence_tokens = self.tokenizer.count_tokens(sentence)
                            if sentence_tokens <= self.settings.api.max_input_tokens:
                                chunks.append(
                                    {
                                        "content": sentence,
                                        "metadata": SplitMetadata(
                                            section_level=header_level,
                                            section_title=header_title,
                                            parent_section=parent_header,
                                        ),
                                    }
                                )
                        continue

                    # If adding this paragraph would exceed limit, save current chunk
                    if (
                        current_tokens + paragraph_tokens
                        > self.settings.api.max_input_tokens
                    ):
                        if current_chunk:  # Only save if we have content
                            chunks.append(
                                {
                                    "content": "\n\n".join(current_chunk),
                                    "metadata": SplitMetadata(
                                        section_level=header_level,
                                        section_title=header_title,
                                        parent_section=parent_header,
                                    ),
                                }
                            )
                        current_chunk = [paragraph]
                        current_tokens = paragraph_tokens
                    else:
                        current_chunk.append(paragraph)
                        current_tokens += paragraph_tokens

                # Save any remaining content
                if current_chunk:
                    chunks.append(
                        {
                            "content": "\n\n".join(current_chunk),
                            "metadata": SplitMetadata(
                                section_level=header_level,
                                section_title=header_title,
                                parent_section=parent_header,
                            ),
                        }
                    )
            else:
                # Chunk is small enough, keep as is
                chunks.append(
                    {
                        "content": chunk.page_content,
                        "metadata": SplitMetadata(
                            section_level=header_level,
                            section_title=header_title,
                            parent_section=parent_header,
                        ),
                    }
                )

        return chunks
