# Asset quote validity and small-price clarity

## Outcome

An invalid asset quote now reads **Unavailable / 暂无**. A valid small positive quote retains useful precision instead of appearing as $0.00. The asset itself, its independently supplied date, relative reading, structure and risk remain usable.

This is a presentation/projection repair in dependent Draft PR #10901, based on source `af9322f8e870be16f6f29fc38b8b573267347bd6`. It does not change producer calculations, refresh market data, authorize a model or replace a public route.

## Display contract

| Supplied numeric quote | Presentation |
|---|---|
| Missing, invalid type, nonfinite, zero or negative | Unavailable / 暂无 |
| Strictly positive and below 0.00000001 | <$0.00000001 |
| At least 0.00000001 and below 0.01 | At most eight decimal places; round positive halves upward and remove trailing fractional zeros |
| At least 0.01 | The existing ordinary-money formatter for that consumer |

Check the lower bound before rounding. The bound asserts a strictly positive supplied number; never use it for missing or zero input. Eight decimal places is a display limit, not a market tick size, execution precision or a source-quality guarantee.

Examples verified through the server renderer include:

| Input | Visible price |
|---|---|
| 0 / -1 / null | Unavailable / 暂无 |
| Smallest positive finite float / 0.000000009 | <$0.00000001 |
| 0.00000001 | $0.00000001 |
| 0.000000015 | $0.00000002 |
| 0.000000025 | $0.00000003 |
| 0.000123455 | $0.00012346 |
| 0.001 | $0.001 |
| 0.009999994 | $0.00999999 |
| 0.009999995 | $0.01 |
| 0.01 / 104.19 / 2413.2 | $0.01 / $104.19 / $2,413 |

Rounding a sub-cent input up to $0.01 is intentional. It remains a nonzero, correctly rounded display.

## Existing owners and build path

| Owner | Change and responsibility |
|---|---|
| `lib/crypto_intelligence_view.py` | Qualify only the projected asset price with the existing finite-number guard plus strict positivity. Retain the asset and every other projected field. |
| `scripts/build_crypto_intelligence_r4.py` | Add asset-only `asset_money` alongside unchanged generic `money`. Use `Decimal(str(number))`, a fresh local `Context(prec=28, rounding=ROUND_HALF_UP)`, fixed decimal output and trailing-zero removal. Pass the formatter to the existing Jinja render. |
| `templates/crypto_intelligence_r4.html.j2` | Render the Markets price cell with the asset formatter and explicit bilingual unavailable fallback. Jinja escapes the bound's less-than sign. |
| `templates/crypto_intelligence_r4.js` | Add asset-only `assetMoney`; use existing Intl number formatting for the new sub-cent branch. Apply it only to the asset inspector's Price field. |
| Existing served candidate artifacts | Rebuild the two R4 candidate pages and served JS from the retained view. Both pages change only their two asset-version references; view JSON and CSS stay exact. |

The normal builder continues to read the existing published contracts and call `build_view`, then `render_view`. There is no new quote service, source fetch, name registry, routing owner or state store. A retained view can also be rendered: the server consumer independently rejects nonpositive/missing quotes without modifying that view.

The original source strings are already parsed numeric inputs. Decimal conversion controls display rounding; it does not reconstruct precision that the source may have lost.

### Decimal context isolation

The first candidate's quantize call used the caller's ambient decimal context. A focused reproduction showed that low precision could raise `InvalidOperation`, while a normal precision call changed the caller's `Inexact` and `Rounded` flags. The final helper passes a fresh explicit context to quantize. It neither changes caller settings nor leaks rounding flags.

This is local calculation state, not a shared context object. The bounded branch needs no more than seven coefficient digits after quantization; precision 28 is sufficient. The ordinary-money branch is unchanged.

### Rounding references

