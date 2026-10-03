# MedTech Catalyst Intelligence R1 — regulatory authorization is not an investment thesis

**Date:** 2026-09-29
**Operation:** `ci-w1-medtech-r1-20260929-sol-001`
**Program:** Catalyst Intelligence / Medical Devices and Diagnostics
**Readiness:** research contract and executable reference only; no forecast, recommendation, production, or Paper acceptance

## 1. Question resolved in this installment

How should Catalyst Intelligence represent a medical-device regulatory event without collapsing:

1. FDA pathway and decision;
2. public knowledge time;
3. device/applicant/rights-to-listed-issuer identity;
4. issuer materiality;
5. manufacturing, launch, reimbursement and adoption readiness;
6. market expectations and price reaction; and
7. investment recommendation admission?

R1 resolves the minimum contract and supplies a tested reference. It does **not** estimate a probability of approval, conditional equity values or a stock recommendation.

## 2. Primary-source distinctions that must survive implementation

### 2.1 Approval, clearance, De Novo and registration are different facts

FDA describes PMA as its most stringent premarket review and bases approval on sufficient valid scientific evidence of safety and effectiveness for Class III devices. A 510(k) instead asks whether a device is substantially equivalent to a legally marketed predicate. De Novo classifies a novel low- to moderate-risk device. Establishment registration or device listing is not approval, clearance or authorization.

Primary anchors:

- FDA PMA: https://www.fda.gov/medical-devices/premarket-submissions-selecting-and-preparing-correct-submission/premarket-approval-pma
- FDA 510(k): https://www.fda.gov/medical-devices/device-approvals-and-clearances/510k-clearances
- FDA approvals/clearances databases: https://www.fda.gov/medical-devices/products-and-medical-procedures/device-approvals-and-clearances
- FDA explanation of registration versus approval/clearance: https://www.fda.gov/medical-devices/consumers-medical-devices/are-there-fda-registered-or-fda-certified-medical-devices-how-do-i-know-what-fda-approved

**Ruling:** production vocabulary must preserve the pathway-native verb. A 510(k) is `cleared`, not `approved`; a De Novo request is `granted`; PMA/HDE decisions may be `approved`. An invalid pathway/decision pairing is refused rather than normalized into a generic positive event.

### 2.2 Original PMAs and supplements are not interchangeable

FDA's PMA database distinguishes original applications and supplements, and lists supplement type/reason. A supplement can expand an indication or change a device/manufacturing process, but its economic significance depends on the exact change and the issuer's existing base.

Primary anchors:

- FDA PMA approvals/database fields: https://www.fda.gov/medical-devices/device-approvals-and-clearances/pma-approvals
- FDA PMA supplements and amendments: https://www.fda.gov/medical-devices/premarket-approval-pma/pma-supplements-and-amendments

**Ruling:** `PMA_ORIGINAL`, `PMA_PANEL_TRACK_SUPPLEMENT` and `PMA_OTHER_SUPPLEMENT` are separate pathway values. The system cannot infer “new platform launch” from the word `approval` alone.

### 2.3 Regulatory success does not establish commercialization or equity materiality

A marketing decision can precede manufacturing scale, launch readiness, reimbursement/coverage, physician training, hospital budget approval, procedure growth, installed-base conversion and consumables pull-through. The same regulatory event can be company-defining for a focused small issuer and immaterial for a diversified company.

**Ruling:** the case contract carries regulatory state, commercial readiness and issuer materiality separately. Commercial evidence must bind the same listed issuer, security, retained-rights relationship, device, applicant, submission, indication, territory and regulatory source before readiness can qualify. A missing, mismatched, future or explicitly unresolved rights relationship also prevents commercial readiness from being projected as qualified for that listed case. Positive authorization with missing or mismatched commercial binding is `AUTHORIZED_AWAITING_COMMERCIAL_PROOF`; unresolved issuer materiality is `REVIEW_MATERIALITY`; an immaterial event is `CONTEXT_ONLY_IMMATERIAL`.

### 2.4 Public knowledge time is its own clock

Decision date, database refresh, advisory-panel scheduling, rights evidence, materiality evidence, commercial evidence and market observation are distinct clocks. Historical analysis uses only facts with a timezone-qualified public or observation timestamp no later than the case cutoff. Later regulatory, rights, materiality, commercial or options facts cannot be backfilled into an earlier case.

**Ruling:** the event, rights relationship, materiality evidence and commercial evidence each require their own qualified clock; a supplied options layer requires a qualified observation clock. Missing or timezone-naive clocks are refused. Any layer later than the analysis cutoff makes the case `WITHHELD_TEMPORAL`. A future event also redacts decision state, marketing status, positive-decision flag, event timestamp and event source—including any nested relationship projection of that source—rather than returning the withheld outcome through another field.

### 2.5 Listed-security exposure must be case-bound and evidence-backed

