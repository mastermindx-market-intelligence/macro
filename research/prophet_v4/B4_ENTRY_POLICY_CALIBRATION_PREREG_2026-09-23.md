# B4 Entry-Policy Calibration Prereg

**Machine-readable freeze:** `research/prophet_v4/b4_entry_policy_calibration/PREREG.json`

## Amendment A1 (2026-09-23, pre-capture)

Capture has not started: there is no live B4 runtime on main. This amendment is therefore pre-capture. It makes the following nine changes.

1. `C6` now points to `C2`, and `C7` now points to `C4`. These are aliases, not new evidence, so the study has six distinct configurations: C0 through C5. All eight original labels remain in the record.
2. The study population is the first admissible decision instant for each candidate episode. Reports must show effective N by date and by issuer.
3. Maximum adverse excursion at 10 sessions is the sole primary endpoint. Every other metric and horizon is descriptive support only and cannot rescue a result.
4. Holm correction applies to the five non-control distinct cells, C1 through C5, for the primary endpoint. The declared search family includes the EL H10 timing study registered under D06.
5. At 10 sessions, a cell is non-inferior to C0 only if the lower confidence bound for net excess is at least −25 basis points. A nonsignificant point estimate is not non-inferiority.
6. The round-trip cost value is a 50 basis point floor, not a measured cost. A read using a lower floor is invalid until D08 supplies the measured range.
7. A row refused by a gated cell stays in the study at cash return over the declared horizon; it is never dropped.
8. The fixed look is 300 episodes for each distinct cell. Counts at 50 and 100 are monitoring only. At 150 episodes per cell, if every cell's primary lower bound excludes any improvement, the study stops as rejected.
9. A cell is supported only by the single primary endpoint with its non-inferiority bound; the old any-of-K support path is superseded. Pareto dominance and non-identifiability remain grounds to kill a cell. The original decision-law arrays are preserved under `decision_law.superseded_by_A1`.

The clock law still forbids historical backfill, the cohort start is unchanged, and all research-only authority flags remain false. This record authorizes evaluation only; it does not rank, admit, size, execute, trade, or promote policy.
