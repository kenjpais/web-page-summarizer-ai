import json
import unittest
from utils.utils import get_env
from scrapers.jira_scraper import JiraScraper
from scrapers.exceptions import ScraperException


class TestJiraScraper(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jf = JiraScraper()

    def test_extract_urls_invalid(self):
        urls = [
            "https://example.com/this/is/invalid",
            "https://example.com/invalid/this/is",
        ]
        with self.assertRaises(ScraperException) as cm:
            self.jf.extract(urls)
        self.assertIn("[!] Invalid JIRA URLs", str(cm.exception))

    def test_extract_urls_valid(self):
        data_dir = get_env(f"DATA_DIR")
        urls = [
            "https://issues.redhat.com/browse/ODC-7710",
            "https://issues.redhat.com/browse/ART-13079",
            "https://issues.redhat.com/browse/CONSOLE-3905",
            "https://issues.redhat.com/browse/NETOBSERV-2023",
            "https://issues.redhat.com/browse/STOR-2251",
            "https://issues.redhat.com/browse/OCPBUILD-174",
            "https://issues.redhat.com/browse/IR-522",
            "https://issues.redhat.com/browse/ETCD-726",
        ]

        test_result = {
            "OpenShift Storage": {
                "STOR-2241": {
                    "summary": "",
                    "description": "",
                    "stories": {
                        "STOR-2251": {
                            "summary": "Chore: update CSI sidecars",
                            "description": "Update all CSI sidecars to the latest upstream release from [https://github.com/orgs/kubernetes-csi/repositories]\r\n * external-attacher\r\n * external-provisioner\r\n * external-resizer\r\n * external-snapshotter\r\n * node-driver-registrar\r\n * livenessprobe\r\n\r\nCorresponding downstream repos have `csi-` prefix, e.g. [github.com/openshift/csi-external-attacher|https://github.com/openshift/csi-external-attacher].\r\n\r\n*This includes update of VolumeSnapshot CRDs* in [cluster-csi-snapshot-controller-|https://github.com/openshift/cluster-csi-snapshot-controller-operator/tree/master/assets] [operator assets|https://github.com/openshift/cluster-csi-snapshot-controller-operator/tree/master/assets] and client API in\u00a0 [go.mod|https://github.com/openshift/csi-external-snapshotter/blob/e260f00bc18ad3a4d3b511e526a7ca14ce20ee65/go.mod#L14]. I.e. copy all [snapshot CRDs from upstream|https://github.com/kubernetes-csi/external-snapshotter/tree/v6.0.1/client/config/crd] to the operator assets + {{go get -u github.com/kubernetes-csi/external-snapshotter/client/v6}} in the operator repo.",
                            "related": [],
                        }
                    },
                }
            },
            "OpenShift Dev Console": {
                "ODC-7716": {
                    "summary": "",
                    "description": "",
                    "stories": {
                        "ODC-7710": {
                            "summary": "Remove RHOAS plugin from the console",
                            "description": "h3. Description\r\n\r\nAs a developer, I do not want to maintain the code for a project already dead.\r\nh3. Acceptance Criteria\r\n # Remove RHOAS plugin [https://github.com/openshift/console/tree/master/frontend/packages/rhoas-plugin]\r\n # Remove RHOAS-catalog-source [https://github.com/openshift/console/blob/master/frontend/packages/dev-console/integration-tests/testData/yamls/operator-installtion/RHOAS-catalog-source.yaml]\r\n # Check if there is dependencies in other package and fix it\r\n\r\nh3. Additional Details:",
                            "related": [
                                {
                                    "key": "CONSOLE-4325",
                                    "type": "Epic",
                                    "summary": "Adopt PatternFly 6 and remove PatternFly 4",
                                    "description": "",
                                }
                            ],
                        }
                    },
                }
            },
            "Network Observability": {
                "NETOBSERV-1940": {
                    "summary": "",
                    "description": "",
                    "stories": {
                        "NETOBSERV-2023": {
                            "summary": "Implement a quickstart for netobserv operator",
                            "description": "OCP Console provides quickstarts as CRD to add items under the help menu\r\n\r\n[https://docs.openshift.com/container-platform/4.17/web_console/creating-quick-start-tutorials.html#description-quick-start-element_creating-quick-start-tutorials]\u00a0\r\n\r\n[https://github.com/openshift/api/blob/de9de05a8e436e9bd3f85148251b926951bbcb0c/console/v1/types_console_quick_start.go#L12]\r\n\r\n\u00a0\r\n\r\nThose quickstarts can be linked to the getting started card on the dashboard overview page\r\n\r\n[https://docs.openshift.com/container-platform/4.17/web_console/creating-quick-start-tutorials.html#linking-to-other-quick-starts_creating-quick-start-tutorials]\r\n\r\n\u00a0\r\n\r\nThe quickstart should contain\r\n - the steps to install and configure netobserv\r\n\r\n - an overview of the resources usage and the capabilities\r\n\r\n[https://operatorhub.io/operator/netobserv-operator]\u00a0\r\n\r\n[https://github.com/netobserv/network-observability-operator/blob/c86c4a8204292367b0893371bb5af88803e08cac/config/descriptions/upstream.md?plain=1]\u00a0\r\n\r\n\u00a0",
                            "related": [
                                {
                                    "key": "NETOBSERV-1929",
                                    "type": "Story",
                                    "summary": "Display resources recommendations in operator installation page",
                                    "description": "",
                                },
                                {
                                    "key": "NETOBSERV-2296",
                                    "type": "Story",
                                    "summary": "Backport quickstart for netobserv operator for older supported OCP versions",
                                    "description": "",
                                },
                            ],
                        }
                    },
                }
            },
            "OpenShift Image Registry": {
                "IR-513": {
                    "summary": "",
                    "description": "",
                    "stories": {
                        "IR-522": {
                            "summary": "Allow registry to run in new regions without code changes",
                            "description": "We want to allow the image registry to run in new AWS regions without requiring a manual intervention in the code every time a new region pops up.\r\n\r\nAs we can see [here|https://github.com/openshift/docker-distribution/blob/release-4.18/registry/storage/driver/s3-aws/s3.go#L45-L54] every time a new region is added we need to manually add it to the list of known regions as well. This is required because the upstream project uses an AWS client that isn't receiving these new regions automatically.\r\n\r\n\u00a0\r\n\r\n\u00a0",
                            "related": [
                                {
                                    "key": "IR-526",
                                    "type": "Story",
                                    "summary": "[4.18] Allow registry to run in new regions without code changes",
                                    "description": "",
                                }
                            ],
                        }
                    },
                }
            },
            "OpenShift Etcd": {
                "ETCD-725": {
                    "summary": "",
                    "description": "",
                    "stories": {
                        "ETCD-726": {
                            "summary": "Rebase openshift/etcd 4.19 to upstream etcd 3.5.21",
                            "description": "Rebase openshift/etcd release-4.19 to upstream etcd 3.5.21",
                            "related": [
                                {
                                    "key": "ETCD-720",
                                    "type": "Story",
                                    "summary": "Rebase openshift/etcd 4.19 to upstream etcd 3.5.20",
                                    "description": "",
                                },
                                {
                                    "key": "ETCD-740",
                                    "type": "Story",
                                    "summary": "Rebase openshift/etcd 4.20 to upstream etcd v3.6.0",
                                    "description": "",
                                },
                            ],
                        }
                    },
                }
            },
            "OpenShift Console": {
                "CONSOLE-4350": {
                    "summary": "",
                    "description": "",
                    "stories": {
                        "CONSOLE-3905": {
                            "summary": "Update Webpack package to version 5",
                            "description": "As a developer I want to make sure we are running the latest version of webpack in order to take advantage of the latest benefits and also keep current so that future updating is a painless as possible.\r\n\r\nWe are currently on v4.47.0.\r\n\r\nChangelog: [https://webpack.js.org/blog/2020-10-10-webpack-5-release/]\r\n\r\nBy updating to version 5 we will need to update following pkgs as well:\r\n * html-webpack-plugin\r\n * webpack-bundle-analyzer\r\n * copy-webpack-plugin\r\n * fork-ts-checker-webpack-plugin\r\n\r\nAC: Update webpack to version 5 and determine what should be the ideal minor version.",
                            "related": [
                                {
                                    "key": "CONSOLE-4226",
                                    "type": "Story",
                                    "summary": "Prepare migration to webpack v5",
                                    "description": "",
                                },
                                {
                                    "key": "CONSOLE-2971",
                                    "type": "Story",
                                    "summary": "Update Console's Webpack version to 5+",
                                    "description": "",
                                },
                            ],
                        }
                    },
                }
            },
        }

        result = self.jf.extract(urls)
        with open(f"{data_dir}/jira.json") as f:
            result = json.load(f)

        self.assertGreater(len(result), 0)
        self.assertDictEqual(test_result, result)


if __name__ == "__main__":
    unittest.main()
