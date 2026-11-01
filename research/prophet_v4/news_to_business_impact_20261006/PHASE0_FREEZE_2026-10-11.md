# Phase 0 freeze — news-to-business-impact event templates (2026-10-11)

Status: DRAFT until the seat adjudicates the ORCH-W1 synthesis. Masterplan reference:
`package/MASTERPLAN.md` §3 (atomic fact packet), §4 (channels), §11 (research and
evaluation plan), §12 (phases and commissions), §13 (scope limit), §14 (holds).
Workstream `WS:PROPHET-NEWS-IMPACT`; program state in
`research/PROPHET_NEWS_IMPACT_CONTINUATION_HANDOFF_2026-10-11.md`.

## 0. Acceptance gates (what "frozen" means)

Not frozen unless every item holds:

1. Three templates — `capital_allocation_event.v1`,
   `demand_guidance_contract_event.v1`, `strategic_product_partnership_event.v1` — each
   with ≤12 critical fields, each critical numeric field bound to a `source_span.v1`
   reference, and a typed-absence alternative for every optional critical field.
2. Shared `$defs` (`quantity`, `source_span_ref`, `typed_absence`, `baseline`,
   — amended 2026-10-12: implemented as `source_span_v1` inside `evidence_span` and
   `field_absence.v1` / `owner_typed_absence_v1` (`absence_union`), renames D13/D14 in §3 —
   `novelty`, `issuer_role`, `commitment_status`, `fiscal_period`) defined once and
   referenced by all three templates.
3. `additionalProperties: false` on every object; `maxLength` on every string; no
   field named or meaning confidence, probability, score, target, fair value or
   rating (DNR:KILL-LLM-CONFIDENCE, DNR:KILL-CAUSAL-DAG-ALPHA).
4. Acceptance labels for commission D graders: one label set per template, each label
   decidable from the source text alone, with the critical-field correctness and
   material-event routing definitions the §11 thresholds are measured against.
5. ≥2 worked cases per template, including one misleading near-duplicate that the
   validator must reject, with the pasted validator outcome.
6. An adversarial review (amended 2026-10-12: fabric review lane `R_D1r_remote_r1`,
   glm-5.3, read-only, in place of the native opus `reviewer`) concluded against the
   frozen schemas with every ACCEPT-blocking finding resolved by name.

Outcome (seat, 2026-10-12): all six gates hold — evidence in §2 and §3; the two amended
gate wordings are renames, not relaxations.

## 1. Phase 0 exit evidence (masterplan §12, row 0)

| §12 exit item | where it lands | state |
|---|---|---|
| One reuse matrix | §9 below (from the C3_owners census, seat-corrected) | DONE (V_C3_remote_r1 PASS; §9) |
| #6514 hold/disposition understood | §1.1 | DONE (seat) |
| Benchmark sampling plan | §6 | DRAFT (seat design; counts filled from C1_tape, 2026-10-11 — §6, §8) |
| No rival schema/store | §1.2 | DONE (seat) |
| Four remaining research questions frozen | §1.3 | DONE (seat) |

### 1.1 #6514 disposition

PR #6514 (K3-D) is HOLD-FOR-SOL. It is not repaired, rebased, merged, armed or
commented on by this workstream. Commission C reads its diff and records as inputs only
and returns ten supported/refused transfer examples plus a predictive-consumer boundary;
any change #6514 needs follows its own acceptance path under its holding authority.

### 1.2 No rival schema or store

The only schema home for this program is `contracts/news_impact/`; the only code home is
`engine/news_impact/`. Both consume the existing owners and mint no parallel event
ledger, document store, span verifier, identity resolver or economic-observation store:
`engine/news_events.py` (`classify_event`), `engine/news_event_ledger.py`,
`engine/company_intelligence/{events,documents,resolution,economic_observations,
contracts}.py`, `data/qbus/items.parquet`. The three templates are typed payloads that
attach to the existing `company_event.v1` / `event_fact.v1` lineage (the exact attachment
point is seat fork F1 in §4); they never replace it.

### 1.3 The four research questions, frozen

- **A. Economic channels and expectations.** Which ≤12 critical fields per template,
  which baseline hierarchy, which share-count/cash mechanics, which strategic
  double-count safeguards and which typed absence states make an event packet
  gradable from source text alone? Returns: three templates, acceptance labels, worked
  positive/negative cases, unit-test vectors. (Phase 0, this document.)
- **B. Strategic evidence and novelty.** What materially changes a thesis without
  immediate EPS impact? Returns: an annotation guide for 50 varied strategic cases,
  source-independence rules, falsifiers, weak-keyword nonnumeric counterexamples;
  reuses existing data-intelligence studies rather than rerunning them.
