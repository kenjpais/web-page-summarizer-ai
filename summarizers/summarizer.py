import json
from pathlib import Path
from utils.utils import json_to_markdown
from clients.llm_client import LLMClient
from chains.chains import project_summary_chain
from chains.chains import summary_chain
from config.settings import get_settings
from utils.logging_config import get_logger

logger = get_logger(__name__)

settings = get_settings()

# Configuration paths for summarization pipeline
data_dir = Path(settings.directories.data_dir)
config_dir = Path(settings.directories.config_dir)

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
    Generate project-level summaries using LangChain processing.

    This function creates higher-level summaries focused on project
    organization and strategic overview rather than detailed technical
    changes. It uses the project_summary_chain for structured processing.

    Note: This function appears to be a starting point for project-level
    summarization but may need additional implementation.
    """
    logger.info("\n[*] Generating summary for projects...")
    projects_summary_file = data_dir / "projects_summary.txt"

    with open(correlated_file, "r") as cor_file:
        release_notes = json_to_markdown(cor_file.read())

    result = project_summary_chain.invoke({"correlated_info": release_notes})
    with open(projects_summary_file, "w") as summary:
        summary.write(result)
    return result


def summarize_feature_gates():
    with open(correlated_feature_gate_table_file, "r") as f:
        feature_gate_artifacts = json.load(f)

    with open(summarized_features_file, "w") as f:
        # Feature gate summaries Generated with Google Gemini, hardcoding for temp testing until Gemini is used with langchain
        json.dump(
            {
                "RouteExternalCertificate": "The **RouteExternalCertificate** feature gate has been promoted to the default feature set, meaning it is now enabled by default for both Self-Managed and HyperShift OpenShift environments. This change makes it easier for developers and operators to leverage external certificates for routes, as the functionality is now natively available without explicit feature gate activation.",
                "GatewayAPI": "The **GatewayAPI** feature has been updated with several key improvements. The **GatewayAPIController** feature gate has been introduced to separate the lifecycle management of Gateway API Custom Resource Definitions (CRDs) from the Gateway Controller itself, which aids in staging component releases. Additionally, Gateway API resources and OpenShift Service Mesh (OSSM) resources are now included in must-gather reports, improving debugging and troubleshooting for operators. Furthermore, the existing Gateway API feature gate has been updated to be enabled in clusters utilizing either the DevPreviewNoUpgrade or TechPreviewNoUpgrade feature sets, broadening its accessibility for early adopters.",
                "GatewayAPIController": "A new feature gate, **GatewayAPIController**, has been implemented to separate the installation of OpenShift Service Mesh (OSSM) from the existing **GatewayAPI** feature gate. This provides distinct control over the Gateway API CRDs and the Gateway Controller, which will facilitate more streamlined and independent component releases. When this feature gate is disabled, the gatewayclass and service-dns controllers will not start.",
                "OnClusterBuild": "The **OnClusterBuild** feature, specifically its Machine Config Operator (MCO) APIs, has been graduated to v1. This API promotion is a foundational step towards the General Availability (GA) of On-Cluster Builds, providing a stable and mature API for developers and operators to interact with this functionality.",
                "VSphereStaticIPs": "The **VSphereStaticIPs** feature gate has been removed. This functionality, which allows for static IP support on vSphere, was generally available in OpenShift 4.16, and its feature gate has been cleaned up as part of the ongoing release cycle, making static IP configuration a standard capability without the need for explicit enablement through a feature gate.",
                "ServiceAccountTokenNodeBinding": "The **ServiceAccountTokenNodeBinding** feature gate has been enabled. This brings OpenShift's behavior in line with upstream Kubernetes, where this feature is available in Beta, allowing for improved security and management of service account tokens tied to specific nodes.",
                "MetricsCollectionProfiles": "The **MetricsCollectionProfiles** feature gate has been graduated to General Availability (GA). This signifies that the feature meets the standards for production readiness, providing stable and reliable capabilities for managing and collecting metrics based on defined profiles within OpenShift clusters.",
                "CPMSMachineNamePrefix": "The **CPMSMachineNamePrefix** feature gate has been promoted to the default feature set. This enhancement introduces a new `machineNamePrefix` field within the `ControlPlaneMachineSet` specification, allowing OpenShift administrators and developers to define custom prefixes for Control Plane Machine names. This provides greater flexibility in naming conventions for control plane nodes, making it easier to identify and manage them within complex environments. When a prefix is specified and the feature is enabled, machine names will combine the custom prefix with a randomly generated string and the machine index; otherwise, the default naming convention will be used.",
                "ConsolePluginContentSecurityPolicy": "The **ConsolePluginContentSecurityPolicy** feature gate has been lifted, signifying its promotion to a generally available capability. This allows for the configuration of Content Security Policy (CSP) for Console Plugins, enhancing the security posture of the OpenShift Console by controlling which content sources are permitted for execution, thus mitigating risks such as cross-site scripting (XSS) attacks.",
                "VSphereControlPlaneMachineSet": "The **VSphereControlPlaneMachineSet** feature gate has been removed. This indicates that the functionality related to managing Control Plane Machine Sets on vSphere is now a standard and fully integrated capability, no longer requiring a feature gate for enablement. This also includes a fix to ensure the associated Custom Resource Definition (CRD) has its configuration available by default.",
                "AdditionalRoutingCapabilities": "The **AdditionalRoutingCapabilities** feature gate has been promoted, leading to the deployment of the `frr-k8s` daemonset by the Cluster Network Operator (CNO). This feature is specifically designed for bare-metal OpenShift deployments and is crucial for core functionalities of MetalLB. The `frr-k8s` daemonset was previously deployed by the MetalLB operator but is now handled by the CNO, streamlining the deployment process and providing essential routing capabilities for bare-metal environments.",
                "CSIDriverSharedResource": "The **CSIDriverSharedResource** feature gate has been removed. This indicates that the functionality related to CSI driver shared resources is now a standard and fully integrated part of OpenShift's storage capabilities, no longer requiring a feature gate for enablement.",
                "OpenShiftPodSecurityAdmission": "The **OpenShiftPodSecurityAdmission** feature gate will enforce the `EnsurePSANotPrivileged` policy by default starting with OpenShift 4.19 and later releases. This change impacts how Pod Security Admission policies are applied, ensuring a more secure posture for pods by default in newer OpenShift versions compared to 4.18, where this policy was not enforced by default.",
            },
            f,
        )
    # return feature_gate_summary_chain.invoke(
    #    {"feature-gates": f"""Feature Gates:\n{feature_gates}"""}
    # )


def summarize():
    logger.info("\n[*] Summarizing...")
    current_settings = get_settings()
    if current_settings.processing.summarize_enabled:
        summarize_correlated_info()


def summarize_correlated_info():
    with open(correlated_file, "r") as cor_file:
        correlated_info_md = json_to_markdown(cor_file.read())

    release_notes = f"""Release information:\n{correlated_info_md}"""

    with open(data_dir / "release_notes_payload.txt", "w") as f:
        f.write(release_notes)

    result = summary_chain.invoke({"release-notes": release_notes})
    with open(summary_file, "w") as summary:
        summary.write(result)


def raw_summarize():
    """
    Feature gates are structured in a separate section for better highlighting.
    """
    with open(correlated_feature_gate_table_file, "r") as f:
        feature_gate_info_md = json_to_markdown(f.read())
    with open(correlated_file, "r") as cor_file:
        correlated_info_md = json_to_markdown(cor_file.read())

    release_notes = f"""FeatureGates:\n{feature_gate_info_md}\nRelease information:\n{correlated_info_md}"""

    with open(data_dir / "release_notes_payload.txt", "w") as f:
        f.write(release_notes)

    result = summary_chain.invoke({"release-notes": release_notes})
    with open(summary_file, "w") as summary:
        summary.write(result)

    return

    def build_prompt_payload(release_notes):
        summarize_prompt_template = config_dir / "summarize_prompt_template.txt"
        example_summary_file_path = config_dir / "example_summary.txt"

        with open(summarize_prompt_template, "r") as template_file, open(
            example_summary_file_path, "r"
        ) as example_file:
            example_summary = example_file.read()
            prompt_payload_str = template_file.read()

            prompt_payload_str = prompt_payload_str.replace(
                "{summary-example}", f"\n{example_summary}"
            )
            prompt_payload_str = prompt_payload_str.replace(
                "{release-notes}", f"\n{release_notes}"
            )

        with open(prompt_payload, "w") as out:
            out.write(prompt_payload_str)

        return prompt_payload_str

    result = LLMClient().prompt_llm(build_prompt_payload(summarized_projects))
    with open(summary_file, "w") as summary:
        summary.write(result)
