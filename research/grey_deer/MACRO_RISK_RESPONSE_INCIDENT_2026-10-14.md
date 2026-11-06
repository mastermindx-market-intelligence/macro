# Macro risk-response incident — 2026-10-14

## Finding and decision

The Chairman's screenshots show a decision-support failure: weak participation, elevated stress readings and stale rotation evidence coexist with a prominent 50 / Mixed headline and generic trading guidance. The correction is not to manufacture a 99 or label every correction a systemic crash. It is to distinguish observed selling, slower background conditions, forecast probability and data confidence, and ensure that observed deterioration reaches the user's primary decision surface.

This investigation establishes source mechanisms and a reproduced presentation defect. It does not establish the exact production revision, every Oct-14 runtime gate value, or a newly validated trading strategy. The supplied screenshots are the incident observations. The later closing-market assessment must not be treated as information available when those screenshots were captured.

## Source and scope

- Original operation: `macro-risk-response-20261014-c1`, Chairman's current Oct-14 Web commission. No transfer of an older Grey Deer worker or PR is asserted.
- Protected procedure pin: Mastermind `78388ac29f7e54c9dfe7799a8e4769fb46d4aed6`.
- Macro source base / local HEAD: `9e8f22ec1fc03c046bc1f38b3f397d5f6c9965ef`.
- Later main read: `a4065a0f04790e7556b7615b50dfb3ded49853e5`. Git blob equality verified for `engine/market_state.py`, `engine/risk_radar.py`, `scripts/build_risk_state.py`, and `scripts/build_rr_banner.py`; these inspected mechanisms had not changed.
- Existing owners remain authoritative: Risk Radar, Market State, the existing live builder, warning publisher/client, sector intelligence and Grey Deer research. No second risk engine, lifecycle, queue, retry owner, memory store, or alert transport is created.

## Reproduced mechanisms

### 1. The blend explains 50 but does not justify a calm tactical interpretation

`engine/market_state.py:WEIGHTS` is trend .24, risk .18, volatility .16, breadth .16, liquidity .14, downturn guard .12. Applying the screenshot values 68,27,84,0,38,80 gives 49.54, rounded to 50. Calm volatility and a benign downturn guard can offset weak participation. `_TF_W` assigns 70% of the trend component, not the total score, to weekly/monthly readings. This is a slow-background construction being asked to carry a fast trading-state message.

Breadth zero is a normalized component score, not a claim that no stocks are advancing. Risk 74 is not 74% crash probability. The screenshot's 21-day probability of a >=5% index pullback is not the same target as an ongoing short-horizon technology sell-off or a drawdown in one stock. These quantities must not be numerically conflated.

### 2. Loud Risk Radar status waits for a broad-market breakdown gate

`engine/risk_radar.py:context_gate_live` requires SPY below its 200-day moving average AND weak breadth. `_resolve_state_row` caps a stronger state at `caution` when that gate is false. Source inspection proves that rule, not that the exact gate bit has been recovered from the screenshot's runtime.

The rule can be retained as a calibrated broad-market escalation condition without making it a prerequisite for reporting a verified Nasdaq/semiconductor breakdown. Do not bypass `can_force` or turn an ungated score into new forecast/sizing authority. Instead, explicitly project already measured current-state evidence, with scope and source dates, through the existing owner chain.

### 3. The publisher suppresses even Elevated warnings

At current main, `scripts/build_rr_banner.py:RR_ALERT_FROM` is `risk-off`; `build_alert` returns None for any other state. A read-only call of the actual function reproduced: caution/74 -> no banner; elevated/85 -> no banner; risk-off/88 -> banner. This is not a browser test, but it proves the publisher threshold.

The same builder writes `alert:null` on a source-read failure. This avoids retaining an undated extreme banner but also conflates unavailable evidence with an empty warning channel. The replacement contract is bounded, visibly dated last-known warning retention plus a separate unavailable status, never indefinite alarm retention and never a silently fresh all-clear.

The module prose says price OR breadth; the actual live gate uses AND. The source function, not the stale prose, governs the diagnosis.

### 4. Mixed discarded the existing breadth warning

At the source base, `_participation_scope` qualified only US RISK_ON. A move to MIXED returned None even with the same verified breadth=0 input. Generic Mixed copy then replaced the specific warning. Four new focused tests first produced three expected failures and one passing control.

A local candidate now preserves the measured 50/MIXED result while qualifying verified weak participation and unverified participation separately. Supportive/uneven MIXED, RISK_OFF and other countries retain their existing contracts. Existing source-clock checks remain unchanged. The wording is bilingual and reaches the existing headline, subline and action fields without a new client or layout.

### 5. Current quotes do not establish current context

The screenshots date the main settled reading Oct13 but rotation Oct8. The live builder selects the nightly snapshot when there is no active splice, including closed/no-usable-quote conditions. Its live recomputation does not make every slow input newly observed. The exact production fallback event is not recovered here. Source-to-screen time, observation time and generated time must remain separate; a live price strip must not visually vouch for an old sector panel.

Other screenshot tensions require source/horizon reconciliation: credit level versus spread change, rate-path level versus recent repricing, sentiment level versus worsening momentum, sector rank versus rank change. Different measures can legitimately disagree; the product must explain their direction and date rather than flatten them into contradictory calm instructions.

## Existing delivery work, not a new replacement program

PR #8132 remains Draft/unmerged at inspected head `639aaed06ce7754110d3bd6e94a0b704bb6c7760`. Its body expressly records that its broader warning projection is not connected to the production publisher/client, and that the candidate alone does not make caution/80 produce a live warning. Its historical test claims are not production proof and were not independently rerun here.

