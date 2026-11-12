# OLI S0 first-forming preregistration candidate

Date: 2026-10-04  
Operation: `oli-existing-owner-recovery-20261003-astra-001`  
Status: **DRAFT_NOT_REGISTERED / OUTCOMES_UNREAD / ZERO_AUTHORITY**  
Parent: Macro #8328 / PR #8333 / MAS-262.

This is a records-only preregistration **candidate**, not an accepted Setup Species,
TrialLedger row, QLedger claim, B1 episode, signal, recommendation, rank, sizing rule,
Plan, position, alert, or outcome study. It freezes the first bounded denominator and
decision-time relation far enough to prevent later hindsight selection while preserving
all current owner/admission gates.

## 1. Existing owners reused

No OLI store or event namespace is introduced.

- Observation tape: existing monthly PIT store
  `data/us_prophet_rank/candidates/YYYY-MM.parquet`.
- Candidate-pool semantics: `engine/us_candidate_lanes.py`,
  `POOL_DEFINITION = "us_candidate_pool_v1"`.
- Refusal vocabulary: existing `engine/prophet_bridge.py`; `not_ready` is the
  owner-defined refusal for `buy_soon`, `await_confluence`, and `watch`, with the
  user meaning “Setting up, but the entry hasn't come”.
- Decision-time source law: K3-E `prophet_stamp_date` in
  `contracts/opportunity_evidence/slot_registry.v1.json`, owner store
  `data/us_prophet_rank/candidates/`, recorded clock class `belief_or_build`,
  lawful modes `live` / `retrospective_research`, maximum recording lag 2 days.
- Identity: existing Data OS `IdentitySpine` from
  `engine/us_candidate_episode_intake.py`; no ticker is an identity.
- Trigger/episode truth: canonical B1 `engine/us_candidate_episode.py`, including
  one-active-per-security/identity-epoch law and canonical TURN WATCH `OPENED`
  events.
- Scientific species/promotion: existing Setup Species / TOI / Evaluation owners.
- Prospective prediction scoreboard: existing QLedger, after its separate versioned
  OLI relation decision. No claim is emitted by this artifact.

## 2. Formation predicate frozen before outcomes

A row is a **formation-candidate row** only when all four owner-native facts on the
same immutable PIT row are true:

```text
pool_definition == "us_candidate_pool_v1"
AND pool_lane == "forming"
AND pool_in_buy_lane == true
AND pool_headline_reason == "not_ready"
```

This is intentionally narrower than every row whose lane happens to be named
`forming`. It does not include `conviction_low`, `grade_low`,
`pointing_down`, fail-closed/data-integrity states, `ran_too_far`, or
`stood_down`.

The predicate adds no threshold, score, fitted parameter, or future-return condition.

## 3. Decision cut and immutable source reference

For one source row:

- `t0_source = prophet_stamp_date`;
- `t0 = stamp_date` under the K3-E owner/clock law;
- source object = exact monthly candidate part containing that row;
- source receipt = digest of the exact source part plus the row's existing
  candidate-source identity/receipt when materialized through the incumbent intake;
- later rewrites/corrections do not backdate the original decision cut.

A row whose source object, recording clock, or required digest cannot satisfy the
K3-E source law is **UNAVAILABLE**, not a negative observation.

## 4. Identity relation — no ticker surrogate

The formation row's `ticker` is resolved at `stamp_date` through the same
Data OS membership alias/issuer pair B1 intake uses:

```text
VendorAliasTable.resolve("membership", ticker, on=stamp_date)
IssuerMaster.issuer_of_security(security_id)
```

The pre-B1 intake identity is preserved exactly as the current owner represents it:

- canonical `security_id`;
- canonical `company_id`;
- `identity_epoch = "epoch_0"`;
- `identity_epoch_state = "provisional"`;
- current `stock_identity.fingerprint_spec.v1` schema/hash.

Failure to resolve security or issuer is typed identity-unavailable and excludes the
row from an evaluable cohort. This artifact does not “fix” identity by ticker/date
matching or mint a permanent epoch from the provisional state.

The referenced candidate-source key remains the incumbent shape
`candidate:{stamp_date}:{ticker}:{board_definition}`; OLI does not mint a new event ID.

## 5. First-forming unit

The tentative scientific unit is **one first formation per canonical
security + provisional identity epoch within an admitted source era**.

`first_forming_at` is the earliest qualifying `stamp_date` for that identity after
the admitted source-era start, subject to all of these conditions:

