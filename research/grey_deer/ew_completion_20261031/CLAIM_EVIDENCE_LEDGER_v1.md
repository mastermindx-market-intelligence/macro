# Claim-evidence ledger v1 — Grey Deer × Leadership Rotation early-warning forecasts (product B)

This is the research ledger chosen under SD-18 = (ii) + (i)-pointer. Each row is one registered forecast claim: a family and a horizon. GD1 `GD1_CAUSAL_HYPOTHESIS_LEDGER.md` carries only a pointer (`H-EWF`). The field families follow R&V §5 (:57–69). The ledger is research, not a runtime table, a qledger write or a product surface.

Rules for this file:
- **Append only.** A verdict is written once per registered look. A later fact is appended as a new event; an old entry is never edited.
- **Who writes.** The seat's records lane writes every entry after the PR head. A builder or reviewer never writes it.
- **No outcomes before an entry permits them.** Nothing here was derived from an outcome row. The first outcome-derived entry can only be a P1-DEV result (DEVELOPMENT) or a registered P3 look (prereg §8.3).

## 1. Registration pins

| Item | Value |
|---|---|
| Prereg | `research/grey_deer/ew_completion_20261031/EW_FORECAST_PREREG_v1_2026-10-31.md` |
| Prereg blob at the PR head (undated machine lines) | `efc932f221fae18f2e31a72c6b6b1d407601be88` |
| Registered prereg blob (first `main` blob with both machine lines dated; the fingerprint input, X5) | `f6d411e379c3d5d799d7514f96c05a2214453e6e` (dated in the records r3 commit; the first `main` blob with both machine lines dated) |
| Frozen contract | `research/grey_deer/ew_completion_20261031/CLAIM_EVIDENCE_CONTRACT_v1_2026-10-31.md`, blob `5270e309927a8a40eb9e72bbd1bda6907a5fe800` |
| `EW_P3_MERGE_DATE_UTC` / `EW_P3_PROSPECTIVE_START` | 2026-10-31 / 2026-11-02 (first NYSE session strictly after the merge date, `lib/nyse_calendar.py`); earliest first look `L0` = 2027-12-31 (§11.2) |
| Trial-ledger declared budgets (`data/trial_ledger.jsonl`) | `grey_deer_ew_mkt_v1` = 3 and `grey_deer_ew_rs_v1` = 3. APPENDED by the records r3 commit via `scripts/grey_deer_ew_forecast_reader.py --register-families` (two `declared_budget` rows, n = 3 each, appended to the `main` ledger copy; no other row touched). |
| Holm set | m = 2 (`grey_deer_ew_mkt_v1`, `grey_deer_ew_rs_v1`). C-SEC is not in it (prereg §3). |

## 2. How each R&V §5 field family is filled for these claims

| R&V field family | Withholding rule (R&V) | Filled here as |
|---|---|---|
| Claim/model epoch, version, target, horizon | Never pool epochs or relabel market as sector event | `family`, `epoch`, `model_fingerprint`; target `E_MKT` or `E_RS`; h ∈ {5, 10, 21}. One row per (family, h). A new epoch is a new event entry, never pooled. |
| Issued probability vs categorical watch | Probability null for WATCH; no synthetic odds | Issued probability only (product B). The product-A watch is not scored here. |
| Original availability, recorded, issued, served and delivered clocks | UNKNOWN where not witnessed, no backdating | X4: `vendor_available_at` UNKNOWN; `issued_at` first writer wins; `served_at`/`notified_at` NULL; `lead_delivered` undefined. |
| Market, benchmark, GMI member vintage, source rights | Eligibility is not inferred from current constituents or Yahoo data | SPY (C-MKT); SMH/SPY (C-RS); no GMI membership is used. Input vintages are recorded beside the fingerprint. Rights: APPROVED_BY_CHAIRMAN_ATTESTATION. History is RECONSTRUCTED (P-01 open). |
| Outcome onset, label published time, episode cluster | No premature grading or repeated daily pseudo-independent cases | `outcome_onset`, `label_mature_at`, `graded_at`; honest N = RDY :46 clusters. |
| Same-row baseline, proper score, interval and power | No convenient wrong-target comparator | Paired Brier vs the required comparators on identical rows; CMB interval (block = h, 2000 draws, seed 20261031 + h); power artifact `EW_POWER_v1.json`. |
| Original event/revision, account-safe delivery receipt | Preserve correction ancestry and no personal data leak | `corrected_at` with ancestry (SD-17a). No delivery exists, so no receipt is claimed. |

