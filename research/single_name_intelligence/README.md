# Single-Name Intelligence (SNI)

## 1. What this tree is

Single-Name Intelligence (SNI, commission 8659) is the research program in this tree: the Alibaba/Tencent reference product, the research-registration and immutable evaluation loop, and the US/Mag-7 generalization. Every artifact here is descriptive research. All authority flags — rank_authority, gate_authority, size_authority, signal_authority, escalation_authority, trade_authority — are false, and code in this tree refuses a caller that sets any of them true. Nothing in this tree feeds a ranker, gate, sizer, signal, escalation, or trade path. Identity ids are caller-supplied opaque strings owned by Stock Identity / Data OS; unknown identity stays UNRESOLVED / null.

## 2. Status at a glance

Status words are copied from the cited file. They are not upgraded. `REGISTERED-GATED` on a protocol row means the design is frozen and maps to an existing qledger primitive, and registration is blocked on register §2 (`S0_PROTOCOL_REGISTER.md` L99); it does not mean a claim is registered. The register also states "No protocol below is registered today" (`S0_PROTOCOL_REGISTER.md` L91) and "No row is registered in qledger today" (`S0_PROTOCOL_REGISTER.md` L129).

| artifact | kind | status as written in its own file | citation |
|---|---|---|---|
| S0 Protocol Register | protocol | S0 FROZEN PROTOCOL. This is a research document only. It implements nothing and registers nothing. | `research/single_name_intelligence/protocols/S0_PROTOCOL_REGISTER.md` L3 |
| S0 Independence Law | protocol | S0 FROZEN PROTOCOL. This is a research document and implements nothing. | `research/single_name_intelligence/protocols/S0_INDEPENDENCE_LAW.md` L3 |
| S0 Split and Contamination Law | protocol | S0 FROZEN PROTOCOL. This is a research document and implements nothing. | `research/single_name_intelligence/protocols/S0_SPLIT_AND_CONTAMINATION_LAW.md` L3 |
| S0 amendment A01 | draft | DRAFT — not registered (`applied:` false) | `research/single_name_intelligence/protocols/S0_AMENDMENT_A01_DRAFT.md` L9, L11 |
| S1 residual v1 (`runs/s1_residual/`) | sealed run | superseded by v1.1 | `research/single_name_intelligence/runs/s1_residual/SUPERSEDED_BY_V1_1.md` L1, L8 |
| S1 residual v1.1 (`runs/s1_residual_v1_1/`) | reprint | v1.1; HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met. Sealed BEFORE any outcome. | `research/single_name_intelligence/runs/s1_residual_v1_1/VERSION_RECORD.json` (`version`); `research/single_name_intelligence/runs/s1_residual_v1_1/SEAL_AND_BUDGET.md` L3 |
| S2 event-response v1 (`runs/s2_event_response/`) | sealed run | superseded by v1.1 | `research/single_name_intelligence/runs/s2_event_response/SUPERSEDED_BY_V1_1.md` L1, L7 |
| S2 event-response v1.1 (`runs/s2_event_response_v1_1/`) | reprint | study_version v1.1; HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met | `research/single_name_intelligence/runs/s2_event_response_v1_1/VERSION_RECORD.json` (`study_version`); `research/single_name_intelligence/runs/s2_event_response_v1_1/SEAL_AND_BUDGET.md` L5 |
| P04 v2 prereg | draft | DRAFT — not registered | `research/single_name_intelligence/event_response/P04_V2_PREREG_DRAFT.md` L9 |
| A8 US residual-transfer prereg | draft | DRAFT — not registered | `research/single_name_intelligence/us_transfer/A8_US_RESIDUAL_TRANSFER_PREREG_DRAFT.md` L21 |
| Evaluation registration ledger | draft | DRAFT — not registered (`registered: false`) | `research/single_name_intelligence/evaluation/REGISTRATION_LEDGER_DRAFT.md` L1, L3 |
| U0 reference journey and wire contract | draft | DRAFT — not registered | `research/single_name_intelligence/SNI_U0_REFERENCE_JOURNEY_AND_WIRE_CONTRACT_DRAFT.md` L3 |
| US/Mag-7 science stress set | draft | DRAFT — not registered (SNI-local draft contract; not a product surface, registration, or seal) | `research/single_name_intelligence/us_stress/README.md` L9, L20 |
| `common/sni_inference.py` | library | SNI-local DRAFT inference contract | `research/single_name_intelligence/common/sni_inference.py` (module docstring) |
| `common/sni_seal.py` | library | SNI-local DRAFT seal contract (`sni_seal.v1`) | `research/single_name_intelligence/common/sni_seal.py` (module docstring) |
| `evaluation/sni_eval_ledger.py` | library | SNI-local DRAFT evaluation registration ledger | `research/single_name_intelligence/evaluation/sni_eval_ledger.py` (module docstring) |
| `tests/test_sni_*.py` | test set | 45 files; names in §5 | `tests/test_sni_*.py` |

