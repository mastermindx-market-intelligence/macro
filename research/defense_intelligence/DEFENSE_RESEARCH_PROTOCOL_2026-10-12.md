# Defense investor research — separate targets and an admission protocol

Status: **PROPOSED_FOR_INDEPENDENT_REVIEW; no evaluation or promotion**.
Assignment: Defense Procurement V3, delivery contracts Q0–Q4/A24–A30.
This proposal becomes a registration only when its exact Git revision, manifest
digest and independent acceptance are recorded before the affected outcomes are
opened. It is not a new evaluation owner, issuance ledger, signal or trade rule.
The existing `GRV-FA1` 4.1.0 registration and its amendment closure are unchanged.

## Questions and units

The product can be useful as a research workflow without predicting a stock
return. Stage progression, financial conversion, equity response and workflow
quality therefore have independent targets and verdicts. A supported result in
one cannot qualify another, and no aggregate conviction score is computed.

| Family proposal | Unit and primary target | Fixed horizon | Primary baseline | Score |
| --- | --- | --- | --- | --- |
| DPV3-STAGE-1 | One source-native FMS case: documented signed-case status after a notification | 365 calendar days after actual first house availability | Training-only stage/age base rate | Paired Brier-loss reduction, only if an admissible probability forecast exists |
| DPV3-FIN-1 | One exact issuer/segment/fiscal-period observation: subsequently reported segment revenue growth | Second fiscal quarter ending after issuance | Last available same-segment year-over-year growth; management guidance separately where genuinely comparable | Paired absolute-error reduction in percentage points |
| DPV3-EQUITY-1 | One deduplicated issuer/program/event cluster: security's adjusted total return relative to ITA | 63 US equity trading sessions from the first tradable entry after availability | Event-only and prior-return baseline, both frozen before scoring | Paired absolute-error reduction for a forecast; descriptive excess return otherwise |
| DPV3-WORKFLOW-1 | One blinded public-company research task completed with and without the product | One bounded task, maximum 45 minutes per condition | Existing source-reading workflow | Time to a defensible answer, conditional on noninferior source accuracy and omitted-risk rate |

These are proposed targets, not forecasts the product already emits. Missing
probabilities, segment comparability, lawful adjusted prices or an accepted
outcome source cause **NOT_EVALUABLE**, not a fabricated prediction or zero.
FMS notification amount is never a signed case or revenue label. A document's
silence about a signed case is **unobserved**, not a negative outcome. Signed
case disclosure requires an exact native case link; if no complete ascertainment
window exists, report bounds/censoring and withhold the binary verdict.

Financial growth is a reported-company outcome, not revenue attributed to one
procurement action. Margin, EAC charges, working capital and cash are separately
reported adverse/supporting outcomes with their own period, unit, accounting
basis and missingness. They have no primary-test switching power. A change in
segment perimeter or accounting basis without a reported comparable series is
ineligible for the growth target and remains in the exclusion denominator.
Financing, preferred claims and partial business sales are not sales revenue.

The new equity family does not pool into GRV-FA1 or reuse its sample size. The
existing family admits only exact-issuer positive funded action events from its
registered source rail. Ceiling changes, new awards, options, snapshots and FMS
observations retain their existing out-of-family treatment there. No Sharpe,
portfolio, position size, ranking or causal market-impact claim is created.

## Source and availability admission

Each input and outcome must retain owner contract/version, stable native ID,
source-document/version hash, exact supporting span, public release time where
evidenced, actual house first-seen time, effective time and correction lineage.
Missing first availability must not be filled with an event date, retrieval-now,
model inference or a producer generation clock. Existing point-in-time helpers
own cutoff semantics. The input cutoff precedes forecast issuance; an outcome's
later document cannot repair an incomplete issuance-time input.

The disclosed DoD publication delay is a source coverage limitation. An absent
recent row cannot establish no award, and a late discovery cannot be relabeled
contemporaneous knowledge. Bounded top-dollar and press-release collections are
their named populations, not the entire defense procurement universe. Report
all requested, retrieved, admitted, excluded, unavailable and censored counts.

