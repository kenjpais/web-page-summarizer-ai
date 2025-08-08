import os
import json
import unittest

from unittest.mock import patch
from summarizers.summarizer import Summarizer
from config.settings import get_settings
from utils.logging_config import get_logger, setup_logging
from utils.file_utils import delete_all_in_directory, copy_file
from tests.mocks.mock_llm import create_mock_llm

setup_logging()

logger = get_logger(__name__)

settings = get_settings()

data_dir = settings.directories.data_dir
test_data_dir = settings.directories.test_data_dir
mock_correlated_file = test_data_dir / "correlated.json"
dummy_correlated_file = data_dir / "correlated.json"


class TestSummarizer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):

        get_settings.cache_clear()
        cls.data_dir = data_dir
        cls.url = "https://amd64.origin.releases.ci.openshift.org/releasestream/4-scos-stable/release/4.19.0-okd-scos.0"
        cls.release_name = cls.url.strip().split("/release/")[1]
        cls.summarized_features_file = cls.data_dir / "summarized_features.json"
        cls.summary_dir = data_dir / "summaries" / cls.release_name
        cls.summary_file_path = cls.summary_dir / "summary.txt"
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

    def test_summarize_disabled(self):
        settings.processing.summarize_enabled = False
        summarizer = Summarizer(settings)
        summarizer.summarize()

        self.assertFalse(os.path.exists(self.data_dir / "summaries"))

    @patch("clients.local_llm_chain.create_local_llm", side_effect=create_mock_llm)
    def test_summarize_enabled(self, mock_create_llm):
        settings.processing.summarize_enabled = True
        settings.api.llm_provider = "local"
        get_settings.cache_clear()
        setup_dummy_test_data()
        summarizer = Summarizer(settings)
        summarizer.summarize()

        # Check that summary.txt was created in data directory
        summary_file_path = self.data_dir / "summary.txt"
        self.assertTrue(
            os.path.exists(summary_file_path), "summary.txt was not created"
        )

    @patch("clients.local_llm_chain.create_local_llm", side_effect=create_mock_llm)
    def test_summarize(self, mock_create_llm):
        # Set LLM provider to local for testing
        settings.api.llm_provider = "local"
        delete_all_in_directory(data_dir)

        # Mock data
        copy_file(src_path=mock_correlated_file, dest_dir=data_dir)

        summarizer = Summarizer(settings)
        summarizer.summarize()

        # Check that summary.txt was created in data directory
        summary_file_path = self.data_dir / "summary.txt"
        self.assertTrue(
            os.path.exists(summary_file_path), "summary.txt was not created"
        )

        with open(summary_file_path, "r") as f:
            summary_content = f.read()

        self.assertGreater(len(summary_content.strip()), 10, "summary.txt is empty")


def setup_dummy_test_data():
    test_data = {"test": "data"}
    with open(dummy_correlated_file, "w") as f:
        json.dump(test_data, f)
