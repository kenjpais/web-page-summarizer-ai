import os
import unittest
from pathlib import Path
from scrapers.scrapers import scrape_all
from filters.filter_urls import filter_urls
from scrapers.html_scraper import scrape_html
from correlators.correlator import correlate_all
from summarizers.summarizer import summarize
from utils.file_utils import delete_all_in_directory
from config.settings import get_settings
from runner import run
from utils.logging_config import get_logger, setup_logging

setup_logging()

logger = get_logger(__name__)

settings = get_settings()
data_dir = Path(settings.directories.data_dir)


class TestSummarizer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure FILTER_ON is True for this test (restore original .env value)
        # This is needed because other tests may have modified os.environ["FILTER_ON"]
        os.environ["FILTER_ON"] = "True"
        get_settings.cache_clear()

        cls.url = (
            "https://amd64.origin.releases.ci.openshift.org/releasestream/"
            "4-scos-stable/release/4.19.0-okd-scos.0"
        )
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
            delete_all_in_directory(cls.data_dir)
            scrape_html(cls.url)
            filter_urls()
            scrape_all()
            correlate_all()
            summarize()

        run_pipeline()

    def test_summarize_enabled(self):
        os.environ["SUMMARIZE_ENABLED"] = "False"
        get_settings.cache_clear()

        def run_pipeline():
            # delete_all_in_directory(self.data_dir)
            scrape_html(self.url)
            filter_urls()
            scrape_all()
            correlate_all()
            summarize()

        run_pipeline()

        self.assertFalse(os.path.exists(self.summarized_features_file))
        self.assertFalse(os.path.exists(self.data_dir / "summaries"))
