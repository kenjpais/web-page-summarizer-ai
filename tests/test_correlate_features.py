import os
import json
import unittest
import pickle
from pathlib import Path

from correlators.correlator import Correlator
from config.settings import get_settings
from utils.file_utils import copy_file, delete_all_in_directory


class TestCorrelateFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Clear settings cache
        get_settings.cache_clear()
        settings = get_settings()

        # Setup test directories and files
        cls.data_dir = settings.directories.data_dir
        cls.test_data_dir = settings.directories.test_data_dir

        # Clean data directory
        delete_all_in_directory(cls.data_dir)

        # Copy mock data files
        copy_file(
            src_path=cls.test_data_dir / "correlated_feature_gate_table.json",
            dest_dir=cls.data_dir,
        )
        copy_file(src_path=cls.test_data_dir / "correlated.json", dest_dir=cls.data_dir)

        # Create a sample feature gate project map
        cls.feature_gate_project_map = {
            "GatewayAPI": "Network Edge",
            "GatewayAPIController": "Network Edge",
            "VSphereStaticIPs": "vSphere Platform",
            "VSphereControlPlaneMachineSet": "vSphere Platform",
            "CPMSMachineNamePrefix": "Control Plane",
            "OnClusterBuild": "Machine Config",
            "ConsolePluginContentSecurityPolicy": "Console",
            "RouteExternalCertificate": "Ingress",
            "CSIDriverSharedResource": "Storage",
            "AdditionalRoutingCapabilities": "Network",
            "OpenShiftPodSecurityAdmission": "Security",
            "ServiceAccountTokenNodeBinding": "Auth",
            "MetricsCollectionProfiles": "Monitoring",
        }

        with open(cls.data_dir / "feature_gate_project_map.pkl", "wb") as f:
            pickle.dump(cls.feature_gate_project_map, f)

        # Create correlator instance
        cls.correlator = Correlator(settings)

    def test_correlate_features_with_real_data(self):
        """Test correlation using real mock data"""
        # Run the correlation
        self.correlator.correlate_features()

        # Read the output file
        with open(self.data_dir / "correlated.json", "r") as f:
            result = json.load(f)

        # Test Network Edge project features
        self.assertIn("Network Edge", result)
        self.assertIn("enabledFeatures", result["Network Edge"])
        network_features = result["Network Edge"]["enabledFeatures"]

        # Verify GatewayAPI features were added
        self.assertIn("GatewayAPI", network_features)
        self.assertIn("GatewayAPIController", network_features)

        # Verify feature content matches mock data
        gateway_api_data = network_features["GatewayAPI"]
        self.assertIsInstance(gateway_api_data, list)
        self.assertTrue(
            any(
                item.get("summary")
                == "Enable GatewayAPI feature gate in Default feature set"
                for item in gateway_api_data
            )
        )

        # Test vSphere Platform project features
        self.assertIn("vSphere Platform", result)
        self.assertIn("enabledFeatures", result["vSphere Platform"])
        vsphere_features = result["vSphere Platform"]["enabledFeatures"]

        # Verify vSphere features were added
        self.assertIn("VSphereStaticIPs", vsphere_features)
        self.assertIn("VSphereControlPlaneMachineSet", vsphere_features)

        # Verify feature content matches mock data
        vsphere_static_ips_data = vsphere_features["VSphereStaticIPs"]
        self.assertIsInstance(vsphere_static_ips_data, list)
        self.assertTrue(
            any(
                item.get("summary") == "vSphere Static IP GA+1 Cleanup"
                for item in vsphere_static_ips_data
            )
        )

    def test_correlate_features_preserves_existing_data(self):
        """Test that correlation preserves existing data in the correlated file"""
        # Read initial correlated data
        with open(self.data_dir / "correlated.json", "r") as f:
            initial_data = json.load(f)

        # Add some test data that should be preserved
        initial_data["Test Project"] = {
            "metadata": {"key": "value"},
            "enabledFeatures": {"ExistingFeature": "Should be preserved"},
        }

        with open(self.data_dir / "correlated.json", "w") as f:
            json.dump(initial_data, f)

        # Run correlation
        self.correlator.correlate_features()

        # Read result
        with open(self.data_dir / "correlated.json", "r") as f:
            result = json.load(f)

        # Verify test data was preserved
        self.assertIn("Test Project", result)
        self.assertEqual(result["Test Project"]["metadata"], {"key": "value"})
        self.assertEqual(
            result["Test Project"]["enabledFeatures"]["ExistingFeature"],
            "Should be preserved",
        )

    def test_correlate_features_handles_empty_project_mapping(self):
        """Test handling of features with empty project mappings"""
        # Add a feature with empty project mapping
        feature_gate_project_map = self.feature_gate_project_map.copy()
        feature_gate_project_map["UnmappedFeature"] = ""

        with open(self.data_dir / "feature_gate_project_map.pkl", "wb") as f:
            pickle.dump(feature_gate_project_map, f)

        # Add the feature to the table
        with open(self.data_dir / "correlated_feature_gate_table.json", "r") as f:
            feature_table = json.load(f)
        feature_table["UnmappedFeature"] = [{"summary": "Test summary"}]
        with open(self.data_dir / "correlated_feature_gate_table.json", "w") as f:
            json.dump(feature_table, f)

        # Run correlation
        self.correlator.correlate_features()

        # Read result
        with open(self.data_dir / "correlated.json", "r") as f:
            result = json.load(f)

        # Verify unmapped feature wasn't added anywhere
        for project_data in result.values():
            if "enabledFeatures" in project_data:
                self.assertNotIn(
                    "UnmappedFeature",
                    project_data["enabledFeatures"],
                    "Unmapped feature should not be added to any project",
                )
