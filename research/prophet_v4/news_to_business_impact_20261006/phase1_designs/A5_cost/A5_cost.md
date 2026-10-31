# A5_cost — Cost cascade as an operable routing and budget contract

Lane: A5_cost · Seat: Fable 0e739467 · Wave 2 · 2026-10-12
Worktree HEAD: `295e76c6a0` (`295e76c6a0718e49c94b11c501906e4c5ea0adcd`)
Contract schema sha256 prefix: `3edc7139` (frozen; not reopened)
Authority of this artifact: DESIGN only. No signal, score, confidence, probability, price target, or fair value is originated (DNR:KILL-LLM-ORIGINATION). Model output under this cascade may only describe, cite, and abstain.

## (1) ANSWER FIRST

If the 20,000-raw → 3,000-extraction-unit reduction hypothesis fails by half (6,000 extraction units/day), **compact extraction (cheap-tier class) dominates incremental dollar cost**, because it is the first paid-inference stage whose volume scales with extraction-unit count; stronger adjudication (100/day) and frontier review (5/day) are capacity-capped and do not scale with the failed reduction.

The **$10/day incremental ceiling is PROPOSED, not authorized**. At the §10 Flash-Lite anchors the 6,000-unit day is **$4.495** bare and **$8.99** with the masterplan’s own 100% overhead allowance — the $10/day figure does not bind on those anchors alone. It **does bind first** as the operational admission stop because (i) §10 bills retries, retrieval, and tool results into the same envelope, (ii) this repo’s cheap-tier pricing table lists Haiku-class rates at $1/$5 per MTok (`config/ai_pricing.yml`), under which 6,000 compact calls are **$20.70/day before stronger or frontier fire**, and (iii) the conservative admission policy is: **defer cheap extraction when the existing usage ledger would exceed the proposed daily ceiling**, so the daily figure, not the $250/month figure, is the first stop. Exact reproduced arithmetic is in §(g). Current measured tape volume is median **461 items/day** (C1_tape Q2), not 20,000; the 20,000 figure remains an unmeasured assumption until the 600-case run logs the counters in `cost_counters.v1`.

---

## (2) CONSTRAINTS

### STATED (masterplan / freeze)

- S1. Processing order is existing ingestion → cheap deterministic screening and dedup → compact extraction on distinct material deltas → validation → issuer/exposure lookup → deterministic mechanism calculations → selective stronger-model adjudication → rare frontier thesis review → existing evidence/Prophet consumers. (MASTERPLAN.md §10)
- S2. Use the existing router, metering, concurrency admission, queue and retry owners. No shadow router, second queue, or per-chat multiplied concurrency budget. (MASTERPLAN.md §10)
- S3. Cache by document revision, event facts, baseline, relationship generation, model/prompt/schema version and rights state. A source correction invalidates dependent analyses. A model update does not retroactively rewrite old predictions. (MASTERPLAN.md §10)
- S4. Expensive review packet contains new evidence, old thesis, relevant driver/exposure facts, alternative mechanisms, and the unresolved decision; not months of duplicated articles. Analyze a macro/industry event once, then derive issuer-specific exposures. (MASTERPLAN.md §10)
- S5. Escalation rules: material issuer-relative change; disputed high-consequence fact; unfamiliar mechanism; contradiction to an active thesis; or time-sensitive adverse information. Reserve 10–15% of review capacity for random/stratified low-score and rejected-item audits. These are proposed workload controls, not capital-allocation rules. (MASTERPLAN.md §10)
- S6. Preserve all inputs when model budgets are exhausted; mark inference deferred; maintain basic factual visibility. Do not turn unprocessed into neutral or silently truncate the tape. Adverse-event visibility must not depend on an expensive analyst call. (MASTERPLAN.md §10)
- S7. $10/day and $250/calendar-month incremental inference ceilings, and the $750 development envelope in $150/$350/$250 tranches, are **PROPOSED, not authorized**. Existing subscriptions, licenses, taxes, paid-search/tool fees, storage and infrastructure are excluded. No universal per-article internet search. (MASTERPLAN.md §10)
- S8. §10 table numbers are assumptions, not measured traffic. The 20,000 → 3,000 reduction is a hypothesis to measure on the sampled 600 before any wider run. (MASTERPLAN.md §10; program upgrade 6)
- S9. Company identity = `cik:` + 10 digits. Evidence = owner `source_span.v1` exactly as `documents.py` SourceSpan emits, or `field_absence.v1`. Every enum closed as the schema states. No confidence / probability / price-target / score field. (PHASE0_FREEZE_2026-10-11.md D12/D13/D14; rulings R1–R4)
- S10. Novelty is read from qbus `novelty_z` and echo context only; this program mints no second novelty score. (PHASE0_FREEZE D11)
- S11. Envelope carries `fact_id`, `document_id`, `observed_at`, `source_available_at`, `supersedes_fact_id`; `novelty = corrected_fact` requires `supersedes_fact_id` non-null. (PHASE0_FREEZE D16)
- S12. Source text is data, never tool authority. (MASTERPLAN.md §3.5)
- S13. Standing kills: DNR:KILL-LLM-ORIGINATION, KILL-LLM-CONFIDENCE, KILL-LLM-CONTAGION-TAGS, KILL-CAUSAL-DAG-ALPHA, KILL-THESIS-LOBE, KILL-STALENESS-ALPHA, HOLD-STRUCTURE-LEARNERS. PR #6514 remains HOLD-FOR-SOL.
- S14. Routing-quality endpoints already named: cost at fixed material-event recall; coverage of strategically important nonnumeric events; **reject-audit miss rate**; calibration of defer/escalate decisions. (MASTERPLAN.md §11)
- S15. Proposed §11 thresholds (owner-frozen before measurement): ≥98% critical-numeric correctness among auto-published outputs; ≥95% material-event routing recall on the labeled set; zero unsupported ticker-to-supplier assertions; complete processing/defer/reject accounting; successful correction replay. (MASTERPLAN.md §11)

### PHYSICS

- P1. Token cost is linear in (input_tokens × in_rate + output_tokens × out_rate) / 1e6. Cache-read and cache-create tokens bill at the multipliers in `config/ai_pricing.yml` (read 0.10×, write 1.25×).
- P2. A keep-FIRST store cannot recover a dropped first-seen row after a later duplicate arrives (`engine/qbus.py` drop_duplicates keep=first). Truncating the tape is irreversible for PIT identity.
- P3. POSIX O_APPEND JSONL writes under PIPE_BUF are atomic (`lib/ai_costs.py` record_usage docstring). Parallel lanes may interleave rows; they must not share a mutable in-process budget counter as the source of truth.
- P4. 6,000 × Flash-Lite envelope = $1.92/day compact; 6,000 × Haiku $1/$5 = $20.70/day compact. The daily ceiling’s bind-or-not is a rate-table fact, not a routing-policy fact.

### INHERITED (owner modules read this session)