A nonempty ticker, issuer id or `owned`/`licensed` enum does not prove that the listed security retains economics from a specific device decision. The relationship must bind evidence-side issuer and security identifiers to the top-level listing and bind the exact device, applicant, submission, indication, territory and regulatory source to that listing. It must carry a stable relationship id plus source provenance. Licensed rights also require a specific license-term identity. Materiality requires its own source, clock and basis rather than inheriting from the rights assertion.

**Ruling:** any missing or mismatched relationship field—including issuer or security identity—makes rights `unresolved` and materiality `unknown`; the case becomes `WITHHELD_IDENTITY_RIGHTS`. An explicitly unresolved or not-yet-public rights state also keeps the relationship and materiality evidence unresolved even when the remaining identifiers are syntactically complete; public materiality provenance cannot become a resolved relationship-dependent claim before the rights join is cutoff-qualified. Materiality evidence must separately bind its issuer, security and retained-rights relationship to the listed exposure; missing, mismatched or inconsistent materiality provenance makes materiality `unknown` and the case `REVIEW_MATERIALITY`. Claimed rights and materiality are never accepted from enums, an arbitrary source id or an unbound listing id alone.

### 2.6 Options and positioning are expectations evidence, not native regulatory evidence

Observed event-expiry alignment, implied-volatility term structure, skew, open/close classifications and other qualified market evidence may help measure expectations, reaction amplification or timing. They do not become clinical/regulatory evidence and cannot directly rewrite the native event probability.

**Ruling:** qualified options input is labeled `expectations_reaction_and_timing_only`; the executable reference hard-codes `can_change_native_event_probability=false`. Only `None` means the optional layer is absent. Every supplied mapping—including `{}`—must carry complete timezone-qualified observation and provenance fields, must be no later than the case cutoff, and is redacted when temporally withheld. Estimated observations remain context-unqualified rather than silently used.

For R1, options qualification is deliberately fail-closed: only `coverage=listed-options-complete-for-snapshot` with `latency=t_plus_1` is admitted as qualified context, and both fields remain in the returned expectations receipt for audit. Any other nonempty coverage or latency value is retained but marked `UNQUALIFIED` until a later source-backed contract explicitly admits it. The options snapshot must also bind its evidence-side issuer and security identifiers to the exact listed exposure; mismatched listing identity remains `UNQUALIFIED` and cannot inform reaction/timing.

### 2.7 Market revisions stay inside the frozen snapshot

A price observation is another point-in-time fact. Attaching a later price to a case while leaving the earlier case cutoff unchanged creates hidden look-ahead, even when the revision does not alter regulatory or commercial fields.

**Ruling:** `apply_market_revision` accepts an identified market-observation receipt containing security id, source id, finite positive reference price and a timezone-qualified observation at or before the case's own `as_of`. The market security must match the case exposure exactly, and the returned revision retains security/source provenance for audit. NaN, infinities, wrong-security observations and later observations are refused; producing a later snapshot requires re-qualifying the whole case at that later cutoff rather than partially advancing only price.

## 3. Worked historical mechanism — TransMedics OCS Heart

The existing repository autopsy `research/winners/cases/TMDX_2021.md` is a useful positive-and-adverse mechanism, not a model-training label by itself.

- FDA scheduled the OCS Heart advisory panel for 2021-04-06, creating a clean expectation catalyst.
- The panel vote was favorable but not uniformly strong, including a 9-7 safety vote.
- Heart and Liver approvals ultimately arrived, but approval-related gaps did not hold over ten sessions in the repository's measured tape.
- Revenue and commercialization timing lagged the regulatory de-risking; the 2021 market had capitalized part of a later revenue curve too early.

Primary FDA anchors:

- Advisory-panel meeting: https://www.fda.gov/advisory-committees/advisory-committee-calendar/april-6-2021-circulatory-system-devices-panel-medical-devices-advisory-committee-meeting
- OCS Heart PMA information: https://www.fda.gov/medical-devices/recently-approved-devices/organ-care-system-ocs-heart-system-p180051s001

**Mechanism learned:** the investable target is not “FDA positive.” It is the joint path from regulatory de-risking through launch timing, transplant-center adoption, procedure utilization, disposable/service economics, gross margin and the valuation already embedded in the share price. Anticipation, announcement reaction, commercialization and durable rerating require separate labels.

## 4. Executable R1 reference

Files:

- `research/medtech/medtech_catalyst_reference_r1.py`
- `research/medtech/test_medtech_catalyst_reference_r1.py`

The pure reference:

