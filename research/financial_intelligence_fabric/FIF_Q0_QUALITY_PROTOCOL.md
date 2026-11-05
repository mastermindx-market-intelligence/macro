# FIF Q0 — Independent quality and sampling protocol (A37/A34)

**Lane:** `fif-q0-quality-protocol-20261012`  
**Workstream:** WS:FINANCIAL-INTELLIGENCE-FABRIC  
**Program:** `fundamental-forensics`  
**Repo / pin:** `mastermindx-market-intelligence/macro` HEAD `5267c66846e7733bc1eb30edc1524daff51598ca`  
**`protocol_id`:** `fif-q0-quality-protocol/v1`  
**Machine manifest:** `research/financial_intelligence_fabric/FIF_Q0_QUALITY_PROTOCOL.json`  
**Report schema:** `contracts/fundamental_forensics_pack_quality_report.v1.schema.json`

Q0 freezes; Q1 evaluates; builders never read held-out.

This document freezes the split, directory grammar, per-issuer roles, isolation rule, sampling matrix, minimum N, label vocabulary, metrics, false-positive report, failed-family disposition, quality labels, and operator rules for specialist packs PK01–PK12 and the kernel five-detector family. It is not a Q1 measurement and not pack acceptance. Every value a later evaluator prints is a deterministic function of source bytes (constitution A7).

---

## 0. Identity

| Field | Value |
|---|---|
| `protocol_id` | `fif-q0-quality-protocol/v1` |
| `frozen_at_commit` | `5267c66846e7733bc1eb30edc1524daff51598ca` |
| `schema` (manifest) | `fundamental_forensics.quality_protocol/v1` |
| Calibration root | `tests/fixtures/fundamental_forensics` |
| Held-out root | `tests/fixtures/fundamental_forensics_held_out` |
| Calibration-only accessions | `0000320193-25-000079`, `0000320193-26-000020` (`engine/fundamental_forensics/ixbrl_raw_ledger.py:56-58`) |
| Golden fixture map | `GOLDEN_AAPL_FIXTURES` (`engine/fundamental_forensics/statement_graph.py:76-78`) |
| Issuers | AAPL, SNOW, CAT, BAC, GOOGL |
| Packs | PK01–PK12 (`~/lanes/fif_plan/SPECIALIST_PACKS.json`) |
| Kernel family | `kernel_detectors_v1` / detector pack `fundamental-forensics-five/v1` (`config/fundamental_forensics.yml:4`) |

The two committed AAPL packages are calibration / regression gold. They are never copied into held-out and never counted in Q1 precision/recall denominators. A later held-out AAPL document, if used, is a different accession than the pair above.

Query factory remains `GoldenAaplFinancialQueryProvider` (`app/forensics.py:731-746`); statement factory remains `GoldenAaplStatementProvider` (`app/forensics.py:767-773`). Lawful delivery is `{kind: committed_golden_fixture, attested: false, production_issuer_service: false}` (`engine/fundamental_forensics/query_service.py:53-56`; `engine/fundamental_forensics/ixbrl_raw_ledger.py:66-72`).

---

## 1. Split law (design §2.1)

| Split | Who may read | What it proves |
|---|---|---|
| **Calibration gold** | Pack builders, kernel tests, CI regression | Schema, extraction, and unit tests; AAPL golden pair; builder-visible labeled examples |
| **Held-out** | Independent Q1 operator only, after builders freeze | A37 unseen issuer/format and negative examples |

Calibration gold is the builder-visible set. Held-out is the independent proof set. The AAPL golden pair stays under `tests/fixtures/fundamental_forensics/aapl_10k_2025` and `aapl_10q_2026q3` as mapped by `GOLDEN_AAPL_FIXTURES`.

---

## 2. Directory and naming (design §2.2)

Held-out is a **sibling** of the calibration root. Nesting held-out under `tests/fixtures/fundamental_forensics/` is forbidden: that directory is already consumed by golden loaders (`engine/fundamental_forensics/statement_graph.py:76-78`).

