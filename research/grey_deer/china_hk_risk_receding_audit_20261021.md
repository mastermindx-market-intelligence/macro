# China and Hong Kong “Risk receding” — feature census and audit

**Audit date:** 21 October 2026 America/Chicago; fresh production retrieval at 04:00 UTC on 22 October.

**Scope:** the Risk Radar recovery panel, its China/HK producers, shared renderer, probability surface, evidence claims and existing repair/release work.

**Status:** verified audit and remediation specification. This audit does not implement or deploy a product fix, establish a current market bottom, or qualify a trading strategy.

**Source baseline:** Macro `1f536032d446e2b51bda47f0575e371f0c4a0aae`.

**Owning workstream:** `WS:GREY-DEER-RISK-INTELLIGENCE`; existing recovery repair `MAS-258`, PR #7029.

## 1. Finding

The current green message is misleading. It promotes an easing composite and a generic U.S. liquidity condition into a local market TURN and an instruction to scale exposure, although China/HK local recovery confirmation is unavailable.

Declining prices do not, by themselves, disprove a decline in forward risk. A market can remain weak while incremental selling pressure eases, and useful bottom detection must be able to recognize that early. The defect here is that the displayed conclusion exceeds the evidence: the implementation has no China/HK local recovery channel, missing eligibility permits the positive branch, and a Fed liquidity category is treated as a fresh confirming event.

The immediate remedy is to finish the existing source repair with current release evidence. The durable feature should display local condition, change in pressure, repair evidence, forecast qualification and strategy eligibility separately. It must preserve useful early stabilization observations without turning them into an all-clear.

### Freshly served evidence

Both pages returned HTTP 200 with a page date of **2026-10-21**. Their complete downloaded bytes exactly matched the generated files at the audited main revision. The contradiction therefore exists in freshly served content; it is not explained by an old screenshot or browser cache. The supplied screenshot was also visually inspected. This audit did not perform a new interactive browser session.

| Surface | Observed risk/condition | Observed recovery presentation |
|---|---|---|
| China | Risk-off **92/100**; breadth breakdown **100th percentile**; Shanghai Composite **7% below its 200-day average**; 21-session pullback odds **45%** versus a displayed normal **30%** | Green “Risk receding — liquidity turning supportive”; TURN; “Fed liquidity expanding”; “~6pp” buying-dips claim; “Begin scaling exposure back in tranches” |
| Hong Kong | Calm **43/100**; Hang Seng **7% below its 200-day average**; displayed 5/10/21-session odds **0% / 0% / 31%** | The same green TURN and scaling-in advice; “Pullback odds 54% → 31% (peaked 11 days ago)” |
| China, adjacent action | “Protect capital: raise cash, no new chases” | Appears alongside the recovery panel’s instruction to add exposure |
| Evidence qualification | China: 28 graded readings; Hong Kong: 31; both say recovery has too few graded observations | The prominent TURN and instruction appear despite this qualification |

The 92/100 score is an intensity measure, not a 92% probability. The displayed 0% values do not prove that the underlying stored probabilities are exactly zero. Small values can round to zero.

Evidence: [China generated page at the audited revision] [S1], [HK generated page] [S2], and the companion [verification receipt](china_hk_risk_receding_audit_20261021/verification.json).

## 2. Feature census

