# Seat ruling — CDV-1 Task 3, round 5, 2026-09-30

Seat: CDV-1 Meta-CEO, session `251f88c8`. This record adjudicates the second review of PR #8232 (`reviews/OPUS_T3_PR_REVIEW_R2_2026-09-30.md`: REJECT, B1–B6) and dispatches one fix round on the same PR and branch. It changes no grant, no placement and no Task 1 freeze.

## Dispatch

- **Packet:** `packets/CDV1_T3_R5_PACKET_2026-09-30.md`. It is byte-identical to the `ruling` field the lane received (`args_cdv1_t3_interpretation_r5.json`).
- **Lane:** label `cdv1_t3_interpretation_r5`; glm-codex / glm-5.3 on mini2; PR 8232, from head `e8666eed`; fix timeout 14,400 s; seat review.
- **Relation to r4:** the r4 packet is incorporated by reference (the packet's "WHAT STILL BINDS" section), so no r4 paragraph can drop silently. The r4 items this round changes are named in the packet's "r4 ITEMS THIS ROUND CHANGES" section.

## Why a design correction, not more cases

The operating brief says that when the same semantic defect class survives again, the seat proposes a bounded design correction rather than another literal special case. This is that second survival.

R4 fixed each earlier defect in place, and the class came back in three new places:
- clocks validated by shape;
- an argument checked after it was used;
- an order borrowed from the caller.

The correction changes where decisions are made, not which cases are listed:
- **Parse once, at one boundary.** Every external scalar is converted exactly once into a typed value. Every function downstream accepts only the typed value, so a renderer can no longer receive an unparsed string.
- **One canonical order.** The selection is normalized to Task 1 row order before anything is derived from it.
- **One fired set.** A finding exists if and only if its rule fired. Its handles are recorded separately and are never used as the firing signal.
- **One differential rule.** A fixture proves its edit caused its outcome by showing the outcome is absent from the base build.

## Rulings

| Ruling | Finding | Decision |
|---|---|---|
| R5.1 | B1, B2 | Private parse functions for instants, dates, tokens, decimals and precision. Each tests type by identity first (`type(x) is T`), then range and form, and raises only `EconomicInterpretationError`. Instants are exactly `YYYY-MM-DDTHH:MM:SSZ`: ASCII digits, `strptime`, round trip. The boundary covers the selection's state and clock, the stored selection on validate, both lifecycle clocks, the four `fiscal_scope` dates and the revision arguments. `_clock_text` and `_fiscal_clock` take parsed values, and `_valid_timestamp` and `_TIMESTAMP_PATTERN` are deleted. |
| R5.2 | B3, note 3 | `compare_eps` parses all four arguments before any outcome. All arithmetic, the quantize included, runs inside one guard that converts `ArithmeticError` into `EconomicInterpretationError`. |
| R5.3 | B4 | Duplicate handles are refused. The chosen rows are returned in Task 1 row order, and every derived list and the identity iterate that list. The same set in any order gives the byte-identical payload. |
| R5.4 | B5 | Findings come from one fired set in §5.5 order, with handles recorded separately. The bridge and `missing_consensus` carry `[]`, and `None` never appears. |
| R5.5 | B6 | One `CAUSED_OUTCOMES` table, and one parametrized test asserting each outcome is present in the edited build and absent from the base build. `unlocated_outcome` targets a metric the base build discloses, edited where Task 1's locator reads. |
| R5.6 | note 1 | A whole-table exactness test against spec §5.3 literals, which replaces the 3-label assertion. |
| R5.7 | notes 4, 5 | A declined comparison carries Task 1's verbatim reason, or `not_selected`, and the invented default is deleted. The unavailable payload carries `missing_context: []`, so R4.5 holds for every payload. |

Note 2 (the order inside `owner_lookup`) is not carried, because owners come only from the closed mapping.

## Verification the seat will run on the r5 head

- The seat harness: grants, freeze, RED/GREEN, dossier line, ci_pack, contract-delta, pyflakes, merge-tree.
- The seat's path probe (`check_t3_r4.py`), extended with the r5 checks:
  - the boundary refusals and positive controls;
  - permutation invariance;
  - the handle invariant;
  - the differential table;
  - the whole label table.
- Independent re-runs of the twelve r5 mutants and the eleven r4 mutants.
- A bounded Opus re-review limited to R5.1–R5.7.

## Carried forward, unchanged

The r4 ruling's carried items stand:
- the `next_evidence` links are resolved at the Task 6 packet;
- Task 4 builds `selection` from Task 2's currentness context;
- Task 7's known-field set equals Task 3's merged observation shape.

Task 2 round 4 (ruling R4.2) now emits exactly the canonical clock form that R5.1 parses. Task 4 therefore passes Task 2's `currentness_context.currentness` into Task 3's `selection.currentness` with no translation.
