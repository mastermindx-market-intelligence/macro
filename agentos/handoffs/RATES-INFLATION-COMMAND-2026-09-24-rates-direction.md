---
workstream: WS:RATES-INFLATION-COMMAND
session: claude/rates-direction-20260924-sol-001
model: sol
prs: [7909]
ended_because: context_budget
mission: >
  Deliver Chairman-authorized short/medium-term Treasury direction, swing and
  jump-risk intelligence through incumbent RIC, source, evaluation and transmission owners.
state_before: >
  RD1 daily endpoint construction failed its baseline. Chairman supplied a two-hour
  yield chart and oscillator source. Formulas and an intraday source were bound,
  but no real-market comparison of those supplied formulas existed.
changed:
  - path: research/rates_direction/SWING_PROXY_PILOT_V1.md
    what: Freeze a non-promotable proxy feasibility comparison without claiming native Pine/TVC parity.
  - path: research/rates_direction/swing_proxy_pilot.py
    what: Existing-capture consumer, closed/stub/missing bar handling, delayed observed-session targets and purged forecasts.
  - path: research/rates_direction/swing_proxy_extended.py
    what: Unchanged-rule expanded replication with exact synthetic walker parity and earlier/seen-overlap partitions.
  - path: data/trial_ledger.jsonl
    what: Preserve prefix and append nine pilot plus nine expanded configurations to ric_swing_proxy_v1, eighteen cumulative.
  - path: research/rates_direction/SWING_PROXY_EXTENDED_RESULTS_2026-09-24.md
    what: Retain every primary comparison, sample and denominator limit, and no-promotion conclusion.
  - path: agentos/decisions/DEC-RIC-UPLOADED-CROSSOVERS-NO-PROMOTION.md
    what: Refuse predictive/risk authority while leaving new early-phase/reset hypotheses open.
verified:
  - claim: Both registered comparisons executed on the original Studio.
    command: >
      python3 research/rates_direction/swing_proxy_pilot.py run --capture <original-3mo> --output <frozen-18841b8>;
      python3 research/rates_direction/swing_proxy_extended.py run --capture <original-2y> --output <extended-975259d>
    result: Processes35332 and64919 completed; pilot123 origins/110 scored; expanded1870 origins,1597 primary scored,243 overlap scored.
  - claim: Frozen rules, chronological training and synthetic invariants pass.
    command: >
      python3 -m pytest tests/test_rates_direction_research.py tests/test_rates_swing_proxy_pilot.py
      tests/test_rates_swing_proxy_extended.py tests/test_trial_ledger.py tests/test_validation.py
      -q --tb=short --disable-warnings
    result: 75 passed,16 warnings, process67910; final-targeted-tests.log in original evidence root.
  - claim: Saved forecasts reproduce scores and preserve trial accounting.
    command: Recompute model/partition Brier from saved rows; verify frozen hashes, strict training cutoffs and original ledger prefix plus suffix.
    result: Same-author audits37761/65602 PASS; zero new fits/trials; nine plus nine append-only rows, family total18.
unverified:
  - claim: Exact Pine/TVC replication and actual chart override settings.
    what_would_verify: Native exported indicator golden rows and matching TVC source/session/closed-bar inputs.
  - claim: Historical first-known data, prospective skill and equity decision benefit.
    what_would_verify: Owner source clocks, immutable forecasts evaluated after outcomes, and separate equity-baseline incremental test.
  - claim: Independent review, exact-final-head hosted acceptance, merge and production integration.
    what_would_verify: Qualified independent verdict, concluded applicable checks, lawful release, actual RIC/machine path and required browser proof.
unresolved:
  - All seven additions lost to trend/volatility on expanded primary; do not promote.
  - Primary MPR has only37 resolved non-overlapping episodes, below50 floor; this does not test all waveform methods.
  - RD2 policy constituent/roll attribution remains separate, not applied or replaced here.
  - HS1's previously proven date/bear-baseline defects remain unrepaired and its old report disputed.