Qualification and decision records (admitted assessment while R1 is gated: E0, M0, V0, U0 — `e2e_20261011/SNI_PROGRAM_CONTINUATION_2026-10-11.md` L10). These are not protocol rows, sealed runs, reprints, or unregistered study drafts.

| artifact | kind | status as written in its own file | citation |
|---|---|---|---|
| E0 issuer evidence qualification | draft | qualification facts about existing owners | `research/single_name_intelligence/SNI_E0_ISSUER_EVIDENCE_QUALIFICATION_2026-10-11.md` L6 |
| M0 market-data qualification | draft | qualification facts about existing owners | `research/single_name_intelligence/SNI_M0_MARKET_DATA_QUALIFICATION_2026-10-11.md` L6 |
| V0 evaluation support matrix | draft | V0 DECISION INPUT. This document decides; it implements nothing. | `research/single_name_intelligence/SNI_V0_EVALUATION_SUPPORT_MATRIX.md` L3 |
| V0 evaluation extension decision | draft | V0 DECISION (one recommendation). Nothing in this document is implemented. | `research/single_name_intelligence/SNI_V0_EXTENSION_DECISION.md` L3 |
| V0 collision check vs PR #8042 | draft | V0 DECISION input. Read-only analysis; this document edits nothing and touches no PR. | `research/single_name_intelligence/SNI_V0_8042_COLLISION_CHECK.md` L3 |
| U0 Company Intelligence reuse map | draft | U0 DECISION input (product/integration owner). Read-only. Nothing here is implemented. | `research/single_name_intelligence/SNI_U0_COMPANY_INTELLIGENCE_REUSE_MAP.md` L3 |
| U0 composition seam decision | draft | DECISION (U0 product/integration owner). Nothing is implemented here; P0 implements. | `research/single_name_intelligence/SNI_U0_COMPOSITION_SEAM_DECISION.md` L3 |
| E1 Alibaba evidence pack | draft | this pack is qualification evidence only | `research/single_name_intelligence/evidence/Alibaba/E1_EVIDENCE_PACK_2026-10-11.md` L8 |
| E2 Tencent evidence pack | draft | owner-native evidence pack; all authority flags in the coverage JSON are false | `research/single_name_intelligence/evidence/Tencent/E2_EVIDENCE_PACK_2026-10-11.md` L1, L6 |
| E1 / E2 adversarial cases | draft | seven required probes against owner output (as-of 2026-10-11) | `research/single_name_intelligence/evidence/Alibaba/E1_ADVERSARIAL_CASES_2026-10-11.md` L1; `research/single_name_intelligence/evidence/Tencent/E2_ADVERSARIAL_CASES_2026-10-11.md` L1 |
| Seat continuation ledger | draft | seat continuation ledger (Fable seat 508c3757, 2026-10-11) | `research/single_name_intelligence/e2e_20261011/SNI_PROGRAM_CONTINUATION_2026-10-11.md` L1 |

The second table uses kind `draft` only as the index class for records that are not a sealed run, reprint, S0 protocol, code library, or test set. The status column is the claim: E0/M0/V0/U0 are admitted qualification and decision records (`SNI_PROGRAM_CONTINUATION_2026-10-11.md` L10). They are not unregistered study drafts. Unregistered study drafts stay "DRAFT — not registered" in the first table.

Places where two files in this tree disagree about a status:

