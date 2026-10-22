# Market Navigator: product, research and delivery master plan

Version 1.0 - 22 October 2026. Program owner: the assigned Mastermind CEO Integrator.
Status: implementation underway; not a shipped or validated trading system.

## 1. The product decision

Build a coherent decision experience inside the existing Macro dashboard and Terminal,
not a new scorecard, another data platform, or an imitation of an analyst's personality.
A user should understand the environment, the decision area, competing paths, the
observation that distinguishes those paths, and the appropriate next step. Waiting is a
useful output. Direction, volatility and entry readiness are different concepts.

The initial inspiration is Michael Bento's conditional, cross-market synthesis. His
performance has not been established from a complete contemporaneous archive. The
supplied case is an explanatory example, not a market-data source or a training set.
Do not reproduce his identity, imply endorsement, redistribute his archive, or copy
proprietary vendor graphics. General mechanisms and independently tested hypotheses,
not an analyst's confidence or writing style, are the reusable intellectual product.

### User promise and measurable completion

The primary user is a self-directed investor or swing trader trying to answer:
"What matters now, what would change the picture, and am I early, late, or waiting?"
The intraday expert can inspect expiry/clock detail without imposing it on everyone.

Product acceptance requires all of the following, not merely a merged backend:

1. On desktop and mobile, a user can identify the state, one key uncertainty and the
   next observation without reading a methodology report. Proposed usability target:
   at least 8 of 10 representative task participants succeed within 30 seconds.
   This is a target, not a study result or guaranteed user performance.
2. The same symbol, horizon and knowledge cutoff produce consistent Macro and Terminal
   explanations. The canonical market verdict is consumed, never recomputed here.
3. Every directional hypothesis has a horizon, explicit trigger, invalidation and
   deadline. A condition currently true does not claim an earlier crossing or a trade.
4. Missing, delayed, corrected and contradictory evidence remain visible. A new file
   timestamp cannot make old contents current. Estimates never become observations.
5. A user can inspect the strongest contrary evidence, save through the incumbent
   personal-state owner, revisit what changed, and inspect the original hypothesis.
6. Forecast quality, trade-expression quality and user comprehension are measured
   separately. No predictive label or trade authority is earned by attractive design.
7. Signed-in real-path proof covers shared authentication, approved data rights,
   existing save/watch/alert contracts, response failure and refresh behavior.
8. Paper designs, implementation and dark/light x EN/ZH x 1440/390 evidence agree.

### Architectural ruling

Navigator is an **interpretation and conditional-path consumer**. It has no independent
regime, signal, portfolio allocation, alert escalation, execution or publication authority.
Research uses the existing evaluation and Market Memory owners. No new database,
message bus, scheduler, retry service, identity service, feature store or LLM agent swarm
is required for the initial product.

Current source-law pin: Mastermind protected master
`c9cbee5569ba50e30e28715d930809061a169517`, compatible skillpack 1.0.1.
Implementation census baseline: Macro main
`aad27efd2f5a0bcc09f7278807dff6862839e398`.

Preserve `DNR:KILL-REGIME-SCORECARD`, `DNR:KILL-POSITIONING-FUSION`,
`DNR:KILL-FUSED-COMPOSITE`, `DNR:KILL-LLM-ORIGINATION`,
`DNR:KILL-OFFHORIZON-VERDICTS`, `DNR:KILL-PARALLEL-SHOCK-CLASSIFIER`,
`DNR:KILL-PUBLIC-INTERNALS` and existing research-arena exceptions exactly. This plan
is not an amendment to those controls. New hypotheses begin without live authority.

## 2. Reuse map and responsibility

These are source-inspected implementations, not claims of current production liveness.

| Responsibility | Incumbent owner / interface | Navigator work |
|---|---|---|
| Market posture | `engine/market_state.py`, `market_state.v1`, `data/market_state/latest.json` | Read verdict and degradation; do not blend another score |
| Regime axes | `engine/regime_vector.py` | Read categorical context for the declared horizon |
| Shock/driver attribution | `engine/market_drivers.py::snapshot` | Present measured attribution and competing explanations |
| Gamma context | `engine/market_gamma.py` | Preserve sign method, source clock and estimation assumptions |
| Volatility weather | `engine/vol_velocity.py::compute_vol_weather` | Preserve per-chip clocks; do not borrow its display freshness for an entry signal |
| Greek calculations | `engine/greeks.py`, `engine/intraday_greeks.py` | Reuse kernels; test conventions rather than rewrite mathematics |
| Finite hedge scenarios | `engine/options_scenario_surface.py`; strict `engine/options_scenario_admission.py` | Consume qualified finite scenarios; no new dealer-inventory model |
| Historical knowledge | `engine/neuralweb/market_memory.py::AsKnownAtReader` and validator | Read existing point-in-time contexts; no second history/analogue store |
| Identity / calendars | Existing instrument owners and `lib/nyse_calendar.py` | Reference resolved identity, sessions, fixing and corporate-action evidence |
| Publication | Existing Data OS/regime/build owner | Add bounded consumer output only after integration qualification |
| Shared frontend | `_site_nav.html.j2`, `theme.css`, canonical component specimen | Integrate a D-archetype overview and detail workflow |
| Personal saves / alerts | Incumbent user-preferences, user-state and alert owners | Explicit schema compatibility check; no new personal-state or outbox service |
| Analyst acquisition | Existing `engine/marketing/x_intel.py` transport/budget owner | Separate rights-approved research extraction from engagement scoring |
| Organizational continuity | Macro `agentos/` | One workstream, decision record and cumulative continuation |

