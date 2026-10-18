# WM/KO Prophet backend delivery evidence — 2026-10-18

Root: `prophet-wmko-miss-20261018`. Continuation of Macro #6817 comment 6247452059.
Protected compatible authority: Mastermind `d5cce731a23588ddbf4df806bd9e8dcfa5eecf24`.
Original carrier and branch preserved. This document records source/test evidence, not deployment or authenticated live completion.

## Behavior and invariants

- Observation JSON serializes through the actual HTTP route. Only native observations contribute event IDs, counts, pagination and B1 relations; ticker absence is a separate `subject_coverage` field.
- Universe membership is proven against the exact source session, manifest digest, producer source contract and the same verified public-artifact receipt. Missing or inconsistent proof withholds the membership claim.
- Row price/asof/reset/slow-confirmation fields preserve the source's own values and unknowns. A missing row clock is never replaced by the document clock.
- All BUY, alert, entry, ranking, sizing and episode-write authority remains false. WATCH is evidence for review only.
- Existing legacy callers still default to frozen v1. Only the Turn Watch producer selects the prospective v2 contract, once per build, and passes that same parsed snapshot through selection and qualification.
- v2 cannot qualify before session 2026-10-19. Calendar failure, missing stores, invalid grading floors, future/stale modal session or era mismatch fail closed.
- Frozen v1 manifest, signal/detector math and held files `scripts/build_turn_watch.py` and `engine/us_candidate_episode_intake.py` are unchanged.
- New metadata participates in snapshot identity. Consumers may receive one normal 409 while moving between old/new snapshot versions; retry starts a fresh read rather than joining pages across versions.

## Prospective source floor and existing ingestion owner

The v2 roster has 1,928 US resolved-issuer names from the exact canonical reference committed at `1d20bdebb10b30e1924cfcf18c689440c2059d7c`.
The actual punctuation exclusion is BF.B, BRK.B and MOG.A. Its transition metadata discloses 520 retained, 1,408 added and 177 removed names with reference-derived reasons.

An immutable native-loader census of Yahoo price blobs at `e19053d7e5c7cca07646ef9b3328ad029e2619fa` found 1,858 readable stores, 70 missing, 1,845 with at least 200 bars and 1,841 with at least 260 bars.
Observed modal session: 2026-10-14; 1,077 graded names reached it.
Inventory SHA-256: `5eabed98d325a2e0bf58800cd29d53dae7c1e88f07d82fe2d64b067d8b202503`.
This is a preactivation floor measured from that committed tree, not a claim about current production or a completed v2 session.

The existing Yahoo backfill owner now includes the validated v2 roster as a declared consumer. At that snapshot, 68 missing unparked names become eligible; SAFE and SATS remain explicit parked fetch failures.
Existing stored/parked filters, attempt ordering, budget/cap, validation, provenance and refresh owner remain intact. No alternative price basis, synthetic price history, manually fabricated ledger entry or silent completeness relaxation is introduced.
The normal daily owner must supply and qualify actual data before a v2 publication can pass.

## Executed verification

- Complete backend battery: **391 passed, 1 skipped**, process-reported `TEST_EXIT=0`, 22.36 seconds.
  Suites: us_turn_watch; us_turn_watch_v2; prophet_early_observations; prophet_early_observations_v2; prophet_observations_api; prophet_wmko_delivery_contract; yahoo_universe_backfill; us_scan_tier; us_leader_pullback_coverage.
  Receipt preserved at `research/prophet_v4/wm_ko_20261018/prophet-final-backend-battery-20261018.log`.
  The skip is not counted as a pass; sparse-worktree data-dependent gates remain for their normal owner.
- Added regressions first reproduced the source/transport/clock/coverage defects. Yahoo queue tests reproduced five missing-integration failures after installing the repository's existing yfinance requirement in an isolated test environment.
- Exact frozen-v1 file SHA-256: `645dc6274aaa7606734d6f9f77168425fea21556737996ef0664b2c9a122e4eb`.
- Native v1 fixture parity against preimplementation base `1d20bdebb10b30e1924cfcf18c689440c2059d7c`: public artifact bytes equal; uncapped candidate-row bytes equal. The fixture contains zero eligible candidates, so this is not positive-candidate output coverage.
  AST comparison found 37 old function definitions unchanged; only universe, source_contract_status and compute_deck_with_candidates changed.
  Receipt: `research/prophet_v4/wm_ko_20261018/v1_parity_proof_20261018.json`.
- Native committed Oct16 source/public/reference blobs yield 378 source observations, one matched KO row (recorded close 93.90) and zero WM rows with NOT_IN_UNIVERSE under frozen v1. The resulting JSON is also consumed by Terminal decoder/responsive tests as an explicitly labeled fixture, never live proof.
- Existing research `native_replay.json` and `replay.py` were preserved and not rerun. Native cut/replay dates are not silently substituted for dates recorded in earlier source checkpoints.

## Independent review disposition

Paid Fabric `prophet-wmko-independent-review-20261018-r1` completed an independent **REJECT** review of original e190 source.
Response SHA-256: `c583b13ca6194e5239fda419dbcf58cb5c17623935e7e580921e1af495c26da4`.
Its result was accepted as a review report, not acceptance of the implementation.

Repairs cover its JSON-set leak; synthetic-row/count/security-filter issues; incorrect missing-asof fallback; unbound universe proof; source-era versus wall-clock mismatch; legacy-consumer era bleed; repeated contract reads; permissive calendar fallback; optional-import failure; null grading floors; false exclusion metadata; undisclosed v1 removals; and tests that mutated the committed manifest.
The missing-store finding is addressed through the incumbent queue plus an unchanged fail-closed publication guard. The e190 snapshot still has explicit upstream data dependencies.
The original inaccessible Linux-to-Mac build child is terminal/blocked and was not retried. No predecessor safety-blocked checkpoint write was replayed.

Final immutable-head CI/review, normal deployment, authenticated current-source proof and the first eligible v2 session remain separate acceptance gates.
