# Industrials Wave 9 - Verification and limits

Research cutoff: 23 September 2026. Operation: `gmi-industrials-sector-research-20260923-sol-001`. Macro Draft/HOLD PR #7789. Principal research and proposed requirements, not a final Fable handoff.

## Executed checks

`python verify_wave9.py --snapshot <authorized-local-copy>` completed before and after immutable publication readback with **28 passed, 0 failed**, exit 0. Of these, 21 are package/catalog/diagnostic checks; the seven additional checks re-read the exact native snapshot and compare its digests, footer/column validation, timestamp distribution, nulls, histories and selected row/absence results. `python verify_wave9.py` without the undistributed snapshot separately returned **21 passed, 0 failed**. Those default 21 overlap the 28 and are not added again as independent coverage.

`python -m unittest -v test_wave9_snapshot_helpers` returned **6 tests passed**, separate from the 28 package checks. The six component tests originally failed against empty helper implementations and then passed after implementation. When packaging renamed the helper module, one test-import attempt failed because it still used the old module name. The import was corrected, with no changes to input values, expected values or tolerances, and both the helper suite and complete snapshot/package checks were rerun successfully.

The exact file was recovered by the native GitHub base64 read, decoded, and matched to its Git blob and SHA-256. All six decoded columns matched footer counts, null counts, minima/maxima and page boundaries; source ticker labels were unique. These are authored helper and internal file-consistency checks, not a standard-engine independent cross-check or independent factual review. No current production data-health verdict is inferred.

## Immutable-byte verification

Containing commit: `5b2fd0f9a6984991296ee7e0ce417759ce469d9a`. The audit's first immutable readback was at `ff665f911408ded64ea904e8e08136402b027085`; the other six files were read at the containing commit. All native Git blobs matched the executed local files exactly:

| Artifact | UTF-8 bytes | Git blob |
|---|---:|---|
| `INDUSTRIALS_WAVE9_HISTORICAL_DATA_AUDIT_2026-09-23.md` | 9,696 | `f732a65781b70dfe6be6bc123b027e490badcc3c` |
| `INDUSTRIALS_WAVE9_RESEARCH_TO_PRODUCT_CATALOG_2026-09-23.md` | 39,005 | `513335044c4032a1053ca31d339aac57360572eb` |
| `inspect_wave9_snapshot.py` | 5,917 | `80450dd2a6c39a94ffcc64e3dd52137d837ce78e` |
| `test_wave9_snapshot_helpers.py` | 666 | `5398e8d2decd855adae2dd1de301d1d48eb6b88c` |
| `WAVE9_SNAPSHOT_DIAGNOSTIC.json` | 2,011 | `b7af44dfa22ed7d4845cc51ba1c860e18732b568` |
| `WAVE9_TASK_CATALOG.json` | 11,784 | `4845515775d6fde3c3ba43e6fe7f55692ee69fd0` |
| `verify_wave9.py` | 6,210 | `cc34cca05672d4ca2b45aba6557c8064cc5ee086` |

The catalog has 5,293 whitespace-delimited words, 24 investor tasks, six reference dossiers and 30 proposed application requirements. The historical-data audit has 1,236 words. These are coverage and artifact-structure descriptions, not proof of investment advantage or production behavior. The JSON task catalog is an exact derivative of the written rows; it is not a native schema or new data registry. The snapshot diagnostic contains aggregate statistics and four selected editorial examples, not the complete feed.

## Reproduction and exclusions

The default package verifier uses Python's standard library and does not require the historical binary. The optional hash-bound inspection uses the installed Thrift compact-protocol reader and Linux `libsnappy.so.1`; it rejects other file hashes/layouts. Prefer a separately validated standard reader in the incumbent native environment for independent cross-checking. No production dependency or new collector is proposed.

The raw historical Parquet file, base64 text, complete decoded rows and private scratch directory are excluded from GitHub publication and the portable archive. Recovery inputs remain owned by the existing native source. Portable check outputs and hashes are derived evidence, not another canonical data owner. Archive integrity, exact member hashes and private-input exclusion must be checked after packaging.

## Remaining limitations

The current result establishes historical artifact recovery and a negative comparison-eligibility case, not fresh or basis-matched consensus. Contributor timestamps, accounting/per-share/currency/fiscal basis, original publication/revision history, canonical listing, prices, corporate actions and permissible use are not fully qualified. Pentair direct-source retrieval is now resolved narrowly; it does not prove private retention or historical estimate availability. No raw report corpus or paid feed was acquired.

The proposed future eight-issuer evaluation is a feasibility design. It has not been accepted/started by the evaluation owner and contains no committed prediction, observed later outcome or autonomous watcher. The previously selected examples remain retrospective development cases.

The 30 W9-T requirements and six dossiers are unexecuted application specifications. No independent factual/design review, calibrated forecast, held-out validation, stock-return attribution, live schema admission, application test, CI acceptance, deployment, authenticated browser proof, worker or trading effect is claimed. Final Fable handoff remains withheld pending the selected real-case/native-interface and source-rights qualification.
