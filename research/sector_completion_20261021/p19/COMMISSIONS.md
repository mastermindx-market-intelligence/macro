# P19 independent verification — commissions (record copy)

Three READ_ONLY Opus reviewers (ROUTE: review, MODE: READ_ONLY) were commissioned on
2026-11-02 against candidate head ec1f1ea694d5442e773b6158ce0cbad1385677fe. Each received
the same review standard and scope; the ranges differ. The seat authored the claim packet
(P19_CAPABILITY_DISPOSITION_2026-11-02.csv, P19_ACCEPTANCE_2026-11-02.md) and did not
verify its own work. Returns are stored byte-exact beside this file; sha256 in README.md.

## Ranges

| Verifier | Rows | Journeys |
| --- | --- | --- |
| A | R3A-01..R3A-46 | — |
| B | R3A-47..R3A-92 (incl. BLOCKED_DATA SC-066, SC-092) | — |
| C | C01..C28, U01..U14 | J01–J15 (section B of the acceptance note) |

## Review standard (common text)

A row is CONFIRMED only when the capability is found on HEAD in source (templates/, engine/,
scripts/, tests/) or in the named evidence (research/reference_integrity/
sector-intelligence-cycles-20261021/evidence/*.png + cells.yml + README.md;
design_refs/sector-paper-20261021/state_matrix.csv; the R4 specimen under
design_refs/sector-paper-20261021/{brief_repair,cycles_repair}; the proposal.yml
coverage_matrix) in the form the proposal target describes. IMPROVE rows: DELIVERED /
PARTIAL (residual named) / NOT_DELIVERED on HEAD with file:line. RELOCATE rows: the
destination route/anchor exists on HEAD. BLOCKED_DATA rows: BLOCK_CONFIRMED only when the
block is real on HEAD and the interim states it truthfully. Otherwise UNSUPPORTED with the
reason. Scientific fences stand: no invented signals/sizing; W4.2 hazard 4/6 qualified with
up/3m and up/6m PRIOR; W4.6 sizing 1.0; W5.1 lead-lag STOP; the grader hit rate is not a
win rate; PARITY_FAILS is recorded, never repaired on the surface. Journeys (C only):
UPHELD / DOWNGRADED to <status> with reason / UNSUPPORTED; a served-product interaction
proof may legitimately be PENDING_LIVE / PENDING_BY_DESIGN.

## Scope (common text)

Read-only over the sparse SSD worktree (data/ and most of site/ absent by design; a missing
generated file is not evidence of a missing capability). Allowed: `git -C <tree>
show|log|grep|diff`, `python3 -m pytest -q <one test_sector*/test_cycle* file>
-p no:cacheprovider`. Forbidden: writes, git state change, checkout, stash, worktree
commands, scripts/worktree_sparse.py, materializing data/ or site/, network, credential
files or env secrets, push or PR actions, reading the other verifiers' returns.

## Return format (common text)

Plain text ≤ 25,000 characters: STATUS (COMPLETE | PARTIAL); RESULT (counts per verdict);
TABLE (`row_id | verdict | evidence file:line or cell id | note ≤ 200 chars`, then for C
`J## | UPHELD or DOWNGRADED to <status> or UNSUPPORTED | evidence | reason`); EVIDENCE
(commands run, fence records read, test counts); GAPS (every UNSUPPORTED / NOT_DELIVERED /
PARTIAL row and every DOWNGRADED journey with a one-line reason); DEVIATIONS (what could
not be verified and why).

## Run notes

Each reviewer runs under a 24-turn harness limit per resume; when a reviewer stopped
before emitting its packet it was resumed once with the instruction to close within eight
more tool calls and to mark unreached rows UNSUPPORTED "not reached in budget" under
DEVIATIONS rather than leave the packet unwritten. Resumes are recorded in README.md.