next_actions:
  - Review exact current PR and retained results independently without repeating frozen fits.
  - Register a new causal early-phase/impulse-reset comparison against the frozen crossover benchmark before evaluating it; all examined history stays seen.
  - Bind native indicator exports and TVC clocks for exact replication through the existing Terminal source owner.
  - Advance existing RIC/Transmission prospective consumers only through their own release and no-promotion gates.
do_not_redo:
  - Do not rerun/tune RD1, small pilot or expanded replication to find a winner; preserve eighteen wave configs and forty-eight RD1 configs.
  - Preserve original carrier, immutable captures, pre-outcome freezes, all results and ledger prefix.
  - Do not modify or self-release held7418,7400,7521,7593,7320,7877 or Mastermind769; preserve completed A/B/C studies.
  - Do not install research-reference formulas as a second production indicator owner or add another collector/evaluator/ledger/control plane.
danger_areas:
  - Yahoo ^TNX is a proxy, not verified TVC:US10Y; percent-yield scaling is explicit provider convention, not raw Cboe index identity.
  - Closing stubs are40min, not full2h; overnight paths are unobserved; date labels are not historical availability receipts.
  - No-hit/ambiguous/censored cases stay visible; neither overlapping origins nor non-overlapping episodes are independent samples by definition.
  - Native Pine seeds/warmup and actual chart settings remain unverified; these are supplied-default research formulas.
  - A yield downswing is not automatically equity risk-on; no equity strategy or return was tested.
decisions: [DEC:RIC-RATES-DIRECTION-PROGRAM, DEC:RIC-RD1-NO-PROMOTION, DEC:RIC-WAVE-PHASE-IS-A-SEPARATE-TARGET, DEC:RIC-UPLOADED-CROSSOVERS-NO-PROMOTION]
---

# Current cumulative continuation

FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION
MISSION_COMPLETE: false
CAPABILITY_STATE: BUILT_NOT_PROVEN

Boundary: two preregistered comparisons and saved-row audits are complete. A new
phase-feature construction/native replication is a different scientific unit,
not a rerun or selected winner. The parent and production acceptance remain open.

## Authority and custody

Current Chairman end-to-end delegation and indicator test request remain valid.
Protected procedure Mastermind819abc8c23609cdded2b33f6e1bfc7854bd5c847,
Skillpack1.0.1/bootstrap1; required procedure blobs freshly matched.
Original workspace:
/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/rates-direction-20260924-sol-001
Branch claude/rates-direction-20260924-sol-001 / PR7909. Keep Draft/HOLD, no automatic
merge. This carrier does not grant custody of held siblings. Containing immutable
revision and GitHub readback identify the current checkpoint.

## Immutable evidence

RD1 freeze8796829eea9fe8792a73155f64d5c1dbe83ae3b6:48 configs, richer endpoint
candidate4.3034% worse than no-change,11/12 cells lost. Preserve source/results and
post-outcome entrypoint repair history; no repeat was performed this turn.

Small swing freeze18841b8f37af5a0257b1c08df78e5ab3eb53a8bb at14:15:23.690573Z,
published pre-outcome.256 bars,123 origins,110 scored. MPR no improvement; P+R+1.71%
on six episodes never accepted. Result6fbbd6b33f21d729fe84daece245c177ce7aa246
pushed successfully on original process41775.

Expanded freeze975259d0f78b090b8941af5e5168a906d39a7905 at14:26:10.695092Z,
published before registration/outcomes.2004 slots/2003 valid,501 closing stubs;
1870 reconstructed origins. Primary1597 scored across401 dates:473up/483down/
641no-hit, plus4ambiguous;13boundary origins excluded. Seen overlap243 scored,
13censored. All seven additions lost to trend/volatility Brier0.665530:
M-0.533%,P-0.335%,R-0.975%,MP-0.070%,MR-0.256%,PR-0.575%,MPR-0.026%.
Primary MPR37 resolved episodes. No predictive, portfolio or trade authority.

