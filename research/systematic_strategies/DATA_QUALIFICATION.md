# Systematic Strategies — actual input qualification, 2026-10-22

Scope: parent-owned research evidence for Macro #10089. This is not a new data authority, an economic validation, or capital permission. Facts below supersede the initial census's broad claim that no suitable ETF OHLC source exists. Original raw stores are unchanged.

## Existing licensed source, not another feed

At Macro `41247163ca95d9a9d3c6ea75c1bbc5d6cd962b46`, `config/dataset_registry.yml` registers `equity.bars.daily.massive` as PRODUCED, raw OHLCV, with purchase/internal-computation/redistribution grants referencing `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md`. That record is operator-confirmed; the private agreement was not accessed or disclosed. Dataset-specific conditions and public vendor-debranding law remain applicable.

`collectors/massive_stock_day.py` identifies R2 `massive_stock_day/` as canonical. Git holds sidecars, NOT all per-ticker files. Absence from Git cannot establish absence of data. Reuse the existing store/reader and `scripts.publish_r2._client`; do not launch a new collector or bulk restore/publish a partial tree.

## Observed local mirror is stale

Read-only parent inspection of the original M2 checkout found SPY, XLK and XLE each at 1,254 rows, 2021-07-06 through **2026-07-02**. A current manifest elsewhere does not make these bytes current.

Evidence: `/Volumes/Mastermind/evidence/systematic-10089-ceo-web-01/input-census-20261022T185935Z.json`.
SHA256: `48d32c4e15a043d05cd10aa4dc043b357d7ec42d10479654a0c1714db7b21d17`.

No primary checkout data or credentials were modified. The existing config loader was used without printing/copying secret values. A task-local transport venv installed the already-declared boto3 client; global/shared environments were unchanged.

## Four exact R2 reads succeeded

Read-only capture time: 2026-10-22T19:01:23.660073Z through 19:01:25.406573Z.
Directory: `/Volumes/Mastermind/evidence/systematic-10089-ceo-web-01/r2-capture-20261022T190123Z/`.
Receipt: `receipt.json`, SHA256 `3c93f555b0b2b30a5d575aec8c5bf94871428b5b8ea0d0b3cc745d78fa6a8b10`.
Exactly four GETs, no all-store scan/restore, no source write, no scheduled job or account effect.

| Object | Rows / range | SHA256 |
|---|---|---|
| `_manifest.json` | Wrapper count 21,776; nested store 21,775 tickers, latest 2026-10-21 | `5563e333bbb20e33290e2dad302628118217814ff9cd19a8a06ec45e9ca31691` |
| `SPY.parquet` | 1,331; 2021-07-06 through 2026-10-21 | `4132e14624e2f3bc4d1a3171f87e19ff9b34b824586ed57d7ed9d373ae14097e` |
| `XLK.parquet` | 1,331; same range | `de9cce04a8d37712e41c42beec248e7f096b727ae2474f6b2065711076ba149f` |
| `XLE.parquet` | 1,330; same range | `3d236f18a82eb66e3c0c3df331bd623a57135ef71ec4359de6c026711d7f932f` |

The manifest's `files` array lists basenames, not per-object digests. Exact object hashes in the capture receipt authenticate the captured bytes, not an atomic cross-object provider snapshot. LastModified/ETag values are retained in the receipt. No provider-original historical arrival clock is inferred.

## Independent structural/calendar checks

The existing `lib.us_cash_calendar.expected_last_session` gives **2026-10-21** at this capture cutoff. All three files reach it. `sessions_between` identifies:

- SPY: zero missing expected sessions.
- XLK: zero missing expected sessions.
- XLE: **2026-08-18 is absent**. Do not silently intersect it away or fill it from another close.

All three have unique monotonically ordered session labels; zero nonfinite/nonpositive OHLC; zero OHLC inequality failures; and zero missing/nonpositive volume in the captured bytes. Index timezone is absent: these are session DATE labels, not source arrival timestamps.

Qualification receipt: `qualification.json` beside the capture.
SHA256: `6b39584f384f52387000518cab7d5bcf06370b6e3447c90a348467ffa746cb46`.

## Corporate actions are a real economic blocker

Raw close changes exceed 30% only on **2025-12-05** in XLK and XLE (approximately -49.6% and -50.2%). Price discontinuity is a SUSPECTED action, not an event authority. The issuer's original November 20, 2025 announcement independently confirms 2:1 splits effective December 5 for both funds:

https://investors.statestreet.com/investor-news-events/press-releases/news-details/2025/State-Street-Investment-Management-Announces-Share-Splits-for-Five-Select-Sector-SPDR-ETFs/default.aspx

Inspected source states the split applies to December 2 holders, is payable after December 4 close, and trades post-split December 5. No strategy return is derived from this publication. It is independent corroboration, not an imported/qualified production action-revision set or evidence of completeness for all actions.

Existing `lib/dataos.price_views` owns exact split factors, opposite-direction volume adjustment, dividend treatment, revision clocks and `admit_action_input`/`admit_revision_set`. `qualify_action_input` rejects an inferred discontinuity, missing source receipt, unknown convention or non-PRODUCED source. It must be used rather than duplicating factor math.

The source `reference.corporate_actions.massive_split_evidence` is **PROPOSED** at the inspected registry revision. Its code is opt-in acquisition, `basis_eligible:false`, no live producer/store activation. This record cannot be flipped to CONFIRMED or PRODUCED by a caller flag. No such mutation has occurred. A safe capture may establish source evidence; economic use still requires the existing qualifier's accepted path and completeness/correction semantics.

Consequently, the current raw ETF set is **not yet economically qualified for return certification**. SPY's absence of a large discontinuity is not proof of action-history completeness. Cash distributions, share adjustments and simulator conventions remain explicit requirements. No backtest/forward return, prospective claim or paper trade has been asserted from these captures.

## Integration action

The disjoint `systematic-10089-input-bridge-01` child implements an offline thin qualification adapter only. It must detect stale objects, hash mismatch, future/naive receipt clocks, missing sessions, basis/action/rights gaps and source status. It may show structurally current data while keeping economic readiness false. It does not collect, change registry status, calculate replacement factors or import the unmerged engine.

Parent continues actual action-source qualification through existing Data OS contracts and resolves the missing XLE observation through the existing store owner. Current-vintage reconstruction and genuine point-in-time historical evaluation remain different allowed uses. A successful daily current capture can establish a future observation baseline but cannot retroactively create historical availability.

## Rejected audit conclusions

The read-only child `systematic-10089-data-01` correctly found missing opens in the inspected Yahoo frames and important vintage/rights limitations. Its recommendation to extend Yahoo as the only route is rejected: it overlooked the canonical R2 OHLC store and existing sector-ETF collector. Its Git-only absence inference does not establish missing runtime receipts or missing data. Its source-branch identity confusion is not accepted. Preserve only independently verified narrow findings; do not repeat the audit or treat its entire return as acceptance.
