# Seat ruling — CDV-1 Task 3, round 4, 2026-09-30

Seat: CDV-1 Meta-CEO, session `251f88c8`. This record adjudicates the first review of PR #8232 (`reviews/OPUS_T3_PR_REVIEW_R1_2026-09-30.md`, REJECT, B1–B10) and dispatches one fix round on the same PR and branch. It changes no grant, no placement and no Task 1 freeze.

## Dispatch

- **Packet:** `packets/CDV1_T3_R4_PACKET_2026-09-30.md`. It is byte-identical to the `ruling` field the lane received (`args_cdv1_t3_interpretation_r4.json`).
- **Lane:** label `cdv1_t3_interpretation_r4`; glm-codex / glm-5.3 on mini2; PR 8232; fix timeout 14,400 s; seat review.
- **Relation to r3:** the r3 packet is incorporated by reference (the packet's "WHAT STILL BINDS" section) rather than rewritten, so no r3 paragraph can drop silently. The five r3 items this round changes are named in the packet's "r3 ITEMS THIS ROUND CHANGES" section.

## Rulings

| Ruling | Finding | Decision |
|---|---|---|
| R4.1–R4.5 | B1 | The §6.2 display contract, exact. `selection` becomes a closed mapping `{facts, currentness: {state, source_clock}}`, with `None` meaning `currentness_unverified`. Currentness enters the identity. Every observation gains `fact_id`, `family`, `group`, a §5.2 `basis` chip (T1's basis moves to `native_basis`), `label.{en,zh}` from one closed table byte-copied from §5.3, `period` (typed-absent rows take it from `fiscal_scope` by the table's `period_role`) and `value_and_unit.{en,zh}`. `clocks` gains `fiscal_period`, `source_accepted` and `source_currentness`. Every missing item gains one of six `owner` values. |
| R5 | B2 | `compare_eps(current, prior, *, precision, uncertainty=None)`. `precision` only quantizes. A PROVIDED half-width refuses when `prior - uncertainty <= 0`, and no other threshold exists. The plan's call and test stay verbatim. |
| R6 | B3 | One general rule: every selected typed-absent row yields exactly one item, in Task 1 order, with the reason and detail verbatim. Then `margin_to_cash`, then `consensus`. The special subjects `core_reconciliation` and `segment_organic_sales` are deleted. |
| R7 | B4, B6 | The validator type-checks what the rebuild reads, then compares the whole payload. No exception class other than `EconomicInterpretationError` escapes it. |
| R8 | B5 | `SEMANTIC_REVISION` is the digest of `PG_DEFINITIONS`, and `CODE_REVISION` is the digest of the module's own bytes; both are computed at import. Supported means equal to one of them. An unsupported build returns unavailable, and an unsupported validate raises `UnsupportedInterpretationVersion`. |
| R9 | B7 | The source revision is `sha256(source_texts[release.document_id])`, the bytes Task 1 validated against. No release-entry field except `document_id` is read. |
| R10 | B8 | Fixtures obtain every outcome through the real `build_event_workspace`. `_decline` and `_absent_fact_id` are deleted. |
| R11 | B9 | A direct probe of `_validate_pair` with a real row whose period alone is altered. On the build path Task 1 already refuses that row. |
| R12 | B10 | One `_direction` helper for both difference rules. `segment_scope_limitation` fires when segments are PRESENT. `incomplete_margin_to_cash_bridge` fires when no present margin or cash measure exists, which today is every supported build. Findings keep §5.5 order. |
| R13 | (note) | `FINDING_TEXT` is the §5.6 table byte-for-byte, because one copy source prevents drift. |

## Why a bounded design correction, not more special cases

B3, B5 and B10 share one defect class: behavior written as hand-listed cases. The operating brief directs that a surviving defect class gets a bounded design correction rather than another literal case. Each ruling above therefore replaces a list with one general rule, and the packet tells the lane to report under GAPS rather than add a case.

## Spec amendment made in this records PR (design spec §5.7 and §6.2)

R6 emits one item per typed-absent row, so a response with five absent segment rows carries five `segments` items. Two changes follow:
- §5.7 gains owner rows for `demand` and `earnings`, the two owners R4.5 adds;
- §5.7 and the §6.2 missing-context row now say that each owner's sentence renders once, at its first item's position.

The payload stays complete; only the rendering is deduplicated. The spec stays `PROPOSED` until Task 6 merges.

## Carried forward, not in this round

- `next_evidence.company_link` and `.gmi_link` (§6.2): Task 3 owns neither binding. This is resolved at the Task 6 packet, either by Task 6 supplying the links or by amending §6.2.
- Task 4 builds R4.1's `selection` mapping from Task 2's currentness context and publishes it. Task 6 checks the interpretation's `selection` against that published receipt.
- For Task 7 (spec §6.1): the adapter's known-field set for an observation must equal Task 3's closed observation shape as merged, so that no Task 3 field renders "unavailable" as unknown.

## Discharge

| Obligation | Checked by |
|---|---|
| R4–R13 | seat verification of the r4 head (harness, R3 path walk, the eleven mutants' named failures); a bounded re-review limited to R4–R13 |
| §5.7 and §6.2 amendment | this PR |