```
tests/fixtures/fundamental_forensics/                  # calibration; builders + CI regression
  aapl_10k_2025/                                       # CALIBRATION ONLY
  aapl_10q_2026q3/                                     # CALIBRATION ONLY
  packs/PK01..PK12/gold/                               # builder-visible gold (later)
  packs/PK01..PK12/labels/                             # builder-visible labels (later)

tests/fixtures/fundamental_forensics_held_out/         # Q1 only; builders never read
  README.md
  packs/PK01..PK12/<package>/
  packs/PK01..PK12/negatives/
  packs/PK01..PK12/labels/                             # sealed until Q1 open
    _SEALED
  unseen_formats/PK04../
```

Inner package layout copies the existing golden package:

```
{ticker}_{form}_{period}/
  package_manifest.json     # schema fundamental_forensics.golden_filing_package/v1
  index.json
  sec_submissions_witness.json
  members/
```

Filename grammar: `{ticker_lower}_{form_lower}_{period}` where `form` is `10k`, `10q`, `10ka`, `def14a`, `8k` and `period` is `YYYY`, `YYYYqN`, or `YYYYMMDD` (8-K). Negatives append `_absent_{section_family_id}`. Label files sit next to the package, never inside `members/`.

This Q0 freeze ships the held-out **root and README only**. No corpus, no labels.

---

## 3. Per-issuer split (design §2.3)

Issuer roles (commissioning; observed coverage at this HEAD is the AAPL golden pair only):

| Issuer | Gold (builders) | Held-out (Q1 only) | Pack emphasis |
|---|---|---|---|
| AAPL | Existing 10-K/10-Q pair is kernel/statement/lineage calibration. Additional AAPL gold must be a different labeled span, never the two golden accessions relabeled. | Optional later-year 10-K or 10-K/A outside `GOLDEN_AAPL_QUERY_ACCESSIONS`. | End-to-end kernel; not pack efficacy. |
| SNOW | One annual + one interim for PK02/PK04 gold (RPO/SBC/revenue). | Different fiscal year than gold, plus one negative (e.g. absent bank capital, PK11). | PK02, PK04. |
| CAT | One annual + one interim for PK03/PK01/PK06 gold (segments, debt, leases). | Different year; negative for PK11/PK12. | PK03, PK01. |
| BAC | One annual bank 10-K for PK11 gold; industrial-ratio negative gold for five-detector leakage (A30). | Different year; unseen format (10-K/A or MD&A-only excerpt). | PK11. |
| GOOGL | One annual for PK03/PK07 gold (segments, intangibles); identity-binding gold. | Different year; Class A/C security projection without duplicate issuer. | PK03, PK07. |

A33: same general provider and kernel; no ticker-specific patched answers. Held-out tests call the same pack code paths as gold.

---

## 4. Isolation (design §2.4)

**Directory:** `tests/fixtures/fundamental_forensics_held_out/` is the only held-out root.

**Forbidden references** in `engine/`, `app/`, `lib/`, `scripts/build_*.py`, `scripts/render_*.py`, `engine/fundamental_forensics/`, pack builder modules, `GOLDEN_AAPL_FIXTURES`, and any runtime `*_FIXTURES` dict: substrings `fundamental_forensics_held_out` and `fixtures/fundamental_forensics/held_out`.

**Allowed references:** `tests/test_fundamental_forensics_held_out_isolation.py`; `tests/test_fundamental_forensics_q0_quality_protocol.py` (manifest pin only; this module never opens the held-out root); `tests/test_fundamental_forensics_q1_held_out_*.py` (Q1 operator only); this protocol document.

**Six isolation assertions** (CI: `tests/test_fundamental_forensics_held_out_isolation.py`):

1. Held-out root path is exactly `tests/fixtures/fundamental_forensics_held_out` and exists.
2. No file under `engine/`, `app/`, `lib/`, `scripts/build_*.py`, `scripts/render_*.py` contains `fundamental_forensics_held_out` or `fixtures/fundamental_forensics/held_out` (text walk of `*.py`, `*.js`, `*.json`, `*.yml`).
3. Every `GOLDEN_AAPL_FIXTURES` value (ast of `engine/fundamental_forensics/statement_graph.py`) sits under `tests/fixtures/fundamental_forensics/` and not under the held-out root.
4. No `engine/fundamental_forensics/*.py` import names a module containing `held_out` (ast).
5. No test module other than the isolation file, `tests/test_fundamental_forensics_q0_quality_protocol.py`, and `tests/test_fundamental_forensics_q1_held_out_*.py` contains the held-out root string.
6. The held-out root contains no `labels/*.json` except under a `labels/` directory that also holds `_SEALED` (vacuous until labels arrive).

