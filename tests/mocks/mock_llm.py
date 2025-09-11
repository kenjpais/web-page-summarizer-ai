"""Mock LLM for testing."""

from typing import Any, Dict, Optional, Union
from langchain_core.runnables import Runnable


class MockLLM(Runnable):
    """Mock LLM that returns predefined responses."""

    def __init__(self):
        super().__init__()
        self.responses = {
            # Feature gate summaries
            "CSIDriverSharedResource": "A feature gate for CSI driver shared resource support",
            "VSphereControlPlaneMachineSet": "A feature gate for vSphere control plane machine set",
            "VSphereStaticIPs": "A feature gate for vSphere static IPs",
            "GatewayAPI": "A feature gate for Gateway API support",
            "AdditionalRoutingCapabilities": "A feature gate for additional routing capabilities",
            "ConsolePluginContentSecurityPolicy": "A feature gate for console plugin content security policy",
            "MetricsCollectionProfiles": "A feature gate for metrics collection profiles",
            "OnClusterBuild": "A feature gate for on-cluster build support",
            "OpenShiftPodSecurityAdmission": "A feature gate for OpenShift pod security admission",
            "RouteExternalCertificate": "A feature gate for route external certificate",
            "ServiceAccountTokenNodeBinding": "A feature gate for service account token node binding",
            "CPMSMachineNamePrefix": "A feature gate for CPMS machine name prefix",
            "GatewayAPIController": "A feature gate for Gateway API controller",
        }

    def invoke(
        self,
        input: Union[str, Dict[str, Any]],
        config: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> str:
        """Return a predefined response based on input."""
        if isinstance(input, dict):
            if "feature-gate" in input:
                # Extract feature gate name from input
                feature_gate = input["feature-gate"]
                if isinstance(feature_gate, dict):
                    # Get first key from the dict
                    feature_gate_name = next(iter(feature_gate))
                    return self.responses.get(feature_gate_name, "No summary available")
                return "No summary available"
            elif "release-notes" in input:
                return """# Release Summary

## Project Overview
Mock release notes summary with proper formatting.

## Key Changes
- Change 1
- Change 2

## Impact Analysis
No major impacts identified."""
            elif "correlated_info" in input:
                return """# Release Summary

## Project Status
Mock correlated info summary with proper formatting.

## Features
- Feature 1
- Feature 2

## Dependencies
No major dependencies."""
        return """# Release Summary

## General Information
Mock response with proper formatting.

## Details
- Detail 1
- Detail 2"""


class MockLLMClient(Runnable):
    """Mock LLM client that uses MockLLM."""

    def __init__(self, api_settings=None):
        super().__init__()
        self._client = MockLLM()

    def invoke(self, *args, **kwargs):
        return self._client.invoke(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._client, name)


def create_mock_llm(api_settings=None):
    """Create a mock LLM client."""
    return MockLLMClient(api_settings)
