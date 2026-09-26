# Signal Lab / Alert-Trust Repair — Sol Acceptance and Continuation

**Date:** 2026-09-14
**Operation:** `signal-lab-alert-trust-20260910-sol-001`
**Repository:** `mastermindx-market-intelligence/macro`
**Writer carrier:** `admins-Mini-652.ts.net lan`
**Branch:** `claude/signal-lab-alert-trust-20260910-sol-001`
**Reviewed semantic head:** `7d67c8e640b2227883daeaf63e5ee15d289d8615`
**Semantic tree:** `dc0b3836962d73c0615eaed69c0074c253e49fca`
**Pickup / semantic comparison base:** `acb0d75e49596a62230542cf297a84391694f765`
**Latest protected-main compatibility receipt:** `878147de1cfbce89768ccf98a140d922ba1a6ce5`
**Protected Skillpack pin used for closeout:** `51b815ab9527e15c9218b049f622dc4d3e0bfbc4` / `mastermind.sol_skillpack.v1` 1.0.1
**Capability state:** `BUILT_NOT_PROVEN`
**Release state:** `HOLD-FOR-SOL` — no push, PR, merge, deploy, or production-live claim.

## Capability delta

Before this repair, a BTC impulse fire could remain a valid historical observation while its persisted
issue-time `tier=act` and “verified LEADING / act early” language were still consumed as if they were
current authority after the validation evidence had been demoted, underpowered, stale, or otherwise
unusable.

After this repair, history and authority are distinct. Stable historical event IDs and original
issue-time claims survive as history, while current action/push/board authority is recomputed through
one resolver from the current validation artifact plus independent gate, source, and event clocks.
Malformed leading evidence fails closed. Missing typed direction remains unknown rather than being
inferred from alert type. Signal Lab exposes the current evidence receipt and Alert Center consumes the
same authority state instead of re-authorizing old prose.

## Authority and implementation boundaries

- `engine/btc_impulse_radar.py::resolve_leg_permission` remains the sole BTC impulse current-permission
  resolver. `engine/signal_evidence.py` adapts the result into a passport; it does not own a second
  verdict registry.
- Raw fire history remains intact for research/backtesting. The repair withdraws current authority; it
  does not delete observations or rewrite stable event identity.
- `engine/alert_triage.py::pressure_effect` accepts only explicit typed direction for impulse pressure.
  Alert type is identity, not direction authority.
- Existing `scripts/build_vector.py` / `scripts/build_site.py` publication ownership is preserved; no
  new publication plane, queue, retry store, preference store, or alert authority was created.
- Macro PR #7022 remains a separate draft/HOLD owner of overlapping Alert Center files. No custody
  transfer occurred. PR #6974 remains a separate draft on the shared builder surface.

## Independent review

The first immutable review of `a10c4ac8eb06212620c522a3f31a43776506502c` returned
`REQUEST_CHANGES` for two material defects:

1. a row labeled `leading` could authorize without proving structurally valid measured
   `n_fires_holdout`, `lift_holdout`, and `perm_p` values;
2. `pressure_effect()` could infer absent impulse direction from alert type.

Both were repaired test-first. The repaired exact head `7d67c8e640b2227883daeaf63e5ee15d289d8615`
received an independent read-only Sonnet review on the Studio packet and returned:

- `VERDICT: APPROVE`
- `BLOCKERS: NONE`
- `MAJORS: NONE`
- review output SHA256: `de59e41cab4ddce6c04d0d178e4f47ae62670d29fad805b2fa29283c910345a4`

The reviewer identified three nonblocking residues only: explicit NaN/inf/bool measurement variants
are not individually parametrized, a composite `d2+d3` measurement-failure case is not directly
parametrized, and the review packet itself contained the then-pending contract-delta log. The first
two are low-risk test-depth follow-ups; the implementation was approved by inspection. The third is
closed separately by the exact-head Mini contract receipt below.

## Exact-head verification

Fresh post-commit evidence bound to semantic head `7d67c8e640b2227883daeaf63e5ee15d289d8615`:

- broad affected regression: **310 passed, 1 skipped**;
- exact enrolled Alert Command Center CI command: **192 passed, 1 skipped**;
- Python compilation and `git diff --check`: pass before commit;
- the three new trust suites are explicitly enrolled in the existing Alert Command Center CI step;
- legacy CI manifest validates with **212 jobs**;
- contract-delta on the reviewed semantic head against protected main `878147de1cfbce89768ccf98a140d922ba1a6ce5`: **0 introduced, 0 inherited**; log SHA256 `e8e828b9adbeacb841dea2a755e4e88884ae0be7853023bd00d944707294c42f`.
- Agent OS record validation after the closeout discovery was added: **0 errors**; inherited store warnings remain visible and are not claimed fixed by this operation.

