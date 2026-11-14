# FINRA producer and disclosure composition — #11061 / #11050

## Outcome

The scoped consumer now explains producer coverage for latest ratio, recent window, baseline window, and historical z-score in fixed English/Chinese copy. A withheld z remains visible with its reason. Supported measurements stay visible; a displayed rounded zero never creates a measured-zero claim.

The composed native source passes **133 tests / zero skips**, using Python 3.14.7 and actual Node v26.5.0. Candidate tests against the original consumer template and the same repaired producer give **17 failures / 116 passes**. Those 17 failures include repeated calls into the shared new disclosure contract, not 17 separate defects.

The published producer contribution at `45ca874522907687393960e33222ac4e88cd614b` and original consumer contribution at `1a346ad7aa6cfac1bb57f630e916ada3d67017ae` are preserved. The composition uses main `16e874433e0ff0fb0ad863b839deb1d16f824005`, retaining unrelated main changes including the #10918 flow-surface closure. Existing original commits and the producer's two proof files remain attributable.

**Draft and unarmed.** Composed natural CI, full-page/browser acceptance, and any covering production render remain distinct. No independent-review ceremony is added; no actual repository or release hold is cleared by these native results.

## Consumer behavior

- Coverage is shown in the fixed order latest → recent → baseline → history_z.
- Only recognized scopes/states receive fixed translated copy. Incoming reason strings, unknown enum names and arbitrary keys are never inserted into HTML.
- The historical-z row renders when a numeric z exists or its scope has a recognized qualification. A withheld value uses the existing localized unavailable display.
- With no recognized scoped note, a recognized legacy top-level error gets a generic qualification without an invented scope.
- Original partial-history and genuine-zero notes remain unchanged.
- Original numbers, trend formatting, thresholds, clock escaping and row helpers remain unchanged.

The Node harness now executes the **actual template helper section**, including localization, escaping, numeric markup and row formatting, as well as the actual short-flow block. It no longer substitutes those helpers. Baseline parity is explicitly enabled during qualification: **604 full-HTML cases** are identical, and **600 legacy-error cases** preserve their numeric rows while intentionally gaining explanations.

## Actual producer → consumer path

Sixteen fixtures begin with valid rows admitted by the actual FINRA parser. Retained missing/corrupt examples are then explicitly introduced into the temporary store; the proof does not pretend fresh malformed rows pass the repaired parser.

Every case runs real Parquet → `panel_state` → `signal_map` → actual `_load_short_volume` → `_positioning` → strict JSON → shipped EN/ZH JavaScript. A nonempty direct signal map must equal the catch-all loader result.

Cases include healthy and short history; genuine recent zero; positive volume rounded to 0.0%; missing numerator/denominator; all-missing pairs; infinite volume; an old invalid pair outside the calculation windows; invalid cached latest ratio; optional latest-ratio fallback; baseline-only missingness; mixed invalid/missing precedence; a recent zero window; latest-only zero with a nonzero recent window; and absence of the optional ratio column.

Discriminating outcomes include:

| Case | Preserved reading and disclosure |
|---|---|
| Old invalid pair outside 20 rows | Latest 50.0% and zero trend remain visible; only z is withheld and qualified. |
| Invalid stored latest ratio | Latest/z unavailable; valid zero trend remains. |
| Baseline missing | Latest 50.0% remains; trend and z are qualified as unavailable. |
| Optional latest ratio absent | Existing 54.0% recent-window fallback, 3pp trend, and partial-history state remain. |
| Rounded positive / latest-only zero | Displayed 0.0% does not gain the recent-window zero note. |
| Genuine recent zero | Original measured-zero note remains. |

## Committed-panel consumer parity

The already-qualified real producer output covers **171,946 panel rows and 1,545 tickers**. Its positioning JSON SHA-256 is `1450a8574935684fc7dc22dd30443d05947583e93d49046bc44f15c20d018f30`; the exact digest is checked before reuse, so accepted producer/data work is not silently replaced or remeasured.

All **3,090** actual ticker/language renderings are byte-identical between the original and extended consumer, including its production helpers:

- EN: 1,545 identical; HTML-map SHA-256 `40608d73f8f49267f144b6a7a7a29d0846dcbf766d70c00388ad05582df84f28`.
- ZH: 1,545 identical; HTML-map SHA-256 `fdaaffb87e9a721a15cf340b51b38872b17c6a857bf061c4909f5e41349e72b2`.

The pinned real panel has no paired-input defect. The adversarial cases establish the changed behavior; real-panel parity establishes preservation of the existing populated output. Neither is an out-of-sample trading result.

## Style compatibility and preserved effects

The exact short-flow blocks in the current main template and #10654's `9cd1c665595933532a2186164deb1dce18962708` template are identical before disclosure composition. Applying the original disclosure plus this extension to the style variant preserves **all bytes outside that block**. The real Node harness passes **1,238 cases** on that union, including the same 604 full-HTML and 600 numeric-row parity cases.

This is a bounded source/helper compatibility result, not validation of #10654's complete style delivery or browser layout. Its original unknown native completion effects and protected-asset access denial remain untouched. No style branch or generated site files are changed.

The producer's original CI **43091844204** was still running at **20:52:13 UTC**. It remains on its original carrier and is neither cancelled nor replayed. Its old proof is not relabeled as composed-head CI.

## CI selector completion

The existing CODE owner `c19-wp24-consumer-states` gains exact selectors for `tests/test_short_flow_disclosure.cjs` and `templates/stock.html.j2`, covering the Python → Node → template boundary.

The actual loader measures **401 owners / 328 CODE owners**, other **400 definitions/weights unchanged**, the same two owner commands, and owner weight **6 → 6**. Selector-only marginal weight is zero. The producer's already-funded +2 remains the sole adjustment: ceilings **5968 / 5991 / 5726**, existing job/pack limits, baseline and CI-pack test bytes all remain unchanged from the donor.

The outer workflow already accepts test/template changes. Its hosted/non-PC route already sets up Node 20; the PC route keeps its existing runtime owner. Native zero skips proves Node ran locally. A later successful hosted step must still be checked for actual Node-dependent test execution before claiming hosted consumer proof.

Full-tree inference, packing and composed semantic qualification remain with natural CI; no local full-tree planner execution is claimed.

## Evidence and limits

The companion JSON contains exact source blobs, native log hashes, all 16 positioning payloads and both rendered-language outputs, real-panel render hashes, the style-union receipt, selector accounting and executable audit source. Producer [#11072](https://github.com/mastermindx-market-intelligence/macro/pull/11072) retains its historical paired-volume reports unchanged.

These are native producer/consumer results. Full-page bootstrap, browser interaction, responsive layout, production render and deployment are not established. Existing browser restrictions were not retried or bypassed. No GitHub approval, native auto-merge, controller arming or release-hold clearance occurred.
