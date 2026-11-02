# FIF D0 — Five-issuer source and coverage contract

- **Contract id:** `five_issuer_v1`
- **Machine config:** `config/fundamental_forensics/coverage/five_issuer_v1.json`
- **Schema:** `fundamental_forensics.coverage_contract/v1`
- **Capture basis:** `reconstruction`
- **Attested:** `false`
- **Historical attestation:** `unavailable_until_d2_admission`
- **Worktree head:** `5267c66846e7733bc1eb30edc1524daff51598ca`

This is a **contract**, not an acquisition. Nothing is fetched, nothing is retained by this document, and nothing is attested. Accession numbers, CIKs, dates, and metric ids are copied from the D0/G-pack/C0C2 census and from committed fixtures. A row the census marks uncertain stays marked `uncertain`.

---

## 1. Purpose

Freeze the five-issuer source and coverage surface (AAPL, SNOW, CAT, BAC, GOOGL) so later FIF lanes share one denominator:

1. **A52 rights** — public SEC EDGAR only; names of unused credentials; no purchase, licence, or bypass.
2. **A13 reconstruction** — downloaded-today bytes are reconstruction. Historical attestation waits for a future D2 admission reference.
3. **A36 field denominator** — the 50 core metric ids in `config/fundamental_forensics/metrics/v1/metric_catalog.yaml`, with bank-class `not_applicable` only where the census states a reason.
4. **A20 budget owner** — one incumbent SEC pacer, named; no second scheduler, queue, pacer, or budget owner.

The four clocks (source accepted, observed/recorded, admitted, as-of query) remain distinct. A comparative reprint is not a restatement. Rounded consistency is not transitive. A partial package is never advertised complete. A model or narrative never creates a canonical number or action.

---

## 2. Rights and eligibility (A52) — names only

| Field | Value | Cite |
|---|---|---|
| provider | `sec_edgar_public_filings` | census `fif-d0-source-contract.md` §6; public `data.sec.gov` / `www.sec.gov/Archives/` |
| access_policy | `sec_fair_access_declared_user_agent` | `collectors/edgar_forensics.py:238`; `collectors/sec_document_spine.py:821`; `collectors/fundamental_forensics_companyfacts.py:90` |
| purchases | `[]` | census §6: no SEC API keys, logins, or purchases |
| licences_accepted | `[]` | census §6 |
| credentials_required | `[]` | this contract does not require any credential to *exist* as a source right |

**Declared user-agent config key (name only):** `config.yml` → `edgar.user_agent` (`collectors/edgar_forensics.py:646-651`). Value is not recorded here.

**Known credential environment names, not used by this contract:**

- `R2_RESEARCH_BUCKET`
- `R2_RESEARCH_ENDPOINT`
- `R2_RESEARCH_ACCESS_KEY_ID`
- `R2_RESEARCH_SECRET_ACCESS_KEY`
- `RESEARCH_LOCAL_STORE`

Those names come from `engine/research_vault/r2_store.py:7-15`. They are the private research-store family. This contract does **not** consume them. If a later lane needs that plane, the dependent release is blocked until those names are admitted by their owner — this contract does not purchase, copy, or bypass them.

**SEC request budget owner (the one incumbent pacer):** `collectors.edgar_forensics:SecForensicsCollector` (`collectors/edgar_forensics.py:225`, `_pace` at `:248`). Census §4 and C0C2 §1.4 record that pacing is duplicated across three collector classes and A20 is not met today. Naming the incumbent is the freeze; adding a tenth pacer is forbidden.

---

## 3. Reconstruction versus retained history (A13)

| Claim | Status | Cite |
|---|---|---|
| Capture clock on golden fixtures | `fixture_recorded_at` is a capture-process clock; request time must never mint it | `engine/fundamental_forensics/statement_graph.py:117` |
| Served AAPL goldens | `attested: False`, `production_issuer_service: False` | `engine/fundamental_forensics/ixbrl_raw_ledger.py:66-72` |
| Reconstruction proof (`ffxbrl_`) | replay over retained bytes | census §5 |
| Sealed source-read attestation (`ffatt_`) | not minted by this contract; waits for D2 admission | census §5 |

