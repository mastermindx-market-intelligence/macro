---
workstream: WS:LEADERSHIP-ROTATION-INTELLIGENCE
session: chatgpt-sol-sector-theme-factors-20261030
model: sol
ended_because: ci_handoff
mission: >-
  Add a read-only, multi-horizon sector/theme/ticker factor measurement and
  source-qualified granular regime fingerprint to incumbent rotation intelligence.
  No novel score, market truth, macro regime engine, collector or trade authority.
state_before: >-
  Measured leadership product W1–W5 recorded as delivered under its own ruler;
  predictive capability explicitly not qualified. Existing source-scoped P1
  candidate Draft #10213, not reviewed or merged, has CI failures.
changed:
  - path: engine/sector_theme_factor_intelligence.py
    what: >-
      Pure same-horizon factor projection with coverage/unknown bounds and no
      rights, publish, ranking, forecast or trading authority; source-only.
  - path: tests/test_sector_theme_factor_intelligence.py
    what: >-
      Synthetic counterexamples for clock and MA basis, missing cohort,
      matched-member transitions, weighting and source abstentions.
  - path: research/sector_theme_factor_intelligence/MASTERPLAN.md
    what: >-
      P0–P8 task tree and downstream owner/gate sequence for full product.
  - path: research/sector_theme_factor_intelligence/FACTOR_RESEARCH_AND_EXPERIENCE.md
    what: >-
      Data qualification, factor laboratory, credit/inverse constraints and
      Paper customer-experience spec.
  - path: research/sector_theme_factor_intelligence/GRANULAR_REGIME_MODEL_DECISION_2026-10-30.md
    what: >-
      Twelve-axis quantitative state decision, first-difference/acceleration
      distinction, own-group and single-name exceptions, and draft falsifiable
      prospective forecasting research protocol; no accepted probability.
  - path: engine/sector_theme_regime_fingerprint.py
    what: >-
      Pure read-only P1a view; per-horizon observed axes and bounded breadth
      morphology, same-member first differences and single-name exceptions.
      Explicitly abstains on credit, future probability and unqualified sources.
  - path: tests/test_sector_theme_regime_fingerprint.py
    what: >-
      31 authored synthetic test functions including parameterized authority
      refusals, negative-majority bounds, PIT clocks, units, roster/vintage
      mismatch, two-endpoint acceleration prohibition and individual-name cases.
  - path: .github/ci/legacy-jobs.yml
    what: >-
      Adds new P1a engine/test paths to incumbent leadership-rotation-contract
      job and names both P1 and P1a suites; no separate test runner or waiver.
  - path: research/sector_theme_factor_intelligence/P2_SOURCE_INTERFACE_AUDIT_2026-10-30.md
    what: >-
      Read-only incumbent producer and PIT source census; identity/rights,
      membership vintages, group_flow factor reuse, market-wide versus
      constituent separation and first real vertical acceptance falsifiers.
  - path: engine/sector_theme_owner_bridge.py
    what: >-
      New pure P2/P2b one-US-theme research-preview ingress that composes
      native-shaped PIT membership/identity/rights/known-at market evidence
      and existing group_flow numeric legs without a new data source or score.
      Always denies customer/trade/predictive rights; unqualified preview only.
  - path: tests/test_sector_theme_owner_bridge.py
    what: >-
      Synthetic counterexamples for current-roster vs PIT, stale/future clocks,
      duplicate identity, benchmark/price basis, original receipt, separate
      research rights, owner flow windows, stage and cohort binding.
  - path: engine/sector_theme_regime_explain.py
    what: >-
      Pure EN/ZH numerical explanations from validated descriptive predicates
      and no-forecast source-qualified refusal; no LLM or new narrative truth.
  - path: tests/test_sector_theme_regime_explain.py
    what: >-
      Bilingual proof cases, forged facet abstentions, flat/nonpositive and
      MA-equal distinction, zero/missing basis, and explicit no-publication.
  - path: engine/sector_theme_regime_comparison.py
    what: >-
      Pure cross-sector/theme research scanner with exact benchmark, price,
      session and decision-clock equality, issuer/security overlap separation,
      explicit source/issuer counts and zero rank/customer/trade authority.
  - path: tests/test_sector_theme_regime_comparison.py
    what: >-
      Synthetic aligned-vs-incompatible cohort, benchmark, session, time,
      quote missingness, input forge and issuer/share-class overlap cases.
  - path: engine/sector_theme_regime_timeline.py
    what: >-
      Pure, no-store P3 chronology of as-provided owner previews: matched
      member endpoint transitions via incumbent breadth_change, bounded
      participation direction, and sliding-window RS changes NOT acceleration.
  - path: tests/test_sector_theme_regime_timeline.py
    what: >-
      Static regression cases for source clock, population revision,
      coverage arrivals, partial breadth delta, changed benchmark basis,
      boundary cases, and explicit no-original-lookahead-proof.
