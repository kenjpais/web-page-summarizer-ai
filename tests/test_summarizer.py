import unittest
import asyncio
from utils.utils import get_env
from utils.parser_utils import parse_html
from utils.utils import extract_valid_urls
from summarizers.summarizer import summarize
from summarizers.summarizer import summarize
from runner import filter_srcs, filter_urls, correlate_all, build_prompt_payload


class TestSummarizer(unittest.TestCase):

    def test_valid(self):
        source = get_env("SOURCE_PAGE")

        extract_valid_urls(parse_html(source))
        filter_urls()
        asyncio.run(filter_srcs())
        asyncio.run(correlate_all())
        build_prompt_payload()
        summarize()


if __name__ == "__main__":
    unittest.main()
