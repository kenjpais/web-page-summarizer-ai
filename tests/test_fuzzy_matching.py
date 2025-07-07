import unittest
from filters.jira_fuzzy_matching import (
    clean_feature_name,
    clean_jira_summary,
    calculate_match_score,
    fuzzy_match_features_to_jira,
    get_best_match_per_feature,
    find_jira_matches_for_features,
)


class TestFuzzyMatching(unittest.TestCase):

    def setUp(self):
        """Set up test data."""
        self.feature_names = [
            "enable-new-dashboard",
            "user_authentication_v2",
            "payment-processing-enhancement",
            "mobile_app_notifications",
            "enable-feature-x(deprecated)",
        ]

        self.jira_issues = [
            {
                "key": "PROJ-123",
                "summary": "Implement new dashboard feature for users",
                "description": "Add new dashboard with enhanced UI",
            },
            {
                "key": "PROJ-124",
                "summary": "User authentication system version 2",
                "description": "Update authentication to support OAuth2",
            },
            {
                "key": "PROJ-125",
                "summary": "Payment processing improvements",
                "description": "Enhance payment gateway integration",
            },
            {
                "key": "PROJ-126",
                "summary": "Mobile notifications for iOS app",
                "description": "Add push notifications for mobile",
            },
            {
                "key": "PROJ-127",
                "summary": "Bug fix for login page",
                "description": "Fix CSS issue on login page",
            },
        ]

    def test_clean_feature_name(self):
        """Test feature name cleaning."""
        # Test removing parentheses
        self.assertEqual(
            clean_feature_name("enable-feature-x(deprecated)"), "feature x"
        )

        # Test removing prefixes
        self.assertEqual(clean_feature_name("enable-new-dashboard"), "new dashboard")

        # Test replacing underscores and dashes
        self.assertEqual(
            clean_feature_name("user_authentication_v2"), "user authentication v2"
        )

        # Test removing enable/disable prefixes
        self.assertEqual(clean_feature_name("disable-old-feature"), "old feature")

    def test_clean_jira_summary(self):
        """Test JIRA summary cleaning."""
        # Test removing common prefixes
        self.assertEqual(
            clean_jira_summary("Feature: New dashboard implementation"),
            "New dashboard implementation",
        )

        # Test removing ticket numbers
        self.assertEqual(
            clean_jira_summary("PROJ-123: User authentication"), "User authentication"
        )

        # Test removing brackets
        self.assertEqual(
            clean_jira_summary("Payment processing [URGENT]"), "Payment processing"
        )

    def test_calculate_match_score(self):
        """Test match score calculation."""
        # Test exact match
        score = calculate_match_score("new dashboard", "new dashboard feature")
        self.assertGreater(score, 80)

        # Test partial match
        score = calculate_match_score(
            "user authentication", "User authentication system version 2"
        )
        self.assertGreater(score, 70)

        # Test no match
        score = calculate_match_score("payment processing", "mobile notifications")
        self.assertLess(score, 30)

    def test_fuzzy_match_features_to_jira(self):
        """Test fuzzy matching functionality."""
        matches = fuzzy_match_features_to_jira(
            self.feature_names,
            self.jira_issues,
            threshold=60.0,
            max_matches_per_feature=2,
        )

        # Should find matches for most features
        self.assertGreater(len(matches), 0)

        # Check that matches have required fields
        for match in matches:
            self.assertIn("feature_name", match)
            self.assertIn("jira_key", match)
            self.assertIn("jira_summary", match)
            self.assertIn("score", match)
            self.assertGreaterEqual(match["score"], 60.0)

    def test_get_best_match_per_feature(self):
        """Test getting best match per feature."""
        best_matches = get_best_match_per_feature(
            self.feature_names, self.jira_issues, threshold=60.0
        )

        # Should return dictionary with feature names as keys
        self.assertIsInstance(best_matches, dict)

        # Check that each match has required fields
        for feature_name, match in best_matches.items():
            self.assertIn(feature_name, self.feature_names)
            self.assertIn("jira_key", match)
            self.assertIn("jira_summary", match)
            self.assertIn("score", match)
            self.assertGreaterEqual(match["score"], 60.0)

    def test_specific_matches(self):
        """Test specific expected matches."""
        # Test that "enable-new-dashboard" matches with dashboard issue
        score = calculate_match_score(
            "enable-new-dashboard", "Implement new dashboard feature for users"
        )
        self.assertGreater(score, 70, "Dashboard feature should match with high score")

        # Test that "user_authentication_v2" matches with auth issue
        score = calculate_match_score(
            "user_authentication_v2", "User authentication system version 2"
        )
        self.assertGreater(
            score, 80, "Authentication feature should match with high score"
        )

        # Test that "payment-processing-enhancement" matches with payment issue
        score = calculate_match_score(
            "payment-processing-enhancement", "Payment processing improvements"
        )
        self.assertGreater(score, 70, "Payment processing should match with high score")

    def test_find_jira_matches_for_features(self):
        """Test find_jira_matches_for_features function."""
        matches, unmatched = find_jira_matches_for_features(
            self.feature_names, self.jira_issues, threshold=60.0
        )

        # Should return tuple of (matches, unmatched_features)
        self.assertIsInstance(matches, list)
        self.assertIsInstance(unmatched, list)

        # Check that matches have required fields
        for match in matches:
            self.assertIn("feature_name", match)
            self.assertIn("jira_key", match)
            self.assertIn("jira_summary", match)
            self.assertIn("score", match)
            self.assertGreaterEqual(match["score"], 60.0)

        # Check that unmatched features are strings
        for feature in unmatched:
            self.assertIsInstance(feature, str)
            self.assertIn(feature, self.feature_names)

    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Test with empty feature names
        matches = fuzzy_match_features_to_jira([], self.jira_issues)
        self.assertEqual(len(matches), 0)

        # Test with empty JIRA issues
        matches = fuzzy_match_features_to_jira(self.feature_names, [])
        self.assertEqual(len(matches), 0)

        # Test with very high threshold (should return no matches)
        matches = fuzzy_match_features_to_jira(
            self.feature_names, self.jira_issues, threshold=99.0
        )
        self.assertEqual(len(matches), 0)

        # Test with very low threshold (should return many matches)
        matches = fuzzy_match_features_to_jira(
            self.feature_names, self.jira_issues, threshold=1.0
        )
        self.assertGreater(len(matches), 0)

    def test_special_characters_and_formatting(self):
        """Test handling of special characters and formatting."""
        special_features = [
            "enable-feature@v2.0",
            "user.authentication#new",
            "payment_processing$enhanced",
            "mobile-app!notifications",
            "feature   with   spaces",
        ]

        special_jira_issues = [
            {
                "key": "PROJ-200",
                "summary": "Feature @v2.0 implementation",
                "description": "Special characters test",
            },
            {
                "key": "PROJ-201",
                "summary": "User.authentication#new system",
                "description": "Authentication with special chars",
            },
            {
                "key": "PROJ-202",
                "summary": "Payment processing $ enhanced version",
                "description": "Enhanced payment processing",
            },
        ]

        matches = fuzzy_match_features_to_jira(
            special_features, special_jira_issues, threshold=50.0
        )

        # Should handle special characters gracefully
        self.assertGreaterEqual(len(matches), 0)

        # Check that matches contain valid data
        for match in matches:
            self.assertIsInstance(match["feature_name"], str)
            self.assertIsInstance(match["jira_key"], str)
            self.assertIsInstance(match["jira_summary"], str)
            self.assertIsInstance(match["score"], float)

    def test_case_sensitivity(self):
        """Test case sensitivity in matching."""
        case_test_features = [
            "NEW-DASHBOARD",
            "user-authentication",
            "Payment-Processing",
        ]

        case_test_jira = [
            {
                "key": "PROJ-300",
                "summary": "new dashboard implementation",
                "description": "Dashboard feature",
            },
            {
                "key": "PROJ-301",
                "summary": "USER AUTHENTICATION SYSTEM",
                "description": "Auth system",
            },
            {
                "key": "PROJ-302",
                "summary": "payment processing Enhancement",
                "description": "Payment feature",
            },
        ]

        matches = fuzzy_match_features_to_jira(
            case_test_features, case_test_jira, threshold=70.0
        )

        # Should match regardless of case
        self.assertGreater(len(matches), 0)

        # Verify specific case insensitive matches
        feature_to_jira = {
            match["feature_name"]: match["jira_key"] for match in matches
        }
        self.assertIn("NEW-DASHBOARD", feature_to_jira)
        self.assertIn("user-authentication", feature_to_jira)
        self.assertIn("Payment-Processing", feature_to_jira)

    def test_real_world_scenarios(self):
        """Test with real-world OpenShift feature gate scenarios."""
        openshift_features = [
            "GatewayAPI",
            "OpenShiftPodSecurityAdmission",
            "RouteExternalCertificate",
            "VSphereControlPlaneMachineSet",
            "MetricsCollectionProfiles",
            "ConsolePluginContentSecurityPolicy",
        ]

        openshift_jira = [
            {
                "key": "NETOBSERV-1234",
                "summary": "Implement Gateway API support for network observability",
                "description": "Add Gateway API integration",
            },
            {
                "key": "CONSOLE-5678",
                "summary": "Pod Security Admission for OpenShift Console",
                "description": "Enable pod security admission policies",
            },
            {
                "key": "ROUTING-9012",
                "summary": "Route External Certificate management",
                "description": "Support for external certificates in routes",
            },
            {
                "key": "VSPHERE-3456",
                "summary": "vSphere Control Plane Machine Set implementation",
                "description": "Machine set for vSphere control plane",
            },
            {
                "key": "METRICS-7890",
                "summary": "Metrics Collection Profiles for monitoring",
                "description": "Collection profiles for system metrics",
            },
        ]

        matches = fuzzy_match_features_to_jira(
            openshift_features, openshift_jira, threshold=60.0
        )

        # Should find matches for most OpenShift features
        self.assertGreater(len(matches), 3)

        # Check for expected matches
        matched_features = [match["feature_name"] for match in matches]
        self.assertIn("GatewayAPI", matched_features)
        self.assertIn("OpenShiftPodSecurityAdmission", matched_features)
        self.assertIn("RouteExternalCertificate", matched_features)

    def test_max_matches_per_feature(self):
        """Test max_matches_per_feature parameter."""
        # Create multiple similar JIRA issues
        similar_jira_issues = [
            {
                "key": "PROJ-400",
                "summary": "User authentication system v1",
                "description": "First version of auth system",
            },
            {
                "key": "PROJ-401",
                "summary": "User authentication system v2",
                "description": "Second version of auth system",
            },
            {
                "key": "PROJ-402",
                "summary": "User authentication system v3",
                "description": "Third version of auth system",
            },
            {
                "key": "PROJ-403",
                "summary": "User authentication implementation",
                "description": "Implementation of auth system",
            },
        ]

        # Test with max_matches_per_feature = 2
        matches = fuzzy_match_features_to_jira(
            ["user-authentication"],
            similar_jira_issues,
            threshold=50.0,
            max_matches_per_feature=2,
        )

        # Should return at most 2 matches for the feature
        auth_matches = [
            m for m in matches if m["feature_name"] == "user-authentication"
        ]
        self.assertLessEqual(len(auth_matches), 2)

        # Should return highest scoring matches
        if len(auth_matches) > 1:
            scores = [match["score"] for match in auth_matches]
            self.assertEqual(scores, sorted(scores, reverse=True))

    def test_cleaning_functions_comprehensive(self):
        """Test cleaning functions with comprehensive cases."""
        # Test feature name cleaning edge cases
        test_cases = [
            ("", ""),
            ("   ", ""),
            ("enable-feature-gate-test", "feature gate test"),
            ("disable_old_feature_gate", "old feature gate"),
            ("FEATURE-NAME-WITH-CAPS", "NAME WITH CAPS"),
            ("feature___with___underscores", "feature with underscores"),
            ("feature---with---dashes", "feature with dashes"),
            ("feature(with)(multiple)(parentheses)", "feature"),
            ("gate-feature-enable", "feature"),
            ("test-feature-disable", "test feature"),
        ]

        for input_str, expected in test_cases:
            result = clean_feature_name(input_str)
            self.assertEqual(result, expected, f"Failed for input: '{input_str}'")

        # Test JIRA summary cleaning edge cases
        jira_test_cases = [
            ("", ""),
            ("   ", ""),
            ("Story: Feature implementation", "Feature implementation"),
            ("TASK-123: Bug fix for login", "Bug fix for login"),
            ("Epic: New dashboard [PRIORITY-HIGH]", "New dashboard"),
            ("Feature: Payment processing [URGENT] [REVIEW]", "Payment processing"),
            ("BUG-456: Login issue", "Login issue"),
            ("   STORY:   Spaced   summary   ", "Spaced summary"),
        ]

        for input_str, expected in jira_test_cases:
            result = clean_jira_summary(input_str)
            self.assertEqual(result, expected, f"Failed for input: '{input_str}'")

    def test_score_calculation_edge_cases(self):
        """Test match score calculation edge cases."""
        # Test with empty strings
        score = calculate_match_score("", "")
        self.assertEqual(score, 0.0)

        # Test with one empty string
        score = calculate_match_score("feature", "")
        self.assertEqual(score, 0.0)

        score = calculate_match_score("", "summary")
        self.assertEqual(score, 0.0)

        # Test with single characters
        score = calculate_match_score("a", "b")
        self.assertEqual(score, 0.0)

        # Test with identical strings
        score = calculate_match_score("identical", "identical")
        self.assertEqual(score, 100.0)

        # Test substring matching boost
        score = calculate_match_score("auth", "authentication system")
        boosted_score = calculate_match_score("auth", "this contains auth somewhere")
        self.assertGreater(boosted_score, score)

    def test_missing_jira_fields(self):
        """Test handling of missing JIRA fields."""
        incomplete_jira_issues = [
            {
                "key": "PROJ-500",
                "summary": "Complete issue with all fields",
                "description": "Full description",
            },
            {
                "key": "PROJ-501",
                "summary": "Issue missing description",
                # Missing description field
            },
            {
                "key": "PROJ-502",
                "description": "Issue missing summary",
                # Missing summary field
            },
            {
                "summary": "Issue missing key",
                "description": "No key field",
                # Missing key field
            },
        ]

        matches = fuzzy_match_features_to_jira(
            ["complete-issue", "missing-fields"], incomplete_jira_issues, threshold=30.0
        )

        # Should handle missing fields gracefully
        for match in matches:
            self.assertIsInstance(match["jira_key"], str)
            self.assertIsInstance(match["jira_summary"], str)
            self.assertIsInstance(match["score"], float)


if __name__ == "__main__":
    unittest.main()
