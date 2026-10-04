# Rotation programme: actual-close repair acceptance and continuation

Owner: Sol. Current Chairman direction is to advance independent programme capabilities while other sessions restore PC CI. Macro W1 PR7174 was left unchanged; no PC runner, label, job or permission was modified.

Procedure: protected Mastermind `f590c068880dbb848bda90b80b73dbcb6688d6fc`, compatible Skillpack 1.0.1. Operation: `rotation-session-close-20260916-sol-001`. Existing scientific owner: `WS:TECHNICAL-OPPORTUNITY-INTELLIGENCE`; no new workstream or control plane.

## Current state: merged, not deployed

Terminal PR593 in `mastermindx-market-intelligence/mastermind-terminal` was normally squash-merged at **2026-09-16T05:36:17Z** as **`8f518af76231667a75d5af91a79ae8454b937424`**. Reviewed semantic head: `953ab4d79316baf9c05c4a8cf87c9bde065d3539`; unchanged reviewed base: `702d81bb35f2c900a5aa1215437bf968aa9e6d93`; source branch: `claude/rotation-session-close-20260916-sol-001`.

All eight CI jobs in run **35058485567** concluded SUCCESS before merge: unit/typecheck, desktop/tablet/mobile/serial browser shards, Quote Hub, ingest/signal-layer, and the required aggregate. All three branch-required contexts were SUCCESS. CodeQL also passed. Sol explicitly released this PR's earlier software HOLD in comment5692562120, then marked it ready and used `gh pr merge --squash --match-head-commit` without an administrator override.

**Production remains unproven and unchanged.** The normal supported SSH command to execute `/opt/terminal/terminal-build.sh` was blocked by the tool safety layer before execution. No owned deployment log was created. Public Terminal HTML still reports `data-dpl-id="702d81bb35f2c900a5aa1215437bf968aa9e6d93"`, the pre-fix release. The deployment action was not retried through a different command, connector, worker, or carrier. Capability remains **BUILT_NOT_PROVEN**, not PROVEN_LIVE.

The earlier deployment preflight had verified the active service, the old deployment marker, no existing Terminal build, and installed script SHA256 `22ac2e1ec24dd2b965d25435c9953790548321af274834ff2a67c444682f75a5`, matching the accepted repository script. Technical readiness did not defeat the later tool refusal.

## Actual capability and one canonical clock

The existing regular-session filter and resampler now use the date's actual close, including shortened sessions and full closures. A five-minute bar starting at13:00 on a13:00 close cannot contaminate the regular-session candle. Existing live-source and stored-history consumers use this same helper. Direct resampling cannot bypass the close filter, even at one-minute resolution. No indicator formula, ranking, admission, plan, feed, ledger or capital authority changed.

The immutable JSON projection is compiled from Macro's existing `lib.nyse_calendar` and `engine.session_digest.session_window_et`. The exporter verifies the exact four owner/package files before and after generation against Macro `112eba2036fd1186e67b914e194f4fa541cfc4df`. There is no second holiday algorithm or runtime cross-repository import. Projection coverage: 2016-01-01 through 2028-12-31, 3,267 sessions. SHA256: `d803dc85fcf3318bc78392e1d645b7063881b86eec95cf06f51192e1d836de98`.

An absent in-coverage date is closed; an unsupported date or invalid projection produces `US_SESSION_CLOCK_UNAVAILABLE`, not an assumed16:00 close. This projects known rules, not future unannounced closures; owner corrections require regeneration and normal release.

## Recovered dependency and CEO boundary

Macro PR7094 at `5bb1bc68c99146fab040aade04bbf1903c51e5b7` identified five failing2025-11-28 cases, each with43 five-minute rows including13:00 instead of42 rows ending12:55. Current production reads independently reproduced that defect in this turn.

Sol accepted the bounded canonical-clock correction for ordinary software release qualification. This does NOT accept the entire TOI W2-0 dataset, authorize W3 outcome work, waive any other research gate, or establish a superior timeframe. Existing main-branch calendar owners provide source authority; the unmerged study is supporting evidence, not an execution grant.

Macro PR7180 has overlapping open plan-origination/source-clock changes, so this slice made no competing edit there. Its PR body and head currently disagree about the final evidence SHA; no claim about its accepted or running state is inferred. At this Terminal slice's pickup, the complete15-open-PR changed-file census had no overlap with the four intraday helper/store/source/route paths. The protected Terminal base remained byte-identical through release.

## Source tests and real-input API proof

The new25-test clock suite first failed10 cases and passed15 against the old shared filter/resampler. After repair, the five focused clock/session/source/route/math suites passed **119 tests**. They cover early/full closures, DST dates, boundary-price/volume sentinels, direct-resampler enforcement, input immutability, unknown coverage, unchanged extended behavior, and volume/anchor checks across every3,267 projected session.

