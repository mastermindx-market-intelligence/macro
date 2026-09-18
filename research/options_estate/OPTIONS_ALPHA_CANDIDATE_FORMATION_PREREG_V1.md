# Options Alpha Candidate Formation v1 — preregistration

**Date:** 2026-09-18  
**Operation:** `options-alpha-candidate-formation-prereg-v1-20260918-sol-001`  
**State:** PREREGISTERED_INACTIVE — records/contract only; no composer, candidate feed, score, rank, alert, issue, trade, deployment, or production claim.  
**Governing source pin:** Macro `348913be88d6486a68f63e57b2375c4b5fa6879f`.  
**Machine policy:** `research/options_estate/options_alpha_candidate_formation_policy_v1.json`.  
**Schema:** `contracts/options/options.alpha_candidate_formation_policy.v1.schema.json`.

## 1. Purpose

OA-0 deliberately left the exact research-candidate formation rule unfrozen. That was correct: a candidate threshold selected after reading campaign outcomes would turn the next “prospective” result into a selected backtest.

This preregistration closes that specific scientific dependency without activating OA-1C. It preserves the accepted architecture:

`Flow -> Package -> Positioning -> Candidate -> Outcome -> Calibration -> Decision Support`

and the harder distinction:

**Attention != research candidate != calibrated probability != promoted signal != operator issue != trade.**

The output is a zero-authority research-candidate decision. It is not a bullish/bearish call, a confidence score, a Prophet pick, a Tactical/Radar event, or an option recommendation.

## 2. Why this rule is intentionally small

The canonical live-flow event has already crossed an existing root-class premium-floor notability gate. Campaign v2 then preserves every valid exact-contract/session campaign revision without adding a second premium, frequency, side, unusualness, or outcome threshold.

OA candidate formation therefore must not add an outcome-tuned “bigger is better” score on top.

The minimal additional semantic distinction is **persistence**. The current source engine already defines an event-level `repeated` state when the same exact contract becomes notable again. Campaign v2 preserves that state and publishes `descriptive.repeated_count`.

V1 uses that existing state instead of inventing a new recurrence window or numeric score:

> A campaign becomes eligible for a research candidate at the first prospective campaign revision whose `descriptive.repeated_count >= 1`, provided the final member can be joined to real measured trade/NBBO microstructure with at least one source-valid print and at least one valid measured NBBO print.

This is a formation rule, not evidence that recurrence predicts return.

## 3. Frozen formation rule

A revision may form a `research_candidate` only when all of the following are true:

1. The source row strictly validates as canonical `options.signal_campaign/v2`.
2. The campaign is in its prospective source phase and lies after both the policy and later activation fences in §4.
3. Its source-prefix receipt and exact final-member identity are valid.
4. `descriptive.repeated_count >= 1`.
5. The final member's exact `source_event_id` joins to `options.trade_nbbo_microstructure/v1` measured at that event's decision-time source path.
6. That measurement has `source_print_count >= 1`, `nbbo_valid_print_count >= 1`, and finite `nbbo_premium_coverage > 0`.
7. Every formation evidence leg was available no later than the candidate decision cutoff.
8. No upstream artifact carries authority incompatible with this research-only view.

The first campaign revision that satisfies the complete rule is frozen as the candidate-forming revision.

Candidate identity is:

`sha256(candidate_schema, policy_id, campaign_id, first_qualifying_campaign_revision_id)`

Later campaign revisions update that same candidate; they do not mint a new candidate merely because more evidence arrived.

## 4. Two prospective fences

Merging a preregistration does not retroactively make known outcomes prospective.

V1 therefore requires two forward fences.

**Policy fence.** The policy becomes eligible no earlier than the first NYSE session open after this exact preregistration lands on protected `main`. Any campaign formed before that boundary permanently abstains under this policy.

**Activation fence.** A later OA-1C implementation must durably record its own activation receipt. Its candidate denominator begins no earlier than the first NYSE session open after that activation receipt. A campaign formed before activation can never be cured by observing it later.

This means there is no historical “backfill” of candidates after implementation. Historical rows remain useful for diagnostics and schema tests only.

## 5. Why there is no new 60/80/90% NBBO threshold

OA-1T deliberately publishes both the measured shares and how much source premium supports them. No accepted source law establishes a candidate-level predictive cutoff for 60%, 80%, 90%, or any other coverage value.

V1 therefore requires **measured evidence to exist** but does not tune a minimum coverage percentage beyond `> 0`.

A low-coverage candidate must display that low coverage. It may not convert missing premium into neutral flow, may not hide the denominator, and may not describe an aggression share as broadly representative without its coverage beside it.

A later policy may introduce a stricter quality floor only through a new version and a new prospective cohort.

## 6. Evidence that cannot originate a v1 candidate

The following are context or description only and cannot independently cause formation:

- Terminal Attention/Salience or `flowScore`;
- `at_ask_share`, `at_bid_share`, or aggression balance crossing a chosen directional threshold;
- call versus put right;
- soft `~buy` / `~sell` tape signing;
- `swept`;
- volume greater than prior OI or `vol_gt_oi_ratio`;
- GEX, gamma flip, walls, skew, term structure, IV, or other positioning/volatility context;
- package association or an LLM interpretation;
- later settled OI;
- Tactical/Radar setup state;
- any historical or prospective outcome.

Those fields may be displayed when their own contracts permit it. They do not become a hidden composite.

## 7. EOD and Package policy

Settled EOD evidence is **not a v1 formation predicate**.

