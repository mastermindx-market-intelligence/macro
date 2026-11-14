# Macro reading: truthful absence explanations

Date: 2026-11-14

## Consumer problem and decision

The Macro overview currently uses late-arrival wording for source failure and staleness, labels missing coverage as a rights restriction, and promises first publication or nightly refresh when no verified publication is available. Those explanations are not supported by the producer's typed facts. Comparable figure rows can also bypass rights, coverage and release restrictions in the structural-summary shortcut.

This change selects plain English and Chinese explanations from the actual availability, headline absence reason, or typed read failure. It preserves the economic state, values, tones, source dates, source classifications and action authority. No new freshness state, endpoint, scoring model, control plane, entitlement or release path is introduced.

## Scope and custody

- Source pin: `1a974658633b50b050366a34eee1a76875559d9b`.
- Publication parent: `fa704f31ba33adfc7bc474bfbe7e8bf84dd808bf`; intervening changes only touch marketing and research-vault data. All three edited source preimages are identical.
- The exact target functions and label tables were also compared with active Macro PR #11258 at `5f464a227fd33799210bcfca294b8b63099d5c4a`. They are identical; other changes in those files remain that writer's work.
- This isolated main-based change does not modify #11258 or Terminal's live parent #1524. Integration must preserve those writers' unrelated changes.
- Mastermind source-law pin: `199fd4f91ecc426b1d974eb3bf47f5162476cf24`.

Preimage Git blob identities:

| Path | Blob |
| --- | --- |
| `lib/macro_suite_view.py` | `2c7a4c266d8f84552b68ceb10b169d1a3f1cd2cc` |
| `lib/macro_suite_labels.py` | `309c0458fb15f974170314decf58adbcc79ad8b1` |
| `tests/test_macro_command_read_strip.py` | `ccb04eb43ce9d06f0effb335d49de1de36fed0d8` |

## Behavior

Hard availability conditions take precedence over structural absence. Known headline absence reasons then select their matching explanation. Only explicit NOT_APPLICABLE establishes that the section has no single summary. A permitted reporting lag is not described as a missed delivery. Missing or unknown reasons receive a bounded fallback without a refresh promise.

| Producer fact | Presentation cause | Meaning |
| --- | --- | --- |
| SOURCE_FAILED | source_failed | Source data are unavailable for this reading. |
| STALE_SOURCE | stale | Source data exceed the allowed age for this reading; no update clock is invented. |
| RIGHTS_BLOCKED | rights | Usage rights restrict display. |
| NOT_COVERED | not_covered | This publication does not cover the reading. |
| NOT_YET_RELEASED | not_released | The source has not published the reading yet. |
| COMPUTATION_REFUSED | calculation_refused | The publication provides no summary calculation; other measures may still exist. |
| NOT_APPLICABLE | no_state | The section provides individual measures without one summary reading. |
| LATE_WITHIN_TOLERANCE without a more specific cause | late | Inputs remain within the permitted reporting lag; the summary is unavailable. |
| Missing snapshot without a recognized typed failure | no_snapshot | No verified publication is available. |
| Unknown or absent headline reason | unavailable | The summary is unavailable; further details remain in the section. |

COMPUTATION_REFUSED remains a headline/read-failure reason, not a new freshness state.

The `see_curve` shortcut is reachable only after a structural `no_state` result and usable comparable figure rows. It retains the producer date and any permitted-lag, historical or simulated qualification. Hard source conditions cannot be bypassed by retained rows. No change is made to the shared `_snapshot_figure_populated` helper.

Only one primary absence explanation is shown in a null chip. A structural absence or explicit calculation refusal takes priority over a secondary permitted-lag note; the detailed workspace remains the place for all source qualifications.

## Qualification

- New regression cases against the original implementation: **25 failed, 9 passed**. Failures reproduced conflated causes, missing typed failures, shortcut bypasses and unsupported copy.
- Final focused producer and existing template/theme checks: **66 passed, zero skipped**. This includes all 34 new cases and 32 existing cases.
- Actual pinned `_macro_command_macros.html.j2` rendered eight distinct absence conditions through `build_command_header`, using strict undefined handling and the real bilingual state-strip macro. Both language notes survived in the output and the existing copy guard reported **zero violations**.
- Preserved owner-state tests cover unchanged market values, tones, clauses, source dates and source objects. A usable zero-delta figure remains usable.
- Eight full-checkout tests requiring the shipped site/artifacts were not run in the sparse local qualification tree. They remain unchanged and belong to the existing hosted gate. No test is newly skipped, no job is added and no CI definition is edited here.
- Local warnings concern the installed pytest plugin's deprecated symbol and marker registration absent from the sparse tree; they do not change test outcomes.

The native Terminal reader accepts `cause` as an open presentation value and renders the supplied bilingual `note`. Its existing `see_curve` handling is retained. Previously saved fixture text does not prove regenerated output.

## Programme continuity

