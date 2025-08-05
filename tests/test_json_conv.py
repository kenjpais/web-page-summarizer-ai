import unittest
from utils.parser_utils import convert_json_text_to_dict

json_text = """
```json
{
  "OnClusterBuild": "The Machine Config Operator (MCO) APIs for OnClusterBuild have been graduated from v1alpha1 to v1, preparing the feature for general availability.  This involved updates to the openshift/api repository.",
  "ConsolePluginContentSecurityPolicy": "The OpenShift command-line interface (CLI) binaries for both Red Hat Enterprise Linux (RHEL) 8 and RHEL 9 are now distributed via the console-operator.  The `ConsoleCLIDownloads` Custom Resource (CR) has been updated to include these binaries, improving CLI accessibility for users on different RHEL versions.",
  "GatewayAPIController": "The `GatewayAPIController` feature gate has been enabled in the Default feature set. This makes the OpenShift Gateway API controller, currently based on Istio, available by default, simplifying deployment and improving usability.  This change follows the completion of required implementation tasks and the addition of five origin tests.",
  "VSphereStaticIPs": "All feature gate logic related to vSphere Static IP support has been removed.  The feature is now enabled by default, with the option to disable it via install-config. This simplifies the codebase and removes unnecessary feature gate checks.",
  "RouteExternalCertificate": "The `RouteExternalCertificate` feature gate has been promoted to the default feature set and is enabled by default. This simplifies the configuration and improves the user experience.",
  "VSphereControlPlaneMachineSet": "All feature gate logic for vSphere Control Plane Machine Set (CPMS) support has been removed. The feature is now enabled by default, with the option to disable it via install-config. This streamlines the codebase and eliminates redundant feature gate checks.",
  "GatewayAPI": "The `GatewayAPIController` feature gate has been enabled in the Default feature set, making the OpenShift Gateway API controller available by default.  The Cluster Ingress Operator (CIO) now ensures the Gateway API CRDs are present at a specific version and marks the cluster as degraded if unmanaged CRDs exist.  The `GatewayAPI` feature gate, covering Gateway API CRD lifecycle management, has also been enabled in the Default feature set.  Additionally, the CIO's `relatedObjects` field now includes Gateway API and potentially OSSM resources in must-gather reports, improving troubleshooting capabilities.  The Gateway API is now enabled in clusters with either the DevPreviewNoUpgrade or TechPreviewNoUpgrade feature set.",
  "CPMSMachineNamePrefix": "The `CPMSMachineNamePrefix` feature gate has been promoted to the default feature set and is enabled by default. This allows users to customize the naming format of Control Plane Machines via a new `machineNamePrefix` field in the ControlPlaneMachineSet spec. The implementation uses this prefix to generate machine names, superseding the previous control plane label and role combination.",
  "CSIDriverSharedResource": "The Shared Resource CSI Driver feature, previously available as a tech preview, has been removed.  This is due to its general availability through the Builds for OpenShift layered product.",
  "AdditionalRoutingCapabilities": "The `additionalRoutingCapabilities` feature gate has been promoted to the default feature set. This enables the deployment of the frr-k8s daemonset by the Cluster Network Operator (CNO), which is used by features such as MetalLB.",
  "OpenShiftPodSecurityAdmission": "The behavior of `EnsurePSANotPrivileged` has been adjusted for OpenShift 4.19 and later releases.  The exact change is not specified.",
  "ServiceAccountTokenNodeBinding": "The `ServiceAccountTokenNodeBinding` feature gate has been enabled. This aligns OpenShift with the Kubernetes beta feature.",
  "MetricsCollectionProfiles": "The `MetricsCollectionProfiles` feature gate has been graduated to general availability. This allows for more flexible and customized metrics collection."
}
"""


class TestJsonConv(unittest.TestCase):
    def test(self):
        res = convert_json_text_to_dict(json_text)
        self.assertTrue(isinstance(res, dict))
        self.assertEqual(
            list(res.keys()),
            [
                "OnClusterBuild",
                "ConsolePluginContentSecurityPolicy",
                "GatewayAPIController",
                "VSphereStaticIPs",
                "RouteExternalCertificate",
                "VSphereControlPlaneMachineSet",
                "GatewayAPI",
                "CPMSMachineNamePrefix",
                "CSIDriverSharedResource",
                "AdditionalRoutingCapabilities",
                "OpenShiftPodSecurityAdmission",
                "ServiceAccountTokenNodeBinding",
                "MetricsCollectionProfiles",
            ],
        )
