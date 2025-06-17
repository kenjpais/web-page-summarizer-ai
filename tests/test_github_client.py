import unittest
from clients.github_client import GithubGraphQLClient


class TestGithubGraphQLClientIntegration(unittest.TestCase):
    def setUp(self):
        self.client = GithubGraphQLClient()
    
    def test_params(self):
        self.assertIsNotNone(self.client.api_url)
        self.assertIsNotNone(self.client.token)


    def test_build_graphql_query_pr_and_commit(self):
        parsed_items = [
            {"type": "pr", "owner": "octocat", "repo": "Hello-World", "id": "1347"},
            {
                "type": "commit",
                "owner": "octocat",
                "repo": "Hello-World",
                "id": "e5bd3914e2e596debea16f433f57875b5b90bcd6",
            },
        ]
        query = self.client.build_graphql_query(parsed_items)

        self.assertIn("pullRequest(number: 1347)", query)
        self.assertIn(
            'object(expression: "e5bd3914e2e596debea16f433f57875b5b90bcd6")', query
        )

    def test_post_query_pr(self):
        parsed_items = [
            {"type": "pr", "owner": "octocat", "repo": "Hello-World", "id": "1"}
        ]
        query = self.client.build_graphql_query(parsed_items)
        response = self.client.post_query(query)

        pr = response.get("data", {}).get("item0", {}).get("pullRequest")
        self.assertIsNotNone(pr, "PR data should not be None")
        self.assertEqual(pr.get("number"), 1)

    def test_post_query_commit(self):
        parsed_items = [
            {
                "type": "commit",
                "owner": "openshift",
                "repo": "azure-service-operator",
                "id": "0ae129b4768d2e10e0ca215d272e207bfae963a3",
            }
        ]
        query = self.client.build_graphql_query(parsed_items)
        response = self.client.post_query(query)
        self.assertIsNotNone(response, "response should not be None")
        commit = response.get("data", {}).get("item0", {}).get("object")
        self.assertIsNotNone(commit, "Commit data should not be None")
        self.assertIn("oid", commit)
        self.assertIn("message", commit)


if __name__ == "__main__":
    unittest.main()
