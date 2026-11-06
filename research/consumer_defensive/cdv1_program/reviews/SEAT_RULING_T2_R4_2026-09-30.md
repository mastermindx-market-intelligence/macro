# Seat ruling — CDV-1 Task 2, round 4, 2026-09-30

Seat: CDV-1 Meta-CEO, session `251f88c8`. This record adjudicates the first review of PR #8234 (`reviews/OPUS_T2_PR_REVIEW_R1_2026-09-30.md`: REJECT, B1–B6) together with the seat's own reading of the same head, and dispatches one fix round on the same PR and branch. It changes no grant, no placement and no Task 1 freeze.

## Dispatch

- **Packet:** `packets/CDV1_T2_R4_PACKET_2026-09-30.md`. It is byte-identical to the `ruling` field the lane received (`args_cdv1_t2_source_currentness_r4.json`).
- **Lane:** label `cdv1_t2_source_currentness_r4`; glm-codex / glm-5.3 on the MacBook; PR 8234, from head `58c72efb`; fix timeout 10,800 s; seat review.
- **Relation to r3:** the r3 packet is incorporated by reference (the packet's "WHAT STILL BINDS" section). The r3 items this round changes are named in the packet's "r3 ITEMS THIS ROUND CHANGES" section.

## Rulings

| Ruling | Finding | Decision |
|---|---|---|
| R4.1 | B2 (H1) | The fiscal scope comes from the admitted calendar and the acceptance clock: the registry's `fiscal_year_end_month` and the latest quarter end strictly before acceptance. The prior interval is the same quarter one fiscal year earlier. Labels come from `_fiscal_identity`, and the document's period verdict gates admission. `asof` is the acceptance date. The report date is never an input to the scope. An unresolved issuer, a malformed clock or a foreign period is a typed refusal. |
| R4.2 | H2 | The currentness vocabulary is exactly spec §5.4 (`up_to_date`, `newer_source_pending`, `currentness_unverified`), carried as one object `{state, source_clock}` at `currentness_context.currentness`. The clock is the one the trace read, in the canonical `YYYY-MM-DDTHH:MM:SSZ` form. The top-level duplicate is deleted. |
| R4.3 | B4, B5 (H3) | Two digests, each from its own source. The release entry keeps the native decoded-text digest. The receipt comes only from `received_bytes`, is cross-checked against the body's UTF-8 bytes, and has a decode label that is never defaulted. The changed-bytes test gets its bytes from the fixture seam and computes every expectation itself. |
| R4.4 | B5, review notes (H3) | One source-identity predicate (same accession AND same text digest) governs the carried clocks, the revision and `supersedes_document_id`. Currentness never enters it. Plan step 2.4's 8-K/A test and its "missing prior bytes" test become real probes. |
| R4.5 | H4 | One typed refusal, `PgPreparationRefused(ValueError)`, with a closed `reason` set. A failure to read the prior still propagates. |
| R4.6 | B1 (H5) | `PROFILE_SOURCE_FAMILY` exactly as erratum T2 R6 rules. |
| R4.7 | B3 | The exact-accession path builds the same acquisition as the latest-accepted path, with its receipt and currentness. The success path is tested. |
| R4.8 | B6 | Remove the dossier-job line. The three closure-required widenings to other jobs are ratified. |

## Why R4.2 departs from the r3 vocabulary

The reviewer noted that `unverified` matched the r3 packet's own vocabulary, which is true. The seat nevertheless rules the spec §5.4 tokens for three reasons:
- Task 3 accepts exactly those tokens (Task 3 R4.1 and R5.1);
- Task 4's commissioned job is to pass Task 2's object through, not to translate it;
- a translation layer in Task 4 would be one more place for the vocabulary to drift.

The rest of the trace keeps its own records.

## Verification the seat will run on the r4 head

- The seat harness: grants, freeze, RED/GREEN, both job lines, ci_pack, contract-delta, pyflakes, merge-tree.
- A hunk-level check that no line of the `earnings-economic-dossier` job changed.
- Independent re-runs of the sixteen mutants.
- A bounded Opus re-review limited to R4.1–R4.8.

## Integration order

Task 2 and Task 3 run in parallel on disjoint grants. Whichever lands second merges main first, and the seat runs `git merge-tree` against the other before the second merge. Task 4 starts only after both merge, and its packet takes `currentness_context.currentness.state` and `.source_clock` from the merged Task 2.