The inspected Capital Structure saved-scenario PR #9774 is domain-specific. Its
"restore against current generation" principle is useful; its financial scenario
payload must not be silently repurposed for market-path hypotheses. Active Market
Memory PRs #9797, #9779 and #9746 retain their paths and responsibilities. Integration
must consume their accepted contracts rather than modify their in-flight writers.

## 3. System shape

```
Existing licensed/public source owners
        -> identity + clocks + quality + permitted-use receipts
        -> existing feature, market-state, option and event engines
        -> horizon-bound evidence adapters
        -> read-only Navigator composition
        -> existing authenticated Macro / Terminal consumers
        -> existing save / return / alert owners, when admitted

Existing Market Memory <-> registered research and outcome evaluation
                                |
                     accepted evidence references only
                                v
                     Navigator explanation and reliability
```

The first implementation is `engine/market_navigator.py`: a pure, bounded compositor
with no I/O, no persisted lifecycle and all authority flags false. Its condition
operators are a small typed set, not executable expressions. It proves composition
invariants, not market predictability. The initial public projection is a closed
allowlist; routing still owes identity, authorization and data-rights checks.

### Four knowledge classes

- **Observation:** a source-qualified fact available to this consumer by the cutoff.
- **Estimate:** a model output with assumptions, input universe and model version.
- **Hypothesis/forecast:** a bounded future proposition with ruler and evaluation status.
- **Authorized action:** an existing risk/decision consumer's separately admitted output.

No arrow between these classes is implicit. A source citation proves lineage, not
accuracy; a deterministic calculation proves arithmetic under assumptions, not an edge.
An LLM can describe and challenge, but cannot promote a class or originate a score.

### Time and identity contract

Every input needs instrument identity, venue where relevant, currency/unit, source
revision, market observation time, receipt time, consumer-available time, validity end,
bar completion and quality. Operational reads obey:

`observed_at <= received_at <= available_at <= decision_cutoff < valid_until`.

**Adapter warning:** these generic clock names are not a field-by-field mapping to
Market Memory. Its `observed_at` is a capture clock with different ordering. The
lossless boundary and exact verified mismatch are specified in INTEGRATION_CONTRACT.md;
retain the incumbent context or translate by meaning, never by matching field names.

A late revision retains its original market date but cannot be known before its actual
availability. Historical reads use the incumbent `AsKnownAtReader` and validator.
Public reconstruction, current-snapshot backfill and operational point-in-time capture
remain separate evidence classes. ALFRED vintage dates help with revised economics,
but are not minute-level feed receipt timestamps [S2, S3].

Contract expiry is not just a calendar date. Preserve market, timezone, economic
fixing, exercise style, deliverable and multiplier. SPY, SPX and SPXW are not the same
risk unit. A daily price close is not an after-hours quote; an option-chain snapshot
from before earnings must not be recombined as if refreshed after earnings.

## 4. Engine contracts

The engines below are functional responsibilities, not permission to create twelve
new services. Existing owners remain authoritative. New pure adapters are justified
only where the listed consumer capability cannot be obtained through the incumbent.

### E0. Eligibility, freshness and evidence binding

**Input:** existing source receipts and the explicit symbol/horizon/knowledge cutoff.
**Method:** validate units, identity, causal availability, completed bars, entitlement,
source coverage and consumer-specific age tolerance. Quarantine structural errors;
represent ordinary missingness with reason codes. Never coerce missing to zero.
**Output:** eligible observation references plus noneligible reasons and source lineage.
**Tests:** late revision, timezone/DST/holiday, corrected bar, stale series in a fresh
bundle, missing expiry members, wrong currency/multiplier, future availability,
provider outage and rights revocation.

A valid hash is not source authenticity. Owner-issued receipts, their actual verifiers
and authenticated read paths must be used by production adapters. A source receipt
provided by a caller is not sufficient to grant operational qualification by itself.

### E1. Trend and structural location

**Input:** incumbent completed OHLCV bars, adjustment policy and existing trend features.
**Method:** describe price relative to averages, slopes, prior swing structure and
range. Normalize distance by a contemporaneously available volatility/ATR denominator.
Compute slopes over declared past windows; no centered filter that reads future bars.
Treat RSI, MACD, stochastic and AO as one correlated price-derived family initially.
**Output:** location and trend descriptors by horizon; candidate decision zones with
creation/retirement rules; no synthesized directional confidence percentage.