- I1. **Queue / item identity.** `engine/qbus.py:12-24, :61-62, :248-265` — append storage, keep-FIRST on `item_id`, shingled-title `event_key`, `novelty_z`, `echo_stats`. Not a scoring input.
- I2. **Item key mint.** `engine/qkernel.py:207-211` — `item_id(source, url, title, lang)` SHA1-16 of normalized title plus host.
- I3. **Deterministic screen.** `engine/news_common.py:368-430` — `is_low_value` / `low_value_reason` closed reason tokens; PURE.
- I4. **Reject/kept PIT ledger.** `engine/news_event_ledger.py:8-9, :105-203` — keep-FIRST on `event_id`; `persist_reject_sample`; leaf, context-only. LEAF never appends from this program (freeze §9 reuse matrix).
- I5. **News revision identity.** `engine/qbus_news_contract.py` SCHEMA `qbus.news_revision.v1`; fields `revision_id`, `content_hash`, `body_sha256`, `action` (pure, no clock).
- I6. **Bounded clustering.** `engine/qbus_news_cluster.py` — conservative false-negative-leaning cluster; exact source identity; fuzzy join requires shared canonical security, family, window, discriminators, immutable-anchor title match.
- I7. **Router (in-process waterfall).** `engine/llm_auth.py:341-450` `make_call(providers, call_fn, …)` 401-fallback waterfall; dead-provider skip; `LEDGER_PROVIDER` at `:535-541`; `_capture_usage` → `lib.ai_costs`. This is the call router this estate owns.
- I8. **Lane admission.** `engine/neuralweb/capability_broker.py` `resolve(capability_id, lane=)` returns ref NAME only; fail-closed allowlist from `config/capability_manifest.yml`.
- I9. **Concurrency / cooling admission.** `engine/neuralweb/key_pool.py` — estimated 5h/weekly load, `is_cooling`, `mark_cooling` on 429, `all_cooling_freeze_info`; NEVER-RAISE; no secret values.
- I10. **Budget admission.** `engine/metabolism/budget_gate.py:1-22, :59-82, :capacity_budget_config` — gate verdicts `5h_max` / `weekly_max` / `manual`; config `config/metabolism_budget.yml` IMMUTABLE operator-tap (`per_cycle_usd_cap: 25` is metabolism-loop, **not** this program’s $10/$250).
- I11. **Metering / usage ledger.** `lib/ai_costs.py:1-48, :279-338` SCHEMA `ai_costs.usage.v1`; `record_usage(lane, provider, model, tokens, cost_basis, cycle_id, stage, …)`; lobe map already contains `"news-llm": "News"`.
- I12. **Capacity projection.** `engine/provider_capacity.py:1-12, :22` SCHEMA `mastermind.provider_capacity.v1`; secret-free; does not dispatch. DEC-EXECUTIVE-CAPACITY-FABRIC-OWNERSHIP-AND-CONTRACT: Macro owns provider availability; **Mastermind Model Router** (other repo, `control_plane/model_router.py`) is the stateless task-to-acceptable-model/execution-class filter; Executive OS is placement. This cascade consumes those three; it does not replace them.
- I13. **Retry / rung telemetry.** `engine/provider_health.py:1-40` — one JSONL row per waterfall ATTEMPT (`error_class` includes `usage_limit`, `auth`, `timeout`); credentials never written. `llm_auth.make_call` is the retry owner (next-rung on 401; cooling on 429).
- I14. **Pricing table.** `config/ai_pricing.yml` — Haiku $1/$5, Sonnet-4-6 $3/$15, Opus/Fable-placeholder $5/$25, DeepSeek-flash $0.14/$0.28, DeepSeek-pro $0.435/$0.87. No Gemini Flash-Lite row exists in this table. §10’s $0.10/$0.40 anchors are research arithmetic, not a routing instruction.
- I15. **Cheap annotator (do not reuse as extractor).** `engine/news_llm.py:1-42, :225-256` — gated, default-off in freeze reuse matrix; produces `llm_importance` / `llm_tone` (forbidden as scored inputs); `max_batches` silently dropped ~87% of the tape. This cascade does **not** call `annotate()` for extraction.
- I16. **Issuer identity.** `engine/company_intelligence/identity.py:50-58` `company_id_for_cik` → `cik:` + 10 digits (example `cik:0000320193`).
- I17. **Evidence object.** `engine/company_intelligence/documents.py:308-365` `SourceSpan.to_payload()` 12-key `source_span.v1`; `:189-201` revision ≥ 1 and `supersedes_document_id` required when revision > 1; `:369-371` `span_id` from full locator.
- I18. **Closed company-event types.** `engine/company_intelligence/events.py:93-99` `EVENT_TYPES` has no `news` member. Leaf templates key by `company_id` + `source_document_id` (freeze F1/D6); `ci_event_id` is typed absence unless type ∈ EVENT_TYPES.
- I19. **Resolution order.** `engine/company_intelligence/resolution.py:1-25, :285` — availability firewall → supersession collapse → byte replay → declared address → typed absence. Failure direction is more absences, never more receipts.
- I20. **Display cost panel.** `admin/ai_cost.py:1-12` — estimator + unified view over `lib.ai_costs`; not a write path for this cascade.

### ASSUMED (dropped if they have no consumer)

- A1. Cheap-tier class is placed by the existing Model Router onto whatever admitted cheap capability the waterfall has that day. This design names **classes**, not vendors. (If this is wrong, I12 already forbids us from picking a vendor inside Macro.)
- A2. “Low-score” in §10 means **router dispositions that did not escalate** (reject, duplicate-stop, not-material, compact-only), not a numeric score. A numeric score field is a standing kill. What breaks if violated: KILL-LLM-CONFIDENCE.
- A3. Review-capacity denominator for the 10–15% audit is **stronger-tier decision slots per UTC day** (illustrative 100), not raw items. What breaks if violated: audit volume would explode to 10% of 20,000.
- A4. UTC day is the daily ceiling window; calendar month is UTC month. What breaks: a local-tz day would desynchronize `lib.ai_costs` `ts` stamps (UTC).
- A5. Metabolism `per_cycle_usd_cap: 25` is a **different program**. This cascade does not spend against it and does not raise it. What breaks: mixing them would either starve metabolism or silently double-count.

---

## (3) THREE MECHANISM-DISTINCT CANDIDATES

### C1 — Existing-owner stage gate (CHOSEN)

One routing table (`cascade.v1`) consulted by a leaf adapter under `engine/news_impact/`. Every paid call goes through `llm_auth.make_call` with a capability-broker-allowed lane (new lane name `news-impact-extract` / `news-impact-adjudicate` / `news-impact-frontier` added to the manifest by operator tap, not by this design). Every call writes `lib.ai_costs.record_usage` with `stage=<stage_id>`. Admission is `budget_gate` + `key_pool.is_cooling` + the proposed $10/$250 counters summed from the same ledger. The news queue remains `qbus` keep-FIRST. No second queue.

**Refutation test:** grep the adapter for any HTTP client, SDK construct, or `record_usage` bypass; a single paid call that has no `ai_costs.usage.v1` row with `stage` set **kills C1**.

### C2 — Per-item always-extract, savings only via cache

