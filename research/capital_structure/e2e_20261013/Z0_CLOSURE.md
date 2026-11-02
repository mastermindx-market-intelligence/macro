# Capital Structure V2: Z0 closure map

Masterplan: draft #9115, §13 Z0 ("Map W0–W7 included outcomes to evidence; reconcile children, holds, unknown effects and excluded obligations. Close only proven scope."), with §16 for the wave mapping.

Each row gives the outcome, the PR that landed it, and that PR's squash SHA on `main`. "Code landed" means the PR is on `main` and its fixture tests pass; it does not mean the outcome has been seen on real served data. A row whose real-data evidence is still pending is marked OPEN. This map was last reconciled against `origin/main` on 2026-11-02.

**Closure verdict: PARTIAL. Only W0 is closed.** W1, W4 and W6 have their code landed, but none of their real-data outcomes is proven: on today's served data every evaluate is a typed refusal (V0: 0 of 3258 issuers are evaluable), and each input family waits on a natural nightly or on the human gate named below. W2, W3, W5 and W7 each still have open rows. The workstream record still holds W3 and W4 behind the W2 natural proof, and this closure does not lift that hold (see "Holds"). Nothing in this file claims a real evaluated scenario.

## Holds

| Hold | Recorded in | Disposition in this closure |
|---|---|---|
| #8673 (held UI repair, owns `site/capital_structure.js`, `templates/capital_structure.js` and their tests) | workstream record lines 153–155 | Stands. The PR is an open draft at head 851d7f7c. Real-browser A34 evidence was produced on that head, but its hosted `gate: data` is still open and no release is recorded. Never lifted by inference. |
| W3 and W4 held behind the W2 natural proof | `agentos/workstreams/WS-CAPITAL-STRUCTURE-INTELLIGENCE-V2.md` lines 155–156 ("W3 and W4 remain held"), 200 ("W3/W4 remain held until that proof closes W2") and 269; handoff `agentos/handoffs/CAPITAL-STRUCTURE-INTELLIGENCE-V2-2026-10-13-r2.md` lines 18–19 | Stands. W3 and W4 code was merged anyway (the PRs listed below). The workstream record does not record a release of this hold, and this closure does not infer one. W3 and W4 stay OPEN until W2's natural proof closes and the hold is released in the record. |
| W2C / W2D BUILT_NOT_PROVEN | workstream record lines 155–156, 196–200, 226, 237 | Stands. See the W2 table. |

## W0: R0, C0 — CLOSED

| Task | Evidence | Squash SHA | State |
|---|---|---|---|
| R0 | Reconciliation done 2026-10-13. #5959/#6415/#6424 merged; #5901 closed as absorbed. Workstream record `agentos/workstreams/WS-CAPITAL-STRUCTURE-INTELLIGENCE-V2.md` (original owner kept, no duplicate parent). The #8673 hold and the W3/W4 hold are reconciled in "Holds" above: both stand. | n/a (record) | done |
| C0 | #9159; fixes #9266, #9278, #9263 | 2fafe10e, 0179dccb, 05bcc762, 2af42e8d | landed |
| #5901 | absorbed into #5959 and not reopened (A01) | n/a | reuse |

## W1: R0, R2, T0 — code landed; real-data outcome OPEN

| Task | Evidence | Squash SHA | State |
|---|---|---|---|
| R2 | #9146 | d8b1c105 | code landed |
| T0 | #9270 | cb1c0ebb | code landed; real-data outcome OPEN. The nightly compiler refused every night because the `cs_candidates` step had no source-store env (see "Why every issuer is unevaluable today"). |
| T0 nightly store env | #10555 | e7232371 | code landed; OPEN until the first natural nightly after merge |
| T0 path fixes | #10575 (same-night visibility) / #10576 (per-issuer decisions) | 16cda951 / a427d4a6 | code landed; OPEN until a natural nightly exercises them |
| E0 (reference pack) | #9244 | 6f160f83 | landed |

## W2: R1, R2 (natural-chain proof, never a manufactured dispatch) — OPEN