| Component | Current producer/consumer | What it actually supplies | Required treatment |
|---|---|---|---|
| International radar | `engine/risk_radar_intl.py` | Weighted external/local pressure percentiles, a context gate, categorical state, band-based probabilities and a 30-session trajectory | Preserve measured scope; do not present every profile as complete local market risk |
| Shared trajectory | `engine/risk_radar.py::_trajectory_from_series` | Phase from recent composite intensity; five-session velocity, distance below a 30-session peak, ten-session odds change | Name the measured quantity and comparison period; distinguish intensity change from probability change |
| Recovery assessment | `engine/risk_radar_recovery.py::assess` | Joins trajectory, liquidity catalysts and, for the U.S. only, local confirmation | Fail closed for qualified TURN when required permission/evidence is absent |
| Liquidity catalysts | `_liquidity_catalysts` in the recovery module | Fed, policy and global liquidity context, including U.S. latest data on international pages | Preserve market applicability, observation time, release time and event age |
| Local repair channel | `engine/risk_radar_market_catalysts.py` | U.S. internals, mood, tape and volatility conditions | Currently not applicable to CN/HK; build local adapters using existing inputs |
| View-model integration | `engine/market_state.py` | Attaches recovery as a display field without relaxing the machine risk ceiling | A non-authoritative backend field must not become action advice in presentation |
| China/HK builders | `scripts/build_china.py`, `scripts/build_hk.py` | Compute international radar before Market State, attach audit results, invoke the tuner on the armed nightly lane, render the shared card | Fix the generator and regenerate both markets; preserve nightly-only write controls |
| Shared UI | `templates/_risk_radar_card.html.j2` and its CSS | Uses legacy `turn_confirmed` for TURN and `receding` for green; renders liquidity claim and `do_en/do_zh` | Derive visible confidence from the qualified claim, not a legacy compatibility flag |
| Probability calibration | `engine/risk_radar_intl_tune.py` | Repeated bounded movement toward realized daily outcomes; acceptance scored only on h21 | Audit repeat-update semantics, horizon-specific scoring, effective sample size and uncertainty |
| Forward grading | `risk_radar_intl_audit.py`, `risk_radar_recovery_audit.py`, `risk_radar_scorecard.py` | Separate downside-alert and recovery observations | Do not transfer alert performance to recovery or strategy permission; separate construction versions |
| Tests | `tests/test_risk_radar_recovery.py` and related suites | Current tests explicitly preserve a liquidity-only legacy turn and CN market-channel N/A | Replace unsafe semantic expectations and add adverse-path regressions |
| Existing repairs | #7029, #7068, #8021; related held #8721 | Source containment, generated-page hotfix, missing-evidence repair, and observed-damage research | Reuse accepted work; reconcile current gates instead of opening a competing implementation |

The shared card/recovery path also reaches U.S. and Canada consumers. The international engine has ten profiles (CN, HK, CA, KR, JP, TW, IN, AU, GB, EZ); not every profile’s live page was inspected. The release regression scope must include every actual shared consumer, without claiming that all ten currently exhibit this incident.

Evidence: [international engine] [S3], [recovery engine] [S4], [shared template] [S5], [China builder] [S6], [HK builder] [S7], [Market State integration] [S8].

## 3. Proven failure mechanisms

### 3.1 Missing eligibility becomes permission

Current recovery logic is equivalent to:

```python
deesc = rr.get("deescalation")
suppressed = bool(deesc) and deesc.get("eligible") is False
receding = phase == "receding" and not suppressed
turn_confirmed = bool(receding and n_fresh >= 1)
```

The international `compute` return does not supply `deescalation`. Therefore an absent block does not suppress the positive branch. Empty blocks and null eligibility also fail open. Only an explicit Boolean false blocks it.

The independent review identified this issue. Principal verification executed the truth table and checked the exact source contract. This is a construction defect, independent of whether the next market return is positive or negative. [S3] [S4]

### 3.2 Local confirmation exists only for the U.S., while the UI uses the weaker flag

The recovery module calls the market catalyst channel only when `market == "us"`. For China/HK, the market channel and `turn_confirmed_full` are `None`.

The stronger full-confirmation field was added as a sibling, while legacy `turn_confirmed` was deliberately preserved for compatibility. The template still uses that legacy field for TURN; the stronger flag only adds an extra “INTERNALS ✓” badge. Absence of the stronger badge does not prevent the green conclusion.

Existing tests explicitly assert that international market confirmation is N/A while the legacy liquidity-only Boolean remains available. Thus a passing existing test suite can preserve the misleading behavior. [S4] [S5][S9]

### 3.3 A continuing liquidity category is labelled fresh

When `liquidity_overlay == "expanding"`, the Fed net-liquidity catalyst sets `fresh: True` unconditionally. It does not establish a newly observed event, a permissible source age, or that the condition has just turned.

International pages may load the U.S. latest record for these legs. A supportive U.S. liquidity backdrop can be useful context, but it does not establish local participation or price repair in China/HK. U.S. rate-shock inputs and Fed net liquidity are distinct series; this audit does not claim they are literally the same variable or that one causes the other.