Every eligible item is a cheap-tier extraction unit; cache-key hits skip a billable call. Mechanism: volume reduction is a cache property, not a screening property.

**Refutation test:** on the C1_tape population, 94.9% of rows are already first-in-`event_key` (C1_tape Q5) and `event_key` is 91% singletons, so cache-on-item-id barely reduces first-seen volume. Run: `N_extract / N_eligible` after cache-only policy on a 90-day replay; if the ratio stays > 0.5, C2 has not produced the 20k→3k reduction and is dead. Also fails S1 (“compact extraction on **distinct material deltas**”).

### C3 — Human-queue-first (outside the build-something space)

No model call until an operator (or seat) picks the item from a docket. Deterministic stages still run and persist facts.

**Refutation test:** freeze §12 Phase 1 exit requires “Real documents → validated claims → dedup/novelty deltas → issuer facts; full rejection/defer accounting.” A 600-case commission D that cannot start without a human pick per case fails the ready-to-start condition. Also fails S6: adverse-event visibility would depend on an expensive (human) analyst call.

### Why C1 wins

C2 cannot create the material-delta unit §10 named; C1_tape already shows item-level identity is near-unique. C3 blocks Phase 1 and the 600-case measurement. C1 is the boring baseline: it is a **policy table over owners that already admit, meter, retry, and queue**. A shadow router (explicitly forbidden, not a candidate) would fail I12’s DEC: Model Router stays the task-to-class filter; this table only names the class each stage may request.

---

## (4) FROZEN-SPEC DRAFT

Builder implements this without asking. Anything not listed is out of scope.

### 4.1 Objects and closed enums

Schema files: `cascade.v1.json` (instance) and `cost_counters.v1.schema.json` (this directory). JSON Schema dialect: draft 2020-12. Authority: `context_only`.

**`model_tier_class`** (closed): `deterministic` | `cheap` | `stronger` | `frontier`. No vendor string on the cascade object. Placement of a class onto a capability is the existing Model Router + `llm_auth` waterfall.

**`stage_id`** (closed, order frozen, 0-indexed `stage_index`):

| stage_index | stage_id | tier |
|---|---|---|
| 0 | `ingestion` | deterministic |
| 1 | `deterministic_screen_dedup` | deterministic |
| 2 | `compact_extraction` | cheap |
| 3 | `validation` | deterministic |
| 4 | `issuer_exposure_lookup` | deterministic |
| 5 | `deterministic_mechanism` | deterministic |
| 6 | `stronger_adjudication` | stronger |
| 7 | `frontier_thesis_review` | frontier |
| 8 | `consumers` | deterministic |

A stage may not run unless every lower `stage_index` has a terminal disposition in `{completed, cache_hit, stop_*, reject, defer_*}` for that item. Skipping forward is a contract error `stage_order_violation`.

**`routing_disposition`** (closed): `process` | `cache_hit` | `stop_duplicate` | `stop_low_value` | `stop_not_material_delta` | `stop_unresolved_issuer` | `extract_complete` | `validate_complete` | `validate_reject` | `lookup_complete` | `lookup_absence` | `mechanism_complete` | `mechanism_absence` | `adjudicate_complete` | `frontier_complete` | `consume_complete` | `defer_budget` | `defer_capacity` | `defer_body_unavailable` | `defer_rights` | `reject` | `audit_sample`.

**`escalation_reason`** (closed; trigger table in §(c) below): `none` | `material_issuer_relative_change` | `disputed_high_consequence_fact` | `unfamiliar_mechanism` | `contradiction_to_active_thesis` | `time_sensitive_adverse_information` | `audit_reserve_draw`.

**`inference_state`** (closed): `not_required` | `completed` | `deferred` | `rejected`. Unprocessed items stay `deferred` or stay in their last completed deterministic state. **Never** write a synthetic “neutral / no-change / zero-impact” fact for an unprocessed item.

**`ceiling_authority`** (closed): `proposed_not_authorized` | `authorized` | `exhausted`. Ship with `proposed_not_authorized` until the seat records an authorization DEC.

**`audit_stratum`** (closed): `rejected_low_value` | `stop_duplicate` | `stop_not_material_delta` | `extracted_not_escalated` | `validate_reject` | `deferred_any`.

**`lane_id`** (closed, capability-broker names to add by operator tap): `news-impact-extract` | `news-impact-adjudicate` | `news-impact-frontier` | `news-impact-audit`. These join the News lobe via `lib/ai_costs.py` `_LANE_LOBE_EXACT` (today `"news-llm": "News"` at `lib/ai_costs.py` ~lobe map). Until the tap lands, the adapter **must not** call a model (fail closed).

Forbidden fields on every object in this spec: `confidence`, `probability`, `score`, `llm_importance`, `llm_tone`, `price_target`, `fair_value`, `rating`, `expected_move`. A builder adding one fails the freeze forbidden-grep.

### 4.2 Stage table (question a)

Volume formulas use measured counters from `cost_counters.v1` (names in **bold**). Substitute §10’s illustrative numbers only in the commentary column; builders wire the formula.

Token envelopes are **hard caps** (a call that would exceed them is `defer_budget` with reason `token_envelope_exceeded`, not truncated). Billable reasoning, retries, retrieval, and tool results count against the envelope and against the day/month ceilings (MASTERPLAN.md §10).

| stage_id | input | output | tier | expected volume / UTC day | token envelope (in/out) | ceiling | at ceiling |
|---|---|---|---|---|---|---|---|
| `ingestion` | collector/qbus revision (`qbus.news_revision.v1`) | `qbus` row with `item_id`, `body_sha256`, capture stamps | deterministic | **n_raw** = counted ingestions that UTC day | 0 / 0 | none (I/O only) | keep writing; never drop; back-pressure via existing collector retry |
| `deterministic_screen_dedup` | qbus row | disposition + optional `event_key` / cluster id | deterministic | **n_raw** | 0 / 0 | none | n/a |
| `compact_extraction` | distinct material-delta packet (body + template id + prior fact ids) | `news_impact_event.v1` candidate or `field_absence.v1` | cheap | **n_extract** = `n_material_delta` | 2200 / 250 | min(remaining proposed $10 day, remaining $250 month, envelope, key_pool not cooling) | `defer_budget` or `defer_capacity`; inputs preserved; `inference_state=deferred` |
| `validation` | candidate packet | accept / `validate_reject` with closed reason | deterministic | **n_extract_complete** | 0 / 0 | none | n/a |
| `issuer_exposure_lookup` | accepted packet | `company_id` (`cik:`+10) + issuer_role + exposure facts or typed absence | deterministic | **n_validate_complete** | 0 / 0 | none | n/a (D12 ladder; no web search) |
| `deterministic_mechanism` | accepted packet + lookup | channel_hint ∈ closed 7-enum **from the template**, or `mechanism_absence` | deterministic | **n_lookup_terminal** | 0 / 0 | none | n/a |
| `stronger_adjudication` | review packet §(e) | adjudicated packet or abstention; never a score | stronger | **n_escalate** + **n_audit** ≤ `stronger_slot_cap` (illustrative 100) | 4500 / 700 | same $ ceilings + slot cap | items past cap stay at last deterministic output; `defer_budget`; **not** rewritten as no-change |
| `frontier_thesis_review` | same packet shape, plus alternative mechanisms | thesis-review note (describe/cite/abstain) | frontier | **n_frontier** ≤ `frontier_slot_cap` (illustrative 5) | 12000 / 1500 | same $ ceilings + slot cap | defer; keep deterministic/cheap outputs visible |
| `consumers` | any terminal packet with `inference_state ∈ {completed, deferred, rejected}` | Prophet `context_only` read; B4 unchanged | deterministic | **n_terminal** | 0 / 0 | none | consumers must render deferred items as deferred (plain words + window), never as silence |