A head-and-shoulders candidate is a parameterized geometric hypothesis, not an automatic
forecast. Freeze pivot detection delay, neckline, breakout tolerance, retest rule and
expiry before evaluation. Do not redraw a neckline after the outcome. Retain failed
patterns. Test increment over simple momentum/location baselines [S4].

**Acceptance:** historical replay reveals pivots only after detection was possible;
partial candles never act as completed closes; normalized features have units and
stable constant-price/zero-range behavior.

### E2. Participation and leadership

**Input:** point-in-time universe membership, constituent price coverage, existing
breadth and sector engines. Use the existing coherent publication path.
**Method:** percent above 20/50/200-day averages, participation change and acceleration,
advance/decline and equal-weight divergence where actually available. Separate
index concentration from broad participation. Report the eligible denominator and
missing constituents; do not silently shrink a broken universe into apparent strength.
**Output:** level, direction, speed, sector distribution and counterevidence to an
index-only interpretation.

A rise to 55% after broad deterioration is different from a fall through 55%. The
proposed 70% health boundary is a hypothesis, not a universal truth. Test the raw level,
its change and a simple level-plus-change model against the exact threshold, without
silently optimizing the latter after looking at results.

**Acceptance:** no survivorship from today's members, no unit mismatch between breadth
percent and fraction, no false acceleration induced by coverage changes, public display
makes limited coverage understandable.

### E3. Historical transaction zones and liquidity

**Input:** qualified prints with event/report timestamps, corrections/cancels, price,
size and trade-condition metadata; existing off-exchange owner.
**Method:** aggregate price zones using a frozen width rule; normalize notional to
instrument-specific volume/liquidity; track age, touches and observed reactions.
Separate tape-observed completed transactions from delayed venue aggregates. A print
is not a remaining resting order or an identified institution's intention.
**Output:** historical activity zones, source class, reaction history and limitations.

Near sister levels should merge under a predeclared distance rule, not disappear from
history when they fail. Test zones against price pivots, round numbers and matched
random levels at equal distance from spot. Test whether repeated touches predict
weakening or strengthening; do not assert depletion without evidence.

**Acceptance:** cancels remove original contribution, late-reported prints are not
backdated as knowable, corporate-action adjustments remain aligned, sparse/free
aggregate data cannot pretend to deliver intraday print-level support/resistance.

### E4. Options positioning and finite hedge response

**Input:** existing chain, trade and contract-reference receipts; exact expiry scope;
OI/volume distinction; explicit assumed/supplied position signs; IV surface convention.
**Method:** reuse the existing Greek and finite scenario owners. For a supplied signed
book with positions q and multiplier m, hedge target is H = -sum(q*m*delta).
Compare finite H at named spot, volatility and time scenarios. Inventory changes and
exercise/settlement are separate model inputs, not implied by delta repricing.

Dollar gamma per 1% move has dimensions `sum(q*m*Gamma*S^2*0.01)`. Other unit choices
need explicit labels. Charm = dDelta/d(calendar time), while some libraries differentiate
remaining tenor with the opposite sign. Vanna IV increments use decimal volatility,
not percent points unless explicitly converted. Finite-difference tests bind conventions.

Calculate all-expiry, ex-0DTE, 0DTE and selected-expiry slices by contract membership,
not by removing a strike. OI and directionalized volume are distinct lenses. Gamma,
charm and vanna computed from one book share lineage and do not count as three
independent confirmations. Positive/negative gamma describes possible hedge feedback,
not up/down direction.

**Output:** conditional hedge-target differences and uncertainty across assumptions;
concentration map; missing-universe/expiry applicability reasons. Never "dealers will
buy/sell X" without actual ownership and execution evidence.

**Acceptance:** every expected contract accounted for; whole-book output refuses
missing members; expiry crossings use incumbent refusal until settlement is modeled;
no artificial TTE floor; fixed-IV and alternative surface sensitivities distinguish
model uncertainty. SPX-risk scenarios cannot be silently labeled SPY-share flow.

### E5. Volatility structure and compression

**Input:** VIX1D/VIX9D/VIX/VIX3M/VVIX and existing realized-vol/surface measures with their
own timestamps and frequencies. Intraday measurements need intraday rights and history.
**Method:** use existing level/change/percentile features. Add clock-conditioned research
normalization where support exists; account for VIX1D's shifting near/next expiry weights
and its business-time basis [S1]. Velocity and acceleration require smoothing and
noise diagnostics, not raw second differences promoted as special predictive insight.

**Output:** separate horizon-appropriate volatility state, curve shape, changes and
price/vol disagreement. Ratio changes must retain numerator and denominator attribution;
VIX falling and VIX3M/VIX rising are not automatically independent evidence.

**Acceptance:** exact 6.88 and 1.12 hypotheses retained in the study; same-clock and
calendar/event alternatives evaluated; no daily OHLC dataset used to validate intraday
entry timing; no low one-day reading directly authorizes a multi-month option position.

