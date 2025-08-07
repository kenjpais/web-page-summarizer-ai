import unittest
import argparse
from unittest.mock import patch, MagicMock

from cli.cli import CLI

# Argument parser functions
from cli.github_cli import add_github_cli, parse_github_cli_args
from cli.jira_cli import add_jira_cli, parse_jira_cli_args
from cli.default_cli import add_default_cli, parse_default_cli_args


# -------------------------------
# Unit Tests for CLI Execution
# -------------------------------


class TestCLIExecution(unittest.TestCase):

    def setUp(self):
        self.cli = CLI()

    @patch("cli.cli.Scraper")
    def test_scrape_command_calls_scraper(self, mock_scraper_class):
        mock_scraper_instance = MagicMock()
        mock_scraper_class.return_value = mock_scraper_instance

        args = ["scrape", "--url", "https://example.com"]
        self.cli.run(args)

        mock_scraper_class.assert_called_once()
        mock_scraper_instance.scrape.assert_called_once()

    @patch("cli.cli.Correlator")
    def test_correlate_command_calls_correlator(self, mock_correlator_class):
        mock_correlator_instance = MagicMock()
        mock_correlator_class.return_value = mock_correlator_instance

        args = ["correlate"]
        self.cli.run(args)

        mock_correlator_class.assert_called_once()
        mock_correlator_instance.correlate.assert_called_once()

    @patch("cli.cli.runner.run")
    def test_summarize_command_calls_runner(self, mock_run):
        args = ["summarize", "--url", "https://example.com"]
        self.cli.run(args)

        mock_run.assert_called_once()
        called_kwargs = mock_run.call_args[0][0]  # first positional arg
        self.assertEqual(called_kwargs["command"], "summarize")

    @patch("cli.cli.logger")
    def test_execute_logs_error_and_exits_on_failure(self, mock_logger):
        with patch("cli.cli.Scraper", side_effect=Exception("Boom")), self.assertRaises(
            SystemExit
        ) as cm:
            self.cli.run(["scrape", "--url", "https://example.com"])

        self.assertEqual(cm.exception.code, 1)  # exit code 1 for runtime errors
        mock_logger.error.assert_called_with("Workflow failed: Boom")
        mock_logger.debug.assert_called()


# -------------------------------
# Unit Tests for GitHub Args
# -------------------------------


class TestGitHubCLIArgs(unittest.TestCase):

    def test_parse_github_args(self):
        parser = argparse.ArgumentParser()
        add_github_cli(parser)

        args = parser.parse_args(
            [
                "--github-server",
                "gh-server",
                "--github-username",
                "user",
                "--github-password",
                "pass",
                "--github-token",
                "token123",
            ]
        )

        parsed = parse_github_cli_args(args)
        self.assertEqual(
            parsed,
            {
                "github": {
                    "github_server": "gh-server",
                    "github_username": "user",
                    "github_password": "pass",
                    "github_token": "token123",
                }
            },
        )


# -------------------------------
# Unit Tests for Jira Args
# -------------------------------


class TestJiraCLIArgs(unittest.TestCase):

    @patch("cli.jira_cli.validate_cs_input_str")
    def test_parse_jira_args(self, mock_validate):
        mock_validate.side_effect = lambda val, _: val.split(",") if val else []

        parser = argparse.ArgumentParser()
        add_jira_cli(parser)

        args = parser.parse_args(
            [
                "--jira-server",
                "jira-server",
                "--jira-username",
                "jira-user",
                "--jira-password",
                "jira-pass",
                "--issue-ids",
                "JIRA-1,JIRA-2",
                "--usernames",
                "alice,bob",
            ]
        )

        parsed = parse_jira_cli_args(args)

        self.assertEqual(
            parsed,
            {
                "jira": {
                    "issue_ids": ["JIRA-1", "JIRA-2"],
                    "usernames": ["alice", "bob"],
                    "jira_server": "jira-server",
                    "jira_username": "jira-user",
                    "jira_password": "jira-pass",
                }
            },
        )

        mock_validate.assert_any_call("JIRA-1,JIRA-2", "issue_ids")
        mock_validate.assert_any_call("alice,bob", "usernames")

    @patch("cli.jira_cli.validate_cs_input_str")
    def test_parse_jira_args_with_defaults(self, mock_validate):
        mock_validate.return_value = []

        parser = argparse.ArgumentParser()
        add_jira_cli(parser)

        args = parser.parse_args([])

        parsed = parse_jira_cli_args(args)
        self.assertEqual(
            parsed,
            {
                "jira": {
                    "issue_ids": [],
                    "usernames": [],
                    "jira_server": "",
                    "jira_username": "",
                    "jira_password": "",
                }
            },
        )


# -------------------------------
# Unit Tests for Default Args
# -------------------------------


class TestDefaultCLIArgs(unittest.TestCase):

    def test_parse_default_cli_args_enabled(self):
        parser = argparse.ArgumentParser()
        add_default_cli(parser)

        args = parser.parse_args(["--filter-on"])
        parsed = parse_default_cli_args(args)
        self.assertEqual(parsed, {"filter_on": True})

    def test_parse_default_cli_args_disabled(self):
        parser = argparse.ArgumentParser()
        add_default_cli(parser)

        args = parser.parse_args([])
        parsed = parse_default_cli_args(args)
        self.assertEqual(parsed, {})


if __name__ == "__main__":
    unittest.main()