**Screen/dedup stop rules (deterministic, no model):**

1. `low_value_reason(title, domain, author) is not None` → `stop_low_value` (reason token from I3). Still persisted on the tape.
2. `item_id` already in qbus keep-FIRST → `stop_duplicate` (identity duplicate).
3. Cluster member that is not the representative (qbus `event_key` representative, else `qbus_news_cluster` anchor) **and** no new discriminator (no new numeral, no new counterparty string, no `corrected_fact` marker) → `stop_duplicate`.
4. After 1–3, a **material delta** is a remaining item whose body is available and that is either first-in-cluster **or** carries a new numeral / commitment_status change / named counterparty relative to the cluster representative’s extracted facts. Count these as **n_material_delta**. Items that fail this test → `stop_not_material_delta`.
5. Body fetch failure through the allowlisted owner → `defer_body_unavailable` (C1_tape / freeze §8). Counted, never dropped.
6. Rights registry miss → `defer_rights`. Counted.

Issuer unresolved after D12 ladder (`cik_map` snapshot ≤ capture date → `ticker_cik_ledger` flagged `ledger_fallback` → typed absence) → `stop_unresolved_issuer` with `field_absence.v1` reason `not_stated` (or owner_reason `unjoinable_filing_identity` when that is the owner fact). Counted.

**Volume formulas (measured):**

```
n_raw              = count(ingestion completions that utc_day)
n_low_value        = count(stop_low_value)
n_identity_dup     = count(stop_duplicate where cause=item_id keep-FIRST)
n_cluster_dup      = count(stop_duplicate where cause=cluster_representative)
n_eligible         = n_raw - n_low_value
n_first            = n_eligible - n_identity_dup
n_cluster_rep      = n_first - n_cluster_dup
n_body_unavail     = count(defer_body_unavailable)
n_material_delta   = count(material-delta true after rules 1–6)
n_extract          = n_material_delta          # cheap-tier offered volume
n_extract_complete = count(extract_complete)
n_escalate         = count(escalation_reason != none AND != audit_reserve_draw)
n_audit            = count(escalation_reason == audit_reserve_draw)
n_frontier         = count(stage_id==frontier_thesis_review & disposition==frontier_complete)
reduction_ratio    = n_raw / max(n_extract, 1)
```

Illustrative substitution (NOT to be wired as constants): `n_raw=20000`, `n_extract=3000`, `n_escalate=100-n_audit`, `n_frontier=5`.

### 4.3 Cache key and invalidation (question b)

Cache object `news_impact.inference_cache.v1`. Lookup is exact-match on `cache_key`.

```
cache_key = sha256( utf8( join("|", [
    "news_impact.inference_cache.v1",
    document_id,
    str(document_revision),          # SourceDocument.revision >= 1
    news_revision_id,                # qbus.news_revision.v1 revision_id
    content_hash,                    # qbus NewsRevision.content_hash
    body_sha256,
    event_facts_hash,                # sha256 of canonical JSON of extracted critical fields, or "none"
    baseline_id,                     # baseline.type + period key, or "absence"
    relationship_generation,         # integer; 0 if no relationship owner read (K3-D still HOLD)
    model_id,                        # Model Router class placement id (opaque)
    prompt_version,
    schema_version,                  # "news_impact_event.v1" + schema sha256 prefix 3edc7139
    rights_profile,                  # SourceSpan.rights_profile
    stage_id
]))) )
```

`event_facts_hash` covers the critical numeric slots of the frozen templates (T1 amounts, T2 stated_amount, T3 none-numeric allowed). Canonical JSON: UTF-8, sorted keys, no whitespace.

**Hit rule:** if `cache_key` exists and `inference_state=completed`, replay the stored packet; disposition `cache_hit`; **do not** call a model; **do** write a cost-counter increment `n_cache_hit` with `est_cost_usd=0`.

**Source-correction invalidation:** a new `SourceDocument` with `revision = old+1` and `supersedes_document_id = old.document_id` (documents.py:199-201), or a `NewsRevision` whose `content_hash`/`body_sha256`/`revision_id` differs, produces a **new** `cache_key`. The old cache row is retained (append-only). Dependent analyses are not patched in place. A new extraction is offered; if it produces `novelty=corrected_fact` the envelope **must** set `supersedes_fact_id` (D16). Consumers read the latest revision chain, same as `DocumentRevisionChain.latest()`.

**Model/prompt/schema update:** new version ⇒ new `cache_key` ⇒ new analysis **appended**. Old predictions remain with their versions. **Never** overwrite an old packet’s fields. (MASTERPLAN.md §10)

**Rights-state change:** a tighter `rights_profile` on the same bytes ⇒ new key; previously published excerpts that fail R1/R2 projection are nulled at the projector (rulings R1/R2), not by cache mutation.

No TTL. No wall-clock invalidation (KILL-STALENESS-ALPHA). Freshness is revision identity.

### 4.4 Escalation rules (question c)

Closed enum `escalation_reason`. Each trigger is a predicate over **already-typed fields**. No score. First matching reason wins (order below). `none` if none match. Audit draw is applied **after** this table, on the residual, without removing a true escalation.

