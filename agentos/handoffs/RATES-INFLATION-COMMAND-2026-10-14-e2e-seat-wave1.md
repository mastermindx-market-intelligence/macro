---
workstream: WS:RATES-INFLATION-COMMAND
session: claude/rates-inflation-fable-masterplan (Fable Meta-CEO seat fc3dfe4b)
model: opus
ended_because: ci_handoff
mission: >
  Chairman masterplan 2026-10-13 (research/rates_inflation_command/e2e_20261013/MASTERPLAN.md
  at fd5c6600, section 12 = the commission): recover and complete the included core of Rates &
  Inflation Command plus Macro Release Intelligence. Real release and rates evidence must reach
  matched-basis calculations and the existing entitled user/machine consumers with target, model,
  vintage, basis and rights intact. All six reference families, independent scientific and
  user-usefulness decisions, correction/recovery and operating economics must be proven. This
  checkpoint records the first wave of that programme; the programme continues.
state_before: >
  F0 (#6543) and the release_forecast.v2 consumer (#8836) were merged. The seat recorded the
  R0 custody ledger and the B0 basis-contract freeze (#9206). No basis-aware comparison
  contract, no board qualification repair, no futures/SEP or curve provenance, and no frozen
  research protocol existed on main. The Rates Command board defaulted the ZQ policy gap to 0
  and showed an unqualified CPI row.
changed:
  - path: research/rates_inflation_command/seat_20261014/R0_CUSTODY_LEDGER.md
    what: Custody and effects ledger for the programme (#9206).
  - path: research/rates_inflation_command/seat_20261014/B0_BASIS_CONTRACT_FREEZE.md
    what: Frozen basis-contract design for matched-basis comparisons (#9206).
  - path: research/rates_inflation_command/e2e_20261013/
    what: E0 frozen research protocol and the P0 workflow design spec (#9212, f57ee3a7).
  - path: engine/event_window.py
    what: F0 gap A10 — reads the canonical calendar at call time; the HK desk reads it too; drift ledgers pinned empty (#9222, 9947bf53).
  - path: scripts/build_release_forecast.py
    what: F1 first-print track record on the release radar in templates/dashboard.html.j2 (A04, A08, A11), with dark/light EN/ZH evidence crops (#9232, 818a571b).
  - path: engine/rates_command_basis.py
    what: B0 contract rates_command_basis.v1 (A06) — pure comparison over target/model/vintage/basis/rights; rights default unknown and unknown blocks the export purpose (#9233, c930bdb5).
  - path: engine/fed_path.py
    what: D0 futures and SEP provenance on fed_path (A14, A15, A19) (#9252, 013e99ca).
  - path: engine/yield_momentum.py
    what: Y0 curve convention and endpoint qualification (A20, A21) (#9254, b23c4bf8).
  - path: engine/rates_inflation_command.py
    what: T0 board truth (A03, A04, A05) — no ZQ gap default, qualified CPI row, historical countdown, per-row basis and rights from the D0 strip metadata (#9253, 2f0cf411).
  - path: research/rates_inflation_command/seat_20261014/F0_COVERAGE.md
    what: The F0 A07-A10 coverage receipt with a seat addendum recording that the HK calendar drift is fixed on main (this PR).
verified:
  - claim: All eight wave-1 PRs are squash-merged on main.
    command: git log origin/main --format="%h %s" -E --grep="\(#(9206|9212|9222|9232|9233|9252|9253|9254)\)"
    result: Eight commits returned (3e5b68f3, f57ee3a7, 818a571b, 9947bf53, b23c4bf8, 013e99ca, c930bdb5, 2f0cf411).
  - claim: The HK desk has no second US calendar on main.
    command: sed -n 18,23p tests/test_ric_f0_a10.py
    result: _HK_US_CPI_KNOWN_DRIFT = {} and _HK_US_NFP_KNOWN_DRIFT = {}.
  - claim: The T0 merge carries its own bytes, not only a PR state.
    command: land_check against the T0 head and merge commit, then git grep for _rate_path_rights in origin/main
    result: Landed; _rate_path_rights is present in engine/rates_inflation_command.py on main.
unverified:
  - claim: The wave-1 board changes are visible on www.mastermind-x.com macro.html.
    what_would_verify: A successful render covering 2f0cf411 (the F1 render 38530684032 was cancelled; a covering render was reported in flight), then a live read of the Rates Command rows for the not_identified gap state and the row basis.
  - claim: The served numbers are current.
    what_would_verify: The nightly data lane has been stale since cdab77c4 (2026-10-09); the prophet-outage issue #9050 is owned elsewhere. Current numbers need a successful nightly; never dispatch daily.yml from this programme.
  - claim: M0/X0 retrospective runs are merged.
    what_would_verify: PR #9282 merged at head 2dd2f856 after concluded-green CI, then a land check.
unresolved:
  - "#9282 (M0 + X0 retrospective runners and their one recorded run) is in CI at head 2dd2f856. The CI job is scope: exclusive and listed in CURATED_EXCLUSIVE."
  - "T0 and #9282 both edit CI-authority paths. One green main ci.yml baseline on a descendant of both merges is owed; dispatch only over a clear field."
  - "D1 (A16-A19), Y1 (A22-A24) and I0 (A12-A13) are being built under the RIC ORCH-B orchestrator. I0 waits for fabric admission after a disk-reserve refusal. ORCH-B also owes the 2027 FOMC calendar."
  - "The C0 composition packet is written except its S5 slot (owners and merged heads of D1, Y1, I0) and its lane base. The C0 PR also carries the amendment to B0 doc section 7."
next_actions:
  - "Merge #9282 on concluded green with --match-head-commit, land-check it, then run the one main baseline."
  - "Ship D1, Y1 and I0 as each returns, each with its suites wired in .github/ci/legacy-jobs.yml."
  - "Launch C0 after D1, Y1 and I0 land, then P1, X1, V0-pre, A0, E1, P2, G0, S0, V0-post, E2, B1, A1 and Z0 per the masterplan section 13 task graph."
  - "G0 expected family status: CPI supported, PCE partial, NFP and claims supported, ZQ meeting gap, SR3 gap, yield/premium partial (KW only). Print gaps; do not fill them."
do_not_redo:
  - "M0 and X0 ran once against the frozen E0 protocol. Never re-run them; their recorded output is the result."
  - "F0 (#6543, #9222) and the release_forecast.v2 consumer (#8836) are reused, never rebuilt."
  - "The B0 rights vocabulary is (public_official, redistribution_limited, display_only, unknown) with default unknown. Do not widen it or default to a permissive value."
  - "Do not build another source, calendar, forecast, evaluation, publication or control plane, a policy-timing predictor, an opaque market score or trade sizing. Original F2 dealer/OPEX work is excluded, not complete."
danger_areas:
  - "The policy-rate gap in bp is (ZQ - mid) x 100 - gap. The gap is never defaulted to 0. When it is absent the result is not_identified (underidentified:effr_target_basis)."
  - "ZQ is monthly-average EFFR and SR3 is compounded SOFR. CPI is not PCE. Par, zero and forward yields are different series. KW and ACM term premia are never summed."
  - "A new legacy CI job whose inferred closure selects it on the packing probes (scripts/build_free_content.py, templates/index.html, engine/prophet/plan_book.py) must carry scope: exclusive, a CURATED_EXCLUSIVE entry in tests/test_ci_pack.py and paths covering its whole static import closure. Dropping exclusivity widens the job and fails the probe ceilings."
  - "Held PRs #7909, #7521, #7923, #7940 and #7965 and the GRI programme (#8317 and its PRs) are preserved: never merge, arm, push to or comment on them. regime_outlook stays byte-unchanged."
decisions:
  - DEC:RIC-BASIS-CONTRACT-V1-QUALIFIED-COMPARISON
  - DEC:RIC-F1-EVALUATION-TARGET-IS-PUBLISHED-FIRST-PRINT
  - DEC:RIC-E0-RETROSPECTIVE-FALSIFIES-PROSPECTIVE-PROMOTES
prs: [9206, 9212, 9222, 9232, 9233, 9252, 9253, 9254, 9282]
---

## Notes

Wave 1 closes the qualification layer: comparisons now carry target, model, vintage, basis and
rights, and the board no longer invents a policy-rate gap. The composition (C0) and the six
reference families (G0) are next; neither is claimed here.
