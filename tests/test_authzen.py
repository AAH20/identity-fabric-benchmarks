import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar

from identity_fabric_benchmarks.assurance import envelope
from identity_fabric_benchmarks.authzen import (
    run_authzen,
    validate_endpoint,
    validate_fixtures,
)
from identity_fabric_benchmarks.core import load_pack

PACK = load_pack(
    Path(__file__).resolve().parents[1] / "scenarios" / "authzen-local.json"
)


class DecisionHandler(BaseHTTPRequestHandler):
    response_mode = "normal"
    seen: ClassVar[list[tuple[bytes, bytes]]] = []

    def do_POST(self):
        if self.path != "/access/v1/evaluation":
            self.send_error(404)
            return
        request_bytes = self.rfile.read(int(self.headers["Content-Length"]))
        payload = json.loads(request_bytes)
        decision = payload["resource"]["id"] == "public-synthetic"
        body = json.dumps(
            {"decision": decision if self.response_mode != "false-allow" else True}
        ).encode()
        self.seen.append((request_bytes, body))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header(
            "X-Request-ID",
            self.headers["X-Request-ID"]
            if self.response_mode != "wrong-id"
            else "wrong",
        )
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class AuthZENTests(unittest.TestCase):
    def setUp(self):
        self.assertEqual([], validate_fixtures(PACK))
        handler = type(
            "FixtureHandler",
            (DecisionHandler,),
            {"response_mode": "normal", "seen": []},
        )
        self.handler = handler
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.endpoint = (
            f"http://127.0.0.1:{self.server.server_port}/access/v1/evaluation"
        )

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def test_observed_local_decisions_and_assurance_provenance(self):
        result = run_authzen(PACK, self.endpoint)
        self.assertTrue(result["qualified"])
        self.assertEqual("simulation", result["run_kind"])
        self.assertIsNone(result["score"])
        self.assertTrue(
            all(row["transport"]["request_id_match"] for row in result["observations"])
        )
        self.assertEqual(
            hashlib.sha256(self.handler.seen[0][0]).hexdigest(),
            result["observations"][0]["transport"]["request_sha256"],
        )
        self.assertEqual(
            hashlib.sha256(self.handler.seen[0][1]).hexdigest(),
            result["observations"][0]["transport"]["response_sha256"],
        )
        item = envelope(PACK, result)
        self.assertEqual("simulation", item["run"]["kind"])
        self.assertEqual("none", item["evidence"]["verification"])

    def test_false_allow_fails_gate(self):
        self.handler.response_mode = "false-allow"
        result = run_authzen(PACK, self.endpoint)
        self.assertFalse(result["qualified"])
        self.assertFalse(result["security_gates"]["AZ-DENY-001"])

    def test_request_id_mismatch_fails_closed(self):
        self.handler.response_mode = "wrong-id"
        result = run_authzen(PACK, self.endpoint)
        self.assertFalse(result["qualified"])
        self.assertTrue(
            all(row["observed"] == "missing" for row in result["observations"])
        )

    def test_endpoint_rules(self):
        self.assertEqual("local-mock", validate_endpoint(self.endpoint))
        with self.assertRaises(ValueError):
            validate_endpoint(
                "http://example.com/access/v1/evaluation", allow_remote=True
            )
        with self.assertRaises(ValueError):
            validate_endpoint("https://example.com/access/v1/evaluation")
        self.assertEqual(
            "provider-endpoint",
            validate_endpoint(
                "https://example.com/access/v1/evaluation", allow_remote=True
            ),
        )

    def test_cli_writes_result_and_assurance(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            assurance = Path(directory) / "assurance.json"
            env = {
                **os.environ,
                "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
            }
            command = [
                sys.executable,
                "-m",
                "identity_fabric_benchmarks.cli",
                "run-authzen",
                "--endpoint",
                self.endpoint,
                "--output",
                str(output),
                "--assurance-output",
                str(assurance),
            ]
            completed = subprocess.run(
                command, capture_output=True, text=True, env=env, check=False
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertTrue(json.loads(output.read_text())["qualified"])
            self.assertEqual(
                "simulation", json.loads(assurance.read_text())["run"]["kind"]
            )


if __name__ == "__main__":
    unittest.main()
