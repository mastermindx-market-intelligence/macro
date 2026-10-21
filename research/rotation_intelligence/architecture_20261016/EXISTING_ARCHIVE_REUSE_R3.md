# R3 source-provider decision: reuse existing Data OS archives before acquiring again

Date: 2026-10-17. This is the latest source-discovery delta for PR #9507. It narrows the earlier SOURCE_READER_REHEARSAL_R3 next action: **do not assume a new Yahoo capture is the first dependency. Existing Tiingo/Data OS receipts already cover all thirteen requested instruments.** Qualify those exact retained sources and their native research reader first. No market values or outcome labels were decoded for this investigation.

## 1. Current source and source-owner evidence

Inspected at Macro `ab5156a4b2c336181f3c5256e7c0766f04f99598`:

- `collectors/tiingo_archive.py`, blob `d5ea5459bad6c687a4aef919b30c8d9fa4a149c0`: incumbent raw archive and context-bound receipts, fixed-origin EOD endpoint, raw/adjusted fields retained separately.
- `lib/dataos/tiingo_reader.py`, blob `7d39cde303d8b4ee3d05a86478e109577ec91411`: existing evidence-bound research view/history reader, not a new API to create.
- `lib/dataos/tiingo_views.py`, blob `22d6058648bc111313dd0de5e4a679897b7c25e7`: provisional Data OS normalization with explicit identity/rights/PIT limitations.

Source PR #8698 is merged (merge `fba80a12a2886c8a143bee2c9cf9ce580702e5f1`, October 11, 2026). Its broader source/consumer obligations remain distinct from merger. Yahoo archive-refresh PR #8066 remains Draft; its basis and acquisition protections were not modified or displaced.

The source owner’s current records in #8697 and #8698 affirm Chairman-reported special Tiingo business/public-display/redistribution permission. This investigation does not manufacture agreement fields, independently verify the underlying agreement, or infer every product/derived-use permission. **Generic public self-service restrictions and old provisional archive flags are not proof that the company's special agreement is absent.** They are also not a machine-readable consumer enrollment; exact EOD use, attribution, fields and audience still need mapping through the incumbent rights owner.

## 2. Actual retained evidence found

At `2026-10-17T07:34:18.401787+00:00`, a bounded scan of six dated `eod-bars` partitions checked only the thirteen named symbol directories and their exact associated receipt files. It found **37 original receipts and 37 materialized views**. No key file, raw response payload, numeric price/return/volume column, or outcome dataset was opened; no provider request or archive write occurred.

The native `validate_receipt` function accepted all 37 original receipt identities. Each selected manifest bound the same receipt ID, payload digest, symbol context and capture clock; its row count matched the Parquet footer. This is checksum/context validation, not independent authentication of a vendor or certification of the underlying prices. Full raw/output hashes were **not** recomputed in this metadata-only pass.

| Instrument | Deep-view row count | Earliest date in deep footer | Latest date in any inspected footer |
|---|---:|---|---|
| XLB | 6,992 | 1998-12-22 | 2026-10-15 |
| XLC | 2,089 | 2018-06-19 | 2026-10-15 |
| XLE | 6,992 | 1998-12-22 | 2026-10-15 |
| XLF | 6,992 | 1998-12-22 | 2026-10-15 |
| XLI | 6,992 | 1998-12-22 | 2026-10-15 |
| XLK | 6,992 | 1998-12-22 | 2026-10-15 |
| XLP | 6,992 | 1998-12-22 | 2026-10-15 |
| XLRE | 2,767 | 2015-10-08 | 2026-10-15 |
| XLU | 6,992 | 1998-12-22 | 2026-10-15 |
| XLV | 6,992 | 1998-12-22 | 2026-10-15 |
| XLY | 6,992 | 1998-12-22 | 2026-10-15 |
| SPY | 8,482 | 1993-01-29 | 2026-10-15 |
| BIL | 4,873 | 2007-05-30 | 2026-10-09 |

All thirteen deep-view schemas include distinct raw close, adjusted close, dividend and split fields. The deep histories end October 9; separately captured short slices extend the twelve equity/benchmark inputs through October 15. BIL has no later inspected slice. **A date minimum/maximum does not prove uninterrupted session coverage, correct values or revision-consistent joining.** No mixed-vintage history has been assembled here.