1. the exact PIT row satisfies section 2;
2. the Data OS identity relation in section 4 is resolvable;
3. no canonical B1 TURN WATCH `OPENED` event for the same security/epoch was already
   known at or before that decision cut;
4. later qualifying nightly rows are dependent history of the same formation, not
   additional independent opportunities.

The admitted source-era start/end are **not yet promoted by this candidate**. Prior
read-only feasibility work observed the predicate in the current Aug-Oct tape, but
source-era admission remains an Evaluation/Data owner gate.

## 6. Positive transition reference, not yet an outcome definition

The only nominated positive transition is a **later canonical B1 TURN WATCH
`OPENED` event** joined by exact canonical security + identity epoch and carrying
its native `event_id`, `source_event_id`, `known_at`, `recorded_at`, source
receipt, and generation identity.

It must satisfy `OPENED.known_at > first_forming_at`. A B1 event already known at
or before t0 disqualifies the row from the pre-B1 risk set rather than becoming an
instant success.

This transition nomination is not yet a registered dependent variable. No horizon,
censoring rule, return label, benchmark, cost model, or economic-success definition is
created here.

## 7. Explicit non-outcomes

Until owner registration is accepted, none of these may be relabeled as scientific
failure/success:

- a later nightly row disappears;
- `pool_lane` or `pool_headline_reason` changes;
- `ran_too_far`, `stood_down`, `conviction_low`, or another refusal appears;
- no B1 event appears within an analyst-chosen interval;
- a public model plan appears or closes;
- B4 is `UNAVAILABLE_DATA`, `WAIT_PULLBACK`, or another current-entry state;
- price rises/falls after t0.

Those may become separately registered endpoints only through the existing science
owner before outcomes are opened.

## 8. Blocking gates before any outcome access

**G1 — Prophet semantic-owner acceptance.**  
The exact section-2 predicate must be accepted (or narrowed) by the current Prophet
US owner as a zero-authority research landmark. Existing request: #6805 comment
5976844334.

**G2 — Setup Species binding.**  
The Setup Species / TOI owner must name an exact existing `species_id + version`,
or explicitly HOLD and version a lawful new species through the incumbent process.
Current registry search found no exact binding for `us_candidate_pool_v1`,
`turn_watch_reset_low`, or `pool_headline_reason`. Existing request: #6817
comment 5976861635. No species is created here.

**G3 — data/source-era admission.**  
Freeze exact source-era boundaries, eligible population, coverage/exclusion
denominators, correction rules, and Data OS identity eligibility. Missing source is
not a negative observation.

**G4 — evaluation law.**  
Before outcomes, freeze the transition horizon/censoring, return/benchmark ruler,
execution/cost model where relevant, baseline/control, sample/power plan, search
budget, economic minimum, harmful-tail margin, multiplicity and formal look
schedule. This document intentionally supplies none of those by guess.

**G5 — QLedger relation.**  
The Evaluation/QLedger owner must accept the versioned
opportunity + strategy + landmark + evidence relation and semantic-conflict law.
Legacy claim IDs remain unchanged. Zero OLI QLedger claims exist now.

Every gate is blocking for protected outcome access. Engineering/Product P0 may
continue independently because this artifact grants no action authority.

## 9. Falsifiers before the first outcome read

The candidate is narrowed or rejected without opening outcomes if any of these is
established:

- Prophet owner says the section-2 predicate is not a lawful interpretation of its
  existing state;
- no exact Setup Species can bind the nominated formation/trigger semantics without a
  new owner version;
- immutable PIT history cannot establish the source/recording clock claimed here;
- Data OS cannot resolve historical subject identity without unacceptable ticker
  surrogate assumptions;
- the nominated B1 relation cannot be joined causally without using future knowledge;
- repeated nightly rows cannot be collapsed into a deterministic first-formation unit
  without outcome-dependent choices.

A negative result on any of these is useful: preserve the HOLD and redesign before
outcomes rather than rescuing the construction after seeing them.

## 10. Authority ceiling

This candidate cannot rank, admit, open entry, size, trade, alert, modify a Plan,
modify a watchlist/portfolio, or publish a probability. It cannot make the current
B4 control-only risk constant actionable. It cannot waive W1 #7107, W2-0 #7094,
TURN WATCH #7227, Phase 22, Top OOT, source-rights, identity, or data-admission gates.

**OUTCOMES_UNREAD remains load-bearing.**
