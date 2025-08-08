import os
import json
import unittest

os.environ["LLM_PROVIDER"] = "local"
os.environ["LLM_MODEL"] = "mistral"

from correlators.correlator import Correlator
from utils.file_utils import copy_file, delete_all_in_directory
from config.settings import get_settings
from utils.logging_config import get_logger, setup_logging

setup_logging()

logger = get_logger(__name__)

# Clear settings cache to pick up new environment variables
get_settings.cache_clear()
settings = get_settings()

data_dir = settings.directories.data_dir
test_data_dir = settings.directories.test_data_dir
correlated_file = test_data_dir / "correlated.json"
table_file = test_data_dir / "feature_gate_table.pkl"
github_file = test_data_dir / "github.json"


class TestCorrelateTable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure FILTER_ON is True for this test (restore original .env value)
        # This is needed because other tests may have modified os.environ["FILTER_ON"]
        os.environ["FILTER_ON"] = "True"
        get_settings.cache_clear()

        cls.correlated_table_file = data_dir / "correlated_feature_gate_table.json"
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
        copy_file(src_path=table_file, dest_dir=data_dir)
        copy_file(src_path=github_file, dest_dir=data_dir)

        # Use Correlator class method instead of standalone function
        correlator = Correlator(settings)
        correlator.correlate_table()

        with open(cls.correlated_table_file, "r") as f:
            cls.correlated_table = json.load(f)

    def test_feature_gate_keys_match(self):
        actual_keys = set(sorted(list(self.correlated_table.keys())))
        self.assertSetEqual(
            actual_keys,
            self.expected_feature_gates,
            msg="Mismatch in expected feature gate keys",
        )

    def test_feature_gate_presence_in_issues(self):
        for feature_gate in self.expected_feature_gates:
            feature = self.correlated_table.get(feature_gate, {})
            details = []
            if isinstance(feature, dict):
                details = feature.get("details", [])
            else:
                details = feature
            for dtl in details:
                values = json.dumps(dtl).lower()
                self.assertIn(
                    feature_gate.lower(),
                    values,
                    msg=f"{feature_gate} not found in detail values: {values}",
                )