verified:
  - claim: >-
      Draft source and the versioned research/plan files were published to the
      existing branch; PR #10213 remains unmerged and Draft/Hold.
    command: >-
      GitHub get_pr_info #10213, fetch_file branch and blob SHA readbacks
    result: >-
      Source-branch commits exist; exact CI acceptance and independent review
      are not proven.
  - claim: >-
      Exact-head hosted checks for prior PR head 42cba03b9e5ec1b7fa85111914d45523128b3f51
      reported concrete source problems.
    command: >-
      GitHub fetch_workflow_run_jobs 41121200535/41121200456 and
      fetch_workflow_job_logs 124287730019/124287877927
    result: >-
      contract-delta: missing new test suite legacy job registration;
      fence-pack: this handoff unparseable without YAML frontmatter.
  - claim: >-
      The actual hosted leadership-rotation-contract suite executed P1/P1a
      before the subsequent P2/P2b/P2c commits.
    command: >-
      GitHub fetch_workflow_job_logs for job 124324232107 (PR head
      73db860f5ebd495ce3950254f9296d29dbd99949;
      CI run 41131426079), selected-job section and pytest results.
    result: >-
      Existing leadership-rotation-contract selected in pack4; 134 passed
      in 4.60 seconds. That prior head's aggregate CI was later cancelled
      by later commits; no current-head green accepted.
unverified:
  - claim: Current exact-head P1a/P2/P2b/P2c CI and independent non-author review
    what_would_verify: >-
      Fetch current head's completed Actions CI/fence checks and the named
      leadership-rotation-contract job's actual new suites. Prior 134-pass
      P1/P1a qualification is from an older head only. Obtain independent
      non-author review after lawful Fabric/reviewer admission; no approved
      review currently exists. Signed-in producer-to-browser and rights/PIT
      gates are separately owed.
  - claim: Granular regime forecasting improves forward detection, calibration or returns
    what_would_verify: >-
      Rights-cleared PIT known-at inputs, preregistered horizon/event outcomes,
      purged chronological tests and prospective shadow calibration against baselines.
unresolved:
  - >-
    Old PR head 42cba03 failed CI for unregistered test suite and malformed
    handoff; both now repaired in candidate source. Prior unrelated
    git-derived workstream-date failure may recur; do not claim a healed CI
    until an exact-current-head run concludes. New P1a tests are CI-wired but
    do not have a returned passing run.
  - >-
    Fabric manual Grok review of new head 8f85fd31 rejected with
    MANUAL_ROUTE_UNAVAILABLE, retry_allowed=false. No independent review;
    do not replay that logical request on another pool or carrier.
  - >-
    GMI qualified true subtheme constituents and rights/use/availability remain
    held; ancestor proxy is never member-level observed breadth.
  - >-
    Paper document target and approved carrier were not resolved; no Paper
    canvas edit or screenshot, no signed-in customer path.
next_actions:
  - >-
    Verify latest exact PR #10213 source head and actual current-head
    leadership-rotation-contract (P1/P1a/P2/P2b/P2c) test execution,
    contract-delta, fence and full-CI conclusions; repair only introduced
    failures on the existing source branch. Keep Draft/Hold until independent
    non-author review and rights/source entitlement gates.
  - >-
    P2 pure research-preview now composes owner-shaped data, separate
    group_flow context and quantified EN/ZH narratives. P3 adds a
    source-only multi-sector/theme comparison matrix and observational
    chronology with exact basis and PIT/correction/overlap abstentions.
    The real critical path is one CURRENT qualified U.S. theme cohort
    with native GMI membership/identity, genuine purpose-specific
    use entitlement and timestamped quote source readers. Never use
    current roster as historical PIT or ancestor proxy as true micro
    membership. No customer publication on unverified receipts.
  - >-
    Bind owner-admitted member PIT, rights, credit source and live clocks;
    future-state probability modeling remains a separately preregistered P6G
    research challenger, not an entry/sizing authority.