- enforces pathway-native decision vocabulary;
- applies the case cutoff independently to event, rights, materiality, commercial and supplied options evidence;
- redacts future decision-derived and future layer-derived fields rather than returning them beside a withheld disposition;
- requires an evidence-backed relationship binding device, applicant, submission, indication, territory, regulatory source and listed security;
- requires separate rights and materiality provenance, including evidence-side issuer/security/relationship identity and a bound license term for licensed rights;
- requires commercial evidence to bind the exact qualified regulatory case before readiness can qualify;
- keeps issuer materiality separate from authorization;
- keeps manufacturing, launch, coverage and adoption separate;
- distinguishes an omitted options layer from a malformed supplied mapping;
- refuses to turn options context into native regulatory probability;
- permits only cutoff-qualified market-price revisions and never rewrites regulatory, rights, materiality or commercial evidence;
- never emits a probability, conditional equity value or recommendation.

Verification in a clean scratch root:

- `python3 -m pytest -q test_medtech_catalyst_reference_r1.py` → **52 passed**;
- discriminating cases cover sixteen harmful families:
  1. accepting `approved` as a 510(k) state;
  2. returning future decision fields despite a withheld disposition;
  3. leaking a future event source through a nested relationship projection;
  4. admitting future rights, materiality, commercial or options evidence;
  5. accepting claimed rights/materiality without exact regulatory-case relationship and provenance;
  6. letting an unrelated issuer or security inherit another listing's device rights;
  7. resolving materiality from evidence bound to another listing or relationship;
  8. qualifying commercial readiness from evidence bound to another case;
  9. treating an empty supplied options mapping as an omitted layer;
  10. allowing options context to change native event probability;
  11. attaching a market observation later than the frozen case cutoff;
  12. accepting NaN or infinite market prices;
  13. projecting known materiality through an explicitly unresolved rights join;
  14. projecting commercial readiness through an unresolved or future rights relationship;
  15. presenting materiality evidence as resolved before a future rights join becomes public;
  16. treating every authorization as commercially ready.

These tests establish contract behavior only. They are not independent review, source coverage, historical calibration or investment performance.

## 5. R1 architecture decisions

1. **Case identity:** device + exact regulatory submission/decision + indication/version + applicant + territory + retained-rights relationship + listed issuer/security. The relationship has its own evidence-side issuer/security identifiers, id, source, clock and, for licensed rights, license-term identity. Applicant or ticker text alone is not security identity.
2. **Knowledge clocks:** event, rights, materiality, commercial and supplied options evidence are separately timestamped and cutoff-checked. Future evidence is redacted, not merely labeled withheld.
3. **Native targets:** regulatory outcome, time-to-decision, launch readiness, commercial adoption and persistent rerating remain separate.
4. **Commercial bridge:** procedure/patient volume × realized price × recurring consumables/service, less launch/manufacturing/service costs, reimbursement friction and dilution. Commercial evidence carries an exact case binding; installed base is not revenue without utilization.
5. **Materiality:** focused/core, material, immaterial and unknown are explicit states backed by separate source/clock/basis plus issuer/security/relationship identity. Unknown never becomes zero or “small.”
6. **Market layer:** expectations and price reaction are overlays. A price-only update must remain within the frozen case cutoff and does not revise regulatory, rights, materiality or commercial evidence.
7. **Recommendation layer:** admission requires later calibrated probabilities, conditional diluted-equity values, priced-in comparison, costs/liquidity and accepted policy. R1 always returns `recommendation_eligible=false`.
8. **No new platform:** use incumbent identity, event, financial, options, recommendation, evaluation and publication owners. This reference is not a production kernel.

## 6. Next research unit

R2 should build the first reconstructable cohort and denominator:

1. choose one material family—recommended: PMA originals plus panel-track supplements for listed issuers;
2. freeze separate event, rights, materiality, commercial and market-observation clocks and define how withdrawals, denials, pending cases and missing public submissions are represented;
3. bind exact device/applicant/submission/indication/territory/rights/issuer/security identities across rights, materiality and commercial evidence, including evidence-side listing identifiers, source provenance and license-term identity where applicable;
4. construct positive, adverse, delayed, commercially weak and immaterial diversified-company cases;
5. measure anticipation, announcement reaction and durable 3/6/12-month excess returns separately;
6. build a deterministic revenue/materiality bridge and an explicit abstention policy;
7. produce the first native MedTech detail/timeline/scenario/revision design on an admitted Paper window.

A 510(k)-wide scraper should not be the first vertical: high event volume, predicate heterogeneity and issuer immateriality can create a large but low-value dataset before the identity/materiality contract is proven.

## 7. Readiness and limits

- Research decisions: **R1 PARTIAL / usable contract**
- Source denominator: **NOT QUALIFIED**
- Forecast calibration: **NOT STARTED**
- Recommendation promotion: **NOT QUALIFIED**
- Native Paper: **NOT APPLIED**
- Production integration: **NOT BUILT**
- Trade authority: **NONE**
- `EFFECT_UNKNOWN`: **none in the local reference build**

This R1 advances the missing MedTech lane without claiming that the earlier absent Web CEO completed its assignment. It is a bounded first installment under the already-approved Wave 1 MedTech commission; the full multi-turn research, design and Codex return remain owed.
