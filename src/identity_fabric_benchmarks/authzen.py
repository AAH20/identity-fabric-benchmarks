"""Bounded AuthZEN 1.0 Access Evaluation runner for synthetic fixtures."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from urllib import error, parse, request

from .core import score_run


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def validate_endpoint(endpoint: str, allow_remote: bool = False) -> str:
    parsed = parse.urlsplit(endpoint)
    loopback = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("endpoint cannot include userinfo, query, or fragment")
    if parsed.path != "/access/v1/evaluation":
        raise ValueError("endpoint must end at /access/v1/evaluation")
    if loopback and parsed.scheme in {"http", "https"}:
        return "local-mock"
    if parsed.scheme == "https" and parsed.hostname and allow_remote:
        return "provider-endpoint"
    raise ValueError(
        "use a loopback endpoint, or explicitly allow an HTTPS remote endpoint"
    )


def validate_fixtures(pack: dict) -> list[str]:
    errors: list[str] = []
    fixtures = pack.get("fixtures")
    if not pack.get("pack_id") or not pack.get("version"):
        errors.append("pack_id and version are required")
    if not isinstance(fixtures, list) or not fixtures:
        return errors + ["fixtures must be a non-empty array"]
    seen: set[str] = set()
    for index, fixture in enumerate(fixtures):
        label = f"fixtures[{index}]"
        identifier = fixture.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in seen:
            errors.append(f"{label}.id must be unique and non-empty")
        seen.add(identifier)
        if type(fixture.get("expected_decision")) is not bool:
            errors.append(f"{label}.expected_decision must be boolean")
        payload = fixture.get("request")
        if not isinstance(payload, dict):
            errors.append(f"{label}.request must be an object")
            continue
        for field, required in (
            ("subject", ("type", "id")),
            ("action", ("name",)),
            ("resource", ("type", "id")),
        ):
            value = payload.get(field)
            if not isinstance(value, dict) or any(
                not isinstance(value.get(key), str) or not value[key]
                for key in required
            ):
                errors.append(f"{label}.request.{field} is invalid")
        if "context" in payload and not isinstance(payload["context"], dict):
            errors.append(f"{label}.request.context must be an object")
    return errors


def run_authzen(
    pack: dict,
    endpoint: str,
    *,
    allow_remote: bool = False,
    token: str | None = None,
    timeout: float = 3.0,
) -> dict:
    errors = validate_fixtures(pack)
    if errors:
        raise ValueError("; ".join(errors))
    environment = validate_endpoint(endpoint, allow_remote)
    if timeout <= 0 or timeout > 30:
        raise ValueError("timeout must be within (0, 30] seconds")
    opener = request.build_opener(request.ProxyHandler({}), _NoRedirect())
    actual: dict[str, str] = {}
    transport_evidence: dict[str, dict] = {}
    for fixture in pack["fixtures"]:
        identifier = fixture["id"]
        request_id = str(uuid.uuid4())
        payload = fixture["request"]
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Request-ID": request_id,
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request_bytes = json.dumps(
            payload, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        call = request.Request(
            endpoint, data=request_bytes, headers=headers, method="POST"
        )
        started = time.perf_counter()
        status = None
        response_hash = None
        request_id_match = False
        failure = None
        try:
            with opener.open(call, timeout=timeout) as response:
                status = response.status
                body = response.read(65537)
                response_hash = hashlib.sha256(body).hexdigest()
                if len(body) > 65536:
                    raise ValueError("response exceeds 64 KiB")
                reply = json.loads(body)
                request_id_match = response.headers.get("X-Request-ID") == request_id
                if status != 200:
                    raise ValueError("response status is not 200")
                if response.headers.get_content_type() != "application/json":
                    raise ValueError("response Content-Type is not application/json")
                if type(reply) is not dict or type(reply.get("decision")) is not bool:
                    raise ValueError("response lacks a Boolean decision")
                if not request_id_match:
                    raise ValueError("response X-Request-ID does not match request")
                actual[identifier] = "allow" if reply["decision"] else "deny"
        except error.HTTPError as exc:
            status = exc.code
            failure = "http-error"
        except (error.URLError, TimeoutError, OSError):
            failure = "transport-error"
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            failure = "invalid-response"
        transport_evidence[identifier] = {
            "request_sha256": hashlib.sha256(request_bytes).hexdigest(),
            "response_sha256": response_hash,
            "http_status": status,
            "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            "request_id_match": request_id_match,
            "failure": failure,
        }
    normalized = {
        "pack_id": pack["pack_id"],
        "version": pack["version"],
        "scenarios": [
            {
                "id": fixture["id"],
                "family": fixture.get("family", "authorization"),
                "mandatory": True,
                "expected": "allow" if fixture["expected_decision"] else "deny",
                "evidence": [
                    "request-sha256",
                    "response-sha256",
                    "http-status",
                    "request-id-match",
                ],
            }
            for fixture in pack["fixtures"]
        ],
    }
    result = score_run(
        normalized,
        actual,
        adapter="authzen",
        run_kind="simulation" if environment == "local-mock" else "provider-observed",
    )
    result["environment"] = environment
    result["limitations"] = [
        "Decisions are observed through AuthZEN; configured policy and enforcement are not independently verified.",
        "Fixtures use synthetic identities and resources; this is not a certification.",
    ]
    for observation in result["observations"]:
        observation["transport"] = transport_evidence[observation["scenario_id"]]
    return result
