# Superseded before native application

The v1 row repair in this directory was **never applied to Paper**. A source cross-check found that the retained 17-year income history already supplies FY2021 baselines for five income series and supports a derived operating-margin baseline. Marking every FY2022 comparison unavailable would therefore be incorrect.

Use the separate `../company-annual-growth-v2/` row and caveat packets, which compute all six available FY2022 comparisons and retain `Prior unavailable` only for EPS, dividend and free cash flow. The original v1 files remain unchanged as preparation history. Their `PREPARED_NOT_APPLIED` state is not permission to apply them, and their local validation is superseded by the v2 arithmetic check.

The sole native writer explicitly confirmed that no v1 Company row or header had been mutated before this correction. Actual v2 replacement effects and IDs belong in the writer's later receipts.
