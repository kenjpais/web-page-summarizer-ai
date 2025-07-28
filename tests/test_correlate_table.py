import os
import json
import unittest
from pathlib import Path
from scrapers.scrapers import scrape_all
from filters.filter_urls import filter_urls
from scrapers.html_scraper import scrape_html
from correlators.correlator import (
    correlate_table,
    correlate_with_jira_issue_id,
)
from config.settings import get_settings
from utils.logging_config import get_logger, setup_logging

setup_logging()

logger = get_logger(__name__)

settings = get_settings()
data_dir = settings.directories.data_dir
test_data_dir = settings.directories.test_data_dir


class TestCorrelateTable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure FILTER_ON is True for this test (restore original .env value)
        # This is needed because other tests may have modified os.environ["FILTER_ON"]
        os.environ["FILTER_ON"] = "True"
        get_settings.cache_clear()

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

        def run_pipeline():
            correlate_with_jira_issue_id(data_directory=test_data_dir)
            correlate_table()

        run_pipeline()

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
