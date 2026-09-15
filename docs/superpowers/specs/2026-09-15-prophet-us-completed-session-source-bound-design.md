# Prophet US Completed-Session and Source-Bound Publication Design

**Status:** Approved by Chairman in the active Sol session on 2026-09-15.

**Outcome:** Restore lawful US Prophet origination on weekday pre-close runs without weakening mixed-vintage safety, and ensure the exact ranked board and every derived Prophet publication become durable atomically.

## User and machine jobs

The user must receive fresh Prophet plans when valid candidates exist, rather than a zero-pick surface caused by provisional daily bars or a publication-date clock error.

The machine must score one coherent completed-session US equity cross-section, preserve raw vendor reach for diagnostics, validate entry-price clocks against the actual observation instant, and publish the source board with its derived plans through one guarded checkpoint.

## Confirmed failure chain

On 2026-09-15 the US board combined 3,038 members ending on the completed 2026-09-14 session with 198 members already carrying provisional 2026-09-15 daily bars. Ranking happened before the existing mixed-vintage guard refused all eligible candidates.

A second defect treated the date-only publication stamp `2026-09-15` as though that session were already complete, rejecting the valid 2026-09-14 price basis during the 2026-09-15 trading day.

A third defect let the narrow Prophet checkpoint publish plans and `site/prophet/index.json` without publishing the exact `site/factordata/us_standouts.json` bytes they derived from. The later broad engine commit could also publish that board after the narrow checkpoint refused, recreating a split source/projection state.

## Architecture

Capture one UTC observation timestamp at the start of the US board build. Derive one `expected_last_session(observed_at_utc)` and reuse it across residual alpha, benchmark context, the stock universe, per-name OHLC, signal and entry gauges, extension and dispersion reads, staleness, live origination, and Prophet Arena.
US equities and equity-derived benchmarks are sliced to dates at or before that completed session before any scoring. Crypto remains on its continuous calendar. The receipt preserves the raw maximum date and the bounded names carrying provisional rows, so normalization changes the scoring authority without deleting evidence.

The existing mixed-vintage gate remains unchanged. After normalization it judges differences among completed session dates, so a genuinely torn Monday/Friday panel still fails closed.

Live and Arena origination read `staleness.observed_at_utc` when present. Timestamp-aware validation uses `expected_last_session`; date-only historical fixtures and replay inputs retain the existing `last_session_on_or_before` fallback.

## Source-bound publication

The exact board file is part of the Prophet-owned delta even though `build_site` wrote it before the Prophet step. Its before-fingerprint therefore comes from checkout `HEAD`, while its after-fingerprint comes from the frozen working-tree bytes hashed into the origination source snapshot.

`site/factordata/us_standouts.json` must participate in every checkpoint boundary:

- the build-owned exact allowlist and delta manifest;
- checkpoint protected-path race detection;
- checkpoint manifest path allowlist and byte verification;
- post-push current-main proof;
- public-health R2 supersession proofs;
- accepted-source restore for downstream derived ledgers;
- final broad-engine safe restore and reset, so checkpoint refusal cannot be bypassed.

The narrow checkpoint remains the sole publisher for this board-plus-Prophet operation. Correction ledgers remain inputs and never enter the output manifest. Deletions, symlinks, same-path races, off-main dispatches, and changed source bytes remain fail-closed.

## Failure and null behavior

A missing or malformed observation timestamp does not authorize freshness. Existing date-only semantics remain available only where the caller supplied no timestamp.

An empty candidate night is valid. A non-empty eligible population with zero originations remains an acceptance alarm, not permission to weaken chronology or mixed-vintage gates.
A failed narrow checkpoint leaves the prior accepted source and projection authoritative. Downstream shadow ledgers may run only after restoring both from current accepted `origin/main`.

The public R2 payload remains the minimal health projection. The full plan book remains forbidden on public R2, and its unconditional tombstone remains a separate step.

## Non-goals

- Do not disable or soften mixed-vintage refusal.
- Do not create a new clock, event, publication, retry, or health authority.
- Do not change Prophet admission, ranking, scoring weights, plan identity, geometry, or trade authority.
- Do not use provisional same-day daily bars as completed-session evidence.
- Do not combine the separate China recovery effect reconciliation into this US source-writing operation.
- Do not replace PR #7161's market-session cohort repair; integrate or rebase that separate control-plane slice after this producer repair is accepted.

## Acceptance

The implementation is accepted only when all of the following are true on one immutable candidate head:

1. A pre-close Tuesday observation scores every US equity through Monday while retaining raw Tuesday reach.
2. Crypto retains its continuous-calendar row.
3. A genuine completed-session tear still reports `mixed_vintage=true` and remains blocked.
4. Pre-close Monday price basis validates; the same board after Tuesday settlement fails stale.
5. Live origination and Arena use the same observation clock.
6. Residual alpha and stock-library scoring use the same completed-session cutoff.
7. The source board is in every narrow checkpoint, R2 supersession, accepted-source restore, and broad-commit refusal fence.
8. Existing Prophet chronology, staleness, extension, workflow-contract, and checkpoint tests remain green.
9. A real scheduled or bounded production-path run originates from a coherent current board, or truthfully reports no valid eligible candidates for reasons other than the repaired defects.

Merging the implementation establishes `BUILT_NOT_PROVEN`. Only an observed production run through the real nightly path can establish `PROVEN_LIVE`.