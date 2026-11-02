# Capital Structure V2: Z0 closure map

Masterplan: draft #9115, §13 Z0 ("Map W0–W7 included outcomes to evidence; reconcile children, holds, unknown effects and excluded obligations. Close only proven scope."), with §16 for the wave mapping.

Each row gives the outcome, the PR that landed it, and that PR's squash SHA on `main`. A row whose evidence is still pending is marked OPEN. This map was last reconciled against `origin/main` on 2026-11-02.

**Closure verdict: PARTIAL.** W0, W1, W4 and W6 are closed on landed evidence. W2, W3, W5 and W7 each still have open rows, listed below with the exact thing each one waits for. Nothing in this file claims a real evaluated scenario: on today's served data every evaluate is a typed refusal (see V0).

## W0: R0, C0

| Task | Evidence | Squash SHA | State |
|---|---|---|---|
| R0 | Reconciliation done 2026-10-13. #8673 is an open draft whose hosted `gate: data` and real-browser gates are still open; the hold stands. #5959/#6415/#6424 merged; #5901 closed as absorbed. Workstream record `agentos/workstreams/WS-CAPITAL-STRUCTURE-INTELLIGENCE-V2.md` (original owner kept, no duplicate parent). | n/a (record) | done |
| C0 | #9159; fixes #9266, #9278, #9263 | 2fafe10e, 0179dccb, 05bcc762, 2af42e8d | landed |
| #5901 | absorbed into #5959 and not reopened (A01) | n/a | reuse |

## W1: R0, R2, T0

| Task | Evidence | Squash SHA | State |
|---|---|---|---|
| R2 | #9146 | d8b1c105 | landed |
| T0 | #9270 | cb1c0ebb | landed |
| E0 (reference pack) | #9244 | 6f160f83 | landed |

## W2: R1, R2 (natural-chain proof, never a manufactured dispatch)

| Task | Evidence | State |
|---|---|---|
| R1 | Closed on silent GH001 publication loss, then repaired by the sibling #9556 carve-out (861de75d). Nightly capital-structure generations ran 10-20 → 10-31; the latest is 748fb147. | natural chain proven through 10-31 |
| Nightlies after 10-31 | The 11-01 scheduled run skipped `collect` at the ET gate. In the 11-02 run (41378879186) `collect` was cancelled, so the `capital_structure` job was skipped. The job stays coupled to `collect` by design. No daily dispatch was made to fill the gap. | OPEN, waits on the next natural nightly |

## W3: P0, U0, U1, U2

| Task | Evidence | Squash SHA | State |
|---|---|---|---|
| P0 | #8673, held UI repair. Real-browser A34 evidence complete on head 851d7f7c. | none | HELD; never lifted by inference |
| U0 | #9355, plus `U0_JOURNEY_FREEZE.md` | b4e1d4c7 | landed |
| U1A / S0 / U1B | S0 #9618 and U1a #9628 folded into U1B #9689, which folded into #9748 | cb8b16fa | landed |
| U1C | #10527: real Exhibit 107 fee terms sealed into served state | ba90d91e | landed |
| U1C-1.3 | #10554 (head beeccff6): parser 1.3.0, B/C/D fee-table recovery from the 99-accession census. 45 → 62 of 99 accessions usable. Accession 0001731122-26-000704 stays ambiguous, and the class B `registration_fee` stays unavailable. 1.0.0–1.2.0 are add-only. Authority goldens unchanged (468 / 35ed9840). A fresh reviewer approved it; the approval is recorded on the PR. | 9b2b7336 | landed |
| U2 / V0b | #9774: saved scenarios, change desk, dormant monitor, served joint-solve refusal (U2-1 already in #9748) | 527dc17b | landed |

## W4: L0, L1, C1, C2

| Task | Evidence | Squash SHA |
|---|---|---|
| L0 | #9314 | d054f60f |
| L1a / L1b | #9363 / #9359 | cfb56918 / 7dd06ff5 |
| C1 | #9374 | 8f00ee9a |
| C2a / C2b / C2c-P / C2c-A / C2x | #9393 / #9402 / #9400 / #9414 / #9543 | 9f79ef50 / 07723d7e / 3666527e / d771d488 / bbf93bcc |
| C2d | folded into #9748 | cb8b16fa |

## W5: T0, I0, I1, I2, X0

| Task | Evidence | Squash SHA | State |
|---|---|---|---|
| I0 | #9274 | 4908edbf | landed |
| I1a | #9388 | e32d4109 | landed |
| I2a | #9406 | 5f6536be | landed |
| X0a | #9409 | 52163c9f | landed |
| I1b / I2b / X0b | Source extractors that would fill the I1/I2/X0 typed families from filings. Not built. | none | OPEN, deferred |