Mirror the research-census rule at `research/financial_intelligence_fabric/replay_fif3a4r_aapl_overlap_census.py:545-549`: held-out JSON must never be loaded by a production or query provider.

**Seal:** `packs/PKxx/labels/_SEALED` is a marker file. Q1 tests refuse to run if a builder test module (`tests/test_fundamental_forensics_pk*.py` without `_q1_held_out_`) reads `labels/` under the held-out root.

Pack-builder CI may go green on gold + isolation. Pack **acceptance** requires a separate Q1 job the builder does not author (A34: each pack carries its own held-out proof; a group summary cannot hide a gap).

---

## 5. Sampling matrix (design §3.3)

Applicability: `required` = extract when the disclosure exists; `negative` = typed absence expected; `optional` = extract if present, absence is not a pack failure. Pack names from `SPECIALIST_PACKS.json`.

| Pack | Name | Section family ids | AAPL | SNOW | CAT | BAC | GOOGL | Forms |
|---|---|---|---|---|---|---|---|---|
| PK01 | Debt, liquidity, covenants and maturities | `debt_outstanding`, `maturity_schedule`, `covenant_text`, `liquidity` | optional | optional | required | required | optional | 10-K, 10-Q |
| PK02 | Stock compensation and dilution | `sbc_expense`, `award_activity`, `share_basis` | optional | required | optional | optional | optional | 10-K, 10-Q |
| PK03 | Segments and geographic/product dimensions | `segment_map`, `eliminations`, `reporting_change` | optional | optional | required | optional | required | 10-K, 10-Q |
| PK04 | Revenue recognition and contract balances | `recognized_revenue`, `deferred_revenue`, `contract_asset_liability` | optional | required | optional | negative | optional | 10-K, 10-Q, 8-K |
| PK05 | Tax and uncertain tax positions | `etr_recon`, `deferred_tax`, `utp` | optional | optional | optional | optional | optional | 10-K |
| PK06 | Leases and off-balance commitments | `lease_liability`, `lease_term`, `offbalance_commitments` | optional | optional | required | optional | optional | 10-K, 10-Q |
| PK07 | M&A, goodwill, intangibles and impairments | `acquisition_date`, `goodwill_rollforward`, `impairment_evidence` | negative | optional | optional | optional | required | 10-K, 8-K |
| PK08 | Legal contingencies | `allegation`, `disclosed_range`, `procedural_status` | optional | optional | optional | optional | optional | 10-K, 10-Q |
| PK09 | Controls, auditor and going concern | `icfr_opinion`, `auditor_opinion`, `going_concern_wording` | optional | optional | optional | optional | optional | 10-K, 10-Q |
| PK10 | Proxy compensation and governance | `comp_table`, `perf_period`, `pay_vs_perf` | required | required | required | required | required | DEF 14A |
| PK11 | Financial-institution credit/capital/liquidity | `cet1_or_stated_ratio`, `credit_loss`, `lcr_or_stated_liq` | negative | negative | negative | required | negative | 10-K, 10-Q |
| PK12 | Biotech cash/R&D/financing disclosures | `cash_runway_disclosure`, `rd_expense`, `going_concern_or_financing` | negative | negative | negative | negative | negative | 10-K |

Conditions (also in the machine manifest `applicability_conditions`):

- PK04 × BAC: negative (bank interest vs contract).
- PK07 × AAPL: negative unless a deal year.

PK10 forms are `DEF 14A` only; a 10-K is not a substitute. PK12 positives among these five issuers would be a labeling error; A37 on this issuer list is satisfied by negative examples. A later biotech issuer is a D0/C2 concern.

Stratum of a labeled trial: `(pack_id, issuer, form_type, fiscal_year, section_family, polarity, format_class)`. Gold year ≠ held-out year for the same `(pack, issuer, form)`. Format classes: `ixbrl_inline`, `unseen_amendment`, `unseen_exhibit`, `unseen_proxy`.

---

## 6. Minimum N (design §3.2)

These minima are protocol budgets, not observed corpus counts. Current on-disk FIF packages = 2 (`engine/fundamental_forensics/statement_graph.py:76-78`). Q1 may not lower N after seeing a bad result.