- `research/single_name_intelligence/protocols/S0_PROTOCOL_REGISTER.md` L129 says four rows "carry REGISTERED-GATED: P01 … and P04, P05 and P06". The Status column at L115 (P01) and L118 (P04) is `RETIRED-CONTAMINATED` with prior status REGISTERED-GATED. P05 L119 and P06 L120 remain REGISTERED-GATED on the US leg.
- `research/single_name_intelligence/runs/s2_event_response/REPORT.md` L17 (and L136, L166, L196) says successor "P04 v2 — not drafted". `research/single_name_intelligence/event_response/P04_V2_PREREG_DRAFT.md` L9 says Status is DRAFT. `research/single_name_intelligence/protocols/S0_AMENDMENT_A01_DRAFT.md` L34 points at that draft (`applied:` false at L11). The frozen register §7 successor cell is still "— (none registered)" (`S0_PROTOCOL_REGISTER.md` L324); S2 v1.1 `REPORT.md` L13 and L77 match that cell.
- `research/single_name_intelligence/runs/s1_residual_v1_1/SEAL_AND_BUDGET.md` L1 and L5 still title the reprint "s1_residual v1" / "vv1". `research/single_name_intelligence/runs/s1_residual_v1_1/VERSION_RECORD.json` carries `"version": "v1.1"`.

## 3. Registered split and horizons

Citation lines are in the protocol register. The split law table is the companion that the register's "Time-axis split" term names.

- **TRAIN** `s` < 2024-01-01 — register L110; split law L39.
- **TUNE** [2024-01-01, 2026-10-01) — register L110 (`TUNE [2024-01-01, 2026-10-01)`); split law L40 (`2024-01-01 ≤ s < 2026-10-01`).
- **QUARANTINE** `s` ≥ 2026-10-01 — register L110 (`QUARANTINE otherwise for s ≥ 2026-10-01`); split law L42.
- **TEST** is prospective claims only, after the S0 freeze and after register §2 — register L110.
- **Horizons** 5 / 21 / 63 — register L107 (`GRADE_HORIZONS` = 5/21/63, unit `HORIZON_UNIT_TRADING`).

Register §2 (`S0_PROTOCOL_REGISTER.md` L71): no SNI claim may be registered until the named gates have landed. QUARANTINE is listed and counted and is never analysed (`S0_SPLIT_AND_CONTAMINATION_LAW.md` L51).

## 4. Directory map

Top-level `SNI_*.md` files at `research/single_name_intelligence/` are the E0/M0 qualification records, U0 reuse map, U0 composition-seam decision, U0 journey draft, and V0 matrix / extension / collision-check records (status in §2).

- `acceptance/` — acceptance evidence matrix (`ACCEPTANCE_EVIDENCE_MATRIX.md` / `.json`) and its renderer `render_matrix.py`. Row status is evidence bookkeeping, not acceptance by the commissioning authority.
- `common/` — shared SNI-local draft libraries `sni_inference.py` and `sni_seal.py`.
- `e2e_20261011/` — seat continuation ledger `SNI_PROGRAM_CONTINUATION_2026-10-11.md`. E0/M0 cite `e2e_20261011/MASTERPLAN.md`; that path is not in this tree.
- `evaluation/` — R1-gated draft ledger spec `REGISTRATION_LEDGER_DRAFT.md` and `sni_eval_ledger.py`; `seal_full_check.py` regenerates every sealed S1/S2 v1.1 output from its pinned inputs and compares it with the sealed bytes (verification only, it writes nothing into `runs/`).
- `event_response/` — S2 study modules (P04–P06) plus P04 v2 prereg draft (`P04_V2_PREREG_DRAFT.md` / `.json`).
- `evidence/` — Alibaba E1 and Tencent E2 owner-native packs, coverage JSON, and adversarial cases.
- `protocols/` — frozen S0 register, independence law, and split/contamination law; unapplied A01 draft (`S0_AMENDMENT_A01_DRAFT.md` / `.json`).
- `residual/` — S1 study modules (P01–P03). Its git tree sha is pinned as `code_tree_sha` in the S1 v1.1 `REPORT.md`, so any byte change here breaks S1 v1.1 `--check`.
- `reviews/` — dated review receipts (program invariants, public exposure, quarantine fence, seal coverage, S2 v1.1 red-team, cross-host re-execution, A20 injection safety).
- `runs/` — sealed study trees: `s1_residual/` (superseded by v1.1), `s1_residual_v1_1/`, `s2_event_response/` (superseded by v1.1), `s2_event_response_v1_1/`.
- `us_stress/` — Mag-7 science stress-set draft contract, `stress_set.py`, and seven profile drafts under `profiles/`.
- `us_transfer/` — A8 US residual-transfer prereg draft (`A8_US_RESIDUAL_TRANSFER_PREREG_DRAFT.md` / `.json`) and `a8_draft_loader.py`.