Ancillary source risk: `_recent` accepts dates using only an upper age bound, so a future date can qualify as recent. This is a regression case, not a proven cause of the current incident. [S4]

### 3.4 “Receding” does not require falling displayed odds or local price improvement

The shared classifier uses composite intensity, its distance below a recent peak, and its recent velocity. It does not require the current risk level to be low, the local benchmark to rise, local breadth to repair, or displayed odds to fall.

A deterministic execution of the exact classifier and actual constants produced:

| Synthetic input/output | Value |
|---|---|
| Window | 30 sessions |
| Intensity peak / current | 98 / 92 |
| Distance below peak | 6 points |
| Five-session velocity | −2 points |
| State throughout | risk-off |
| Probability throughout | 45% |
| Returned phase | receding |
| Returned ten-session probability change | 0 |

This is a valid descriptive statement about intensity. It becomes misleading when rendered as a qualified market turn or an invitation to add exposure.

International probabilities are looked up from state buckets. A score can move within one bucket while the displayed odds remain unchanged. Moreover, the historical trajectory maps prior intensities through the current calibration surface; that reconstructed line is not necessarily the sequence of probabilities originally issued on those dates. A changed calibration version must not be mistaken for a newly observed market improvement. [S3] [S10]

### 3.5 Hong Kong’s “calm” has incomplete local coverage

The current HK profile has no breadth group. Its composite uses U.S. rate shock at weight 1.0 and dollar strength at weight 0.6. The local benchmark’s relationship to the 200-day average is a context gate, not a local recovery detector.

This finding is specific to the **Risk Radar composite**. Other parts of the HK page and Market State builder already reference HK price, breadth, VHSI/HIBOR and HKMA/peg conditions. Their existence does not mean they are integrated into this recovery decision. Reuse these owners; do not conclude that no local HK data exists anywhere.

For China, the listed groups are U.S. rate shock (1.0), USD/CNH (0.6), U.S.–China yield gap (0.8), and local breadth (1.0). When all groups are available, 2.4 of 3.4 weight lies outside the local breadth group; the result is subsequently percentile-ranked. These weights describe construction, not calibrated causal attribution.

External pressure can ease while local deterioration persists. Until HK coverage is repaired, label the existing number as external pressure and disclose the incomplete local risk assessment. Changing the number arbitrarily or hiding known local damage would not solve the scope problem. [S3] [S6][S7]

### 3.6 The “~6pp” claim has been transferred beyond its evidence

The source study, `research/LIQUIDITY_LADDER.md`, examines actual stock cycle-ladder **FRESH BUY + TURN SIGNALED** setups under expanding versus contracting U.S. net liquidity. Its 21-day hit rates were 61.2% versus 54.8%, a 6.4 percentage-point difference.

That is not a generic result for buying any dip, not a comparison against an unspecified average, and not a China/HK bottom detector. The document reports roughly 72 effective liquidity episodes, rather than treating all 122,087 evaluations as independent. Its episode-level 21-day permutation result was approximately p=0.06, and the longer 63-day effect weakened. Original wiring notes explicitly left China builds untouched.

The present Chinese copy also calls the difference an advantage “versus average,” which differs from the study’s expanding-versus-contracting comparison. The immediate repair should remove this claim from CN/HK recovery. A tooltip or “not a promise” caveat cannot supply the missing population, conditioning or strategy match. No rerun of the original study is needed to establish this applicability mismatch. [S11]

### 3.7 “Display-only” does not neutralize a visible instruction

The backend comments say recovery does not relax Market State’s ceiling, and the rendered tooltip says it is not forward-tested. The prominent action nevertheless says to begin scaling exposure. Users encounter an instruction even if no machine order is placed.

Recovery context should describe what improved, what remains impaired and what would confirm or invalidate the observation. Entry permission belongs to a qualified strategy. Numerical portfolio sizing belongs to its existing policy/portfolio owner. [S4] [S5][S8] [S16]

## 4. Probability calibration: a related issue requiring its own containment

HK’s rendered 0% short-horizon odds deserve scrutiny. The source and synthetic audit establish these limitations:

