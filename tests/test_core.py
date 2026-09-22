import json
import unittest
from pathlib import Path

from identity_fabric_benchmarks.core import load_pack, reference_observations, score_run, validate_pack


ROOT = Path(__file__).resolve().parents[1]


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.pack = load_pack(ROOT / "scenarios" / "core.json")

    def test_core_pack_is_valid(self):
        self.assertEqual([], validate_pack(self.pack))

    def test_reference_adapter_qualifies(self):
        result = score_run(self.pack, reference_observations(self.pack))
        self.assertTrue(result["qualified"])
        self.assertEqual(100.0, result["score"])

    def test_one_security_failure_disqualifies(self):
        observations = reference_observations(self.pack)
        observations["IFB-TENANT-001"] = "allow"
        result = score_run(self.pack, observations)
        self.assertFalse(result["qualified"])
        self.assertIsNone(result["score"])

    def test_missing_observation_fails_closed(self):
        result = score_run(self.pack, {})
        self.assertFalse(result["qualified"])
        self.assertTrue(all(not gate for gate in result["security_gates"].values()))

    def test_assets_parse(self):
        for directory in ("scenarios", "adapters", "schemas"):
            for path in (ROOT / directory).glob("*.json"):
                json.loads(path.read_text())


if __name__ == "__main__":
    unittest.main()