**Rule:** data downloaded today is **RECONSTRUCTION**, never historical attestation. Only a future D2 admission reference may mint an attestation label. This contract sets `capture_basis=reconstruction`, `attested=false`, and `historical_attestation=unavailable_until_d2_admission` at the top level. No accession row carries `attested`.

The two AAPL golden packages already on disk are **retained reconstruction fixtures**, not attested history:

- `0000320193-25-000079` — `tests/fixtures/fundamental_forensics/aapl_10k_2025/package_manifest.json:8-12`
- `0000320193-26-000020` — `tests/fixtures/fundamental_forensics/aapl_10q_2026q3/package_manifest.json:8-12`

They equal `GOLDEN_AAPL_QUERY_ACCESSIONS` (`engine/fundamental_forensics/ixbrl_raw_ledger.py:56-59`). This contract does not widen that v1 two-accession guard.

---

## 4. Retained package law (nine component types)

Copied from census `fif-d0-source-contract.md` §2 and the AAPL FY2025 golden (`tests/fixtures/fundamental_forensics/aapl_10k_2025/package_manifest.json:1-26`; admission `engine/fundamental_forensics/statement_graph.py:177`).

**Retained component types (9):**

| # | Component | Role |
|---|---|---|
| 1 | Package manifest (`package_manifest.json`) | package identity/inventory |
| 2 | Archive index (`index.json`) | package-level, digest-bound |
| 3 | Acceptance witness | package-level; binds `accessionNumber/form/primaryDocument/reportDate/filingDate/acceptanceDateTime` |
| 4 | Primary iXBRL document (`.htm`) | `primary` |
| 5 | Schema (`.xsd`) | `schema` |
| 6 | Calculation linkbase (`_cal.xml`) | `calculation` |
| 7 | Definition linkbase (`_def.xml`) | `definition` |
| 8 | Label linkbase (`_lab.xml`) | `label` |
| 9 | Presentation linkbase (`_pre.xml`) | `presentation` |

Member states: `stored | missing | not_requested | rejected_by_policy` (`engine/fundamental_forensics/filing_package.py:58`).

**`not_requested` member classes** (declared reason: "not required for XBRL statement reconstruction"): archive index headers/html, raw complete submission `.txt`, `*-xbrl.zip`, exhibits, graphics, extracted XBRL instance `*_htm.xml`, `FilingSummary.xml`, `MetaLinks.json`, all R-files (`package_manifest.json:29-390` region; census §2.2).

AAPL FY2025: `member_count: 93`, `retained_count: 6` (`package_manifest.json:25-26`). The six stored members are primary+schema+cal+def+lab+pre; the three package-level objects (manifest, index, witness) sit beside them. Wave-2 acquires primary HTML only (`collectors/fundamental_forensics_acquisition.py:7-9`) and is not a complete admitted source package.

---

## 5. Field denominator (A36)

- Catalog path: `config/fundamental_forensics/metrics/v1/metric_catalog.yaml`
- Catalog id: `fundamental_forensics_core_gaap_metrics` (`metric_catalog.yaml:2`)
- Count: 50 (`engine/fundamental_forensics/metric_registry.py:29`, `CORE_V1_METRIC_COUNT`)
- Metric ids: the exact sorted list of `metric_id` entries in that catalog (frozen in the JSON `field_denominator.metric_ids`)

C0C2 (`fif-c0c2-coverage-discovery.md` §5.4) freezes this 50-metric catalog, not the 9-metric detector YAML.

**`not_applicable` (census reason only, never a guess):**

| Ticker | metric_id | Reason | Cite |
|---|---|---|---|
| BAC | `gross_profit` | bank-class; `GrossProfit` absent | `fif-g3-bac.md` §3.2 |
| BAC | `gross_margin` | bank-class; generic gross-margin detector must refuse | `fif-g3-bac.md` §3.2, §5.2 |
| BAC | `cost_of_revenue` | bank-class; `CostOfRevenue` / `CostOfGoodsAndServicesSold` absent | `fif-g3-bac.md` §3.2 |
| BAC | `inventory_net` | bank-class; `InventoryNet` absent | `fif-g3-bac.md` §3.2, §5.2 |
| BAC | `free_cash_flow` | bank-class; industrial FCF not applicable; capex concept absent | `fif-g3-bac.md` §3.2, §5.2 |

