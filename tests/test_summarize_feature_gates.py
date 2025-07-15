import json
import unittest
from pathlib import Path
from summarizers.summarizer import summarize_feature_gates
from config.settings import get_settings

settings = get_settings()
data_dir = Path(settings.directories.data_dir)


class TestSummarizeFeatureGates(unittest.TestCase):
    def test_summarize_feature_gates(self):
        with open(data_dir / "correlated_feature_gate_table.json", "r") as f:
            feature_gate_info = json.load(f)
        result = summarize_feature_gates(feature_gate_info)
        print(f"KDEBUGTEST: {result}")