Until AD-1T2 has production-accepted its real consumer/availability path, candidate output must represent settled EOD context as unavailable/not-admitted rather than reading a convenient local file.

After AD-1T2 acceptance, prior-known EOD evidence may be added as supplemental context only when its own availability time is no later than the candidate cutoff. Later settlement is a post-decision update.

Package evidence is likewise supplemental in v1. Unresolved package state is allowed and visible. A sweep-like flag is not package proof and cannot satisfy candidate formation.

These choices do not waive the separate Package or AD programs; they prevent those unfinished layers from silently determining candidacy.

## 8. Clock contract

For the first qualifying campaign revision:

- `decision_at = campaign.formed_at`, which campaign v2 defines from its final member's availability;
- formation evidence must satisfy `evidence.available_at <= decision_at`;
- `available_at` for the candidate is the durable candidate-view write time;
- `published_at` is the later consumer-publication time.

A later wrapper/build/publication clock cannot make an older source fact fresh.

The final product must preserve event, observation, decision, availability and publication clocks rather than collapsing them into one `asof`.

## 9. Candidate, abstention, and degraded states

A valid prospective campaign that has not reached persistence is `abstain / NO_REPEAT_PERSISTENCE`.

A persistent campaign whose final member lacks measured microstructure is `degraded` or `abstain` with `FINAL_MEMBER_MICROSTRUCTURE_MISSING`.

A measured block with zero valid NBBO observations is not neutral and not zero aggression; it is `NO_VALID_NBBO_MEASUREMENT`.

Invalid clocks, invalid receipts, explicit source stale/unavailable state, pre-fence campaigns, and upstream authority violations fail closed under the reason-code vocabulary in the machine policy.

“No candidate” is a correct product result.

## 10. Corrections and later evidence

The initial candidate receipt is immutable as the decision-time formation record.

A later campaign revision, source correction, Package resolution, EOD settlement, or calibration result is an append-only/versioned update under the existing owner. It may not rewrite the original formation rationale or make a pre-fence campaign prospective.

Outcomes join only after candidate identity and decision evidence are frozen. Candidate formation code must not read campaign outcome ledgers, episode outcome ledgers, qledger grades, or option P&L.

## 11. Authority ceiling

Every v1 candidate has zero authority to:

- score or rank;
- create an Options Issue Desk issue;
- create a Tactical/Radar event;
- publish a pick;
- size or trade;
- train/feed Prophet or Neural Web;
- claim bullish/bearish probability;
- compute or imply exact-option P&L.

The feed may order records chronologically for presentation. Chronology is not ranking.

## 12. Relationship to the existing sparse exact-option selector

`OPTIONS_SPARSE_SELECTOR_PREREG.md` is not this policy.

That selector is a private exact-option research-review truth gate requiring Market Memory, an admitted option mark, and shadow lifecycle evidence. It can produce an internal `propose` decision under its own frozen policy.

OA-1C is the broader Options Alpha research-candidate product derived from the canonical campaign and measured source evidence. It must not import the sparse selector's private lifecycle/mark requirements, proposal cap, benchmark identity, or decision semantics merely because both reference campaign v2.

The reusable pattern is only the scientific one: forward fences, immutable first qualifying identity, one decision per frozen candidate, explicit abstention, and zero inherited trading authority.

## 13. Relationship to Tactical Intelligence

This policy does not block or originate the Tactical program's price-first work.

A later Tactical experiment may consume a typed Options Alpha candidate/evidence reference as an options witness only under its own frozen comparison. Options must demonstrate incremental value over the price baseline. A research candidate never grants an entry trigger, an underlying direction, or 0DTE/short-dated instrument authority.

## 14. Implementation entrance and hold

This preregistration **does not open OA-1C implementation by itself**.

Before a composer implementation may activate, the existing owners must reconcile:

- the OA-1T measured source/consumer path and its unresolved collection completeness/freshness issues;
- the current campaign integrity/publication/runtime condition;
- any current source-path collision;
- AD-1T2 before settled EOD context is admitted.

The implementation must reuse the existing campaign/event/outcome/publication owners. No candidate database, second campaign identity, second event ledger, new scheduler, or second options collector is authorized.

## 15. Required implementation falsifiers

Before activation, real implementation tests must prove at least:

- singleton/no-repeat campaign -> abstain;
- first persistent measured campaign -> exactly one stable candidate;
- later same-campaign revision -> same candidate identity, versioned update;
- source reordering -> byte-identical decision;
- pre-policy and pre-activation campaigns -> permanent abstain;
- delayed observation cannot cure an old formation clock;
- missing final-member microstructure -> explicit degraded/abstain;
- zero NBBO-valid measurements -> no synthetic aggression;
- low but nonzero coverage remains visible and does not create a score;
- soft side, call/put right, `swept`, OI/GEX/skew and Attention cannot independently originate;
- EOD absence before AD-1T2 does not become neutral/zero and does not change v1 formation;
- outcome mutation cannot change candidate formation;
- later evidence cannot change the original formation receipt;
- every authority flag remains false;
- candidate feed failure cannot silently fall back to `options.prophet_shadow/v1`.

## 16. Completion boundary

This records wave is accepted only when the preregistration is reviewed and lands on protected `main`; only then can its policy fence be resolved.

That still does **not** make Options Alpha functional. Parent completion remains a natural source-to-candidate-to-Terminal-to-outcome path with truthful degraded/abstention behavior and later prospective evaluation.
