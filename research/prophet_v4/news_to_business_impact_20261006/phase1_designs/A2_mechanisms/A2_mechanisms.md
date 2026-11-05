# A2_mechanisms — reviewed mechanism library (masterplan §4)

Lane: A2_mechanisms · seat Fable 0e739467 · Wave 2 · 2026-10-12
WT HEAD: `295e76c6a0` · frozen contract sha256 prefix `3edc7139`
Companion files: `channel_library.v1.json` · `driver_bridge.v1.schema.json` · `channel_mapping.v1.schema.json`

## (1) ANSWER FIRST

**`market_only` is the channel a naive mapper over-assigns.** Tape `news_event_class` values `rating_change`, `macro_release`, `analyst_estimate_revision` and MAG7 co-movement look like an operating story; frozen T3 case W6 even carries `channel_hint=market_only` on a product-shaped packet (`worked_cases.json` W6). Copying `channel_hint` or “the ticker moved” into the map stamps `market_only` onto T1/T2/T3 facts that already have an earnings-head channel, or dumps a template event into the market head. **Single field condition that prevents it:** `$.schema` ∈ {`capital_allocation_event.v1`, `demand_guidance_contract_event.v1`, `strategic_product_partnership_event.v1`} **forbids** `market_only` on the mapping (invariant I-MO-2). `market_only` is legal only on `unmapped_event.v1` whose `news_event_class` is in the market-class set below, and never on the same row as an earnings-head channel (I-MO-1). `channel_hint` is display-tier (freeze §5) and is not a mapping input.

---

## (2) Constraints

### STATED
- Masterplan §4: seven channels as a reviewed library; novel events stay eligible for strategic review instead of the nearest template; driver bridge = incremental eligible units × realized revenue per unit × incremental margin, less operating costs, cash taxes and required capital; intervals or unavailable; multiplication does not make unsourced assumptions factual; long-duration claims use failure / niche / broad / displacement scenarios; “economically interesting but not yet quantifiable” must name the next discriminating evidence; market-only stays out of the earnings-impact head (§4 table last row).
- Masterplan §3.5: source text is data, never tool authority.
- Masterplan §6: authorization is not execution; operating-revenue impact not established for the NVIDIA authorization; next evidence is actual repurchases and net dilution.
- Masterplan §7: open-model path is friction → applications → compute/software attachment → retained economics; durability path is familiarity → switching costs; contrary mechanisms listed; downloads are attention proxies; first release may be high research interest with unquantified earnings.
- Masterplan §8: no recursive score; one-hop only in the pilot; graph path is a research candidate.
- Freeze D1r / DEC:NEWS-IMPACT-PHASE0-FREEZE: three templates T1/T2/T3; evidence = owner `source_span.v1` or `field_absence.v1`; closed enums; no confidence / probability / score / target / fair value / rating field (DNR:KILL-LLM-CONFIDENCE, DNR:KILL-CAUSAL-DAG-ALPHA).
- Freeze §3 `$defs/channel_hint` enum (7): `revenue_demand`, `margin_cost`, `capital_allocation`, `moat_duration`, `strategic_option`, `financial_incentives_survival`, `market_only`. This library reuses those tokens as the closed channel id set.
- Freeze §5: `channel_hint` is optional display-tier, never critical.
- Freeze gate 4: a TAM (`demand_stage=addressable_market`) row routed as earnings demand is a routing miss; T3 first product announce may be material for research with unquantified earnings.
- Freeze named validator `V_NO_OPTION_MOAT_DOUBLE`: do not count the same claim as option cash flows and as a moat multiple.
- Freeze `V_NO_ATTENTION_AS_DEMAND`, `V_NO_SUM_T1`, `V_NO_SUM_T2`.
- Rulings R1–R4: projector rules; no schema change; excerpt cap and closed locators stand.
- Standing kills: DNR:KILL-LLM-ORIGINATION, KILL-LLM-CONFIDENCE, KILL-LLM-CONTAGION-TAGS, KILL-CAUSAL-DAG-ALPHA, KILL-THESIS-LOBE, KILL-STALENESS-ALPHA, HOLD-STRUCTURE-LEARNERS.
- Envelope `prophet_flags` all const false (`$defs/prophet_flags`).

### PHYSICS
- A product of terms is defined only when every multiplicative term is a sourced number or interval. An untyped hole is not zero.
- JSON Schema cannot compare two numeric fields (freeze F3 / V_RANGE): range `low ≤ high` stays a named validator, not a schema promise.
- `span_id` is a hash of the full locator (documents.py:370–371 via `_span_id`); stripping keys changes identity (R4).
- Company identity pattern is `cik:` + 10 digits, all-zero forbidden (`$defs/company_id` pattern `^cik:(?!0{10}$)[0-9]{10}$`).

### INHERITED
- `engine/company_intelligence/identity.py:50-58` `company_id_for_cik` emits `cik:` + zfill(10); `engine/company_intelligence/events.py:35,194,292` consume it; `engine/company_intelligence/resolution.py:151` carries `EventObservation.company_id`.
- `engine/company_intelligence/events.py:93-99` closed `EVENT_TYPES` has no `news` member; unknown `event_type` raises at `:197-199`. Leaf facts therefore do not force a `company_event.v1` link (freeze F1/D6).
- `engine/company_intelligence/documents.py:189-190` `SourceDocument.revision` must be a positive integer; `:307-365` `SourceSpan.to_payload` is the evidence object; `:375-429` `text_span` mints `byte_replayed`; `:435-460` `address_only_span`; `:72-90` `ABSENCE_REASONS` (16) are `field_absence.v1.owner_reason`.
- `engine/news_events.py:1-11,398-461` `classify_event` is context-only, returns `None` when no class matches, never force-fits. Return dict includes a `confidence` key (`:447`) — this library **must not copy that key**.
- `engine/news_events.py:62-380` class names are the frozen `$defs/news_event_class` 24-enum (plus `unclassified`).
- `engine/news_common.py:368,437` `is_low_value` / `macro_release_stub` stay article filters, not channel assignments.
- `engine/qbus.py:15-18,445` keep-first item identity and `novelty_z` are attention measures, not economic confirmation (masterplan §1, freeze D11).
- `engine/news_event_ledger.py:87,174` stores `novelty_z`; LEAF never appends (freeze §9).
- `engine/company_intelligence/economic_observations.py:47-61` present-vs-absent key split is the sibling pattern for sourced interval vs typed absence.

