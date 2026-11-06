# NewsImpact material-change accumulation repair (R4)

## Problem and change

A later duplicate or cosmetic report could erase a legitimate numeric correction or independently sourced change already found for a proposition. A separate cleanup pass could also let an unrelated proposition's numeric record preserve a numeric-change trigger for a milestone-only view.

Each attached record now contributes its own eligible triggers. Contributions are combined by union and cannot be removed by later reporting-only records. Company and proposition membership checks precede all record-derived contributions.

Numeric eligibility is decided for the attached record. Independently observed milestones do not independently contribute changed_numeric_terms; known-group reporting retains its exclusion. The global numeric cleanup scan is removed.

Trigger ordering, correction, contradiction, milestone, deadline, exposure, market-state, and first-materialization semantics remain unchanged. Fact-log records and owner states are not rewritten.

## Verification

Root ran the actual public owner-projector suite: **46 passed**, with two inherited pytest temporary-directory cleanup warnings. Nine new cases cover mirror/commentary ordering, cross-proposition and cross-Company leakage, lawful same-proposition numeric/cosmetic records, and reporting-only nonmateriality.

Against the old source, four valid cases reproduced the defects. An initially proposed cosmetic fact_revision fixture was refused by the existing schema; it was corrected to a lawful article manifestation and is not counted as an established runtime defect.

Fixtures pass through the owner's record-validation and append path. git diff --check passed. A separate C3 review accepted the complete modified trigger function and nine regression cases. Test execution is root's separate evidence.

## Scope

The repair preserves the owner's material_delta_triggers vocabulary. It does not estimate economic direction, magnitude, surprise, price impact, causality, or a trade recommendation. It does not establish native source admission.

Current news visibility without a historical owner snapshot remains a separate consumer gap. Missing historical evidence must remain distinct from no observed change.

Base: ff1b80af0f5efa5982656a59d63a0c623d5cd531.

Disposition: **DRAFT / HOLD**. Existing program holds remain in force.