Private evidence root:
/Volumes/Mastermind/evidence/rates-direction-20260924-sol-001/swing-proxy-v1/
Small:frozen-18841b8; expanded:extended-975259d.
Expanded raw:longer-source-preflight/tnx_2y_raw.json,
SHA2561dc7e9121fd6aa36c5019beba303b629257eb1cab752ae937e4cef1aa8161b76.
Expanded predictions SHA256f97e2771ece94241c5d1f6f4e46a1519414034cc29ffbe077c0a0a592f32790c.
Expanded summary SHA2569d3339455075f28e1954a38f284a74c07df2dcdb23c14d989bce442d5b80ba1b.
Original3mo remains in uploaded-formula-source-probe-20260924/tnx_raw.json under
the parent evidence root; SHA256687b93d52beeb141dbfc3ea3eff787b67da7b36daa8effedc19568cbe544d070.

## Effects and exact continuation

No child, worker, watcher, automatic wake or live forecast exists. Tests and both
studies terminated. Technical call failures were reconciled on the original
carrier. One checkpoint overwrite was rejected for omitted explicit mode; exact
readback preserved the old file and explicit-mode replacement supplies this
cumulative update. No safety denial was evaded and no unknown effect is discarded.
Studio terminal/file writes are available; obsolete read-only claims do not apply.
Raw vendor payloads/third-party source are not committed to public evidence.

Resume from this checkpoint/results, not older bootstrap chains. Frozen CLIs
intentionally refuse duplicate registration. Native qualification and independent
review remain owed. The next new candidate needs a distinct hypothesis/freeze/
TrialLedger entry, not a rewrite of negative results. Intended resume: current
program or fresh Chairman-assigned session after same-source reconciliation.


## Continuation: phase/reset technical hypothesis evaluated and not promoted

Fresh protected procedure for this continuation: Mastermind
819abc8c23609cdded2b33f6e1bfc7854bd5c847, Skillpack1.0.1/bootstrap1.
Current source carrier remained PR7909 / claude/rates-direction-20260924-sol-001;
unexpected branch movement was reconciled before new effects and was the prior
completed swing work, not an unresolved modifier.

A distinct seen-history phase/reset study was frozen before opening outcomes at
8e6936cfa4218188cb366c848b1fa83005af5b07, 2026-09-24T15:01:12.467332Z.
It used the already-preserved two-year ^TNX capture
1dc7e9121fd6aa36c5019beba303b629257eb1cab752ae937e4cef1aa8161b76 and
registered exactly7 new configs in family ric_swing_phase_reset_v1. History was
explicitly marked seen by the prior program; no prospective or holdout claim.

Primary discovery partition:1597 scored origins /401 source dates. Incumbent
five-bar trend/vol Brier0.665530. EMA20 broad-trend/vol Brier0.669350,0.574%
worse. SHALLOW_MPR primary had3 active origins,1 resolved non-overlap episode,
0 directional successes and exactly zero Brier improvement versus the weaker EMA20
baseline. None of seven candidates reached50 resolved episodes. P_RESET +0.049%
and PR_RESET +0.036% versus the weaker phase baseline were tiny, underpowered and
non-significant; neither beats the incumbent baseline. Same-author audit recomputed
all partition/model Briers, normalized probabilities, purged clocks, unique origins,
ledger prefix and seven-row suffix. Independent review remains absent.

Do not tune these technical phase/reset thresholds on the same seen source or promote
a post-result directional subset. Preserve DEC:RIC-PHASE-RESET-NO-PROMOTION and the
prior crossover no-promotion ruling. Oscillator phase remains eligible only as
context/incremental timing in a materially different hypothesis.

New scientific frontier: macro-driver-conditioned rates direction. Build on incumbent
RIC sources/owners for policy-path repricing, real-yield/breakeven decomposition,
growth/inflation surprise state, event density, Treasury auction/supply context and
cross-asset response. The next model must compare those driver states against the
existing trend/vol baseline and only then test oscillator phase as incremental.
Preserve RD1, crossover and phase/reset null results; no live forecast, equity-risk
switch, alert, rank, size, gate or trade authority exists. Parent mission incomplete.


## Continuation: driver-conditioned rate-shock transition is also null

Procedure pin remains Mastermind 819abc8c23609cdded2b33f6e1bfc7854bd5c847,
Skillpack1.0.1/bootstrap1. Same research carrier PR7909.