| Task | Evidence | State |
|---|---|---|
| R1 | A silent GH001 publication loss was diagnosed and repaired by the sibling #9556 carve-out (861de75d). Capital-structure generations exist for 10-15 (c20db3ec), 10-17 (b9ae8e8f) and 10-20 through 10-31 (latest 748fb147). Whether every night in that range published has not been verified. | natural generations observed through 10-31; continuity unverified |
| R2 | see W1 (#9146, d8b1c105). Its natural-chain proof is part of the W2 proof below. | code landed; OPEN |
| W2C / W2D | #6415 (5bc31a70) and #6424 (cadfa403) merged. The workstream record keeps both BUILT_NOT_PROVEN until the first natural scheduled chain containing both proves runtime below warning, healthy current discovery and reconciliation, zero unserved LIVE work and the frozen W1/W2 invariants. This closure has not checked those four conditions against the 10-15 → 10-31 nightlies. | BUILT_NOT_PROVEN |
| Nightlies after 10-31 | The 11-01 scheduled run skipped `collect` at the ET gate. In the 11-02 run (41378879186) `collect` was cancelled, so the `capital_structure` job was skipped. The job stays coupled to `collect` by design. No daily dispatch was made to fill the gap. | OPEN, waits on the next natural nightly |

## W3: P0, U0, U1, U2 — OPEN (held)

| Task | Evidence | Squash SHA | State |
|---|---|---|---|
| P0 | #8673, held UI repair: open draft at head 851d7f7c; real-browser A34 evidence produced on that head; hosted `gate: data` still open. | none | HELD; never lifted by inference |
| U0 | #9355, plus `U0_JOURNEY_FREEZE.md` | b4e1d4c7 | code landed; behind the W3 hold |
| U1A / S0 / U1B | S0 #9618 and U1a #9628 folded into U1B #9689, which folded into #9748 | cb8b16fa | code landed; behind the W3 hold |
| U1C | #10527: real Exhibit 107 fee terms sealed into served state | ba90d91e | code landed; behind the W3 hold |
| U1C-1.3 | #10554 (head beeccff6): parser 1.3.0, B/C/D fee-table recovery from the 99-accession census. 45 → 62 of 99 accessions usable. Accession 0001731122-26-000704 stays ambiguous, and the class B `registration_fee` stays unavailable. 1.0.0–1.2.0 are add-only. Authority goldens unchanged (468 / 35ed9840). A fresh reviewer approved it; the approval is recorded on the PR. | 9b2b7336 | code landed; behind the W3 hold |
| U2 / V0b | #9774: saved scenarios, change desk, dormant monitor, served joint-solve refusal (U2-1 already in #9748) | 527dc17b | code landed; behind the W3 hold |

## W4: L0, L1, C1, C2 — code landed; real-data outcome OPEN (held)

The W3/W4 hold above stands. C1 and C2 have never been evaluated on real data: 0 of 3258 issuers are evaluable today (V0).

| Task | Evidence | Squash SHA | State |
|---|---|---|---|
| L0 | #9314 | d054f60f | code landed; real-data outcome OPEN (0/3258 evaluable) |
| L1a / L1b | #9363 / #9359 | cfb56918 / 7dd06ff5 | code landed; real-data outcome OPEN (0/3258 evaluable) |
| C1 | #9374 | 8f00ee9a | code landed; real-data outcome OPEN (0/3258 evaluable) |
| C2a / C2b / C2c-P / C2c-A / C2x | #9393 / #9402 / #9400 / #9414 / #9543 | 9f79ef50 / 07723d7e / 3666527e / d771d488 / bbf93bcc | code landed; real-data outcome OPEN (0/3258 evaluable) |
| C2d | folded into #9748 | cb8b16fa | code landed; real-data outcome OPEN (0/3258 evaluable) |

## W5: T0, I0, I1, I2, X0 — OPEN

| Task | Evidence | Squash SHA | State |
|---|---|---|---|
| T0 | see W1 (#9270) | cb1c0ebb | code landed; real-data outcome OPEN |
| I0 | #9274 | 4908edbf | landed |
| I1a | #9388 | e32d4109 | landed |
| I2a | #9406 | 5f6536be | landed |
| X0a | #9409 | 52163c9f | landed |
| I1b / I2b / X0b | Source extractors that would fill the I1/I2/X0 typed families from filings. Not built. | none | OPEN, deferred |

The I1/I2/X0 engines are on `main` and consume typed records, but no extractor fills those families from filings yet. Until one does, each family answers `unknown` with its blocker named. Nothing else is counted as completing it (A43). This closure does not claim those families are filled from real filings.

## W6: B0, B1, F0, F1, S0 — code landed; real-data outcome OPEN

| Task | Evidence | Squash SHA | State |
|---|---|---|---|
| B0 | #9264 | 3443fc24 | code landed; real-data outcome OPEN |
| B1 | #9277 | 02a88a2e | code landed; real-data outcome held: share_basis is served `share_observations_not_admitted` until a person sets the publication variable (the human gate below), and no corporate-actions producer exists |
| F0 | #9268 | 7cac374c | code landed; binding OPEN |
| F0b | #10564: binds each FIF-covered issuer's financials from FIF's published production datasets | d8d958df | code landed; OPEN until the first natural nightly after merge |
| F0c | #10569: selects that mode and the dedicated `R2_RESEARCH_*` store for the nightly `cs_inputs` step only | 45ba0510 | code landed; OPEN until the first natural nightly after merge |
| F1 | #9283 | 59ea9175 | code landed; real-data outcome OPEN |
| S0 | see W3 (folded) | cb8b16fa | code landed; behind the W3 hold |

## W7: N0, A1, V0, Z0 — OPEN

| Task | Evidence | Squash SHA | State |
|---|---|---|---|
| G0-S / G0-E / A0 / A1 | folded into #9748 | cb8b16fa | landed |
| G0-V | #9770 | b2bf0b63 | landed |
| A1-1 | #10535: served active pair, branch-bound boundary; the monitor records only outbox-proven firings | 4aa393e7 | landed |
| N0 | #10543 (head 4a39aa79): typed `capital_structure` leg in the integrated answer, read through the same `_state_view` the state route serves; typed negatives; receipt leg. `MACRO_INTEGRATED_ANSWER_ENABLED` stays off. A fresh reviewer approved 7ea45d97; 4a39aa79 only merges main and changes no line of the reviewed diff. | 554cdd64 | landed |
| V0 | #10548: validity of a published inputs bundle is cached by file stat, and binding is checked on every request. Measured warm 10×8 p95 is 117–138 ms per route; cold state load 19.8 s; cold inputs validation 4.1 s. **Every real evaluate is a typed 409 `scenario_inputs_unavailable`: 0 of 3258 issuers are evaluable**, because financials, instruments and share_basis are unavailable for all of them. Evaluation p95 is therefore not measured on real data. Numbers are in `V0_OPERATING.md`. The p95 ≤ 2 s target stays a proposal, not acceptance. | 5a56f949 | landed (serving path); evaluation timing OPEN |
| A0-2 / A0-3 / A1-3 / V0-3 | natural nightly proofs | none | OPEN, waits on the nightly |

## Why every issuer is unevaluable today

V0 found three input families unavailable for all 3258 issuers. Each one has a different cause and owner. None of them is fixed by changing a flag.

| Family | Typed reason served today | Cause | Path to a real value |
|---|---|---|---|
| instruments | `candidate_terms_not_materialized` | The nightly `cs_candidates` step had no source-store env, so `build_source_stores()` found no admissible store and the compiler refused every night. | #10555 (`e7232371`) gives that step the same R2 store env as `cs_terms`, with no flag, mode or authority change. It merged after #10575, which keeps the first night (when every candidate is newer than the cutoff) a typed negative instead of a job failure. OPEN until the first natural nightly after merge. That night should still serve `candidate_terms_not_materialized`; from the next night, issuers with a visible candidate should bind. |
| financials | `companyfacts_snapshot_unavailable` | The capacity-inputs producer does not yet bind the financial owner's existing outputs (§13 F0: bind, don't rebuild FIF). | F0b #10564 binds each FIF-covered issuer's financials from FIF's published production datasets; F0c #10569 selects that mode and the dedicated `R2_RESEARCH_*` store for the nightly `cs_inputs` step only (no default change, never the golden AAPL corpus). Only the 5 FIF-covered issuers can get a real family; every other issuer is still served `companyfacts_snapshot_unavailable`, with the unpublished detail `fif_entity_not_covered` in the run summary. F0c landed as `45ba0510` and F0b as `d8d958df`. OPEN until the first natural nightly after both are on `main` binds those 5 issuers. |
| share_basis | `share_observations_not_admitted` | `share_count_observations.jsonl` is produced only when `vars.CAPITAL_STRUCTURE_SHARE_COUNT_PUBLICATION_ENABLED` is true. That variable is a pre-production gate, held until publication protocol v2 and the bounded full-generation retention lane pass their release audits. No corporate-actions producer exists in this pipeline, so actions are unobserved. | Upstream release audits, then a human sets the variable. This seat does not build an exporter that would front-run that gate (B0: no flag activation or admission bypass). Until then the served answer stays this typed negative. |

## Known latent defects (recorded, not fixed here)

None of these changes a served answer today; each is a reason a future answer could be slower, later or less precise than it should be. They are recorded so a later lane starts from them rather than rediscovering them.

| Area | Defect | Effect |
|---|---|---|
| inputs producer | FIXED by #10574 (`12ea2ac3`): `_issuer_rows` re-read the whole candidate/term parquet once per issuer. Each ledger is now read once per file version (stamp: inode, size, mtime). | Was about 157 s of the nightly `cs_inputs` step on a full roster, and quadratic as rows grew. Follow-ups from its review: add `st_ctime_ns` to the stamp, scope the cache to one `build_from_disk` call, and add a non-string `issuer_id` fixture. No current writer can reach a stale read: every ledger writer uses `os.replace`. |
| inputs producer | FIXED by #10575 (`16cda951`): the same-night visibility crash. An issuer whose candidates were all compiled after tonight's cutoff made the resolver raise `ResolutionRefusal("no visible candidate or decision names the issuer")`. Nothing caught it, so the fatal `cs_inputs` step failed the whole `capital_structure` job. It was latent while the candidate ledger was absent, and #10555 would have triggered it on its first nightly; #10575 landed first. That case is now the typed `candidate_terms_not_materialized`. | Prevented a whole-job nightly failure. The hardening from its review is taken by #10555: the gate now asks the resolver's own `visible_candidate_count`, which runs every row check resolution runs, so a tampered, malformed or truncated history still refuses even when every row is late. #10555's main merge drops #10575's parallel `_any_visible` predicate and keeps both integration tests. |
| inputs producer | FIXED by #10576 (`a427d4a6`): the owner decisions ledger was read whole and passed to every issuer's resolution unfiltered. The resolver puts the issuers of the visible candidates and the visible decisions into one set and requires exactly one (`instrument_resolution.py:712-716`). Each issuer now receives only the decisions that name it; a record with a missing, blank or non-string `issuer_id` still reaches the resolver and is refused. Open follow-ups from its review, none affecting published output: records that name an issuer outside the served bundle, or an issuer with no candidate rows, or a string that fails the id pattern, are now dropped without being validated (hardening: validate every ledger line once before filtering); no digest of the whole ledger file is recorded, which was also true before. | Was latent: no decisions ledger is materialized in production (`decisions_ledger_absent`). Without the fix, the first nightly with a decisions ledger naming two or more issuers would have raised "one issuer per resolution required" in the fatal `cs_inputs` step. |
| inputs producer | The "no candidate visible" pre-check runs before decisions are read, so an issuer with decisions but no visible candidate is reported as `candidate_terms_not_materialized`. | A decision-only issuer cannot bind instruments. With no candidate there is nothing to resolve, so this is arguably the correct answer. |
| inputs producer | `candidate_terms_not_materialized` covers both "no ledger file" and "no row visible at the cutoff". | Two different causes share one served reason. The closed reason set is not split without a contract change. |
| nightly clock | `cs_state` fixes tonight's `as_of` before `cs_candidates` compiles, and each candidate is stamped `available_at` = compile time. A new candidate is therefore visible from the next night's cutoff. | A one-night lag for every new instrument. This is honest point-in-time behaviour: at tonight's cutoff the term had not been compiled. The ledger is append-only and keeps the original `available_at`. |
| financials binder | Instant-date selection ignores dimensions and recorded time (F0b review M4); minor items N1–N4 from the same review. Recorded on #10564. | If a dimensioned or later-recorded event sets the date, the requested cells at that date can be missing or past the cutoff. The cell-level clock check still skips them, so the family becomes the typed negative `fif_no_reported_cells` instead of using an earlier date with real values. That is a less complete answer, never a value read before it was available. |
| financials binder | `_clock_moment` silently drops a clock it cannot parse, so availability would fall to the latest clock that does parse. | Not reachable for receipts FIF produces: FIF parses every provenance clock with the same `parse_utc` and writes it back with `utc_text` (`engine/fundamental_forensics/query.py`). Failing closed would only be hardening. |
| tests | `test_u2_daily_job_previous_capture_changes_and_monitor_steps_are_ordered_and_scoped` expected `always()` on `main` while the workflow already said `always() && steps.cs_changes.outcome == 'success'` (a stale assertion shipped with #9774). F0b #10564 and #10555 each pin the shipped gate with byte-identical text, so whichever lands second merges cleanly; the workflow is unchanged. CI never caught it because the `capital-structure-intelligence` legacy job was not selected for those runs. | A red test on `main` until F0b landed (`d8d958df`), which fixed it. |

## Excluded, not completed (§16 W7)

Prophet shadow, predictive offering models and authority promotion. Authority flags stay False. A48 holds: no probability, ranking, sizing or Prophet authority.

## Sibling commits (not this seat's work)

#9785 588dcf3d, #9854 5561ef75, #9844 2309b89d, #10434 916b72ec, #10273 1937fd75.