### E6. Cross-asset transmission

**Input:** incumbent market_drivers, rate/inflation transmission, credit, FX and commodity
context, with aligned observation windows and economic vintages.
**Method:** consume existing shock classification. Distinguish level from change and
supply from demand interpretations; preserve ambiguity when identification is absent.
Separate contemporaneous attribution from a forecast. A high nominal yield is not the
same as a rising real yield; a dollar rise is not universally bad for every sector.
**Output:** a small set of plausible transmission channels and the observed evidence
supporting or challenging each; sector sensitivity only where an existing qualified
consumer provides it. No new causal-DAG-to-alpha path.

**Acceptance:** synchronized windows; revised macro inputs excluded from prior cutoffs;
no inference of policy intent or geopolitical probabilities by an LLM. A channel that
is explanatory but not predictive remains useful context, not an allocation rule.

### E7. Events, expectations and response

**Input:** source-qualified earnings/releases/news, announced and actual release times,
prior expectations where licensed and available, and contemporaneous prices/options.
**Method:** distinguish the event, surprise relative to expectations and observed market
response. Freeze pre-event reference time and implied-move definition/expiry. Separate
regular-hours, after-hours and next-open observations. News duplicates share one origin.

For earnings, `absolute realized gap / pre-event implied magnitude` is descriptive. It
is not a hurdle a stock must clear. Test underreaction/reversal after controlling for
news surprise, guidance, prior run-up, liquidity and the option book. Evaluate option
profit after IV change, spreads and time decay separately from stock direction.

**Output:** what changed, how price responded, what remains unverified, and response
scenarios. A lack of price reaction can mean prior pricing, uncertain information,
offsetting news or resilience; it does not uniquely imply complacency.
**Acceptance:** source correction propagates, rumors remain unverified, no claim source
is overwritten, no future consensus or revised announcement timestamp in historical tests.

### E8. Evidence families and contradiction handling

**Input:** qualified evidence from E1-E7, source lineage and historical evaluation status.
**Method:** group shared causal/data ancestry. Momentum oscillators form one price family;
Greeks from one inventory assumption form one positioning family. Keep support and
counterevidence side by side. Do not sum colored tiles into a fresh market score.

The first version uses transparent named facts, not learned weights. Any future
conditional interaction must use an already authorized research arena and its
promotion process. Independent sources are not automatically independent information.
**Output:** evidence map, unresolved assumptions, concentration of support, and strongest
falsifier. Numerical forecast probabilities remain absent until the exact target,
horizon and calibration set support them.
**Acceptance:** duplicating an input cannot increase certainty; a new contradictory fact
cannot be silently discarded; missingness reduces what can be asserted, not what is shown.

### E9. Scenario composition and readiness

**Input:** explicit scenario definitions and eligible observation references, existing
market posture and independently admitted setup/readiness outputs where available.
**Method:** each scenario specifies subject, horizon, trigger, invalidation, deadline,
source prerequisites, evidence reference list and research status. Triggers use AND;
invalidations use OR in the first pure implementation. Both are explicit nonempty
lists. Unknown invalidation prevents a resolved trigger. Deadlines are exclusive.

Point-in-time statuses are `waiting`, `conditions_met`, `invalidated`, `unresolved`,
`expired` or `horizon_mismatch`. These are evaluation results at this cutoff, not a
new persisted scenario lifecycle or an order state. A later independent evaluation
cannot erase an earlier saved result. Historical "held for two bars" and "crossed"
conditions require their own completed-bar input from the incumbent time-series owner.

**Output:** at most three primary paths, the distinguishing observation, and an honest
stance. Two simultaneously met conditions produce a visible ambiguity, not an
arbitrary winner. The first implemented module always returns research-only readiness
and no ranking/sizing/trading/alert authority. Its output must not be wired into a
trade gate simply because it is deterministic.

**Acceptance:** zero is not missing; unit/horizon/subject mismatch abstains; missing
invalidation abstains; deadline behavior deterministic; scenario ordering does not
alter outcomes; no new market verdict derived from scenario counts.

### E10. Explanation, daily change and personal relevance

**Input:** qualified snapshot plus original prior snapshot reference, user-selected
horizon and existing authorized portfolio/watchlist context.
**Method:** render stable templates first; optionally use grounded language synthesis
inside the existing model gateway. Restrict the model to supplied evidence and approved
public definitions. Validate every numeric claim against its structured source. Treat
retrieved posts as data, never tool instructions. If the model is unavailable, templates
still answer the user job. Do not call an LLM on every price tick.

Changes are typed: new evidence, changed observation, new source revision, invalidated
condition, expired hypothesis or unavailable source. Do not compare two different
horizons or unrelated symbols and call that a thesis change. Saved context is immutable;
restoring it produces a separate current comparison through the incumbent save owner.

