# A8 US residual-transfer pre-registration DRAFT

This is an SNI-local DRAFT contract. It consumes owner-supplied values from
Data OS identity, Company Event/Earnings, FIF, Capital Structure, Stock
Identity, Options, Research Vault, and qledger/Evaluation. It does not
re-implement those owners. Identity ids are caller-supplied opaque strings;
unknown identity stays UNRESOLVED / null.

**Cohort disclosure (HINDSIGHT):** `cohort.selection` = `HINDSIGHT — 2026 market-cap leaders`; `cohort.survivorship` = true. The seven names were chosen knowing they became the largest US companies. Any result on them is a STRESS test of the METHOD's mechanics (does it run, abstain, count and disclose correctly), never evidence that a residual effect transfers, never representative of "US large caps". The bridge required to make a transfer claim is a point-in-time, outcome-free cohort rule (for example top-N by then-known market cap at each split start). Status: **NOT SUPPORTED — BRIDGE REQUIRED** (no PIT market-cap owner admitted).

This draft registers nothing; registration is gated by S0 register §2 and the R1 Chairman gate.

Drafted by grok-4.6 lane A8 under seat 508c3757 at 2026-10-13T03:10:00Z.

**Status:** `DRAFT`
**Family id:** `sni.us_transfer.RESID-DIR-US`
**Names:** `AAPL`, `AMZN`, `GOOGL`, `META`, `MSFT`, `NVDA`, `TSLA`
**Horizons:** `5`, `21`, `63`
**Declared budget:** `21`
**Version:** `v0-draft`
**registered:** false
**outcome:** none

This study writes the frozen P01 residual design applied to seven other US names. It is not P07 (P07 is EVT-RESPONSE-WINDOW, intraday, procurement-gated). Surfaces never claim forecast skill, never claim a calibrated probability, and never claim transfer shown. This draft is not validated as confirmatory evidence.

## 1. Status

- **Status:** DRAFT
- **registered:** false
- **outcome:** none
- **version:** `v0-draft`
- **drafted_by:** grok-4.6 lane A8 under seat 508c3757
- **drafted_at:** 2026-10-13T03:10:00Z (explicit Z)
- **Registration sentence:** This draft registers nothing; registration is gated by S0 register §2 and the R1 Chairman gate.

v0-draft is unregistered. No Mag-7 residual result is computed here. Computing outcomes before this prereg is frozen would contaminate the transfer study. The S0 protocol register is not edited. Nothing is sealed.

## 2. Family and cells

**Family id:** `sni.us_transfer.RESID-DIR-US`

One cell per (name, horizon): 7 names × h ∈ {5, 21, 63} = 21 cells.

**Arms:** HISTORICAL-DESCRIPTIVE (TRAIN/TUNE per SL §2) only is open. The PROSPECTIVE arm is named but not opened and contributes 0 trials.

Open arm × cells = 21 × 1 = 21 declared trials.

## 3. Design copied from P01 v1

Copied from `research/single_name_intelligence/residual/s1_prereg.py` by citation of its STRUCTURE (`S0_BLOBS`, `INPUT_PINS`, `ENGINE_CITATIONS`, frozen decisions) and decision ids D1, D3, D4, D5, D9, D10, D11, D12, D14 and `kill_hold_rule`. Subject and bench are the only substitutions. Residual construction, horizons, split boundaries, purge, unit-independence rule, null, and kill/retirement stay the P01 v1 rules.

**Residual construction (P01 / s1_prereg.py protocols.P01):** excess = subject_ret − bench_ret, simple returns on the owner's split-adjusted TR close (`grade_claim` convention, qledger L2698). Hit = (sign(excess) == direction); excess == 0 exactly → non-hit, listed as a tie; direction 0 → ABSTAIN (listed, not a hit, not a miss).

**Baselines (frozen, P01):** (i) always-long (+1); (ii) sign of the trailing 63-session excess at D(s).

**Horizons:** 5/21/63 trading sessions (`GRADE_HORIZONS` qledger L114; `HORIZON_UNIT_TRADING` L141).

**Split boundaries (SL §2, copied):** TRAIN s < 2024-01-01; TUNE [2024-01-01, 2026-10-01); QUARANTINE s ≥ 2026-10-01. TEST is prospective-only; the PROSPECTIVE arm is not opened.

**Purge, per h (SL §2):** TRAIN purged when the last session of W_h is on or after 2024-01-01; TUNE purged when the last session of W_h is on or after 2026-10-01. Purged units keep their label, are counted visibly, and are never moved.

**Unit-independence rule:** IL §3 step 7 (REG §3 fixed term "Unit independence"): honest-N = distinct non-overlapping units.

**Pre-registered null (verbatim from the P01 register row, S0_PROTOCOL_REGISTER.md L115):** H0₁: hit rate = 0.50 per horizon. H0₂: median excess = 0.

**Retirement rule (verbatim from the P01 register row, S0_PROTOCOL_REGISTER.md L115):** Visible retirement

