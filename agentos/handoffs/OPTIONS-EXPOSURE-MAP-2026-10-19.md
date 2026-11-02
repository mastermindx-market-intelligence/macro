---
workstream: WS:ADVANCED-DATA-OPTIONS
session: 01a156f1-f450-7793-8951-bddadd4784c2
model: codex
ended_because: ci_handoff
mission: Deliver the Options Exposure Map through Release A, then admitted B/C mechanics and research gates.
prs: [9815, 9868, 9874, 9877]
state_before: The initial Options build was rejected for inadequate product quality and competitor parity; the full handoff remained assigned.
changed:
  - path: collectors/thetadata.py
    what: Add an explicit one-GET full-observed-root capture profile while preserving selected-capture limits and defaults.
  - path: engine/options_exposure_projection.py
    what: Add source-bound joint projection and explicitly dated Gamma qualification.
  - path: scripts/build_options_hub_nightly.py
    what: Compose bounded captured inputs through the existing builder while preserving legacy inputs and publication guards.
  - path: .github/ci/legacy-jobs.yml
    what: Keep affected Options tests owned by the existing flow-surface CI lane.
verified:
  - command: Affected exposure, receipt, dated identity, reference-page, Hub, Theta and daily-owner tests
    result: 560 passed; 253 targeted checks passed after malformed-link/metadata repairs; 9 focused daily opt-in cases passed after call-path additions.
  - command: python3 -m pytest tests/test_options_dated_projection.py tests/test_options_source_receipts.py tests/test_thetadata.py -q
    result: 155 passed, including a 14000-row multi-expiry capture and refusal/byte/row controls.
  - command: python3 -m pytest tests/test_options_source_receipts.py tests/test_options_contract_identity.py tests/test_options_dated_projection.py -q
    result: 83 passed after indexing full-book term composition, including 3000 exact term merges and duplicate refusal.
  - command: python3 -m pytest tests/test_options_observed_qqq.py tests/test_repair_gex_history.py -q
    result: 17 QQQ adversarial cases and11 archive cases passed; actual full SPY archive repair also verified offline.
  - command: python3 scripts/audit_unrun_tests.py
    result: Exit 0 after the current-main integration; no newly unwired suite.
  - command: curated_exclusive_closure_findings(Path('.github/ci/legacy-jobs.yml'))
    result: No uncovered flow-surface dependency after the merge.
  - command: TERMINAL_E2E_PORT=3193 npm run test:e2e:responsive -- e2e/options-exposure-workspace.spec.ts --workers=1
    result: All six EN/ZH desktop, tablet and mobile workspace journeys passed after the copy-layer repair.
unresolved:
  - Full actual QQQ source qualification and rights-held native publication; canonical QQQ intake merged, Hub install remains on its original fetch.
  - Protected Terminal release, production deployment and authenticated product acceptance.
unverified:
  - Full QQQ qualification and authenticated production rendering; actual full SPY dated source and local browser proof now pass.
  - Release B nonlinear and Release C empirical/PIT acceptance.
danger_areas:
  - Do not replace a last-good full book with the 20-contract canary or weaken its empty-book guard.
  - Preserve exact source/Fabric operation identities, rights, held carriers and the Chrome extension UI consent boundary.
next_actions:
  - Integrate the matched captured source pair through the incumbent nightly publisher, then verify qualified native API output.
  - Complete exact-head protected CI, merge, git-gated deployment and authenticated product verification.
do_not_redo:
  - Preserve Macro 8555 and 7328 HOLD, IW2 T03k refusal, Save admission and recovered negative QQQ/calibration evidence.
  - Keep original Fabric identities, failed operations and the stopped M2 acquisition distinct; no replay or new truth store.
---

# Current Options source checkpoint — October20,2026

Original root `01a156f1-f450-7793-8951-bddadd4784c2`; source coordinator
`01a15700-1ae2-7a73-9756-f1546da7ace8`. Root owns Terminal, numerical/domain decisions
and final acceptance. Evidence: `/Volumes/Mastermind/evidence/options-exposure-01a156f1`.

**Source:**9815 merged `5c2d0a04afd19642d2dab483885d46c73b7baed4`;9868 canonical intake
merged `e474e63180871fcb55ccc2660f509f336689b9b3`;9874 observed QQQ/archive extension
merged `ef029bd56030c313bc36906a31f6b508c199410b`. Exact active authority, all12packs,
contract-delta, semantic gate and fences passed. Owned source/tests/docs landed; main's
additional China CI job is unrelated. Snapshot follow-up9877 base7634004 retains actual
regular endpoint/parameters/raw hash/capture clock and exact secondary contract+timestamp
joins, no numerical capability. Reuses8684 owner87cc03d raw-clock pattern; no duplicate
history repair or broader8684/CI shard change.337 affected cases passed;25 snapshot negatives.
Current repair adds explicit-economics/URL/date/OI-parameter defenses,243 affected cases
plus46 final receipt cases pass. Existing flow-surface closure{}, unwired audit exit0.
Previous9877 exactCI39427001365/base7634004 has original observer29862/log
`macro-snapshot-ci-7634004-observer.log`; consume its real return after repair push and
verify a new exact-head observer. No idle wake or unlaunched observer is claimed.

