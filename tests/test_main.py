import unittest
from unittest.mock import patch, MagicMock
from main import CLI
from config.settings import get_settings
from utils.file_utils import delete_all_in_directory, copy_file


class TestMain(unittest.TestCase):
    def test_main_runs_cli(self):
        """Test that main creates and runs the CLI."""
        # Set up test data
        settings = get_settings()
        test_data_dir = settings.directories.test_data_dir
        data_dir = settings.directories.data_dir

        # Clean data directory
        delete_all_in_directory(data_dir)

        # Copy required test data
        copy_file(src_path=test_data_dir / "feature_gate_table.pkl", dest_dir=data_dir)
        copy_file(src_path=test_data_dir / "correlated.json", dest_dir=data_dir)

        with patch("main.CLI") as mock_cli_class:
            mock_cli = MagicMock()
            mock_cli_class.return_value = mock_cli

            cli = mock_cli_class()
            cli.run(["scrape", "--url", "https://example.com"])

            mock_cli.run.assert_called_once_with(
                ["scrape", "--url", "https://example.com"]
            )
