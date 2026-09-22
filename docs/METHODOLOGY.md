# Benchmark methodology

## Result states

- **Planned:** adapter or scenario is documented but not executable.
- **Experimental:** executable with known coverage or reproducibility gaps.
- **Verified:** maintainers reproduced the result from the published bundle.
- **Disputed:** a material challenge is under review.
- **Withdrawn:** evidence is no longer reproducible or the tested version is unavailable.

## Security gates

A mandatory scenario is a non-compensating gate. Any false allow, cross-tenant access, delegation amplification, replay acceptance, approval bypass, fail-open partition, or ungoverned physical action makes the submission unqualified. The project publishes the failed scenario rather than averaging it away.

## Operational scoring

Qualified systems may be scored across assurance, resilience, performance, interoperability, and evidence quality. Each metric must define units, sample size, percentiles, warmup, hardware, software version, network conditions, retry policy and confidence interval. The current reference runner uses a placeholder score of 100 only to test the result contract; it is not a provider benchmark.

## Evidence bundle

A publishable bundle contains:

1. Scenario-pack ID, version and digest.
2. Adapter source revision and configuration digest.
3. Product and dependency versions.
4. Synthetic dataset and seed identifiers.
5. Normalized request, decision and timing observations.
6. Artifact digests and signature metadata.
7. Environment and hardware manifest.
8. Exceptions, missing evidence and reviewer identity.

Secrets, personal data, biometric templates, live surveillance data and exploitable customer configuration are prohibited.

## Fairness and corrections

Results identify the tested version and configuration, never an entire vendor indefinitely. A named provider receives a documented response window. Corrections preserve history through superseding records rather than silent replacement.

## Future A2ZSOC views

The signed result format may later feed `a2zsoc.com/benchmarks`, `/providers`, and `/certification`. Website work is outside the current repository scope.
