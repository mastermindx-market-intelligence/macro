# CN pack tradability: the caller gap is concrete and bounded

**Decision:** reuse the existing nightly metadata owner and `stock_tradability_ok` predicate, construct a complete Boolean map for the pack's stock universe, and supply it at the existing caller. The pinned caller currently omits that argument. The offline laboratory establishes the filtering seam and its current coverage; it does not establish a full-universe gate, armed-board or return effect.

Study pin: `3d90aad6d83152dfeeaf8345bc995826ac9d3139`. Corrected input SHA256: `8106d35c0caccfdc000f50652cf5a673605cd2d6e11882ccb28741e85490f7a3`. The design preceded the census. The corrected read-only host census completed with exit 0 in 11.70 seconds; **77 offline checks pass**, including an exact replay of the principal weight laboratory's 12 checks. Source identities, exact native functions/statements, 1,745 immutable data-read receipts, captured arguments and results are retained in this package.

## 1. Exact current seam

`scripts/build_cn_live_pack.py:main` supplies only `root`, `cfg`, `now` and `limit` to `build`. The native `build` accepts `tradable: dict[str, bool] | None`, but applies it only when it is truthy and only in the normal `series is None` branch. A missing key passes through via `.get(ticker, True)`. An empty map performs no filtering. An explicitly injected series bypasses both this map and the native stock-universe filter.

The shared predicate's name is misleading at this interface: **it returns a rejection reason (`"st"`, `"mcap"`, `"adv"`) or `None` for a pass**. The map must use `stock_tradability_ok(...) is None`. Passing raw predicate results reverses the truthiness of accepted and rejected names.

The native main was executed with a recording build callee and no output/publication options. Separately, the unmodified native build was traced to line 115, immediately before gate construction. That preserves the actual filtering branch without running an expensive gate grid or touching a latch.

| Six actual names at the pre-gate frontier | Count | ST / low-ADV witnesses retained |
|---|---:|---|
| Current caller, no map | 6 | `600079.SS` and `000028.SZ` |
| Complete Boolean map from native predicate | 4 | Neither |
| Raw rejection-reason map, incorrect conversion | 2 | Both; valid names are removed |
| Partial map rejecting only the ST name | 5 | Low-ADV name still passes |

The other four names are `002460.SZ`, `300750.SZ`, `300773.SZ` and `603799.SS`. The fixture includes the integration laboratory's three original names plus deterministic actual ST, ADV and missing-cap witnesses. Native filtering also excludes labeled ETF/index/BJ context fixtures; native price cleaning excludes unusable price series. These checks establish the seam, not later centre states or probe outcomes. [Evidence: `results.json`, `checks`, and `observations.native_frontiers`; exact caller source in `TRADABILITY_INPUT.json`.]

## 2. Metadata schema and incumbent source owner

The required metadata already lives in the nightly `build_china_library.py` owner, mainly lines 2203–2272 and 2529–2542. There is a shared pure predicate, but the metadata loading is still inline. Extracting a read-only helper at that existing owner is compatible; copying these rules into a new store, separate universe policy or collector is unnecessary.

| Native predicate argument | Existing map / source | Schema, units and precedence |
|---|---|---|
| `st_flag` | `st_flag_by`, from `data/tushare/moneyflow.parquet` | `ticker`, `name`, optionally `trade_date`; sort by trade date, latest row per ticker; `is_st(name, None)` produces Boolean flags. Missing entry defaults to `False`. |
| `name_zh` | `name_zh_by`, from `data/china_search/members.parquet` | Ticker index or column, `name_zh`; fallback name check catches `ST`, `*ST`, `S*ST`, `SST` prefixes and the `退` character. |
| `mktcap` | `mktcap_by`, from members plus Tushare valuation | Members `mktcap_yi`, unit 亿 CNY. Exact `30.0` placeholder is removed. Tushare `ticker` / `total_mv_yi` positive values fill gaps; a real member cap retains precedence. Tushare-vs-free preference compares with `data/china_a_val/pe.parquet` through the existing freshness helper. |
| `adv_yi` | `liq_by[ticker]["adv_yi"]`, from `engine.china_liquidity.liquidity_map` | Reads `data/china_stocks/<ticker>.parquet` with `close` and `volume`. Native formula is `median((close * volume).dropna().tail(20)) / 1e8`, rounded to four decimals; output 亿 CNY/day under the owner's input-unit contract. |