do_not_redo:
  - >-
    Existing leadership-rotation W1–W5 and GMI D2C/D2D; preserve W6
    withheld predictive hypothesis test and all incumbent PR source writers.
  - >-
    Existing macro Regime One, regime_vector and GRI regime_outlook; its
    nine overlapping paths are not mutually-exclusive probabilities.
danger_areas:
  - >-
    Older engine/regime_hmm.py smoothed historical P(Quad) uses future
    observations, unsuitable for causal point-in-time backtests.
  - >-
    Legacy CI manifest is CI-authority. Keep an exact single job owner,
    full dependency closure and one branch writer; no CI waiver.
  - >-
    Do not claim favorable predictive power, actual cross-asset cash flows,
    true microtheme membership, or product/production acceptance.
---

# Sector & Theme Factor Intelligence — Sol leadership / source-linked continuation

RECORDED_UTC: 2026-10-30 (fixed session). STATUS: **SOURCE_CANDIDATE / NOT ACCEPTED / NOT SHIPPED**.
RECEIVER_MODE: OPEN_PICKUP; this is a recoverable source record, **not** a worker assignment, START, Executive Job, accepted Agent OS transition, watcher or user signal.
Parent existing organizational programme: `WS:LEADERSHIP-ROTATION-INTELLIGENCE`; dependency existing `WS:GMI-THEME-GRAPH`; do not create a second program.
Current Chairman live directive: build advanced sector/theme/subtheme constituent breadth, multi-timeframe RS leaders/laggards, stage/extension, breadth acceleration/deterioration, inverse/credit interactions, science validation and a coherent Paper-designed Macro/Terminal user journey. Leadership assumed by the current Sol session for this *new additive slice*; no previous source author or old PR owner is assumed to be a live approver. Preserve incumbent live writers and normal review gates.
Protected procedure: `mastermindx-market-intelligence/Mastermind@bb85b429f2ffffd38408080ce4df7d6378c34100`, `mastermind.sol_skillpack.v1` / `1.0.1` / bootstrap-major 1.
Reconciled source starting pin `mastermindx-market-intelligence/macro@6f60f9c75328996fbd43e4472d8890283de165fc`.

## Actual published source carrier — do not clone this effort
- **Draft PR #10213**: https://github.com/mastermindx-market-intelligence/macro/pull/10213 ; branch `sol/sector-theme-factor-intelligence-20261030`. **Do not mark ready, merge, deploy, claim GMI admission or modify other incumbents until the missing exact gates are met.**
- Docs `research/sector_theme_factor_intelligence/MASTERPLAN.md` — P0–P8, owner boundaries, model/experience acceptance.
- Research `research/sector_theme_factor_intelligence/FACTOR_RESEARCH_AND_EXPERIENCE.md` — 12 factor families, preregistration, source/rights, explicit micro-theme ancestor-proxy constraint, Paper screen design. **NOT_APPLIED_TO_PAPER**.
- Code `engine/sector_theme_factor_intelligence.py` — display-only, pure same-horizon source-clock-gated projection. No collector, identity graph, theme truth/state, source entitlement, ranks, user alerts, existing score override or trade authority. Source blob after hardening: `7f5b70c7c832c03158ab25e9fccae04c9c7fb357` at code commit `926df5a4dd5538f0a8a2a73225f9bc6fa092af8e`.
- Tests `tests/test_sector_theme_factor_intelligence.py` source blob `1cfb96b2a43503a28a96e46cc493c97bb7d13b25` at tests commit `0290b1eb5858cd929d9a723305bb88545fd04e42`.
- PR head as of test commit `0290b1eb5858cd929d9a723305bb88545fd04e42`. This handoff may advance the branch head by one additional source-only commit; always re-read the PR's **current exact head**.

## Verified evidence vs missing proof

