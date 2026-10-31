# R6: qualify correction magnitude from the actual quantity evidence

**Disposition: DRAFT / HOLD-FOR-SOL. Bounded source review complete; broad integration acceptance is held.**

This extends the R4 trigger-accumulation repair in #9732. It fixes a separate problem: an observed source correction could arm a “reduces magnitude” condition merely because a quantity fingerprint existed. Missing, unchanged, increased or incomparable amounts could therefore receive an unsupported direction. The display also attached an invented date and repurchase-specific language to generic corrections.

## What changed

The producer now preserves the original canonical point/range quantity objects in the leaf's `quantity_terms`, including units, basis, declared period and source-evidence fields. It deep-copies each quantity alongside its derived legacy scalar; the first-currency convenience field is retained for existing consumers but is not comparison authority. The producer identifies the changed output as `ni-producer-facts-2`.

The thesis owner qualifies only a currently live correction and its exact predecessor leaf. It requires matching templates, non-negated leaves and quantities, exact finite nonnegative scalar/structured agreement, explicit matching base-currency units, matching total or incremental basis, and the same supported declared issuer fiscal year or quarter. Bounds, ranges, missing evidence, unsupported periods/bases, incompatible terms and missing leaves remain unqualified. No fallback to the current view payload or to a fingerprint is allowed.

The amount condition and its evidence IDs now come from the same qualified correction set. An unrelated correction cannot inherit a reduction's evidence, and a retired reduction cannot remain armed solely through historical attachment. Generic correction copy is neutral and source-specific fabricated dates are removed.

The supported factual conclusion is deliberately narrow: a currently live correction states a lower exact monetary amount than its immediate predecessor under matching supported terms and the same declared issuer fiscal period. This does not establish economic deterioration, stock direction or entry eligibility.

## Verification against this source

| Evidence | Result |
| --- | --- |
| Focused thesis + producer-facts suite, PID 38780 | **138 passed**, exit 0; two inherited pytest temporary-directory cleanup warnings |
| Newly added cases | **48**, in the actual producer-facts test module |
| Combined NewsImpact / consumer / entry run, PID 4076 | **1,251 passed / 1 failed**, exit 1; two inherited cleanup warnings |
| Four unchanged R5 CLI requests through composed R3/R5/R6 source, PID 89448 | All four captured successfully; request bytes unchanged |
| Bounded C3 source review | Concurrence for comparison/evidence guards; reviewer did not execute tests |
| Standalone synthetic replay, PID 59264 | 13 behavior checks, 32 condition/theme/width combinations, no browser errors |

The regression path adapts schema-valid synthetic events through the actual producer leaf function, then **explicitly constructs validated correction records through the fact-log API**. It is not proof that stage two natively identifies corrections. Nonfinite cases demonstrate request refusal rather than a published unarmed result.

The original R5 captures are unchanged. The new captures preserve entry and peer JSON and the input digest; the three observed news triggers survive while the unsupported reduction warning is withheld. Missing peers preserve current news; missing history preserves the current case but withholds the comparison; missing current news never substitutes historical content. The positive monetary-comparison path is covered separately by the owner tests, not by these legacy scalar-only CLI cases.

The combined proof is a research composition, not a merged or deployed runtime. `composition-manifest.json` names the exact R5 consumer, R3 entry and R6 source bytes. Omitted checkout dependencies were restored unchanged from the pinned R5 head: `collectors/` and the 113 tracked NewsImpact research-fixture files. No gold labels or frozen registration were changed.

## The remaining registration conflict is intentional and blocking

The single combined-suite failure is:

`tests/test_news_impact_section11.py::test_committed_registration_matches_a_rebuild`

The existing Section 11 registration names `ni-producer-facts-1`; the current implementation names `ni-producer-facts-2`. Its whole-text rebuild check correctly detects that difference.

This repair preserves the frozen registration, the registration code and the failing drift check. It does not roll the producer version back, relabel it as a narrower identifier, update benchmark inputs, change thresholds, skip the test or claim qualification under the frozen report. Independent source advice concurred with retaining this hold. Historical producer profiles, current implementation identities and any future registration require a separate owner-reviewed contract change.

## Reproducing the composition

Use the exact heads and source hashes in `composition-manifest.json`. The current consumer is #9616 at `a073abedc58d945b10eb27380d49b879754c5bcc`; the entry owner is #9731 at `d4d43810c18f8e48b8cf49fa447392f7901f6b97`; the news carrier is #9732 based on `28f35fd86233cae3a42078966538cd8248c3f738` with this directory's recorded R6 source bytes.

Run the focused and combined commands in `verification.json`. From that composed tree, run:

```bash
python research/catalyst_intelligence/news_magnitude_r6/capture_replay.py
```

The capture script refuses mismatched critical source hashes and verifies the original request digests. It writes only this research lane's fixtures. It does not acquire native feeds or write publisher input.

## Remaining native dependencies

The actual producer constructs `FactObservation` without forwarding explicit correction intent and predecessor identity. Stage-one novelty can be provisional; blindly promoting model novelty into admitted correction history would cross the existing evidence boundary. A native acquisition/classification contract must establish that lineage before a real correction case can exercise this path.

Also outstanding are a compatible native B4 availability projection, owner-admitted peer formation and synchronized prices, authentic current/prior NewsImpact cuts, and authenticated source-to-client correction delivery. This repair enables none of those by itself. All assessment authority flags remain false and no lane, ranking, model qualification, order or release is activated.
