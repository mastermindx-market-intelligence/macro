# Market Memory capacity and storage qualification

The live storage census on 2026-10-15 at 17:53 UTC measured 106,870,171 logical bytes and 110,342,144 allocated bytes across the existing retained public store and private context-projection store. It read filesystem metadata only, followed no symlinks, and made no content reads or writes. The store had 113 captures; this is a later whole-store observation, distinct from the frozen 109-member population used in the accepted latency baseline.

The public retained store accounted for 5,479,661 logical bytes across 568 files. Private context-projection evidence accounted for 101,390,510 bytes across 756 files, including 3,151,382 bytes of options-context receipts. Raw source snapshots accounted for 97,520,436 bytes (91.25% of the combined logical size). Directory traversal was not atomic with the ordinary writer. These totals do not establish monthly growth, marginal capture cost, filesystem reservation, provider billing, or a retention-deletion policy.

The predeclared synthetic protocol uses 16, 64, 128 and 256 captures, five fresh-process read trials at each size, and the unchanged 257-capture refusal. The real capability APIs and file-backed capture helpers are used with the existing test policy. Synthetic source values, fixture clocks and that fake authorizer are explicit; this experiment does not measure production entitlement work, external data freshness, independent research samples or forecast usefulness. Operating-system caches remain untouched. Build time, query/disclosure time, storage and peak RSS are separate measurements. The protocol stops larger experiments on a failure or timeout rather than silently altering bounds.

The parent-verified local run completed all 20 trials, with no gaps. Every size accounted for all N captures, admitted N−1 historical representatives, returned eight cases, and produced stable membership and selection digests across its five trials. A subsequent 257th capture was refused by the exact `whole_generation_capture_bound_exceeded` guard; no retrieval was attempted. Source hashes were unchanged across the run.

| Captures | Build seconds | Read/disclosure P50 seconds | P95 seconds | Peak RSS maximum MiB | Retained artifact logical bytes |
|---:|---:|---:|---:|---:|---:|
| 16 | 0.377 | 0.111 | 0.116 | 171.188 | 620,334 |
| 64 | 2.475 | 0.432 | 0.443 | 171.719 | 3,008,972 |
| 128 | 9.280 | 1.067 | 1.182 | 178.734 | 7,437,466 |
| 256 | 23.264 | 2.036 | 2.093 | 189.016 | 20,558,394 |

P50 and P95 use nearest rank across five trials: P95 is the sample maximum, not an estimated population tail. The measured phases comprise owner-pin read, cohort read/disclosure, query-feature read, retrieval and disclosure. Process startup is separately recorded. Peak RSS includes imported engine and fixture/test dependencies. Source fixture and harness metadata bytes are counted separately from retained artifacts. The single build at each size is not a build-time distribution.

Measured environment: `macOS-26.5-arm64-arm-64bit-Mach-O`, Python `3.14.7`, external SSD. Source checkout: `7f5395b7b95b89c19bc1bb15809745cfb6c6a6af`; exact module hashes and harness hash are in [synthetic_results.json](synthetic_results.json). These data establish bounded fixture correctness and observed local scaling through the existing 256-capture cap. They establish no production latency, concurrency guarantee, larger admitted population, dollar cost or forecast usefulness.

Reproduce from a checkout with project test dependencies installed:

```sh
python3 research/market_memory/performance_20261015/benchmark.py \
  --repo "$PWD" --output-dir /absolute/new/private/output-directory
```

The output directory must not exist. Each build, append, and read child has a 300-second wall-clock limit; a failed size stops larger sizes. The harness does not clear OS caches, change source limits, contact a provider, or read production data. The original synthetic protocol remains unchanged; parent corrections enforce its timeout and precise-refusal requirements and separate harness metadata from storage artifacts.

The admitted Fabric worker supplied the initial harness. Parent review found and corrected unbounded build/append execution, an overly broad refusal match, inaccurate unexpected-capability reporting and mixed metadata accounting; six failure-path checks passed before this run. The returned artifact itself has not been marked accepted in the Fabric ledger. Its SHA-256 was `f8a354abf71f20a959be1d0229970aa621bf62d776d1f1c2231fb1fe72af8195`; the corrected measured harness SHA-256 is `e7585997e72cf09794d7faf0661a70ad2d3ee302abf2d1a32a7e8463a28fc77a`. No worker billing receipt was available, so no provider-cost claim is made.


The prior real eight-run baseline remains in `research/MARKET_MEMORY_REAL_CORPUS_LATENCY_2026-10-14.md`: nearest-rank P50 20.512 seconds and P95 31.253 seconds (the largest of eight observations). Current-policy checks remain intact. Full program economics still requires qualified refresh, review/model and production-concurrency measurements, including the G0/G1 consumers.

## Existing producer refresh accounting

A read-only systemd metadata snapshot at 2026-10-15T18:33:08.692032+00:00 captured the most recent process accounting for five existing units. No job was triggered and no log payload, source values or outcomes were read. These are individual last-run observations, not a latency distribution or a forecast of recurring costs.

| Existing unit | Last process wall seconds | Recorded CPU seconds | Result |
|---|---:|---:|---|
| source-spy-rest | 305.729 | 3.385 | success |
| technicals-v2 | 0.438 | 0.236 | success |
| experience-v2 | 2.186 | 1.133 | success |
| context | 1.490 | 0.486 | success |
| options | unavailable | 0.208 | signal |

The source unit intentionally waits through a five-minute sealing window; its 305.729-second wall duration is not CPU consumption. Systemd reported 3.385 CPU seconds and 70,410,240 peak memory bytes for that run. Context projection reported 17,866,752 peak bytes. Technicals/experience memory peaks were unavailable. The options unit reported a signal termination and no complete duration, so no successful options-refresh cost is claimed. Exit status alone does not qualify a data generation or prove a causal join; the separate accepted natural-capture evidence retains that obligation. Provider/API fees, fitted-model work, human review and independent evaluator costs remain unmeasured.
