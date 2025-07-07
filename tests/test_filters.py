import unittest
from scrapers.html_scraper import HtmlScraper
from filters.filter_enabled_feature_gates import filter_enabled_feature_gates
from utils.utils import get_env

url = "https://amd64.origin.releases.ci.openshift.org/releasestream/4-scos-stable/release/4.19.0-okd-scos.0"
scraper = HtmlScraper(url)


class TestFilters(unittest.TestCase):
    def test_df_filter_enabled_feature_gates(self):
        df = scraper.scrape_table_info()
        result = filter_enabled_feature_gates(df)
        expected = [
            "CSIDriverSharedResource (0 tests)",
            "VSphereControlPlaneMachineSet (0 tests)",
            "VSphereStaticIPs (0 tests)",
            "GatewayAPI (6 tests)",
            "AdditionalRoutingCapabilities (0 tests)",
            "ConsolePluginContentSecurityPolicy (0 tests)",
            "MetricsCollectionProfiles (5 tests)",
            "OnClusterBuild (0 tests)",
            "OpenShiftPodSecurityAdmission (0 tests)",
            "RouteExternalCertificate (19 tests)",
            "ServiceAccountTokenNodeBinding (0 tests)",
            "CPMSMachineNamePrefix (0 tests)",
            "GatewayAPIController (5 tests)",
        ]
        self.assertListEqual(expected, result)