| reason | deterministic trigger (all must hold) |
|---|---|
| `material_issuer_relative_change` | A critical quantity slot has `form != absent` AND (`commitment_status ∈ {executed, completed, withdrawn}` OR `revision_direction ∈ {raised, cut, withdrawn, cancelled, awarded}` OR T1 `action_type ∈ {share_repurchase, equity_issuance, debt_issuance, special_dividend}`) AND the quantity is present as point or range. Issuer-relative: the same slot’s prior fact (by `supersedes_fact_id` chain or same `(company_id, template, period)`) is absent OR the canonical numeric value differs. No ratio threshold is originated here; “differs” is exact after the Phase 1 normaliser. |
| `disputed_high_consequence_fact` | Two independent cheap-tier passes (same `cache_key` except `prompt_version` distinguished as `extract.a` / `extract.b`, different model **families** when the router can place them; otherwise two prompt_versions) disagree on any critical numeric (value, unit, basis, period, negation) OR on `commitment_status` OR on `negation` of the fact, AND the fact’s quantity is present. “High-consequence” is the same material-change predicate as the previous row (so a disputed incidental comment does not escalate). |
| `unfamiliar_mechanism` | `channel_hint` cannot be filled from the template’s closed enum given the extracted facts (validator would have to invent a hint) OR the mechanism card cache for `(channel_hint, relationship_generation)` is absent. Outcome of the stage-5 function is `mechanism_absence` with `field_absence.v1` reason `not_stated`. |
| `contradiction_to_active_thesis` | An active thesis packet exists for `company_id` (consumer-owned, read-only) AND a newly accepted critical field is logically incompatible with a stored field of the same slot (e.g. new `commitment_status=withdrawn` vs stored `executed` without a `corrected_fact` / `supersedes_fact_id`; or `revision_direction=cut` vs stored `raised` on the same period). Absence vs value is not by itself a contradiction (that is ordinary new information). |
| `time_sensitive_adverse_information` | `news_event_class ∈ {guidance_cut, customer_loss, product_delay, regulatory_probe, litigation, bankruptcy_restructuring, mna_rumor}` OR `commitment_status=withdrawn` OR T2 `revision_direction ∈ {cut, withdrawn, cancelled}` AND `source_available_at` is on the same UTC day as `observed_at` (envelope timestamps; **no ambient clock**). |
| `audit_reserve_draw` | Item was **not** escalated by the five reasons above AND it is in the seeded stratified draw of §(d). |
| `none` | Otherwise. Compact extraction is the terminal paid stage. |

Frontier review is **not** an escalation_reason. It is a second gate: among `stronger_adjudication` completions, a frontier slot is consumed only when `unfamiliar_mechanism` OR `contradiction_to_active_thesis` still holds after stronger adjudication (the stronger packet’s `unresolved_decision` field is non-empty). Cap: `frontier_slot_cap` (illustrative 5). Remainder stays at stronger output.

### 4.5 Audit reserve (question d)

**Denominator.** `review_capacity = stronger_slot_cap` (illustrative 100/day; on the 600-case run, `stronger_slot_cap = max(1, ceil(0.15 * n_labeled_in_run))` is replaced by the measurement plan’s explicit audit count).

**Rate.** Closed interval 10–15%. **Default 12%** (see Q1). `n_audit_target = floor(rate * review_capacity)`. Escalations from §4.4 consume slots first; audit fills leftover slots, and **never** starves a true escalation (if `n_escalate >= review_capacity`, audit_target becomes `max(0, review_capacity - n_escalate)` and a counter `n_audit_starved` increments — the tripwire in §6).

**Who is eligible.** Residual items with `escalation_reason=none` in strata `audit_stratum`. Rejected and low-disposition items **must** be in the frame (this is how the cheap router is audited).

**Draw (seeded, stratified, no `random` module).**

```
seed = 20261012          # recorded; integer; see Q2
for each stratum S:
    eligible = items with audit_stratum=S and inference not already escalated
    quota[S] = round(n_audit_target * weight[S]) with largest-remainder to sum exactly
    rank_key(item) = sha256( utf8( f"{seed}|{S}|{item_id}" ) ).hexdigest()
    take the quota[S] items with smallest rank_key
```

Default weights (sum 1.0): `rejected_low_value=0.25`, `stop_duplicate=0.10`, `stop_not_material_delta=0.25`, `extracted_not_escalated=0.25`, `validate_reject=0.10`, `deferred_any=0.05`. A stratum with fewer eligible than quota donates remainder to `extracted_not_escalated` then `stop_not_material_delta`.

**Who reviews.** Stronger-tier class via lane `news-impact-audit`, **distinct** `prompt_version` from `news-impact-extract` and from `news-impact-adjudicate`. Same token envelope as stronger (4500/700). Labeler protocol of freeze §7 applies: two families, third on disagreement, seat residual. The reviewer produces the same frozen templates (describe/cite/abstain), never a score.

**Miss-rate metric (feeds §11 routing quality).**

```
reject_audit_miss_rate = n_audit_rejects_labeled_material / n_audit_rejects
```

where `n_audit_rejects` = audit-sampled items whose cheap-path disposition ∈ {`stop_low_value`, `stop_not_material_delta`, `stop_duplicate`, `validate_reject`, `reject`}, and `n_audit_rejects_labeled_material` = those whose audit label is a material event that should have reached compact extraction (gate-4 label `correct` on template identity, freeze §3 gate 4). Report the Wilson interval at n recorded. **This is the eval endpoint** named in MASTERPLAN.md §11 “reject-audit miss rate”. Calibration of defer/escalate is a separate counter pair (`n_escalate_agreed`, `n_escalate_over`) on the audit of `extracted_not_escalated` vs `n_escalate`.

Display-tier wording for a miss: “On the audit sample of rejected items, N of M were later labeled as material events; the window is the labeled 600-case run.” Never a certainty.

### 4.6 Review packet (question e)

Object `news_impact.review_packet.v1`. Hard cap: **4500 input tokens / 700 output tokens** at stronger; **12000 / 1500** at frontier. A builder who cannot fit the packet **must** drop in this order (never drop 1–2): (6) cluster sibling titles beyond 5, (5) mechanism-card bodies beyond 3, (4) driver-dossier rows beyond 10, (3) alternative-mechanism cards beyond 4. If still over cap: `defer_budget` reason `token_envelope_exceeded`.

Required keys (all present; use `field_absence.v1` rather than omitting):

1. `new_evidence` — the candidate `news_impact_event.v1` plus its `evidence_span` list (owner `source_span.v1` or `field_absence.v1`). `claimed_quote` ≤ 500 chars, text_safe (R1/R2).
2. `old_thesis` — last accepted thesis packet for `company_id` if any; else `field_absence.v1` reason `not_stated`, subject `old_thesis`.
3. `driver_exposure_facts` — precomputed issuer driver-dossier rows **already in cache** (S4 “Precompute issuer driver dossiers”); no live per-article search. Each row cites a span or an absence.
4. `alternative_mechanisms` — 0–4 mechanism cards from the precomputed set whose `channel_hint` differs from the candidate’s. Empty array is allowed; it is not an invitation to invent.
5. `unresolved_decision` — closed: `which_template` | `critical_numeric_conflict` | `mechanism_choice` | `correction_linkage` | `exposure_identity` | `none`. Plain-words description ≤ 240 chars, text_safe, **no** instruction-like not-patterns (D17). This field is the question the expensive tier is asked to describe/cite/abstain on.

Forbidden in the packet: raw duplicated article bodies; months of cluster members; any confidence/score; any price; any internet-search result that was not already an allowlisted owner capture.

Macro/industry event rule: one frontier (or stronger) call per `event_cluster_id`; issuer-specific exposures are **derived deterministically** at stage 4–5 from that one review plus the issuer dossier. Never N frontier calls for N tickers sharing a tag (MASTERPLAN.md §10).

### 4.7 Budget exhaustion (binds S6, S7)

**Meters (summed from `ai_costs.usage.v1` where `lane` starts with `news-impact-` and `ts` in window):**

- `usd_day` — UTC date of `ts`
- `usd_month` — UTC year-month of `ts`
- `tokens_in_stage[stage_id]`, `tokens_out_stage[stage_id]`
- `n_calls_stage[stage_id]`
- `n_retry_rungs` from `provider_health` attempts with `ok=false`

