"""
Chunk manager for optimal distribution and processing of text chunks.
Handles chunk prioritization, merging, and distribution strategies.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import heapq
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
from utils.gemini_chunker import GeminiTokenizer, ChunkMetadata
from utils.semantic_splitter import SemanticSplitter, SplitMetadata
from utils.rate_limiter import GeminiRateLimiter, rate_limited
from config.settings import AppSettings


@dataclass
class ChunkPriority:
    """Priority information for a chunk"""

    importance: float  # 0-1 score based on content relevance
    dependencies: List[int]  # chunk indices this chunk depends on
    dependents: List[int]  # chunk indices that depend on this chunk


@dataclass
class ProcessedChunk:
    """A processed chunk with its summary and metadata"""

    content: str
    summary: str
    metadata: ChunkMetadata
    priority: ChunkPriority


class ChunkManager:
    """
    Manages chunk processing workflow
    - Handles chunk prioritization
    - Manages dependencies between chunks
    - Optimizes processing order
    - Implements smart merging strategies
    """

    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.tokenizer = GeminiTokenizer(settings)
        self.semantic_splitter = SemanticSplitter(settings)
        self.rate_limiter = GeminiRateLimiter()

        # Processing settings
        self.max_parallel_chunks = 2  # Keep well under rate limits
        self.min_merge_similarity = 0.7  # Threshold for merging similar chunks

    def _calculate_chunk_importance(
        self, content: str, metadata: SplitMetadata
    ) -> float:
        """
        Calculate importance score for chunk prioritization

        Args:
            content: Chunk content
            metadata: Chunk metadata

        Returns:
            Importance score between 0 and 1
        """
        importance = 0.5  # Base importance

        # Adjust based on section type and level
        if metadata.section_type == "markdown":
            if metadata.section_level == 1:
                importance += 0.3
            elif metadata.section_level == 2:
                importance += 0.2
            elif metadata.section_level == 3:
                importance += 0.1

        # Adjust based on content indicators
        lower_content = content.lower()
        if any(
            kw in lower_content for kw in ["new", "feature", "important", "breaking"]
        ):
            importance += 0.1

        # Normalize to 0-1
        return min(1.0, importance)

    def _find_chunk_dependencies(
        self, chunks: List[Dict[str, Any]]
    ) -> List[ChunkPriority]:
        """
        Identify dependencies between chunks

        Args:
            chunks: List of chunks with content and metadata

        Returns:
            List of chunk priorities with dependency information
        """
        priorities = []

        for i, chunk in enumerate(chunks):
            # Calculate base importance
            importance = self._calculate_chunk_importance(
                chunk["content"], chunk["metadata"]
            )

            # Find dependencies based on section hierarchy
            dependencies = []
            dependents = []

            for j, other_chunk in enumerate(chunks):
                if i == j:
                    continue

                # Check for parent-child relationships
                if (
                    chunk["metadata"].parent_section
                    and chunk["metadata"].parent_section
                    == other_chunk["metadata"].section_title
                ):
                    dependencies.append(j)

                if (
                    other_chunk["metadata"].parent_section
                    and other_chunk["metadata"].parent_section
                    == chunk["metadata"].section_title
                ):
                    dependents.append(j)

            priorities.append(
                ChunkPriority(
                    importance=importance,
                    dependencies=dependencies,
                    dependents=dependents,
                )
            )

        return priorities

    def _create_processing_order(
        self, chunks: List[Dict[str, Any]], priorities: List[ChunkPriority]
    ) -> List[List[int]]:
        """
        Create optimal processing order for chunks

        Args:
            chunks: List of chunks
            priorities: List of chunk priorities

        Returns:
            List of chunk index groups for parallel processing
        """
        # Create dependency graph
        graph = {i: set(p.dependencies) for i, p in enumerate(priorities)}

        # Track processed chunks and their dependencies
        processed = set()
        processing_order = []

        while len(processed) < len(chunks):
            # Find chunks with no unprocessed dependencies
            available = []
            for i in range(len(chunks)):
                if i not in processed and not (graph[i] - processed):
                    available.append((priorities[i].importance, i))

            if not available:
                # Handle cycles by processing highest priority chunk
                unprocessed = set(range(len(chunks))) - processed
                available = [(priorities[i].importance, i) for i in unprocessed]

            # Sort by importance and take up to max_parallel
            available.sort(reverse=True)
            current_batch = [i for _, i in available[: self.max_parallel_chunks]]
            processing_order.append(current_batch)
            processed.update(current_batch)

        return processing_order

    @rate_limited
    async def _process_chunk(self, content: str, metadata: ChunkMetadata, chain) -> str:
        """Process a single chunk with rate limiting"""
        return await chain.ainvoke({"content": content})

    async def _process_chunk_batch(
        self, chunks: List[Dict[str, Any]], chunk_indices: List[int], chain
    ) -> List[ProcessedChunk]:
        """Process a batch of chunks in parallel"""
        tasks = []
        for idx in chunk_indices:
            chunk = chunks[idx]
            task = self._process_chunk(chunk["content"], chunk["metadata"], chain)
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        processed_chunks = []
        for idx, summary in zip(chunk_indices, results):
            chunk = chunks[idx]
            processed_chunks.append(
                ProcessedChunk(
                    content=chunk["content"],
                    summary=summary,
                    metadata=chunk["metadata"],
                    priority=self.priorities[idx],
                )
            )

        return processed_chunks

    def _remove_duplicate_intro(self, text: str) -> str:
        """
        Remove duplicate introductory text that appears in multiple chunks

        Args:
            text: Text to clean

        Returns:
            Cleaned text without duplicate intros
        """
        # Common intro patterns to remove if they appear after the first occurrence
        intro_patterns = [
            "This document summarizes the user-facing changes included in this software release",
            "This document details the user-facing changes included in",
            "Release Notes",
            "Release Documentation",
            "This document summarizes the",
        ]

        lines = text.split("\n")
        seen_patterns = set()
        filtered_lines = []

        for line in lines:
            should_keep = True
            line_lower = line.lower()
            for pattern in intro_patterns:
                pattern_lower = pattern.lower()
                if pattern_lower in line_lower:
                    if pattern_lower in seen_patterns:
                        should_keep = False
                        break
                    seen_patterns.add(pattern_lower)

            if should_keep:
                filtered_lines.append(line)

        return "\n".join(filtered_lines)

    def _merge_chunks(self, processed_chunks: List[ProcessedChunk]) -> str:
        """
        Merge processed chunks into final summary

        Args:
            processed_chunks: List of processed chunks with summaries

        Returns:
            Combined summary text
        """
        # Sort chunks by section hierarchy and importance
        chunks_by_section = {}
        for chunk in processed_chunks:
            section = chunk.metadata.semantic_section or "General"
            if section not in chunks_by_section:
                chunks_by_section[section] = []
            chunks_by_section[section].append(chunk)

        # Build hierarchical summary
        summary = []

        # Add high-level sections first
        for section, chunks in chunks_by_section.items():
            # Sort chunks by importance within section
            chunks.sort(key=lambda x: x.priority.importance, reverse=True)

            # Merge chunk summaries
            section_summary = []
            for chunk in chunks:
                if chunk.summary.strip():
                    section_summary.append(chunk.summary.strip())

            # Only add section if it has content
            if section_summary:
                if section != "General":
                    summary.append(f"# {section}\n")
                merged_section = "\n".join(section_summary)
                # Remove duplicate intros within the section
                cleaned_section = self._remove_duplicate_intro(merged_section)
                if cleaned_section.strip():
                    summary.append(cleaned_section)
                    summary.append("\n")

        merged_summary = "\n".join(summary).strip()
        # Final pass to remove any remaining duplicates across sections
        return self._remove_duplicate_intro(merged_summary)

    async def process_text(self, text: str, chain, prompt_template: str = "") -> str:
        """
        Process text through chunking and summarization pipeline

        Args:
            text: Input text to process
            chain: LangChain chain for processing chunks
            prompt_template: Optional prompt template

        Returns:
            Final processed summary
        """
        # Split text into semantic chunks
        chunks = self.semantic_splitter.split_text(text)

        # Calculate priorities and dependencies
        self.priorities = self._find_chunk_dependencies(chunks)

        # Create processing order
        processing_order = self._create_processing_order(chunks, self.priorities)

        # Process chunks in optimal order
        processed_chunks = []
        for batch_indices in processing_order:
            batch_results = await self._process_chunk_batch(
                chunks, batch_indices, chain
            )
            processed_chunks.extend(batch_results)

        # Merge results
        final_summary = self._merge_chunks(processed_chunks)

        return final_summary
