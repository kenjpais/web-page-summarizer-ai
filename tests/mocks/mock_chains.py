"""Mock implementation of Chains class for testing."""

from typing import Dict, Any
from langchain_core.runnables import Runnable


class MockChain(Runnable):
    """Mock chain that returns predefined responses."""

    def __init__(self):
        super().__init__()
        self.rate_limiter = None

    def invoke(self, input_dict: Dict[str, Any]) -> str:
        """Return a mock summary based on input."""
        if self.rate_limiter:

            @self.rate_limiter.check_rate_limit
            def _invoke(_input_dict: Dict[str, Any]) -> str:
                key = _input_dict.get("key", "unknown")
                return f"Mock summary for: {key}"

            return _invoke(input_dict)
        else:
            key = input_dict.get("key", "unknown")
            return f"Mock summary for: {key}"


class MockChains:
    """Mock chains for testing."""

    def __init__(self, settings):
        """Initialize with mock chains."""
        self.settings = settings
        self.llm_client = MockChain()  # Add llm_client attribute
        self.map_chain = MockChain()
        self.reduce_chain = MockChain()
        self.summary_chain = MockChain()
        self.summarize_single_feature_gate_chain = MockChain()

        # Set rate limiter for all chains
        self.rate_limiter = None

    def set_rate_limiter(self, rate_limiter):
        """Set rate limiter for all chains."""
        self.rate_limiter = rate_limiter
        self.llm_client.rate_limiter = rate_limiter
        self.map_chain.rate_limiter = rate_limiter
        self.reduce_chain.rate_limiter = rate_limiter
        self.summary_chain.rate_limiter = rate_limiter
        self.summarize_single_feature_gate_chain.rate_limiter = rate_limiter

    def get_chain_by_name(self, name: str) -> MockChain:
        """Get a mock chain by name."""
        chain = getattr(self, f"{name}_chain", MockChain())
        chain.rate_limiter = self.rate_limiter
        return chain