A materially different daily driver-transition construction was frozen before its
outcomes were opened at cc3b56c1e5c30d1a323f114d460a20315003c599
(2026-09-24T15:14:13.304403Z). It asks whether a large five-session DGS10 impulse
is more forecastable once its real/breakeven composition, release-basis PIT
Kim-Wright term premium, HY/OIL/2s10s state and recent incumbent Treasury-auction
absorption are known. The motivating September2026 event is excluded; evaluation
ends 2025-12-31. Rolling ZQ/SOFR policy paths are explicitly held because RD2 has
not yet separated constituent repricing from contract reweighting.

Run evidence directory:
/Volumes/Mastermind/evidence/rates-direction-20260924-sol-001/rate-shock-driver-v1/frozen-cc3b56c

89 non-overlapping shock events produced59 forecasts after warm-up. The primary
2022-2025 partition has57 scored events and meets the >=50 floor:24 continuation,
22 reversal,11 no-hit. Impulse-direction Brier=0.665101. Decomposition=0.672208
(-1.068% relative); PRIMARY decomposition+PIT term premium=0.682122 (-2.559%);
crossasset=0.691956 (-4.038%); full+auction=0.700381 (-5.304%). All added driver
layers degraded the baseline. The earlier development partition contains only two
forecasts after warm-up, so its numerically lower driver Brier is not regime evidence.
DEC:RIC-SHOCK-DRIVERS-NO-PROMOTION preserves the null.

Same-author integrity recomputed every model/partition Brier, verified59 unique
forecast origins, normalized finite probabilities, purged training clocks, exact
pre-registration ledger prefix and exactly5 appended configs in family
ric_rate_shock_driver_transition_v1. Independent review remains absent.

Scientific frontier is now sharper: vulnerability/state is not the same as catalyst.
Do not tune the rejected technical or categorical driver constructions on seen
history. Next investigate the existing macro-release forecast + release-playbook
owners for a genuine pre-release catalyst expectation and event response. Current
release_forecast surprise_skew is projection-vs-naive-prior, NOT market-consensus
surprise; expectation_read can compare to available external expectations but the
captured history is only mid-2026 onward and often one-source. Preserve that
distinction. RD2 constituent policy repricing remains a separate independent
source-quality dependency. No live forecast/risk switch/trade authority.


## Continuation: prospective CPI catalyst-to-rates shadow frozen and registered

Procedure pin remains Mastermind 819abc8c23609cdded2b33f6e1bfc7854bd5c847,
Skillpack1.0.1/bootstrap1. Carrier remains PR7909 /
claude/rates-direction-20260924-sol-001.

After the technical and categorical-driver nulls, the next distinct hypothesis was
moved to the missing causal layer: pre-release catalyst expectation -> realized CPI
catalyst -> Treasury response. The source audit found two material constraints:
historical expectation_read rows examined through the freeze use only Cleveland Fed
nowcast, not a multi-source market-consensus series; and legacy champion target epochs
remain evaluation-excluded by DN-004. DSC:RIC-EXPECTATION-READ-IS-NOT-MARKET-CONSENSUS
preserves this source law.

A prospective-only protocol was frozen at commit
fed5da304400c6775a1c50734a35ef806b64e034, freeze timestamp
2026-09-24T23:49:47.727759Z. It creates no new ledger or producer. It consumes only
existing release_forecast forward-ledger rows:
- coherent_ridge_v1 / alfred_same_release_vintage_proxy_v1 CPI headline+core
  shadow_projection rows with exact calendar T-1 cutoff;
- the same existing champion row ONLY for frozen expectation_median + source names,
  never for legacy forecast math;
- incumbent DGS10 history for later h0/h1/h5 grading.

Headline+core are one CPI event. Component gap is coherent point minus the exact
stored expectation median; +/-0.05pp is the frozen HOT/COOL threshold. Conflicts or
missing inputs abstain. Only release_date >2026-09-24 is eligible. Primary DGS10 h0
direction uses +/-2bp; h1/h5 are secondary. Baseline is prior five-observation DGS10
direction on the same active events. Floors: >=12 eligible events and >=8 active for
descriptive evaluation; >=24 eligible before any promotion review can be requested.
No live RIC/equity/alert/rank/size/gate/trade authority.