**Output:** one-sentence state, what changed, the strongest counterargument, and what to
watch next. Portfolio relevance is exposure context, not a silently generated order.
**Acceptance:** no invented explanations for missing data, no unsupported certainty,
no internal repo/source-path disclosure, no model text controls authority flags,
EN/ZH preserves caveats and status meaning.

### E11. Outcome learning and research promotion

**Input:** original point-in-time prediction/condition receipt, exact outcome ruler,
universe, costs and revisions; existing Market Memory and research owners.
**Method:** score observations, forecasts, option expressions and user decisions
separately. Record non-triggered conditional scenarios separately from losses/wins.
Preserve original deadlines, revised hypotheses and negative results. Use chronological
holdouts, overlapping-outcome purge/embargo and dependence-aware intervals. Register
all tried variants, not only the winner [S5].

An outcome is missing until its actual horizon matures. A model-generated probability
is not calibrated evidence. A conditional event probability is not a probability that
a user will profit. Require target-specific calibration and simple baselines; inspect
performance by regime, time of day and data quality before any existing promotion.
**Output:** evidence maturity, reliability by defined setup, known failure conditions
and research verdict. No new memory writer, trial registry or promotion authority. In particular, do not rebuild the killed family-by-regime reliability table (`DNR:KILL-PER-SIGNAL-FAMILY-RELIABILITY`); its exact re-entry requirements remain binding.

## 5. Infrastructure hardening

### Data paths, not a new platform

The production compositor should run in an existing accepted build/request path and
consume bounded immutable input references. Use existing atomic publication and data
contracts. The UI receives one coherent response generation. Do not introduce a new
Kafka bus, cron fleet, vector database or microservice to connect already available
functions. Containerized isolation may be useful for existing workers; it is not a
reason to duplicate service owners.

A dependency manifest is a field in the existing publication object, not a second
publication registry. It records source versions, observation/availability ranges,
coverage, model/calculation version, horizon, rights class and the reason a component
was withheld. `generated_at` is never promoted to source freshness.

### Freshness and partial failure

Consumer freshness is specified per capability. A ten-day display tolerance in the
existing volatility context is not suitable for an intraday condition. Quote, chain,
OI, economics and fundamental data have different update semantics. Production values
must be set after source latency/market-calendar measurement, not invented in this plan.

Required evidence missing: scenario unresolved. Optional evidence missing: retain the
qualified path with an explicit missing counterargument, not a stronger claim. A stale
canonical verdict remains inspectable historically but cannot lead a current hero.
Do not hard-fail the entire existing nightly because a new contextual leaf fails.
Preserve the prior good snapshot and clearly show its age; never refresh its clock.

Cache keys include subject, horizon, as-known-at, source-generation identities and
entitlement class. No shared cache for personalized context across users. Partial
refreshes must not combine a newer quote with a misleading older option book. Corrected
inputs change identity; old predictions remain bound to the old input set for grading.

### Idempotence, ordering and concurrency

Pure composition has no side effects. Deterministic digests make repeated evaluation
recoverable, but are not an authorization token. Existing publication/save owners handle
compare-and-swap, duplicate prevention and monotonic-generation rules. Exactly-once
claims require existing owner proof; adding another retry queue is forbidden.

Client requests bind symbol, horizon and generation. A late response for a previous
symbol cannot replace the current view. Abort or ignore outdated requests; test this
with controlled delay. A restore should compare a saved snapshot to a current one,
never overwrite the original or silently redate it. A browser refresh cannot create an
alert or purchase. All modifying user actions remain explicit and idempotent through
the incumbent API.

### Safety, data rights and privacy

Every source has allowed acquisition, retention, display, derived-use and model-use
fields; unknown entitlement means unavailable for that use. Public/free access is not
redistribution permission. Raw analyst corpora, licensed market history, credentials,
private portfolios and original uploaded screenshots do not belong in the public Git
repository. Commit code, sanitized fixtures, methodology and non-sensitive aggregate
results only. Keep secrets in the existing credential owner.

The X Developer Agreement inspected on 22 October 2026 prohibits using X API/content
to train or fine-tune foundation/frontier models [S6]. Therefore this project does not
fine-tune a foundation model on a harvested analyst corpus. Rights-approved analysis
and structured rule testing must be separately scoped; third-party API availability
is not a blanket downstream-rights grant. Apply deletion/retention obligations through
the existing acquisition owner and consult the actual applicable agreements.

Prompt injection controls: raw post/news text cannot select tools, endpoints, recipients,
authority, credentials or code. Extract bounded claims with source spans into an inert
schema. HTML escapes all text; no model-provided HTML or executable condition strings.
Public explanations use curated receipts, not repository-internals retrieval.

### Proposed performance and operational targets

These are engineering budgets to validate, not achieved measurements:

