import json
import unittest
from pathlib import Path

from identity_fabric_benchmarks.core import load_pack, reference_observations, score_run, validate_pack
from identity_fabric_benchmarks.assurance import digest, envelope


ROOT = Path(__file__).resolve().parents[1]


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.pack = load_pack(ROOT / "scenarios" / "core.json")

    def test_core_pack_is_valid(self):
        self.assertEqual([], validate_pack(self.pack))

    def test_reference_adapter_qualifies(self):
        result = score_run(self.pack, reference_observations(self.pack))
        self.assertTrue(result["qualified"])
        self.assertIsNone(result["score"])
        self.assertEqual("not-scored", result["score_basis"])
        self.assertEqual("synthetic-reference", result["run_kind"])

    def test_one_security_failure_disqualifies(self):
        observations = reference_observations(self.pack)
        observations["IFB-TENANT-001"] = "allow"
        result = score_run(self.pack, observations)
        self.assertFalse(result["qualified"])
        self.assertIsNone(result["score"])

    def test_assurance_envelope_binds_pack_and_result(self):
        result = score_run(self.pack, reference_observations(self.pack))
        item = envelope(self.pack, result)
        self.assertEqual("bpa.assurance-result.v1", item["schema_version"])
        self.assertEqual(digest(result), item["evidence"]["artifact_sha256"])
        self.assertEqual(digest(self.pack), item["subject"]["pack_sha256"])
        self.assertEqual("none", item["evidence"]["verification"])
        self.assertIsNone(item["qualification"]["score"])

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
