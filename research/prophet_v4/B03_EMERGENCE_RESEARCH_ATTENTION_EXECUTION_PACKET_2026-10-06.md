# B03 Execution Packet — Emergence / Research-Attention Projection

**Date:** 2026-10-06  
**Parent research carrier:** PR #8495  
**Program owner:** existing R6 B03 / Prophet visibility + private-delivery owner  
**Current main inspected:** `macro@1bd2813bfffc228b4dd9d70e1bb43d4e66cb0a6e`  
**Authority:** implementation plan only; zero rank, gate, plan, sizing, execution, deployment or experiment-promotion authority  
**Do not create a new carrier until current B03 custody/reviewer/effects are reconciled.**

## 0. Outcome

Extend the **existing lossless searchable opportunity field** so a user can see:

> **Important emerging candidate — entry not open yet**

without:

- changing candidate membership;
- inventing a score;
- inventing a candidate episode;
- changing C1 ordering;
- changing Prophet admission;
- bypassing Entry Availability;
- duplicating B04 evidence;
- duplicating Live Entry Radar RP1.

The golden acceptance case is NVDA Sep-04 → Sep-23.

---

# 1. Exact incumbent surfaces

## 1.1 Lossless pool

Owner file:

`engine/us_candidate_lanes.py`

Incumbent function:

`build_candidate_pool(...)`

Current invariant:

> `sum(lane_counts.values()) == len(rows) == eligible`

Current membership/order basis:

- `eligible_order` is the board's existing pre-cap blend order;
- `pool_rank` preserves that order;
- no off-lane Prophet score is invented;
- buy rows are not mutated.

**Ruling:** do not make emergence a membership predicate inside this function.

## 1.2 Existing historical continuity

Existing functions already support:

- `load_pool_history(...)`
- `graduation_fields(...)`

Existing fields include:

- `days_in_pool`;
- `score_delta_5d`;
- `lane_transitions`;
- `prev_lane`;
- `first_seen`;
- `window_truncated`;
- `window_oldest`.

This is sufficient to express “how long has this candidate remained under observation?”

Do not create a second continuity ledger.

## 1.3 Browser projection

Incumbent function:

`project_candidate_visibility(board, archive=None)`

Current properties:

- fail-closed source/session checks;
- strict field allowlist;
- no raw upstream field leakage;
- off-buy rows retain honest null score;
- source digest binds the exact projected object;
- display-only semantics.

This is the correct B03 consumer seam.

## 1.4 Canonical episode identity

Owner:

`prophet.candidate_episode/v1`

Do not modify episode identity from B03.

B03 must render one of:

- `PRESENT` — exact canonical episode relation available;
- `NOT_YET_ANCHORED` — candidate exists but no canonical episode is currently established;
- `UNAVAILABLE` — relation could not be safely determined.

Never synthesize `episode_id = ticker|date`.

---

# 2. Proposed additive read-model contract

Recommended schema:

`prophet.candidate_emergence_projection/v1`

This is a **projection**, not a source of truth.

One row per existing candidate-pool row.

Suggested shape:

```json
{
  "schema": "prophet.candidate_emergence_projection/v1",
  "ticker": "NVDA",
  "as_of": "2026-09-04",
  "display_only": true,
  "candidate_status": {
    "pool_lane": "forming",
    "pool_rank": 12,
    "first_seen": "2026-09-04",
    "days_in_pool": 1
  },
  "canonical_episode": {
    "state": "NOT_YET_ANCHORED",
    "episode_id": null,
    "reason": "no canonical anchored episode relation at this decision cut"
  },
  "research_attention": {
    "state": "EMERGING",
    "evidence_family_count": 3,
    "evidence_family_ids": [
      "attention_information_arrival",
      "positive_fundamental_rerating",
      "ownership_positioning"
    ],
    "first_emergence_seen": "2026-09-04",
    "latest_emergence_seen": "2026-09-04",
    "prospective_hypothesis": "H-EMERGENCE-CONVERSION",
    "validated": false
  },
  "technical_state": {
    "tier_cascade": null,
    "confirmation_state": "UNRESOLVED"
  },
  "entry_availability": {
    "state": "NOT_OPEN",
    "reason": "await_confluence"
  },
  "research_priority": null
}
```

The exact field vocabulary must be reconciled against current B04/B4/RP1 schemas before code.

---

# 3. Research-attention state must not become a score

