import json
import unittest
from utils.utils import get_env
from utils.parser_utils import is_valid_markdown
from runner import run


class TestSummarizer(unittest.TestCase):
    def test_valid_summary(self):
        source = get_env("SOURCE_PAGE")
        data_dir = get_env("DATA_DIR")
        correlated_file = f"{data_dir}/correlated.json"
        correlated_data = {}
        run(source)

        with open(correlated_file, "r") as corfile:
            correlated_data = json.dump(corfile)

        summary = ""
        with open("summary.txt", "r") as f:
            summary = f.read()

        projects = list(correlated_data.keys())
        self.assertTrue(all([proj in summary for proj in projects]))
        self.assertTrue(is_valid_markdown(summary))


if __name__ == "__main__":
    unittest.main()