**Proposed ceilings (not authorized):** `DAY_USD=10`, `MONTH_USD=250`. Whichever binds first. Development tranches $150/$350/$250 are **out of the runtime path**; they are a seat/operator envelope, logged as `ceiling_authority=proposed_not_authorized` on the program record, never as a per-call check.

**Admission, in order, before every paid call:**

1. capability_broker.resolve(cap, lane) allowed.
2. key_pool: not `all_cooling`; prefer non-cooling.
3. budget_gate.gate_verdict for the execution mode the host is in (do not invent a mode).
4. `usd_day + estimate_cost_usd(model, envelope_in, envelope_out) <= DAY_USD` (when ceiling_authority is treated as binding by operator; while still `proposed_not_authorized`, the adapter **still computes and logs** the would-bind flag `day_would_bind` / `month_would_bind` so the 600-case run can report it).
5. stage envelope.
6. slot cap for stronger/frontier.

On any fail of 1–6: disposition `defer_budget` or `defer_capacity`; **do not** call; **do not** delete or rewrite inputs; qbus row remains; `inference_state=deferred`; consumers show the deterministic facts already in hand (title, source, time, issuer if resolved, low-value reason if any) with the plain-words window “inference deferred this UTC day because the incremental inference ceiling was reached.” Adverse classes in the `time_sensitive_adverse_information` trigger still **must** remain visible at the factual layer (title + class + time) even when inference is deferred.

**Never:** map deferred → `revision_direction` that implies no change; map deferred → `commitment_status` invented; drop the qbus row; skip writing a cost-counter row (write `n_deferred_budget += 1`).

Retries: only the `llm_auth.make_call` waterfall (next rung on 401; cool on 429). No extra retry loop. Each rung attempt is a `provider_health` row; successful usage is one `record_usage` row. Retry tokens count.

No per-chat budget. No second queue: deferred items remain on qbus and are offered again the next UTC day in keep-FIRST order, oldest `source_available_at` first, **without** re-ingesting.

### 4.8 Measurement plan replacing the 30-day scenario (question f)

The 600-case run **is** the measurement. It is not a production day. Counters are those in `cost_counters.v1`. Required per stage, per case, and run-level.

**Per case (600 rows):** `case_id`, `group_id`, `fold`, `template_id`, `item_id`, `company_id` or absence, `stage_terminal`, `routing_disposition`, `escalation_reason`, `inference_state`, `cache_hit` bool, `n_rungs_attempted`, `input_tokens`, `output_tokens`, `est_cost_usd`, `model_tier_class`, `prompt_version`, `schema_version`, `rights_profile`, `supersedes_fact_id` or null, `body_available` bool, `audit_stratum` or null, `audit_drawn` bool.

**Per stage run-level:** the volume formula fields in §4.2 plus `sum_input_tokens`, `sum_output_tokens`, `sum_est_cost_usd`, `n_cache_hit`, `n_defer_budget`, `n_defer_capacity`, `n_defer_body_unavailable`, `n_reject`, `n_envelope_exceeded`, `n_stage_order_violation` (must be 0).

**Run-level reduction:**

```
R = n_raw_in_sampling_window / n_extract_in_sampling_window
```

The sampling window is the freeze §6 manifest window (trailing 90d of publisher `seendate` frozen by tape sha), not a live 30-day guess. `n_raw_in_sampling_window` is C1-style tape count in that window after ingestion identity (53,658 in the 2026-05-05..2026-10-11 census — **this number moves with the tape**; the manifest freezes it). `n_extract_in_sampling_window` is how many distinct material deltas the stage-1–2 predicates emit when run over that window (including the 600 labeled plus unlabeled residuals). The 20,000/3,000 hypothesis is **R_hyp = 20/3 ≈ 6.667**.

**Decision rule for scaling beyond the 600:**

| gate | default | fail action |
|---|---|---|
| complete processing/defer/reject accounting (`n_raw == sum of all terminal dispositions`) | required | do not scale; fix accounting |
| `n_stage_order_violation == 0` | required | do not scale |
| material-event routing recall on labeled 600 ≥ 0.95 | §11 | do not scale; retune screen/escalation |
| critical-numeric correctness on auto-published subset ≥ 0.98 | §11 | do not scale; keep cheap extractor in abstain-heavy mode |
| unsupported ticker-to-supplier assertions | 0 | do not scale |
| `reject_audit_miss_rate` ≤ 0.05 | Q3 default | do not scale; raise audit rate to 15% and retune screen |
| measured R ≥ 4.0 | Q4 default (half of 6.667, matching “fails by half”) | do not scale to live 20k-class volume; compact extraction would dominate; stay on the labeled population and retune dedup/material-delta |
| recorded `sum_est_cost_usd` for the 600 run | any, but must be logged | missing log = do not scale |
| `day_would_bind` under proposed $10 at the **projected** live `n_extract = n_raw_live / R` using the **measured** cheap-tier `est_cost_usd` per extract | if true, scale only with defer policy armed | arm S6 defer before any wider run |

A wider run means “live cascade on the current tape beyond the 600 labels.” It does **not** mean raising DAY_USD. Ceilings stay proposed until a seat DEC authorizes them.

### 4.9 Invariants (complete)

1. Stage order is total; `stage_order_violation` is fatal to the run (counter, then halt that item).
2. No paid call without `capability_broker` allow + `record_usage` row with `stage`.
3. No second queue; no per-chat budget; no shadow waterfall.
4. No ambient clock in predicates; envelope `observed_at` / `source_available_at` only.
5. No RNG except the recorded SHA256 rank of §4.5.
6. No internet search per article.
7. Model update never mutates old packets.
8. Correction: `novelty=corrected_fact` ⇒ `supersedes_fact_id` non-null (schema already requires this).
9. Unprocessed ≠ neutral.
10. Display-tier sentences use windows (“on the labeled 600, …”) and never claim a certainty.
11. PR #6514 unread as a write owner; `relationship_generation` stays 0 until that hold lifts.
12. `news_llm.annotate` is not a cascade stage.

---

## (5) WORKED CASES

Deterministic fixtures. Identifiers are synthetic but schema-shaped. No scores.

### W1 — ordinary item stops at dedup

```json
{
  "schema": "news_impact.routing_decision.v1",
  "case_id": "W1_stop_duplicate",
  "item_id": "a1b2c3d4e5f60718",
  "event_key": "ev_8c5a9639eac89",
  "company_id": "cik:0000320193",
  "utc_day": "2026-10-09",
  "stage_terminal": "deterministic_screen_dedup",
  "routing_disposition": "stop_duplicate",
  "escalation_reason": "none",
  "inference_state": "not_required",
  "cause": "cluster_representative",
  "representative_item_id": "00aa11bb22cc33dd",
  "new_numeral": false,
  "new_counterparty": false,
  "model_tier_class": "deterministic",
  "input_tokens": 0,
  "output_tokens": 0,
  "est_cost_usd": 0,
  "cache_hit": false,
  "notes": "Second outlet restates the same buyback authorization already extracted from the representative. Tape-visible; no cheap call."
}
```