LOCAL: An isolated local Python/pytest copy at `/mnt/data/stfi_verification/` reproduced the **exact Git blob hashes** of both proposed engine and tests. `python -m pytest -q tests/test_sector_theme_factor_intelligence.py` returned **32 passed in 0.12s**. The import of `engine.leadership_rotation_context` was satisfied by a local **faithful stand-in** of the incumbent selected pure functions. This verifies the new source and regression cases against those formulas, **not** the actual full repository dependency environment or a production integration. No live data, account, price feed or customer path was touched.
GITHUB CI: Latest observed branch head `0290b1eb5858cd929d9a723305bb88545fd04e42` triggered CI workflow run **41120990442** and fences **41120990435**, both reported `queued` at observation. This is NOT green CI or proof that the newly added test pack is selected; inspect original exact-head check/jobs and CI pack ownership.
INDEPENDENT REVIEW: Not accepted or completed. A bounded read-only Fabric audit `stfi-source-audit-20261030-c1`, root `stfi-20261030`, terminated `accepted=false`, `claude-code:unrecognized_model` for AUTO-routed `glm-5.3-flash`; no research report. A distinct PR review request `stfi-pr10213-review-20261030-r1` was refused `INVALID_ARGUMENT field=max_turns` with `retry_allowed=false`; no review completed. **Do not replay either run.** Any genuinely new independent review is a new scoped action after policy/route repair, not a retry or fabricated approval.
PAPER: Direct Mastermind Paper `paper_inspect` returned MCP SSE 429. Studio Direct `studio_fleet_status` also returned MCP SSE 429. No Paper exact document/fileId/artboard/snapshot, no edit, no screenshot, no JSX or live UI. Treat these as tool transport errors, not Paper product/user login failure; no host/bridge fallback authorized by those errors.
EXECUTIVE: `Mastermind_Executive_V3__executive_state` returned MCP SSE 429; original Executive runtime/admission not verified. This does not affect the independently authorized source PR, but no canonical Job/ACK/START is claimed.

## New substantive discovery — do not bypass

`engine/theme_graph/hierarchy_breadth_display.py` measures graph topology, not stock participation. `engine/theme_graph/micro_rs_proxy_display.py` explicitly forbids direct `EXPRESSES/MEMBER_OF` edges for `sub_theme`/`micro_theme` as current law; micro RS is a **PROXY** from ancestor theme ETFs/baskets. The actual graph and current rights do NOT permit invented direct ticker-level subtheme breadth. `theme_state_owner_readers.py` produces selected consistency reads for PIT basket membership/identity/rights but not eligibility; W3B/W3C live qualifications still outstanding. Original owner must adjudicate when authentic subtheme membership may be surfaced.
`engine/live_breadth.py` is display-only with genuine coverage and feed-age gates; use its existing source, no second poller.
`engine/theme_scoring.py` exists but no validated performance of proposed factor interactions. Keep current scoring/entry/position/alert authorities.

## DO_NOT_REDO and access/effects ledger

- Reuse accepted leadership rotation T01–T26 W1–W5 and their scientific negatives; W6 prereg V3 is distinct incumbent continuation. Do not modify their PR heads.
- Reuse accepted GMI graph D2C/D2D and hold W3B/W3C qualifications; no duplicate ThemeState/ontology/rights/writer/source.
- No data collector, market data, Yahoo cache, licensed credit historical series, record, user account, Terminal PR or production state was modified by this project.
- GitHub carries all 5 proposed artifact paths on one isolated branch; source effects verified by GitHub commit/reads. No reviews, merge, deployment or production proof asserted.
- Fabric original controller has terminal result and no accepted work; no duplicate audit commission or automatic fallback. Studio/Paper/Executive 429 are transport observations, not an open invitation to bypass protected carriers.

## Next material actions — in order

