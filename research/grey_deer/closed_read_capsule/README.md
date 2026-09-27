# Closed-read quality: reproducible, unapplied source-owner capsule

**Date:** 2026-09-11 UTC. **Parent:** Prophet research PR #7043,
`prophet-absolute-downside-research-20260910-sol-001`.
**Status:** retained historical-source reproduction and an UNAPPLIED selector proposal.
No production template, quote, policy, candidate/plan state, ranking or authority changed.

## What the owner can reproduce without reconstructing the chat

`plv_mode_original.js` is the exact previously extracted `_plvMode` function from
`templates/dashboard.html.j2` at Macro
`6e1fb2ab35f68bbaf3695ffee5fe5ba268e46bae`. Its SHA256 is
`98b7605cd1ee31ff5dd7061df0fc1c488e56a452a09d13379ceb6c953a9de62e`.
This is a historical source pin, NOT a current production version assertion.

A pass with 175 checked names and 166 unreadable names can return ordinary
`closed` after 16:20 because that branch precedes the unreadability check. The
retained downstream diagnosis is in `../absolute_downside_pilot/ROUND3_RESULTS.md`.

`plv_mode_candidate.js` computes the same existing unreadability fraction once
and applies it to the closed branch. It retains the 50% inclusive threshold,
producer-dark precedence and the special healthy-post-close ageing behavior.
It does not mix unknown/out-of-probed-band with unreadable. This is a proposal,
not a new accepted classifier contract.

## Commands in a disposable copy of this directory

Requires Node.js; no installation, network, credentials or market data.
The test runner executes the frozen function in an isolated VM with a controlled
clock adapter. It is not the full template or an authenticated browser run.

```sh
# Expected exit 1: 23 pass / 5 fail; all five are the reproduced closed-read defect.
node test_plv_closed_quality.cjs plv_mode_original.js
# Expected exit 0: 28 pass / 0 fail for the unapplied proposal.
node test_plv_closed_quality.cjs plv_mode_candidate.js
```

Fresh repetition on September 11 UTC reproduced both counts. A separate retained
mutation run rejected all four deliberately wrong variants: missing closed check,
strict-greater threshold, wall-clock ageing ahead of closure, and treating unknown
as unreadable. Those author checks are not independent review or hosted CI.

## Required remaining source-owner work, not silently implemented here

The candidate emits reason `coverage`. `plv_coverage_copy_proposal.json` contains
the proposed EN/ZH explanation. The actual `PLV_DARK` copy consumer must be wired;
otherwise a fallback may tell the user quotes are failing now merely because the
market closed. A selector-only patch is not the complete repair.

Preserve valid historical crossing evidence. A last-pass quality failure does not
prove that nothing crossed earlier. Keep the existing event owner and raw
candidates intact; this capsule does not authorize a new history store. Any
retained current-page rows need their actual evidence/time scope explained.

A real repair still requires the existing owner's exact-path/hunk custody,
current permitted source compatibility, actual render/consumer tests, applicable
concluded code checks, independent review and normal production/browser proof.
The source owner must separate current candidate availability from this
observational crossing panel. This does not complete B2, B3 or B4 Availability.

## Scope and safety boundary

Existing Entry Truth #6805 and Cockpit #6817 retain their source responsibilities;
this capsule does not assign a writer, transfer a branch, reopen #6840, or widen
any intake-copy, dossier, or related repair.

During the later research turn a separate compound host diagnostic for current
live-source filenames/header/template hash was safety-refused before a result.
It was NOT retried. Neither this capsule nor its recipient is asked to reproduce
that refused query or its components by another tool, account or worker. This
capsule publishes only the previously retained historical selector and tests.
Any coordination request asks the existing owner for its OWN already-held custody
and disposition, not execution of that refused investigation.

No current serving version, first-availability timestamp, actual September
crossing count, or live customer improvement is inferred from these fixtures.

## Acceptance and return

The finite requested owner disposition is one of: accepted into an existing
lawful maintenance boundary; already superseded with an exact receipt; or a named
custody/permission/consumer blocker. Evidence delivery is not that disposition.
If source work is separately admitted, its return must include the real copy
consumer, healthy-close and degraded-close behaviors, retained historical
observations, same candidate/plan populations, and real browser/publication proof.