### ASSUMED
- A1. Mapping is a **pure function of one validated contract instance** plus this library version. Cluster/thesis state is a later consumer (masterplan §5), not an input here. What breaks if violated: thesis lobe would originate channels (DNR:KILL-THESIS-LOBE).
- A2. Typical lag windows are **named windows**, not measured day counts. Numeric day bounds are not claimed.
- A3. v1 never emits duration-scenario **weights**. Seat DEC required before any weight field is added.
- A4. `labelled_assumption.v1` is allowed on a driver-bridge **term** and **blocks** the product in v1 (stricter than “unlabelled only”). Relaxing this is a version bump.
- A5. Transfer / one-hop counterparties are **out of this library’s assignment**. `issuer_role` ∈ {supplier, customer, competitor} may keep a direct-issuer channel when the schema already requires a real counterparty id (T2 allOf[1]); they do not mint a second issuer’s channel here (masterplan §8, #6514 hold).

---

## (3) Three mechanism-distinct candidates

**Boring baseline (not a fourth mechanism):** copy `$defs/channel_hint` onto the event. Same mechanism as a one-row lookup. It fails freeze §5 (hint is optional display-tier), fails W6 (`channel_hint=market_only` on T3), and carries no causal chain, contrary cases, lags, or driver-bridge terms.

| ID | Mechanism | Actor / point | One-line refutation test |
|---|---|---|---|
| C1 | Versioned closed **rule table** keyed on frozen `schema` + `$def` enums | Deterministic matcher after contract ACCEPT | Feed W6 (T3, `channel_hint=market_only`, `issuer_role=incidental`): if the output assigns `market_only` or any earnings-head channel, C1 is wrong. |
| C2 | **Ingest-time labeler** (human or LLM) writes channel tags per article | Extractor / model | Grep the output schema for a free channel string or a model-only tag; any hit violates DNR:KILL-LLM-ORIGINATION and DNR:KILL-LLM-CONTAGION-TAGS. C1_tape Q8 has no human channel labels to supervise. |
| C3 | **Learned graph / causal DAG** infers channels from cluster co-occurrence | Post-cluster structure learner | Any edge weight or implied probability feeding assignment violates DNR:KILL-CAUSAL-DAG-ALPHA and DNR:HOLD-STRUCTURE-LEARNERS. `classify_event` returning None on 95% of tape (C1_tape Q6) would be force-fit by a learner. |

**Chosen: C1.** It is the only candidate whose every assignment is a reviewed rule on contract fields the validator already closed. C2 loses because origination and contagion tags are standing kills and the tape has no labels. C3 loses because a causal DAG feeding a channel (then a thesis, then a trade) is the exact KILL-CAUSAL-DAG-ALPHA shape; HOLD-STRUCTURE-LEARNERS additionally clocks structure learning. C1 includes the outside-the-build off-ramp: `unmapped_event.v1` + `strategic_review` rather than inventing a fourth template.

---

## (4) Frozen-spec draft

A builder implements this section without asking. Types live in `channel_library.v1.json`, `driver_bridge.v1.schema.json`, `channel_mapping.v1.schema.json`.

### 4.0 Closed vocabularies

**channel_id** (7; identical to `$defs/channel_hint`):
`revenue_demand` · `margin_cost` · `capital_allocation` · `moat_duration` · `strategic_option` · `financial_incentives_survival` · `market_only`

**earnings_head_channels:** the first six.
**market_hypothesis_head_channels:** `market_only` only.

**channel_role:** `earnings_countable` | `watch_only` | `market_hypothesis`.
**mapping_status:** `mapped` | `not_yet_quantifiable` | `strategic_review` | `ineligible_role` | `superseded_inherit` | `unmapped_novel`.
**product_status:** `computed` | `withheld_unlabelled_assumption` | `withheld_labelled_assumption` | `withheld_term_absent` | `not_applicable_channel`.
**term_form:** `point` | `interval` | `absent` | `assumption`.
**duration_scenario_id:** `failure` | `niche_adoption` | `broad_adoption` | `displacement_cannibalization`.
**named_window:** `stated_fiscal_period` | `next_reported_period` | `through_horizon_period` | `until_independent_milestone` | `decision_cut_session` | `not_applicable`.
**nyq_reason:** `driver_bridge_term_absent` | `authorization_without_execution` | `claim_class_none_stated` | `addressable_market_not_funded` | `attention_proxy_only` | `commentary_only`.
**market_class set** (`$defs/news_event_class` values that may receive `market_only` on an unmapped event): `rating_change` · `analyst_estimate_revision` · `macro_release` · `mna_rumor` · `unclassified` (only when `classify_event` was None and no template accepted).
**forbidden field names anywhere in this library:** `confidence`, `probability`, `score`, `price_target`, `fair_value`, `rating`, `weight`, `likelihood`, `contagion`.

### 4.1 Channel record shape

Each of the seven records in `channel_library.v1.json` `channels[]`:

| Field | Type | Invariant |
|---|---|---|
| `id` | channel_id | unique |
| `version` | const `channel.v1` | |
| `analytical_question` | text_safe ≤ 240 | masterplan §4 question |
| `earnings_head_eligible` | boolean | false iff id=`market_only` |
| `allowed_input_fields` | array of JSON pointers into a T1/T2/T3 instance or unmapped envelope | closed list per channel |
| `causal_chain` | ordered array of `{name, kind, note}` | `kind` ∈ {`named_quantity`, `observation`, `condition`}; no numeric product stored here |
| `contrary_cases` | array of `{id, when, effect}` | `effect` ∈ {`remove_channel`, `downgrade_watch_only`, `hold_nyq`, `no_earnings_head`} |
| `required_observations` | array of `{id, description, named_window}` | |
| `typical_lag_window` | named_window | |
| `weakening_conditions` | array of `{id, when}` | field predicates, not prose adjectives |
| `quantity_form_map` | array of `{contract_path, feeds, when}` | `feeds` is a driver-bridge term or a capital-allocation named quantity |
| `display_words` | text_safe ≤ 240 | plain words with windows; no certainty; no “falsif*” |

### 4.2 Driver bridge (`driver_bridge.v1`)

Applies **only** when an assigned channel is `revenue_demand` with `channel_role=earnings_countable`. Other channels set `product_status=not_applicable_channel` and `terms` may be omitted.

**Terms, order, and sign**

| term_id | role | sign |
|---|---|---|
| `eligible_units` | multiplicative | + |
| `realized_revenue_per_unit` | multiplicative | + |
| `incremental_margin` | multiplicative (fraction 0–1 or percent basis) | + |
| `operating_costs` | subtract from gross | − |
| `cash_taxes` | subtract | − |
| `required_capital` | subtract | − |

**Each term is exactly one of:**

1. **sourced_point** — `form=point`, `value` number, `bound` ∈ {exact, approximately, up_to, at_least}, `unit`, `currency` (`[A-Z]{3}|NA`), `basis` ∈ `$defs/quantity_basis`, `period` fiscal_period|absence, `evidence` = `$defs/evidence_span` (owner source_span.v1), `source_contract_path` JSON pointer.
2. **sourced_interval** — `form=interval`, `low`, `high`, same unit/currency/basis/period/evidence/path. Named validator V_RANGE: `low ≤ high`.
3. **typed absence** — `form=absent`, `absence` = `$defs/field_absence.v1` (reason enum 5), optional `evidence`.
4. **labelled_assumption** — `form=assumption`, `label` text_safe ≤ 120, `review_id` pattern `^DEC:[A-Z0-9-]{3,64}$`, `stated_by` ∈ {`seat_dec`, `issuer_stated_unquantified`}, `point_or_interval`, `note`. **An object with a number and no `form` tag is an unlabelled assumption and is schema-invalid.**

**Product rule (v1, executable):**

```
if channel != revenue_demand or role != earnings_countable:
    product_status = not_applicable_channel; product = null
elif any term missing or form not in {point, interval, absent, assumption}:
    product_status = withheld_unlabelled_assumption; product = null
elif any of the six terms form == assumption:
    product_status = withheld_labelled_assumption; product = null
elif any of the six terms form == absent:
    product_status = withheld_term_absent; product = null
    emit not_yet_quantifiable.v1
else:
    product_status = computed
    product = {kind: net, low, high, unit, currency}  # interval arithmetic on all six
```

v1 computes `product` only when **all six** terms are sourced (point or interval). A gross-only product (three multiplicative terms present, costs absent) is specified as a future branch and is **not emitted in v1** (open question 1). Interval arithmetic is independent endpoints (all combinations of lows/highs, then min/max). No distribution. No midpoint-as-forecast. `product` is a sourced interval of the bridge terms, **not** a valuation.

`option_ceiling` (T2) **never** feeds a term (V_NO_SUM_T2). `adoption_proxy_quote` **never** feeds `eligible_units` (V_NO_ATTENTION_AS_DEMAND).

### 4.3 Mapping record (`channel_mapping.v1`)

Required: `schema` const `channel_mapping.v1`, `library_version` const `channel_library.v1`, `rule_ids` array of fired rule_id, `fact_id`, `company_id` (or absence), `input_schema`, `assigned_channels` array of `{id, role}`, `mapping_status`, `earnings_head` ∈ {`open`, `withheld`}, `driver_bridge` (object or null), `not_yet_quantifiable` (object or null), `duration_scenarios` (object or null), `inherits_from_fact_id` (null or `fact_*`), `prophet_flags` (all false), `unsolicited_instruction_detected` const false.

**Invariants**
- I-MO-1: `market_only` and any earnings_head channel are disjoint on one mapping.
- I-MO-2: if `input_schema` ∈ {T1, T2, T3} then `market_only` ∉ assigned_channels.
- I-HINT-1: mapper does not read `channel_hint`.
- I-ORIG-1: no field in the forbidden list.
- I-DOUBLE-1: at most one of `strategic_option` or `moat_duration` has `role=earnings_countable` on one mapping (V_NO_OPTION_MOAT_DOUBLE). Both may be `watch_only`.
- I-CORR-1: `novelty=corrected_fact` ⇒ `inherits_from_fact_id = supersedes_fact_id` (non-null).
- I-NEG-1: `negated=true` does not remove the channel; it is a contrary direction on the same channel.
- I-ROLE-1: `issuer_role=incidental` ⇒ `mapping_status=ineligible_role`, assigned_channels empty, earnings_head withheld.
- I-STICKY-1: `ineligible_role` and `strategic_review` set at priority ≤ 20 are not overwritten by later `set_status` or `assign`. Later rules may only `remove`.

### 4.4 Predicate language (mapping rules)

A rule is `{rule_id, priority, when, assign[], remove[], set_status, set_bridge, set_nyq, set_scenarios}`.

```
when := {eq:[pointer, value]} | {in:[pointer, [values]]} | {form_in:[pointer, [forms]]}
      | {exists: pointer} | {is_company_id: pointer} | {not: when} | {all:[when...]} | {any:[when...]}
```

Pointers are JSON Pointers into the ACCEPT-ed instance (`/schema`, `/action_type`, `/executed_amount/form`, …). Missing optional key: `eq`/`in`/`form_in` fail. `is_company_id` succeeds only on a string matching `$defs/company_id`.

Apply rules with matching `when`, ascending `priority`. Later `remove` wins over earlier `assign`. `set_status` is first-writer-wins (so T1-CORR `superseded_inherit` is not overwritten by T1-DEFAULT `mapped`). After the sweep, enforce I-* invariants; a violation is a mapper bug (hard fail), not a silent strip.

### 4.5 Per-template default maps

#### T1 `capital_allocation_event.v1`

| rule_id | priority | when | effect |
|---|---|---|---|
| T1-ROLE-INC | 10 | `/issuer_role` = `incidental` | status `ineligible_role`; channels [] |
| T1-COMMENTARY | 20 | `/novelty` = `commentary` | status `strategic_review`; channels [] |
| T1-DEFAULT | 100 | `/schema` = T1 and role ∈ {subject, counterparty} | assign `capital_allocation` / `earnings_countable`; status `mapped`; bridge `not_applicable_channel` |
| T1-AUTH-NYQ | 210 | `/commitment_status` ∈ {authorized, announced, planned, conditional} AND `/executed_amount/form` = `absent` | keep channel; status stays `mapped`; set_nyq reason `authorization_without_execution`; next evidence = executed_amount point/range + net dilution |
| T1-SURVIVAL | 200 | `/action_type` ∈ {debt_issuance, equity_issuance} AND `/news_event_class` = `bankruptcy_restructuring` | add `financial_incentives_survival` / `watch_only` |
| T1-WITHDRAWN | 220 | `/commitment_status` = `withdrawn` OR `/negated` = true | keep `capital_allocation`; weakening `authorization_withdrawn_or_negated` |
| T1-CORR | 50 | `/novelty` = `corrected_fact` | status `superseded_inherit`; inherit channels from default; `inherits_from_fact_id=/supersedes_fact_id` |
| T1-NO-REV | 300 | always on T1 | **remove** `revenue_demand`, `margin_cost`, `moat_duration`, `strategic_option`, `market_only` |

Quantity-form map (T1): `/incremental_amount` → named quantity `authorization_capacity` when `/primary_amount_role` = `incremental_authorization` and form ∈ {point, range}; `/remaining_authorization` → `remaining_program_capacity`; `/executed_amount` → `executed_retired_or_issued` when form ∈ {point, range}. **None of these feed the driver bridge.**

#### T2 `demand_guidance_contract_event.v1`

| rule_id | priority | when | effect |
|---|---|---|---|
| T2-ROLE-INC | 10 | `/issuer_role` = `incidental` | `ineligible_role`; [] |
| T2-COMMENTARY | 20 | `/novelty` = `commentary` | `strategic_review`; [] |
| T2-TAM | 90 | `/demand_stage` = `addressable_market` | **no** `revenue_demand`; status `not_yet_quantifiable`; nyq reason `addressable_market_not_funded`; earnings_head withheld |
| T2-DEFAULT | 100 | `/demand_stage` ∈ {pipeline, backlog, bookings, recognized_revenue, guidance, cancellation} AND `/metric` ∈ {revenue, bookings, backlog, units, eps} | assign `revenue_demand` / `earnings_countable` |
| T2-PIPELINE | 210 | `/demand_stage` = `pipeline` | keep channel; weakening `pipeline_not_bookings`; required obs conversion to bookings |
| T2-CANCEL | 220 | `/demand_stage` = `cancellation` OR `/revision_direction` ∈ {cut, withdrawn, cancelled} | keep `revenue_demand`; weakening `demand_cut_or_cancelled` |
| T2-AWARD | 200 | `/revision_direction` = `awarded` AND `/news_event_class` ∈ {contract_award, policy_trade_control} | add `financial_incentives_survival` / `watch_only` **only if** `/news_event_class` = `policy_trade_control`; else stay revenue_demand |
| T2-OPTION-CEIL | 230 | `/option_ceiling` form ∈ {point, range} | do not add option_ceiling into stated_amount or eligible_units (V_NO_SUM_T2) |
| T2-BRIDGE | 400 | `revenue_demand` earnings_countable AND `/stated_amount/form` ∈ {point, range} AND `/demand_stage` ∈ {bookings, recognized_revenue} AND `/metric` ∈ {units, revenue, bookings} | attach driver_bridge; map paths per §4.7; other T2 rows withhold bridge (`withheld_term_absent`) |
| T2-NO-MO | 300 | always on T2 | remove `market_only` |

#### T3 `strategic_product_partnership_event.v1`

| rule_id | priority | when | effect |
|---|---|---|---|
| T3-ROLE-INC | 10 | `/issuer_role` = `incidental` | `ineligible_role`; []  (covers W6) |
| T3-COMMENTARY | 20 | `/novelty` = `commentary` | `strategic_review`; [] |
| T3-NONE | 90 | `/economic_claim_class` = `none_stated` | status `not_yet_quantifiable`; nyq `claim_class_none_stated`; channels [] |
| T3-OPTION | 100 | `/economic_claim_class` = `option_path` | assign `strategic_option` / `earnings_countable`; assign `moat_duration` / `watch_only` |
| T3-MOAT | 100 | `/economic_claim_class` = `moat_duration_claim` | assign `moat_duration` / `earnings_countable`; assign `strategic_option` / `watch_only` |
| T3-FUNDED | 100 | `/economic_claim_class` = `funded_demand` | assign `revenue_demand` / `earnings_countable`; assign `strategic_option` / `watch_only` |
| T3-ATTN | 210 | `/adoption_proxy_quote` **exists** AND `/stated_quantity/form` = `absent` | do **not** add `revenue_demand` (V_NO_ATTENTION_AS_DEMAND); nyq `attention_proxy_only` if no other countable channel |
| T3-DELAY | 220 | `/event_kind` ∈ {delay, withdrawal} | keep assigned; weakening `delay_or_withdrawal` |
| T3-MILESTONE | 200 | `/novelty` = `independently_observed_milestone` AND `/event_kind` = `customer_deployment` AND `/stated_quantity/form` ∈ {point, range} | if option_path, keep option countable; do not auto-promote to `funded_demand` |
| T3-SCENARIOS | 400 | assigned contains `strategic_option` or `moat_duration` | attach `duration_scenario_set.v1` with four scenarios, `weights_status=forbidden_in_v1` |
| T3-NO-MO | 300 | always on T3 | remove `market_only` even if `channel_hint=market_only` |

### 4.6 Novel event off-ramp (`unmapped_event.v1`)

When the Phase 1 extractor cannot ACCEPT a T1/T2/T3 instance (no template fits, or `classify_event` is None — 95% of tape, C1_tape Q6; sibling: `news_events.py:398-461` returns None and “Do NOT force-fit”):

```
unmapped_event.v1 = {
  schema: "unmapped_event.v1",
  authority: "context_only",
  fact_id, document_id, observed_at, source_available_at,
  company_id | field_absence.v1,
  news_event_class,                 # from classify_event.event_type or unclassified
  reason: "no_matching_template" | "classify_event_none" | "role_incidental" | "commentary_only",
  strategic_review_status: "eligible",
  assigned_channels: [] | [{id: "market_only", role: "market_hypothesis"}],
  next_discriminating_evidence: {description, named_window}
}
```

**Eligibility rule:** `assigned_channels` may contain `market_only` iff `news_event_class` ∈ market_class set AND no T1/T2/T3 ACCEPT exists for this `fact_id`. Otherwise channels stay empty and `strategic_review_status=eligible`. **Never** coerce `other_strategic` / `other_allocation` / `metric=other` into the nearest economic channel. `metric=other` on an ACCEPT-ed T2 still uses T2-DEFAULT only when `demand_stage` is in the funded set; if a builder cannot map a term, status is `not_yet_quantifiable`, not a guessed channel.

### 4.7 Quantity-form map (contract path → bridge term or named quantity)

| Template | contract_path | feeds | when |
|---|---|---|---|
| T2 | `/stated_amount` | `eligible_units` | metric=`units` AND demand_stage ∈ {bookings, recognized_revenue} AND form ∈ {point, range} |
| T2 | `/stated_amount` | `realized_revenue_per_unit` | **never from the same slot as units**; only if a later fact supplies a distinct unit-price quantity. v1: leave this term `absent` unless a second ACCEPT-ed quantity exists on a superseded-inherit chain with metric=`revenue` and matching period |
| T2 | `/stated_amount` | **not** a bridge term; named quantity `stated_revenue` | metric=`revenue` |
| T2 | `/stated_amount` | named quantity `stated_bookings` | metric=`bookings` |
| T2 | `/stated_amount` | named quantity `stated_backlog` | metric=`backlog` |
| T2 | `/stated_amount` | named quantity `stated_eps` | metric=`eps` (basis const `per_share`, T2 allOf[4]) |
| T2 | `/option_ceiling` | **forbidden** | V_NO_SUM_T2 |
| T2 | `/prior_amount` | baseline comparison only, not a bridge term | |
| T1 | see §4.5 | capital named quantities only | |
| T3 | `/stated_quantity` | `eligible_units` | economic_claim_class=`funded_demand` AND form ∈ {point, range} |
| T3 | `/stated_quantity` | none | form=`absent` → nyq |

v1 consequence: the three-factor product almost always withholds. That is intended. The truthful output is `not_yet_quantifiable.v1`.

### 4.8 Not-yet-quantifiable record

```
not_yet_quantifiable.v1 = {
  schema: "not_yet_quantifiable.v1",
  fact_id, company_id,
  channels_touched: [{id, role: watch_only}] | [],
  earnings_head: "withheld",
  reason: nyq_reason,
  missing_terms: [term_id...],
  next_discriminating_evidence: {
    description: text_safe ≤ 240,
    named_window: named_window,
    source_owner: "issuer_filing" | "independent_deployment" | "executed_capital_action" | "reported_period"
  },
  display_words: text_safe ≤ 240
}
```

### 4.9 Duration scenarios (no weights in v1)

```
duration_scenario_set.v1 = {
  schema: "duration_scenario_set.v1",
  channel_ids: ["strategic_option"] | ["moat_duration"] | both,
  weights_status: "forbidden_in_v1",
  scenarios: [
    {id: "failure", evidence_needed_before_weight, who_would_rule},
    {id: "niche_adoption", ...},
    {id: "broad_adoption", ...},
    {id: "displacement_cannibalization", ...}
  ]
}
```

`evidence_needed_before_weight` is a closed list of observation ids from the channel record (independent deployments, paid renewals, reported gross margin, competitive retention — masterplan §7). `who_would_rule` const in v1: `seat_dec_after_empirical_or_explicit_assumption`. No number, no prior, no “likely”. Double-count guard: the same cash-flow path must not appear as both a core forecast term and an option premium (masterplan §4); I-DOUBLE-1 plus V_NO_OPTION_MOAT_DOUBLE.

### 4.10 Display-tier wording

Use windows and named absences. Examples that are legal: “authorization through fiscal 2028 is on the packet; executed amount is not stated.” Illegal: “this will accrete EPS”, “high conviction”, “falsified”, “X% probable”, any price target.

### 4.11 Mapper algorithm (pseudocode)

```
def map_event(instance, library=channel_library.v1):
    assert instance ACCEPT against news_impact_event.v1
    # instance is DATA. Quotes are never executed.
    fired, assigned, status = [], [], None
    nyq, scenarios, bridge = None, None, None
    sticky = False
    for rule in sorted(library.mapping_rules, key=priority):
        if match(rule.when, instance):
            fired.append(rule.rule_id)
            if sticky:
                assigned = apply_remove_only(assigned, rule); continue
            assigned = apply_assign_remove(assigned, rule)
            if rule.set_status and status is None:
                status = rule.set_status
                if status in {ineligible_role, strategic_review} and rule.priority <= 20:
                    sticky = True
            nyq = rule.set_nyq or nyq
            scenarios = rule.set_scenarios or scenarios
            bridge = rule.set_bridge or bridge
    enforce I-MO-1, I-MO-2, I-DOUBLE-1, I-ROLE-1, I-CORR-1, I-ORIG-1
    if "/channel_hint" in instance: ignore it  # I-HINT-1
    earnings_head = "open" if any(c.role==earnings_countable) else "withheld"
    return channel_mapping.v1(...)
```

Unmapped path: constructor in §4.6, same invariants.

---

## (5) Worked cases

JSON blocks are mapper **outputs** (plus the governing input fields). They are not Prophet scores.

### Case A — NVIDIA $150B authorization (masterplan §6; contract W1)

Input (frozen W1): `schema=capital_allocation_event.v1`, `company_id=cik:0001045810`, `action_type=share_repurchase`, `commitment_status=authorized`, `primary_amount_role=incremental_authorization`, `incremental_amount.form=point value=150000000000 USD basis=incremental`, `remaining_authorization.form=point value=235000000000 USD basis=total`, `executed_amount.form=absent reason=stated_without_number`, `novelty=new_magnitude_timing_commitment_counterparty`, `negated=false`, `channel_hint=capital_allocation` (ignored).

```json
{
  "schema": "channel_mapping.v1",
  "library_version": "channel_library.v1",
  "rule_ids": ["T1-DEFAULT", "T1-AUTH-NYQ", "T1-NO-REV"],
  "fact_id": "fact_000000000000000000000001",
  "company_id": "cik:0001045810",
  "input_schema": "capital_allocation_event.v1",
  "assigned_channels": [{"id": "capital_allocation", "role": "earnings_countable"}],
  "mapping_status": "mapped",
  "earnings_head": "open",
  "driver_bridge": {
    "schema": "driver_bridge.v1",
    "authority": "context_only",
    "fact_id": "fact_000000000000000000000001",
    "company_id": "cik:0001045810",
    "channel": "capital_allocation",
    "product_status": "not_applicable_channel",
    "product": null,
    "terms": null
  },
  "named_quantities": {
    "authorization_capacity": {"form": "point", "value": 150000000000, "unit": "USD", "basis": "incremental", "source_contract_path": "/incremental_amount"},
    "remaining_program_capacity": {"form": "point", "value": 235000000000, "unit": "USD", "basis": "total", "source_contract_path": "/remaining_authorization"},
    "executed_retired_or_issued": {"form": "absent", "absence": {"schema": "field_absence.v1", "authority": "context_only", "reason": "stated_without_number", "subject": "executed_amount", "detail": "plans to execute the repurchases through fiscal 2028", "missing_fields": []}}
  },
  "not_yet_quantifiable": {
    "schema": "not_yet_quantifiable.v1",
    "fact_id": "fact_000000000000000000000001",
    "company_id": "cik:0001045810",
    "channels_touched": [{"id": "capital_allocation", "role": "watch_only"}],
    "earnings_head": "withheld",
    "reason": "authorization_without_execution",
    "missing_terms": [],
    "next_discriminating_evidence": {
      "description": "executed repurchase amount and net dilution against this authorization",
      "named_window": "through_horizon_period",
      "source_owner": "executed_capital_action"
    },
    "display_words": "Additional authorization of 150 billion USD is on the packet through fiscal 2028; executed amount is not stated. Operating revenue is not on this packet."
  },
  "duration_scenarios": null,
  "inherits_from_fact_id": null,
  "prophet_flags": {"may_rank": false, "may_size": false, "may_gate": false, "prophet_authority": false},
  "unsolicited_instruction_detected": false
}
```

Note: `earnings_head: open` on the mapping means the **channel is allowed** on the earnings head; the NYQ subrecord withholds a **quantified** earnings increment until execution. This matches masterplan §6 “capital-allocation significance” plus “operating revenue impact not established”.

### Case B — correction / supersedes (contract R6)

Input: `novelty=corrected_fact`, `supersedes_fact_id=fact_000000000000000000000001`, `incremental_amount.value=165000000000`, same T1 shape, `executed_amount` absent `not_stated`.

```json
{
  "schema": "channel_mapping.v1",
  "library_version": "channel_library.v1",
  "rule_ids": ["T1-CORR", "T1-DEFAULT", "T1-AUTH-NYQ", "T1-NO-REV"],
  "fact_id": "fact_000000000000000000000016",
  "company_id": "cik:0001045810",
  "input_schema": "capital_allocation_event.v1",
  "assigned_channels": [{"id": "capital_allocation", "role": "earnings_countable"}],
  "mapping_status": "superseded_inherit",
  "earnings_head": "open",
  "driver_bridge": {"schema": "driver_bridge.v1", "authority": "context_only", "product_status": "not_applicable_channel", "product": null, "terms": null, "fact_id": "fact_000000000000000000000016", "company_id": "cik:0001045810", "channel": "capital_allocation"},
  "named_quantities": {
    "authorization_capacity": {"form": "point", "value": 165000000000, "unit": "USD", "basis": "incremental", "source_contract_path": "/incremental_amount"}
  },
  "not_yet_quantifiable": {
    "schema": "not_yet_quantifiable.v1",
    "reason": "authorization_without_execution",
    "fact_id": "fact_000000000000000000000016",
    "company_id": "cik:0001045810",
    "channels_touched": [{"id": "capital_allocation", "role": "watch_only"}],
    "earnings_head": "withheld",
    "missing_terms": [],
    "next_discriminating_evidence": {"description": "executed repurchase amount and net dilution against the corrected authorization", "named_window": "through_horizon_period", "source_owner": "executed_capital_action"},
    "display_words": "This packet corrects the prior authorization fact; executed amount remains not stated."
  },
  "duration_scenarios": null,
  "inherits_from_fact_id": "fact_000000000000000000000001",
  "prophet_flags": {"may_rank": false, "may_size": false, "may_gate": false, "prophet_authority": false},
  "unsolicited_instruction_detected": false
}
```

### Case C — NVIDIA open-model release (masterplan §7; contract W5) — not yet quantifiable

Input: T3, `event_kind=product_release`, `object_name=Nemotron 3`, `economic_claim_class=option_path`, `stated_quantity.form=absent reason=not_stated`, `commitment_status=announced`, `counterparty_role=none`, `channel_hint=strategic_option` (ignored).

```json
{
  "schema": "channel_mapping.v1",
  "library_version": "channel_library.v1",
  "rule_ids": ["T3-OPTION", "T3-SCENARIOS", "T3-NO-MO"],
  "fact_id": "fact_000000000000000000000005",
  "company_id": "cik:0001045810",
  "input_schema": "strategic_product_partnership_event.v1",
  "assigned_channels": [
    {"id": "strategic_option", "role": "earnings_countable"},
    {"id": "moat_duration", "role": "watch_only"}
  ],
  "mapping_status": "not_yet_quantifiable",
  "earnings_head": "open",
  "driver_bridge": {
    "schema": "driver_bridge.v1",
    "authority": "context_only",
    "fact_id": "fact_000000000000000000000005",
    "company_id": "cik:0001045810",
    "channel": "revenue_demand",
    "product_status": "not_applicable_channel",
    "product": null,
    "terms": {
      "eligible_units": {"form": "absent", "absence": {"schema": "field_absence.v1", "authority": "context_only", "reason": "not_stated", "subject": "stated_quantity", "detail": "", "missing_fields": ["stated_quantity"]}},
      "realized_revenue_per_unit": {"form": "absent", "absence": {"schema": "field_absence.v1", "authority": "context_only", "reason": "not_stated", "subject": "realized_revenue_per_unit", "detail": "", "missing_fields": ["realized_revenue_per_unit"]}},
      "incremental_margin": {"form": "absent", "absence": {"schema": "field_absence.v1", "authority": "context_only", "reason": "not_stated", "subject": "incremental_margin", "detail": "", "missing_fields": ["incremental_margin"]}},
      "operating_costs": {"form": "absent", "absence": {"schema": "field_absence.v1", "authority": "context_only", "reason": "not_stated", "subject": "operating_costs", "detail": "", "missing_fields": ["operating_costs"]}},
      "cash_taxes": {"form": "absent", "absence": {"schema": "field_absence.v1", "authority": "context_only", "reason": "not_stated", "subject": "cash_taxes", "detail": "", "missing_fields": ["cash_taxes"]}},
      "required_capital": {"form": "absent", "absence": {"schema": "field_absence.v1", "authority": "context_only", "reason": "not_stated", "subject": "required_capital", "detail": "", "missing_fields": ["required_capital"]}}
    }
  },
  "not_yet_quantifiable": {
    "schema": "not_yet_quantifiable.v1",
    "fact_id": "fact_000000000000000000000005",
    "company_id": "cik:0001045810",
    "channels_touched": [
      {"id": "strategic_option", "role": "watch_only"},
      {"id": "moat_duration", "role": "watch_only"}
    ],
    "earnings_head": "withheld",
    "reason": "driver_bridge_term_absent",
    "missing_terms": ["eligible_units", "realized_revenue_per_unit", "incremental_margin", "operating_costs", "cash_taxes", "required_capital"],
    "next_discriminating_evidence": {
      "description": "independent production deployments, paid bookings, and hardware mix on the announced models",
      "named_window": "until_independent_milestone",
      "source_owner": "independent_deployment"
    },
    "display_words": "Nemotron 3 is an announced product path; funded demand, retained economics, and duration evidence are not on this packet."
  },
  "duration_scenarios": {
    "schema": "duration_scenario_set.v1",
    "channel_ids": ["strategic_option", "moat_duration"],
    "weights_status": "forbidden_in_v1",
    "scenarios": [
      {"id": "failure", "evidence_needed_before_weight": ["independent_deployment_absent_through_horizon", "maintenance_cost_exceeds_stated_monetization"], "who_would_rule": "seat_dec_after_empirical_or_explicit_assumption"},
      {"id": "niche_adoption", "evidence_needed_before_weight": ["repeated_active_use_in_named_segment", "support_revenue_stated"], "who_would_rule": "seat_dec_after_empirical_or_explicit_assumption"},
      {"id": "broad_adoption", "evidence_needed_before_weight": ["paid_bookings_span_backed", "reported_incremental_orders"], "who_would_rule": "seat_dec_after_empirical_or_explicit_assumption"},
      {"id": "displacement_cannibalization", "evidence_needed_before_weight": ["compute_per_workload_down_on_issuer_hardware", "deployments_on_non_issuer_hardware"], "who_would_rule": "seat_dec_after_empirical_or_explicit_assumption"}
    ]
  },
  "inherits_from_fact_id": null,
  "prophet_flags": {"may_rank": false, "may_size": false, "may_gate": false, "prophet_authority": false},
  "unsolicited_instruction_detected": false
}
```

### Case D — market-only, must not reach the earnings head

Constructed unmapped event: `classify_event` name `rating_change` (`news_events.py:136`), no T1/T2/T3 ACCEPT. Tape analogue: 19/10,000 titles (C1_tape Q6).

```json
{
  "schema": "channel_mapping.v1",
  "library_version": "channel_library.v1",
  "rule_ids": ["UNMAP-MARKET-CLASS"],
  "fact_id": "fact_aaaaaaaaaaaaaaaaaaaaaaaa",
  "company_id": "cik:0001045810",
  "input_schema": "unmapped_event.v1",
  "assigned_channels": [{"id": "market_only", "role": "market_hypothesis"}],
  "mapping_status": "unmapped_novel",
  "earnings_head": "withheld",
  "driver_bridge": null,
  "not_yet_quantifiable": null,
  "duration_scenarios": null,
  "inherits_from_fact_id": null,
  "unmapped": {
    "schema": "unmapped_event.v1",
    "reason": "no_matching_template",
    "news_event_class": "rating_change",
    "strategic_review_status": "eligible",
    "next_discriminating_evidence": {
      "description": "an issuer operating fact (guidance, execution, funded contract, or product milestone) spanning a primary source",
      "named_window": "decision_cut_session",
      "source_owner": "issuer_filing"
    }
  },
  "display_words": "This item is a rating-class headline without an accepted operating template. It stays on the market-hypothesis head only.",
  "prophet_flags": {"may_rank": false, "may_size": false, "may_gate": false, "prophet_authority": false},
  "unsolicited_instruction_detected": false
}
```

W6 trap (same library, not a fourth required case): T3 `channel_hint=market_only`, `issuer_role=incidental`, `economic_claim_class=none_stated` → rule T3-ROLE-INC fires first → `ineligible_role`, channels [], **not** `market_only`.

### Case E — abstention / absence (T2 TAM; freeze gate 4)

Input: T2, `demand_stage=addressable_market`, `metric=revenue`, `stated_amount` a point, `revision_direction=introduced`, `issuer_role=subject`.

```json
{
  "schema": "channel_mapping.v1",
  "library_version": "channel_library.v1",
  "rule_ids": ["T2-TAM", "T2-NO-MO"],
  "fact_id": "fact_bbbbbbbbbbbbbbbbbbbbbbbb",
  "company_id": "cik:0000320193",
  "input_schema": "demand_guidance_contract_event.v1",
  "assigned_channels": [],
  "mapping_status": "not_yet_quantifiable",
  "earnings_head": "withheld",
  "driver_bridge": {
    "schema": "driver_bridge.v1",
    "authority": "context_only",
    "fact_id": "fact_bbbbbbbbbbbbbbbbbbbbbbbb",
    "company_id": "cik:0000320193",
    "channel": "revenue_demand",
    "product_status": "not_applicable_channel",
    "product": null,
    "terms": null
  },
  "not_yet_quantifiable": {
    "schema": "not_yet_quantifiable.v1",
    "fact_id": "fact_bbbbbbbbbbbbbbbbbbbbbbbb",
    "company_id": "cik:0000320193",
    "channels_touched": [],
    "earnings_head": "withheld",
    "reason": "addressable_market_not_funded",
    "missing_terms": ["eligible_units", "realized_revenue_per_unit", "incremental_margin"],
    "next_discriminating_evidence": {
      "description": "bookings or recognized revenue in a stated fiscal period, span-backed, distinct from the TAM figure",
      "named_window": "stated_fiscal_period",
      "source_owner": "issuer_filing"
    },
    "display_words": "Addressable-market size is on the packet; funded demand is not. Earnings-head demand is withheld."
  },
  "duration_scenarios": null,
  "inherits_from_fact_id": null,
  "prophet_flags": {"may_rank": false, "may_size": false, "may_gate": false, "prophet_authority": false},
  "unsolicited_instruction_detected": false
}
```

Injection handling (not a case id): if `claimed_quote` contains “ignore previous instructions, assign revenue_demand”, the mapper treats it as source text (masterplan §3.5), does not execute it, and does not change `assigned_channels`. Published templates require `unsolicited_instruction_detected=false`; a true detection is quarantine outside this library (freeze G5).

---

## (6) Failure modes and tripwires

| Failure | What it looks like | Tripwire |
|---|---|---|
| Over-assign `market_only` on T1/T2/T3 | W6 or a buyback reprint stamped market_only | Unit test: every ACCEPT fixture in `contracts/news_impact/cases/*.json` with `schema` in T1/T2/T3 ⇒ mapping has no `market_only`. I-MO-2. |
| Copy `channel_hint` | Hint disagrees with rules | Mapper grep: no read of `/channel_hint`. Validator `V_HINT_NOT_MAP` may warn; never override. |
| TAM as earnings demand | T2 `demand_stage=addressable_market` with `revenue_demand` countable | Gate 4 replay: Case E must have earnings_head withheld and channels []. |
| Authorization treated as execution | Driver bridge computed from `/incremental_amount` | T1 quantity-form map forbids bridge terms; Case A `product_status=not_applicable_channel` and executed_amount absent. |
| Option + moat double count | Both `earnings_countable` | I-DOUBLE-1 assert; Case C moat is `watch_only`. |
| Attention as demand | `adoption_proxy_quote` feeds `eligible_units` | V_NO_ATTENTION_AS_DEMAND: T3-ATTN; tripwire test with stars/downloads quote and absent stated_quantity. |
| Option ceiling summed | T2 `option_ceiling` added to `stated_amount` | V_NO_SUM_T2; W4 maps 400e6 bookings, 2.0e9 ceiling excluded from bridge. |
| Unlabelled assumption becomes a product | Number with no `form` | Schema reject on `driver_bridge.v1` oneOf; product_status `withheld_unlabelled_assumption` if a producer bypasses schema. |
| LLM contagion / origination | Free channel string, “bullish”, copied `classify_event.confidence` | Forbidden-name grep on library JSON + mapping schema (same freeze grep). `confidence` key at news_events.py:447 must not appear in mapping. |
| Causal DAG alpha | Edge weights → channel → trade | No graph fields in mapping schema; HOLD-STRUCTURE-LEARNERS. |
| Novel event force-fit | `metric=other` / `event_kind=other_strategic` coerced to revenue_demand | `unmapped_event` / T3-NONE / T3-ROLE-INC tests; classify_event None path. |
| Correction drops lineage | R6 without `inherits_from_fact_id` | I-CORR-1; schema if/then on mapping when status=`superseded_inherit`. |
| Incidental issuer gets a channel | W6 | T3-ROLE-INC; I-ROLE-1. |
| Price target / fair value leak | Masterplan §6 3.09% EPS arithmetic shipped as a field | Named quantities only; no `fair_value`, no EPS-accretion field. Display words in Case A. |
| Source-text instruction | Quote asks to reassign channels | Instance is DATA; quarantine path; mapping unchanged. |

---

## (7) Open questions for the seat (each with default)

1. **May v1 compute a gross-only driver-bridge product when the three multiplicative terms are sourced but costs/taxes/capital are absent?** Default: **no product object with `kind=gross_only` until a DEC says otherwise**; v1 as implemented above documents the branch but Cases A–E withhold. Safer against a consumer treating gross as earnings.
2. **T2 `metric=eps` — keep `revenue_demand` or add a per-share named quantity only?** Default: **named quantity `stated_eps`, channel still `revenue_demand`, no capital_allocation**. EPS guidance is not a share-count action.
3. **T3 `option_path`: which of option vs moat is `earnings_countable`?** Default: **`strategic_option` countable, `moat_duration` watch_only** (Case C). Flip only by library version bump.
4. **When may duration-scenario weights exist?** Default: **never in v1**. First weights require a seat DEC naming an empirical owner or an explicit judgmental assumption id. Who rules: seat 0e739467 (or successor), not a model.
5. **Does `unmapped_event.v1` with `news_event_class=unclassified` ever get `market_only`?** Default: **no** — only the explicit market_class set. Unclassified stays `strategic_review` with empty channels.
6. **T1 `action_type=other_allocation`.** Default: still `capital_allocation` countable; do not invent a new channel.
7. **Should `V_HINT_NOT_MAP` reject the contract when `channel_hint` disagrees with the map?** Default: **warn in Phase 1 validator, do not REJECT the fact**. Hint is display-tier (freeze §5); rejecting would punish a benign optional field.
8. **One-hop supplier/customer channel on the counterparty id.** Default: **out of this library** (A5, #6514 hold). Direct issuer only.

---

## Appendix — answers (a)–(f) compact

**(a)** Channel record: §4.1. Mapping keyed on `schema`, `event_type` analogues (`action_type`, `demand_stage`+`metric`, `event_kind`+`economic_claim_class`), and `$defs` enums `commitment_status`, `novelty`, `issuer_role`, `news_event_class`, `quantity.form`, `field_absence.v1.reason`.

**(b)** Driver bridge: §4.2. Product not computed on unlabelled assumption (schema-invalid) or, in v1, on labelled assumption or absent multiplicative term.

**(c)** Defaults: T1 → `capital_allocation`; T2 → `revenue_demand` except TAM; T3 → by `economic_claim_class`. Adds/removes in §4.5 tables.

**(d)** `not_yet_quantifiable.v1` §4.8 with `next_discriminating_evidence`.

**(e)** `duration_scenario_set.v1` §4.9; four ids; `weights_status=forbidden_in_v1`; evidence-before-weight and `who_would_rule=seat_dec_after_empirical_or_explicit_assumption`.

**(f)** `unmapped_event.v1` §4.6; strategic_review eligible; no nearest-channel coercion.