Closed V1 states:

- `NONE`
- `EMERGING`
- `CONFIRMATION_REACHED`
- `STALE`
- `UNAVAILABLE`

Suggested derivation:

## NONE

No registered prospective emergence exposure is asserted.

## EMERGING

The candidate qualifies for the **prospective research cohort** under the frozen H-EMERGENCE-CONVERSION exposure definition.

This does not mean likely winner.

## CONFIRMATION_REACHED

The same candidate subsequently has a valid T1/T2 confirmation.

This is an evaluation milestone, not a buy instruction.

## STALE

The evidence/read-model clock is no longer current enough to present as a current research state.

## UNAVAILABLE

Required evidence state could not be safely resolved.

No numeric emergence score in V1.

---

# 4. Evidence source boundary

B03 does not parse or reinterpret raw filings/news/13F.

It may consume only a source-qualified typed read-model from B04/D5 / accepted evidence adapters.

Minimum per-family input:

- `family_id`;
- `active`;
- `direction`;
- `known_at`;
- `staleness_state`;
- `source_ref`;
- `independence_group`;
- `eligibility_for_emergence_study`.

A family counts toward `evidence_family_count` only when the prospective preregistration allows it.

Missing evidence is not false evidence.

Unknown is not absent.

---

# 5. RP1 boundary

Existing owner:

`mastermind.research_priority.v1`

Rules:

- B03 may display RP1 only where an exact lawful RP1 object already exists.
- B03 must not recompute RP1.
- B03 must not fill RP1 from Prophet score.
- B03 must not create `emergence_priority`.
- If RP1 is missing, render null/Unavailable, not 0.

The emergence cohort and RP1 are orthogonal:

- emergence = typed hypothesis exposure;
- RP1 = existing structural/recovery research-attention ordering.

---

# 6. Entry Availability boundary

B03 reads the existing B4/Entry-Signal truth.

It never derives “buy now” from:

- evidence convergence;
- C1 score;
- candidate lane;
- RP1;
- T1/T2 alone.

Required presentation combinations include:

### High research importance + entry closed

> Emerging · Entry not open

### Confirmation reached + entry closed

> Confirmed · Waiting for entry

### Entry open

Only the existing Entry Availability owner may supply this.

### Stale availability

> Entry status unavailable — stale input

Never retain a prior green action appearance.

---

# 7. Exact code-shape recommendation

Do **not** enlarge `build_candidate_pool` into an evidence engine.

Prefer an additive pure projector beside `project_candidate_visibility`, e.g.:

`project_candidate_emergence(...)`

Inputs should be already-resolved read models:

- candidate visibility/pool projection;
- candidate history;
- canonical B1 relation map;
- B04/D5 evidence summary map;
- B4 availability map;
- optional RP1 map.

Output:

- one additive row keyed by ticker;
- no changes to pool row identity/order;
- strict allowlist;
- deterministic digest;
- explicit source clocks.

Then the protected/private B03 surface composes:

`candidate_visibility row + emergence projection row`

rather than mutating the canonical pool schema unnecessarily.

---

# 8. Required tests

## T1 — No authority leak

Mutation test:

Adding/removing/changing emergence projection must not change:

- `build_candidate_pool(...)` output membership;
- `pool_rank`;
- `lane`;
- C1 score/order;
- `prophet_bridge.select_candidates(...)`;
- Entry Availability.

Static import closure should prove no authority-path module imports the emergence projection.

## T2 — Off-board candidate remains visible

Fixture:

- eligible candidate displaced by sector cap;
- no final Prophet score;
- two valid evidence families.

Expected:

- remains in original pool lane/order;
- score remains null;
- emergence may read `EMERGING`;
- no admission or plan effect.

## T3 — No fabricated episode

Fixture:

- candidate exists;
- no active canonical B1 episode.

Expected:

- `canonical_episode.state = NOT_YET_ANCHORED`;
- `episode_id = null`;
- no ticker/date surrogate.

## T4 — Exact canonical episode binding

Fixture:

- candidate has an accepted B1 relation.

Expected:

- exact B1 `episode_id`;
- identity mismatch fails closed;
- B03 never rewrites B1 identity.

## T5 — Evidence independence

Fixtures:

- two articles about one earnings release;
- one earnings release + one independent ownership filing.

Expected:

- first = one family / one independence group;
- second = two families if both prospective semantics are valid.

