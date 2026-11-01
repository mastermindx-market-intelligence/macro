# Audit record

## Registration

Protocol and config were pushed at commit `b8036161bb84c2cab452d4d797081f7026f6b87d`, before new outcomes. Engine/input/check sources were pushed at `7bdfefa21fc18` before execution. `REGISTRATION.json` preserves those exact original hashes. Existing historical results were already known; this is a constraint on new discretion, not a fresh holdout.

## Corrections before first outcome inspection

Independent reviewer identified two implementation defects from source and synthetic examples:

1. The initial deadline function certified month ends from the priced index rather than a separate fixed calendar. A priced prefix ending on January 31 could postpone a known January deadline until February became visible. The revised function takes a fixed session-calendar argument; synthetic prefixes ending mid-month and exactly at month-end are both checked. Actual study cutoff remains October 8, a partial month, so this correction changes prefix robustness, not the intended investment rule.
2. For still-unspent contributions, the initial attribution bundled unincurred fees into a price-movement residual. The revised identity separates net price movement, cash interest, and unincurred purchase/liquidation fees. A flat-price pending contribution with zero cash interest now has zero price-movement benefit. Total account wealth is unchanged by this attribution correction.

The first execution attempt failed before calculating outcomes: the accepted source manifest legitimately points some prices to earlier retained directories, so assuming every ticker lived under the newest study's price folder failed at JNJ. Preparation now creates ignored per-ticker symlinks to the already verified manifest paths. There is no price substitution, additional vendor retrieval, or threshold change. All 31 original parquet hashes are reverified.

The protocol text is clarified for fixed-calendar prefixes and pending-fee attribution. Config, source signal roster, baskets, contribution size, costs, cash scenarios, policies, and outcome clocks are unchanged. Final source hashes and completed verification are recorded with the accepted run.

## Executed verification and reporting completion

All 10 synthetic checks passed. An independent contribution-lot reconstruction checked cash and holdings on every session of all 36 accounts; the largest dollar discrepancy was $1.46e-10. All 31 input price hashes matched. There are 82 funded monthly lots per account, 76 mature common endpoints and six immature lots retained in capital paths. The original 108 nominations collapse to 60 execution dates; none lacks its next observed open.

The code already emitted actual immediate/delayed adjusted-unit quantities and the fixed 2020-2022 / 2023-cutoff funding split before the first successful run. Protocol wording is made explicit to match that already-fixed split. The final run manifest also records the executed analysis and verification source hashes. These reporting additions do not change account or cohort outcomes. The independent methods adviser accepted the funding, unitization, cash, maturity and exact waiting identities after the two repairs. The hypothetical terminal-fee adjustment is excluded when checking prefix invariance of historical account paths.

## Final publication review

A bounded independent review reconciled the report's wealth, attribution, acquisition counts, maturity denominators, resampling intervals, sensitivities and risk claims with the saved result tables. It accepted the report, decision-record design, untested next-hypothesis contract and reproduction qualifications, with no blocking finding. The full all-account daily-path artifact remains on the original execution host and is included in the Git publication; it was not transferred into the adviser's smaller local review package.

The separate source review accepted four focal guidance packets with two clarifications: Caterpillar October lacks a comparable annual *operating* outlook in the inspected release, while its annual tax estimate is present; Microsoft October's energy-cost context retains the reported remaining-quarter timing. These clarifications are reflected in the published packets. This is a bounded source review, not a double-annotation or inter-rater validation study. See `guidance_review.md` for the source locations and reviewed-input hashes.