The incumbent rejection order is ST, then real market cap below **30 亿**, then ADV below **0.5 亿/day**. The `30.0` cap sentinel is explicitly exempted. Unknown cap or ADV passes the incumbent predicate; missing ST evidence relies on the name fallback and otherwise passes. Reusing these semantics does not certify unknown metadata as fresh or safe. It preserves the existing owner while making the caller consistent. [Evidence: exact native predicate, owner blocks and liquidity/freshness source in `TRADABILITY_INPUT.json`; current and synthetic boundary checks in `results.json`.]

## 3. Frozen current coverage

The corrected native universe contains **1,739 rows: 1,716 stock rows and 23 configured ETF/index context rows**, with stock-panel date **2026-10-09**. The actual native nightly stock set and the pack's stock filter coincide on this input. They are not assumed equivalent on arbitrary future inputs.

| Census measure | Current result |
|---|---:|
| Native predicate passes | 1,638 |
| Native ST exclusions | 1 |
| Native ADV exclusions | 77 |
| Native market-cap exclusions | 0 |
| Missing ST-map / Chinese-name entries | 0 / 0 |
| Missing real market-cap map entry | 1 |
| Missing ADV-map entries | 0 |
| Nightly price-stale exclusions | 0 |
| Names exceeding the pack's resolved three-session lag | 0 |

The actual ST witness is `600079.SS` (`ST人福`). The first sorted ADV witness is `000028.SZ`, with ADV **0.3827 亿/day**. `300773.SZ` is the one name without a real-cap map entry and passes the incumbent unknown-cap rule. Members has no null cap field, but its placeholder/overlay handling leaves that usable-cap gap. The Tushare valuation source has 5,559 rows and moneyflow has 6,025 rows; their relevant dates run through October 9. All 1,716 selected ST-name dates are `20261009`. The member frame itself has no date recognized by the native freshness helper. The free PE frame runs through October 8. [Evidence: `summary`, `metadata_frames`, `stock_rows`, and `data_read_receipts` in `TRADABILITY_INPUT.json`.]

The breadth cache is absent both from the immutable Git pin and from the observed host path. Its versioned constituents contain seven tickers outside this current stock set; absent cache prices mean they contribute no native rows. This is an explicit coverage boundary, not proof of an all-A-share universe. No missing cache was fabricated or collected.

The corrected overlay upgrades **1,666 names** to deep price history and keeps **3 fresher cache series** over older deep stores. Their close / ADV-source dates are:

| Ticker | Native last close | Deep source used by ADV | Pack lag |
|---|---|---|---:|
| `300773.SZ` | 2026-10-08 | 2026-09-30 | 1 session |
| `601059.SS` | 2026-10-08 | 2026-09-14 | 1 session |
| `601198.SS` | 2026-10-08 | 2026-09-14 | 1 session |

These are actual source-age differences. They do not establish official suspension status. [Evidence: `observations.actual_close_vs_adv_source_dates` and the corrected native loader log.]

## 4. Missingness, freshness and suspension limits

The native ST-name block does not apply a cutoff or an age gate. Synthetic tests show it accepts an old ST row and allows a future-dated normal-name row to replace an earlier ST flag. Missing or unreadable moneyflow produces an empty flag map, retaining the member-name fallback. These are executed boundary witnesses; the current selected ST rows are dated October 9, and no current future-name corruption is claimed.

`prefer_tushare` is a relative-freshness rule, not a complete availability contract. With a fresh free source it rejects a two-session-stale Tushare frame and accepts a one-session lag. Without a free source it can retain ancient or undatable Tushare data. A future-dated valid-session row also wins the comparison. Native ADV similarly has no absolute age or decision-cutoff argument, and any nonempty dollar-volume tail can yield ADV; it does not require 20 observations. The current six actual liquidity fixtures reproduce exactly from their retained tails. These behaviors should be carried to the existing vintage/source owner, not silently patched with a new expiry threshold inside this caller fix.