### W2 — compact extraction only (correction / supersedes)

A later 8-K revises the remaining authorization down. Cheap extractor records `corrected_fact` with `supersedes_fact_id`. Not high-consequence-disputed (single extractor, numbers replay). Stops after validation + lookup + deterministic mechanism.

```json
{
  "schema": "news_impact.routing_decision.v1",
  "case_id": "W2_compact_correction",
  "item_id": "f00d1e2a3b4c5d6e",
  "company_id": "cik:0000320193",
  "utc_day": "2026-10-09",
  "stage_terminal": "deterministic_mechanism",
  "routing_disposition": "mechanism_complete",
  "escalation_reason": "none",
  "inference_state": "completed",
  "model_tier_class": "cheap",
  "input_tokens": 2180,
  "output_tokens": 240,
  "est_cost_usd": 0.000314,
  "cache_hit": false,
  "template": "capital_allocation_event.v1",
  "envelope": {
    "fact_id": "fact_aa11bb22cc33dd44ee55ff66",
    "document_id": "doc_8k_aapl_2026_10_09",
    "document_version": 2,
    "observed_at": "2026-10-09T14:02:00Z",
    "source_available_at": "2026-10-09T13:55:00Z",
    "novelty": "corrected_fact",
    "supersedes_fact_id": "fact_000011112222333344445555"
  },
  "channel_hint": "capital_allocation",
  "commitment_status": "authorized",
  "action_type": "share_repurchase"
}
```

### W3 — escalated for a disputed high-consequence fact

Two cheap passes disagree on the incremental authorization amount (50e9 vs 15e9) on an executed-scale buyback. Stronger adjudication consumes one slot. Frontier not used (`unresolved_decision` becomes `none` after stronger cites the 8-K table span).

```json
{
  "schema": "news_impact.routing_decision.v1",
  "case_id": "W3_disputed_high_consequence",
  "item_id": "ab12cd34ef56aa77",
  "company_id": "cik:0000320193",
  "utc_day": "2026-10-09",
  "stage_terminal": "stronger_adjudication",
  "routing_disposition": "adjudicate_complete",
  "escalation_reason": "disputed_high_consequence_fact",
  "inference_state": "completed",
  "model_tier_class": "stronger",
  "cheap_pass_a": {"incremental_authorization": "50000000000", "unit": "USD"},
  "cheap_pass_b": {"incremental_authorization": "15000000000", "unit": "USD"},
  "review_packet": {
    "schema": "news_impact.review_packet.v1",
    "new_evidence": "evidence_span on 8-K table_cell page=2 table=1 row=3 column=2",
    "old_thesis": "prior remaining_authorization 12e9 USD",
    "driver_exposure_facts": ["share_count_basic from last 10-Q span"],
    "alternative_mechanisms": ["capital_allocation"],
    "unresolved_decision": "critical_numeric_conflict"
  },
  "input_tokens": 4410,
  "output_tokens": 620,
  "est_cost_usd": 0.01502,
  "frontier_used": false
}
```

### W4 — budget-exhausted UTC day; deferred inference; inputs preserved

`usd_day` already 9.97 against proposed $10. Next material delta would cost ~0.00032 (Flash-Lite) or more. Admission step 4 fails. Item stays on qbus. Title and `news_event_class` remain visible.

```json
{
  "schema": "news_impact.budget_day.v1",
  "case_id": "W4_budget_exhausted_day",
  "utc_day": "2026-10-09",
  "ceiling_authority": "proposed_not_authorized",
  "day_usd_cap": 10.0,
  "month_usd_cap": 250.0,
  "usd_day": 9.9741,
  "usd_month": 41.22,
  "day_would_bind": true,
  "month_would_bind": false,
  "item": {
    "item_id": "bbccddee11223344",
    "title": "Issuer announces additional repurchase authorization",
    "news_event_class": "buyback",
    "qbus_retained": true,
    "tape_truncated": false,
    "stage_terminal": "deterministic_screen_dedup",
    "routing_disposition": "defer_budget",
    "escalation_reason": "none",
    "inference_state": "deferred",
    "model_tier_class": "cheap",
    "input_tokens": 0,
    "output_tokens": 0,
    "est_cost_usd": 0,
    "visible_factual_layer": {
      "title": "Issuer announces additional repurchase authorization",
      "source": "globenewswire inc.",
      "source_available_at": "2026-10-09T20:40:00Z",
      "company_id": "cik:0000320193",
      "news_event_class": "buyback"
    },
    "synthetic_neutral_written": false,
    "offer_again_utc_day": "2026-10-10"
  }
}
```

### W5 — abstention / absence (compact extraction records typed absence; no escalate)

Body available; template T2; the source states a contract award with no dollar figure. Extractor writes `field_absence.v1` reason `stated_without_number`. Deterministic mechanism is `mechanism_absence`. Not material-issuer-relative (no quantity). Not disputed.

```json
{
  "schema": "news_impact.routing_decision.v1",
  "case_id": "W5_absence_abstain",
  "item_id": "cc11dd22ee33ff44",
  "company_id": "cik:0000789019",
  "utc_day": "2026-10-08",
  "stage_terminal": "deterministic_mechanism",
  "routing_disposition": "mechanism_absence",
  "escalation_reason": "none",
  "inference_state": "completed",
  "model_tier_class": "cheap",
  "template": "demand_guidance_contract_event.v1",
  "stated_amount": {
    "schema": "field_absence.v1",
    "authority": "context_only",
    "reason": "stated_without_number",
    "subject": "stated_amount",
    "detail": "Award named; no currency amount in body.",
    "missing_fields": ["stated_amount"]
  },
  "channel_hint": "revenue_demand",
  "input_tokens": 1980,
  "output_tokens": 180,
  "est_cost_usd": 0.00027,
  "display_window": "On this source, the award is named and the amount is not stated."
}
```

---

## (6) FAILURE MODES AND TRIPWIRES