- **C. Cross-issuer transmission.** How do K3-D/K3E reconcile with GMI and Group Reads,
  separating economic exposure from semantic membership and residual co-movement?
  Returns: ten supported/refused transfer examples and a predictive-consumer boundary.
- **D. Cost-quality frontier and false negatives.** On the 600-case benchmark, what are
  the error taxonomy, recall-versus-cost curves, actual token/search costs,
  calibration and burst/defer behaviour of approved inexpensive models with a small
  stronger-model audit? Local executable evaluation only.

## 2. Judge panel verdicts (seat ruling 2026-10-12)

| Artifact | Lane | Rung | Candidate verdict | Basis |
|---|---|---|---|---|
| D1 fact-integrity design | grok local (sentinel lost) | DELIVERED, accepted by artifact (W1 record) | ACCEPT, superseded as base by D1r | schema check OK, 6/6 worked cases, forbidden grep empty |
| D1r repair (D1 + R1-R6 grafts) | ubuntu2 glm-5.3 C2 | DELIVERED | PASS-equivalent -> FREEZE BASE | suite 19/19 expected-matched, proofs P1-P5 OK, 20/20 objects closed, field tables 27/27/27/29 |
| D2 labeler-first design | ubuntu2 glm-5.3 C2 | DELIVERED | PASS (diversity lane; adjudication form F graduates into gate 4) | V_D2D3_remote_r1: PASS 57f3041e22 (D2 object_nodes=76, closed=15) |
| D3 consumer-first design | ubuntu2 glm-5.3 C2 | DELIVERED | PASS (diversity lane; worked-case ids reused as benchmark seeds) | V_D2D3_remote_r1: PASS 57f3041e22 (D3 object_nodes=47, closed=31) |
| C3 owner census | ubuntu2 glm-5.3-flash | DELIVERED | PARTIAL -> section 9 matrix (seat-corrected) | V_C3_remote_r1: PASS 57f3041e22; four citations drifted by line number only; propagation contract absent (#6514) |
| R_D1r adversarial review | ubuntu2 glm-5.3 C2 review | DELIVERED | PASS; grafts accepted (R copy 3b7346f6) | sentinel R_D1r_remote_r1: PASS 57f3041e22; 8/8 owner payloads accept; 4 conflict probes -> seat rulings R1-R4 (DEC:NEWS-IMPACT-PHASE0-FREEZE); attack battery 443 rows: base admits 356, R copy admits 0; benign 154 rows: 0 false rejects; replaces the native opus reviewer named in gate 6 |
| B1 contract build (schema + 5 case files + contract test + CI entry) | ubuntu2 glm-5.3 C2 build (ORCH-W1d) | DELIVERED; integrated into the freeze worktree by the seat | PASS | schema sha256 prefix 3edc7139; 46/46 in the freeze worktree; adversarial 0/443 admitted; benign 0/154 rejected; owner integer-table case ACCEPT; semantic diff vs D1r = T2 allOf 3 -> 8 (F3) + table index integer-or-string (G-OC1) |
Ruling (seat, 2026-10-12): D1r + the accepted R_D1r grafts (R copy 3b7346f6) + G-OC1 + F3 is the frozen base, byte-frozen as `contracts/news_impact/news_impact_event.v1.schema.json` (sha256 prefix 3edc7139) and guarded by `tests/test_news_impact_contracts.py`; D2 section F is the gate-4 label set; D3 cases join the worked-case set. D1 ACCEPT stands as lineage only.

## 3. Frozen templates

Base: D1r + accepted grafts, frozen as `contracts/news_impact/news_impact_event.v1.schema.json` (sha256 prefix 3edc7139; cases under `contracts/news_impact/cases/`; guard `tests/test_news_impact_contracts.py`, 46 cases). Critical fields marked *, counted per gate 1 (<= 12 each; envelope fields are machine-set and not counted).
Shared envelope on every template: schema (const), authority (const context_only), prophet_flags (all const false), unsolicited_instruction_detected, fact_id, document_id, observed_at, source_available_at, supersedes_fact_id (novelty corrected_fact => non-null).
### T1 capital_allocation_event.v1 — 27 props / 21 required / closed
Critical (12): company_id*, issuer_role*, novelty*, action_type* (share_repurchase | dividend | special_dividend | equity_issuance | debt_issuance | other_allocation), commitment_status*, primary_amount_role*, incremental_amount* (basis const incremental), remaining_authorization* (basis const total), executed_amount* (basis const total; present when executed/completed), horizon_period*, negated*, action_span*.
Optional: baseline, channel_hint, cluster_grain, conditions_quote, consideration_quote, news_event_class.
Coherence (allOf): slot basis consts; executed/completed => executed_amount present; corrected_fact => supersedes_fact_id non-null.
### T2 demand_guidance_contract_event.v1 — 27 / 21 / closed
Critical (12): company_id*, issuer_role* (supplier/customer => counterparty is a real id, never an absence), demand_stage*, metric*, commitment_status* (executed/completed => stated_amount present), stated_amount* (F3: basis const keyed by metric via allOf if/then: revenue, backlog, units -> total; eps -> per_share; bookings -> incremental; metric=other unconstrained), fiscal_period*, revision_direction*, negated*, novelty*, counterparty_company_id* (id | array 1-8 | absence), baseline* (REQUIRED on T2 only).
Optional: channel_hint, cluster_grain, conditions_quote, news_event_class, option_ceiling (V_NO_SUM_T2), prior_amount.
### T3 strategic_product_partnership_event.v1 — 29 / 21 / closed
Critical (12): company_id*, issuer_role* (supplier => action_span span-backed), event_kind*, object_name*, commitment_status* (executed/completed => stated_quantity present), novelty*, counterparty_company_id*, counterparty_role* (supplier => span-backed), stated_quantity*, economic_claim_class*, negated*, action_span*.
Optional: adoption_proxy_quote (V_NO_ATTENTION_AS_DEMAND), baseline, channel_hint, cluster_grain, contrary_mechanism_quote, horizon_period, license_quote, news_event_class.
Every critical numeric is a quantity (oneOf quantity_point / quantity_range / quantity_absent); point and range carry an evidence_span (source_span_v1) and absent carries absence_union — gate 1 satisfied by construction.
### Shared $defs (defined once, referenced by all three) — 32 in D1r
Gate-2 names reconciled: source_span_ref -> source_span_v1 (owner 12-key payload) wrapped by evidence_span; typed_absence -> field_absence.v1 (closed reason enum 5 + optional owner_reason enum 16) and owner_typed_absence_v1, unioned as absence_union; quantity (oneOf quantity_point / quantity_range / quantity_absent); baseline (type enum 6; each field or absence); novelty (5); issuer_role (6); commitment_status (7); fiscal_period (year, quarter | null, period_kind enum 5, calendar_end, optional end_year).
Also shared: envelope, evidence, evidence_absence, receipt (7 keys), three locators (text_span, table_cell, slide_region), company_id (cik: + ten numerals, zero floor), prophet_flags, quantity_basis, news_event_class (24), channel_hint (7), cluster_grain (3), text_safe (string with injection not-patterns), quarantine_note.v1 (OUTSIDE the templates).
### Named validators after schema acceptance
V_RANGE, V_SPAN_REPLAY (documents.verify_span), V_SHA_TIE (+ numeral-in-quote), V_NO_SUM_T1, V_NO_SUM_T2, V_DIRECTION, V_PERIOD_BASIS_MATCH, self-counterparty, V_NEGATION, V_COMMITMENT, V_BASIS, V_STAGE / V_METRIC_STAGE, V_TRANSFER, V_NO_ATTENTION_AS_DEMAND, V_NO_OPTION_MOAT_DOUBLE, unit/currency agreement, top-level vs slot negation.
### Suite evidence (gate 5; pasted from D1r_suite_output.txt; ubuntu2 clone HEAD 57f3041e22)
check_schema: OK (jsonschema 4.10.3, draft 2020-12). 19 cases: A1-A7 REJECT (first error paths $.action_span.span.document_id, $.remaining_authorization.evidence.span.receipt, $.incremental_amount.evidence, $.incremental_amount.basis, $.executed_amount.form, $.company_id, $.action_span); R1-R6 ACCEPT; W1-W6 ACCEPT. SUITE: 19/19 EXPECTED-MATCHED.
Proofs: P1 corrected_fact_without_supersedes -> REJECT at $.supersedes_fact_id; P2 unknown_field_confidence -> REJECT at $; P3 absence_reason_outside_closed_vocab -> REJECT; P4 envelope contract on all W/R cases OK; P5 owner re-mint equality OK (receipt_state byte_replayed). SUITE-PROOFS: ALL OK; suite_exit_code=0.
Forbidden grep (confidence | price_target | score | contagion | probability) exit 1 (empty). additionalProperties walk object_nodes=20 additionalProperties_false=20 open=0. Field-table coverage T1 27/27, T2 27/27, T3 29/29.
Near-duplicate cases in the worked set: D2 T1-W2 (execution under the same program), D2 T2-W2 (same number affirmed, not raised), D3 T1-B_execution_near_dup, D3 T2-B_negated_withdrawal, D3 T3-B_supplier_commentary; the A-series rows are the schema-level rejections.

Final-contract evidence (B1, freeze worktree): `python -m pytest tests/test_news_impact_contracts.py -q` -> 46 passed; attack battery 443 rows, 0 admitted; benign 154 rows, 0 rejected; owner payload conformance 5/5 (documents.py / events.py minted spans, absences, fiscal periods, integer table index).

### Changes vs D1 (recorded)
- D13 `source_span_ref` -> `source_span_v1` (owner 12-key payload) wrapped by `evidence_span`.
- D14 `typed_absence` -> `field_absence.v1` (reason enum 5 + optional owner_reason enum 16) and `owner_typed_absence_v1`, unioned as `absence_union`.
- G-OC1 locator `table` index: integer >= 0 or text-safe string (owner shape `tests/test_company_intelligence_spine.py:414`).
- F3 metric-keyed basis const on T2 `stated_amount` (above); closes D1r-A4 (W4 bookings basis=total now REJECT).
- G5 injection not-patterns on every free string; `quarantine_reason` outside the templates.
- R1-R4 (DEC:NEWS-IMPACT-PHASE0-FREEZE) are projector rules: no schema change; the Phase 1 projector nulls `display_excerpt` on URL or > 500 chars and rejects unknown locator keys as `locator_key_not_in_contract`.

### Gate reconciliation (seat ruling 2026-10-12)Gate 2 names: the committed gate text names source_span_ref and typed_absence; D1r implements them as source_span_v1 (inside evidence_span) and field_absence.v1 / owner_typed_absence_v1 (absence_union). Ruling: gate 2 is read with the D1r names (renames D13/D14 above); the frozen $defs set is the 32 named in this section.
Gate 6 wording: "native opus reviewer" -> "adversarial review (fabric review lane R_D1r_remote_r1, glm-5.3, read-only, commissioned by the Opus orchestrator ORCH-W1c)"; every ACCEPT-blocking finding resolved by name: G-OC1 grafted, F3 grafted, G5 grafted, R1-R4 ruled as projector rules.
Gate 5 near-duplicate: ruled. The worked cases and pasted outcomes hold (>= 2 per template, 19/19 suite, 443/0 attacks, 154/0 benign). The misleading near-duplicates (D2 T1-W2, T2-W2; D3 T1-B_execution_near_dup, T2-B_negated_withdrawal, T3-B_supplier_commentary) are ACCEPT at the schema by design; the rejecting rule is named — V_SHA_TIE numeral-in-quote for a new_magnitude claim whose quote carries no new numeral, and the ledger novelty rule for a same-number re-statement — and both live in the Phase 1 validator `engine/news_impact/validate.py`, not in the schema. The executable rejection is carried to Phase 1 and listed in section 10.

### Gate 4 — acceptance labels for commission D graders (one set per template; D2 section F form + D1 (e) sections + freeze section 7 grading)
Per critical field (12 rows): correct | wrong_value | wrong_absence | unevidenced (D2 form) — collapsing to correct | incorrect | absence_correct for the section-11 numeric-correctness count (correct = value, unit, basis, period and negation all equal after normalisation; absence_correct = typed absence where the source states nothing).
Case-level (one each): routing_label in material / immaterial / defer / reject (material = would change an issuer thesis, baseline or open commitment; immaterial = routine / repeat / no economic content; defer = source, rights or parse insufficient; reject = not an event for this issuer); issuer_role (6); novelty (5); unsupported_transfer yes / no (a supplier, customer or counterparty relationship asserted without a cited span naming both parties — the section-11 zero endpoint).
Template specifics: T1 — incremental, total and executed amount slots marked separately; T2 — a guidance range is correct only if both bounds match, and a TAM row routed material as earnings demand is a routing miss; T3 — a first product announce may be material for research with unquantified earnings; a supplier role without a supply span is unsupported_transfer yes even when otherwise well typed.
Decidable from the source text alone: yes for every row (no external lookups; baseline rows arrive pre-assembled in the context header). Budget 5:00 per case hard; a case needing more is a defect report against the template, not a slower labeler.
Section-11 measurement: critical numeric correctness = share of present critical numerics marked correct (target >= 98%); routing recall = labeled material events reaching the correct template (>= 95%); unsupported transfer assertions = count of unsupported_transfer yes (target zero).
No confidence, score, expected move or consensus-database check is asked for (DNR:KILL-LLM-CONFIDENCE).

## 4. Seat forks

Pre-registered before the synthesis arrives, so the artifacts are judged against named
questions rather than by salience:

- **F1 attachment point.** New top-level object kinds versus typed `details` payloads of
  the existing `company_event.v1` keyed by event kind. Cheapest falsifier: C2's executed
  probe of `company_event.v1` extensibility (does the existing contract reject unknown
  payload keys, and does `canonical_event_id` survive a typed payload?). Default if
  unanswered: typed payload, no new top-level kind.
- **F2 span receipts for non-filing sources.** Whether `SourceDocument` / `verify_span`
  admit a news URL with `source_sha256` as-is, or the LEAF needs a thin adapter that
  yields `address_only` receipts until byte replay is available. Falsifier: C2's probe
  with a real news URL from the tape. Default: `address_only` receipt admitted, byte
  replay preferred, never a fabricated `byte_replayed`.
- **F3 quantity basis.** Whether {total, incremental, run_rate, per_share, percent} is
  complete for all three templates or needs `annualized` / `cumulative_to_date`.
  Falsifier: the worked cases; any case that cannot be expressed without free text
  widens the enum once. Default: the five values.
- **F4 baseline source when no consensus exists.** Order of the type-tagged baseline
  hierarchy when sell-side consensus is unavailable under current rights: prior
  company guidance → prior reported period → prior announced programme → typed
  absence `not_stated`. Default: that order, never an inferred number.
- **F5 negation and conditionality.** One `negation` boolean plus a bounded
  `condition` string versus a `commitment_status` enum {announced, authorized,
  conditional, completed, withdrawn, rumoured}. Default: both — status carries the
  category, the bounded string carries the condition text with its span.

### 4.1 Resolutions recorded before the synthesis (seat, 2026-10-11)

Recorded from the seat ledger (D6–D12) so the synthesis in §5 starts from closed forks. Each resolution names the existing-owner fact that closed it. No owner file is edited in Phase 0.

- **F1 — RESOLVED (D6).** The leaf contract is `news_impact.<template>.v1`, keyed by CIK `company_id` (`cik:` + 10 digits, the E0 identity key) plus `source_document_id` plus the span ids it cites. It links to `company_event.v1` only when the extracted event type is in that contract's closed `EVENT_TYPES`; otherwise `ci_event_id` is a typed absence. Why: `company_event.v1` has no `news` type, and `canonical_event_id(None, …)` mints `evt_cik0000000000_<period>_<type>` for a missing CIK, so a news leaf that forced a link would either invent an event type or collide on the CIK-floor id.
- **F2 — RESOLVED (D7, D8).** Evidence spans are `byte_replayed` through `documents.text_span()`; the `sub_kind: transcript_segment` stamp it applies is accepted as-is. `address_only_span()` stays limited to `table_cell` / `slide_region`, exactly as the owner defines it. Because a non-filing `source_document.v1` has no `url` field and refuses `document_kind='news'` / `source_class='news'`, the Phase 1 adapter is a leaf `news_impact.source_locator.v1` — `{url (https only, is_safe_source_url), capture_time, source_sha256, qbus item_id}` — wrapping, never modifying, a `source_document.v1`. `documents.py` is not edited.
- **F3 — RESOLVED (D13, review attack 4 = A4).** `quantity_basis` is not a free per-slot choice. Each quantity slot carries a `basis` CONST fixed by the template (`incremental_amount` → `incremental`, `remaining_authorization` → `total`, per-share slots → `per_share`, percentage slots → `percent`); `run_rate` is admitted only on slots the template names. A4 (basis `total` on an incremental slot, `percent` unit with `NA` currency, inverted range) must be REJECTED by the schema, not by prose. Range ordering (`low` ≤ `high`) stays a NAMED validator because JSON Schema cannot compare two fields; it is listed in §3 as a validator, never as a schema promise.
- **F4 — RESOLVED (D9).** The baseline for any delta follows a fixed ladder: `prior_guidance` → `prior_reported_period` → `prior_announced_programme` → typed absence `not_stated`. Consensus is never written as a number by this program.
- **F5 — RESOLVED (D14, review attack 5 = A5).** Conditionality is a closed `commitment_status` enum, not a bounded free string. Coherence is enforced in schema by `if/then`: `commitment_status ∈ {executed, completed}` requires `executed_amount.form ≠ absent`; `primary_amount_role = X` requires the matching slot's `form ≠ absent`; a present quantity forbids the absence branch of its evidence. One negation flag per fact (slot-level `negated` is dropped — two flags that can disagree are a defect, A5). A condition's text, where one exists, is a bounded quoted span on the evidence wrapper (`claimed_quote`), never a second free field.
- **D10.** Issuer role is a closed enum: `{subject, counterparty, competitor, supplier, customer, incidental, unknown}`.
- **D11.** Novelty is read from the qbus tape's `novelty_z` and echo context only; the program mints no second novelty score.
- **D12.** Issuer resolution ladder: `data/symbol_directory/cik_map/<date>.parquet` snapshot at or before the capture date → `data/edgar/ticker_cik_ledger.json` (flagged `ledger_fallback`) → typed absence. `data/edgar/dead_name_cik.json` feeds the benchmark's failure quota. Resolver version and snapshot date ride as provenance on every row.
- **D13.** Evidence shape (review F1/F3, graft G1): every numeric critical field binds `evidence = oneOf(owner source_span.v1 payload EXACTLY as documents.py SourceSpan emits it — receipt_state ∈ {byte_replayed, address_only}, byte locator keys, receipt required when byte_replayed — | field_absence.v1)`. `typed_absence` is NOT a receipt state; the frozen assumption that said so was wrong and is withdrawn. The evidence wrapper keeps an extractor-side `claimed_quote` (1–500 chars). The owner's own serialized SourceSpan must validate unchanged (R3 of the counterexample suite).
- **D14.** Absence (graft G2): the program's absence is `field_absence.v1` with reasons `{not_stated, stated_without_number, range_only, redacted_rights, parse_failed}` plus optional `owner_reason ∈ documents.py ABSENCE_REASONS`. It is never named `typed_absence.v1`, which is the owner's absence schema with a disjoint reason set (review F2).
- **D15.** Period (graft G3): the owner `FiscalPeriod.to_payload()` keys `{year, quarter 1–4|null, calendar_end ISO date|null}` are adopted verbatim, plus `period_kind ∈ {quarter, half_year, nine_months, fiscal_year, multi_year}` with optional `end_year`. No second period type.
- **D16.** Envelope (graft G4, review F5): every fact carries `fact_id` (`fact_` + 24 hex), `document_id`, `observed_at`, `source_available_at` (date-time) and `supersedes_fact_id` (null or `fact_` pattern), with `novelty = corrected_fact ⇒ supersedes_fact_id` required non-null. This is what makes the §11 "successful correction replay" gradeable.
- **D17.** Injection containment (graft G5, §3.5): every free string carries a not-pattern for `ignore previous|prior`, `system prompt` and `http://`-style URLs; `quarantine_reason` lives OUTSIDE the publishable templates so a quarantined item can never be published by accident. A1 (instruction smuggled through bounded fields) must be rejected by the schema.

## 5. Parsimony demotions (fields proposed and dropped, with the reason)

Retained optional (display-tier, never critical): news_event_class (24-enum routing prior from news_events.classify_event), channel_hint (7), cluster_grain (3), the per-template quote strings (conditions / consideration / adoption_proxy / contrary_mechanism / license), T1 and T3 baseline (critical only on T2 per D1 open fork 4).
Demoted from D1 (recorded in D1r changes-vs-D1): span_typed_absence, source_span_ref, char-offset locators, quoted_text, the fiscal_period quarter/year fork, the typed_absence name collision.
Kept out of the extractor by law: routing_label and the other case-level marks are adjudicator-only (D1 open fork 8); quarantine_note.v1 lives outside the templates; no confidence, probability, score, target or rating field anywhere (forbidden grep empty).
Open forks carried into Phase 1 (falsifier on the 200-label sets): three T1 amount slots vs one amount + role (fork 1); horizon_period on T1 amounts left absent (fork 9).

## 6. Benchmark sampling plan (seat design; counts filled from C1_tape)

- **Population.** Items on the current qbus tape (`data/qbus/items.parquet`) that pass
  the existing eligibility filter (`engine/news_common.is_low_value` false) and resolve
  to an issuer with a `cik:` identity through `engine/company_intelligence/resolution`.
  Items that fail resolution are counted, never silently dropped (masterplan §11:
  coverage counts distinguish discovered, unique, extracted, impacted, deferred,
  evaluated).
- **Strata.** 200 capital-allocation, 200 demand/guidance/contract, 200 strategic
  product/partnership, each split across positive / negative / ambiguous / no-change
  and carrying a quota of deliberately misleading near-duplicates and indirect-transfer
  targets. Minimum per cell is set from C1's measured counts; a cell the tape cannot
  fill is reported short, never padded from synthetic text.
- **Counts (from C1_tape, 2026-10-11; §8).** Draw population = the trailing 90 days of publisher `seendate` on the qbus tape, frozen by tape sha and date bounds in the sampling manifest. Candidate pools per template (tagged rows / distinct issuers / pool-to-target ratio for 200): T1 964 / 870 / 4.8×; T2 793 / 826 / 4.0×; T3 549 / 443 / 2.7×. Per template of 200: 90 positive / 50 negative / 30 ambiguous / 30 no-change. Tagged within those cells: ≥20 misleading near-duplicates (drawn from the 1,905 size-2–5 `event_key` clusters plus cross-outlet duplicates found at labeling) and ≥10 indirect-transfer targets. Caps: ≤6 clusters per issuer per template (so ≥100 issuers per template); the seven megacaps (NVDA, MSFT, AAPL, GOOGL, TSLA, AMZN, META) ≤10% of each template's draw against 26% raw; no economic cluster >25%. Positives are supplemented from the 177-row `event_log` feeder (buyback 15, dividend_change 15, equity_offering 34, guidance_raise+guidance_cut 84, contract_award+customer_win 6, product_launch 23); negatives from the 1,764-row `reject_sample`. A cell that comes up short is reported short in the manifest, never back-filled.
- **Issuer mix.** The 100 deep issuers span several economically distinct clusters and
  include less-followed names and failures; megacaps are capped so no cluster exceeds
  a fixed share of cases.
- **Grouping and holdout.** Every duplicate article and every related issuer of one
  source event share one group id; groups are assigned to chronological folds with an
  untouched prospective cohort. No case is selected after reading its outcome.
- **Provenance.** Every case records `source_sha256`, capture time, qbus item id, group
  id, fold, the sampler version and the sampling seed so the draw replays exactly.
- **Rights.** Only sources already lawful under the existing rights registry; the
  sampler reads the registry and refuses an unregistered source rather than skipping
  silently.

## 7. Labeling protocol (seat design)

- Two independent labelers from different model families draft each case's critical
  fields with spans; the validator checks every span by replay before a label is
  stored. Agreement on every critical field accepts the case; disagreement routes to a
  third labeler of a third family; residual disagreement is adjudicated by a human or
  the seat and recorded with its reason.
- The label is what the source says at the cited span, never whether it is true, and
  never any model's confidence. Labeler identity, model vintage and prompt version are
  stored on every case.
- Grading definitions for §11 thresholds: critical-numeric correctness = value, unit,
  basis, period and negation all equal after normalisation; material-event routing
  recall = labeled material events reaching the correct template; unsupported
  ticker-to-supplier assertion = any transfer edge without a cited span naming both
  parties.

## 8. Tape fit (what the benchmark population looks like on the current qbus tape)

Source: seat census C1_tape (run under the continuation law at head `cf4ca641fb9d`, script `c1_tape.py`, seeds 7 and 11; sentinel `C1_tape: PASS cf4ca641fb9d`). Numbers are from the tape as read on 2026-10-11 and will move with the tape; the sampling manifest freezes its own.

**Answer first.** The tape carries enough tagged, issuer-resolved headlines to fill all three 200-row templates from a 90-day window at 2.7–4.8× oversampling, but it carries headlines only: no bodies, no labels, and a duplicate structure that is mostly singletons. The benchmark therefore samples candidates from the tape, re-fetches bodies through the allowlisted owner, and labels by hand. The tape is a recall net, never ground truth.

| Fact | Value |
|---|---|
| Rows / date range | 53,658 rows, 2026-05-05 → 2026-10-11; `_crawled_at` populated from 2026-09-12 (352 distinct values) |
| Daily volume | median 461 / p10 218 / p90 757 rows per day; 0 zero-days of 91 |
| Bodies | none on the tape (`body_sha256` only); `classify_event(title, body="")` returns null for 95.0% (n=10,000, seed 11) |
| Issuer tags | `entities` present on 52.6% of rows |
| Low-value filter | `is_low_value` fires on 0.3% (n=20,000, seed 7) |
| Duplicate structure | 50,896 `event_key` values; 91% singletons; 94.9% of rows are first-in-cluster |
| Template families (rows / tagged / issuers / 90-day clusters) | T1 1,348 / 964 / 870 / 156 · T2 1,297 / 793 / 826 / 46 · T3 744 / 549 / 443 / 20 · ANY 3,263 / 2,210 / 1,603 / 227 |
| Family overlaps | T1∩T2 84 · T1∩T3 17 · T2∩T3 26 · all three 1 |
| Rates | 30.8 family matches/day; 21.5 tagged/day; 1,476 distinct issuers |
| Megacap share | 848 of 3,263 family matches (26%) are NVDA/MSFT/AAPL/GOOGL/TSLA/AMZN/META |
| Labeled seed | none. `event_log` has 1,335 rows / 592 tickers of machine labels only; 177 rows match the feeder types |
| Reject sample | 1,764 rows: stock_pick_roundup 804, single_stock_advertorial 429, calendar_preview 345, personal_finance_advice 74, morning_aggregator 57 |

**Consequences for the plan.**

- The family regexes are a RECALL net. Precision is settled by labeling, so the sampler draws from the families and never treats a family match as a positive.
- A per-issuer cap of ≤6 clusters per template keeps the 26% megacap mass under the 10% ceiling without exhausting the pool (≥100 issuers per template remain).
- Bodies are re-fetched through the allowlisted retrieval owner (masterplan §3.5). A row whose body cannot be fetched is `deferred: body_unavailable`, counted in the accounting, never silently dropped.
- Cross-outlet clustering is Phase 1 work. The holdout group id is `(resolved issuer, template, event date ± 2 d)`, never `event_key`, because `event_key` is 91% singletons and would leak mirrors across folds.
- Known gaps: `_crawled_at` is blank before 2026-09-12, so publisher `seendate` is the sampling clock; there is no labeled seed, so the first 600 labels are all hand adjudication; indirect-transfer targets are found at labeling, not by regex.

## 9. Reuse matrix

Verdict: V_C3_remote_r1: PASS 57f3041e22 — matrix rows verified against the owners; four citations drifted by line number only between 57f3041e22 and HEAD 81f1d5f0 and point at the same statements (section 10).

| Owner | Consumable as-is | LEAF adapter | Forbidden |
|---|---|---|---|
| engine/news_common | YES (is_low_value) | - | may not become a scored input |
| engine/news_events | YES (classify_event -> news_event_class) | - | nothing in the scoring path imports it; fail-open |
| engine/news_event_ledger | YES read | - | LEAF never appends to event_log |
| engine/qbus (data/qbus/items.parquet) | YES read, PIT keep-FIRST | - | append_items |
| engine/qledger | YES read | - | register() / grade writes; D4 claim law |
| engine/news_llm | annotate() when enabled | - | DNR:KILL-LLM-ORIGINATION; default OFF |
| engine/intel_hub, alert_triage, master_brain | Partial (typed read-only artifact readers) | optional | build() composite authority; DNR:KILL-ONE-TICK-ESCALATION; import-for-data |
| engine/company_intelligence | YES (documents, events, resolution, economic_observations, contracts) | reuse the intelligence_workspace adapter | - |
| k3e, engine/contracts* | TYPED ABSENCE | LEAF mirrors the shape: engine/news_impact/contracts.py + contracts/news_impact/ | no store, score or LLM origination |
| economic_propagation (K3-D PR #6514) | NO / BLOCKED | - | until #6514 lands and Sol accepts; Commission C reads its diff as inputs only |
| data/revisions (collectors/equity_revisions.py) | TYPED ABSENCE on host | K=1 MANDATORY read-only expectation-baseline adapter | - |
| neuralweb importers | n/a | - | News -> NW only via the governed channel |

## 10. Not verified in Phase 0

- data/ absent on ubuntu2 and in the sparse worktree: no real benchmark draw; the sampler is unit-tested on synthetic rows only; the seat runs any real draw locally against the C1 tape path.
- Article bodies are not on the qbus tape (section 8): span replay against bodies waits for the Phase 1 document fetch through the existing owner.
- No labeled seed set exists; the section-11 thresholds are unmeasured until commission D.
- Propagation contract absent (economic_propagation blocked on #6514).
- text_safe injection not-pattern is a syntactic guard only: the R_D1r grafts close the 443-row attack battery (0 admitted), but a semantic quarantine rule is projector-side Phase 1 work.
- ubuntu2 host porcelain non-empty is pre-existing host state (empty working tree), not a lane mutation.
- Four C3 citations marked DRIFT (line numbers moved between 57f3041e22 and HEAD 81f1d5f0) were not re-verified against HEAD; their statements were unchanged at 57f3041e22.
- The named validators (V_RANGE through V_NO_OPTION_MOAT_DOUBLE) and the R1-R4 projection rules are specified, not executed: `engine/news_impact/validate.py` is Phase 1 wave w1.
- RS11 (low <= high on bounded quantities) is a runtime check, not a schema constraint; unverified for any producer.
- The gate-5 near-duplicate rejection is named (V_SHA_TIE numeral-in-quote; ledger novelty rule) but not executable until the Phase 1 validator exists.
