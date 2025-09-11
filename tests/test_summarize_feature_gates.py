import json
import unittest

from unittest.mock import patch
from summarizers.summarizer import Summarizer
from utils.file_utils import copy_file, delete_all_in_directory
from config.settings import get_settings
from utils.logging_config import get_logger, setup_logging
from tests.mocks.mock_llm import create_mock_llm
from tests.mocks.mock_gemini_tokenizer import MockGeminiTokenizer

setup_logging()

logger = get_logger(__name__)

# Clear settings cache to pick up new environment variables
get_settings.cache_clear()
settings = get_settings()

data_dir = settings.directories.data_dir
test_data_dir = settings.directories.test_data_dir

correlated_feature_gate_table_file = (
    test_data_dir / "correlated_feature_gate_table.json"
)
correlated_file = test_data_dir / "correlated.json"
summarized_features_file = data_dir / "summarized_features.json"


class TestSummarizeFeatureGates(unittest.TestCase):
    @classmethod
    @patch("clients.local_llm_client.create_local_llm", side_effect=create_mock_llm)
    @patch("utils.gemini_tokenizer.GeminiTokenizer", side_effect=MockGeminiTokenizer)
    def setUpClass(cls, mock_create_llm, mock_tokenizer):
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

        delete_all_in_directory(data_dir)

        # Mock data
        copy_file(src_path=correlated_feature_gate_table_file, dest_dir=data_dir)
        copy_file(src_path=correlated_file, dest_dir=data_dir)

        summarizer = Summarizer(settings)
        summarizer.summarize_feature_gates()

        with open(summarized_features_file, "r") as f:
            cls.summarized_features = json.load(f)

    def test_summarize_feature_gates(self):
        result = self.summarized_features
        self.assertTrue(isinstance(result, dict))
        self.assertTrue(self.expected_feature_gates.issubset(set(result.keys())))
        self.assertTrue(isinstance(result, dict))
        self.assertTrue(len(result) > 0)
        self.assertTrue(all(isinstance(k, str) for k in result.keys()))
        self.assertTrue(all(isinstance(v, str) for v in result.values()))
        self.assertTrue(all(isinstance(k, str) for k in result.keys()))