| Path | Proposed target | Verification |
|---|---|---|
| Pure composition, 128 observations / 12 scenarios | p95 under 50 ms on reference CI host | deterministic microbenchmark, reported host/version |
| Cached authenticated response | p95 under 300 ms, excluding network | existing request telemetry and load test |
| First meaningful mobile content | under 2.5 s on agreed test profile | browser timing + real production path |
| Incremental Navigator JavaScript | at most 35 KiB gzip, no charting framework added for basic view | bundle report |
| Primary response | at most 80 KiB uncompressed | schema/budget tests |
| Model synthesis outage | no loss of structured explanation | force model failure, render deterministic template |
| Evidence error | no false-current or false-confirmed result | adversarial and mutation tests |

Instrument the existing observability owner for stale/refused reasons, missing domains,
source lag, cache generation, response latency, unsupported horizons and user workflow
completion. Avoid portfolio contents/raw text in logs. Error-rate improvements must not
be manufactured by hiding unavailable rows. An operational dashboard is not another
lifecycle owner.

## 6. Product composition and design contract

### Placement

The Macro overview remains archetype D. Navigator becomes its focused "what matters /
what would change" experience, replacing duplication rather than adding a sixth wall.
Deep evidence lives in existing instrument/options/volatility/Market Memory destinations.
Terminal gets the same structured packet in instrument context, not a separate analyst
with contradictory state. No third global navigation header.

Primary composition: state and stance -> what changed -> decision map -> up to three
conditional paths -> one next-watch row. Detailed mechanics, history and source rights
are one click deeper. Do not present fourteen engines as fourteen equal cards.

### Visual direction

Institutional editorial clarity, with restrained instrument precision. Keep the house
Inter/system typography, numeric monospace, spacing and existing semantic colors.
Use meaningful chart series, even neutral borders and whitespace. No colored left
stripe or equivalent relocated accent edge. Risk is labeled in words as well as color.

Dark treatment: calm luminance depth, controlled raised surfaces, bright primary copy,
no neon heatmap as decoration. Light treatment: cool research canvas, white surfaces,
crisp neutral rules and small structural shadows; no dark chart islands. Both share
information architecture, ordering and semantics, but each gets its own visual review.

### Required Paper frames

1. Desktop overview, dark and light: mixed evidence, no confirmed action.
2. Mobile overview, dark and light: one dominant answer, next step, expandable paths.
3. Evidence detail: supporting/contrary evidence, definitions, input clocks, assumptions.
4. Change review: original vs current hypothesis, with unchanged original deadline.
5. Missing/stale/conflicting state: no stale confidence, clear next available action.
6. Saved-view restore: exact old snapshot and rebased current comparison, no fabricated save.

English and Chinese must fit at 1440 and 390 px; no truncation of material caveats.
Desktop may display paths together; mobile is an ordered vertical decision journey,
not a horizontally scrolling heatmap. Minimum targets 44 px where practical, visible
keyboard focus, reduced motion, labeled controls and no color-only status.

### Interaction specification

Horizon selection changes only to supported source/evaluation horizons. Unsupported
choices explain what is missing, not produce guessed resampling. Clicking a decision
zone shows why it exists and its source class. Clicking a scenario shows its exact
trigger, invalidation and counterevidence. "Why waiting?" explains the missing condition.
"What changed?" opens a typed difference from the last bound snapshot. Save/watch uses
the existing authenticated owner only when the real operation is available; no pretend
button. An uncalibrated probability slot stays absent, not a decorative 50/50 split.

### Current Paper boundary

The guarded Paper connection read the existing shared file successfully, but Paper
returned: its file is too large and further changes risk data loss. No mutation was
performed. The guarded catalog blocks file creation. The precise human action is to
create/open a new blank file named Market Navigator, after which its exact identity
can be inspected and bound. Do not bypass this by writing to the oversized file,
opening another guessed ID, or using a different carrier to evade a refusal.

A browser design study may proceed for layout/interaction validation, but is explicitly
NOT_APPLIED_TO_PAPER and not a claimed Paper export. Production UI styling waits for
that safe design path; non-UI foundation and research remain independently executable.

## 7. Research program and admission

Research proceeds on independent evidence tracks. The adjacent RESEARCH_PROTOCOL.md
is the executable study specification; it is not a second hypothesis registry. Exact
research registration and promotion stay with the existing Research Factory/Signal
Commons/Options arena owners. A draft specification is not an admitted live trial.

**Track A - measurement and contracts.** Verify clocks, units, expiry, coverage,
corrections and mathematical applicability before asking whether a feature predicts.
The first executed study is MODEL_AUDIT.json: a deterministic simulation using the
incumbent Greek kernel, not a market backtest. It compares local charm approximation
with finite repricing at valid pre-expiry horizons and exposes invalid full-day
extrapolation. The explicit assumptions prevent attributing its numbers to real dealers.

**Track B - analyst method reconstruction.** Acquire only a rights-approved corpus
through the existing transport and budget owner. Resolve the actual account identity,
archive window, pagination and deletion policy. Distinguish author originals, replies,
quotes, follow-ups and edits. Extract atomic claims with original deadlines. Store
source IDs and permitted evidence references, not an ungoverned copy in public Git.
Do not use likes/views as evidence of forecast quality.