TrialLedger family ric_cpi_catalyst_rate_shadow_v1 was registered exactly once at
2026-09-24T23:50:17.516517Z, config hash4a5ee1dacd021f48. Prefix hash matched the
freeze and literal_n=1. Immediate report found2 joined pre-freeze events, both
excluded, and ZERO prospective events / ZERO matured outcomes. Therefore there is no
performance claim yet and no historical backfill can satisfy the future sample floor.
Same-author integrity verifies frozen files, ledger prefix and zero-outcome boundary;
independent review remains owed before any stronger authority.

Independent rate-policy lane remains separate: PR7923 qualifies matched-contract
policy repricing versus roll; PR7940 stacks prospective retention into the incumbent
rates_command forward ledger and MUST NOT be duplicated here. Continue by reviewing
that existing lane rather than building another policy path, while future CPI outcomes
accrue through the incumbent Release Radar producer. Parent mission remains incomplete.


## Continuation: independent RD2 review found SR3 source blocker

Same procedure pin: Mastermind 819abc8c23609cdded2b33f6e1bfc7854bd5c847,
Skillpack1.0.1/bootstrap1. The parent #7909 carrier was clean and exact local/remote
at 034264fce90d04770a871132cc9a842f2d49dba0 before this record update.

Independent CEO review of sibling PR7923 exact head
dbf8d03ed4f2a29ea349bb37a23b9048f18bc2db found a release-blocking SR3
contract-identity error. collectors/rate_futures.gen_contracts starts quarterly
generation from the civil as-of month and therefore drops the still-live March SR3
contract throughout April and May. The same candidate's
engine/rate_futures_repricing.reference_period correctly reports March2026 SR3 as
2026-03-18 through 2026-06-17. Exact-head reproduction showed:
- 2026-03-19 -> first requested 2026-03
- 2026-04-01 -> first requested 2026-06 while March reference quarter remains active
- 2026-05-15 -> first requested 2026-06 while March reference quarter remains active
- 2026-06-16 -> first requested 2026-06 while March reference quarter remains active

Because producer and verifier share the omitted contract set, digest/weight
reconstruction can remain internally consistent while the live quarterly strip is
incomplete. ZQ is not rejected by this finding; the blocker is SR3 quarterly contract
identity and any claim that the full two-family source is qualified.

REQUEST_REPAIR was posted on the existing #7923 GitHub carrier:
https://github.com/mastermindx-market-intelligence/macro/pull/7923#issuecomment-5824269359
No #7923 source edit was made by this reviewer. Required repair is to retain the
active SR3 reference-quarter contract through its actual third-Wednesday interval,
with boundary regressions, while preserving ZQ, New York/capture clocks and authority
ceilings.

Current-base compatibility was independently checked against macro main
25fb8fa805d611727078f65626f2c3b0388070b3. A conflict-free local merge tree
274e03b7ccee56eefbf28c44d3a3910e744706cd was produced and the selected
test_rates_command + test_fed_path + test_yield_momentum suite passed147 tests with
301 warnings. This does not waive the semantic blocker.

Downstream PR7940 must remain dependency-held on an accepted #7923 repair. Do not
duplicate its forward-ledger retention implementation. Independent research may
continue on disjoint hypotheses. The next medium-term scientific lane is a
curve-system forecast (dynamic level/slope/curvature versus no-change), not another
oscillator or post-impulse state-stack variant.


## Continuation: dynamic Treasury curve model reconciled and null

Same carrier PR7909. An in-flight dynamic-curve operation was reconciled before any
new research effect: freeze commit 08ddb2c550ec84a4de9c780121a938dc0d02a1cf had
already registered its 12 TrialLedger rows and written complete evidence to
/Volumes/Mastermind/evidence/rates-direction-20260924-sol-001/curve-system-dns-v1/frozen-08ddb2c5.
No matching process remained active; the operation had completed rather than being
restarted.

