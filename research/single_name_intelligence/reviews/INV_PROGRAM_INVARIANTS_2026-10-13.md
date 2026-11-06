# SNI program invariants — 2026-10-13

Tree-wide tripwire on INT1 head `040b61c32fc7d1be1f9b0f22d03f6a43540a4fe5`.
Scanner consumes owner-supplied ids from Data OS / Stock Identity
(`data/reference/security_master.parquet`); it never mints identity ids and
does not feed a ranker, gate, sizer, signal, escalation, or trade path.

## Summary

| Measure | Count |
|---|---|
| Files read | **115** (json 79, yml 7, yaml 0, py 29) |
| Authority-flag occurrences checked | **529** |
| Identity-id values checked | **309** |
| Secret-shape hits | **0** |
| Violations | **none** |
| `SKIPPED` | empty (no scanned file > 20 MB) |
| `ALLOWED_SPLIT_DEVIATIONS` | empty |
| `ALLOWED_HORIZON_DEVIATIONS` | empty |
| Pytest | 7 passed, wall **1.15 s** (pytest 0.93 s) |

JSON Schema `{"const": false}` on an authority flag is the schema form of
required-false and is counted as checked. Unknown identity is `null` /
`UNRESOLVED`. Integer `GRADE_HORIZONS: 114` engine line pins are citations,
not horizon sequences.

## Declarations found

**Split law (S0 §2: TUNE start 2024-01-01, QUARANTINE start 2026-10-01)**

| Path | Key | Value |
|---|---|---|
| `event_response/s2_seal.py` | `SPLIT_TUNEE_START` / `SPLIT_QUARANTINE_START` | 2024-01-01 / 2026-10-01 |
| `event_response/s2_seal.py` | TRAIN / TUNE / QUARANTINE | `s < 2024-01-01` / `2024-01-01 <= s < 2026-10-01` / `s >= 2026-10-01` |
| `residual/s1_manifest.py` | `TRAIN_END` / `TUNE_END` | 2024-01-01 / 2026-10-01 |
| `residual/s1_prereg.py` | train / tune / quarantine | same window + purge `>= 2024-01-01` / `>= 2026-10-01` |
| `runs/s1_residual{,_v1_1}/PREREG_SPEC.json` | `splits.train/tune/quarantine` + purge | same |
| `runs/s2_event_response{,_v1_1}/PREREG_SPEC.json` | `splits.TRAIN/TUNE/QUARANTINE` | same |
| `us_transfer/A8_US_RESIDUAL_TRANSFER_PREREG_DRAFT.json` | `splits.train/tune/quarantine` + purge | same |
| `event_response/P04_V2_PREREG_DRAFT.json` | TRAIN / QUARANTINE | `s < 2024-01-01` / `s >= 2026-10-01` |
| `event_response/P04_V2_PREREG_DRAFT.json` | TUNE | **EMPTY** (v2 membership; no moved date; TRAIN/QUARANTINE still match §2) |

Non-date `train` strings (`TRAIN is never retired`, `info_leak_predicate.train`)
were listed by the leaf-key matcher and carry no boundary date.

**Horizons (must be [5, 21, 63])**

| Path | Key | Value |
|---|---|---|
| `event_response/s2_seal.py` | `GRADE_HORIZONS` | [5, 21, 63] |
| `residual/s1_prereg.py` | `HORIZONS` | [5, 21, 63] |
| `event_response/P04_V2_PREREG_DRAFT.json` | `horizons` | [5, 21, 63] |
| `runs/s1_residual{,_v1_1}/PREREG_SPEC.json` | `protocols.P01/P02.horizons` | [5, 21, 63] |
| `us_transfer/A8_US_RESIDUAL_TRANSFER_PREREG_DRAFT.json` | `horizons`, `p01_copy.horizons` | [5, 21, 63] |

## Violations

none

## Skips

none — `SKIPPED` is empty; pandas/pyarrow/yaml present; parquet on disk.
Positive control (tmp_path): `trade_authority: true` YAML, `SEC:US-XNAS-FAKE`
JSON, `AUTHORITY_FLAGS = {"rank": True}` py, QUARANTINE `2026-09-01` JSON,
horizons `[5, 20, 63]` JSON — each reported.
