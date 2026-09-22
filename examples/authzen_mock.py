"""Synthetic AuthZEN policy decision point for local demonstration only."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/access/v1/evaluation":
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 65536:
                raise ValueError("invalid request length")
            payload = json.loads(self.rfile.read(size))
            allowed = (
                payload["subject"]["id"] == "synthetic-reader"
                and payload["action"]["name"] == "can_read"
                and payload["resource"]["id"] == "public-synthetic"
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            self.send_error(400)
            return
        body = json.dumps({"decision": allowed}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        if self.headers.get("X-Request-ID"):
            self.send_header("X-Request-ID", self.headers["X-Request-ID"])
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    with ThreadingHTTPServer(("127.0.0.1", args.port), Handler) as server:
        print(f"synthetic AuthZEN mock listening on 127.0.0.1:{args.port}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
