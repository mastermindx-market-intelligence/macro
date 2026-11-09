# Relative comparison integrity: unavailable is not a direction

## Implemented outcome

The R4 projection now qualifies the comparison number and both state labels together. A missing or invalid relative number cannot remain Leading, Lagging or Tracking in either language. Genuine finite zero remains a reported result. An explicitly supplied Building history state remains available in the canonical bilingual form.

The change belongs to the existing `lib/crypto_intelligence_view.py::build_view` owner. It adds no model, producer, browser controller or classification threshold. The producer and all saved HTML/JSON/JS/CSS artifacts remain unchanged; the fixture consumer proof runs the existing projection and renderer with synthetic contracts. This is source implementation and local workflow proof, not a data refresh or production cutover.

Source parent: `6ab9a6d09052aa66c556b26d371c5d59620622ee`. Frontend asset version remains `1bbbd2258e94`.

## Problem and cause

Previously, `finite(relative.change_90d_pct)` could produce null while the independent state fields were copied unchanged. The existing leaders filter correctly consumed the projected English label, but that projection could still say Leading Bitcoin with no usable numeric comparison.

Native parent falsifiers reproduced both visible failures: Overview showed the stale direction and the leaders filter included the invalid row. Optional non-dictionary relative containers could also raise an AttributeError and interrupt projection of an otherwise usable asset.

The producer review found a possible arithmetic path to the inconsistency: `_close` retains zero, negative and infinite numeric prices; `_relative_state` divides the joined series before validating the resulting ratio. A zero final Bitcoin denominator can therefore produce a nonfinite result and a directional label. That is a code-derived counterexample, not an assertion that retained real histories contain such observations. No histories were fetched and the producer was not executed or changed in this phase.

## One qualification decision

The existing coverage/date rule is reused unchanged. An asset must already qualify through its own coverage flag and valid date, and must not be later than a valid cockpit cutoff.

| Eligibility | Finite relative number | Supplied English state | Projected number and state |
|---|---|---|---|
| Fails existing coverage/date rule | Any | Any | null; Unavailable / 暂无 |
| Eligible | Present, including 0 and -0.0 | Any | Preserve the existing finite-value projection and supplied labels |
| Eligible | Unavailable | Exactly Building history | null; Building history / 积累历史中 |
| Eligible | Unavailable | Any other state | null; Unavailable / 暂无 |
| Eligible | Missing or non-dictionary relative container | None | null; Unavailable / 暂无; retain the asset |

The existing `finite()` helper rejects booleans, nonnumeric values and nonfinite values. The repair does not coerce numeric strings, use truthiness to decide zero, substitute 0, derive thresholds, infer paired observations or mutate source contracts.

For a null value, the two labels are one semantic decision. A raw Chinese Leading label cannot survive an English Building history state. Conversely, a Chinese Building history string alone cannot authorize that exception. Exact English state identity selects the existing canonical bilingual pair.

Building history describes the supplied state only. It does not establish a matched count, missing-data reason, refresh schedule or running background process. Finite-value label/translation disagreements are outside this bounded repair; the projection still does not independently validate the producer's classification.

## Consumer behavior and ownership

| Surface | Behavior proved |
|---|---|
| Overview | Invalid comparison shows unavailable; finite zero keeps its supplied Tracking state. Asset identity, risk and inspection remain. |
| Markets | Invalid relative number has no directional sublabel; zero stays 0.0%; supplied history appears as non-directional context. |
| Leaders filter | Only the qualified finite Leading fixture remains; unavailable and history rows stay in the underlying cohort. |
| Asset inspector | Relative value and state agree. Independent price, structure and risk remain visible. |
| Compare all assets | Includes all four synthetic assets, regardless of the leaders filter; null, zero, history and finite positive reading stay distinct. |
| Return and persistence | Close retains the filter context; no saved-snapshot storage write occurs. |

The existing JavaScript predicate remains untouched. Repairing the existing source projection makes every consumer receive the same qualified state; a second browser-side policy was unnecessary.

## Verification

Parent baseline with the new falsifiers: **18 failed, 14 passed, 169 deselected**, 4.54s pytest / 4.952s subprocess. Fourteen failures expose source qualification/container behavior; four expose the bilingual Overview/filter paths. Four browser contexts/pages, zero page errors or external/WebSocket traffic.

Initial candidate: **69 passed, 2 failed** from 71 selected cases, 6.72s / 7.117s. All **67 contract cases** passed, retaining the original 39 and adding 28. Both leaders-filter cases passed. The two remaining failures were test indexing: a broad `dd` selector included the two collapsed calculation-rule definitions before the inspector's own seven fields.

Corrected affected run: **2 passed**, 4.24s / 4.655s. The selectors now target the inspector's direct definition list. Product source and frontend assets were unchanged. The initial browser input is archived, and the three selector corrections are recorded.

The JUnit union establishes **71 unique passing cases: 67 contract + four browser** across those two candidate runs. This is not a single all-passing 71-case run and not a rerun of the whole browser suite. The initial four contexts/pages and corrected two contexts/pages all have zero errors/external/WebSocket traffic.

Two native drawer crops were inspected: English unavailable relative evidence at 390px and Chinese supplied history at 320px. They are explicitly synthetic contracts; the symbols/prices in these fixtures are not current market quotations.

Three ordered projection transformations invert to the exact source parent. Only the projection and two test files change in the runtime/test input set. **Eighteen other inputs remain exact**, including saved HTML/JSON/JS/CSS, templates, builder and shared assets. Python syntax parses. No producer/H5/model threshold or authority rule changes.

## Remaining build work

1. **Overview field clarity.** Its compact unlabelled “Unavailable · Stressed” summary can still be ambiguous. Add short field labels in the existing paragraph so the unavailable state clearly belongs to the BTC comparison, with a separate risk label. Preserve existing values/actions and native narrow wrapping.
2. **Producer numeric validity.** Separately validate finite positive price observations and ratio endpoints/results within the existing producer owners. Preserve true zero/negative returns, actual last usable dates and asset identity. Rejecting a bad latest observation must not stamp an earlier usable reading with the rejected date.
3. **Missing trend input.** At exactly 30 asset observations, the 30-step change requires a 31st observation. The producer's current `or 0.0` turns missing evidence into a failed vote. A separate bounded fix should withhold an unqualified trend rather than recalculate thresholds from fewer votes. Existing qualified classifications must remain stable.
4. **Paired-window receipt.** Implement actual matched endpoints/counts and Bitcoin source/identity/price basis in the existing producer contract before promoting the proposed Paper receipt. Neither this projection repair nor a copied coverage date supplies that evidence.

The last three items remain findings/plans, not implemented claims. H5/model, alerts, public-route cutover, hosted/independent visual acceptance, admission and release remain held.

## Evidence

- [Exact source, runs and qualifiers](RELATIVE_INTEGRITY_VALIDATION.json)
- [Parent baseline](relative/BASELINE.txt)
- [Initial candidate output](relative/INITIAL_CANDIDATE.txt) and [JUnit](relative/CANDIDATE_RESULTS.xml)
- [Corrected affected JUnit](relative/FOCUSED_RESULTS.xml)
- [Exact initial browser test input](relative/INITIAL_BROWSER_TEST.py)
- [Source and test-selector transformations](relative/SOURCE_TRANSFORMS.json)
- [Publication and capture receipt](relative/PUBLICATION_RECEIPT.json)
- [Inspected synthetic captures](relative/captures)
