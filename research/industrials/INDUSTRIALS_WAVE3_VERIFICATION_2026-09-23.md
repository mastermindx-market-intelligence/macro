# Industrials Wave 3 - Verification and limits

23 September 2026. Operation `gmi-industrials-sector-research-20260923-sol-001`. Macro Draft/HOLD PR #7789. Research evidence and proposed design only; final Fable handoff withheld.

## Executed checks

Command: `python verify_wave3_research.py`, run locally with the files in this directory. Latest complete run: **62 PASS, 0 FAIL**, exit 0.

The suite comprises 32 arithmetic/scenario checks, five invalid-input checks, fourteen deliberately incompatible comparison fixtures, one matching positive control, and ten document-integrity checks. The comparator is a narrow authored research fixture, not an implementation of a production admission gate. The 34 W3-T application cases in the economic model are proposed requirements, not executed application tests.

The initial run had one failed expected-value assertion for the broker AGP-denominator margin. Independent Decimal arithmetic on 255.743 / 737.966 * 100 established 34.655119612556676; the hard-coded expected number had been transcribed incorrectly. The expected value was corrected without changing source inputs or loosening tolerance. The entire suite then passed, and was rerun after immutable readback with the same result. This was a test-constant defect, not a discovered change in company economics.

## Immutable-byte verification

At commit `738347e3d5462bcca40828cda8e48b22e56e2114`, all four following GitHub file blobs exactly matched Git blobs calculated from the executed local UTF-8 files:

| Artifact | Bytes | Git blob |
|---|---:|---|
| `INDUSTRIALS_WAVE3_ECONOMIC_MODEL_2026-09-23.md` | 40033 | `49f4452c86237b1a80c1e879e12394819106f728` |
| `INDUSTRIALS_WAVE3_ASSET_MARKET_EVIDENCE_2026-09-23.md` | 6248 | `fd134d7818b53aa90ecb1a52aff5b38ad81c0b7e` |
| `calculate_wave3.py` | 6792 | `d44e1a2718ba342879b326f6a04e0d0e5f859b60` |
| `verify_wave3_research.py` | 8480 | `6d738f0fbd0b9b256ee13eb1bb320a7af4c5e166` |

The first 27-source evidence register was separately read back at `e37a0b1795e377582695eac33f13818a31f9b6e1`, blob `c0814bf4c24d9c8153ec70009fc24c7e52aba1ad`. It was not redownloaded through the container and no local exact-copy claim is made for it.

The calculator generates `INDUSTRIALS_WAVE3_CALCULATIONS_2026-09-23.json`; the verifier generates `INDUSTRIALS_WAVE3_LOCAL_CHECKS_2026-09-23.json`. These generated outputs are included in the portable package, not committed as additional authoritative datasets. The committed source scripts reproduce them.

## Research coverage and limitations

The economic model contains 5659 whitespace-delimited words, 24 proposed research slices, nine proposed rerating mechanisms and 34 proposed application acceptance cases. The main evidence register plus asset-market supplement contain 31 source records. Multiple records from one issuer or overlapping regional surveys are not independent corroboration. These counts describe coverage, not investment advantage or complete sector research.

No independent factual review, current company valuation, licensed point-in-time consensus/price panel, empirical backtest, forecast calibration, application test, CI acceptance, deployment or browser proof is claimed. No live basket, ranking, entry, size, trade, provider subscription, private production curation or raw vendor corpus changed.

Unresolveds remain visible: Sunbelt's internal ending-versus-average OEC definition conflict; Fastenal's indexed-only release text; AGCO dealer-unit geographic comparability; unexplained Old Dominion component residual; revised Komtrax and lender sample populations; category-average versus constant-quality used prices; missing transaction-level rights/history; customer-specific credit and replacement probabilities; full-lifecycle maintenance/capital attribution.

The next domain unit is aerospace original equipment versus aftermarket economics. The longitudinal and data-feasibility obligations above remain part of the research program and must not disappear from the final Fable specification. Preserve Wave 1, canonical Wave 2, W2X and this Wave 3 rather than repeating their source sweeps.
