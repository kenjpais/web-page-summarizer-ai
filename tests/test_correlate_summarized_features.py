import os
import json
import unittest

from unittest.mock import patch
from correlators.correlator import Correlator
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

correlated_file = test_data_dir / "correlated.json"
correlated_feature_gate_table = test_data_dir / "correlated_feature_gate_table.json"
summarized_features_file = test_data_dir / "summarized_features.json"
feature_gate_project_map_file = test_data_dir / "feature_gate_project_map.pkl"


class TestCorrelateTable(unittest.TestCase):
    @classmethod
    @patch("clients.local_llm_client.create_local_llm", side_effect=create_mock_llm)
    @patch("utils.gemini_tokenizer.GeminiTokenizer", side_effect=MockGeminiTokenizer)
    def setUpClass(cls, mock_create_llm, mock_tokenizer):
        # Ensure FILTER_ON is True for this test (restore original .env value)
        # This is needed because other tests may have modified os.environ["FILTER_ON"]
        os.environ["FILTER_ON"] = "True"
        get_settings.cache_clear()

        # Result files
        cls.data_dir = data_dir
        cls.correlated_table_file = cls.data_dir / "correlated_feature_gate_table.json"
        cls.summarized_features_file = cls.data_dir / "summarized_features.json"
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
        copy_file(src_path=correlated_file, dest_dir=data_dir)
        copy_file(src_path=correlated_feature_gate_table, dest_dir=data_dir)
        copy_file(src_path=summarized_features_file, dest_dir=data_dir)
        copy_file(src_path=feature_gate_project_map_file, dest_dir=data_dir)

        summarizer = Summarizer(settings)
        summarizer.summarize_feature_gates()
        correlator = Correlator(settings)
        correlator.correlate_summarized_features()

        with open(cls.correlated_table_file, "r") as f:
            cls.correlated_table = json.load(f)

        with open(cls.summarized_features_file, "r") as f:
            cls.summarized_features = json.load(f)

    def test_feature_gate_presence_in_summarized_features(self):
        self.assertListEqual(
            sorted(self.expected_feature_gates), sorted(self.summarized_features.keys())
        )
        summaries = list(self.summarized_features.values())
        self.assertTrue(all(summary is not None for summary in summaries))