Issuer class: BAC is `bank`; AAPL, SNOW, CAT, GOOGL are `industrial`.

---

## 6. Per-issuer table (mirrors the JSON)

Identity binding: AAPL is `golden_committed`; SNOW, CAT, BAC, GOOGL are `generic_path_only` (census `fif-d0-source-contract.md` §1). Generic paths exist (`collectors/edgar_forensics.py:654`; `collectors/fundamental_forensics_acquisition.py:97`; `engine/fundamental_forensics/statement_service.py:102`) and parquet membership is unverified in this sparse worktree.

Retention: `retained_golden_fixture` **only** for the two AAPL goldens. Every other row is `not_retained`.

### 6.1 AAPL — Apple Inc. — CIK `0000320193`

| Field | Value | Cite |
|---|---|---|
| legal_name | Apple Inc. | `tests/fixtures/fundamental_forensics/aapl_10k_2025/package_manifest.json:7` |
| issuer_class | industrial | census §1 |
| identity_binding_state | golden_committed | `ISS:US-XNAS-AAPL` at `package_manifest.json:3-7`; `GOLDEN_AAPL_QUERY_ACCESSIONS` `ixbrl_raw_ledger.py:56` |
| fiscal_year_end | 09-27 | committed 10-K `period_of_report` `package_manifest.json:11` (last-Saturday convention; see contradictions) |

| Accession | Form | Period | Filed | Retention | Census |
|---|---|---|---|---|---|
| `0000320193-25-000079` | 10-K | 2025-09-27 | 2025-10-31 | retained_golden_fixture | `fif-grok-aapl-golden-audit.md` §0; `package_manifest.json:8-12` |
| `0000320193-26-000020` | 10-Q | 2026-06-27 | 2026-07-31 | retained_golden_fixture | `fif-grok-aapl-golden-audit.md` §0; `aapl_10q_2026q3/package_manifest.json:8-12` |

A2 is a 10-Q (FY2026 Q3), not a 10-K 2026. The 10-Q related_event_ref names 8-K `0000320193-26-000018` (`aapl_10q_2026q3/package_manifest.json:49`) without census dates; that 8-K is not invented as a row.

### 6.2 SNOW — Snowflake Inc. — CIK `0001640147`

| Field | Value | Cite |
|---|---|---|
| legal_name | Snowflake Inc. | `fif-g1-snow.md` line 4; submissions `name` |
| issuer_class | industrial | census |
| identity_binding_state | generic_path_only | census §1 |
| fiscal_year_end | 01-31 | `fif-g1-snow.md` line 4, `fiscalYearEnd: "0131"` |

Approved accession set copied from `fif-g1-snow.md` §1 (10-K, 10-Q) and §6 (Item 2.02 8-K). Six older 10-Qs keep `uncertain` because FilingSummary.xml was not fetched.

| Accession | Form | Period | Filed | Uncertain |
|---|---|---|---|---|
| `0001640147-26-000008` | 10-K | 2026-01-31 | 2026-03-20 | |
| `0001640147-25-000052` | 10-K | 2025-01-31 | 2025-03-21 | |
| `0001640147-24-000101` | 10-K | 2024-01-31 | 2024-03-26 | |
| `0001640147-26-000037` | 10-Q | 2026-07-31 | 2026-09-04 | |
| `0001640147-26-000030` | 10-Q | 2026-04-30 | 2026-05-29 | |
| `0001640147-25-000211` | 10-Q | 2025-10-31 | 2025-12-05 | FilingSummary not fetched |
| `0001640147-25-000187` | 10-Q | 2025-07-31 | 2025-09-05 | FilingSummary not fetched |
| `0001640147-25-000110` | 10-Q | 2025-04-30 | 2025-05-30 | FilingSummary not fetched |
| `0001640147-24-000250` | 10-Q | 2024-10-31 | 2024-11-27 | FilingSummary not fetched |
| `0001640147-24-000207` | 10-Q | 2024-07-31 | 2024-08-29 | FilingSummary not fetched |
| `0001640147-24-000135` | 10-Q | 2024-04-30 | 2024-05-31 | FilingSummary not fetched |
| `0001640147-26-000033` | 8-K | 2026-09-02 | 2026-09-02 | |

