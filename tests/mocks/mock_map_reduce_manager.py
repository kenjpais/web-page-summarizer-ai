"""Mock implementation of MapReduceChainManager for testing."""

from typing import Dict, Any, List
from dataclasses import dataclass
from tests.mocks.mock_chains import MockChain


@dataclass
class MockChunkMetadata:
    """Mock metadata for text chunks."""

    token_count: int
    chunk_index: int
    total_chunks: int
    semantic_section: str = "General"


class MockMapReduceChainManager:
    """Mock implementation of MapReduceChainManager."""

    def __init__(self, reduce_enabled: bool = True, settings=None):
        """Initialize with mock settings."""
        self.settings = settings
        self.reduce_enabled = reduce_enabled
        self.map_chain = MockChain()
        self.reduce_chain = MockChain()
        self.chunk_size = 1000
        self.chunk_overlap = 100

    def process_text(self, key: str, text: str) -> Dict[str, Any]:
        """Process text using mock map-reduce pattern."""
        # Split text into mock chunks
        chunks = text.split("\n\n") if "\n\n" in text else [text]
        chunk_summaries = []

        # Process each chunk
        for i, chunk in enumerate(chunks):
            summary = {
                "content": f"Mock summary for chunk {i+1} of {key}",
                "metadata": MockChunkMetadata(
                    token_count=len(chunk),
                    chunk_index=i,
                    total_chunks=len(chunks),
                    semantic_section=f"Section {i+1}",
                ),
            }
            chunk_summaries.append(summary)

        # Create section summaries
        section_summaries = {
            f"Section {i+1}": f"Mock section summary {i+1}" for i in range(len(chunks))
        }

        # Create final summary
        final_summary = f"""# Summary for {key}

## Overview
Mock summary with {len(chunks)} chunks processed.

## Key Points
- Point 1
- Point 2

## Details
{', '.join(section_summaries.values())}"""

        return {
            "final_summary": final_summary,
            "section_summaries": section_summaries,
            "chunk_summaries": chunk_summaries,
            "metadata": {
                "total_chunks": len(chunks),
                "total_tokens": sum(len(c) for c in chunks),
                "sections": list(section_summaries.keys()),
                "reduce_enabled": self.reduce_enabled,
            },
        }

    def split_text(self, text: str) -> List[Dict[str, Any]]:
        """Split text into mock chunks."""
        chunks = text.split("\n\n") if "\n\n" in text else [text]
        return [
            {
                "content": chunk,
                "metadata": MockChunkMetadata(
                    token_count=len(chunk), chunk_index=i, total_chunks=len(chunks)
                ),
            }
            for i, chunk in enumerate(chunks)
        ]
