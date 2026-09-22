from __future__ import annotations

import argparse
import json
from pathlib import Path

from .assurance import envelope
from .core import load_pack, reference_observations, score_run, validate_pack


def default_pack() -> Path:
    return Path(__file__).resolve().parents[2] / "scenarios" / "core.json"


def main() -> int:
    parser = argparse.ArgumentParser(prog="identity-fabric-bench")
    parser.add_argument("command", choices=("validate", "run"))
    parser.add_argument("--pack", type=Path, default=default_pack())
    parser.add_argument("--output", type=Path)
    parser.add_argument("--assurance-output", type=Path, help="write the shared assurance-result.v1 envelope")
    args = parser.parse_args()
    pack = load_pack(args.pack)
    errors = validate_pack(pack)
    if errors:
        print(json.dumps({"valid": False, "errors": errors}, indent=2))
        return 1
    if args.command == "validate":
        print(json.dumps({"valid": True, "scenarios": len(pack["scenarios"])}, indent=2))
        return 0
    result = score_run(pack, reference_observations(pack))
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    if args.assurance_output:
        args.assurance_output.parent.mkdir(parents=True, exist_ok=True)
        args.assurance_output.write_text(json.dumps(envelope(pack, result), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output, end="")
    return 0 if result["qualified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
