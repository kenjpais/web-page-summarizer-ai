import json
import unittest
from utils.utils import get_env
from utils.parser_utils import is_valid_markdown
from runner import run


class TestSummarizer(unittest.TestCase):
    def test_valid_summary(self):
        source = get_env("SOURCE_PAGE")
        data_dir = get_env("DATA_DIR")
        run(source)
        summary = ""
        with open(f"{data_dir}/summary.txt", "r") as f:
            summary = f.read()

        self.assertTrue(is_valid_markdown(summary))


if __name__ == "__main__":
    unittest.main()