All SNOW rows `not_retained`.

### 6.3 CAT — Caterpillar Inc. — CIK `0000018230`

| Field | Value | Cite |
|---|---|---|
| legal_name | Caterpillar Inc. | `fif-g2-cat.md` line 3; submissions `CATERPILLAR INC` |
| issuer_class | industrial | census |
| identity_binding_state | generic_path_only | census §1 |
| fiscal_year_end | 12-31 | `fif-g2-cat.md` Q1, `fiscalYearEnd: "1231"` |

Approved accession set copied from `fif-g2-cat.md` Q1 (10-K, 10-Q) and Q6 (Item 2.02 8-K). Seven of eight 10-Qs stay `uncertain` (index-page cap / Q3 2025 directory listing).

| Accession | Form | Period | Filed | Uncertain |
|---|---|---|---|---|
| `0000018230-26-000008` | 10-K | 2025-12-31 | 2026-02-13 | |
| `0000018230-25-000008` | 10-K | 2024-12-31 | 2025-02-14 | |
| `0000018230-24-000009` | 10-K | 2023-12-31 | 2024-02-16 | |
| `0000018230-26-000046` | 10-Q | 2026-06-30 | 2026-08-05 | |
| `0000018230-26-000021` | 10-Q | 2026-03-31 | 2026-05-06 | FilingSummary not confirmed |
| `0000018230-25-000048` | 10-Q | 2025-09-30 | 2025-11-03 | directory listed index/txt/xbrl.zip only |
| `0000018230-25-000040` | 10-Q | 2025-06-30 | 2025-08-06 | FilingSummary not confirmed |
| `0000018230-25-000016` | 10-Q | 2025-03-31 | 2025-05-07 | FilingSummary not confirmed |
| `0000018230-24-000053` | 10-Q | 2024-09-30 | 2024-11-06 | FilingSummary not confirmed |
| `0000018230-24-000045` | 10-Q | 2024-06-30 | 2024-08-07 | FilingSummary not confirmed |
| `0000018230-24-000020` | 10-Q | 2024-03-31 | 2024-05-01 | FilingSummary not confirmed |
| `0000018230-26-000040` | 8-K | 2026-08-04 | 2026-08-04 | |

All CAT rows `not_retained`.

### 6.4 BAC — BANK OF AMERICA CORP /DE/ — CIK `0000070858`

| Field | Value | Cite |
|---|---|---|
| legal_name | BANK OF AMERICA CORP /DE/ | `fif-g3-bac.md` line 5 (submissions `name`; not companyfacts `entityName`) |
| issuer_class | bank | packet; census §0 |
| identity_binding_state | generic_path_only | census §1 |
| fiscal_year_end | 12-31 | `fif-g3-bac.md` line 5, `fiscalYearEnd: "1231"` |

Approved accession set copied from `fif-g3-bac.md` §1.1–§1.3. Six of eight 10-Qs stay `uncertain`.

| Accession | Form | Period | Filed | Uncertain |
|---|---|---|---|---|
| `0000070858-26-000157` | 10-K | 2025-12-31 | 2026-02-25 | |
| `0000070858-25-000139` | 10-K | 2024-12-31 | 2025-02-25 | |
| `0000070858-24-000122` | 10-K | 2023-12-31 | 2024-02-20 | |
| `0000070858-26-000394` | 10-Q | 2026-06-30 | 2026-07-31 | |
| `0000070858-26-000249` | 10-Q | 2026-03-31 | 2026-05-01 | unconfirmed |
| `0000070858-25-000405` | 10-Q | 2025-09-30 | 2025-10-31 | unconfirmed |
| `0000070858-25-000268` | 10-Q | 2025-06-30 | 2025-07-31 | |
| `0000070858-25-000200` | 10-Q | 2025-03-31 | 2025-04-30 | unconfirmed |
| `0000070858-24-000280` | 10-Q | 2024-09-30 | 2024-10-29 | unconfirmed |
| `0000070858-24-000208` | 10-Q | 2024-06-30 | 2024-07-30 | unconfirmed |
| `0000070858-24-000156` | 10-Q | 2024-03-31 | 2024-04-30 | unconfirmed |
| `0000070858-26-000353` | 8-K | 2026-07-14 | 2026-07-14 | |