1. READ current exact head of PR #10213 and its CI/fences/job selection. If CI fails, repair only this PR/carrier, prove exact-head targeted tests and re-obtain independent non-author review. Stay Draft/Hold meanwhile. If CI new-suite coverage is absent, use the incumbent CI selector's prescribed registration procedure; avoid unreviewed global CI changes.
2. Obtain **genuine qualified owner-admitted** point-in-time member/identity/rights/eligibility/source clocks for one measured US sector or genuine theme via existing `engine.basket_membership_pit`, GMI and price provenance. Build the P2 read-only adapter with fail-closed refusals; **do not** use a claimed micro-member list merely from ancestor proxy.
3. On working exact authorized Paper carrier, choose existing correct source file/artboard, inspect catalog/snapshot, create qualified and proxy/unknown visual states, screenshot/JSX and integrate to authenticated Macro/Terminal route.
4. Build P3–P4 intraday/historical and credit/inverse context only with lawful source rights, session basis and published vintage; research P6 only with actual prospective or verifiable PIT data and frozen new prereg.
5. Production proof: real source→canonical owner→projected frame→served API→signed-in EN/ZH responsive browser; record user-path acceptance, review, scientific outcome and trade/alert authority separately. Never use green CI as this proof.

## Finality classification of this checkpoint

`MORE_WORK_EXISTS` at mission level; P1 source artifact is independently useful but not accepted. External Paper/Executive transport and GMI rights/eligibility currently block their specific effect lanes; a future reader should reassess current evidence before making new changes. No long-running approved autonomous worker is claimed, no guaranteed background continuation, no implicit watcher. If this source branch remains unmerged, this is **not canonically adopted by main**.


## 2026-10-30 granular model addition

See `research/sector_theme_factor_intelligence/GRANULAR_REGIME_MODEL_DECISION_2026-10-30.md` at PR #10213: use an observed 12-axis continuous regime fingerprint and multiple evidence-bound interpretations. Live probability claims remain held pending strict PIT science. This addition does not supersede any existing Granular Regime Intelligence macro authority.


## 2026-10-30 resumed implementation milestone (GitHub source only)

Chairman continuation: **replace the four-condition breadth scan with a more
granular descriptive state, preserving non-predictive and source-law safeguards**.

- Original draft #10213 branch was updated in place; no new lifecycle, feed,
  parent workstream, model authority or conflicting PR. New source files:
  `engine/sector_theme_regime_fingerprint.py`,
  `tests/test_sector_theme_regime_fingerprint.py`.
- 12-axis fingerprint is a projection over the existing P1 factor frame, not
  a new data/model owner: absolute/relative trend, participation, same-member
  breadth first differences, dispersion/median and multi-horizon agreement,
  plus typed UNMEASURED for unsupported slope-acceleration, extension, credit,
  volatility/liquidity and original rights evidence.
- Also reports individual-name per-horizon strength and exceptions against a
  weak group, preserving actual member IDs and without duplicating theme votes.
  Overlapping morphology tags do not form a 100% probability partition.
- Hardening refuses impossible denominator identification bounds, wrong
  fractional units, mixed cohort/membership version, future group knowledge,
  wrong decision time, and any forged publication/predictive/rank rights.
- 31 synthetic test functions authored, parameterized cases more than that;
  **not locally or CI proven yet** for the resumed implementation.
  `.github/ci/legacy-jobs.yml` now names both suites in incumbent
  leadership-rotation-contract pack; no test waiver.
- Research decision expanded with explicit model falsifier, PIT and
  chronology constraints, calibrated event-specific outcomes, duration
  censoring, adverse excursion, macro regime context (non-probabilistic),
  and independent prospective-shadow acceptance. This is a research
  **protocol draft**, not an accepted pre-registration or empirical result.

Latest direct source write BEFORE this handoff: source branch commit
`47d61637f086d767ab74dbf973f5e3891af1e975`;
the handoff update advances that head. Confirm current PR head before acting.
At last read, GitHub CI/fences for that head were `pending` and had not
returned. Independent Fabric manual review was denied with
`MANUAL_ROUTE_UNAVAILABLE`; no review was actually performed. No Paper
edit, customer data integration, release or trading authority asserted.

Classification: `MORE_WORK_EXISTS`. Preserve source changes and diagnose
only newly observed exact-head errors. Next material step: verify code/tests
in the actual repository CI, then obtain non-author review and the GMI PIT/rights
qualified one-group feed before any production-facing consumer.


## 2026-10-30 P2 owner-source audit addendum