- Tuning can begin after 25 graded daily readings and six readings in a state. Adjacent daily forward windows can overlap.
- Each run moves every horizon toward realized rates, with a maximum five-percentage-point step.
- The do-no-harm check measures only the 21-session Brier score on the same graded sample used to tune. It does not separately validate the 5- and 10-session changes or establish out-of-sample calibration.
- There is no new-matured-evidence fingerprint preventing repeated adjustment on an unchanged sample.
- Overlay loading does not establish a complete calibration version, freshness, range and qualification contract.

A no-file, no-network execution of the exact tuner functions used the same 30 synthetic graded records on every invocation. Starting at 15% / 27% / 45%, with realized rates 0% / 0% / 30%, the tuner applied seven successive updates and then held. Final values were **0.2% / 0.9% / 30.1%**. The first would display as 0% at whole-percentage precision. No new observations had arrived.

This reproduces repeat-update semantics; it does **not** prove that this exact history caused the current HK output. The current production calibration JSON, tune log and graded sample still need a version-bound trace before attributing that incident.

The repair should make updates idempotent for a frozen evidence set unless repeated optimization is explicitly part of the declared method. Evaluate each published horizon, preserve episode-aware uncertainty, use appropriate chronological validation, and disclose insufficient support. Do not invent a probability floor or claim that suppressing a zero validates the model. [S12]

## 5. Existing work and why the defect remains

| Work | Verified status at audit | Consequence |
|---|---|---|
| **#7068** — remove misleading China recovery panel | Merged 11 September; changed only generated `site/china.html` | It removed one generated instance. Current source still emits the panel, and fresh live bytes again contain it. Regeneration is the supported explanation for recurrence; the exact reintroduction commit was not established. |
| **#7029** — prevent unconfirmed recovery and re-entry advice | Open, head `f7545a519c02fb8fb7b4c5b8e9f73c62e00aecc0` | Correct immediate containment exists but is not deployed. |
| **#8021** — keep missing evidence out of calm and recovery | Merged 26 September | Relevant U.S. missing-evidence safeguards did not add the absent international eligibility contract. |
| **#8721** — pullback-depth research, Paper states and arithmetic | Open draft, held | Useful observed-damage/forecast-withheld design work; not a release-ready substitute for the recovery fix. |
| Existing repair architecture | `DEC:REPAIR-IS-ORTHOGONAL-AND-FIRST-CLASS`; October 17 proposed contract | Already separates hazard, damage, repair and action eligibility. Reuse it rather than create a new fused score or parallel state store. |

### #7029 is the correct starting point, with an important limit

Its candidate requires explicit eligibility, local confirmation, an evaluated clear volatility veto, and a fresh catalyst applicable to the market before a qualified TURN. It scopes liquidity evidence, removes the generic +6pp claim, replaces action prose with context, and separates construction versions.

That is sound containment. Because the international market channel remains N/A, it does not complete China/HK early recovery detection. A permanent feature must add local observations and allow a narrowly scoped stabilization watch without requiring every condition needed for a stronger or actionable claim.

### The release obstacle is concrete

A fresh check-run query confirmed that #7029’s current head still has failed **ci-pack-4** and **ci-gate**, from run **35740798313** on September 22. Eleven other packs passed. The October 4 checkpoint identifies:

1. Missing same-diff source-bound P0B receipts for the changed shared template: `mockups/evidence/prophet-p0b-zero-fouc/mobile-layout.json` and `mobile-layout-canada.json`.
2. A design-governance infrastructure-unknown result after a bounded fetch of main failed.

The older PR body’s queued status and prior “462 tests” statement are not current release proof. The next receiver must reconcile the current integrated candidate and applicable evidence requirement, produce real updated receipts where required, resolve the identified infrastructure cause, and obtain current binding checks and review. An inactive merge-queue-pilot authority check is not the main-target gate.

Do not blindly rerun unchanged CI, transplant stale generated files, or release held sister work. Preserve the #7875/#7040/China seams and newer shared-popup work until actual collision and custody checks permit integration. [S13] [S14][S15]

## 6. Remediation specification

### Priority 0 — contain unsupported claims

**Owner/action:** currently assigned recovery delivery receiver, on the reconciled #7029 carrier or a lawfully established continuation; do not treat historical authorship as a live assignment.