## 3. Claim rows

| Claim | Family | Target, h, role | Required comparators | Descriptive comparators | Clusters / floors | Verdict | Status |
|---|---|---|---|---|---|---|---|
| EWF-MKT-21 | `grey_deer_ew_mkt_v1` | `E_MKT`, h = 21, **primary** | M0, B1 (matched Radar segment, prereg §6.4) | B0, B2 | X7 | none | IMMATURE — registered 2026-10-31 (#10340 squash `11e6c98eb8c3`); no receipted issue yet; earliest first look 2027-12-31 |
| EWF-MKT-10 | `grey_deer_ew_mkt_v1` | `E_MKT`, h = 10, descriptive | — | M0, B0, B1, B2 | X7 | none (descriptive only) | DRAFT |
| EWF-MKT-5 | `grey_deer_ew_mkt_v1` | `E_MKT`, h = 5, descriptive | — | M0, B0, B1, B2 | X7 | none (descriptive only) | DRAFT |
| EWF-RS-21 | `grey_deer_ew_rs_v1` | `E_RS` (δ = 0.05), h = 21, **primary** | B1_RS, B2_RS | B0_RS | X7 + ≥5 ratio clusters, ≥12 adverse outcomes | none | IMMATURE — registered 2026-10-31 (#10340 squash `11e6c98eb8c3`); no receipted issue yet; earliest first look 2027-12-31 |
| EWF-RS-10 | `grey_deer_ew_rs_v1` | `E_RS`, h = 10, descriptive | — | B0_RS, B1_RS, B2_RS | X7 + C-RS floor | none (descriptive only) | DRAFT |
| EWF-RS-5 | `grey_deer_ew_rs_v1` | `E_RS`, h = 5, descriptive | — | B0_RS, B1_RS, B2_RS | X7 + C-RS floor | none (descriptive only) | DRAFT |

Only the two primary rows can take a verdict: VALIDATED, NOT_SUPPORTED, INSUFFICIENT or NOT_EXECUTABLE. The descriptive rows report deltas and never take a verdict.

## 4. Events (append only)

| Date (UTC) | Event | Evidence | Outcome rows read |
|---|---|---|---|
| 2026-10-31 | Prereg and this ledger drafted at the PR head. Contract v1 frozen by the seat's `FROZEN:` reply. | Prereg blob `61043f3f…`, contract blob `5270e309…` | 0 |
| 2026-10-31 | Repair round 1 after independent review V1 (ACCEPT_WITH_FINDINGS on `0f497525`): text-only fixes for V1-F01, F03, F04, F05, F06, F08 and F09. No frozen value changed. F02 (I-3) and F07 (trial-ledger deferral) are left for the seat's merge. | Prereg blob `e492c20a…`, contract blob `5270e309…` (unchanged) | 0 |
| 2026-10-31 | Repair round 2 after independent delta review V1-R2 (ACCEPT_WITH_FINDINGS on `e959e580`): text-only fix for V1R2-F01 (gate 3's calendar years are bound to the prospective window, not a fixed range) and the reviewer's carried I-5 observation (§6.4 now states contract §5 item 4's "current epoch" in the Radar match). No frozen value changed. | Prereg blob `efc932f2…`, contract blob `5270e309…` (unchanged) | 0 |
| 2026-10-31 | CI repair after independent review r3 (ACCEPT_WITH_FINDINGS on `c5f00584`): the reader's repo-root `sys.path` pin moved to module top (import-hygiene check); no prereg or contract text changed. Seat merged #10340 by exact head `3c986e24` → `main` `11e6c98eb8c3`. | Prereg blob `efc932f2…` (unchanged), contract blob `5270e309…` (unchanged) | 0 |
| 2026-10-31 | Dating commit (records r3, prereg §2 "Who dates them"): `EW_P3_MERGE_DATE_UTC` = 2026-10-31, `EW_P3_PROSPECTIVE_START` = 2026-11-02; V1R3-F01 (§13 P-09 names `L0` as the earliest first-look lower bound) and V1R3-F02 (§6.4 Match bullet carries the segment-pair condition) applied as text-only cross-links; declared budgets 3 + 3 appended to `data/trial_ledger.jsonl`. No frozen value changed. | Registered prereg blob `f6d411e3…`, contract blob `5270e309…` (unchanged) | 0 |