Primary 2021-2025 h20 level MSE: no-change740.153, direct AR774.234, DNS diagonal
798.870, DNS-VAR PRIMARY881.014. Primary relative MSE reduction=-19.03%, therefore
failed. H5 and h60 also lost on MSE; 2010-2020 context likewise favored no-change.
Same-author integrity verified131464 unique horizon/model/origin rows, finite normalized
probabilities, purged fit/calibration clocks, exact primary MSEs, TrialLedger prefix
and exactly12 appended configs. Independent review absent.

Preserve DEC:RIC-CURVE-SYSTEM-NO-PROMOTION. Do not retune lambda/lags or switch the
governing objective on the seen primary period. No live forecast/risk/trade authority.

The highest-leverage frontier remains catalyst expectation and market response plus
RD2 constituent-qualified policy repricing. A prospective CPI catalyst shadow is
already frozen/registered under this carrier; do not duplicate it. Next recover its
exact rule/clock and build the complementary event-response/driver consumer or advance
RD2 if that prospective lane is waiting for natural-time outcomes.


## Continuation: dynamic curve-system point forecast rejected; direction-only lead isolated

Same procedure pin: Mastermind 819abc8c23609cdded2b33f6e1bfc7854bd5c847,
Skillpack1.0.1/bootstrap1. Parent carrier remains #7909 /
claude/rates-direction-20260924-sol-001.

A materially distinct curve-system hypothesis was frozen before opening its outcomes
at commit 08ddb2c550ec84a4de9c780121a938dc0d02a1cf,
2026-09-25T00:04:18.258662Z. It uses fixed Nelson-Siegel lambda0.0609/month on
DGS1/2/3/5/7/10, direct horizon factor dynamics at5/20/60 common observed-date
intervals, strict fit/calibration purging, and a no-change benchmark. No parameter
search or regime/oscillator input is included.

TrialLedger family ric_curve_system_dns_v1 registered exactly12 configurations
(4 models x3 horizons). Private evidence:
 /Volumes/Mastermind/evidence/rates-direction-20260924-sol-001/curve-system-dns-v1/frozen-08ddb2c5/ .
Prediction SHA29fd579355ff8d9b3424ecc5ef3e65822780ee7a5376b914483917ef65666594;
summary SHA8614e219879331571fca6dd9e07df4d3777eaadbb4497c420542026b8bf2dcde.

Predeclared primary 2021-2025 h20 result is a null: no-change MSE740.153bp^2,
DNS-VAR881.014, a19.03% deterioration. Every nontrivial point model lost to
no-change at h5/h20/h60. Preserve DEC:RIC-CURVE-SYSTEM-NO-PROMOTION and do not
retune lambda/lags/windows on the opened primary period.

A predeclared secondary direction-probability diagnostic produced one narrower
hypothesis only: direct AR and DNS-diagonal residual-calibrated direction Brier
improved at h20/h60 in BOTH declared periods, despite worse point MSE. DNS-diagonal
h20 improvement was+0.80% in2021-25 and+0.81% in2010-20 context; h60 was+9.10% and
+6.97%. h60 has only20 primary and45 context non-overlapping windows, so this cannot
be promoted. At h5 the same DNS direction diagnostic worsened in both periods.

Same-author integrity recomputed both period summaries exactly from131,464 saved
prediction rows, verified unique model/horizon/origin identities, finite normalized
probabilities, fit target end < calibration start < calibration target end < origin,
the pre-registration TrialLedger prefix, and exact12-row family suffix. Independent
review remains absent.

Scientific interpretation: random-walk remains the stronger yield-LEVEL baseline;
the remaining curve lead is only whether longer-horizon factor state improves
DIRECTIONAL probabilities after magnitude calibration. A successor must be selected
prospectively and use an existing lawful forward-evidence owner; do not create a
second generic forecast ledger to rescue the retrospective result.

Latest retrospective model output at corrected-history origin2026-09-22 is research
context only, not an issued/accepted forecast. Do not cite it as live direction
authority. Parent mission remains incomplete. Short-term catalyst/policy lanes remain
the higher-priority path for actual near-term direction.


## Continuation: prospective official inflation catalyst -> rates response shadow frozen

