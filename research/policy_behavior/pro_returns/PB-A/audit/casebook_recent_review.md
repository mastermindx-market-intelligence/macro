# PB-A recent-source integration audit

## Scope and receipt

Reviewed the eight recent Fed/Treasury primary episodes and the separately selected June 14, 2023 challenge in `research/policy_behavior/pro_returns/PB-A/PB_A_CASEBOOK.json` against `recent_fed_sources.json`, together with their frozen input rows in `PB_A_DECISION_INPUTS.json`.

Reviewed casebook SHA-256: `11a91c88d4e23e189827424eb787402e793d24b90433124b6127829d07fcd5f0`.

Reviewed decision-input SHA-256: `8235b465e9c0b05f23d499b849d74789d0ef40cb99885306295b92bdf5485ff5`.

Root reported immutable forecast publication/readback commit `8799d065178b7637bc91a0e69696df8b9ef763f6` before its scoring run. This audit did not rerun forecasts or scores and did not change frozen inputs, code, protocol, or casebook.

## Assessment

No model-impacting source-loss, coding, new-rate-decision flag, or clock-grade correction found in these rows. Six recent formal FOMC decisions retain their just-decided target ranges separately from next-day implementation. Jackson Hole and BTFP correctly have no new focal rate decision. December 2021 remains rhetorical ABSTAIN because its state-contingent hold and calendar-year projection differ in horizon. March 2023 retains the conditional weakness of “some” and “may.” The June 2023 challenge remains outside the primary cohort.

May 1, 2024 correctly retains a formal rate HOLD at 5.25–5.5 percent and a separately announced June 1 Treasury-runoff-cap change from $60 billion to $25 billion. Agency cap $35 billion and Treasury-directed excess-principal reinvestment remain intact. The $35 billion cap difference is not labeled realized lending, purchase flow, reserve injection or a policy-rate cut. Later same-day press conference claims remain excluded at the 14:01 EDT cut. The prior 2022 ample-reserves framework remains a competing institutional explanation, not proven exclusive motive.

BTFP quarantine is appropriately stricter than the helper's qualified parent-link date association. The certified block now excludes attachment-only OIS-plus-10bp terms, recourse details, exact eligibility/ownership-date restrictions and request deadline. Timed main-release facts—up-to-one-year loans, par collateral, Treasury backstop up to $25 billion—and joint-statement depositor protection remain admitted. Lending and payout execution remain unverified. None of the quarantined details enters the predictor.

## One annotation correction required

The BTFP row's `material_uncertainties` retains this sentence from the original helper return:

> March13 midnight cut permits posted terms; promised depositor access has not been certified executed.

That sentence conflicts with the normalized row's explicit attachment quarantine. Suggested replacement:

> March 13 midnight is retained as the frozen conservative episode cut; parent-linked term-sheet details remain excluded from the certified decision block. Promised depositor access has not been certified executed.

This is an annotation-only post-freeze correction. It does not require changing decision inputs, source clocks, code, forecasts, outcomes or metrics. Root owns whether/how to publish the correction.

## Provenance wording recommendation

The original source identity for `joint20230312` correctly preserves Treasury/Federal Reserve/FDIC as originator and `US_JOINT_SRE_20230312` as the source family. Its added `originator_family` is currently `FEDERAL_RESERVE_SYSTEM`, and the casebook summary labels two broad institutional umbrella categories as `source_families`.

For provenance summaries, preserve the joint origin explicitly through a composite label or multiple originators. Call the two broad summary categories “institutional umbrella families” rather than implying they are the exact event/document source families. The original document-level lineage is already preserved, and statistical independence is appropriately disclaimed. This recommendation has no forecast or score impact.

## Remaining scope

Official release minutes and prepared-text delivery schedules establish the declared documentary clock standard. They do not certify historical server first-byte delivery, immutable contemporaneous served bytes, every spoken passage by the cut, realized flows, market expectations or private motive. The normalized certificate and Jackson Hole source annotation preserve those limits.

