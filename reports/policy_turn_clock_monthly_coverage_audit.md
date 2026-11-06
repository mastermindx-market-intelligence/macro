# Policy Turn Clock R0 Monthly Coverage Audit

This is a metadata-only availability audit.

- Schema: policy_turn_clock.monthly_coverage_audit.r0.v1
- Semantic digest: 6e289c1d633d3ccd64b92d3c3ac094b7236b407b1e30854dfa520a677a0ca60a

## Source passports

| Owner | First cycle | Last cycle | Monthly cycles | Classification | Missingness |
|---|---|---|---:|---|---|
| broad_flow | 2026-07 | 2026-08 | 2 | forward_only | unknown |
| options | 2017-01 | 2026-07 | 115 | historical | unknown |
| treasury | 2026-06 | 2026-09 | 4 | forward_only | unknown |
| vx_curve | 2026-04 | 2026-09 | 6 | forward_only | unknown |

## Exact required-source intersections

| Hypothesis | Availability | Monthly cycles | Reason |
|---|---|---:|---|
| H1 | UNAVAILABLE | — | required source passport is absent or not present |
| H10 | UNAVAILABLE | — | required source passport is absent or not present |
| H2 | UNAVAILABLE | — | required source passport is absent or not present |
| H3 | UNAVAILABLE | — | required source passport is absent or not present |
| H4 | UNAVAILABLE | — | required source passport is absent or not present |
| H5 | UNAVAILABLE | — | required source passport is absent or not present |
| H6 | UNAVAILABLE | — | required source passport is absent or not present |
| H7 | UNAVAILABLE | — | required source passport is absent or not present |
| H8 | UNAVAILABLE | — | required source passport is absent or not present |
| H9 | UNAVAILABLE | — | required source passport is absent or not present |

No availability count is a decision or outcome.

## Controlling qualification — 2026-11-05

Everything above this line is the original 2026-09-03 report, preserved
byte-for-byte. The report body and its semantic digest were **not** regenerated;
the counts below are the original run's numbers. The behavioral change in this
slice is the metadata-validator hardening described in the last section, which
does not alter the report body, the artifact bytes, or the digest.

### This is a partial historical audit

It records metadata-only availability for four supplied source passports. It is
not a coverage census, not a historical rerun, and not R0 acceptance.

### Required owners: absent/unassessed vs supplied with an unknown clock

The union of required owners across H1–H10 is 17. The table above collapses two
different conditions into one "UNAVAILABLE" label, and they are not the same
finding:

- **13 of 17 required owners have no passport in the retained artifact** —
  their coverage is unassessed by this artifact: `duration_calendar`, `duration_study`,
  `event_identity`, `migration`, `opex_calendar`, `quarterly_calendar`,
  `rebalance_pulse`, `relative_performance`, `replacement`, `session_calendar`,
  `sign_passport`, `volume_breadth`, `vx_calendar`.
- **4 of 17 required owners have a passport with an unknown availability clock
  in the retained artifact** — `broad_flow`, `options`, `treasury`, `vx_curve`. Each carries
  `missingness: unknown` and `available_at: null`. A passport with an unknown
  availability clock is not a present source and cannot contribute a cycle.

For H6, H7 and H9 every required owner is in the first group: the retained
artifact contains no passport for any of them. For H1–H5, H8 and H10 the two
groups mix. This does not establish whether an owner was assessed elsewhere.

The "UNAVAILABLE" rows above therefore establish **no lawful monthly coverage
from these four supplied inputs**. They do not establish that the underlying
mechanisms lack historical evidence, and they do not reverse the earlier issue
census.

### The counts are dated, unverified source-count observations

The "Monthly cycles" figures in the source-passport table (broad_flow 2,
options 115, treasury 4, vx_curve 6) and the first/last cycle values are
observations recorded on 2026-09-03 by the original run. The original
acquisition/input manifest is **not included in this five-path package**, so
these source counts are **not reproducible from this package alone**. No host
or provider receipt is included here. They are retained as dated observations,
not as verified counts or proof that no earlier assessment or receipt exists.

The artifact's semantic digest
`6e289c1d633d3ccd64b92d3c3ac094b7236b407b1e30854dfa520a677a0ca60a` was
re-verified on 2026-11-05 from the preserved artifact bytes under the original
canonical encoding. **A verified output digest is not the missing
input/acquisition receipt** and does not close this gap.

### What the seven original tests do and do not prove

The seven original tests in `tests/test_policy_turn_clock_monthly_coverage_audit.py`
prove: unique monthly cycles rather than daily rows; an explicit timezone-aware
availability clock rather than a filesystem timestamp; the exact required-source
intersection rather than the longest source; a missing required owner reported
as UNAVAILABLE rather than zero; no retrofitting of a forward-only source;
stable serialization carrying no decision/outcome vocabulary; and preservation
of an unknown availability clock without inventing one.

They do **not** prove the original acquisition manifest, any host receipt, or
the full controlling refusal surface of the preregistration — which additionally
refuses inferring dealer inventory or a missing canonical field; backfilling
broad ETF flow, Rebalance Pulse, M1–M6 curve, W1 receipt or migration evidence;
pooling eras or inflating cycles from daily/root/contract records; using a
longest source history in place of an exact required intersection; copying
proprietary ThetaData or raw source records into Git; or turning a coverage
count, availability classification or sample-floor result into an outcome,
efficacy, product or authority claim.

### The 2026-11-05 source change

`scripts/policy_turn_clock_monthly_coverage_audit.py` had a seven-character
month check (`len == 7 and cycle[4] == "-"`) that accepted invalid months such
as `2026-99` and nonnumeric lookalikes such as `abcd-ef`, left the
`row_count`/`entity_count`/`root_count` fields entirely unvalidated (booleans,
floats, strings and negatives were accepted). The validator now requires a
genuine canonical `YYYY-MM` calendar month and requires the count fields to be
nonnegative integers. Hypothesis, intersection, era and floor semantics are unchanged,
and the preserved artifact and preregistration are byte-for-byte unchanged.

The existing nullable correction-clock behavior is preserved. A proposed
requirement that correction identity and time both be non-null is a separate
contract question; it is not imposed by this repair. Known correction identity
with unknown correction time remains representable, without inventing a clock.

### Scope remains closed

W1, every outcome wave, mechanism promotion and capital authority remain closed
and separately unsatisfied. This document confers no ranking, gating, sizing,
trading, product, runtime or capital authority.

### Canonical references

- Canonical carrier and controlling R0 ruling: Macro issue
  [#6794](https://github.com/mastermindx-market-intelligence/Macro/issues/6794),
  controlling comment `5529187973`.
- Original branch and pull request: Macro PR
  [#6807](https://github.com/mastermindx-market-intelligence/Macro/pull/6807),
  branch `warp/warp-e5cf04717ffaddff119215d6e272dc38e0b11e559ea12c4cdb99839c02b9dcae`,
  head `a270c62721fc3fb2c90d52ddd1e5962dd92d05c8`.
- Preregistration, preserved byte-for-byte:
  `research/POLICY_TURN_CLOCK_MONTHLY_TRANSITION_PREREG.md`.
- Audit artifact, preserved byte-for-byte:
  `reports/artifacts/policy_turn_clock_monthly_coverage_audit.json`.
- This report: `reports/policy_turn_clock_monthly_coverage_audit.md`.
- Audit source: `scripts/policy_turn_clock_monthly_coverage_audit.py`.
- Parent assignment: Mastermind issue
  [#2028](https://github.com/mastermindx-market-intelligence/Mastermind/issues/2028).
