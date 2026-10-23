# Communications A1 — Guidance Selection Can Reverse the Answer

**Date:** 24 September 2026. **Carrier:** Macro #7794.
**Operation:** `gmi-communications-research-20260923-sol-001`.
**Status:** Original primary-source research and a reproducible reference counterexample. Not an application implementation, a complete historical guidance archive, consensus surprise or stock recommendation.

## 1. Why this matters to the investor

A source can report one quarter's result and issue the next quarter's outlook in the same document. Choosing the newest guidance text before matching the target period can reverse the apparent answer to “Did the company deliver?” Three concrete examples from the selected A1 sources demonstrate the problem.

All comparisons below concern the **published figures**, not an assertion of unrounded underlying precision. Old and new company guidance retain their issue date, measure, units, target period and bound type. No native retention/knowability or identity receipt is created by this study.

## 2. Original outlook, actual result and new outlook

Amounts in USD millions. The original outlooks target **1 April–30 June 2026**. The outlooks issued with the Q2 results target **1 July–30 September 2026**. TTD and Magnite detailed actuals originally use USD thousands and are explicitly divided by 1,000 in this table.

| Company and measure | Original Q2 outlook, issue date | Reported Q2 actual, release date | New Q3 outlook issued with result | Correct Q2 delivery reading | Wrong reading using newest guide |
|---|---|---|---|---|---|
| Meta consolidated revenue | 58,000–61,000; 29 April | 60,801; 29 July | 61,000–64,000 | Within original range | Below the Q3 lower bound |
| The Trade Desk revenue | At least 750; 7 May | 715.057; 6 August | At least 650 | Below original floor | Meets the Q3 floor |
| Magnite contribution ex-TAC | 177–181; 6 May | 189.595; 5 August | 188–192 | Above original ceiling | Within the Q3 range |

Sources: Meta M1Q/M2Q, TTD T1Q/T2Q and Magnite MG1Q/MG2Q from the accompanying accounting study. The current Q2 releases explicitly name the new Q3 outlook. The selected Alphabet source set does not supply a matched numerical revenue-outlook sequence; preserve that absence and the four-company roster rather than invent a fourth comparison.

These are not merely different ways to describe the same result. The wrong column answers a different-period question and must not be displayed as Q2 delivery. Matching issuer and a familiar metric label does not cure the mismatch.

## 3. Correct selection order

Within the existing guidance/evidence owner and its accepted comparison recipe:

1. Select the user question and target period first: original-guide delivery, latest-qualified-pre-result-guide delivery, or forward trajectory.
2. Match the economic subject, reporting perimeter, metric definition, units/scale and bound type.
3. Apply the appropriate source, recorded/knowable, correction and selection cutoffs. A date-only record does not certify an intraday pre-result ordering.
4. Select the appropriate issuance among eligible candidates. “Newest source” is not step 1.
5. Emit the selected source identity, original issue date, target and basis with the output. No suitable candidate means unavailable—not a substitution from another quarter.

This is a refinement of existing CRV-04/09/17/23/24/47/49/51, not another guidance store, selector service or runtime authority. The Semiconductor-led shared guidance path remains the dependency. A current-cache entry cannot serve as an original-vintage archive unless its existing owner supplies that evidence.

The original Q2 guides in this example are directly located. A complete search for all intervening guidance changes has **not** been performed. Accordingly the correct label is “against original company outlook,” not “against the final outlook before results” or “against analyst consensus.”

## 4. Preserve a useful forward-looking question without calling it a result

Cross-period comparisons are not inherently useless. They simply need a different, explicitly reviewed question: **How does the new company outlook relate to the just-reported business level?**

Using the printed figures only:

- Meta's Q3 range is above its reported Q2 revenue. A displayed sequential comparison may show the range-relative change, with no claim that Q3 has occurred or that seasonality/market expectations are favorable.
- TTD's new floor is below Q2 actual revenue. A floor is only a lower bound. It does not provide a point forecast or upper bound, so it does **not prove management predicts a revenue decline**. A next-quarter outcome above Q2 would still satisfy that floor.
- Magnite's Q3 range includes its reported Q2 contribution. The range permits either a modest increase or decrease from that level. Its midpoint is not automatically the company's expected value or a probability-weighted forecast.

A useful UI can show both **Delivery against the prior period's original outlook** and **New outlook for the next period**. Neither may overwrite the other or silently borrow a peer's definition. No “beat” or “miss” label belongs on the forward-trajectory panel.

## 5. Executable reference experiment

The following standard-library experiment checks the displayed-value counterexample. It is not the accepted product comparator. Its simple target check illustrates the requirement; actual production must use native target/identity/clock/rule receipts, not copy these research strings as proof.

```python
from decimal import Decimal as D

Q2 = ('2026-04-01', '2026-06-30')
Q3 = ('2026-07-01', '2026-09-30')
# name, actual, original low/high, new low/high, original label, wrong label
CASES = (
    ('Meta', '60801', '58000', '61000', '61000', '64000', 'WITHIN_RANGE', 'BELOW_RANGE'),
    ('The Trade Desk', '715.057', '750', None, '650', None, 'BELOW_FLOOR', 'MEETS_FLOOR'),
    ('Magnite', '189.595', '177', '181', '188', '192', 'ABOVE_RANGE', 'WITHIN_RANGE'),
)

def documentary_label(value, low, high):
    value, low = D(value), D(low)
    if high is None:
        return 'MEETS_FLOOR' if value >= low else 'BELOW_FLOOR'
    high = D(high)
    if high < low:
        raise ValueError('invalid_range')
    return 'BELOW_RANGE' if value < low else 'ABOVE_RANGE' if value > high else 'WITHIN_RANGE'

def delivery(value, actual_target, low, high, guide_target):
    if actual_target != guide_target:
        return 'REFUSED_TARGET_PERIOD'
    return documentary_label(value, low, high)

for name, actual, old_lo, old_hi, new_lo, new_hi, old_result, wrong_result in CASES:
    assert delivery(actual, Q2, old_lo, old_hi, Q2) == old_result
    assert documentary_label(actual, new_lo, new_hi) == wrong_result
    assert delivery(actual, Q2, new_lo, new_hi, Q3) == 'REFUSED_TARGET_PERIOD'
    assert old_result != wrong_result
    print(name, old_result, '!= wrong latest-guide:', wrong_result)
# Lower bound below previous actual does not imply a declining next outcome.
assert D('800') >= D('650') and D('800') > D('715.057')
# A range crossing prior actual permits both signs; midpoint is no distribution.
assert D('188') < D('189.595') < D('192')
assert D('61000') > D('60801')
print('15 reference assertions passed; 0 product tests run')
```

## 6. Remaining qualification and next use

This phase proves the source-level example and runs the reference arithmetic; it does not prove a production bug exists. The future Task 3/4 tests should include these exact adverse selections after native fixture adaptation. The current shared implementation is not modified or assessed by this example.

The next historical study needs version-complete issuer guidance events across a stated selection window, explicitly dated source corrections, definition/perimeter changes, and original accepted clock evidence. That later study can distinguish original from final-pre-result delivery. Predicting subsequent operations, establishing consensus surprises and improving stock selection remain separate validation questions.

The Chairman will manually deliver the eventual package to a **new Fable session later**. No delivery, new receiver or request to the Semiconductor session is initiated by this document. Sol retains Communications work and the original broader sector mandate.