## T6 — Synthetic SUE clock rejected

Fixture:

- SUE carries only synthetic `period_end + 60d`.

Expected:

- contextual evidence may display;
- it cannot count as a timed ignition-arrival family for H-EMERGENCE-CONVERSION.

## T7 — Stale 13F is not current flow

Expected display includes staleness/period;
never copy “institutional inflow now”.

## T8 — RP1 is read-only

Fixture has exact RP1 object.

Expected:

- projected unchanged;
- missing RP1 stays null;
- no fallback computation.

## T9 — Entry remains closed

Fixture:

- emergence = EMERGING;
- evidence count >=2;
- availability says await_confluence.

Expected:

- user copy explicitly says entry not open;
- no “buy” synonym appears.

## T10 — NVDA golden journey

Point-in-time fixture sequence:

- Sep-04: unresolved watch + convergence;
- Sep-23: T1 / buy_now;
- Sep-24: extended / T3;
- Sep-25: T2 / partial;
- plan publication Sep-26.

Expected:

- first-emergence clock stays Sep-04;
- confirmation milestone Sep-23;
- availability follows existing owner each day;
- plan publication remains separately timestamped;
- no retroactive rewrite of Sep-04 into “buy”.

## T11 — Negative control

Candidate with >=2 evidence families that never T1/T2-confirms within the registered horizon.

Expected:

- remains research-only;
- later expires/stales honestly;
- no winner label.

## T12 — Freshness fail-closed

Candidate evidence or availability source is stale/mixed.

Expected:

- research state can remain historical/contextual if warranted;
- actionable entry presentation is unavailable/stale;
- no current action survives from a prior cut.

## T13 — Anonymous/private boundary

The new private fields must not leak through anonymous/free projection merely because upstream carries them.

Use the existing entitlement split.

## T14 — Determinism

Same inputs → byte-identical projection/digest.

---

# 9. Prospective evaluation instrumentation

B03 should expose enough immutable clocks for Eval OS to grade H-EMERGENCE-CONVERSION without scraping browser copy.

Required fields or references:

- first emergence observed;
- evidence family set at exposure cut;
- family known-at clocks;
- candidate state at exposure cut;
- technical tier at exposure cut;
- availability at exposure cut;
- first later T1/T2;
- first later availability-open;
- first formal plan publication.

The evaluator, not B03, computes outcomes.

No future outcome may be written back into the historical emergence exposure.

---

# 10. Golden and negative acceptance set

Minimum acceptance pack:

### Golden
- NVDA Sep-04 → Sep-23;
- FORM Sep-03 → Sep-11;
- PWR Sep-04 → Sep-21.

### Negative / non-converted
Use at least three historical discovery-only unresolved >=2-evidence candidates from the re-audit, e.g. candidates that did not confirm inside the matched horizon.

These historical cases validate plumbing/semantics only.

They do not count as prospective evidence.

---

# 11. Browser/product proof

B03 is not complete when JSON is correct.

Required real private user flow:

1. Search for an off-board/forming candidate.
2. See its actual candidate lane/status.
3. See “Emerging” only as a research state.
4. See evidence family explanations and clocks.
5. See Entry Availability separately.
6. See no fabricated Prophet score off the canonical score population.
7. See canonical episode state honestly.
8. Verify narrow/mobile layout and keyboard access.
9. Verify anonymous request does not expose paid/private details.
10. Ordinary next refresh preserves first-seen/emergence continuity.

---

# 12. Stop / handoff boundary

This packet does not authorize implementation.

Before implementation:

1. refresh exact main;
2. reconcile B03 incumbent carrier/reviewer/custody;
3. inspect current B04/D5 output contract and active #7869/#8004;
4. inspect current B4 availability contract;
5. inspect current RP1 live-commissioning state;
6. bind the exact code owner and review path.

If B03 already has an active writer by then, hand this packet to that carrier.

Do not open a rival B03 implementation.

---

# Done-when for B03 emergence capability

The capability is done only when an entitled user can find a real unresolved candidate and truthfully see:

> **why Mastermind is paying attention, how long it has been watching, whether confirmation has arrived, and whether entry is actually open**

with:

- lossless candidate continuity;
- canonical identity honesty;
- typed evidence;
- no duplicate score;
- no admission leakage;
- provenance/freshness;
- prospective evaluation hooks;
- real browser proof.
