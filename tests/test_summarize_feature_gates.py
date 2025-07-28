import json
import unittest
from summarizers.summarizer import summarize_feature_gates
from correlators.correlator import correlate_table, correlate_with_jira_issue_id
from config.settings import get_settings
from utils.logging_config import get_logger, setup_logging

setup_logging()

logger = get_logger(__name__)

settings = get_settings()
data_dir = settings.directories.data_dir
test_data_dir = settings.directories.test_data_dir

summarized_features_file = data_dir / "summarized_features.json"


class TestSummarizeFeatureGates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        url = (
            "https://amd64.origin.releases.ci.openshift.org/releasestream/"
            "4-scos-stable/release/4.19.0-okd-scos.0"
        )
        cls.data_dir = data_dir
        cls.correlated_table_file = cls.data_dir / "correlated_feature_gate_table.json"
        cls.expected_feature_gates = set(
            sorted(
                {
                    "CSIDriverSharedResource",
                    "VSphereControlPlaneMachineSet",
                    "VSphereStaticIPs",
                    "GatewayAPI",
                    "AdditionalRoutingCapabilities",
                    "ConsolePluginContentSecurityPolicy",
                    "MetricsCollectionProfiles",
                    "OnClusterBuild",
                    "OpenShiftPodSecurityAdmission",
                    "RouteExternalCertificate",
                    "ServiceAccountTokenNodeBinding",
                    "CPMSMachineNamePrefix",
                    "GatewayAPIController",
                }
            )
        )

        def run_pipeline():
            correlate_with_jira_issue_id(data_directory=test_data_dir)
            correlate_table()
            summarize_feature_gates()

        run_pipeline()

        with open(summarized_features_file, "r") as f:
            cls.summarized_features = json.load(f)

    def test_summarize_feature_gates(self):
        result = self.summarized_features
        self.assertTrue(isinstance(result, dict))
        self.assertTrue(self.expected_feature_gates.issubset(set(result.keys())))
