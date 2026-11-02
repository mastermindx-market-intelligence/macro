---
workstream: WS:RATES-INFLATION-COMMAND
session: claude/ssd-ric-e0-runs-3b1dac0565d91b0d
model: opus
ended_because: complete
mission: >
  Rates & Inflation Command e2e programme (masterplan
  research/rates_inflation_command/e2e_20261013/MASTERPLAN.md, §13 task graph). This checkpoint
  covers tasks M0 (H1 coherent-target requalification of the release-forecast claims) and X0
  (H3 release-to-rates reaction), both run exactly once against the frozen E0 protocol, plus
  the one consumer change the M0 protocol requires: withdrawing the nfp v3_factor claim.
state_before: >
  E0 (frozen research protocol, PR #9212), F0 (#9222) and F1 (#9232, coherent first-print
  target) were merged. The release-forecast producer still published every model's point and
  interval as a display-only shadow claim, scored against a target that mixed vintages. No
  run had tested any claim against the coherent target, and the release-to-rates reaction had
  never been measured under a declared trial budget.
changed:
  - path: research/rates_inflation_command/seat_20261014/m0_requal.py
    what: Frozen M0 runner (stdlib only). Scores 13 evaluations against the same-release-vintage first print, Holm across m=13, honest-N by distinct release episode.
  - path: research/rates_inflation_command/seat_20261014/m0_results/m0_requal_2026-10-14.json
    what: The one M0 receipt (sha256 80cf894c…). 1 QUALIFIED_RETROSPECTIVE (pce_headline.champion, R=0.461), 1 FALSIFIED_UNDER_COHERENT_TARGET (nfp.v3_factor, R=1.373), 11 NOT_DEMONSTRATED.
  - path: research/rates_inflation_command/seat_20261014/x0_reaction.py
    what: Frozen X0 runner. Release-day surprise vs DGS2/DGS10/DFII10 daily changes, Newey-West, Holm, era split 2010s vs 2021+.
  - path: research/rates_inflation_command/seat_20261014/x0_results/x0_reaction.json
    what: The one X0 receipt (sha256 97c10b6d…). 8 of 8 evaluations NOT_IDENTIFIED; descriptive only.
  - path: data/trial_ledger.jsonl
    what: Two declared_budget rows, ric_mri_coherent_requal_v1 (n=13) and ric_x0_release_reaction_v1 (n=8). Nothing else in the ledger changed.
  - path: scripts/build_release_forecast.py
    what: _WITHDRAWN_SHADOW_CLAIMS pins the nfp v3_factor withdrawal to the M0 receipt and protocol sha256. A withdrawn pair publishes display_only, epochs and claim_withdrawn only — no point, interval or warning. The forward shadow ledger keeps scoring it.
  - path: templates/dashboard.html.j2
    what: v3FactorRow shows a short EN/ZH note and no number when claim_withdrawn is set.
  - path: .github/ci/legacy-jobs.yml
    what: New job ric-e0-retrospective-runners runs tests/test_ric_m0_requal.py and tests/test_ric_x0_reaction.py, with a paths closure over the runners and their engine imports.
  - path: research/rates_inflation_command/seat_20261014/M0_RESULT_2026-10-14.md
    what: Plain-language result note for M0 with receipt identity, verdict table and sensitivities.
  - path: research/rates_inflation_command/seat_20261014/X0_RESULT_2026-10-14.md
    what: Plain-language result note for X0 with receipt identity, the eight post-run checks and the descriptive table.
verified:
  - claim: The withdrawal block in the producer matches the committed M0 receipt byte for byte and covers every FALSIFIED evaluation in it.
    command: python3 -m pytest tests/test_release_integration_2b.py -q
    result: 56 passed, 1 skipped.
  - claim: The dashboard renders no number for a withdrawn claim, in both languages, with no refutation vocabulary in user copy.
    command: python3 -m pytest tests/test_release_radar_ui.py -q
    result: 114 passed.
  - claim: The runners reproduce their committed receipts' rules on synthetic fixtures.
    command: python3 -m pytest tests/test_ric_m0_requal.py tests/test_ric_x0_reaction.py -q -p no:cacheprovider
    result: 79 passed.
  - claim: The design and claim guards pass on the changed template and copy.
    command: python3 scripts/check_design_system.py --mode enforce-added --diff-file <diff of templates, scripts and tests>; python3 scripts/check_runtime_style_injection.py; python3 scripts/check_validated_claims.py
    result: blocking=0; OK; OK.
unverified:
  - claim: The withdrawal is visible on the served macro.html.
    what_would_verify: The first render after merge, then a live fetch of site/macro.html and data/release_forecast/release_forecast.json showing claim_withdrawn on nfp v3_factor and no number in that row.
  - claim: pce_headline.champion's QUALIFIED_RETROSPECTIVE holds forward.
    what_would_verify: E1/E2 forward evaluation per the E0 protocol. A retrospective qualification is not a promotion and grants no rank, size or gate.
unresolved:
  - "B0 (#9233) owns the B0 basis-contract freeze doc amendments; this PR returns that doc to main's bytes."
  - "C0 waits on T0, D1, Y1 and I0; P1, A0, E1, X1, P2, G0, S0, V0, E2, B1, A1 and Z0 follow per §13."
next_actions:
  - "After merge: a green main ci.yml baseline (this PR edits .github/ci/**), then live-verify the withdrawal on the first covering render."
  - "X1 (C0, X0) may cite X0 only as DESCRIPTIVE_ONLY or NOT_IDENTIFIED; with 8/8 NOT_IDENTIFIED it has no co-movement claim to carry."
  - "E1/E2 read the M0 receipt as their retrospective baseline; they do not re-score it."
do_not_redo:
  - "Never re-run M0 or X0. Each family spent its declared budget once; a second scoring double-counts the trial."
  - "Do not restore a number for nfp v3_factor in any consumer without a new, separately budgeted trial that clears the E0 protocol."
  - "Do not read X0 as a forecast, a sizing input or a causal explanation; its vocabulary is {DESCRIPTIVE_ONLY, NOT_IDENTIFIED}."
danger_areas:
  - "The withdrawal check hashes the committed M0 receipt; editing that JSON (even whitespace) fails the integration test by design."
  - "combined_v1 and regime_outlook must stay byte-unchanged; the withdrawal touches only the v3_factor shadow branch."
  - "Front-facing copy may never say falsified, refuted or 证伪; the withdrawn row says only that the estimate is no longer shown."
prs: [9212, 9222, 9232, 9233]
---

# WS:RATES-INFLATION-COMMAND — E0 retrospective runs M0 and X0 (2026-10-14)

A checkpoint of a continuing programme. M0 and X0 ran once each against the frozen E0
protocol; their receipts and the one required consumer change ship together here.
