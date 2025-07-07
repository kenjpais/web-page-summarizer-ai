import os
import json
import pandas as pd
import unittest
from utils.utils import get_env
from scrapers.jira_scraper import JiraScraper
from scrapers.html_scraper import HtmlScraper
from scrapers.exceptions import ScraperException
from filters.filter_enabled_feature_gates import filter_enabled_feature_gates


url = "https://amd64.origin.releases.ci.openshift.org/releasestream/4-scos-stable/release/4.19.0-okd-scos.0"


class TestJiraScraper(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jf = JiraScraper()
        data_dir = get_env("DATA_DIR")
        for filename in ["jira.json", "jira.md"]:
            filepath = os.path.join(data_dir, filename)
            if os.path.exists(filepath):
                os.remove(filepath)

    def test_extract_urls_invalid(self):
        urls = [
            "https://example.com/this/is/invalid",
            "https://example.com/invalid/this/is",
        ]
        with self.assertRaises(ScraperException) as cm:
            self.jf.extract(urls)
        self.assertIn("[!] Invalid JIRA URLs", str(cm.exception))

    def test_extract_urls_valid(self):
        data_dir = get_env("DATA_DIR")
        urls = [
            "https://issues.redhat.com/browse/ODC-7710",
            "https://issues.redhat.com/browse/ART-13079",
            "https://issues.redhat.com/browse/CONSOLE-3905",
            "https://issues.redhat.com/browse/NETOBSERV-2023",
            "https://issues.redhat.com/browse/STOR-2251",
            "https://issues.redhat.com/browse/OCPBUILD-174",
            "https://issues.redhat.com/browse/IR-522",
            "https://issues.redhat.com/browse/ETCD-726",
            "https://issues.redhat.com/browse/NE-2017",
        ]
        issue_ids = [
            "STOR-2251",
            "ODC-7710",
            "NETOBSERV-2023",
            "IR-522",
            "ETCD-726",
            "CONSOLE-3905",
        ]

        self.jf.extract(urls)

        with open(f"{data_dir}/jira.json") as f:
            result = json.load(f)

        with open(f"{data_dir}/jira.md") as f:
            result_md = f.read()

        self.assertGreater(len(result), 0)

        for _, project_dict in result.items():
            self.assertTrue(
                "epics" in project_dict
                or "stories" in project_dict
                or "features" in project_dict
            )
        for issue_id in issue_ids:
            self.assertIn(issue_id, json.dumps(result))
            self.assertIn(issue_id, result_md)

    def test_filter_enabled_feature_gates(self):
        HtmlScraper(url).scrape_table_info()
        df = pd.read_pickle(f"{get_env('DATA_DIR')}/feature_gate_table.pkl")
        feature_gates = filter_enabled_feature_gates(df)
        expected_feature_gates = [
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
        self.assertEqual(expected_feature_gates, feature_gates)


if __name__ == "__main__":
    unittest.main()
