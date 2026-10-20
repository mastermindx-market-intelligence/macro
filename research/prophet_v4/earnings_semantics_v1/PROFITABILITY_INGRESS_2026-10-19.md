# Profitability evidence at the explanation boundary

Status: BUILT_NOT_PROVEN / Draft-HOLD. Continues Prophet #6817, Q06/B14/B15,
inside the already merged earnings evidence owner. No score or trade admission.

## User-visible defect

The existing source producer correctly calculated revenue1000→1200 and operating
income100→108 as margin10%→9%, a compression100 basis points. But a later mutable
payload could replace margin_change_bps with+500, retain its issuer/event labels,
and pass both factual_dossier and earnings_evidence_brief. The explanation then
reported supporting MARGIN_EXPANSION. Missing source references and clocks after
the decision were also accepted. This is a native synthetic reproduction, not
an observed market-data or production incident.

## Repair in the existing consumer

A single shared validator is now invoked at both dossier assembly and explanation.
It validates the producer's existing closed output fields, issuer/event identity,
profit metric and decomposition label, four carried source refs/clocks, child cut
and parent cut, finite positive revenue denominators, and every derived value
against the existing symmetric revenue/margin identity. Numeric tolerance cannot
reverse direction or turn a true zero into positive/negative evidence. Wrong shapes
raise the established EvidenceError. No original source inputs are manufactured.

The producer, C1 defaults and all financial-policy permissions are unchanged. A
zero margin change is now neutral context rather than supporting evidence. Gross,
operating and net profit remain distinct; profit growth does not automatically
mean margin expansion, a positive surprise, remaining upside or permission to buy.

## What this does not prove

This verifies only data carried by the native serialized bridge. It does not
re-authenticate opaque references, reconstruct omitted original periods/bases,
license data, supply missing D5 operating-income facts, change historical clocks,
or independently validate the original source producer. Those owners and their
comparability/readiness gates remain. The existing API currently exposes actual
available facts; this repair does not manufacture broad profitability coverage.

## Executed evidence

On base a88592f801123a6d06268c712b318cf1fe6e7e35, the newly added native cases first
produced79 failed/17 passed on the unchanged source. After the fix, the existing
earnings/D5/API/deploy battery produced758 passed,9 skipped,16 warnings. Skips
require omitted sparse data/site or committed board artifacts; they are not passes.
Two hundred seeded synthetic comparisons retained exactly identical producer
outputs and were accepted through both new validation boundaries. No financial
outcomes or protected experiments were read.

Raw native red/green logs, compatibility results and frozen source/test hashes are
in profitability_integrity_20261019/verification.json. Earlier scratch-overlay
runs are diagnostic only and are not counted again as native acceptance.
Existing CI owners and API restart coverage remain intact; no new workflow or CI
waiver. Hosted checks and genuinely independent source review remain required.

## Continuity

Original operation prophet-profitability-evidence-integrity-20261019-01a14838,
original branch sol/web-prophet-profitability-evidence-integrity-20261019-01a14838.
An interrupted setup was reconciled to no registered tree, branch, directory or
active acquisition before that same canonical operation was resumed successfully.
No replacement workspace or source carrier was created. Source comparison against
main3091c889 found no change to the earnings engine, its test or D5 dossier.
Preserve #9634, #9714, #8240/#8091, #7772 effects and D06/H1/Cycle holds.


## PR-time regression delivery

The existing fusion suite previously executed only in the data-gated owner. The
incumbent prophet-lab code job now also runs the bounded profitability selection:
122 passed,276 deselected,zero skipped. Exactly two paths and one step were added;
all other326 jobs and the data-gated execution remain unchanged. The canonical
curated import-closure regression also passed (1 case). This is an execution
registration repair, not a new workflow, reduced guard or historical CI reuse.

The failing pytest trace is stored losslessly as native-red.log.json: concatenating
its lines array and UTF-8 encoding reconstructs the original bytes and recorded
SHA-256. This preserves pytest's trailing spaces without weakening diff checks.
No failing result or trace content was edited to make a check pass.