1. Reconcile the exact branch, workspace, current writer/lease and pending effects before modifying it.
2. Require explicit, typed eligibility for qualified TURN. Missing, null, malformed, stale or unevaluated required evidence must produce “unconfirmed,” with the reason.
3. Remove scaling-in and other position instructions from descriptive recovery prose. Remove the unsupported CN/HK +6pp claim.
4. Treat U.S. liquidity as dated U.S. context; require a source clock and applicable market scope before it can confirm any claim.
5. Scope HK’s existing score honestly as external pressure while local coverage is incomplete.
6. Regenerate both CN/HK through the source builders and verify the real served output. Do not repeat the generated-file-only hotfix.
7. Preserve visible severe local conditions and useful independently qualified facts.

An appropriate China message using the verified available fields is:

> **Risk remains high. Recovery is unconfirmed.**

> Breadth remains severely weak and Shanghai is below its long-term average. The radar’s composite intensity is below its recent peak. Local price and breadth repair have not been established by this panel.

For HK:

> **External-pressure score below its recent peak. Local recovery is unconfirmed.**

> Hang Seng remains below its long-term average. This radar does not yet provide a complete local breadth-based risk assessment.

These are proposed semantic examples, not newly validated market forecasts. Avoid asserting fresh day-to-day deterioration unless the relevant current local series supports it.

### Priority 1 — provide a useful local stabilization feature

Keep the existing repair lifecycle **NONE / IMPULSE / BROADENING / CONFIRMED / FAILED**, with field-level availability and scope alongside it. Do not create a second lifecycle or event ledger. “Confirmed” means a defined repair condition was satisfied, not certainty that the final low is in. [S16]

| Product concept | Evidence needed | What the user can reasonably infer |
|---|---|---|
| Current local condition | Dated benchmark and participation observations | What is damaged or improving now |
| Pressure change | Comparable input set, definition, calibration version and lookback | Which measured pressures eased or worsened |
| Early stabilization / IMPULSE | A defined local price or participation pattern, narrow scope and invalidation | A repair attempt is visible; further lows remain possible |
| BROADENING | Additional independent local evidence and persistence | Improvement extends beyond one index bounce |
| CONFIRMED repair | The accepted market-specific confirmation contract and qualified critical inputs | The stated repair condition has been met |
| FAILED repair | The predeclared invalidation condition | The earlier attempt failed; retain its original record |
| Strategy eligibility | A separately accepted strategy, current availability and policy conditions | Whether that strategy qualifies an action |

Implement local capability incrementally:

- **Index condition first:** use existing Shanghai/CSI 300/Shenzhen and HSI/HSCEI/Hang Seng Tech owners with explicit benchmark identity, session, drawdown and short-term repair measures.
- **Participation next:** reuse existing breadth fields, new highs/lows, advance/decline participation and coverage denominators where qualified. China’s accessible breadth schema already contains above-50/200-day shares, new highs/lows and advance/decline fields. Confirm HK coverage and membership quality rather than borrowing U.S. internals.
- **Local funding/volatility context:** use applicable PBoC/RRR/LPR and funding conditions for China; HKMA/peg/HIBOR and related local observations for HK, where available and qualified. These add context; they are not universal requirements for every descriptive price watch.
- **Forecast and strategy qualification later:** add numerical bottom/re-entry probability or position instructions only after their own evidence and authority requirements are satisfied.

Do not require a 200-day-average reclaim before an early watch. Do not make supportive liquidity or low volatility mandatory for every observation. A marginal new low with improving participation can be a legitimate, explicitly uncertain retest; a continued breakdown with worsening breadth must remain adverse. A missing breadth feed should narrow a claim to index stabilization, not erase valid index observations or silently certify broad repair.

### Priority 2 — qualify forecasts and learning

For every probability, bind the market/benchmark, currency and price basis, event definition, decision origin, horizon, model/calibration version, sample provenance, effective independent support and uncertainty.

Separate three evaluations:

1. **Downside forecast:** calibration and incremental value relative to a declared baseline, by horizon and era.
2. **Repair observation:** false starts, time to stabilization, subsequent lows, adverse excursion, persistence, missed recoveries and coverage.
3. **Strategy:** realized performance under the declared entry, exit, invalidation, sizing and cost assumptions.

Consecutive daily alerts are not independent trials. Grade episode-aware outcomes and preserve failed repair attempts. Do not infer predictive quality from one realized decline, one successful bounce, a passing UI test, or the existence of a forward log.