The I1/I2/X0 engines are on `main` and consume typed records, but no extractor fills those families from filings yet. Until one does, each family answers `unknown` with its blocker named. Nothing else is counted as completing it (A43). This closure does not claim those families are filled from real filings.

## W6: B0, B1, F0, F1, S0

| Task | Evidence | Squash SHA | State |
|---|---|---|---|
| B0 | #9264 | 3443fc24 | landed |
| B1 | #9277 | 02a88a2e | landed |
| F0 | #9268 | 7cac374c | landed |
| F1 | #9283 | 59ea9175 | landed |
| S0 | see W3 (folded) | cb8b16fa | landed |

## W7: N0, A1, V0, Z0

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
| instruments | `candidate_terms_not_materialized` | The nightly `cs_candidates` step had no source-store env, so `build_source_stores()` found no admissible store and the compiler refused every night. | #10555 gives that step the same R2 store env as `cs_terms` (no flag, mode or authority change). OPEN: in review and CI. Proof is the first natural nightly after merge. |
| financials | `companyfacts_snapshot_unavailable` | The capacity-inputs producer does not yet bind the financial owner's existing outputs (§13 F0: bind, don't rebuild FIF). | F0b #10564 binds each FIF-covered issuer's financials from FIF's published production datasets; F0c #10569 selects that mode and the dedicated `R2_RESEARCH_*` store for the nightly `cs_inputs` step only (no default change, never the golden AAPL corpus). Only the 5 FIF-covered issuers can get a real family; every other issuer gets `fif_entity_not_covered`. OPEN: in review and CI. Proof is the first natural nightly after both merge. |
| share_basis | `share_observations_not_admitted` | `share_count_observations.jsonl` is produced only when `vars.CAPITAL_STRUCTURE_SHARE_COUNT_PUBLICATION_ENABLED` is true. That variable is a pre-production gate, held until publication protocol v2 and the bounded full-generation retention lane pass their release audits. No corporate-actions producer exists in this pipeline, so actions are unobserved. | Upstream release audits, then a human sets the variable. This seat does not build an exporter that would front-run that gate (B0: no flag activation or admission bypass). Until then the served answer stays this typed negative. |

## Known latent defects (recorded, not fixed here)

None of these changes a served answer today; each is a reason a future answer could be slower, later or less precise than it should be. They are recorded so a later lane starts from them rather than rediscovering them.

| Area | Defect | Effect |
|---|---|---|
| inputs producer | `_issuer_rows` re-reads the whole candidate/term parquet once per issuer. | About 157 s of the nightly `cs_inputs` step on a full roster; quadratic as rows grow. |
| inputs producer | The owner decisions ledger is read globally, and the "no candidate visible" pre-check runs before it, so an issuer with decisions but no visible candidate is reported as `candidate_terms_not_materialized`. | A decision-only issuer cannot bind instruments. |
| inputs producer | `candidate_terms_not_materialized` covers both "no ledger file" and "no row visible at the cutoff". | Two different causes share one served reason. The closed reason set is not extended to split them without a contract change. |
| nightly order | Candidates are compiled after the state step, so a new candidate is stamped after tonight's cutoff and binds on the next night's. | One-night lag for every new instrument. |
| financials binder | Instant-date selection ignores dimensions and recorded time (F0b review M4); minor items N1–N4 from the same review. Recorded on #10564. | If a dimensioned or later-recorded event sets the date, the requested cells at that date can be missing or past the cutoff. The cell-level clock check still skips them, so the family becomes the typed negative `fif_no_reported_cells` instead of using an earlier date with real values. That is a less complete answer, never a value read before it was available. |
| financials binder | `_clock_moment` silently drops a clock it cannot parse, so availability would fall to the latest clock that does parse. | Not reachable for receipts FIF produces: FIF parses every provenance clock with the same `parse_utc` and writes it back with `utc_text` (`engine/fundamental_forensics/query.py`). Failing closed would only be hardening. |
| tests | `test_u2_daily_job_previous_capture_changes_and_monitor_steps_are_ordered_and_scoped` expected `always()` on `main` while the workflow already said `always() && steps.cs_changes.outcome == 'success'`. #10555 aligns the test. | A red local test on `main` until #10555 landed. |

## Excluded, not completed (§16 W7)

Prophet shadow, predictive offering models and authority promotion. Authority flags stay False. A48 holds: no probability, ranking, sizing or Prophet authority.

## Sibling commits (not this seat's work)

#9785 588dcf3d, #9854 5561ef75, #9844 2309b89d, #10434 916b72ec, #10273 1937fd75.
