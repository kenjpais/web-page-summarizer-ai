import unittest
from chains.chains import classify_chain


class TestClassifyChain(unittest.TestCase):
    def test_summary_chain_valid(self):
        classified = classify_chain.invoke({"correlated_info": []})
        self.assertTrue(isinstance(classified, str))
        self.assertGreater(len(classified), 0)