The exact-head local acceptance JSON is `/tmp/signal-alert-trust-7d67c8e/acceptance_receipt.json`
with SHA256 `8ff3933f42d13217ceb202da149c9166f5334f4c2e12b68f1438d793f500651e`.
That `/tmp` path is evidence provenance, not the durable owner; this document records the accepted
facts needed by a fresh session.

## Current-base compatibility

Protected main moved after the semantic implementation. The latest bounded receipt in this closeout is
`878147de1cfbce89768ccf98a140d922ba1a6ce5`. Under the protected review-reuse law, the
semantic review and latest-base integration proof are separate receipts. Candidate source/test blobs
on protected main remained byte-identical to the pickup base; the only material overlap previously
observed was `.github/ci/legacy-jobs.yml`, and its three-way merge was conflict-free while retaining
all trust-suite enrollment and closure entries. Later protected-main movement from the prior `2e972811...` receipt to `878147de...` changed only two
repository paths and none intersected the candidate or declared material dependency set. The refreshed
exact-head contract-delta gate remained 0/0.

Therefore the substantive review remains attached to immutable semantic head `7d67c8e...`; do not
merge/rebase protected main merely to make `behind_by=0`. A future release-maintenance action must
refresh the lightweight latest-base compatibility receipt and expected-head checks before any remote
mutation.

## Canonical local publication-path proof

The worktree is intentionally sparse, so importing all of `scripts.build_site` would pull omitted
unrelated collectors. Without widening sparse checkout, the proof executed the **exact AST bodies**
of the current semantic head's canonical functions:

- `scripts/build_site.py::build_signal_lab_page`
- `scripts/build_site.py::build_alerts_page`

with the repository's normal Jinja environment/globals and `lib.pages.inject_text` / `dbase_prefix`,
writing only to an isolated `/tmp` site. No parallel page-builder implementation was created.

Resulting artifact hashes:

- Signal Lab HTML: `9f2fa49d42699143206bce8dbae51b52ac540bcf435cad5270563fd7acec6316`
- Signal Lab JSON: `d7229254e49b0a6e3bc033c9c8a3b5d2c77de0d27583c0adaa1c77f49f7aad0f`
- Alert Center HTML: `e90c76cead370803062472ec52ddd44818a1478ea9ca17a60444df1ac566cabf`
- Alert Center JSON: `602e0020e4d47065b9561272420aff5a1228c10237606f34bfe3076f2d5a97a2`

On the 2026-09-14 evidence clock the committed BTC validation artifact is stale, so the correct
current projection is zero permitted impulse rows in Signal Lab rather than yesterday's demotion
labels. That is expected fail-closed behavior, not a regression.

## Browser proof

The isolated canonical-builder artifacts were served locally with static dependencies materialized
from exact semantic HEAD and rendered through real headless Chrome/CDP.

Matrix: **16 / 16 clean** = Signal Lab + Alert Center × desktop 1440 / mobile 390 × dark / light ×
EN / ZH.

Every final cell had:

- zero failed responses and zero aborted loads;
- zero JavaScript exceptions and zero browser error logs;
- zero horizontal overflow;
- no rendered `verified LEADING` or `act early` stale authority copy;
- correct requested theme and language.

Signal Lab additionally proved the exact D2 evidence anchor present/in-view, observation-only current
use, and the stale-validation status in English and Chinese.

Browser matrix SHA256:
`c9b897b58d00a39a7e30869830fe8288472677e8a6011031d4c42a17a4df56bc`.

## What remains false

- There is no remote branch for `claude/signal-lab-alert-trust-20260910-sol-001`.
- There is no pull request for this branch.
- Hosted CI has not run on a remote candidate head.
- Nothing from this operation has been merged or deployed.
- Production browser acceptance has not occurred.
- The overall Signal Lab / Alert Center programs are not declared complete by this bounded trust repair.

These are deliberate truth boundaries, not missing local implementation claims.

## Durable organizational ruling

No current Agent OS workstream owns this exact repair/path set. Do not attach it to
`WS:COMMERCIAL-PATH-ALERTING` or invent a new workstream simply to make a handoff fit. The durable
cross-session fact is recorded as standalone discovery
`DSC:SIGNAL-LAB-ALERT-AUTHORITY-FAILS-CLOSED`.

## Exact continuation

This bounded W0 is locally accepted and terminal at `HOLD-FOR-SOL`. Do not redo the semantic repair,
recreate its worktree, merge current main for ancestry cosmetics, or send the same logical mutation
through another carrier.

If release is separately authorized later, keep `7d67c8e640b2227883daeaf63e5ee15d289d8615` as the
reviewed semantic head, re-pin current protected procedure, refresh current-main path/dependency
compatibility and contract checks, confirm no overlapping-owner transfer/collision, then perform the
smallest lawful same-branch release-maintenance operation. Push/PR/merge/deploy authority is not
created by this acceptance record.