Full `tsc --noEmit --incremental false` passed after restoring four exact omitted tracked fixtures and required source directories; no fixture was altered. Changed-file ESLint passed. The exporter `--check` reproduced the projection bytes against the pinned owner source.

Forty production HTTP responses were captured for AAPL, SPY, NVDA, JPM and XOM, at5m and4h, on2026-09-10,2026-03-06,2026-03-09 and2025-11-28. No vendor credential or forward outcome was read. Raw captures remain private local proof inputs, not committed price corpora.

Captured5m inputs then travelled through the **actual local Next.js `/api/intraday` route**, its existing stored-history reader and the repaired helper. All **20 cases** matched canonical timestamps and OHLC exactly. Accumulated volume was compared with the explicit binary64 summation bound `(admitted_rows + 2) * epsilon * abs(expected_volume)`. All20 passed; original production4h outputs passed15 under the same comparator. All five early-close defects were corrected locally and all15 ordinary/DST controls remained matching.

The initial bitwise comparator reported15 local passes because five September10 volume sums differed by at most `1.4901161193847656e-08`; timestamps and OHLC already matched. Preserve both `.rotation-clock-http-proof.json` and the explained roundoff-qualified `.rotation-clock-http-proof-r2.json`. No price/time tolerance, material-volume waiver, source-code retuning or strategy-outcome selection was introduced. Every local response disclosed `store-only: POLYGON_API_KEY not set`.

## Actual chart-consumer proof

An isolated Chrome instance loaded the real local Terminal. Starting from its normal3D state, three deliberate ArrowUp control actions on the existing Interval slider selected2D, thenD, then4h. The phone slider, chart legend and actual `tf=4h&ext=0` request agreed. At390/820/1440 widths the chart consumed the seven captured-history bars, including the corrected early-close bar, with zero page-error events and zero horizontal overflow.

This used only the existing documented local guest-auth fixture; it did not use FLOW_FIXTURE for intraday data, a provider credential, production authentication or another user's browser profile. The first browser attempt lacked local public-auth configuration and failed; it is not credited. Earlier legacy-cache-seeded screenshots showed a transient control/legend mismatch and were superseded by the direct UI-control proof rather than mislabeled as coherent acceptance. The controlled local chart intentionally mixes bounded historical input and exact bootstrap fixtures; it is not whole-page live-market or point-in-time proof.

Final proof files: `.rotation-clock-controlled-browser.json`, `.rotation-clock-controlled-390.png`, `-820.png`, and `-1440.png`. Actual API input and response digests are retained separately. The source head remained unchanged through this proof.

## Independent review and resource reconciliation

The first bounded builder submission was refused before execution; no log or operation lease existed. Sol implemented directly. A later distinct read-only check, `rotation-session-clock-codecheck-20260916-sol-001`, ran through the existing selected MiniMax pool and returned `NO_REPRODUCIBLE_FINDING` on the pushed semantic head. It inspected the six commissioned source/test/exporter paths. Process66882 exited0 in57.69 seconds; lease `f74856d81372` was verified released. No watcher or successor was commissioned.

This is bounded source inspection, not a production or statistical verdict. Runtime verifies receipt formatting; the exporter verifies source bytes. A close-boundary print is outside regular hours, not automatically in the next trading session. The checker did not itself execute the20-case HTTP replay; parent tests and actual HTTP evidence are separate proofs.

The extra malformed-projection test append and a custom direct-module replay-script write were refused and are not credited. The separately permitted actual Next.js HTTP path provided real-consumer proof; no refused file write was repeated through another tool.

The owned local Next proof server, PID18957, was explicitly stopped and confirmed completed with exit0. All browser contexts and helper execution are closed. No background CEO task or automation was armed.

## Exact continuation and do-not-redo

Use the existing approved deployment owner once a lawful execution path is restored. Reconcile current master, any other live build, and deployment identity, then perform only the normal git-gated Terminal release and fresh production API/browser verification of merge `8f518af76231667a75d5af91a79ae8454b937424`. Do not replay or reroute the blocked action merely because source is merged.

Do not recreate this branch, PR, calendar or repair. Do not rerun completed tests for a fresh chat absent a material source/integration change. The source note in Terminal retains an earlier WIP snapshot; this record and PR593's latest rulings supersede its old pending-local-proof/CI descriptions, but do not erase history or the genuine production gap.

W1 stays aside for the separate PC-CI recovery owners. Extended04:00–20:00 policy, quote-hub classification, missing5m/provider-hour fallback, daily/intraday adjustment comparability, historical corrections, point-in-time membership and full overnight entitlement remain unchanged and separately unqualified. Continue those existing source-basis and episode/private-publication owners after their actual gates; no duplicate data plane or unvalidated adaptive trade controller.

Proof workspace: `/Users/chriswong/Documents/Cluade/charting-app/.claude/worktrees/rotation-session-close-20260916-sol-001`. Organizational continuation is in the existing Macro Agent OS handoff for this workstream, not in a new Terminal memory plane.