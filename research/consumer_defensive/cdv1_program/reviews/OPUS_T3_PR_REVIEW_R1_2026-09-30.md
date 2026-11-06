# Opus review — CDV-1 Task 3, PR #8232, first review, 2026-09-30

- **Artifact:** PR #8232, head `f2714400cc83d38f3d1e74bc95ab110950216267`, branch `claude/cdv1-t3-economic-interpretation`, produced by the r3 packet (`packets/CDV1_T3_R3_PACKET_2026-09-30.md`).
- **Reviewer:** an independent, read-only Opus reviewer commissioned by the CDV-1 seat (session `251f88c8`). It worked against the task bar in `reviews/SEAT_RULING_T2_T3_R3_ERRATUM_2026-09-30.md` (bar (c1)–(c6)) and the plan's Task 3.
- **Verdict:** **REJECT.** Ten blocking findings.
- **Recorded by:** the seat, from the reviewer's return. Every finding was confirmed by a probe the reviewer ran against the head (its merged tree, the dossier command and direct calls), and the seat re-read the code for B2 and B7 before adjudicating.

## Mechanical baseline (seat harness, same head)

Every mechanical check passed:
- file grants, and an empty Task 1 freeze diff;
- RED rc 2, then GREEN (21 passed);
- the dossier job's exact `run:` line: rc 0, 2,336 passed, 174 skipped;
- `tests/test_ci_pack.py`: 143 passed;
- contract-delta: 0 introduced;
- pyflakes clean;
- `git merge-tree` against main: clean.

The defects below are semantic. None of them could have been caught by these checks.

## Blocking findings

| # | Bar | Finding | Evidence |
|---|---|---|---|
| B1 | (c6) | Eleven erratum T3 R3 paths are absent from every built interpretation, and `selection.currentness` is the constant `"latest_accepted"`, which is outside spec §5.4. | The seat's path walk over both fixture cases (`check_t3_r3_paths.py`), confirmed by the reviewer. |
| B2 | (c5), (a), (b) | `compare_eps` treats `precision` (decimal places) as an uncertainty half-width in dollars. `prior - Decimal(precision) <= 0` at `precision=2` refuses every prior at or below $2.00, which covers every real P&G quarterly EPS. The `uncertain_prior_eps` fixture ($2.00 prior) was fitted to the defect. | Direct `compare_eps` calls; code at `compare_eps`. |
| B3 | (a), R1 | Missing-context items exist only for a hand-listed metric set, so typed-absent organic-sales, reported-sales and price rows produce none. | Built cases with those rows typed-absent. |
| B4 | (a) | The validator compares seven fields. Tampering `issuer`, `event_id`, `build`, `quality` or `next_evidence` in a stored payload validates. | Tamper probes: accepted. |
| B5 | (a) | `_supported_revision` accepts any 64-character string or any `synthetic-` prefix, so "supported" is vacuous. The plan requires that an unsupported historical version returns unavailable. | A `"f" * 64` revision builds and validates. |
| B6 | (e) | A malformed stored payload escapes the typed error: `observations=[1]` raises `AttributeError`, and `observations=5` raises `TypeError`. | Direct validator calls. |
| B7 | (a), n-B2 | `interpretation_id` and `clocks.source_revision` derive from the release entry's `source_sha256`, which Task 1 does not bind. Tampering it changes the identity with no source byte changed. | Tamper probe. Task 1 binds the source only through each present row's receipt, `receipt.source_sha256 == sha256(source_text)`. |
| B8 | (a), R1 | The `unlocated_outcome` fixture forges a typed absence onto a real row (`_decline`, `_absent_fact_id`) instead of obtaining it from Task 1. | Fixture source. |
| B9 | (b) | Deleting the period check in `_validate_pair` (lines 202–203) leaves all 21 tests green. | Mutant run. |
| B10 | (a) | Three rules are wrong: (i) `reported_vs_organic_difference` fires only for reported > 0 with organic ≤ 0; (ii) `segment_scope_limitation` fires only when segments are ABSENT, the inverse of CDV1-10; (iii) `incomplete_margin_to_cash_bridge` fires on reconciliation absence, although reconciliation is not a margin or cash measure. | Rule code; constructed cases. |

## Non-blocking notes (not carried into the fix round)

- `workspace_generation_id` is the empty string in fixture builds.
- The 24-item cap is on the selection length.
- `derived_growth` is always labelled `approximate`. Filing EPS is always rounded, so this matches the plan.
- The EPS disagreement rule already treats flat against up as a difference, which is consistent with §5.6 "differed".
- The n-B1 test is weak, but bar (c1) is met.
- No test pins the `missing_consensus` rule id. The r4 order test now covers it.
- `FINDING_TEXT` differed from spec §5.6. R13 of the fix round aligns it, because R12 (i) would otherwise make one sentence false.
- `next_evidence` is a list, while spec §6.2 names `next_evidence.company_link` and `.gmi_link`. Task 3 owns no company or GMI binding. The seat resolves this at the Task 6 packet: either Task 6 supplies those links, or §6.2 is amended.
- Met: bars (c1), (c2), (c3), (c4), (d) and (f).

## Seat adjudication

All ten findings are upheld. B3, B5 and B10 are one defect class, behavior written as hand-listed special cases. Under the operating brief, the correction is a bounded design change, not another literal case:
- one general missing-context rule (R6);
- a closed set of supported revisions (R8);
- one `_direction` helper for both difference rules (R12).

The fix round is `packets/CDV1_T3_R4_PACKET_2026-09-30.md`, and the rulings are recorded in `reviews/SEAT_RULING_T3_R4_2026-09-30.md`.