**Track C - market hypotheses.** Reconstruct features as known at decision time and
compare exact analyst rules with simple baselines and frozen alternative variants.
Prioritize VIX1D clock conditioning, breadth level vs speed, price-level validity,
option-scope sensitivity and event-response interpretation. Existing negative results
remain priors; do not reopen killed research by renaming it.

**Track D - product utility.** Test whether users can understand the next observation,
recognize disagreement, preserve the original hypothesis, and avoid mistaking context
for a signal. Measure false certainty and unnecessary actions, not only engagement.
A clearer forecast explanation may be valuable even when it does not improve returns;
that benefit must be labeled separately from predictive performance.

### Forecast evaluation contract

Freeze universe, feature timing, entry/cutoff time, horizon, target, costs, baseline,
trial family and selection policy. Separate training/development, chronological
validation and untouched test. Purge overlap using the maximum outcome window and
embargo any shared features/labels as required by the selected design. Cluster/bootstrap
at appropriate session/event units. Record all variants and use the incumbent multiple-
testing controls. Never optimize a threshold on the held-out set, or call a retrospective
reconstruction a prospective study.

A forecast target can be a level touched by deadline, close above/below a level,
maximum adverse excursion, realized volatility or a calibrated bounded outcome. These
are not interchangeable. A stock moving the predicted direction is not necessarily a
profitable option trade. Prospective evidence starts only after a frozen prediction is
captured before its outcome through the incumbent owner.

No probability badge before its sample, denominator, horizon, coverage, calibration
and uncertainty are inspectable. No strong performance claim from a tiny subgroup.
No numerical promotion threshold is invented here to bypass an existing research gate.

## 8. Build sequence, dependencies and acceptance

| Wave | Deliverable | Depends on | Observable acceptance |
|---|---|---|---|
| W0 - foundation | Source reuse decision, master plan, pure compositor, tests, model audit | Current assignment and source pin | Deterministic tests pass; no new authority or network/write side effect |
| W1 - data adapters | Owner-verified source adapters, source capabilities and research coverage | W0; actual existing owner contracts | Missing/late/revised data replay; source clocks and identity proven |
| W2 - design | Safe Paper overview/detail/return flows, bilingual theme matrix | Safe new Paper file; W0 contract | Screenshot critiques resolved; JSX and computed-style handoff tied to exact nodes |
| W3 - contextual product | Macro integration + Terminal contract consumer, shared chrome | W1 + W2 | Signed-in real data visible; defaults/missing/error/mobile states proven |
| W4 - personal continuity | Save/restore/what-changed/watch through incumbents | W3 + compatible personal-state contract | Real save and later restore; exact original retained; cross-user isolation |
| W5 - evidence maturity | Approved studies, negative findings, prospective predictions and outcomes | W1 + research admission/rights | Time-valid outcomes, baselines, uncertainty and held-out findings reproducible |
| W6 - qualified setup use | Reuse independently accepted setup/risk output where authorized | W5 + existing promotion | No context-to-trade laundering; realistic costs and full risk/permission proof |
| W7 - production acceptance | Release, real-path user tasks, monitoring and rollback | Delivered scoped waves | All completion criteria in section 1 satisfied or explicitly retained as unshipped |

W5 can run alongside W2-W4 where data and research admission exist. Paper's file-size
gate blocks design writes, not code correctness or data investigation. A source lacking
intraday history blocks that exact threshold study, not the whole product.

### Sequencing and work ownership

The CEO retains synthesis, architecture boundaries, research adjudication and product
acceptance. Bounded data contract, UI implementation and evaluation work should use
eligible paid Fabric workers through the actual admitted path, with disjoint files,
exact inputs and checkable returns. No worker was started for the current W0 work.
The available Executive submit contract queues only; a queue receipt would not prove
execution. Direct principal work is used for the integrated architecture and foundation.
Do not manufacture a native-worker substitute or a background promise.

Every work packet states the consumer capability, owned files, required upstream
revision, permitted data, missingness behavior, tests, stop conditions and exact return.
No worker may promote a model, add an external feed, change authentication, or allocate
trade authority as an incidental implementation detail. Existing source leases and
active PR writers remain intact. One coherent PR per bounded delivered capability,
not a mega-PR rewriting all neighboring engines.

### Production rollout

Ship correctness/contract code with no production activation first. Integrate descriptive
output behind existing configuration after safe design and owner adapter proof. Exercise
current, missing, stale, contradictory, revised and out-of-order responses. Use existing
release controls and user/audience restrictions. Do not change subscription entitlement
or install new tracking to make a demo work.

A rollout measurement must compare the same source generation. A shadow observation is
not a live signal; a product beta is not evidence of profitability. Roll back by removing
the consumer integration/activation through the incumbent deployment owner, leaving
canonical data and saved evidence intact. Never roll back by deleting outcome history.

