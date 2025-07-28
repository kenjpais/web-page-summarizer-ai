import os
import json
import unittest
from summarizers.summarizer import summarize
from config.settings import get_settings
from utils.logging_config import get_logger, setup_logging
from utils.file_utils import delete_all_in_directory

setup_logging()

logger = get_logger(__name__)

settings = get_settings()
test_data_dir = settings.directories.test_data_dir


class TestSummarizer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["FILTER_ON"] = "True"
        get_settings.cache_clear()
        cls.data_dir = test_data_dir
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

        # Clean up test directory before starting
        delete_all_in_directory(cls.data_dir)
        setup_test_data()

    def setUp(self):
        # Clean up before each test
        delete_all_in_directory(self.data_dir)
        setup_test_data()

    def test_summarize_enabled(self):
        os.environ["SUMMARIZE_ENABLED"] = "False"
        get_settings.cache_clear()

        summarize()

        self.assertFalse(os.path.exists(self.summarized_features_file))
        self.assertFalse(os.path.exists(self.data_dir / "summaries"))


def setup_test_data():
    test_data = {"test": "data"}
    with open(test_data_dir / "correlated.json", "w") as f:
        json.dump(test_data, f)