| Split | Cell | Minimum N | If below |
|---|---|---|---|
| Gold | pack, form_type in {10-K, 10-Q}, polarity=positive, across >= 2 issuers | **3** | pack stays `display_tier`; cannot request `accepted` |
| Gold | pack, polarity=negative | **2** | pack cannot claim refusal coverage |
| Held-out | pack, applicable issuer, polarity=positive | **2** (different FY from gold) | Q1 reports `underpowered`; disposition `unavailable_research_only` |
| Held-out | pack, polarity=negative | **1** | Q1 reports `underpowered`; disposition `unavailable_research_only` |
| Held-out | pack, format_class != ixbrl_inline | **1** | A37 cell empty; pack cannot claim format generalization |
| Held-out | PK11 × non-bank issuers (AAPL/SNOW/CAT/GOOGL) | **1** negative each | industrial-ratio leakage untested (A30) |
| Held-out | PK12 × all five issuers | **1** negative each | PK12 has no biotech among the five; positives need an explicit later issuer or stay blocked |

---

## 7. Label classes (design §3.4)

Frozen vocabulary for gold and held-out:

| `label_class` | Meaning | Counted in |
|---|---|---|
| `extract_positive` | source span exists; admitted extraction must match value/unit/period/definition | precision, recall |
| `extract_absent` | disclosure family not present; system must typed-refuse | abstention / refusal quality; FP if it extracts |
| `extract_present_out_of_scope` | text exists but pack boundary forbids use | FP if emitted as pack claim |
| `finding_triggered_expected` | detector/finding should fire | precision/recall of findings |
| `finding_clear_expected` | detector should be `clear` | FP if `triggered` |
| `finding_not_evaluable_expected` | missing inputs / inapplicable | abstention; not FP |
| `source_fidelity_fail` | wrong span, unit, period, or definition | source-fidelity error rate |
| `relevance_review` | analyst-relevant vs noise (independent domain reviewer) | relevance; not a market-alpha score |

A27: a triggered finding is an observation; a hypothesis tag is optional and never a fraud/alpha claim (`tests/test_fundamental_forensics_contract.py:98-114`).

---

## 8. Metrics (numerator/denominator with exclusions)

Every published quality cell prints:

```
{metric} = {numerator}/{denominator}  excluded={n}  reasons=[...]
```

| Metric | Numerator | Denominator | Exclusions |
|---|---|---|---|
| precision | extract_positive predicted and label-matched | predicted extract_positive | `not_evaluable`, out-of-scope, unlabeled |
| recall | extract_positive predicted and label-matched | label extract_positive | do not drop hard cases after failure |
| abstention | predicted `not_evaluable` or typed_absence | eligible trials in the cell | split `insufficient_evidence` vs `not_applicable` (`tests/test_fundamental_forensics_disclosure_diff.py:268-281`) |
| source_fidelity_error | `source_fidelity_fail` | predicted extract_positive | unlabeled |
| false_positive_rate | predicted extract_positive or finding_triggered on `extract_absent` or `finding_clear_expected` | negative-label trials | `not_evaluable` |

Coverage (pack × issuer): periods with an admitted in-scope field / declared periods in the pack manifest. A truthful refusal is excluded from the numerator.

A group dashboard may show micro-averages only after all 12 pack rows are printed. A missing pack row is a gap.

Map existing finding states (`engine/fundamental_forensics/models.py:31-34`): `TRIGGERED` = predicted-positive finding; `CLEAR` = predicted-negative finding; `NOT_EVALUABLE` (`engine/fundamental_forensics/detectors.py:148-164`; `tests/test_fundamental_forensics_detectors.py:96-106`) = abstention, never FP. Packet `display_only` / `context_only` (`engine/fundamental_forensics/financial_intelligence_packet.py:434-435`) is display-tier output.

Uncertainty: binomial Wilson interval at 95% when denominator >= 1; if denominator is below minimum N the cell is `underpowered`. Domain disagreement on a 20% gold subsample is printed; it does not rewrite labels after Q1 open.

---

## 9. False-positive report

