# Data-health test and documentation drift qualification — 2026-11-12

This bounded repair addresses nine original failure cases from issue #5979.
The five-dependency repair is already merged separately as #11108.

## Changes

| Scope | Correction | Production behavior |
|---|---|---|
| Five delayed-board cases | Select the standalone production delayed-note conditional instead of an earlier data attribute/header | Dashboard remains byte-identical |
| Russell cache-handoff assertion | Match the current push-step label while preserving exact-name uniqueness, ordering, receipt/session qualification and cache keys | Workflow remains byte-identical |
| Tape writer-integrity check | Read through one opened binary handle so metadata and rows belong to one snapshot; correct the old pathname inference | Writer/readers remain byte-identical |
| Signal Bus freshness/count | Generate from main's 651 registrations and record merged #10527's parse-receipt registration | Registry and generator remain byte-identical |

## Executed proof

The banner/Russell selection produced **6 failures / 14 passing controls** before
the changes and **20 passes** afterward, with no errors or skips. The controls
include the actual workflow gate executed in 13 hermetic states.

The Signal Bus module produced **2 failures / 2 passes** before regeneration and
**4 passes** afterward, with no errors or skips. The unchanged canonical generator
wrote only docs/SIGNAL_BUS.md. Complete ID equality, byte equality, determinism and
Mermaid checks pass. The document adds one parse-receipt row and changes only the
Capital Structure, infrastructure and Git-storage counts.

All 24 newly executed candidate cases use the normal repository conftest. Source
hashes and data/site status remain unchanged across each test session. The network
guard records zero attempts. The machine report retains commands, exact inputs,
JUnit/log hashes, full logs, source bindings and native-runtime limitations.

## Reused tape acceptance

[Original executed receipt](https://github.com/mastermindx-market-intelligence/macro/issues/5979#issuecomment-6786440438)
uses the same five source blobs and pandas 3.1.1 / PyArrow 26.0.1 / NumPy 2.5.4.
It records four deterministic pathname failures across atomic replacements,
four exact old-snapshot successes through an opened handle, and four in-place
corruption controls that still fail. The original class was 3 passes / 1 failure; the
prepared correction was 4 passes plus 40 passes across ten fresh processes.

The adopted executable patch is identical to that accepted correction; only its
explanatory docstring is additionally corrected. The complete verifier, outputs,
source manifest and canonical receipt are retained in the machine report.
No accepted tape test was rerun. The reader thread, unsuppressed failures,
32-day row preservation, unique-temp and failed-write cleanup assertions remain.

## Source and custody

Publication base: e7f8565ca26b74b9ae0d637b336e9985d513ff9d.
All five mutable target preimages match that base. The collectors/config/engine/
templates/scripts/lib trees equal the earlier native proof base 6a4cb642.
Direct dashboard, workflow, tape and Signal Bus inputs are separately matched.

Finite exact-file custody includes retained complete inventories, residual H/M
comparisons, refreshed moved heads and the final new-PR frontier. #9574 has a
compatible generated-document baseline overlap. Its three DarkFlow registrations,
refused C4 operation and original UNKNOWN CI are not adopted or replayed.
#11092 cycle work, #11055, template/site refusal and all other held effects remain
separate. No workflow, installer, selector, owner identity, budget or release
control changes.

## Acceptance boundary

These are native affected-path results and source conservation evidence. They do
not assert a green full scheduled DATA lane, deployment, deployed-reader safety,
or completion of the broader #5979 issue. Fourteen other nonpackage cases in the
five diagnosed owners remain outside this repair. Ordinary new-PR CI and installed
merge-on-green release remain required.
