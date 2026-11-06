# 14 — Mastermind / Prophet interface

## 1. Four questions, four meanings

| Question | Meaning | Authority |
|---|---|---|
| Desirability | Do the business/exposure, valuation and higher-timeframe thesis warrant consideration? | Existing Mastermind/Prophet selection and ranking |
| Entry availability | Is this specific strategy/candidate permitted to enter under its accepted geometry, state and required facts? | Existing B4 availability owner |
| Tactical path | What is likely to happen over the next minutes/hours, at what uncertainty and adverse cost? | Qualified tactical forecast/evidence attached through Radar |
| Execution | Can the intended action be completed at reachable prices with acceptable spread, depth, latency and restrictions? | Existing execution/data controls and the user's action policy |

A favorable tactical forecast cannot make an undesirable security desirable, reopen a closed B4 strategy, manufacture a candidate or choose portfolio size. A desirable security can have an unfavorable entry path. A correct direction forecast can still be uneconomic to execute.

## 2. Existing interfaces to reuse

`engine/prophet_entry_availability.py` already supplies `prophet.entry_availability/v1`; `prophet_entry_availability_sources.py` composes canonical runtime owner facts and verifies identity. It binds to the candidate/strategy geometry and does not rank the universe. Missing mandatory facts fail unavailable; ticker equality is not a fallback identity proof. [P19–P20]

The legacy Mastermind `portfolio/entry_engine.py` is a new-buy, subtract-only brake; `entry_quality.py` is its absorbed advisory predecessor. Their optional-input fail-open semantics differ from B4's required-fact fail-closed semantics. Reopening a second timing score or forcing one missingness policy across both would regress the architecture. [P02–P03]

Current draft PTSE #8364 at `22e217a3f5ce0c27a8ad0ea0a2a9a2c9f8074ffb` already contains a pure US/DAILY/REGULAR/H5/NEW_ENTRY context compiler reading B3/B4 and options-owner receipts. Architecture #8325 is also an existing draft. PTSE's H5 and B4's 2–15-session strategy horizon are deliberately distinct. Its B0 source/protocol result is `NON_EVALUABLE`, not a timing null. These drafts are not merged/live authority. [P48–P50]

OLI #8333 likewise relates Data OS identity to native B3, optional B4 and OEV evidence with all authority false. Radar episode IDs and B3 episode IDs belong to different domains. A new timing view must use an explicitly admitted relationship, not assume equal string shape or ticker makes them interchangeable. [R33; I8328; PR8333]

## 3. Proposed read contract

The tactical consumer relation should contain native B3 candidate reference, B4 availability reference/version, canonical security-binding receipt, optional TOI occurrence relation, Radar episode/prediction references, strategy direction, time horizon, valid-from/expiry and source/model-known times. It does not reproduce those owners' state. On mismatch, stale reference, unsupported session or absent required binding, return unavailable with the exact cause.

Higher-timeframe consumers may initially display the annotation beside the canonical candidate. Any later permission for a tactical state to close, defer or reopen entry requires an explicit accepted consumer policy and independent evaluation on that candidate population. The annotation's default authority remains false for ranking, selection, sizing, trading and entry gates.

## 4. Decision-support matrix

| Desirability / B4 / tactical evidence | User-facing interpretation | Allowed initial effect |
|---|---|---|
| Desirable; B4 open; qualified path favorable; execution eligible | “Entry window improving,” with a horizon and invalidation condition | Explain context; no autonomous trade |
| Desirable; B4 open; path adverse or extended | “Wait for a better entry” / “Extended from the setup” when its rule is qualified | Advisory context; any actual gate effect needs consumer acceptance |
| Desirable; B4 closed | “Setup entry is closed,” with owner reason | Preserve B4 decision even if local bounce looks attractive |
| Desirable; B4 or tactical fact unavailable | “Entry timing unavailable” or “Not yet estimated” | No invented approval or negative thesis conclusion |
| Undesirable/unselected; strong local reversal | “Tactical move observed” in the appropriate discovery context | No promotion into Prophet ranking/candidate population |
| Existing position | “Position path improving / weakening,” conditional on its declared horizon | Position context; no retroactive new-entry gate, sizing or exit execution |

Use current owner-issued state names in payloads and plain language in the product. “Tactically favorable” has no permission content by itself. A theoretical `ENTRY_OPEN` string emitted by a new model would be a duplicate authority and is prohibited.

## 5. Evaluation and transfer

Evaluate the tactical family both on the broad descriptive population and on the exact native candidate cohort a consumer proposes to use. The latter can have different base rates, liquidity, holding periods and selection bias. A probability calibrated on all intraday names is not automatically calibrated for Prophet candidates.

Keep the initial candidate and common terminal fixed when measuring buy-now versus waiting. Preserve all unfilled and unavailable candidates in the intended-population accounting. Do not select a new stock after a waiting policy misses its move and compare it to the original buy-now cohort. Portfolio substitution is a separate strategy research question.

Adverse path, entry availability and desirability remain separate in stored outcomes and UI. The prior near-low and Bottom Confidence evidence supports precisely this separation; the DNR Prophet/POP merge and outcome-audition bans protect it. [P04–P05; P11]

## 6. Acceptance and rollback

Contract tests must demonstrate correct and mismatched identity, stale B4, missing optional options context, missing mandatory availability, incompatible horizons, corrected source, invalidated Radar episode and an existing position. Real-path proof follows native candidate → B4 → read-only tactical relation → Terminal/consumer rendering, preserving all original ranking/candidate bytes.

Rollback removes or disables the optional relation and restores the accepted prior display. It does not rewrite candidate histories, degrade a higher-timeframe thesis into a tactical failure, or erase evidence. No consumer authority or portfolio behavior changed in this commission.
