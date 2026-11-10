# Inactive historical RIG review commission — `prophet-hkca-shared-r1`

Current disposition (2026-11-07): source preservation only. The manifest is `draft`; no RIG verdict or approval exists. This document preserves the September review procedure and original frozen target as history. It does not request, dispatch or authorize new reviewers, and it is not a prerequisite to preserving these records. Any future current-reference review requires its own expressly scoped decision under current law.

The original R1 migration approval was superseded by [review 5317458514](https://github.com/mastermindx-market-intelligence/macro/pull/7499#pullrequestreview-5317458514) and [ruling 5825493315](https://github.com/mastermindx-market-intelligence/macro/pull/7499#issuecomment-5825493315). Preserve the baseline and those findings; source preservation does not close the successor product.

## Recorded September commission — inactive

Artifact SHA: `e3077bf50c69063f5d80275fa33dd415dae76fa9`
Route family: `hk_stocks.html + canada_stocks.html`
Historical requested status: `in_review`; no verdict or approval receipt was earned. Current manifest status is `draft`.

The earlier pass-1 commissions against artifact `eca7c779c26e7eaaca04fc33b6b42b8ba2d8a6a1` are superseded by the accepted Session A Tier-1 copy repair. They are not reusable for this replacement artifact. Fresh critic receipts must bind the SHA above.

Both reviewers judge the frozen result before reading designer rationale. They must differ from
the author and from each other. Pass 1 receives only the user job, production-before evidence,
capability ledger, frozen after artifacts, and rendered screenshots. After the first-pass findings
are frozen, pass 2 receives the contract/proposal rationale and records amendments.

## Reviewer A — Product regression

Mission: find anything the current product lets a user understand or do that the paired reference
makes harder, missing, misleading, or more authoritative. Inspect capability preservation, Top/All
identity, stage populations, timing, continuity/history, Grid/Table/filter round trips, access,
failure states, and Canada screen semantics.

Pass-1 inputs:

- `baseline.yml`, excluding `design_lineage` rationale until pass 2;
- committed P0B before screenshots named by `baseline.yml`;
- frozen contact sheets and screenshots under
  `mockups/evidence/prophet-hkca-shared-design-20260920/`;
- frozen artifact SHA above.

Return the exact `mastermind.rig_review.v1` receipt at
`reviews/product_regression.yml`, using `PRC-nnn` finding ids.
## Reviewer B — Visual and taste

Mission: judge whether the reference actually feels and scans better than production for a paying
user. Inspect hierarchy, density, restraint, visual identity, light/dark art direction, EN/ZH,
mobile reduction, 320px stress, interaction states, contrast, and whether the result reads as one
institutional family rather than a generic dashboard assembly.

Pass-1 inputs:

- the same user job and production-before screenshots;
- the four frozen contact sheets and all twenty committed after screenshots;
- JSX projections only for exact structure inspection, not as implementation source;
- frozen artifact SHA above.

Return the exact `mastermind.rig_review.v1` receipt at
`reviews/visual_taste.yml`, using `VTC-nnn` finding ids.

## Quarantine and completion law

Do not read `proposal.yml`, the shared design contract's rationale sections, prior designer review
comments, or any verdict file during pass 1. Freeze `first_pass.frozen_at` before rationale is
revealed. Pass 2 records every amendment as `upheld`, `downgraded`, or `withdrawn`. A surviving
blocker must appear in the design-authority verdict; it cannot disappear through prose or CI.

No reviewer may mark this reference canonical. Only a subsequent design-authority verdict plus a
valid `approval.yml` can move `manifest.yml` to `approved`. Production implementation, browser proof,
and two natural publications remain separate even after RIG approval.