This audit did not run a new historical model fit, replay a frozen Grey Deer study, change a preregistration, or promote a policy. Existing source-purpose and research-admission holds remain controlling.

## 7. Acceptance and regression matrix

| Case | Required behavior |
|---|---|
| Missing/empty/null/malformed eligibility | No qualified TURN or action instruction; explicit unavailable reason |
| Fresh U.S. liquidity, falling CN/HK prices, adverse local participation | Show foreign context separately; no local recovery promotion |
| Composite 98→92, risk-off persists, odds remain 45% | Name intensity easing; retain high risk and unchanged odds |
| Below a window peak but recent intensity rising | Do not imply current pressure is falling; disclose comparator/recency |
| Missing or future-dated source timestamp | No “fresh” confirmation; original observation clocks remain visible |
| Active volatility veto, or an unevaluated veto | No claim that the safety condition passed; independently valid descriptive observations may remain |
| Index stabilizes below 200-day average while liquidity remains adverse | Permit a narrowly scoped early watch if its local pattern qualifies |
| Marginal retest/new low with improving participation | Preserve uncertainty and invalidation; do not mechanically erase every watch |
| Rebound followed by material renewed breakdown | Mark repair FAILED under the accepted rule; retain hazard and original attempt |
| HK local coverage incomplete | External-pressure label and local-coverage gap, not a complete “market calm” inference |
| Missing inputs or unbounded forward fill | Missingness must not improve confidence or become calm; age/coverage limits enforced |
| Calibration changes with no new outcomes | No accidental repeated evidence gain; preserve version and issued-versus-reconstructed distinction |
| Horizon-specific calibration | Every changed published horizon meets its own qualification; h21 alone cannot certify h5/h10 |
| Legacy payload lacks new fields | Safe compatibility path; no fallback to liquidity-only TURN |
| Chinese/English, dark/light, desktop/mobile | Same claim strength, reasons and action boundary in every presentation |
| All actual shared consumers | CN/HK correction survives regeneration; U.S./Canada and newer popup integrations retain their accepted behavior |
| Real release | Accepted source → passing current checks/review → merged bytes → normal generated output → actual served route → rendered UI |

The semantic tests must fail on the current unsafe behavior. Do not preserve old tests that define “receding + fresh generic liquidity” as sufficient local recovery merely to keep the suite green.

## 8. Evidence limits and audit closure

### Established

- The issue is present in both freshly served October 21 pages.
- Served HTML matches the pinned generated source artifacts.
- Source explains missing eligibility, unconditional freshness, legacy UI gating, incomplete HK risk coverage and the unsupported claim transfer.
- An independent bounded worker reviewed the math; the principal corrected its assumed lookbacks and verified the essential classifier/truth-table behavior using actual source.
- A separate synthetic tuner execution established repeat updates on unchanged evidence.
- Existing repairs, exact open head and failed release checks were identified.

### Not established

- A current-day full recomputation from production price/breadth/calibration inputs.
- A validated China/HK market bottom or probability of recovery.
- The exact tune history responsible for HK’s displayed 0%.
- The exact commit that reintroduced the generated China panel after #7068.
- Production acceptance of #7029 or any held related work.

The accessible data-workspace snapshot was explicitly unqualified for production and its benchmark/breadth series ended **October 9**. That cannot be substituted for October 21 inputs. It is a limitation of the inspected snapshot, not evidence that the live pages themselves used October 9 data.

### Completion boundary

The requested **census and audit** is complete once this report and its evidence are durably published and read back. The **product repair remains unimplemented by this audit**. No product code, calibration, source data, release hold, strategy permission or portfolio setting was changed.

**Primary next action:** reconcile and finish #7029’s current source containment, including its actual P0B/design evidence and release gates, then prove the corrected CN/HK pages on the real served path. In parallel, a separately assigned local-repair implementation can reuse the existing repair lifecycle and local data owners. Local descriptive repair work can proceed within its assigned scope without waiting for strategy research. Publishing a new forecast or action claim still requires its existing qualification and authority.

## Sources and immutable identities