This converts a previously uncertain availability question into a concrete reuse opportunity. It also exposes the immediate cash-benchmark mismatch: do not forward-fill BIL through later equity sessions or assume an all-thirteen current snapshot exists.

## 3. Native reader contract and the correct use boundary

`read_research_view` supports `INSPECTION` and explicitly acknowledged `RETROSPECTIVE_EXPLORATORY` use. It refuses `PIT_BACKTEST` for these unadmitted hindsight views. `read_research_history` accepts explicit bounded capture references, verifies exact context and refuses conflicting corrections rather than silently selecting the convenient price history.

The checked manifests retain `dataos_identity_admitted=false`, `pit_backtest_eligible=false` and `redistribution_admitted=false`. Those are real current *consumer* limits. They do not independently describe the company's complete commercial agreement. Do not edit a manifest flag to simulate source admission, nor assume a recent capture proves historical first availability.

The new allocation input adapter should consume the native reader's correctly qualified evidence mode and keep vendor identity/basis distinct. It must not convert Tiingo data into a forged Yahoo capture receipt to satisfy the other research bridge. A provider-specific bounded adapter under existing Data OS/research owners is appropriate; a second data service, archive or rights registry is not.

The retrieved public Tiingo EOD documentation identifies historical-date endpoints, raw and adjusted OHLC, distributions/splits, and evening corrections. That supplies method expectations, not proof that these retained rows cover the required dates or that their original historical release times are known. Documentation: https://www.tiingo.com/documentation/end-of-day . The official yfinance documentation's research/personal-use warning likewise means installation alone cannot establish an organization's source rights: https://ranaroussi.github.io/yfinance/ . No legal opinion or provider restriction bypass is inferred from these public descriptions.

## 4. Revised next action—specific and bounded

1. **Reuse before recollecting:** resolve the thirteen exact native Data OS view references and the applicable EOD research/consumer permission, with the existing source owner. Historical lookup remains a candidate until that scope and the study's native registration are valid.
2. **Qualify the actual values only under that admitted scope:** native receipt/output integrity, complete required calendar, vendor identity, adjusted-return basis, corporate actions and conflicting overlaps. Preserve explicit hindsight status. Do not open native Track A holdouts by relabelling them Track B.
3. **Acquire only a real missing dependency:** the metadata indicates a missing later BIL slice and possibly a latest-session delta; this does not yet prove which provider requests are needed. A qualified native read may establish reuse or an exact gap. No all-ticker or whole-history acquisition is justified by the current evidence.
4. **Adapt the existing research input boundary:** explicit thirteen inputs, current study schedule/cutoff and sufficient lookback, keeping the incumbent nine-node study unchanged. The R3 reference cases remain valid across providers, but source identities/rights are not interchangeable.

The actual source-contract/consumer enrollment and separately admitted empirical study remain the work—not a new architecture census. The current live-source/implementation scope has not been expanded, and no source effect has been started. The prior final-review provider403 remains unretried; this independent read-only source investigation is not a substitute reviewer or permission workaround.

## 5. Evidence references and limits

Detailed selected metadata, with all full receipt IDs, request-context and source references, is retained under the existing M2 research evidence root:

- `r3-published/tiingo_thirteen_receipt_metadata.json`, SHA-256 `bfd537c8387f0d04a6ee6da239f414e1b873b80578d2993dc70bd21e982bf5df`.
- `r3-published/tiingo_thirteen_view_metadata.json`, SHA-256 `09e868610931da4745e4a87c3490ee3d7458c74e370f1727cb406b8ac5ba81e9`.

The actual archive remains `/Volumes/Mastermind/market-data/tiingo`, owned by existing Data OS. This report publishes only aggregate coverage/metadata, not licensed vendor price rows, credentials or raw responses. It is not a duplicate data store or a new source of investment truth. No normal publication, current full-session completeness, native identity admission or historical PIT qualification is claimed.

**Architectural refinement:** earlier R3 language preferring a new bounded Yahoo warmup is superseded only as the *first source action*. Its thirteen-input completeness, no-fabricated-provenance, calendar, missingness and baseline requirements remain. Existing native Tiingo archives must be assessed first; changing provider labels is not evidence equivalence.