There is no official suspension flag in the traced tradability input. The nightly owner separately rejects a close more than **15 calendar days** behind the stock panel. The pack uses the native CN calendar and resolves to **3 sessions**. They are distinct existing safeguards. For a synthetic October 9 panel, September 24 is exactly 15 calendar days old and passes the nightly rule but is five sessions behind and fails the pack guard; September 30 is two sessions behind because of the exchange holiday closure. No current name fails either price-age screen. [Evidence: `relative_freshness_*`, ST/ADV missing-stale cases and `observations.nightly_calendar_days_vs_pack_sessions` in `results.json`.]

## 5. Minimum implementation acceptance

1. Reuse a read-only extraction of the existing nightly metadata loading, keeping source precedence, fields, units and unknown-value behavior. Both the nightly path and pack caller should use that owner.
2. Construct strict Boolean entries for every ticker in the existing pack stock universe using `stock_tradability_ok(...) is None`. Assert exact coverage before calling `build(..., tradable=map)`. An empty/partial map must not silently stand in for completed metadata preparation. The unknown metadata values themselves retain the incumbent predicate semantics.
3. Preserve the broad native universe and the pack's existing session guard. Published-board membership is not a replacement metadata map. Do not claim that this laboratory ran every gate or proved every armed record.
4. Re-run the captured main/frontier witnesses on the implementation, then couple them to the existing real three-name gate/probe acceptance. Require current metadata counts and source receipts to explain any difference. Any additional suspension source, stale-data policy or screen formula requires its existing owner decision.

## 6. Independent weight assessment

The principal weight audit is accepted for its bounded claims. Its exact script/input replay produces a **byte-identical result**: 12 checks, seven scenarios. The current pinned scorecard's mapped valuation, margin and fundflow families are unproven, and the actual current coefficients remain normalized priors:

| value | margin | flow | comment | lhb | block | analyst |
|---:|---:|---:|---:|---:|---:|---:|
| 0.3429 | 0.2857 | 0.2571 | 0.2143 | -0.1429 | -0.0714 | 0.1143 |

These are signed score coefficients, not convex portfolio allocation percentages. Future-card, weak negative-evidence, whole-market margin and malformed numeric/Boolean cases are all explicitly synthetic. An additional date-only control shows the native reader ignores a change from an earlier to a later scorecard timestamp; the timestamp itself is not what causes the coefficient change. The synthetic evidence fields cause it while the reader supplies no cutoff gate.

The feature/target mismatch is also a valid implementation concern: the consumer reads per-issuer `chg_pct`, while the validation family describes a whole-market financing / CSI300 timer. The consumer's division by `20.0` is scaling and does not independently establish a measurement horizon. Exact horizon and feature identity remain the incumbent source owner's premise. **No actual board, rank, return or execution effect is claimed.** [Evidence: frozen `weight_reviewed_source/`, byte-identical `weight_replay/weight_results.json`, and `observations.weight_assessment`.]

## Reproduction and scope

Run `python -B run_tradability_lab.py` from any directory. The full read-only census can be reproduced by `extract_tradability_inputs.py` on the authorized host against the fixed Git pin; no repository checkout or data writer is used. The host census used pandas 3.0.5, and local structural/boundary replay used pandas 2.2.3; both runtimes are recorded. The first unsealed census omitted the `numbers` dependency required by a broad-exception native helper, suppressing deep overlays. That attempt is retained and explicitly rejected in `HARNESS_AMENDMENT.md`; the accepted run includes a native date preflight and the exact nightly stock-set assignment. Current metadata counts stayed the same after correction, while the price-history overlay was corrected.

This package changes no production source, collector, cache, latch, ranker, feature policy or research outcome. Earlier completed labs and reviews remain unchanged. Source dates remain conditional provenance; they do not create historical first-seen availability or executable investment evidence.
