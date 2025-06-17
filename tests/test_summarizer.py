import unittest
from utils.utils import get_env
from runner import run


class TestSummarizer(unittest.TestCase):

    def test_valid(self):
        source = get_env("SOURCE_PAGE")
        run(source)


if __name__ == "__main__":
    unittest.main()
