---
workstream: WS:RATES-INFLATION-COMMAND
session: claude/rates-inflation-fable-masterplan (Fable Meta-CEO seat fc3dfe4b)
model: opus
ended_because: ci_handoff
mission: >
  Chairman masterplan 2026-10-13 (research/rates_inflation_command/e2e_20261013/MASTERPLAN.md,
  immutable at commit fd5c6600, which is not on main; section 12 = the commission): recover and complete the included core of Rates &
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
  - path: research/rates_inflation_command/seat_20261014/E0_RESEARCH_PROTOCOL.md
    what: E0 frozen research protocol, with DEC:RIC-E0-RETROSPECTIVE-FALSIFIES-PROSPECTIVE-PROMOTES (#9212, f57ee3a7).
  - path: research/rates_inflation_command/seat_20261014/P0_WORKFLOW_DESIGN_SPEC.md
    what: P0 workflow design spec for the three macro.html workflows (#9212).
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
  - claim: The F1 first-print track record is live on www.mastermind-x.com macro.html.
    command: curl -s https://www.mastermind-x.com/macro.html | grep -c "against the official first print"
    result: 6 matches at 2026-10-14 10:5xZ, after render 38518460036 (head 818a571b) pushed 57e1bba1 at 10:38Z.
  - claim: M0/X0 retrospective runs (#9282) are squash-merged and landed.
    command: land_check 2dd2f856 against 470a3700, then git log origin/main --grep="(#9282)"
    result: 470a3700 is on main; the head's paths are byte-identical on main.
  - claim: Main is proven green under the T0 and #9282 CI-authority edits.
    command: gh run view 38554196758 --json conclusion,headSha
    result: success at 470a3700 (ci.yml workflow_dispatch on main).
  - claim: Y1a curve accounting (A22-A24, curve_accounting.v1 on yield_momentum) is squash-merged and landed.
    command: land_check c3967956 against 407b89a6, then git grep -n build_curve_accounting origin/main -- engine/yield_momentum.py
    result: Landed as 407b89a6. The legacy-jobs.yml hunk has the same git patch-id --stable (f1d49015) in the PR diff and the squash diff; main had moved under it. The grep hits lines 1 and 15.
unverified:
  - claim: The T0 board fields (no default policy-rate gap, per-row basis and rights, qualified CPI row) are served.
    what_would_verify: The Rates Command artifact is built only by daily.yml (scripts.build_rates_command). The 2026-10-14 nightly (ddfadfeb, 09:28Z) ran before the T0 merge (10:13Z), so data/rates_command/latest.json has no qualified_comparisons key and no row basis yet. The next nightly whose own headSha contains T0 and whose engine job LANDS must write them. The 10-13 (38340204231) and 10-14 (38495183073) nightlies cancelled the engine job (owner prophet-outage #9050 and prophet_rescue), so data/release_forecast has stood since f6d765cb (10-09). Then read latest.json on main and the live Fed Path card. Never dispatch or cancel daily.yml from this programme.
unresolved:
  - "Y1a edits .github/ci, so it owes its own main ci.yml baseline postdating 407b89a6. Run 38563973832 was dispatched over a clear field; never re-dispatch over it."
  - "Seat rulings for A0 and E1 are folded into the A0/E1 packets, which stay DRAFT until P1 lands. The target epoch implements E0 section 2.H1 and section 5 with no E0 revision. interval_pending applies below n=30. causal_frontier reads canonical_scored_rows only. market_packet _rates_block gets an additive qualified key."
  - "D1 (A16-A19), Y1b (producer wiring of curve_accounting into rate_inflation_transmission, display_only, export false) and I0 (A12-A13) are being built under the RIC ORCH-B orchestrator. ORCH-B also owes the 2027 FOMC calendar."
  - "The C0 composition packet is written except its S5 slot (owners and merged heads of D1, Y1, I0) and its lane base. The C0 PR also carries the amendment to B0 doc section 7."
next_actions:
  - "Ship D1, Y1b and I0 as each returns, each with its suites wired in .github/ci/legacy-jobs.yml."
  - "Launch C0 after D1, Y1b and I0 land, then P1, X1, V0-pre, A0, E1, P2, G0, S0, V0-post, E2, B1, A1 and Z0 per the masterplan section 13 task graph."
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
prs: [9206, 9212, 9222, 9232, 9233, 9252, 9253, 9254, 9282, 9317]
---

## Notes

Wave 1 closes the qualification layer: comparisons now carry target, model, vintage, basis and
rights, and the board no longer invents a policy-rate gap. The composition (C0) and the six
reference families (G0) are next; neither is claimed here.
