# R0 — Custody and writer ledger (Rates & Inflation Command e2e 2026-10-13)

Seat: Fable Meta-CEO, Claude Code session `fc3dfe4b-8c15-4c7b-ab42-5741f284f47b`, 2026-10-14.
Acceptance: A01 (custody preserved), A46 (economical delegation, one root/grant/budget).
Masterplan pin: `research/rates_inflation_command/e2e_20261013/MASTERPLAN.md` @ `fd5c6600`
(carrier PR #9132 on `sol/ric-fable-masterplan-20261013` — publication of the plan is not
PICKUP_ACK/START/source transfer; the seat neither touches nor merges #9132).
Base for all work: `origin/main` `6b154e09357300964c0720448cee9654bf2585d0`.
Evidence: `gh pr view <n> --json state,headRefOid,mergedAt,isDraft,title` run 2026-10-14 ~00:5xZ.

## Incumbent work and its disposition
## 2. Custody map (R0, verified 2026-10-14 via gh) — DO_NOT_REDO / NEVER TOUCH

| Item | State | Rule |
|---|---|---|
| #6543 F0 recovery | MERGED 2026-08-28 `a6921aa3` | Reuse. WS record's "awaiting_ci" is stale (seat fixes the record). |
| #8030 yield_momentum fixed_grid_origin.v4 | MERGED | Reuse; do not rewrite F3/v3/v4, do not widen TRAILING_PUBLICATION_LAG_ROWS (>3), do not touch interim TLT/IEF block in credit_momentum. |
| #8836 release_forecast.v2 consumer | MERGED 2026-10-11 `db40ae32` | Reuse. |
| #8396 GRI regime_outlook publish | MERGED 2026-10-04 `bb827bd1` | `regime_outlook` key in the RIC artefact is GRI-owned: preserve byte-compatibly; never rewrite its composer/contract. |
| #7909 [RIC][RESEARCH][HOLD-FOR-SOL] | OPEN DRAFT head `1ddc25a8` | HELD. Never merge/arm/push/ready/comment. Do NOT rerun its 48 RD1 / 18 swing configs; its negatives are retained evidence (E0/M0/X0 read it). |
| #7521 policy consumer integration | OPEN DRAFT HOLD-FOR-SOL head `8da98209` | HELD. Read-only prior art for D0/D1/T0; never cherry-pick its bytes into another PR; record divergence. |
| #7923 matched-contract vs policy-path roll (`engine/rate_futures_repricing.py`, `policy_path_repricing`) | OPEN DRAFT HOLD-FOR-SOL head `15ccca76` | HELD. Read-only prior art for D1/X1; do not mint a competing `policy_path_repricing` key or module name. |
| #7940 freeze policy_path_repricing into forward_log | OPEN DRAFT HOLD-FOR-SOL head `9c2f2d3e` (stacked on #7923) | HELD. Read-only prior art for E1. |
| #7965 regime-cell lookup era fix (`engine/release_market_context.py`) | OPEN DRAFT HOLD-FOR-SOL head `aa256792` | HELD. Do not edit `release_market_context.py`'s regime-cell lookup. |
| #9132 masterplan carrier | OPEN DRAFT `sol/ric-fable-masterplan-20261013` | Never touch (sol/*). |
| Issue #8317 GRI programme + held GRI PRs #8257 #8301 #8304 #8306 #7871 #7088 | OPEN | Separate programme. GRI E0 slices touch Rates Command `asof` fallback and `compact_state.usd_dir`: do not change those two seams' semantics; if a task requires it, STOP and return to the seat. |

Other standing DO_NOT_REDO (WS record + handoffs): no second release/calendar/options/

## Active writers in this programme (single-writer law)

| Writer | Identity | Owned paths |
|---|---|---|
| Seat (Fable Meta-CEO) | session fc3dfe4b | `.github/ci/legacy-jobs.yml` enrolment, `agentos/**` records, `research/rates_inflation_command/` (except `e2e_20261013/`), merges, labels, ready, carrier posts |
| ORCH-A (native Opus orchestrator, parent = seat) | Agent `RIC-ORCH-A` | `engine/rates_command_basis.py`, `contracts/rates_command_basis.v1.schema.json`, `tests/test_rates_command_basis.py`, `engine/rates_inflation_command.py`, `tests/test_rates_command*.py`, `scripts/build_rates_command.py`, `tests/test_build_rates_command_outlook.py`, `templates/dashboard.html.j2`, `templates/macro_rates_curves.html.j2`, `templates/release_publications_live.js` (+ paired site copy) |
| ORCH-B (native Opus orchestrator, parent = seat) | Agent `RIC-ORCH-B` | `collectors/rate_futures.py`, `engine/fed_path.py`, `tests/test_fed_path.py`, `engine/release_forecast.py`, `engine/release_forecast_v3.py`, `engine/inflation_intelligence.py`, `engine/event_calendar.py`, `engine/event_window.py`, `engine/yield_momentum.py` and their tests |
| Fabric lanes | launched by ORCH-A/B via `$K/ext/sub.sh` on m2studio | only the paths of their lane packet, in their own SSD lane tree |

Root identity for every descendant = this seat session; budget = programme lane cap ≤8 concurrent
fabric lanes (≤4 per orchestrator), ≤2 native Opus orchestrators, GLM fair share respected
(pool_status 01:18Z: glm 10 free share 2/orch, grok 54, cursor 18). A queued admission is not
START; START is a lane's first stdout line; a return is consumed by its immediate parent only.

## Uncertain effects
None at R0: the seat had launched no lane, pushed nothing and opened no PR before this ledger.