### Required verification matrix

- Unit/property: clocks, units, NaN/Inf/bool, zero/missing, contract completeness,
  scenario semantics, deterministic identities, no authority changes.
- Integration: exact upstream schemas and receipts, supported domains, snapshot
  consistency, no import-time side effects, downstream schema version rejection.
- Research: shifted data, future-vintage injection, survivorship, selection/trial
  accounting, overlapping targets, placebo rules, missing outcomes and costs.
- Security/privacy: malicious source prose, escaped HTML, cross-user save/cache,
  revoked entitlement, public payload contains no internal paths/credentials.
- Browser: dark/light x EN/ZH x desktop/mobile, keyboard, focus, reduced motion,
  loading/error/empty states, long labels, horizontal overflow and late responses.
- Real path: deployed source identity, authenticated data, actual save/restore when
  in scope, actual alert delivery only after existing activation permits it.

## 9. Risks and concrete mitigations

| Risk | Failure signature | Mitigation / proof |
|---|---|---|
| Attractive but unfounded analyst clone | Fluent confident calls without outcome evidence | Atomic claims; no default probability; frozen evaluation |
| Duplicate regime authority | Navigator and Macro disagree on current verdict | Consume exact incumbent state; parity and no-score tests |
| Snapshot-time laundering | Old input presented current because one file regenerated | Per-input clocks; source-session binding; stale fixture |
| Position-sign error | Put/call convention represented as known inventory | Explicit scenario book and source method; sign tests |
| Expiry blow-up | Large charm treated as a whole-day imminent order | Finite repricing; economic fixing; applicability refusal |
| Hidden missing population | Breadth or GEX looks stronger as members disappear | Declared universe, denominators and complete-book checks |
| Hindsight reconstruction | Revised inputs or changing target improve record | Availability cutoff; immutable originals; correction chain |
| Correlated indicator voting | More similar indicators create fake certainty | Family lineage and ablation, no new fusion score |
| Rights breach | API-access corpus used as unrestricted training/display | Per-use entitlement; no foundation fine-tuning; no raw public corpus |
| Design data loss | Oversized Paper file receives another mutation | New safe file gate, no writes to warned target |
| Endless infrastructure | New queue/registry without user capability | Named consumer and acceptance per wave; reuse first |
| False completion | Green tests called shipped | Distinct source, CI, merge, deployment, browser and acceptance receipts |

## 10. Current capability ledger and next material action

At authoring, W0 contains the new pure compositor and deterministic tests plus an
executed model audit. Neither source inspection nor these tests proves production.
The complete analyst archive, empirical strategy validation, native Paper designs,
production source adapter and signed-in user journey are not yet delivered.

The immediate source work is to finish the research protocol and proof fixtures,
register their tests in existing CI, produce a clearly marked browser design study,
and deliver this bounded foundation through the normal source chain. Then bind the
safe Paper file and existing data adapters; do not repeat the source census or Greek
kernel work. Detailed recovery and exact effects live in CONTINUATION.md and Agent OS.

## Sources and inspection limits

[S1] Cboe, "What the VIX and VIX1D Indices Attempt to Measure and How They Differ",
24 April 2023. HTML inspected 22 October 2026. Definitions/time-weighting only; not a
validation of any reversal strategy.
https://www.cboe.com/insights/posts/what-the-vix-and-vix-1-d-indices-attempt-to-measure-and-how-they-differ/

[S2] Federal Reserve Bank of St. Louis, FRED API Real-Time Periods. HTML inspected
22 October 2026. Default current revision versus historical vintages.
https://fred.stlouisfed.org/docs/api/fred/realtime_period.html

[S3] Federal Reserve Bank of St. Louis, release dates API. HTML inspected 22 October
2026. Publisher release dates need not equal FRED/ALFRED availability.
https://fred.stlouisfed.org/docs/api/fred/release_dates.html

[S4] Lo, Mamaysky and Wang, Foundations of Technical Analysis, NBER WP 7613 / Journal
of Finance 2000. Abstract inspected. Formalized historical pattern information is not
a claim of profitable current execution or a full-paper replication.
https://www.nber.org/papers/w7613

[S5] Bailey and Lopez de Prado, The Deflated Sharpe Ratio, Journal of Portfolio
Management 2014. Publisher/author abstract inspected. Selection/multiple trials and
non-normality are performance-inflation concerns; this plan does not claim to have
replicated that paper's full methods.
https://doi.org/10.2139/ssrn.2460551

[S6] X Developer Agreement, last updated 27 April 2026, inspected 22 October 2026,
section III restrictions. Contract-specific restrictions; not legal advice or a blanket
interpretation of every third-party provider's terms.
https://docs.x.com/developer-terms/agreement

Internal evidence: the exact Macro baseline above, named source modules, relevant
repository design/source laws, and inspected open PR descriptions. Code is evidence
of implementation, not source entitlement, runtime liveness or market performance.