One JSON object per false positive, collected into `false_positives[]` on the pack report. Required fields: `fp_id`, `pack_id`, `issuer`, `form_type`, `accession`, `section_family`, `split`, `predicted` `{kind, value_text, span_ref, finding_id}`, `label` `{label_class, reason}`, `error_class`, `alternative_explanation`, `display_copy_used`, `guarded_token_present`.

`error_class` values: `invented_extraction`, `wrong_span`, `wrong_period`, `wrong_unit`, `detector_leakage`, `ticker_patch_suspected`.

`detector_leakage` is the A30 case (industrial detector on BAC). `ticker_patch_suspected` is the A33 case. Display copy in `display_copy_used` is the surface `check_validated_claims.py` would scan. FP reports live under `reports/` or the held-out tree. Quality copy uses the vocabulary in §11.

---

## 10. Failed-family disposition (blocks that pack only)

A family for disposition is `(pack_id, section_family)` plus the kernel detector id when evaluating `kernel_detectors_v1`.

Trigger any one of: held-out precision lower bound (Wilson) below the predeclared floor, or any false positive on a negative example in that family; held-out cell underpowered (§6); source-fidelity error on any `accepted`-candidate claim; A27 violation (fraud/alpha language) or A25 invented figure; isolation test failure (builders read held-out).

Record on `failed_families[]`: `pack_id`, `section_family`, `disposition`, `blocks`, `does_not_block`, `reason_codes`, `numerator_denominator`, `relabel_forbidden` (const true), `reopen_requires`.

Law:

- Disposition is `unavailable_research_only` until an explicit scope decision, or `blocked_pack` when the pack id is blocked.
- **Block that pack only** (A34). Sibling packs remain independently scorable.
- Do not relabel the family `accepted`. Do not drop the failed cell from the denominator.
- Kernel five-detector failure does not accept or reject PK01–PK12; PK11 leakage fails PK11 and also files an FP against `kernel_detectors_v1` if an industrial detector fired on a bank.

Health endpoint status `current` / `stale` / `degraded` / `unavailable` (`engine/fundamental_forensics/health.py:40`) is freshness, never pack disposition.

---

## 11. Quality labels (design §5.2)

Quality reports, pack schemas, and analyst copy must not use the token scanned by `check_validated_claims.py` (including hyphenated forms). Use this vocabulary:

| Label | Meaning | May appear on | Forbidden uses |
|---|---|---|---|
| `calibration` | known AAPL golden / builder gold; regression | test docs, manifests | “generalizes”; “held-out proved” |
| `display_tier` | may render as `display_only` / `context_only` / `review_priority_only` | UI, packets, findings | production admission; user-facing pack-quality badge using the CI-guarded token |
| `held_out_measured` | Q1 numbers exist for this pack/family | quality report only | user-facing pack badge |
| `accepted` | independent Q1 + domain review + live source trace + isolation test green; pack may bind production provider | pack manifest `acceptance.state` | statistical synonym for the CI-guarded token; AAPL-demo-only |
| `unavailable_research_only` | failed or underpowered family | quality report, UI absence | silent omission from denominator |
| `blocked_pack` | disposition blocks this pack id only | quality report | blocking sibling packs |
| `typed_absence` | disclosure not in source; honest refusal | cells, coverage | counting as positive coverage |
| `underpowered` | N below §6 | quality report | lowering N to pass |

Default finding/packet path today is `display_tier` (`engine/fundamental_forensics/models.py:319-320`; `engine/fundamental_forensics/financial_intelligence_packet.py:434-435`; `app/forensics.py:731-746`). Moving a pack from `display_tier` to `accepted` is a Q1/K-task event.

---

## 12. Report schema

One JSON document per pack per Q1 run (A34). Group summaries are a view over twelve documents.

- Schema file: `contracts/fundamental_forensics_pack_quality_report.v1.schema.json`
- `$id`: `https://mastermind-x.com/contracts/fundamental_forensics_pack_quality_report.v1.schema.json`
- Document `schema` const: `fundamental_forensics.pack_quality_report/v1`
- `protocol_id` const: `fif-q0-quality-protocol/v1`
- `pack_id` enum PK01–PK12 (single pack per document)
- `quality_label` enum = the eight labels in §11
- `aapl_golden_used_as_held_out` const false
- `builders_read_held_out` const false
- Every rate is `{numerator, denominator, exclusions[]}` with integer numerator/denominator (denominator minimum 0). No bare float rates.
- `additionalProperties: false` on every object.