This repair supports the native Macro consumer work in [Terminal #1533](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1533), including the paired Inflation readout, source evidence and overview/study hierarchy. Editable Paper studies and exports are recorded in that PR. The separate [Inflation owner publication proof #11277](https://github.com/mastermindx-market-intelligence/macro/pull/11277) establishes the owner-to-consumer rate handoff.

The parent mission remains open: protected source integration, route/registry activation with the correct custody, remaining original-masterplan scope and authenticated deployed consumer proof are still required. This patch and its CI are not production acceptance. Preserve the existing controller, live writers and release holds; consume this exact head's binding CI before any release opt-in.


## Binding CI repair — exact frozen-copy registration, 2026-11-14

The original exact-head CI run 43624816924 at 57b3650375746bfd7edfdf181b6ecb1fdea3b27b failed pack 1 / job 132538991230. Its semantic artifact 14128867004 recorded one failed proof, 351 passed and two downstream proofs not run. The failure was `test_11_thirteen_other_suite_pages_byte_identical` in the rates-and-curves proof: the intended bilingual LATE_WITHIN_TOLERANCE note differed from the paired frozen hub golden. This was an owned copy change, not an inherited infrastructure failure.

Register only the exact rendered bilingual span in `tests/fixtures/macro_suite_t11/collapses/reading_cause_copy_11279.json`. The incumbent collapse mechanism maps that exact approved copy to the frozen comparison text. The new span is “within the allowed reporting lag” / “发布滞后仍在容忍范围内”; the frozen span is “arriving late” / “延迟送达”. The why field records this bounded intent. No golden page, input snapshot, test implementation, workflow, freshness token or model value is changed.

Qualification used the original immutable 57b365 source plus this one registration. The source checkout includes the real templates/theme.js (21a1fb1627ac34badc6078cff486f98486e9b773), templates/data_base.js, all frozen paired pages and inputs, the published site/macro_monetary.html, and the 18 actual site/macrodata inputs from that same commit. Missing local theme.js initially suppressed the existing Analyst link attributes; restoring its exact bytes resolved the qualification closure without another collapse. The mutable-data build test likewise used the actual published source, not copies of the frozen fixture inputs.

Executed command:

```text
PYTHONPATH=<qualification dependencies>:<exact source root> python -m pytest -q tests/test_macro_rates_curves_route.py tests/test_macro_command_read_strip.py
```

Result: **151 passed**, 8 warnings, 12.22 seconds. This includes the frozen-page identity test, all existing collapse/mutation guards, stamp preservation, the read-strip cases, and the full-checkout published-source cases. Warnings are the installed pytest plugin deprecation and unregistered marker notices in this sparse qualification root; no tests skipped or deselected. The prior 148-pass/3-fail local result was incomplete source hydration and is superseded by this result.

This recovery adds only the exact collapse fixture and this appended qualification record to the existing 57b365 branch. New natural exact-head binding CI remains required. This record does not claim merge, publication, release or deployed consumer acceptance.


## Hosted rates-chip assertion repaired — 2026-11-14

Original head `6ddcae927643c9f8973d5f6922cc921b3f0793b3` ran [CI43636227110](https://github.com/mastermindx-market-intelligence/macro/actions/runs/43636227110). Pack1, [job132574651602](https://github.com/mastermindx-market-intelligence/macro/actions/runs/43636227110/job/132574651602), reported one failed assertion among599 passed,9 skipped and13 deselected cases in the Macro pages step. The subsequent hub step did not run. Other selected packs passed; the failed binding gate was not armed.

The failing test explicitly uses `STALE_SOURCE` but still required `hasn't arrived` somewhere in the full hub. That expectation contradicts this PR's source-specific copy and could also pass on an unrelated chip. The repair locates the rates chip by its existing `data-mc-topic="rates"` identity, requires the exact English and Chinese stale-source explanation, and rejects the old arrival wording there. Every E2/stance/comparison and committed-source branch assertion remains. No production source, fixture, economic calculation, data, template, frozen golden or workflow changes accompany this repair.

Exact preimages: test blob `578dc05016219dafe2e3442701bcb6a062118ddf`; unchanged stale fixture blob `fc5f69ed7205e4ddea0a317a4c44c917da9f41bb`. A local run through the actual page builder and existing committed snapshot inputs reproduced the exact original assertion failure. The repaired case plus both previously affected full modules (`test_macro_command_read_strip.py`, `test_macro_rates_curves_route.py`) then passed **152 tests, zero skips or deselections**. The local run reported32 dependency/custom-marker warnings; these are not hidden or treated as production proof. Source modules, current copy-collapse registration, templates and fixture bytes remain unchanged.

This successor stays on the original branch with parent6ddc, and changes only this assertion and this proof record. Normal new-head binding CI must conclude before the single incumbent-controller enrollment. No rerun, baseline dispatch or check waiver was requested. Original native Macro acceptance remains open.

