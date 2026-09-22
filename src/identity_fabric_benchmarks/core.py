from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_OUTCOMES = {"allow", "deny", "require-approval", "complete"}


def load_pack(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_pack(pack: dict) -> list[str]:
    errors: list[str] = []
    scenarios = pack.get("scenarios")
    if not pack.get("pack_id") or not pack.get("version"):
        errors.append("pack_id and version are required")
    if not isinstance(scenarios, list) or not scenarios:
        return errors + ["scenarios must be a non-empty array"]
    ids = [scenario.get("id") for scenario in scenarios]
    duplicate_ids = sorted(key for key, count in Counter(ids).items() if count > 1)
    if duplicate_ids:
        errors.append(f"duplicate scenario ids: {', '.join(duplicate_ids)}")
    for index, scenario in enumerate(scenarios):
        prefix = f"scenarios[{index}]"
        for key in ("id", "family", "mandatory", "expected", "evidence"):
            if key not in scenario:
                errors.append(f"{prefix}.{key} is required")
        if scenario.get("expected") not in EXPECTED_OUTCOMES:
            errors.append(f"{prefix}.expected is invalid")
        evidence = scenario.get("evidence")
        if (
            not isinstance(evidence, list)
            or not evidence
            or len(evidence) != len(set(evidence))
        ):
            errors.append(f"{prefix}.evidence must be a non-empty unique array")
    return errors


def score_run(
    pack: dict,
    actual: dict[str, str],
    adapter: str = "reference",
    run_kind: str = "synthetic-reference",
) -> dict:
    if run_kind not in {"synthetic-reference", "simulation", "provider-observed"}:
        raise ValueError("invalid run_kind")
    observations = []
    gates: dict[str, bool] = {}
    for scenario in pack["scenarios"]:
        observed = actual.get(scenario["id"], "missing")
        passed = observed == scenario["expected"]
        if scenario["mandatory"]:
            gates[scenario["id"]] = passed
        observations.append(
            {
                "scenario_id": scenario["id"],
                "family": scenario["family"],
                "expected": scenario["expected"],
                "observed": observed,
                "passed": passed,
                "evidence_requirements": scenario["evidence"],
            }
        )
    qualified = bool(gates) and all(gates.values())
    return {
        "result_version": "0.2.0",
        "pack_id": pack["pack_id"],
        "pack_version": pack["version"],
        "adapter": adapter,
        "run_kind": run_kind,
        "qualified": qualified,
        "security_gates": gates,
        "score": None,
        "score_basis": "not-scored",
        "observations": observations,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def reference_observations(pack: dict) -> dict[str, str]:
    return {scenario["id"]: scenario["expected"] for scenario in pack["scenarios"]}