Q1 loader invariants: `failed_families[].blocks` is a subset of `{this pack_id}` (plus optional `kernel_detectors_v1` when leakage is the reason); all twelve pack ids have a report file even if every cell is `underpowered`.

---

## 13. Operator rules (design §7)

1. Q0 (this document) freezes labels, splits, N, metrics, vocabulary, schema.
2. K1–K4 builders produce schema + gold + typed absences + source traces per pack. They do not author Q1 tests that read held-out.
3. Q1 is an independent evaluator. It opens held-out labels, writes twelve `pack_quality_report` documents, and files failed-family records.
4. Isolation test (§4) runs on every PR that touches `engine/fundamental_forensics/`, `app/forensics.py`, or pack builders.
5. A34: a slide that averages twelve packs without twelve report paths is not acceptance evidence.
6. A37: at least one held-out cell per pack is an unseen format or a negative example. PK11/PK12 on the five-issuer set are primarily negatives; that is sufficient for those packs on this issuer list.

---

## 14. Kernel five-detector family (design §8)

Evaluated as `kernel_detectors_v1` using the same metric block, on fixtures that are not the AAPL 10-K/10-Q pair:

- Gold: `tests/fixtures/fundamental_forensics/companyfacts_versions.json` + `submissions_versions.json` (loaded by detector tests at `tests/test_fundamental_forensics_detectors.py:21-22`).
- Expected calibration: five `triggered` (`tests/test_fundamental_forensics_detectors.py:64-71`); findings remain `display_only` / `review_priority_only`.
- Abstention unit test already exists (`tests/test_fundamental_forensics_detectors.py:96-106`).
- Held-out for this family: companyfacts slices from SNOW/CAT/BAC/GOOGL not used while tuning thresholds in `config/fundamental_forensics.yml:60-85`. BAC is a mandatory negative for industrial detectors (A30).

This family remaining `display_tier` / `review_priority_only` (`engine/fundamental_forensics/models.py:319-320`) is correct until Q1 says otherwise.

---

## 15. Assumptions

- Specialist pack code does not exist at this HEAD; this protocol is the freeze K1–K4/Q1 must obey.
- D0 will name exact production accessions; Q0 names roles (gold vs held-out vs negative). When D0 publishes accessions, Q1 binds them into cell rows without changing N or label rules.
- PK12 will not gain a stealth biotech among the five reference issuers.
- Adjacent fixtures (`tests/fixtures/capital_structure`, `cash_runway`, `industrials_result_cash`) remain other products’ tests unless a later owner maps them as gold excerpts with a new manifest; they are not held-out.
- `docs/site_semantics/*forensic*` remaining empty does not block Q0; forensic display law is the packet/finding `display_only` contracts already tested.

---

## 16. Gaps

- Expanded pytest node count (parametrized cases) was not re-censused in this writer lane.
- FIRST_VERTICAL_PLAN diagnostic hashes were not re-run (suite execution out of scope).
- Exact DEF 14A / 8-K package member retention rules — only 10-K/10-Q retention was observed on the golden pair.
- Held-out corpus and labels are not acquired here (D0/Q1; network out of scope).
- Report-schema language-gate field names use `guarded_token_count` / `hyphen_guarded_count` so the owned files can name `check_validated_claims.py` without carrying the scanned token as a JSON key.

---

## 17. Protocol checklist (Q0 done when)

- [x] Held-out sibling directory + naming consistent with `aapl_10k_2025` / `package_manifest.json`
- [x] Isolation test specified against production import/path surfaces
- [x] Isolation test implemented (`tests/test_fundamental_forensics_held_out_isolation.py`)
- [x] Stratified sampling for PK01–PK12 × AAPL/SNOW/CAT/BAC/GOOGL including negatives and unseen formats
- [x] Minimum N and numerator/denominator printing
- [x] Precision/recall/abstention, FP report, failed-family blocks **that pack only**
- [x] Vocabulary compatible with `check_validated_claims.py`
- [x] JSON schema `fundamental_forensics.pack_quality_report/v1`
- [x] Machine manifest `FIF_Q0_QUALITY_PROTOCOL.json`
- [ ] Held-out corpus acquired (D0/Q1; network out of scope)