Security identity, corporate actions, adjustment convention, exchange calendar,
market close, price rights and membership version must be bound by the existing
owner before any equity score. Ticker text or a current company lookup is not a
historical security or economic ownership path. Model-generated narratives may
describe the evidence but cannot admit facts or create outcome labels.

## Sealing, holdouts and contamination

Before a historical outcome is opened, the existing evaluation owner must accept
a manifest containing every input/outcome reference and hash, target definition,
eligibility decision, issuer/program cluster, availability cutoff, split and
exclusion reason. Store it with the research evidence in Git; do not create a
parallel ledger. An issuance record belongs to the existing accepted evaluation
path only after that owner admits its target contract.

This recovery has already inspected quartet Q2 financial summaries and current
program/FMS observations. Those documents and their derived facts are therefore
**exploratory**, not unseen holdouts. No result on them may be called an untouched
test or prospective validation. Historical reconstruction remains labeled as
such even when all timestamps are recoverable.

Split by connected issuer/program clusters before document splitting; repeated
announcements, amendments, source mirrors and related awards travel together.
Use an earlier development window, a later sealed temporal test window and an
issuer/program holdout within that later window. An outcome opened during
development permanently leaves the untouched test set. The manifest must name
the actual windows, group allocation and calendar before acceptance; insufficient
independent groups produces NOT_EVALUABLE rather than a convenient random split.

Each distinct source event counts once. Overlapping issuer/program/calendar
windows are clustered, and confidence intervals resample independent clusters,
not duplicate documents or rows. Include cancellations, de-obligations, no-change
observations, failures and unavailable outcomes under the frozen admission law.
An adverse outcome is never removed because it contradicts the narrative.

## Trial budget, precision and verdicts

The initial budget is one frozen full-input specification plus three declared
ablations (procurement-only, economics-only, and event/prior-price-only) for each
admitted family. Existing `engine/trial_ledger.py` records generated configurations
and their complete hashes before evaluation. Every generated variant consumes a
trial, including discarded variants; reuse is permitted only for the identical
configuration and inputs. The trial ledger is configuration accounting, not proof
of a prospective issuance or an accepted target adapter.

No primary verdict is permitted until a reviewer accepts a target-specific
minimum useful effect, loss scale, precision target and cluster-level sample-size
calculation using development data only. These must be numeric in the sealed
manifest. Values are deliberately not borrowed from GRV-FA1's return-distribution
assumptions or invented from the number of currently available rows. Until this
acceptance, all estimates are descriptive and the trial is NOT_EVALUABLE.

For an admitted numeric manifest: report the paired effect and cluster interval,
all baseline comparisons and the literal trial count; control the declared
co-primary comparison family at alpha 0.05 with Holm adjustment. Supporting
outcomes cannot replace a failed primary test. Report missing-outcome sensitivity
and complete-case results together. Insufficient precision or outcome coverage
cannot become a favorable verdict by dropping difficult cases.

The independent evaluator chooses one result per family:

- **NO_GO**: the registered rejection/futility condition is met, a claimed source
  relationship fails replication, or performance does not meet the useful-effect
  requirement with the accepted precision.
- **CONTINUE_PENDING**: admitted prospective observations need natural time or the
  already-registered accrual plan remains incomplete; show maturity and censoring.
- **QUALIFIED_FOR_RESEARCH_DISPLAY**: exact reproduction, source admission, useful
  effect, precision and all registered comparisons pass. This grants no trading
  or portfolio authority and does not qualify other families.
- **NOT_EVALUABLE**: source/target/rights/baseline/precision admission is absent or
  broken. This is visible product state, not a performance finding.

## Immediate acceptance frontier

There is no accepted DPV3 family issuance or evaluation in this change. Current
source readers, context metadata and the existing candidate audit ledger do not
constitute that proof. Next actions are to qualify exact outcome owners and
historical availability, produce the sealed manifest and development-only power
calculation, obtain independent acceptance, and then run the predeclared tests.
Do not dispatch historical rows as new prospective candidates to manufacture a
track record. Preserve pending natural-time obligations on their original owner.