Procedure pin advanced compatibly to Mastermind
a29161fa0a44cca9927afe042b5f7ea25aae1736, Skillpack1.0.1/bootstrap1.
Parent carrier remains PR7909 / claude/rates-direction-20260924-sol-001.

A distinct prospective transmission shadow was frozen before any eligible outcome at
commit 41d16e1ecfd877f95871d2b8bdb116a97c0d53f4,
freeze timestamp 2026-09-25T01:25:00.250611Z, then registered exactly once in
TrialLedger family ric_inflation_catalyst_rate_response_v1
(config 675da315accb83ab).

Question: after an official CPI/PCE print is actually known, does the initial print
relative to the exact T-1 Release Radar expectation context provide a useful
same-session / near-term DGS10 directional prior?

The shadow creates no source or ledger. It reads the incumbent
data/release_forecast/forward_ledger.jsonl and data/fred/DGS10.parquet. Expectations
must be exact calendar T-1 champion rows with finite expectation median and sigma.
Actuals must be official_published_metric / official_release_document receipts,
deduped across model score rows, with timezone-aware observation no later than
16:00 America/New_York on release day. Late-captured historically correct actuals
cannot masquerade as an actionable h0 signal.

CPI and PCE each form one headline+core announcement event. Component standardized
actual surprise uses the incumbent +/-0.35 expectation scale; conflicting headline/
core or both-inline events abstain. Only releases strictly after 2026-09-24 count.
Primary outcome is release-day DGS10 close vs prior close at +/-2bp; h1/h5 cumulative
moves are secondary. Daily h0 is explicitly a release-day close proxy, not an
08:30 intraday causal impulse. Baseline is prior five-observation DGS10 direction on
the same active events. Floors:12 signal-observable prospective events and8 active
for descriptive review;24 signal-observable before any promotion review request.

Initial post-registration report correctly has0 prospective events /0 observable /0
active; five joined pre-freeze source-sanity events are excluded. Thus no eligible
outcome was opened before freeze/registration.

Material source discovery: Release Radar already owns append-only row_type=reaction
rows, so do NOT create another generic reaction ledger. However its current reaction
producer intentionally emits a partial row when any reaction field is available;
recent rows often preserve null DGS10 h0/h1 while SPY/spread fields are present.
Because the row is then idempotently keep-first by release/period, those null DGS10
fields are not a sufficient rates-response evidence owner for this new shadow. The
shadow therefore reads the incumbent DGS10 series directly after maturity without
modifying or replacing Release Radar's reaction rows.

The pre-release CPI catalyst shadow remains separate/immutable. RD2 PR7923 has an
independent repaired-head PASS review receipt at comment5825034742; downstream
prospective-retention PR7940 has semantic PASS / dependency-hold at comment5825046561.
No merge/deploy was performed here. Future policy-repricing confirmation is a
separate candidate only after that source is lawfully live.

DO_NOT_REDO: RD1 endpoint models, uploaded crossover study, phase/reset study,
post-shock categorical driver stack and DNS point forecast remain null. Do not tune
those opened histories or backfill this prospective shadow to meet its floor.


## Continuation: direct yield month-end translation passes, but remains context-only

Current protected procedure pin remains Mastermind
a29161fa0a44cca9927afe042b5f7ea25aae1736, Skillpack1.0.1/bootstrap1.
Parent carrier remains PR7909 / claude/rates-direction-20260924-sol-001.

The pre-existing d2_rates_calendar_flows V3 month-end extension effect had already
passed on TLT/IEF and later LQD, but had never been translated directly into the
rates-direction target. A direct DGS source-translation amendment was frozen before
opening its outcomes at cfef07d2424a27604698c65eed03df3e0fe8c747,
2026-09-25T01:33:15.401908Z.

It appended exactly8 configs to the SAME d2_rates_calendar_flows TrialLedger family,
moving literal width13->21. Frozen modern interval2007-01-01..2026-09-22 admits236
complete months through2026-08-31. All DGS2/5/10/30 raw and same-month-excess cells
passed negative-sign, HAC t<=-2, BH q<=.10 and negative split-half gates.