**Runtime:** original M1 Hub install completed12:58:55UTC at protected5c2d0a04, import
verified and runtime status preserved. Scoped Theta four-file install completed13:05:57
under incumbent lock/preimages, baseline wrapper/store symlink preserved, opt-in OFF.
Theta GitHEAD remains900b5d8d with intentional scoped source overlay. Distinct later Hub
update installed/import-verified ef029bd. A postflight sparse-absent canonical-file hash
failed after checkout; same-operation reconciliation completed the receipt after verifying
HEAD/code/runtime, with no checkout/fetch replay. Receipts:
`M1-options-hub-5c2d0a04-installed-receipt.json`, `M1-theta-5c2d0a04-install-result.json`,
`M1-options-hub-ef029bd5-reconciled-receipt.json`. Zero providerGET/service restart/book
publication. Canonical master is available as protected Git bytes, not materialized at
runtime path. Native captured-target reader on that blob admits QQQ Oct20 and refuses
Oct19 at actual Oct20 known-by time; no incumbent canonical-store write.

**Accepted A evidence:** actual Oct16 SPY full capture acquired Oct20:13104observed,
12212Gamma-qualified/892missing,33expiries/6552cells/491strikes,251complete strike
aggregates; whole net/gross null. Covered net−20.42010111776526B/gross47.779712252337456B,
provisional leader765, dated underlying763.25USD. Native whole envelope3994690B; full
archive-only dry-run and evidence-copy repair preserve it, no current board replacement.
Parent arithmetic, TS pairing and six EN/ZH responsive map→main-chart journeys pass with
fixture auth/prices, not production. Admission repairs preserve exact actual full-book
metrics/identity/capabilities: `observed-review-actual-positive-witness.json`.
QQQ exact target is SEC:US-XNAS-QQQ/US-XNAS-QQQ, normalized NASDAQ, first effectiveOct20,
ingested11:13:21UTC; no Oct16/19 extension. Native synthetic QQQ119/1/120observed,
3expiries pairs with consumer; actual QQQ source capture remains open. No full-market claim.

**Independent review:** old selected returns remain unaccepted. Broader MiniMax22838
settled provider_output_limit with no findings; preserved, not relabeled. Changed-tactic
GLM/ubuntu2 admission assessment60543 completed and was accepted after discriminating
repairs: explicit contradictory economics remain unknown, exact mapped URL/hash,
resolver-level QQQ admission date, unsupported OIversion refusal rather than invented
Greek version. Actual source mapper already pins chain origin/path; no whole-host attack
or real historical QQQ mint is claimed. `observed-admission-review-v2-adjudication.md`.
This is NOT full numerical/model/temporal acceptance. Root owns distinct numerical review
`oem-01a156f1-gamma-numerical-review-v1`, controller8194/MiniMax/ubuntu0, exact Macroef029/
Terminal3623 excerpts. No duplicate. call-only observed cells may be partial with missing0;
unobserved put membership is unknown, never added to the observed denominator.

**Hard source/publication gates:** original Oct19 full Greek GET remains EFFECT_UNKNOWN,
no return or replay. Distinct Oct16 reference reconciliation charged its repeated settled
page within original15aggregateGET/14104rows/3226397B; no unknown-effect retry. Retained
legacy books lacking acquisition version stay unqualified. Theta signed distribution
terms are unfiled; connected mail found only unsentDRAFT1a13ddd5759e45e7. One exact
signed-terms location question remains pending with Chris; no provider message. Massive
stock terms/reference access do not grant option redistribution. Rights stay null and
publication-only hold remains; never replace newer current books with Oct16 or20-rowcanary.
Qualified nativeAPI target after lawful publication is `/api/hub/gex/SPY` plus entitled
Terminal current/archive flow. Code release/install is separate from these data effects.

**B/C:** explicit EOD requested_version1 guard remains: current methodology and EOD endpoint
docs conflict for omitted-version tenor. Snapshot requested floor is provenance, never
renamed no-floor; actual serving build unknown. Vanna/Charm units/sign remain unproved.
Q02 American finite-difference reference remains RESEARCH_ONLY. Economic expiry must be a
source-bound absolute model horizon, distinct from trading16:15, underlying16:00 mark,
election and physical delivery; do not adapt ETF delivery through SessionClock.settlement.
Existing owners are options_american_exercise/intraday_greeks/options_scenario_surface;
no parallel Greek engine. September21 retrospective price analogue is not exposure-node/PIT
validation. See `expiry-clock-source-boundary.md`; no B/C acceptance.

**Terminal root custody:**1083 at9068d579c7a3925c65dd1b2632f990ac55c0b907,
exact CI39423133774/observer7825/log `terminal-ci-9068d579-observer.log`; prior ffa CI
ALLPASSED and71462 consumed.1091 now3623e8d645b38418ebb800a0578b8c25c2ace27d,
CI39428032213/verified1236/log `terminal-1091-ci-3623e8d6-observer.log`;11971 consumed
exit1 after supersession. Root owns these watchers, protected deploy and authenticated
proof. Preserve Chrome extension consent boundary. Full product A/B/C is not accepted.

Next: finish9877 protected CI/merge and distinct source installation; consume existing
numerical review. Publication follows actual rights/admission and served-session freshness,
not source merge. Preserve #7327/#8555/#7328 HOLD, #8684 custody, IW2T03k refusal, Save
admission, Oct15SPY seal, original source/Fabric identities and effects. No new store,
collector, engine, watcher registry or replacement carrier.
