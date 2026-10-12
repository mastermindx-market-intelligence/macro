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
| Benchmark sampling plan | §6 | DRAFT (seat design; counts pending C1) |
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

_pending C1_tape_

## 9. Reuse matrix

_pending C3_owners_

## 10. Not verified in Phase 0

_pending_