| failure | what it looks like | tripwire |
|---|---|---|
| Shadow router / second queue | adapter opens its own HTTP client or writes a parallel queue parquet | CI grep for `openai`, `anthropic.Anthropic(`, `httpx`, `requests.` under `engine/news_impact/`; test that every paid path calls `llm_auth.make_call`; qbus is the only item store asserted in tests |
| Per-chat multiplied budget | ceiling multiplied by conversation or ticker count | invariant test: `DAY_USD` is a single counter keyed by UTC date, not by `company_id` |
| Unprocessed mapped to neutral | deferred item gains `revision_direction` or empty impact | validator: `inference_state=deferred` ⇒ no new template critical field except absences already earned; fixture W4 |
| Tape truncated on exhaustion | qbus row missing after defer | test: W4 `qbus_retained=true`; `n_raw` accounting identity |
| Cheap router hides misses | rejects never audited | `n_audit_starved > 0` for more than 2 UTC days OR `reject_audit_miss_rate` not computed on a run that had `n_audit_rejects=0` while `n_low_value+n_not_material>0` |
| Score field smuggled | `confidence` / `llm_importance` in packet | freeze forbidden-grep; schema `additionalProperties: false` on cascade objects |
| Model update rewrites history | old `fact_id` bytes change | packets are content-addressed; test that a prompt_version bump appends a new fact_id and leaves the old row |
| Correction without supersedes | `novelty=corrected_fact` and `supersedes_fact_id=null` | already schema-invalid (D16); contract test |
| Universal per-article search | retrieval called inside compact_extraction | grep `gdelt` / search APIs from the adapter; allowlist is body re-fetch of the **same** URL already on the qbus row |
| Ceiling treated as authorized | runtime refuses a seat override | `ceiling_authority` field present and tested; logs `day_would_bind` while proposed |
| Token envelope overrun billed as success | 8k-in cheap call marked extract_complete | `input_tokens > envelope_in` ⇒ `n_envelope_exceeded` and disposition not `*_complete` |
| Audit uses unseeded RNG | `random.random` in adapter | grep `import random` / `secrets.` under news_impact; rank_key must be sha256 |
| Reduction hypothesis wired as a constant | `3000` or `20000` in runtime | those integers appear only in comments/docs; volume is counted |
| news_llm.annotate re-enabled as extractor | llm_importance written | freeze reuse matrix; test that cascade does not import `engine.news_llm.annotate` |
| Relationship generation invented while #6514 held | nonzero `relationship_generation` | invariant: 0 until HOLD lifts |
| Injection via news body | body contains “ignore previous instructions” | D17 text_safe not-patterns on free strings; record as injection finding, do not obey (MASTERPLAN.md §3.5) |

---

## (7) OPEN QUESTIONS FOR THE SEAT (each with default)

**Q1. Audit rate inside 10–15%?** Default **12%**. Midpoint; integer slots at cap 100 = 12 audit items/day.

**Q2. Audit seed?** Default **20261012**. Recorded integer; SHA256 rank. Do not reuse C1’s seed 7 for this draw (different population).

**Q3. `reject_audit_miss_rate` cap to scale beyond 600?** Default **0.05**. Stricter than “complete accounting” and looser than a zero-miss fantasy on n≈15–25 audit rejects.

**Q4. Minimum measured reduction ratio R to scale?** Default **4.0** (half of 20/3, matching the ANSWER FIRST “fails by half” fork). Below 4.0, stay on the labeled set and retune material-delta/dedup.

**Q5. While ceilings are `proposed_not_authorized`, does the adapter still defer?** Default **YES, log-and-defer as if $10/$250 bind**, because Haiku-class placement in this repo would otherwise spend $20.70/day at 6k extracts. The seat may flip to log-only by writing `ceiling_authority=proposed_not_authorized` + `enforce_proposed=false`; recommended is `enforce_proposed=true` for the 600-case run so burst/defer behavior (commission D) is actually observed.

**Q6. Stronger/frontier slot caps on the 600-case run?** Default **stronger_slot_cap = 24** (4% of 600, analogous to 100/3000), **frontier_slot_cap = 2**, **audit at 12% of 24 = 3** plus any leftover. Do not use the live 100/5 numbers on a 600-row labeled set (that would over-adjudicate and wreck the cost curve).

**Q7. Double cheap-pass for `disputed_high_consequence_fact` on every extract?** Default **NO**. Run the second pass only when the material-change predicate is already true (first row of the escalation table). Otherwise cost doubles at the cheap tier and the $10 day binds immediately.

**Q8. Lane names in capability_manifest.yml?** Default the four `news-impact-*` names in §4.1. Operator tap required (manifest is redline/fail-closed). Until the tap, paid stages fail closed (`defer_capacity` reason `lane_not_in_manifest`).

**Q9. Calendar for daily ceiling?** Default **UTC date of `lib.ai_costs` `ts`**. Matches the ledger.

**Q10. What is “review capacity” if stronger slots are unused?** Default still `stronger_slot_cap`, not realized stronger calls. Otherwise a cheap-router that escalates nothing would also audit nothing.

---

## (g) Recomputed §10 illustrative table

Published anchors (MASTERPLAN.md §10, checked Oct 6 2026 in that document): Flash-Lite $0.10/$0.40, Sonnet 5.5 $2/$10, Fable 5.1 $10/$50 per MTok in/out. 30 calendar days. No cache/batch discount.

| Stage | Decisions/day | in/out tok | per-decision USD | daily USD | monthly USD | stated monthly |
|---|---:|---|---:|---:|---:|---:|
| Compact fact extraction | 3,000 | 2,200 / 250 | 0.00032 | 0.96 | **28.80** | 28.80 |
| Stronger adjudication | 100 | 4,500 / 700 | 0.016 | 1.60 | **48.00** | 48.00 |
| Frontier thesis review | 5 | 12,000 / 1,500 | 0.195 | 0.975 | **29.25** | 29.25 |
| Total | | | | 3.535 | **106.05** | 106.05 |

All four stated monthly figures **reproduce exactly**. 100% overhead: 2 × 106.05 = **212.10** (reproduces). Triple workload × double rates: 3 × 2 × 106.05 = **636.30** (reproduces). Frontier-all on 20,000 raw × 2,200/250 at $10/$50: 600,000 × 0.0345 = **20,700** (reproduces).

**Arithmetic I cannot reproduce from this worktree (not a table error — a missing owner):** Gemini Flash-Lite $0.10/$0.40 is **not** a row in `config/ai_pricing.yml` (I14). The repo’s cheap-tier numbers are DeepSeek-flash $0.14/$0.28 and Haiku $1/$5. Using Haiku, compact 3,000/day = $10.35/day **already above the proposed $10 ceiling** even when the reduction hypothesis **holds**. This is why Q5 defaults to enforcing the proposed daily ceiling during measurement.

**Half-failed reduction (6,000 extracts/day), Flash-Lite anchors:** compact $1.92/day; all-stage $4.495/day; +100% overhead $8.99/day; monthly $134.85. Compact share of all-stage dollars = 1.92/4.495 = **42.7%** of the three paid stages (up from 0.96/3.535 = 27.2%). Compact is the **dominant delta**; stronger+frontier stay $2.575/day.

**Measured tape vs 20,000:** C1_tape Q2 median **461**/day, p90 **757**, 0 zero-days of 91. If every median-day item were extracted at Flash-Lite, compact would be $0.15/day. The 20,000 figure is ~43× current tape median. Program upgrade 6 is right to refuse a wider run until R is measured on the 600-linked window.

---

## Builder checklist (observable)

- [ ] `cascade.v1.json` and `cost_counters.v1.schema.json` parse as JSON
- [ ] adapter lives under `engine/news_impact/` and does not import `engine.news_llm.annotate`
- [ ] every paid call: `capability_broker.resolve` → `llm_auth.make_call` → `lib.ai_costs.record_usage(stage=…)`
- [ ] qbus keep-FIRST remains the item queue
- [ ] W1–W5 replay as fixtures of the routing contract
- [ ] forbidden-field grep empty
- [ ] 600-case counters written; scale gates in §4.8 evaluated before any live expansion