"Visible retirement" is the REG §3 fixed term meaning SL §8: one `TrialLedger().log_trial(...)` row plus one REG §7 row; status RETIRED-CONTAMINATED; the successor is a new version; nothing is ever refilled.

**Kill / continue (P01 detail block):** Continue as a gated descriptive registration. The protocol becomes RETIRED-SUPERSEDED (a new version) if, 24 months after its first prospective registration, fewer than 20 units have matured and no cohort successor row exists. It is never re-scoped in place. A failed pre-declared criterion prints KILL/HOLD-AS-RESEARCH; it is never rescued by changing the target, cohort or horizon.

## 4. Bench per name

**Primary** = SPY (same-market broad). Pin: `data/yahoo/SPY.parquet` blob `9b306b50884279e4155030298627faa26e5c6d9a`. First-trade date: NOT VERIFIED (parquet not opened). Units before the owner's then-known first SPY bar ABSTAIN with reason `bench_not_then_known`.

**Secondary** sector bench, declared only where the ETF parquet exists in the origin/main listing:

| Name | Secondary | Parquet on origin/main | Then-known window | Treatment |
|---|---|---|---|---|
| AAPL | XLK | yes (`c1c8a9f06d1bc4ec95fa1065e20d3f3a347d1de5`) | first bar NOT VERIFIED | ABSTAIN `bench_not_then_known` before owner's first bar |
| MSFT | XLK | yes (same blob) | first bar NOT VERIFIED | same |
| NVDA | XLK | yes (same blob) | first bar NOT VERIFIED | same |
| AMZN | XLY | yes (`c0dc88479674fd4d4d69818083cdea26e8c348f1`) | first bar NOT VERIFIED | ABSTAIN `bench_not_then_known` before owner's first bar |
| TSLA | XLY | yes (same blob) | first bar NOT VERIFIED | same |
| GOOGL | XLC | yes (`bc217972a261a8fa6d77439cc685b4aae2513bf6`) | valid from 2018-06-19 | units with s < 2018-06-19 ABSTAIN `bench_not_then_known` |
| META | XLC | yes (same blob) | valid from 2018-06-19 | units with s < 2018-06-19 ABSTAIN `bench_not_then_known` |

No declared secondary ETF is missing from the listing, so no secondary leg is file-`UNAVAILABLE`. The then-known gap is the **XLC window** for GOOGL and META: XLC began trading 2018-06-19, so the XLC leg does not exist for most of TRAIN (s < 2024-01-01). Cells' units outside that window ABSTAIN with reason `bench_not_then_known`. Never back-fill with a later-created ETF or a constituent reconstruction.

FB.parquet is absent from the listing (identity flag, not a bench). GOOG.parquet is present and is not a subject pin.

## 5. Then-known identity flags

Each row has `fact`, `effective_date_or_null`, `source`, `treatment`. Dates that cannot be cited from a repository path are recorded with source `NOT VERIFIED — owner corporate-action feed required`.

| fact | effective_date_or_null | source | treatment |
|---|---|---|---|
| FB to META ticker change | null | NOT VERIFIED — owner corporate-action feed required | Display label META. FB.parquet absent. Do not stitch FB history onto META. Identity UNRESOLVED. Without an owner mapping, units whose then-known ticker is not the display label ABSTAIN `symbol_not_then_known`. |
| GOOG/GOOGL share-class split (Class C created; GOOGL symbol from that date) | null | NOT VERIFIED — owner corporate-action feed required | Subject display label GOOGL. GOOG.parquet is not a subject. Do not reconstruct GOOGL before the owner's then-known GOOGL-symbol date. ABSTAIN `symbol_not_then_known`. Do not mint ids from GOOG vs GOOGL. |
| TSLA IPO 2010-06-29 (no history before it) | 2010-06-29 | NOT VERIFIED — owner corporate-action feed required | Frozen-design date pending owner confirmation. Units with s before the owner's then-known first TSLA bar ABSTAIN `subject_not_then_known`. |
| Share splits (adjusted-return requirement) | null | NOT VERIFIED — owner corporate-action feed required | Returns must come from the owner's split-adjusted series. A split-day test must exist before any run. A run without both ABSTAINS `adjustment_unverified`. |
| XLC began trading 2018-06-19 | 2018-06-19 | NOT VERIFIED — owner corporate-action feed required | GOOGL/META XLC secondary leg valid only for s ≥ 2018-06-19; earlier units ABSTAIN `bench_not_then_known`. |
| XLK first-trade date over TRAIN | null | NOT VERIFIED — owner corporate-action feed required | Parquet present; first bar unknown (file not opened). ABSTAIN `bench_not_then_known` before owner's first bar. |
| XLY first-trade date over TRAIN | null | NOT VERIFIED — owner corporate-action feed required | Same treatment as XLK. |
| SPY first-trade date over TRAIN | null | NOT VERIFIED — owner corporate-action feed required | Same treatment as XLK. |

## 6. Cohort disclosure

**selection** = `HINDSIGHT — 2026 market-cap leaders`

**survivorship** = true

The seven names were chosen knowing they became the largest US companies. Any result on them is a STRESS test of the METHOD's mechanics (does it run, abstain, count and disclose correctly). It is never evidence that a residual effect transfers. It is never representative of "US large caps".

