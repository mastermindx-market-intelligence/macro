# IV-spread input, output and consumer qualification — 2026-11-11

## Outcome and scope

This repair addresses [issue #11080](https://github.com/mastermindx-market-intelligence/macro/issues/11080) and the [original three-seam finding](https://github.com/mastermindx-market-intelligence/macro/pull/629#issuecomment-6807515748): corrupt option-count weights could reverse an otherwise positive call-minus-put spread or persist a non-finite value, and the ticker Options dialog displayed decimal IV-spread units directly as percentage points.

The candidate qualifies count operands before aggregation, preserves the existing weighting hierarchy for valid data, emits strict finite JSON, and converts the decimal spread to percentage points only at the ticker display boundary. It enrolls the complete existing IV-spread suite in the existing CODE owner; it does not create a duplicate CI owner.

The exact native proof contains **231 passing cases, zero skips**: 60 options-skew, 106 IV-spread and 65 price-pressure cases. Applying the new combined 166-case suite to the original production source produces **53 failures and 113 passing controls**. The original 13-case IV suite also passes unchanged. Full ticker rendering is exercised through the actual writer, assessment, ticker builder, Jinja template and page writer, with both language outputs.

The committed-data audit covers **28 chain files and 4,418,705 rows**. It found no malformed, negative or infinite non-null OI/volume operands in these retained inputs. The latest available chain produces **359 identical complete metric objects** before and after the repair. Fresh ledger records are identical, and the existing **9,409-row historical ledger remains byte-identical**. The stored scoring gate remains false.

These are native regression and retained-input findings. Hosted global gates, browser behavior and deployed production are distinct evidence.

## Source and custody

The native source/input pin is `dce366adcf109daa9a2f0bf99ed68120da6b7957`. Publication is composed on current main `18de8ef0a97d86f97537f986eb2452fcdbb06f64`, tree `821944550ee338bb494253cb7394a56d80da1bae`. All six affected source/CI blobs were read again at that current-main commit and exactly match their tested baseline. Unrelated current-main files are preserved by tree composition.

| Baseline path | Git blob |
|---|---|
| engine/options_ivspread.py | 56a7d78a8c1aff2f1ebf65054b885ea1b9bc0d43 |
| scripts/build_options_ivspread.py | 57412bfaed05558f827e3d0bd611ce584244b066 |
| scripts/build_ticker_pages.py | 485f3c610534983d09c33a1db1402c4368bb148b |
| tests/test_options_ivspread.py | d45a1e39041b1b7e80d6a2892c1f696873dd716c |
| .github/ci/legacy-jobs.yml | b68f93a812c85ddaea5dad71c295c51659b7d371 |
| config/unrun_test_baseline.json | 0aef32511dbb3ca4851a53c6f178bd24922ad456 |

The retained estate custody qualification covers 638 identities, 631 complete inventories and seven partial inventories, with 45 fresh stable head/merge-base bindings. All 135 producer-file comparisons across those 45 carriers were disjoint. The four carriers that change the shared ticker file preserve the complete Options-dialog function at their base and head. Their sector-alias, News, Prophet/privacy and PressureWatch holds remain intact. The recovered original custody bytes have SHA-256 `fb5fce84ce816779061787ac1d73ace302385f6979dc77f7ef778b9a2fbd74ee`.

A final bounded source refresh at 23:22:36 UTC qualified the 19 new or changed heads exposed by the CI custody work. All heads remained stable and all 76 producer/ticker M→H comparisons were unchanged. This includes the newer #11083/#11084, #7592/#8791/#11075 and FINRA repair heads. Its SHA-256 is `2447c098ebe126780063c8b49e85c88dae1f5faaba0acebb537ddd51aaf1aca9`; no whole-estate census was repeated.

The separate CI custody record in the JSON companion identifies exact job-field and baseline-entry overlaps. Concurrent Options selectors or independent proof-step additions are not silently absorbed by this patch. In particular, #8791's held S3 proof steps are not executed or released; #8191 and #7328 retain their original verification/provider/store boundaries.

This work uses protected law pin `c42e812e4a754d7a95efd954441d3f01607a7fb5`. The issue's scoped pickup is [6808387637](https://github.com/mastermindx-market-intelligence/macro/issues/11080#issuecomment-6808387637).

## Count validity and weighting behavior

The repair distinguishes an absent count from an invalid supplied count before duplicate, leg or pair aggregation.

| Admitted matched-pair inputs | Candidate behavior |
|---|---|
| OI column absent or nullable OI cell | Treat that missing operand as zero |
| Non-null OI is malformed, Boolean, negative or non-finite | Withhold that underlying's metric |
| Valid positive total OI | Use OI weights; unused bad volume cannot invalidate this basis |
| Valid zero OI, valid positive volume | Use volume weights |
| Valid zero OI, invalid supplied volume | Withhold the metric |
| Valid zero or absent OI and volume | Use equal weights |

Only strikes already admitted by the existing expiry, moneyness, IV and matched-leg rules contribute count support. An invalid count on an excluded expiry, wing, orphan or invalid-IV row therefore does not poison a healthy matched set.

Raw operands are checked before they can cancel against other legs or duplicates. Integer counts are promoted before aggregation to prevent finite signed/unsigned wrap. Ordinary finite floating-point paths preserve their prior arithmetic. When otherwise valid extreme counts would overflow a pair/total/product, or underflow a nonzero weighted product into the subnormal/zero range, the recovery rescales the original admitted counts by their common maximum before regrouping. It preserves the selected weighting basis.

Spot, tenor, ATM IV and final spread must be finite and valid. The weighted spread is required to remain within the convex hull of admitted pair spreads, with a small relative tolerance for ordinary float32 rounding. Values are refused rather than clamped. The original one/two-pair contextual behavior, three-pair scoring floor, five-name relative cohort boundary, ranking/sign semantics and stored decimal units remain unchanged.

For previous-value context, a latest non-finite historical spread is withheld; the reader does not silently backfill an older row. Historical ledger rows are not rewritten.

## Writer and whole-page consumer

The actual writer now uses `allow_nan=False`. Producer admission happens before snapshot persistence, so invalid current metrics cannot first reach the ledger and only later be rejected by JSON. Serialization is evaluated before `write_text`, preserving an existing JSON file if serialization fails.

The ticker change is confined to the Options-dialog IV-spread value. It uses the existing `lib.numeric.finite` helper, multiplies the stored decimal value by 100, validates the converted result, and formats percentage points. Thus 0.04 is displayed as +4.0pp. Boolean, NaN, infinite and conversion-overflow values are absent instead of rendered as misleading text. No shared percentage formatter or stored field unit changes.

Seven complete-page scenarios cover +0.04, -0.04, +0.12, -0.12, +0.005, zero and absence. Each uses an actual session-dated Parquet input, the real IV writer and `assess`, populated stock data and membership fixtures, then the real ticker `run` → Jinja → `write_page` path. The manifest must report one rendered page and zero failures; the HTML must include the shared shell and the real `div#dlg-options[role=dialog]`. A standard HTML parser checks both language labels and the rendered value inside that complete dialog. The fixture contains multiple page sections rather than an isolated template fragment.

The tests prohibit socket connection and DNS attempts, assert zero attempts and set `RENDER_NO_DRIP=1`. They do not call a provider, publish a site, or establish a browser/deployment result.

## Native execution and falsification

| Execution | Result |
|---|---|
| Original 13-case IV suite on original source | 13 passed; exit 0 |
| Candidate options-skew + complete IV suite | 166 passed; 0 errors; 0 skips; exit 0 |
| Same 166 cases against original production source | 53 failed; 113 passed; 0 errors; 0 skips; exit 1 |
| Candidate existing price-pressure suite | 65 passed; exit 0 |

The candidate combined command is:

```sh
python -m pytest tests/test_options_skew.py tests/test_options_ivspread.py -q -p no:cacheprovider
```

The existing price-pressure command remains separate:

```sh
python -m pytest tests/test_price_pressure.py -q -rs
```

The proof uses CPython 3.14.7 with actual installed pytest 9.1.1, pandas 3.0.5, NumPy 2.5.2, PyArrow 25.0.1, PyYAML 6.0.3 and Jinja 3.1.6. An isolated no-pip virtual environment exposes the existing dependency roots so the existing price-pressure subprocess tests can deliberately replace HOME without losing user-site PyYAML. No dependency download or package modification was needed. Hosted CI retains its own Python 3.12 environment.

Initial harness attempts exposed four missing literal workflow/caller inputs, an incorrect context-shape assertion and this HOME/user-site environment issue. Those causes were corrected before the final execution above. They were not hidden as production fixes. The original Sunday calendar fixture is unchanged: its original suite passes under the existing all-non-session fail-open calendar behavior.

The original test source is retained separately as `original-test-options-ivspread.py`; the before-workspace test file intentionally receives the candidate suite for falsification. Source bindings and diffs use the retained original, not that overwritten falsifier input.

| Log | SHA-256 |
|---|---|
| Original baseline | fcef6a24c4262fb03407f1cad898cbdbe7cda00e97ffbe30a87e56f57ee7eac4 |
| Final candidate combined suite | a47acf8289b9c46a7f46bd1bd7a065a8a8cd51ee99a4f14997ec84477d45be3b |
| Original-source falsifier | 2ff25166c5c404457a7e2ec637d10bc786a248ca1f18d81a9cbf8391050310b7 |
| Existing price-pressure suite | 5efd355c23024083b631ddbc264586879a96ec4ede664007acc28cdb27739886 |

## Retained real-input proof

All 31 committed data/artifact blobs were fetched by immutable Git object ID and verified: 28 option-chain files, the historical ledger, stored validation gate and published IV-spread JSON. Their total size is 121,428,037 bytes. The chain files account for 120,996,885 bytes.

The latest retained chain is `data/polygon_gex/chains/2026-08-13.parquet`, blob `e2d46f4adaa6639e56b7bf8f783e644cd6b6df59`: 185,072 rows and 372 raw underlyings. Before and after compute return the same 359 complete metric objects, and their name set matches the committed output. The actual writer produces identical fresh 359-record ledgers on both source variants.

A third actual writer execution starts from the 9,409-row committed ledger, blob `047d833ea2de32f802c8ebe7629ba73fad6aaf4b`. Its ledger remains byte-identical, the JSON has 359 strictly serializable names and the actual stored gate remains false. All 31 input copies remain byte-identical after the proof.

The stored gate reports insufficient history, zero score weight and its retained 39-date/406-name metadata. This repair does not promote it. No held validator is executed.

The committed output was generated on November 11, but all name-level observations are dated August 13. Generation time is not observation freshness. The audit concerns the exact retained history; it does not establish fresh market coverage, point-in-time alpha, all historical provider states, or a deployed stock-data artifact. No committed `site/stockdata` artifact was available for that separate claim.

## CI enrollment and measured closure

The existing `options-skew-engine` CODE owner retains its 63 declared selectors and exclusive mode. This change adds exactly 50 finite selectors, the existing complete IV suite to its skew pytest command, and only Jinja2 to the dependency command. The 65-case price-pressure command, timeout, gates and all other 400 job definitions remain unchanged. Only `tests/test_options_ivspread.py` is removed from the frozen unrun-suite baseline.

The actual incumbent weight estimator changes this owner from 7 to 9. No packing ceiling or global cap is increased. The added literal selectors introduce no new match for the four ordinary-code curation probes.

The native checkout has complete Git tree metadata for 149,917 tracked paths, while materializing only the verified source closure. The tracked-path payload SHA-256 is `370456445ad0b5ddbee9ed438f18584446b6bb28dc6529e7b15229257e82451c`. The measured owner union contains 120 concrete paths, including 11 explicit actual Jinja/shared-shell inputs.

| Suite | Measured files | Opaque findings | safe |
|---|---:|---:|---|
| Options skew | 11 | 12 | false |
| IV spread | 48 | 21 | false |
| Price pressure | 65 | 18 | false |

These raw findings are preserved. All 41 distinct ambiguity entries map to the incumbent recognized opaque-read categories: filesystem roots, subprocess roots, a dynamic import, artifact traversal and a glob. There is no unrecognized or syntax-error ambiguity.

The incumbent exclusive-owner contract deliberately preserves declared finite paths and removes opaque fallback paths. Its coverage audit checks the concrete derived closure; it does not require an empty ambiguity list. The candidate covers every measured concrete path and retains the actual renderer inputs. This is owner-local closure qualification, **not execution of the full-repository planner or global closure gates**.

Normal hosted CI must supply contract-delta, unrun-suite audit, skip-only protection, trigger closure, curated-exclusive coverage and packing-ceiling results for the published head. The local proof does not manufacture those statuses or invoke held browser/APT/provider actions.

## Evidence bundle and remaining outcomes

The [JSON companion](options-ivspread-weight-validation-2026-11-11.json) retains source bindings and diffs, the 474-file qualified native input manifest, environment record, exact commands and logs, JUnit case results, real-input manifests/incidence/maps/writer receipts, the complete owner closure, CI-enrollment self-check and custody evidence. Reproducer scripts are included as evidence; their historical execution receipts remain separately identified.

The source repair and native proofs are complete at this publication. Exact-head hosted CI, any permitted controller merge, natural downstream build/deployment, and the owed production/browser consumer observation remain separate outcomes. The PR must not be described as deployed or PROVEN_LIVE based on these artifacts. Original held options work, provider operations, historical rewrites and scoring promotion remain outside this diff.
