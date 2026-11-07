# Running the acceptance contract later

`ACCEPTANCE.feature` is Gherkin for future owner-bound BDD execution. It is not a report of executed product tests. Bind its steps in the incumbent Terminal/Investigation/alerts test suites after implementation authorization; do not add a production test API, event bus or parallel state store to satisfy the wording.

## Required adapters

| Step family | Binding target | Evidence required |
| --- | --- | --- |
| Pins and draft validation | Existing `optionsContractShortlist` / `optionsPlanDraft` functions with source-valid synthetic rows | Original/canonical values, refusal reason and side-effect count |
| Payoff request/result | Existing `optionsPlanPayoff` functions; admitted proxy/producer test fixtures | Exact request/axis/source boundary; complete refusal vs qualified result |
| Native admission and Save | Original #804 owner test harness, journal and native revision API | Original request identity, retained payload, request count, exact receipt/readback and owner partition |
| Lost responses / auth changes | Existing mock transport or isolated authorized test backend | A controlled committed-or-not-applied outcome, not a guessed effect |
| Alerts and Review | Existing owner alert/receipt test adapters | Condition/revision, activation/firing and delivery facts independently |
| Browser paths | Existing app route and accessibility harness | Actual DOM, focus, dimensions, screenshots and owner responses at exact source/deployment |

Do not execute `@future_product` cases against production or any unresolved real operation. A test owner must have explicit admission for staged modifying effects. No such execution is included in the present assignment.

The production-before browser path was access-unverified, so normal-data functional proof is still required. Source reading and Paper composition are not substitutes for that proof.

## What can run now

From this directory, run:

```bash
python verify_oracle.py
```

This independent Decimal-based oracle checks the synthetic spread's signed payoff, entry alternatives, fixed-grid sample membership, break-even and quantity scaling. It has no network, credentials, persistence or product imports. Its passing output proves only those arithmetic fixture expectations. It does not prove installed contract reference coverage, current quote eligibility, consumer integration or any Save/watch behavior.

Future test reports must state source/owner/environment, cases actually executed, pending/skipped gates, exact evidence and whether an effect was known applied, known not applied or unknown. Preserve failed and refused evidence. Do not call a generated fixture an observed receipt.
