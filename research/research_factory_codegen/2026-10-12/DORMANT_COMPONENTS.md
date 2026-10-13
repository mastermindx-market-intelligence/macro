# Dormant accounting and evaluator components

This source slice follows the Research Factory codegen assignment owned by root
`01a1333c-a475-7052-95a8-72a88eb8c17b`. It starts from Macro
`aaa11157958c20643b273e582943d0f629f1f360`. The selected protocol is recorded in
[the preceding source carrier](https://github.com/mastermindx-market-intelligence/macro/blob/1737b5150056379cfcb8e54078c523cfb9dea1ca/research/research_factory_codegen/2026-10-12/PROTOCOL_DESIGN_V1.md),
semantic SHA256 `af9c6e44c95b34832401b94cf2c7280b29532e93d1202f4502d2f9ae4e0da966`.

`engine/research_codegen/accounting_contract.py` compares a trusted caller's full
explicit emitted and inherited variant set with incumbent-owner readback
references. It refuses missing variants even if a declared trial floor preserves
the numerical count. It checks original family, strong configuration/source
identity, history anchors, counts and optional original Vault consumption
references. All generation, execution, evaluation and authority flags remain
false. Reference agreement does not prove caller or owner authenticity, unseen
history completeness, exclusive writer custody, durability or label mediation.
The existing Trial Ledger and Vault implementations are unchanged.

`engine/research_codegen/evaluation.py` accepts immutable trusted source,
formation and feature-score records. It requires the fixed nine-sector cohort,
complete source calendars and horizons, the 26-session formation grid anchored
on 2010-01-04, and exact finite score coverage. A missing or invalid score refuses
the whole result. It selects the highest `ceil(n/2)` scores with lexicographic
ties, calls the unchanged `_per_entry_rows` once, and selects candidate entries
from those same measured baseline objects. It refuses missing, swapped or
physically inconsistent native measurements. Results contain paired descriptive
adverse-loss diagnostics and coverage; they grant no statistical or promotion
acceptance. The 25-session excursion deliberately includes four sessions after
the fixed 21-session exit, as the incumbent ruler specifies.

The assigning Sol coordinators produced these artifacts directly after verified
Fabric prelaunch admission refusals. The original root independently reviewed
them and required repairs to calendar-anchor binding, impossible measurement
acceptance and boolean/float count equivalence. The integrated affected suite
passed **102 tests**: 66 accounting cases, 35 mocked evaluator cases, and one
real fixed-wrapper integration using entirely invented returns. That final test
calls no CLI, data loader, writer, gauntlet or candidate source. It establishes
synthetic numerical integration only. The existing Research Factory CI job owns
both test files and explicitly installs its numerical test dependencies.

This package is unregistered and unwired. No candidate generation or execution,
historical evaluation, canonical accounting write, Vault label release, workflow
activation, product routing or deployment is introduced. Physical containment,
effective repository protections, qualified real source/calendar/vintage evidence,
trusted writer and label-release integration, full input/output identity mapping,
statistical calibration and the authenticated operator/prospective workflow remain
separate obligations. Pending contract, transport and structural-check artifacts
are not silently treated as accepted by this source slice.