`research/sector_theme_factor_intelligence/P2_SOURCE_INTERFACE_AUDIT_2026-10-30.md`
is now committed to the same draft carrier: it distinguishes PIT `baskets`
snapshot coverage, explicit `pit=False` current-roster fallback, original
clock/rights qualification, GMI micro-theme ancestor proxy, and owner
`group_flow` existing acceleration/cohesion/breadth/persistence. This is
source-based research only, not a source entitlement, new market-data route,
live input, acceptance or worker output.

Draft source also added the P1a fingerprint suite to the existing CI pack.
Old CI failures were real; the latest full CI still awaits an exact-head
conclusion. The manual Fabric Grok-review lane denied admission
(`MANUAL_ROUTE_UNAVAILABLE`), with no accepted review. Keep Draft/Hold.


## 2026-10-30 P2/P2b/P2c implementation and evidence frontier

On the SAME `sol/sector-theme-factor-intelligence-20261030` branch
(Draft PR #10213), new read-only `engine/sector_theme_owner_bridge.py`
and test suite compose one existing `baskets` native PIT member shape,
canonical security identities, same-clock benchmark/parent/constituents,
and an explicitly scoped research-use claim, through the already-owned
P1 factor and P1a fingerprint. The result is ALWAYS
`RESEARCH_PREVIEW_ONLY`, with no customer source-use attestation,
future-event odds, original vintage proof, alerts, sizing or execution.
Strict null/hold states are tested for mixed adjusted-price bases,
unknown identity, missing original membership availability, PIT/current
roster contamination, date-order issues, unqualified child themes, and
future known/benchmark values. No customer data was acquired here.

P2b consumes `engine.group_flow.fingerprint_at`'s already-computed
`accel_z`, `broadening_z`, observed sample breadth, cohesion, persistence,
RS percentile and real lowercase stage in a separate `OWNER_REPORTED_RESEARCH_ONLY`
context with matched 20d cohort, 50-session/daily basis, owner windows,
known-at and research-purpose/source revision. It never copies the incumbent
renormalized `flow_score` into a rank/trade score; owner source is not
authenticated by this bridge. Synthetic tests were authored and registered
in the SAME original `leadership-rotation-contract` CI job.

P2c adds deterministic English/Chinese explanations
(`engine/sector_theme_regime_explain.py`, own tests), bound to numeric
facets and nulls instead of generated model opinion. No fabricated
probabilities or trading verbs. Corrections to P1a semantics distinguish
majority **flat-or-negative** from strictly declining and equal-to-MA
from strictly below-MA; tags and tests were updated accordingly.

Verified actual hosted CI on earlier exact head
`73db860f5ebd495ce3950254f9296d29dbd99949`:
`leadership-rotation-contract` in pack4 completed **134 passed/4.60s**
(job 124324232107), and contract-delta/fence each completed success.
That older aggregate CI was later `cancelled` during successive draft
commits. **The P2/P2b/P2c suites and semantic fixes lack a concluded
exact-head native CI verdict as of this handoff**, and no independent review,
merge, real-source proof or production path is claimed.

The original Fabric manual Grok review returned
`MANUAL_ROUTE_UNAVAILABLE` / `retry_allowed=false`; no same-action
cross-route replay. Paper direct inspect again returned
`MCP SSE probe returned 429 from openai.org` in this session; no
Paper file ID/artboard/screenshot, no studio/desktop fallback. Other
authorized source work remained independent.

Last source commit BEFORE this handoff:
`57caa7c8bd874657bcb226dc40719134467f6a5f`.
Read PR #10213 fresh for the exact current head after the handoff write.
Mission state **MORE_WORK_EXISTS**; no ongoing durable worker and
no trade or customer feature has been promoted.


## 2026-10-30 resumed P3 group comparison / chronology milestone

New source-only `engine/sector_theme_regime_comparison.py` + tests
form an unranked, benchmark/time/session/adjustment-aligned group matrix
from P2 research previews. Input periods now carry original
`period_start`, `period_end`, explicit broad-market benchmark ID,
session basis and price-adjustment basis (P2 bridge and tests updated).
The scanner reports group RS, coverage bounds and unknowns; issuer and
security overlap are distinct. Duplicate securities/issuers across
groups are NOT independent confirmation. No preview is customer
publishable, ranked, predictive or trade-authorized.

New source-only `engine/sector_theme_regime_timeline.py` + tests take
successive already-retained previews (no new history store) for one
group and same basis. The incumbent `breadth_change` owns paired
true endpoint flips; arrivals/coverage/roster revisions remain separate.
Aggregate positive breadth difference is bounded by
`[lo_after-hi_before,hi_after-lo_before]`, not a CI. Sliding-window
RS changes are NOT acceleration. The tool cannot authenticate original
issued/vintage state from a caller timestamp and advertises
`absence_of_upstream_lookahead_proven=false`. No forecast/alert signals.

This phase is **implementation source, not acceptance**: the additional
P3 tests are committed and registered in the same existing
`leadership-rotation-contract` CI job, but current-head CI and
non-author review have not been observed to conclude. Retain the
prior proven 134-pass source run for its then-exact head only, not as
new P3 proof.

Fresh canonical GMI read on Macro main `ce5201f96f...`
confirms W3B source owner rights and production custody still
unqualified and W3C `SOURCE_UNAVAILABLE:CAPTURE_RIGHTS_UNAVAILABLE`
held; Terminal #868 specific refused integration effect remains held
with NO cross-carrier/account retry. These do not block independent
research source work but DO block live-data/customer proof.

Paper direct route was attempted through the required action family
and returned MCP SSE 429. No exact Paper file/artboard was observed,
no design edit or screenshot, no alternate carrier mutation.
No current independent review was accepted. Do not promote PR #10213
or change existing theme scoring/capital/alert owners on Draft.
Prior source code commit before this handoff:
`ac1c53bcacd2a415c5282e471d021315df7a1dbf`.
**Exact next action**: read fresh PR head, latest CI/fences and one
selected leadership-rotation-contract test-pack result; repair any
actual introduced fail within this same branch, then obtain lawful
non-author review and next qualified real owner source adapter when
GMI source/rights gate clears. No session/job is assumed running.


## 2026-10-30 final P3 quality fence before one exact-head CI

Follow-on P2 proof structure now includes `comparison_basis` with
same `period_start/period_end`, explicit broad-market benchmark security ID,
parent ID, RTH/overnight/session basis and price adjustment basis. Every
member/parent/benchmark observation must match that complete window. Synthetic
counterexamples test mismatches and unknown original period start; the
bridge is still deliberately unqualified research preview.

P3a source `engine/sector_theme_regime_comparison.py` with its tests
compares multiple theme/sector previews only when their entire comparison
basis matches. Identity maps preserve a separate unique `security_id`
count and `issuer_id` count and disclose both across-group security overlap
and issuer overlap, including separate share classes. Distinct overlapping
theme membership is not independent corroboration. Malformed/forged
issuer/security populations and numerical coverage fail closed. No ranking,
customer publication, issuer-adjusted inference or trading authority.

P3b source `engine/sector_theme_regime_timeline.py` with its tests
reads *already retained* ordered owner-preview rows, never creates a new
history, schedule, event, watcher or original issuer. Its common-member
positive-return and uptrend state flips reuse incumbent
`breadth_change`. Missing member coverage and changed membership
revisions do not become true flips. Breadth trend only claimed when
`[lower_after-upper_before,upper_after-lower_before]` identifies a strict
direction. Sliding-window RS is labeled **level change, not acceleration**.
The consumer explicitly disclaims original-vintage authentication and
absence of upstream lookahead. No production metric or forecast proof.

Final scoped static hardening:
- Group scanner checks nested `universe` structure, bounded measured
  return count and complete securities before outputting a row.
- Timeline refuses malformed `evidence`, constituent types and
  incomplete member maps before computing paired flips.
- Group-flow consumer refuses missing/forged authority structure rather
  than raising on it.
- Matching regression tests added in each existing new suite, no waivers.
- Existing `.github/ci/legacy-jobs.yml` leadership-rotation-contract
  code job now owns and executes all new suites once selected.

Last code/test source edit BEFORE this note:
`9052d146b787b005124f6c0d5e8fb0a11041397c`.
This handoff update advances the same draft branch. After it, fetch
the **exact current PR #10213 head** and its queued/in-progress CI and
fences. **Only the prior P1/P1a 134-pass earlier-head result was
observed actually passing.** New P2/P3 suites are source-only until the
current complete test pack returns; no independent review was accepted,
no merge, real feed, valid GMI source entitlement or browser acceptance
proven. Original Fabric manual review denied
`MANUAL_ROUTE_UNAVAILABLE/retry_allowed=false`; never cross-route
replay that action. Paper SSE 429 is transport, not design acceptance.

Next critical step: inspect actual exact-head CI and repair failing suites
on THIS PR only if they exist. Then lawful independent non-author review
and original source owner rights/vintage qualification for one U.S.
theme; keep customer/trade/alert/predictive authority false.
Project root mission remains **MORE_WORK_EXISTS**, with held lanes not
mistaken for completed product. Do not restart main's W1–W5 or bypass
GMI W3B/W3C and Terminal #868 explicit source/effect holds.


## 2026-10-30 exact-source isolated P1–P3 QA and input hardening

On immutable PR #10213 code head
`e4cbdb314b841fa3b78dce314168b13440524f59`
the attended Sol session verified the six new suites in a **separate**
`m2studio` temporary directory
`/tmp/stfi-verify-bc14-20261030`, sourced through the GitHub connector
and kept outside the active `~/Documents/GitHub/macro` worktree.
All 13 engine/test files were matched against source at this exact head
using `git hash-object`: **13 matches, zero mismatches**. This is
independent execution of source tests, not an independent code review.

Command, in the isolated directory, with Python 3 and pytest 9.1.1:
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m pytest
tests/test_sector_theme_factor_intelligence.py
tests/test_sector_theme_regime_fingerprint.py
tests/test_sector_theme_owner_bridge.py
tests/test_sector_theme_regime_explain.py
tests/test_sector_theme_regime_comparison.py
tests/test_sector_theme_regime_timeline.py -q -p no:cacheprovider`
Result: **182 passed in 0.24s, zero failed**.

The first exact-source isolated run returned **172 passed / 1 failed**:
`test_p2c_03_flat_stocks_are_not_described_as_decliners`.
It was a semantic English-narrative wording failure, not evidence of
a numeric breadth miscalculation. The explicit flat-or-negative
explanation was repaired at
`6bc02b07e2432437fa557cbee4aeba59fd95a043`
and the six-suite rerun returned **173 passed**.

A seeded mutation test then varied nested owner packet field types in
P2 ingress, P3a cross-group matrix and P3b chronology. Initially
**38 uncaught TypeErrors / 720 malformed-input mutations**, principally
unhashable `list`/`dict` selectors reaching `frozenset` membership
checks. Source fixes at `ed71df1328e5a6250ba5a37d1dd41fe2360a750b`
and `b06f20ce325b1039f9934f68fb0e0bcb8c1de46b`
add explicit string-type admission before membership/horizon/source
vocabulary comparisons. New P2/P3a regression tests were committed in
`4c7bbd26be0ec16b2fb4dd8bdd3430626f7ea116` and
`e4cbdb314b841fa3b78dce314168b13440524f59`.
The **identical 720-mutation seeded sweep now returns zero uncaught
exceptions**; newly authored bad-packet cases contribute to 182 passed.
This is a bounded adversarial sample, not exhaustive correctness proof.

Current hosted CI at `e4cb...` was in progress, not conclusively
green, before this handoff edit. **This handoff write advances the head
again**, so successor must inspect exact new-head CI/fences, read the
selected `leadership-rotation-contract` pack outcome and repair any
newly evidenced failures only. No CI waiver. Draft/Hold, no accepted
non-author review, no Paper artboard, no real GMI owner source entitlement,
no signed-in source-to-browser acceptance, no historical predictive
qualification, no trade/alert/customer authority. The original Fabric
manual review route denial still bars unchanged replay.

Follow-on: when legitimate GMI owner rights/PIT/identity and quote
vintage receipts exist, compose one true U.S. theme group through this
read-only P2 bridge and incumbent Sector Central consumer, then obtain
user-path proof and independent review. Do not substitute mutable current
rosters, synthetic fixtures or owner-**claimed** receipts for authentic
as-known evidence. No source or product release occurs from this QA
checkpoint. Mission remains **MORE_WORK_EXISTS**.