All BAC rows `not_retained`. 8-K Item 2.02 `0000070858-26-000353` is listed and not retained (`fif-g3-bac.md` §1.3).

### 6.5 GOOGL — Alphabet Inc. — CIK `0001652044`

| Field | Value | Cite |
|---|---|---|
| legal_name | Alphabet Inc. | `fif-g4-googl.md` §1 |
| issuer_class | industrial | census |
| identity_binding_state | generic_path_only | census §1 |
| fiscal_year_end | 12-31 | `fif-g4-googl.md` §1, `fiscalYearEnd: "1231"` |

One issuer, two listed tickers (GOOGL / GOOG). Coverage is per CIK; GOOG is not a second issuer (`fif-g4-googl.md` §1, §6.1; C0C2 §4.2).

Approved accession set copied from `fif-g4-googl.md` §2.1–§2.3. Six of eight 10-Qs stay `uncertain`.

| Accession | Form | Period | Filed | Uncertain |
|---|---|---|---|---|
| `0001652044-26-000018` | 10-K | 2025-12-31 | 2026-02-05 | |
| `0001652044-25-000014` | 10-K | 2024-12-31 | 2025-02-05 | |
| `0001652044-24-000022` | 10-K | 2023-12-31 | 2024-01-31 | |
| `0001652044-26-000071` | 10-Q | 2026-06-30 | 2026-07-23 | |
| `0001652044-26-000048` | 10-Q | 2026-03-31 | 2026-04-30 | not fetched |
| `0001652044-25-000091` | 10-Q | 2025-09-30 | 2025-10-30 | |
| `0001652044-25-000062` | 10-Q | 2025-06-30 | 2025-07-24 | not fetched |
| `0001652044-25-000043` | 10-Q | 2025-03-31 | 2025-04-25 | not fetched |
| `0001652044-24-000118` | 10-Q | 2024-09-30 | 2024-10-30 | not fetched |
| `0001652044-24-000079` | 10-Q | 2024-06-30 | 2024-07-24 | not fetched |
| `0001652044-24-000053` | 10-Q | 2024-03-31 | 2024-04-26 | not fetched |
| `0001652044-26-000066` | 8-K | 2026-07-22 | 2026-07-22 | |

All GOOGL rows `not_retained`.

---

## 7. Known contradictions (with repo evidence)

Full machine list: JSON `known_contradictions`. Minimum required plus census §8 and G-pack §0:

| id | Statement | Evidence |
|---|---|---|
| `d0-2docs-vs-3fy` | `HARD_MAX_DOCUMENTS_PER_FORM = 2` is below a 3FY annual+interim window | `collectors/fundamental_forensics_acquisition.py:76` |
| `d0-8k-item-202-retained-nowhere` | 8-K Item 2.02 referenced (AAPL related_event_ref; BAC §1.3) and retained nowhere; `RELEVANT_FORMS` omits 8-K | `engine/fundamental_forensics/statement_graph.py:167` |
| `d0-a20-duplicated-pacer-no-shared-budget` | Three per-process pacers; A20 unmet; incumbent named, no second budget | `collectors/edgar_forensics.py:232` |
| `d0-d1-observation-taxonomy` | Wave-2 has 4 outcomes; D1 names 5 | `collectors/fundamental_forensics_acquisition.py:67` |
| `d0-plan-version-skew` | Plan assessment pinned an older sha; this head still serves the two goldens | `engine/fundamental_forensics/ixbrl_raw_ledger.py:56` |
| `d0-aapl-8k-referenced-not-dated` | 8-K `0000320193-26-000018` has no census dates; not invented | `tests/fixtures/fundamental_forensics/aapl_10q_2026q3/package_manifest.json:49` |
| `d0-aapl-fye-last-saturday` | Stored FYE 09-27 is the committed 10-K period, not a fixed calendar FYE | `tests/fixtures/fundamental_forensics/aapl_10k_2025/package_manifest.json:11` |
| `g2-met-vs-mpe-rename` | Planning ME&T vs FY2025 MP&E / Power & Energy; issuer source wins | `engine/fundamental_forensics/statement_graph.py:76` |
| `g3-companyfacts-entityname` | companyfacts `entityName` BofA Finance LLC vs submissions BANK OF AMERICA CORP /DE/ | `engine/fundamental_forensics/metric_registry.py:53` |
| `g3-planning-vs-aapl-only-goldens` | BAC is a stress pack; goldens remain AAPL-only | `engine/fundamental_forensics/statement_graph.py:76` |
| `g4-apple-primary-statement-roles` | `PRIMARY_STATEMENT_ROLES` is apple.com; GOOGL uses google.com roles | `engine/fundamental_forensics/statement_graph.py:32` |
| `g4-prefixes-omit-goog` | `_PREFIXES` has `apple_` / `aapl_`, not `goog_` | `engine/fundamental_forensics/statement_graph.py:62` |
| `g4-companyfacts-no-goog-taxonomy` | CompanyFacts has zero dimensions and no `goog:` taxonomy | `engine/fundamental_forensics/metric_registry.py:53` |
| `g4-aapl-golden-admission-copy` | Golden admission still requires the AAPL CIK | `engine/fundamental_forensics/statement_graph.py:76` |
| `aapl-a2-is-10q-not-10k-2026` | A2 is 10-Q FY2026 Q3 | `tests/fixtures/fundamental_forensics/aapl_10q_2026q3/package_manifest.json:9` |
| `c0c2-a20-mutex-is-not-a-budget` | `filing-forensics-sec` is a mutex, not a shared per-IP request-rate limiter; scheduler still owns aggregate per-IP | `collectors/fundamental_forensics_companyfacts.py:90` |
| `broad-sec-8k-absent-from-relevant-forms` | FF-1 `RELEVANT_FORMS` has no 8-K | `engine/fundamental_forensics/broad_sec_store.py:113` |
| `wave2-primary-only-vs-nine-component-package` | Wave-2 primary HTML ≠ nine-component package | `collectors/fundamental_forensics_acquisition.py:7` |
| `d1-correction-only-as-broad-sec-reason` | D1 "correction" is `edgar_index_correction_requires_reconciliation` | `engine/fundamental_forensics/broad_sec_store.py:145` |
| `served-goldens-attested-false` | Committed goldens served `attested=False` | `engine/fundamental_forensics/ixbrl_raw_ledger.py:69` |

---

## 8. What this contract does not authorize

- **No fetch.** No SEC/EDGAR request, no retention of new bytes, no fixture capture.
- **No scheduler.** No cron, workflow, or observation-log run.
- **No second SEC budget.** The incumbent pacer is `collectors.edgar_forensics:SecForensicsCollector`. No new queue, pacer, token bucket, or budget owner.
- **No widening of the v1 two-accession guard.** `GOLDEN_AAPL_QUERY_ACCESSIONS` stays `("0000320193-25-000079", "0000320193-26-000020")` (`engine/fundamental_forensics/ixbrl_raw_ledger.py:56-59`). Listing a census accession as `not_retained` does not admit it to the query provider.
- **No engine consumer.** This task adds no loader, scheduler, or engine change.
- **No attestation label.** No row and no reconstruction is labelled `attested`.
- **No purchase or licence bypass.** Dependent R2 research-store release stays blocked on its owner.
- **No invented accession, CIK, date, or metric id.** Uncertain census rows stay uncertain.

Pinning suite: `tests/test_fundamental_forensics_coverage_contract.py`.
