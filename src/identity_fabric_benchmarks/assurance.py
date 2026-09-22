"""Portable assurance envelope; digests bind the exact emitted benchmark result."""

from __future__ import annotations

import hashlib
import json


def digest(value: dict) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def envelope(pack: dict, result: dict) -> dict:
    pack_hash = digest(pack)
    artifact_hash = digest(result)
    return {
        "schema_version": "bpa.assurance-result.v1",
        "result_id": f"{pack['pack_id']}:{artifact_hash[:16]}",
        "producer": {
            "repository": "AAH20/identity-fabric-benchmarks",
            "component": result["adapter"],
            "version": result["result_version"],
        },
        "run": {
            "kind": result["run_kind"],
            "environment": result.get("environment", "local-reference"),
        },
        "subject": {
            "pack_id": pack["pack_id"],
            "pack_version": pack["version"],
            "pack_sha256": pack_hash,
        },
        "qualification": {
            "qualified": result["qualified"],
            "failed_gates": sorted(
                key for key, passed in result["security_gates"].items() if not passed
            ),
            "score": result["score"],
            "score_basis": result["score_basis"],
        },
        "evidence": {
            "artifact_sha256": artifact_hash,
            "receipt_root_sha256": None,
            "verification": "none",
        },
        "limitations": result.get(
            "limitations",
            [
                "Synthetic reference observations are not product measurements.",
                "No signed receipt chain or independent verification is provided.",
            ],
        ),
    }