The Oct14 Opus W7/W8 Agent OS handoff records real research/prospective-lane work and explicitly says those research waves ship no consuming production surface. It leaves W6 warning delivery in the #8132 lineage after publication continuity proof. Preserve #8132/#7029 and other named release holds; do not restart frozen studies or duplicate active research workers. Today's incident adds acceptance requirements and urgency, not permission to bypass those holds.

## Ordered repair contract

### A. Restore truthful foreground communication

First complete the existing warning projection/publisher/client path for non-extreme observed deterioration. The main view must distinguish tactical selling pressure, slower blended backdrop, probabilistic outlook and coverage. An active observed warning must not disappear because the blend is Mixed, VIX is low, news is newer, the modal is closed, or an earlier notice was dismissed. Surface actions should be evidence-scoped risk review, existing stop discipline and setup invalidation, not unvalidated numerical liquidation or model-originated sizing.

### B. Repair source continuity and stale-state behavior

Give every displayed source its market/session, observation time, available-at time, publication time and freshness state using existing artifact contracts. Show last verified warning with an age and bounded expiry when a feed fails. Do not erase an intraday warning with an older nightly snapshot at the close. A later valid recovery can clear it; a failed fetch cannot prove recovery. Rotation dated Oct8 must be labeled stale at the main glance level, not only in a modal footer.

### C. Separate reaction from prediction inside current owners

Reuse existing trend, breadth, leadership, sector-relative-strength and drawdown evidence. Make multi-session selling, failed trend support and defensive outperformance explainable as observations. Do not require SPY<200dma to state that Nasdaq/semiconductor leadership has deteriorated. Keep crash probabilities and systemic escalation separately calibrated. Treat AI infrastructure/hardware, mega-cap platforms, software/agents and cybersecurity as distinct exposures when the existing taxonomy supports it; do not assume all technology shares one state. Relative performance is not proof of net fund inflows.

### D. Demonstrate behavior, not just generated fields

Release is not done unless the publisher payload, long-open browser, main headline, What To Do, modal and chat read the same source-qualified state. Exercise EN/ZH and dark/light; stale, delayed, missing, duplicate and out-of-order inputs; the live-to-close boundary; news collision; dismissal; explicit recovery and bounded retained warnings. Run the motivating Oct episode using only evidence available at each replay timestamp. Compare with ordinary pullbacks and recovery episodes so sensitivity does not become permanent alarm. Record time to first useful warning, time spent falsely calm, false-warning duration, coverage failures and delivery latency. Those are acceptance measures, not results claimed by this investigation.

Forecast/position-sizing promotion remains a separate point-in-time, episode-aware, costed, walk-forward evaluation. No threshold is selected merely to make Oct14 print red. No previous frozen trial is rerun without its original owner's lawful correction/revision procedure.

## Local candidate and verification

Changed implementation: `engine/market_state.py`; three existing test modules. No scoring, Radar, quote-admission, publisher, client or production-data modification.

- Initial regression reproduction: 3 failed, 1 control passed.
- Focused owner/projection/copy-sync run: 25 passed.
- Added actual-JavaScript tests against template and shipped copies: 8 passed (synthetic DOM and supplied inputs; not a full browser or production).
- Broader pre-addition run: 74 passed, 2 failed. The two failures expect synthetic-timestamp quotes to remain usable, while unchanged `engine/live_overlay.py` rejects them. `research/grey_deer/verify_oct14_quote_baseline.py` reproduced the same two failures using the original frozen Market State owner. They remain unresolved; no guard was weakened.
- `git diff --check` passed. Existing CI jobs already name the changed test modules; CI itself has not run for this unpublished candidate.
- Independent retained Fabric review `risk-response-mixed-review-20261014-c1-01`: MiniMax/ubuntu3, rc0, no material issue found in supplied scope. Parent adjudicated its limitations and accepted the bounded review via the same ID; status readback returned ACCEPTED / accepted_by=reviewer. This is not independent test execution, full integration review or production approval.

Candidate hashes and the review limits are in `RISK_RESPONSE_REVIEW_ADJUDICATION_2026-10-14.md` beside this report.

## Recovery frontier and constraints

Workspace: `/Volumes/Mastermind 2/agent-workspaces/macro/web/macro-risk-response-20261014-c1`; branch `sol/web-macro-risk-response-20261014-c1`; local HEAD remains the source base. Source and notes are local, uncommitted and unpublished.

The typed publication-status precheck returned REFUSED / NOT_APPLIED / TYPED_GIT_PRECHECK_REFUSED. No commit/push was attempted and no alternate source-publication carrier was used. This is the immediate release constraint, not a reason to declare the product repaired. The exact permission-owner remedy is not proven here. New local Agent OS/source records are NOT_CANONICALLY_PERSISTED to main.

DO_NOT_REDO: do not reacquire a workspace or duplicate the review; the review is consumed/accepted. Reuse the proved defect and unchanged owner blob evidence. Do not treat 25+8 tests as a full-suite result, replay historical study trials, remove existing release holds, or use a new carrier to bypass the publication refusal. Next source release action is the same-workspace publication route only after actual precheck clearance, with the two existing test-contract failures reconciled by their owner and required CI/production checks completed. Broader activation remains in the existing #8132/W6 path; assessment alone is not activation.

## Durable incident receipt

The diagnostic/frontier comment was posted once to existing Macro PR #8132 and read back through the original GitHub comment endpoint: comment `6179119830`, created `2026-10-14T21:41:43Z`, https://github.com/mastermindx-market-intelligence/macro/pull/8132#issuecomment-6179119830 . This is durable GitHub implementation evidence, not source publication or release clearance. The local Agent OS handoff validated with the whole store: 1,827 records, zero errors, 153 warnings (including sparse/join and existing review-date warnings), exit0. Local changes remain uncommitted/unpublished.
