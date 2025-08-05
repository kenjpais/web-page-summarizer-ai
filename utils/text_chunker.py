"""
Text chunking utilities for managing large payloads to LLM APIs.
Handles token counting and text splitting to stay within API limits.
"""

import re
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config.settings import get_settings


def estimate_token_count(text: str) -> int:
    """
    Estimate token count using a simple approximation.

    This is a rough estimate based on:
    - Average 4 characters per token for English text
    - Adjustment for markdown formatting

    For production use, consider using tiktoken for more accurate counting.

    Args:
        text: Input text to estimate tokens for

    Returns:
        Estimated number of tokens
    """
    # Remove extra whitespace and normalize
    cleaned_text = re.sub(r"\s+", " ", text.strip())

    # Rough estimation: ~4 characters per token for English
    # Add extra for markdown formatting, JSON structure, etc.
    char_count = len(cleaned_text)
    estimated_tokens = int(char_count / 3.5)  # Slightly conservative

    return estimated_tokens


def chunk_text_for_llm(text: str, prompt_template: str = "") -> List[str]:
    """
    Split large text into chunks that fit within LLM token limits.

    Args:
        text: The text to be chunked
        prompt_template: The prompt template that will wrap the text (for size estimation)

    Returns:
        List of text chunks, each small enough to fit within token limits
    """
    settings = get_settings()

    # Estimate tokens in the prompt template (without the {release-notes} placeholder)
    template_tokens = estimate_token_count(
        prompt_template.replace("{release-notes}", "")
    )

    # Reserve space for prompt + response + safety margin
    available_tokens = (
        settings.api.max_input_tokens - template_tokens - 2000
    )  # 2000 token safety margin

    # If text is small enough, return as single chunk
    if estimate_token_count(text) <= available_tokens:
        return [text]

    # Configure text splitter for large texts
    text_splitter = RecursiveCharacterTextSplitter(
        # Convert token limits to approximate character limits
        chunk_size=int(available_tokens * 3.5),  # ~3.5 chars per token
        chunk_overlap=int(settings.api.chunk_overlap * 3.5),
        length_function=len,
        separators=[
            "\n\n",  # Prefer splitting on paragraphs
            "\n",  # Then on lines
            ". ",  # Then on sentences
            " ",  # Finally on words
            "",  # Last resort: split anywhere
        ],
    )

    chunks = text_splitter.split_text(text)

    # Validate chunk sizes
    validated_chunks = []
    for i, chunk in enumerate(chunks):
        chunk_tokens = estimate_token_count(chunk)
        if chunk_tokens > available_tokens:
            # If chunk is still too large, split it more aggressively
            smaller_splitter = RecursiveCharacterTextSplitter(
                chunk_size=int(available_tokens * 3.0),  # More conservative
                chunk_overlap=500,
                length_function=len,
                separators=["\n", ". ", " ", ""],
            )
            sub_chunks = smaller_splitter.split_text(chunk)
            validated_chunks.extend(sub_chunks)
        else:
            validated_chunks.append(chunk)

    return validated_chunks


def combine_chunked_summaries(summaries: List[str]) -> str:
    """
    Combine multiple summary chunks into a coherent final summary.

    Args:
        summaries: List of summary strings from different chunks

    Returns:
        Combined summary with proper formatting
    """
    if not summaries:
        return ""

    if len(summaries) == 1:
        return summaries[0]

    # Combine summaries with clear section breaks
    combined = "# Release Summary\n\n"

    for i, summary in enumerate(summaries, 1):
        # Remove any existing headers that might conflict
        cleaned_summary = re.sub(r"^#+\s*", "", summary.strip(), flags=re.MULTILINE)

        if len(summaries) > 1:
            combined += f"## Part {i}\n\n"

        combined += cleaned_summary.strip() + "\n\n"

    return combined.strip()


def get_chunk_info(text: str, prompt_template: str = "") -> dict:
    """
    Get information about how text would be chunked without actually chunking it.

    Args:
        text: Text to analyze
        prompt_template: Prompt template for context

    Returns:
        Dictionary with chunking information
    """
    chunks = chunk_text_for_llm(text, prompt_template)

    return {
        "total_tokens": estimate_token_count(text),
        "num_chunks": len(chunks),
        "chunk_sizes": [estimate_token_count(chunk) for chunk in chunks],
        "needs_chunking": len(chunks) > 1,
    }