Sibling contract schemas (outside this directory, listed because SNI files pin them): `contracts/single_name_intelligence/coverage_profile.v1.schema.json`, `contracts/single_name_intelligence/sni_seal.v1.schema.json`.

## 5. Tests

Group of `tests/test_sni_*.py` (45 files).

**S1**

- `test_sni_s1_challenger.py`
- `test_sni_s1_cli.py`
- `test_sni_s1_decomposition.py`
- `test_sni_s1_info_leak.py`
- `test_sni_s1_language.py`
- `test_sni_s1_ledger_order.py`
- `test_sni_s1_manifest.py`
- `test_sni_s1_mirror.py`
- `test_sni_s1_property.py`
- `test_sni_s1_report_order.py`
- `test_sni_s1_seal_integrity.py`
- `test_sni_s1_stats.py`
- `test_sni_s1_v1_1_hardening.py`
- `test_sni_s1_v1_2_hash_invariant.py`

**S2**

- `test_sni_s2_abstain.py`
- `test_sni_s2_cli.py`
- `test_sni_s2_clock.py`
- `test_sni_s2_collapse.py`
- `test_sni_s2_info_leak.py`
- `test_sni_s2_language.py`
- `test_sni_s2_ledger_order.py`
- `test_sni_s2_mirror.py`
- `test_sni_s2_property.py`
- `test_sni_s2_report_order.py`
- `test_sni_s2_seal_integrity.py`
- `test_sni_s2_selection.py`
- `test_sni_s2_stats.py`
- `test_sni_s2_v1_1_hardening.py`

**common**

- `test_sni_common_inference.py`
- `test_sni_common_seal.py`

**evaluation**

- `test_sni_eval_ledger.py`

**drafts**

- `test_sni_a8_us_transfer_draft.py`
- `test_sni_p04_v2_draft.py`
- `test_sni_s0_amendment_a01_draft.py`

**US stress**

- `test_sni_us_stress.py`
- `test_sni_us_stress_onboarding.py`
- `test_sni_us_stress_then_known.py`

**program guards** (cross-cutting; not tied to one study)

- `test_sni_acceptance_matrix.py`
- `test_sni_common_equivalence.py`
- `test_sni_injection_safety.py`
- `test_sni_program_invariants.py`
- `test_sni_public_exposure.py`
- `test_sni_quarantine_fence.py`
- `test_sni_run_seal_repro.py`
- `test_sni_seal_full_check.py`

## 6. What is NOT here / not authorised

No registration has been lifted. The registration gate is a Chairman decision recorded outside this tree (register §2 at `S0_PROTOCOL_REGISTER.md` L69–L71; continuation ledger D1 at `e2e_20261011/SNI_PROGRAM_CONTINUATION_2026-10-11.md` L8). There is no forecast. There is no trade sizing. There is no canonical identity minting; identity ids are owner-supplied. Private full text never lives here. Fixtures, where any exist under this tree, are synthetic.

## 7. How to add a study

A new study is a new protocol row (or a successor version of an existing row) under the frozen register `research/single_name_intelligence/protocols/S0_PROTOCOL_REGISTER.md`, including its split, horizon, independence, and retirement rules and the §2 registration gate. Descriptive statistics and seals reuse the shared libraries `research/single_name_intelligence/common/sni_inference.py` and `research/single_name_intelligence/common/sni_seal.py`. This README does not add a process beyond those files.