**Bridge required to make a transfer claim:** a point-in-time, outcome-free cohort rule (for example top-N by then-known market cap at each split start).

**Bridge status:** NOT SUPPORTED — BRIDGE REQUIRED (no PIT market-cap owner admitted).

## 7. Budget and multiplicity

**Declared budget** = 21 cells × 1 open arm = **21** trials, to be written via `TrialLedger.log_declared_budget` at registration time (cite `engine/trial_ledger.py` L204). This draft does not call it.

**Multiplicity:** Holm across the 21 cells for any TESTED label. Family α = 0.05.

**Per-cell labels** follow the SNI inference label rule: TESTED / DESCRIPTIVE_ONLY / ABSTAIN, with min clusters ≥ 2 and honest-N = distinct non-overlapping units (IL §3 step 7). An unestimable family ABSTAINS with a named reason; never a default 50/50 fill (A25). Holm applies only to cells labelled TESTED.

## 8. Grading language

qledger `grade_claim` (L2698) directional only; maturity via `_matured_window` (L2607). Any surface says "direction right/wrong over N matured beliefs". N is IL honest-N. A residual or stress statistic is DESCRIPTIVE, never causal, never news impact (A24).

## 9. Identity

Every name carries `canonical_issuer_id: null`, `security_id: null`, `issuer_link: UNRESOLVED`, and the ticker only as a display label. Never construct an id from a ticker, name, CIK, FIGI or ISIN. Identity ids are owned by Stock Identity / Data OS. The same four fields are repeated on every cell.

## 10. Authority

`rank_authority`, `gate_authority`, `size_authority`, `signal_authority`, `escalation_authority`, and `trade_authority` are all false at top level and repeated false on every cell. A caller that sets any of them true is refused (raise). Nothing in this draft feeds a ranker, gate, sizer, signal, escalation path, or trade path.

## 11. INPUT_PINS

Pins are blob shas from `git ls-tree origin/main`. Files are never opened. `data_read` is false.

**S0 blobs**

| key | path | blob |
|---|---|---|
| REG | research/single_name_intelligence/protocols/S0_PROTOCOL_REGISTER.md | `a0b5cc584a4414ac85ff4cd56616fe23254f595f` |
| IL | research/single_name_intelligence/protocols/S0_INDEPENDENCE_LAW.md | `6ec4b097ce3fd24261da12061b3418fde945efaf` |
| SL | research/single_name_intelligence/protocols/S0_SPLIT_AND_CONTAMINATION_LAW.md | `c06a91beee22626eab1912aaa8a3baa6856913a2` |

**Subject and bench parquets**

| path | blob |
|---|---|
| data/yahoo/AAPL.parquet | `ede863448ed9f92ab403a0e2ea157da186c64b20` |
| data/yahoo/AMZN.parquet | `989989b5ba05ab49b72268ccb62916c3f30b59a9` |
| data/yahoo/GOOGL.parquet | `31d5f42a503c874e2fe7252971572b7cb227d3ac` |
| data/yahoo/META.parquet | `71d378220da19fedb4d364195803deaa45c14e50` |
| data/yahoo/MSFT.parquet | `065060f3ff59f3aba582f4030c110d9a815c79b4` |
| data/yahoo/NVDA.parquet | `e20a4a573295c752dcfc59d80bf8d9f75c5a27e5` |
| data/yahoo/TSLA.parquet | `ece9542a3ae4a06cdd3c495aea8a936b9370a47e` |
| data/yahoo/SPY.parquet | `9b306b50884279e4155030298627faa26e5c6d9a` |
| data/yahoo/XLK.parquet | `c1c8a9f06d1bc4ec95fa1065e20d3f3a347d1de5` |
| data/yahoo/XLY.parquet | `c0dc88479674fd4d4d69818083cdea26e8c348f1` |
| data/yahoo/XLC.parquet | `bc217972a261a8fa6d77439cc685b4aae2513bf6` |

**Engine citations (origin/main grep, not called):** qledger `GRADE_HORIZONS` L114, `HORIZON_UNIT_TRADING` L141, `grade_claim` L2698, `_matured_window` L2607; trial_ledger `TrialLedger` L66, `log_declared_budget` L204; grading_stats `wilson_ci` L56.

## What this draft does not do

- It does not register, seal, or write a trial-ledger budget row.
- It does not compute a residual, hit rate, or interval.
- It does not edit S0 files, `data/`, `engine/`, or existing SNI research files outside the four owned paths.
- It does not mint identity ids.
- It does not open the PROSPECTIVE arm.
- It does not treat the hindsight Mag-7 list as a then-known cohort.

## Registration checklist

The registration gate is not met. Registration requires, in order:

1. Seat review of this draft.
2. S0 register §2 gate open.
3. The R1 Chairman gate.
4. A REG §6 membership seal row (not minted here).
5. `TrialLedger.log_declared_budget(21)` at registration time (L204; not called here).

Until those are done, this file remains a draft: unregistered, unsealed, and without an outcome.
