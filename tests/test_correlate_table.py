import json
import unittest
from pathlib import Path
from scrapers.scrapers import scrape_all
from filters.filter_urls import filter_urls
from scrapers.html_scraper import scrape_html
from correlators.correlator import correlate_all, correlate_table
from utils.file_utils import delete_all_in_directory
from config.settings import get_settings
from utils.logging_config import get_logger, setup_logging

setup_logging()

logger = get_logger(__name__)

settings = get_settings()
data_dir = Path(settings.directories.data_dir)


class TestCorrelateTable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
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

        url = (
            "https://amd64.origin.releases.ci.openshift.org/releasestream/"
            "4-scos-stable/release/4.19.0-okd-scos.0"
        )

        def run_pipeline():
            delete_all_in_directory(cls.data_dir)
            scrape_html(url)
            filter_urls()
            scrape_all()
            correlate_all()

        run_pipeline()
        correlate_table()

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
            issues = self.correlated_table.get(feature_gate, [])
            for issue in issues:
                values = json.dumps(issue).lower()
                self.assertIn(
                    feature_gate.lower(),
                    values,
                    msg=f"{feature_gate} not found in issue values: {values}",
                )
