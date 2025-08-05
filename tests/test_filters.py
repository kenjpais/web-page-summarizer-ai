import unittest
import pandas as pd
from scrapers.html_scraper import HtmlScraper
from filters.filter_enabled_feature_gates import filter_enabled_feature_gates
from filters.filter_urls import filter_urls
from config.settings import get_settings
from utils.file_utils import delete_all_in_directory, copy_file
from utils.logging_config import setup_logging

# Set up logging for tests
setup_logging()

settings = get_settings()
data_dir = settings.directories.data_dir

url = "https://amd64.origin.releases.ci.openshift.org/releasestream/4-scos-stable/release/4.19.0-okd-scos.0"
scraper = HtmlScraper(url)

table_file = data_dir / "feature_gate_table.pkl"
test_data_dir = settings.directories.test_data_dir


class TestFilters(unittest.TestCase):
    def test_df_filter_enabled_feature_gates(self):
        scraper.scrape()
        df = pd.read_pickle(table_file)
        if isinstance(df, pd.Series):
            df = df.to_frame()

        result = filter_enabled_feature_gates(df)
        expected = [
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
        ]
        self.assertListEqual(expected, result)

    def test_filter_urls_basic_functionality(self):
        """Test that filter_urls correctly filters URLs based on sources_dict"""
        urls_file = data_dir / "urls.txt"
        github_urls_file = data_dir / "github_urls.txt"
        jira_urls_file = data_dir / "jira_urls.txt"

        delete_all_in_directory(data_dir)

        # Create test URLs
        test_urls = [
            "https://github.com/openshift/some-repo/pull/123",
            "https://issues.redhat.com/browse/JIRA-456",
            "https://example.com/irrelevant-url",
            "https://github.com/another/repo/commit/abc123",
            "https://issues.redhat.com/browse/OCPBUGS-789",
        ]

        # Write test URLs to file
        with open(urls_file, "w") as f:
            for url in test_urls:
                f.write(url + "\n")

        # Run the actual filter_urls function
        filter_urls()

        # Verify output files were created
        self.assertTrue(github_urls_file.exists())
        self.assertTrue(jira_urls_file.exists())

        # Verify content of GitHub URLs file
        with open(github_urls_file, "r") as f:
            github_urls = f.read().strip().split("\n")
        expected_github_urls = [
            "https://github.com/openshift/some-repo/pull/123",
            "https://github.com/another/repo/commit/abc123",
        ]
        self.assertEqual(github_urls, expected_github_urls)

        # Verify content of JIRA URLs file
        with open(jira_urls_file, "r") as f:
            jira_urls = f.read().strip().split("\n")
        expected_jira_urls = [
            "https://issues.redhat.com/browse/JIRA-456",
            "https://issues.redhat.com/browse/OCPBUGS-789",
        ]
        self.assertEqual(jira_urls, expected_jira_urls)

    def test_filter_urls_with_mixed_urls(self):
        """Test filter_urls with mixed URLs including some that don't match"""
        urls_file = data_dir / "urls.txt"

        github_urls_file = data_dir / "github_urls.txt"
        jira_urls_file = data_dir / "jira_urls.txt"

        test_urls = [
            "https://github.com/openshift/repo1/pull/123",
            "https://github.com/openshift/repo2/pull/456",
            "https://issues.redhat.com/browse/JIRA-789",
            "https://example.com/irrelevant",
            "https://bitbucket.org/some/repo",  # Should not match
        ]
        with open(urls_file, "w") as f:
            for url in test_urls:
                f.write(url + "\n")

        filter_urls()
        # Both GitHub and JIRA files should exist (based on current sources)
        sources_dict = settings.processing.get_sources_dict()
        if "GITHUB" in sources_dict:
            self.assertTrue(github_urls_file.exists())
            with open(github_urls_file, "r") as f:
                github_urls = f.read().strip().split("\n")
                # Should contain GitHub URLs only
                self.assertIn(
                    "https://github.com/openshift/repo1/pull/123", github_urls
                )
                self.assertIn(
                    "https://github.com/openshift/repo2/pull/456", github_urls
                )
        if "JIRA" in sources_dict:
            self.assertTrue(jira_urls_file.exists())
            with open(jira_urls_file, "r") as f:
                jira_urls = f.read().strip().split("\n")
                # Should contain JIRA URLs only
                self.assertIn("https://issues.redhat.com/browse/JIRA-789", jira_urls)

    def test_sources_dict_functionality(self):
        """Test that get_sources_dict returns the expected mapping"""
        sources_dict = settings.processing.get_sources_dict()

        # Verify the function returns a dictionary
        self.assertIsInstance(sources_dict, dict)

        # Verify expected sources are present (based on current configuration)
        expected_sources = settings.processing.sources
        for source in expected_sources:
            self.assertIn(source, sources_dict)
            # Verify each source maps to a non-empty string
            self.assertIsInstance(sources_dict[source], str)
            self.assertGreater(len(sources_dict[source]), 0)

        # Verify that the URLs look like actual server URLs
        for source, url in sources_dict.items():
            self.assertTrue(
                url.startswith("http"),
                f"Source {source} URL {url} should start with http",
            )
