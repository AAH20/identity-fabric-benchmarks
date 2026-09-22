# Contributing

New scenarios must define the threat, preconditions, expected control outcome, mandatory status, evidence requirements, and deterministic pass condition. A benchmark change that affects scoring requires a scenario-pack version change and migration note.

Public provider results require an immutable environment manifest, adapter version, raw normalized observations, artifact digests, and disclosure of limitations. Product claims without executable evidence belong in adapter documentation, not the result ledger.

Run:

```bash
python -m unittest discover -s tests -v
python -m identity_fabric_benchmarks.cli validate
```
