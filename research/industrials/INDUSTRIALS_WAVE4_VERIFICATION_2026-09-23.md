# Industrials Wave 4 - Verification and limitations

23 September 2026. Operation: `gmi-industrials-sector-research-20260923-sol-001`. Macro Draft/HOLD PR #7789. Research and proposed requirements only; not a final Fable handoff.

## Executed research checks

Command: `python verify_wave4_research.py` in the Wave 4 research directory. Complete local runs before publication and after immutable readback each returned **77 PASS, 0 FAIL**, exit 0. No failed assertion or tolerance change occurred in these runs.

The suite contains 40 arithmetic/scenario checks, nine invalid-input checks, fourteen deliberately incompatible measurement comparisons, four comparison/publication-availability controls, and ten document/index checks. The comparator is an intentionally narrow authored fixture, not a production admission service. The 32 W4-T application cases in the economic model are written requirements, not executed application tests.

The arithmetic covers contract-role-dependent durability, maintenance-system work in progress, finite installation-cohort value, hypothetical license investment, generic recognition catch-ups, pass-through denominators and selected issuer reconciliations. Scenario assumptions are visible and uncalibrated. Passing checks do not establish actual contract parameters, future visit counts, current fair value or predictive power.

## Exact-byte readback

At immutable commit `f6b5ad53d5e7ec4b5fda62146a3b67e0e5e21e4a`, all four GitHub file blobs matched the Git blobs calculated from the executed local UTF-8 files:

| Artifact | Bytes | Git blob |
|---|---:|---|
| `INDUSTRIALS_WAVE4_ECONOMIC_MODEL_2026-09-23.md` | 40192 | `4008fdfbc5cf645050a7031de18862d1df66b2a2` |
| `calculate_wave4.py` | 7463 | `686778a2b7e2d187fcffa4a17150fa7a719b079e` |
| `verify_wave4_research.py` | 8517 | `d7f09e3c427749bc57718a459b892a295281fd49` |
| `WAVE4_SOURCE_INDEX.json` | 3613 | `a4dce34daf762dd147a24b218e6a1e42f76982da` |

The economic model contains 5,685 whitespace-delimited words, 24 research slices, 12 hypotheses and 32 proposed application requirements. The original 26-source register was separately read back at `15e0e698ce6edfb0aabb6ebadefe0a15b39b7d11`, blob `7533cc3797ae9edfd769ac9130f1cf04c8b5f110`. No local exact-copy claim is made for that register. The portable source index points to its immutable location and lists the source URLs.

Generated calculation/check/byte-verification JSONs are reproducible portable outputs, not new canonical datasets. No raw reports, paid corpus, source-retention receipt or private product payload is included by this research publication.

## What is not proved

No independent factual-review receipt, source-rights admission, complete company/product universe, current price/consensus panel, empirical backtest, forecast calibration, application test, CI acceptance, deployment or browser proof is claimed. The publicly documented comparison cohort is not a set of authorized live basket constituents.

The maintenance model holds hours fixed and approximates long-run renewals. It is not a finite-fleet age/availability or queue simulation. The work-in-progress identity requires a stable boundary; additional system assets are not automatically owned by the repair provider. The finite cash model has no terminal value and assumes the stated net service stream. The cost-to-cost example is generic and does not implement every aerospace accounting policy or onerous-contract rule. These limitations must survive any later product implementation.

Current gaps include contract terms, active-engine cohorts, workscopes and actual shop economics, substitution/adoption evidence, rights and investment commitments, shareholder-level capital reconciliation, point-in-time expectations and specialist/global breadth. Post-cutoff releases remain unavailable rather than being backfilled.

## Continuation

Retain Wave 1, canonical Wave 2, W2X and Wave 3 without redoing their source sweeps. The next principal unit is defense/long-cycle program funding, risk allocation, execution and cash economics; then construction, building systems and essential services. Fable's final implementation handoff remains withheld. No product source, live curation, worker, Executive Attempt, watcher, merge, deployment or trading authority was changed.