Headline DGS10:
- raw last-day change -1.186bp, HAC t=-3.267, p=.0011, BH q=.0015
- excess vs other same-month daily changes -1.242bp, t=-3.276, q=.0015
- chronological halves raw -1.534bp / -0.839bp

Pre-ETF historical context Feb1962-Jun2002: DGS10 raw -0.703bp, t=-2.581;
excess -0.745bp, t=-2.614; both chronological halves negative. Context only,
not a promotion rescue.

Source-clock qualification: all236 modern DGS10 event dates exactly match the
incumbent engine.rebalance_calendar.month_end_sessions() owner through Aug2026.
No new calendar owner is needed.

Same-author raw reconstruction reproduced all primary counts/means and verified the
original TrialLedger prefix plus exact8-row amendment suffix. Evidence:
registration deed993281afeeabdb5f86f8554ddf65794eae45e0a3de23a041ee88f6626ff7;
summary 7ecd8a9d89b24c45da83603991d2eb6a8b7bede9dbe109adc8bf0a6f7c0aa20c.

POST-RESULT diagnostics are important but are not new selected rules:
- quarter-end DGS10 raw +0.295bp, t=.502; no aggregate lower-yield edge there
- non-quarter month-end -1.918bp, t=-4.370
- 2022-2026 raw only -0.250bp, t=-.387; excess -.536bp, t=-.767
- trimming largest5% absolute month-end moves still yields -.787bp, t=-2.688
- full-family-width Bonferroni upper bounds remain <=.0315 for all8 new cells

DEC:RIC-MONTH-END-EXTENSION-CONTEXT-ONLY therefore withholds score/trade/equity-risk
authority. The effect may be retained as source-backed display/context and future
prospective-validation input, but the post-result non-quarter subset cannot be
promoted. Do not create a separate calendar signal plane; reuse engine.rebalance_calendar
and RIC if/when display integration is admitted.

Next scientific/product action: freeze a generic forward-only month-end DGS10 shadow
from the known aggregate sign, with quarter-end merely tagged diagnostically rather
than changing the sign, so current relevance is resolved without backfitting the
2022-2026/quarter-end cuts.


## Continuation: generic month-end DGS10 prospective shadow is frozen and registered

Following the context-only ruling, the ORIGINAL aggregate month-end sign was frozen
forward without selecting the attractive post-result non-quarter subset.

Freeze commit 3dde99f9fb784cf74e625e497b7757e66ca0cd8e,
freeze timestamp 2026-09-25T01:40:25.269311Z.
TrialLedger family remains d2_rates_calendar_flows; exactly1 prospective config
8c3ba77ccc47b7bd was appended, moving family literal width21->22.

The exact24-event schedule is frozen from incumbent engine.rebalance_calendar:
2026-09-30,10-30,11-30,12-31; monthly through2028-08-31. Generic signal is DOWN
DGS10 on EVERY frozen month-end. Quarter-end is diagnostic only and cannot alter
the sign. There is no subgroup repair, threshold grid or backfill.

Freeze source state: DGS10 latest2026-09-22, canonical finite date/value prefix digest
8f3f8e7ced9629996a187a1db319f40a18b8f2260d6ef308c087d214e07dc93b.
Initial registered report:24 scheduled /0 matured /24 pending; prefix unchanged;
no eligible outcome was opened before freeze/registration. First event2026-09-30.

Outcome per event: exact frozen event-date DGS10 close vs prior finite close, plus
excess vs prior same-month daily changes. Missing frozen event date is never
substituted. Descriptive floor12 events; promotion-review floor24. At24, unchanged
retrospective gate requires raw+excess negative means, HAC t<=-2 and both
chronological halves negative. authority=false.

No new scheduler/collector/evidence ledger was created. Current future DGS correction
vintages are not yet first-observation-custodied; stronger promotion will additionally
need an accepted first-capture/prospective evidence owner, preferably through the
existing RIC forward path rather than a new ledger.

DO_NOT_REDO/SELECT: do not switch v1 to non-quarter month-ends after seeing the
post-result diagnostic. Do not alter signal based on Sep30 being quarter-end/PCE.
Those facts are context for interpretation, not permission to change the frozen rule.
