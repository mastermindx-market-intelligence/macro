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
6. An adversarial review (native opus `reviewer`, read-only) concluded against the
   frozen schemas with every ACCEPT-blocking finding resolved by name.

## 1. Phase 0 exit evidence (masterplan §12, row 0)

| §12 exit item | where it lands | state |
|---|---|---|
| One reuse matrix | §9 below (from the C3_owners census, seat-corrected) | pending C3 |
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

## 2. Candidate verdicts (filled from the synthesis, corrected by the seat)

_pending ORCH-W1_

## 3. Frozen templates

_pending adjudication — field tables per template, shared $defs_

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

_pending_

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

_pending C3_owners_

## 10. Not verified in Phase 0

_pending_