[ECMA-402 2026, SetNumberFormatDigitOptions](https://tc39.es/ecma402/2026/#sec-setnumberformatdigitoptions) defines the default Intl rounding mode as halfExpand. [Python Decimal, ROUND_HALF_UP](https://docs.python.org/3.14/library/decimal.html#decimal.ROUND_HALF_UP) defines the corresponding positive-half behavior used here. Native fixtures verify the selected boundary values in the actual Python/Chrome environment.

The parity claim is scoped to the new sub-cent branch. The pre-existing ordinary branch intentionally remains as it was: Python may show $1.00 where JavaScript shows $1. Do not claim universal currency-format parity.

## User workflow and visual contract

Markets keeps the same asset, symbol, date, filters and Inspect action. The inspector shows the same qualified quote. Close returns to Markets and restores the opener's focus; storage remains unchanged. No banner, retry action or explanatory product footnote is needed.

The comparison matrix contains no quote-price row, so it retains its existing independent readings. Zero remains valid for relative and price percentage changes. Invalidating a quote does not invalidate a genuine zero relative reading or alter a supplied Building history state.

Six native captures were inspected: unavailable and sub-threshold quotes in EN390 dark/fine-pointer and ZH320 light/touch, plus the preserved unavailable/history comparison states. The full lower-bound value fits at 320px, and dates, structure and risk remain readable.

Paper file `01M6Y3F0NXNDPAKJMJGCAD759Z` now has editable companion `3N8-0` on existing page `p-3-0`: EN390 unavailable and ZH320 below-limit quote components. It reuses quote groups `368-0` and `37Y-0` and preserves their 30px/38px value typography. These are explicitly marked synthetic component references; their component styling is not a claim that the current native inspector uses that geometry. Build rules stay outside the product components. Existing proposed paired-window receipt states are preserved.

## Verification and exact scope

| Run | Observed outcome |
|---|---|
| Parent source with new quote cases | 18 failed, 19 passed, 201 deselected; 4 browser contexts/pages, zero errors or external/WebSocket requests |
| Initial quote candidate | 108 passed: 100 contract + 8 browser cases; 8 contexts/pages, zero errors or external/WebSocket requests |
| Ambient-context reproduction | 2 failed: low precision exception and caller flag mutation |
| Final context-isolated builder | 17 passed: 15 existing server-price cases plus the 2 context cases |

There are **110 unique passing cases: 102 contract and eight browser**, across the initial 108-pass and final 17-pass runs. Fifteen server cases overlap. The final refinement changes only the builder and its tests; frontend assets, native captures and browser inputs remain exact. This is not a new complete browser-suite run.

The four new quote browser cases exercise 18 asset Inspect→Close journeys in total, plus the existing relative-integrity paths. Synthetic quotes deliberately include invalid values and tiny values; they are not actual Ethereum, Solana, Bitcoin or XRP market observations.

Final publication readback verifies nine changed source/served/test paths and 12 unchanged inputs. Reversing the four product-source transformations and both test changes recovers the exact parent. Generic Python money AST is unchanged; JavaScript conservation follows from the exact source inverse. The two retained pages differ only in asset references. Runtime asset version: `4165f78946a7`.

## Evidence

- [Validation and limitations](QUOTE_CLARITY_VALIDATION.json)
- [Native publication receipt and all source hashes](quote/PUBLICATION_RECEIPT.json)
- [Parent baseline](quote/BASELINE.txt) / [initial candidate JUnit](quote/INITIAL_CANDIDATE_RESULTS.xml)
- [Context reproduction](quote/CONTEXT_BASELINE.txt) / [final focused JUnit](quote/CONTEXT_FINAL_RESULTS.xml)
- [Source and test transformations](quote/TRANSFORMS.json)
- [Publication verification script](quote/PUBLICATION_READBACK.py)
- [Six inspected captures](quote/captures)

## Next bounded work and release boundary

The captures expose redundant fallback identity such as **BTC · BTC**. Remove that duplication only in presentation while preserving symbol keys, search, routes, comparison headers and the existing canonical-name mapping. More prominent inspector hierarchy can be assessed separately against the implemented data and navigation contract.

Producer positive-history qualification, missing trend votes and emitted paired-window receipts remain separate owner/model work. H5/model, alerts, hosted and independent visual acceptance, public-route cutover, admission and release holds remain. This local fixture proof is not production acceptance or current-market freshness.
