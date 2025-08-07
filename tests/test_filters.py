import unittest
import pandas as pd
from scrapers.html_scraper import HtmlScraper
from filters.filter_enabled_feature_gates import filter_enabled_feature_gates
from scrapers.scrapers import Scraper
from config.settings import get_settings
from utils.file_utils import delete_all_in_directory, copy_file
from utils.logging_config import setup_logging, get_logger

logger = get_logger(__name__)

# Set up logging for tests
setup_logging()

settings = get_settings()
data_dir = settings.directories.data_dir

url = "https://amd64.origin.releases.ci.openshift.org/releasestream/4-scos-stable/release/4.19.0-okd-scos.0"
scraper = HtmlScraper(url, settings)

table_file = data_dir / "feature_gate_table.pkl"
test_data_dir = settings.directories.test_data_dir


class TestFilters(unittest.TestCase):
    def setUp(self):
        # Ensure data directory exists and is clean
        settings.directories.data_dir.mkdir(parents=True, exist_ok=True)
        delete_all_in_directory(data_dir)

    def tearDown(self):
        # Clean up after each test
        delete_all_in_directory(data_dir)

    def test_df_filter_enabled_feature_gates_local(self):
        """Test filtering enabled feature gates from local HTML file"""
        # Use local mock HTML file
        local_url = str(test_data_dir / "release_page.html")
        local_scraper = HtmlScraper(local_url, settings)

        # Extract data from local file
        local_scraper.extract()

        # Read and filter the data
        dfs = pd.read_pickle(table_file)
        self.assertIsInstance(dfs, list, "Expected a list of DataFrames")
        self.assertGreater(len(dfs), 0, "Expected at least one DataFrame")

        # Verify DataFrame structure of first DataFrame
        self.assertIsInstance(dfs[0], pd.DataFrame, "Expected a pandas DataFrame")
        self.assertIn("FeatureGate", dfs[0].columns)
        self.assertIn("DefaultHypershift", dfs[0].columns)
        self.assertIn("DefaultSelfManagedHA", dfs[0].columns)

        result = filter_enabled_feature_gates(dfs)

        # Expected feature gates from our mock HTML
        expected = [
            "CSIDriverSharedResource",
            "VSphereControlPlaneMachineSet",
            "VSphereStaticIPs",
            "GatewayAPI",
        ]
        self.assertListEqual(sorted(expected), sorted(result))

    def test_df_filter_enabled_feature_gates_remote(self):
        """Test filtering enabled feature gates from remote URL"""
        # Use remote URL
        remote_url = "https://amd64.origin.releases.ci.openshift.org/releasestream/4-scos-stable/release/4.19.0-okd-scos.0"
        remote_scraper = HtmlScraper(remote_url, settings)

        try:
            # Extract data from remote URL
            remote_scraper.extract()

            # Read and filter the data
            dfs = pd.read_pickle(table_file)
            self.assertIsInstance(dfs, list, "Expected a list of DataFrames")
            self.assertGreater(len(dfs), 0, "Expected at least one DataFrame")

            # Verify DataFrame structure
            self.assertIsInstance(dfs[0], pd.DataFrame, "Expected a pandas DataFrame")
            self.assertIn("FeatureGate", dfs[0].columns)
            # Remote table has spaces in column names
            self.assertTrue(
                any("Hypershift" in col for col in dfs[0].columns),
                "Expected a column containing 'Hypershift'",
            )
            self.assertTrue(
                any("SelfManagedHA" in col for col in dfs[0].columns),
                "Expected a column containing 'SelfManagedHA'",
            )

            result = filter_enabled_feature_gates(dfs)

            # Expected feature gates that should be enabled in 4.19.0
            expected_gates = [
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

            # Verify that expected feature gates are present
            for gate in expected_gates:
                self.assertIn(
                    gate, result, f"Expected feature gate {gate} not found in results"
                )

            # Log found feature gates for debugging
            logger.info(
                f"Remote test found {len(result)} feature gates: {', '.join(result)}"
            )

        except Exception as e:
            logger.warning(f"Remote test encountered an issue: {str(e)}")
            raise  # Re-raise the exception to fail the test

    def test_filter_urls_basic_functionality(self):
        """Test that filter_urls correctly filters URLs based on source_server_map"""
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

        # Run the actual filter_urls function (now part of Scraper class)
        # Pass valid URL to satisfy validation, but we only need the filtering functionality
        scraper = Scraper({"url": "https://example.com", "filter_on": True}, settings)
        scraper.filter_urls_by_source()

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

        scraper = Scraper({"url": "https://example.com", "filter_on": True}, settings)
        scraper.filter_urls_by_source()
        # Both GitHub and JIRA files should exist (based on current sources)
        source_server_map = settings.api.source_server_map
        if "GITHUB" in source_server_map:
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
        if "JIRA" in source_server_map:
            self.assertTrue(jira_urls_file.exists())
            with open(jira_urls_file, "r") as f:
                jira_urls = f.read().strip().split("\n")
                # Should contain JIRA URLs only
                self.assertIn("https://issues.redhat.com/browse/JIRA-789", jira_urls)

    def test_source_server_map_functionality(self):
        """Test that source_server_map returns the expected mapping"""
        source_server_map = settings.api.source_server_map

        # Verify the function returns a dictionary
        self.assertIsInstance(source_server_map, dict)

        # Verify expected sources are present (based on current configuration)
        expected_sources = settings.api.sources
        for source in expected_sources:
            self.assertIn(source, source_server_map)
            # Verify each source maps to a non-empty string
            self.assertIsInstance(source_server_map[source], str)
            self.assertGreater(len(source_server_map[source]), 0)

        # Verify that the URLs look like actual server URLs
        for source, url in source_server_map.items():
            self.assertTrue(
                url.startswith("http"),
                f"Source {source} URL {url} should start with http",
            )
