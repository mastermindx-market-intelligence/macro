# F07 — Event → AssumptionChange proposal contract (V1, FROZEN)

Commissioned 2026-09-21. Base `origin/main` @ `ea194c5d215c`.
Owner engine: `engine/valuation_event_proposal.py` (new). Consumers: `engine/valuation_assumptions.py`.

## 0. First principle (binding)

An **event is evidence**. An **assumption is a model input**. They are not the same truth
class. A filing does not authorize an arbitrary delta. Therefore:

> **No number may enter a proposal that the valuation model has not already published.**

The event supplies at most a **direction**. Every magnitude that ever appears comes from the
B-F07-1 frozen preset triple (`engine.valuation_scenario.SCENARIOS`), never from the event,
never from prose, never from an LLM. This is `magnitude_source: "model_preset"` and it is the
only permitted value; `"event"` is unrepresentable.

## 1. Why this is not a redo of B-F07-3

`engine/valuation_event_bridge.py` (B-F07-3, merged) maps an event **class** to one of the
three inputs plus a direction word. It is preserved unchanged and is the `DIRECTION_ONLY`
path here. What it cannot do, and what this contract adds:

| Gap in B-F07-3 | Added here |
|---|---|
| No event identity — the class string only | `event.event_id`, `observed_at` |
| No source refs — user cannot verify | `event.source_refs[]` (form, cik, file_date, phrase) |
| Abstention is an untyped `None` | `status: INSUFFICIENT` + enumerated `abstain_reason` |
| Reader failure looks identical to "no event" | `reader_unavailable` is its own reason |
| No engine consumption, no before/after | `evaluate_proposal()` → shadow delta via existing math |
| No double-count / correction law | `already_in_reported_base`, `superseded_by_base` |
| `earnings` (82% of chronicle rows) falls through silently | typed, with a stated reason |

## 2. `assumption_change_proposal.v1`

```
status            "PROPOSED" | "INSUFFICIENT"
ticker            issuer
model_version     "valuation_scenario.v1"     # the model whose inputs this proposes to move
base_period_end   the V1 base period_end      # point-in-time anchor
event             {event_id, event_class, event_class_en, event_class_zh,
                   observed_at, source_refs: [{kind, form, cik, file_date, phrase, url}]}
evidence_class    MANAGEMENT_FORECAST_CHANGE | REPORTED_RESULT | CORPORATE_ACTION_CLASS | NONE
mapping_method    DIRECTION_TO_MODEL_PRESET | DIRECTION_ONLY | NONE
assumption_name   sales_growth_pct | margin_delta_pp | earnings_multiple | null
direction         "up" | "down" | null
baseline_value    from server_default (model authority)
proposed_value    a V1 preset value, or null
magnitude_source  "model_preset" | null        # never "event"
horizon           plain words, from the event's own period
rationale_en/zh   plain words
uncertainty       plain words
falsifier         what would refute this mapping
abstain_reason    the primary reason, by the fixed order below
abstain_reasons   every reason that applied, so nothing is hidden behind the first

  reader_unavailable              the readers failed — NOT the same as "no events"
  no_event                        healthy reader, issuer has none
  event_not_yet_observable        dated after the build's as_of: a calendar entry
  model_version_mismatch          stored proposal replayed against another model
  already_in_reported_base        dated on/before base period end — double count
  superseded_by_base              the base advanced past the proposal
  reported_result_not_an_assumption   a reported result is a FACT, not a forecast
  payload_not_licensed            payload is consensus-derived (rights)
  no_source_ref                   nothing the user could open and check
  event_class_unmapped            no target for this class
  no_lawful_control_mapping       target is not one of the three controls
```

### Invariants (test-enforced)

1. `proposed_value is not None` **iff** `magnitude_source == "model_preset"` **and**
   `proposed_value` is exactly a value in `SCENARIOS` for that `assumption_name`.
2. `status == "INSUFFICIENT"` ⟹ `proposed_value is None` **and** `abstain_reason is not None`.
3. `evidence_class == "REPORTED_RESULT"` ⟹ always `INSUFFICIENT`. A reported result is
   already the valuation base; proposing it again double-counts it.
4. A proposal is never applied. `evaluate_proposal()` is read-only and returns a shadow blob.
5. No probability, confidence, consensus figure, price target, or rating may appear.
6. `status == "PROPOSED"` ⟹ `event.source_refs` is non-empty, with a resolvable
   EDGAR document URL. No unverifiable proposal.
7. **Point-in-time, both directions.** Backward: an event dated on or before the base's
   period end is already inside it. Forward: an event dated after the caller-supplied
   `as_of` has not happened yet — a scheduled earnings date is a calendar entry, not
   evidence. This module never reads a clock; `as_of` is threaded from the build.
8. **Stored-proposal binding.** `evaluate_proposal` refuses a proposal whose
   `model_version` differs from the engine's, or whose `base_period_end` differs from
   the blob's. A proposal is only meaningful against the exact model and base it was
   made against, and re-applying one the newer base has absorbed double-counts it.
   The historical proposal is never rewritten — it keeps its own `base_period_end`.

## 3. Rights gate (`payload_not_licensed`)

`DEC:F07-VALUATION-SOURCE-IS-SEC-COMPANYFACTS-V1` restricts V1 inputs to SEC companyfacts
and forbids consensus estimates. The chronicle's `earnings` rows carry
`EPS <actual> · est <consensus> · surprise <pct>`. The `est`/`surprise` legs are
consensus-derived, so an earnings row's forward-looking content is **rights-blocked** and
abstains with `payload_not_licensed`. This is a rights refusal, not a data gap.

## 4. Correction / double-count law

- `observed_at <= base_period_end` → `already_in_reported_base`. The base already absorbed it.
- A previously emitted proposal whose event later falls inside an advanced base is marked
  `superseded_by_base`. The historical proposal keeps its own `base_period_end` and is **not
  silently rewritten** — supersession is additive.
- Event corrections mint a new proposal keyed `(event_id, model_version, base_period_end)`.

## 5. Phase-4 shadow evaluation — no second valuation math

`evaluate_proposal(controls_blob, proposal) -> assumption_change_scenario.v1` calls the
**existing** `valuation_assumptions.per_share_at()`. It changes exactly one of the three
inputs, holds the other two at `server_default`, and reports both sides plus the refusal
when there is one. No formula is re-implemented.

## 6. Authority

`research_display_only`, shadow. Never a fair value, never a rank/gate/size/trade input.

## 7. Front-facing vocabulary

The controls blob is serialized into the page, so every field in it is front-facing in
practice. Refutation vocabulary is therefore banned from the blob itself, not just from
rendered copy: the contract's conceptual `falsifier` ships as **`what_would_change_this`**
(DESIGN_DOCTRINE Law 2 "rewrite, don't delete"; operator 2026-07-27 on falsifier language).
The commission's own instruction — "exact schema names should follow current repo law
after archaeology" — is what selects the plain-word name.

## 8. What the panel must never imply

The figure shown for a proposal is the model's own adjacent published scenario, chosen by
the event's direction. A reader could mistake it for a number management gave, so the
disclaimer naming whose number it is renders alongside every proposed figure and is
test-pinned, not left to copy drift.
