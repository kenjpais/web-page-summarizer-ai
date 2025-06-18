import os
import json
import unittest
from correlators.correlator import correlate_with_jira_issue_id
from filters.filter_required_fields import remove_irrelevant_fields_from_correlated
from utils.utils import get_env


class TestCorrelateWithJiraIssueId(unittest.TestCase):
    def test_correlate_with_jira_issue_id(self):
        data_dir = get_env("DATA_DIR")
        config_dir = get_env("CONFIG_DIR")
        os.makedirs(data_dir, exist_ok=True)

        jira_file = f"{data_dir}/JIRA.json"
        github_file = f"{data_dir}/GITHUB.json"
        correlated_file = f"{data_dir}/correlated.json"
        required_github_fields_file = f"{config_dir}/required_github_fields.json"

        # Set required fields
        with open(required_github_fields_file, "w") as f:
            json.dump(["title", "body"], f)

        issue_ids = [
            "AGENT-997",
            "OTA-1539",
            "CNTRLPLANE-936",
            "METAL-1376",
            "OU-842",
            "MCO-1652",
            "TRT-1854",
        ]

        relevant_correlated_data = [
            {
                "JIRA": {},
                "GITHUB": [
                    {
                        "title": "AGENT-997: Internal dev docs for authentication-authorization"
                    }
                ],
            },
            {
                "JIRA": {},
                "GITHUB": [
                    {
                        "title": "OTA-1539: pkg/cli/admin/upgrade/recommend: Add a --quiet option",
                        "body": 'As part of the `--accepted-risk` feature (#2017), because listing unaccepted risk names gives us a way to say "we have more problems we think you should consider" for folks who just want a short summary before deciding whether they want more details.  I\'m keeping the chatty version as the default, because historically we have had users who don\'t want to look at the details, and instead hope that waiting will be enough for the issues to resolve.\r\n\r\nFor "there was a regression, and Red Hat will ship a fix", waiting will eventually work.  But for "your cluster is alerting, and you should look into that", waiting is unlikely to help.  And even for the regression situation, it is the user\'s responsibility to weigh the risk of updating into the known regression against the risk of remaining on an old, possibly buggy release.  [Red Hat will support either choice][1].\r\n\r\nHaving `--quiet` be an explicit choice makes it clear that Red Hat thinks the user should be engaging with and evaluating any detected issues, while allowing users to say "I don\'t have time now, sorry.  Give me the short summary".\r\n\r\n[1]: https://docs.redhat.com/en/documentation/openshift_container_platform/4.18/html/updating_clusters/understanding-openshift-updates-1#conditional-updates-overview_understanding-update-channels-releases\r\n',
                    }
                ],
            },
            {
                "JIRA": {},
                "GITHUB": [
                    {
                        "title": "CNTRLPLANE-936: fix(tekton): drop multiarch builds on PR",
                        "body": "**What this PR does / why we need it**:\r\n\r\nIn order to reduce the on-pull-request Konflux load, let's keep the multiarch builds only on the push pipelines.\r\n\r\n**Which issue(s) this PR fixes**:\r\nFixes #[CNTRLPLANE-936](https://issues.redhat.com//browse/CNTRLPLANE-936)\r\n\r\n**Checklist**\r\n- [x] Subject and description added to both, commit and PR.\r\n- [x] Relevant issues have been referenced.\r\n- [ ] This change includes docs. \r\n- [ ] This change includes unit tests.",
                    }
                ],
            },
            {
                "JIRA": {},
                "GITHUB": [{"title": "METAL-1376: Make sushy support NetworkAdapters"}],
            },
            {
                "JIRA": {},
                "GITHUB": [
                    {
                        "title": "OU-842: fix: override notistack dependency to avoid conflict",
                        "body": "Notistack v2 has a peer dependency of material ui V5, the current perses components depend on material UI 6. From notistack v3 this dependency was removed. Overwriting the dependency does not cause issues as the API is compatible.",
                    }
                ],
            },
            {
                "JIRA": {},
                "GITHUB": [
                    {
                        "title": "MCO-1652: Add MCO disruptive suite",
                        "body": "Many MCO tests require node disruption, so it was determined that these would best live as a separate suite.\r\n\r\nCreate the MCO suite and move existing MCO tests in origin to it. The next goal is to add On Cluster Layering tests to this as well, potentially via OTE.",
                    }
                ],
            },
            {
                "JIRA": {},
                "GITHUB": [
                    {
                        "title": "TRT-1854: set network for MicroShift to OVNKubernetes",
                        "body": "MicroShift has no `--network` flag set when running OTE tests which is causing it to miss a skip that it should have.\r\n\r\nThere is some [special configuration](https://github.com/openshift/release/blob/master/ci-operator/step-registry/openshift/microshift/e2e/origin-conformance/openshift-microshift-e2e-origin-conformance-commands.sh#L46-L71) that sets it to `OVNKubernetes` for tests. I confirmed that this is a safe assumption to make in [this thread](https://redhat-internal.slack.com/archives/C03DP9PABNC/p1748958779190589). If, in the future, they start testing it with other network plugins we will have to be smarter about differentiating them.",
                    }
                ],
            },
        ]
        github_dicts = [
            {
                "id": 9224,
                "title": "AGENT-997: Internal dev docs for authentication-authorization",
            },
            {
                "id": 2023,
                "title": "OTA-1539: pkg/cli/admin/upgrade/recommend: Add a --quiet option",
                "body": 'As part of the `--accepted-risk` feature (#2017), because listing unaccepted risk names gives us a way to say "we have more problems we think you should consider" for folks who just want a short summary before deciding whether they want more details.  I\'m keeping the chatty version as the default, because historically we have had users who don\'t want to look at the details, and instead hope that waiting will be enough for the issues to resolve.\r\n\r\nFor "there was a regression, and Red Hat will ship a fix", waiting will eventually work.  But for "your cluster is alerting, and you should look into that", waiting is unlikely to help.  And even for the regression situation, it is the user\'s responsibility to weigh the risk of updating into the known regression against the risk of remaining on an old, possibly buggy release.  [Red Hat will support either choice][1].\r\n\r\nHaving `--quiet` be an explicit choice makes it clear that Red Hat thinks the user should be engaging with and evaluating any detected issues, while allowing users to say "I don\'t have time now, sorry.  Give me the short summary".\r\n\r\n[1]: https://docs.redhat.com/en/documentation/openshift_container_platform/4.18/html/updating_clusters/understanding-openshift-updates-1#conditional-updates-overview_understanding-update-channels-releases\r\n',
            },
            {
                "id": 6223,
                "title": "CNTRLPLANE-936: fix(tekton): drop multiarch builds on PR",
                "body": "**What this PR does / why we need it**:\r\n\r\nIn order to reduce the on-pull-request Konflux load, let's keep the multiarch builds only on the push pipelines.\r\n\r\n**Which issue(s) this PR fixes**:\r\nFixes #[CNTRLPLANE-936](https://issues.redhat.com//browse/CNTRLPLANE-936)\r\n\r\n**Checklist**\r\n- [x] Subject and description added to both, commit and PR.\r\n- [x] Relevant issues have been referenced.\r\n- [ ] This change includes docs. \r\n- [ ] This change includes unit tests.",
            },
            {
                "id": 662,
                "title": "METAL-1376: Make sushy support NetworkAdapters",
            },
            {
                "id": 422,
                "title": "OU-842: fix: override notistack dependency to avoid conflict",
                "body": "Notistack v2 has a peer dependency of material ui V5, the current perses components depend on material UI 6. From notistack v3 this dependency was removed. Overwriting the dependency does not cause issues as the API is compatible.",
            },
            {
                "id": 29776,
                "title": "MCO-1652: Add MCO disruptive suite",
                "body": "Many MCO tests require node disruption, so it was determined that these would best live as a separate suite.\r\n\r\nCreate the MCO suite and move existing MCO tests in origin to it. The next goal is to add On Cluster Layering tests to this as well, potentially via OTE.",
            },
            {
                "id": 29887,
                "title": "TRT-1854: set network for MicroShift to OVNKubernetes",
                "body": "MicroShift has no `--network` flag set when running OTE tests which is causing it to miss a skip that it should have.\r\n\r\nThere is some [special configuration](https://github.com/openshift/release/blob/master/ci-operator/step-registry/openshift/microshift/e2e/origin-conformance/openshift-microshift-e2e-origin-conformance-commands.sh#L46-L71) that sets it to `OVNKubernetes` for tests. I confirmed that this is a safe assumption to make in [this thread](https://redhat-internal.slack.com/archives/C03DP9PABNC/p1748958779190589). If, in the future, they start testing it with other network plugins we will have to be smarter about differentiating them.",
            },
        ]

        with open(jira_file, "w") as jirafile, open(github_file, "w") as ghfile:
            for issue_id, github_dict in zip(issue_ids, github_dicts):
                jirafile.write(json.dumps({"id": issue_id}) + "\n")
                ghfile.write(json.dumps(github_dict) + "\n")

        correlate_with_jira_issue_id()

        with open(correlated_file, "r") as f:
            pre_filter_data = json.load(f)

        self.assertIsInstance(pre_filter_data, dict)
        for issue_id in issue_ids:
            self.assertIn(issue_id, pre_filter_data)
        self.assertIn("GITHUB", pre_filter_data["AGENT-997"])
        self.assertIn("JIRA", pre_filter_data["AGENT-997"])

        remove_irrelevant_fields_from_correlated()

        with open(correlated_file, "r") as f:
            post_filter_data = json.load(f)
        self.assertIsInstance(post_filter_data, list)
        self.assertEqual(relevant_correlated_data, post_filter_data)