[S1]: https://github.com/mastermindx-market-intelligence/macro/blob/1f536032d446e2b51bda47f0575e371f0c4a0aae/site/china.html
[S2]: https://github.com/mastermindx-market-intelligence/macro/blob/1f536032d446e2b51bda47f0575e371f0c4a0aae/site/hk.html
[S3]: https://github.com/mastermindx-market-intelligence/macro/blob/1f536032d446e2b51bda47f0575e371f0c4a0aae/engine/risk_radar_intl.py
[S4]: https://github.com/mastermindx-market-intelligence/macro/blob/1f536032d446e2b51bda47f0575e371f0c4a0aae/engine/risk_radar_recovery.py
[S5]: https://github.com/mastermindx-market-intelligence/macro/blob/1f536032d446e2b51bda47f0575e371f0c4a0aae/templates/_risk_radar_card.html.j2
[S6]: https://github.com/mastermindx-market-intelligence/macro/blob/1f536032d446e2b51bda47f0575e371f0c4a0aae/scripts/build_china.py
[S7]: https://github.com/mastermindx-market-intelligence/macro/blob/1f536032d446e2b51bda47f0575e371f0c4a0aae/scripts/build_hk.py
[S8]: https://github.com/mastermindx-market-intelligence/macro/blob/1f536032d446e2b51bda47f0575e371f0c4a0aae/engine/market_state.py
[S9]: https://github.com/mastermindx-market-intelligence/macro/blob/1f536032d446e2b51bda47f0575e371f0c4a0aae/tests/test_risk_radar_recovery.py
[S10]: https://github.com/mastermindx-market-intelligence/macro/blob/1f536032d446e2b51bda47f0575e371f0c4a0aae/engine/risk_radar.py
[S11]: https://github.com/mastermindx-market-intelligence/macro/blob/1f536032d446e2b51bda47f0575e371f0c4a0aae/research/LIQUIDITY_LADDER.md
[S12]: https://github.com/mastermindx-market-intelligence/macro/blob/1f536032d446e2b51bda47f0575e371f0c4a0aae/engine/risk_radar_intl_tune.py
[S13]: https://github.com/mastermindx-market-intelligence/macro/pull/7029
[S14]: https://github.com/mastermindx-market-intelligence/macro/pull/7029#issuecomment-5974841314
[S15]: https://github.com/mastermindx-market-intelligence/macro/actions/runs/35740798313
[S16]: https://github.com/mastermindx-market-intelligence/macro/blob/1f536032d446e2b51bda47f0575e371f0c4a0aae/agentos/decisions/DEC-REPAIR-IS-ORTHOGONAL-AND-FIRST-CLASS.md

Additional reuse references:

- [#7068 generated China hotfix](https://github.com/mastermindx-market-intelligence/macro/pull/7068)
- [#8021 missing-evidence repair](https://github.com/mastermindx-market-intelligence/macro/pull/8021)
- [#8721 held pullback-depth work](https://github.com/mastermindx-market-intelligence/macro/pull/8721)
- [October 17 proposed architecture contract](https://github.com/mastermindx-market-intelligence/macro/blob/1f536032d446e2b51bda47f0575e371f0c4a0aae/research/grey_deer/risk_radar_architecture_contract_20261017.md)
- [Existing workstream](https://github.com/mastermindx-market-intelligence/macro/blob/1f536032d446e2b51bda47f0575e371f0c4a0aae/agentos/workstreams/WS-GREY-DEER-RISK-INTELLIGENCE.md)

Production evidence hashes:

- China: `2588a511b70993a844f9aa37c178357ed396ff39e991bc107293c29e7e228776`, 265,909 bytes.
- HK: `6f6e5cfcb20107dab09af6a3e636ca2eb6fe35b9fb343c53536094cd678a624f`, 257,288 bytes.

Independent math review: root `china-hk-risk-receding-audit-20261022`, run `cn-hk-recovery-math-audit-20261022-01`, accepted response SHA-256 `4a57d24d1dc15c0173adf99a7bccc29f5a3684ff5506363bc72646e5881537c9`. Acceptance is scoped to verified structural findings. The worker assumed seven-session lookbacks; principal verification used the actual five/ten-session constants. The worker’s literal “one variable” causality claim and unverified aggregation examples were not adopted. The complete returned response and acceptance scope are preserved in the verification receipt.
