# R-ENE-27..28 — Energy nuclear module, round 5 (review-gate closure after #7870 RULING 9)

- Seat: Energy Fable CEO, session 8955bbc3 (claude8). Operation `gmi-energy-fable-ceo-e2e-20260923-chairman-001`.
- Issued 2026-09-25 11:30Z. PR #8002 at `fa4ebadbb9fe7dcdacf4513fa67f454a41f895fc`. Round 4 was ACCEPTED there by the independent Opus closure check.
- Trigger: #7870 comment 5830798482 (RULING 9, Robotics owner, 10:20Z). It confirms a review-gate leak across the theme-research family and names nuclear as having inherited it.

## Why an accepted round reopens
- The round-4 ACCEPT stands for everything it checked.
- RULING 9 is a material invalidator: new evidence from the shared-base owner about a class of site no Energy review had examined. These are reads of the PRE-gate set (`selection.assertions`) outside the evidence selector, and they let records that failed review (held, rejected or review-expired) count.
- Only those sites reopen. Nothing else from rounds 1–4 is redone.

## R-ENE-27 — the nuclear sites, classified against RULING 9

| RULING 9 class (Robotics line) | Nuclear site at `fa4ebadbb9fe` | State | Ruling |
|---|---|---|---|
| evidence selector (:1271), LEAK | `select_authorized_evidence` over `selection.review_ok` (:818) | already closed by R-ENE-20 | none |
| `evidence_refs` (:1170-1176), LEAK | `evidence_refs` over `selection.current` (:756-759) | already closed | newly pinned: with every record withheld, no assertion ref is advertised |
| view reason (:1019), WRONG REASON | `_views` reason: `not selection.assertions` (:669) | OPEN | **E2** → `not selection.current` |
| `selected_revisions` (:904), existence leak | `_summary` block support over `selection.assertions` (:565) | OPEN | **E1** → `selection.review_ok` |
| `authorized_coverage` input_refs / selected (:1239-1240), existence leak | input_refs over `selection.current` (:767); `selected` over `selection.assertions` (:768); `status` over `selection.assertions` (:721) | input_refs closed; `selected` and `status` OPEN | **E4** → `len(selection.current)`; **E3** → `not selection.current` |
| identity-vintage labels (:1136), SAFE | `_refuse_unsupported_identity_vintage` over `selection.assertions` (:693) | SAFE | unchanged |
| review stamps (:439), SAFE | `_now_of_query` over `self.assertions` (:276-280) | SAFE | unchanged |

**Why each choice:**
- **E1 is `review_ok`, not `current`.**
  - RULING 9 names `review_ok` for this site.
  - `current` would also mark as stale a block that cites a collapsed syndicated copy. That copy's fact survives through its original (R-ENE-11), so the stale mark would be false.
  - A block citing a withheld record is marked stale. Its `input_revisions` are published unchanged: that is the interpretation owner's provenance, and rewriting it would be a correction-plane act (forbidden).
- **E4 is `len(selection.current)`, not `len(selection.review_ok)`.**
  - Nuclear's coverage `input_refs` is over `current`, because R-ENE-11 rules that a collapsed copy never appears in any `input_refs`.
  - The base composer counts `selected` over the same set as `input_refs` (`semiconductor_theme_research.py:1007-1013`), so `selected == len(input_refs)` holds there. E4 restores that invariant.
  - `review_ok` would also count collapsed copies that `input_refs` omits. Mutant `r9_selected_review_ok` does that, and the mixed test kills it.
  - The wording differs from RULING 9's Robotics advice (`review_ok`) only because R-ENE-11 already moved nuclear's `input_refs` to `current`. That is relayed to the owner.
- **E2 and E3: `current` and `review_ok` are equivalent.**
  - `current` is empty exactly when `review_ok` is empty. Syndication collapses a copy only into a single surviving original, and supersession never removes a record from `current`.
  - `current` is chosen to match the summary's existing gate (`if not selection.current`).
  - Mutants `r9_reason_review_ok` and `r9_status_review_ok` survive by construction and are recorded as EQUIVALENT.

**Tests (append-only, R-ENE-19).** `tests/test_nuclear_research_review_gate.py` is a new file with 4 tests and 9 cases. No existing test or fixture changes.
- Withheld records (held, rejected, expired) produce: coverage `unavailable`, `selected` 0, `input_refs` [], reason `no_selected_assertions` in every view (the manufacturing view keeps `no_manufacturing_evidence`), and no assertion `evidence_refs`.
- An accepted N04 plus its collapsed copy X05 plus a rejected N05: `selected == len(input_refs) == 1`.
- A block citing a withheld record: its `why_it_matters` and `offset` items are stale, their provenance is kept, and the summary is `degraded` with reason `interpretation_stale`.
- A block citing a current record, or a collapsed copy, stays supported.

**Seat verification (11:26Z).**
- Red check at `fa4ebadbb9fe`, with the new file and the unfixed engine: `7 failed, 2 passed`. The 2 passing tests are the "stays supported" guards, which are meant to pass both before and after the fix.
- Sim with the four edits: `71 passed` (62 + 9, route test executed). Without httpx (ModuleNotFoundError shim): `69 passed, 1 skipped`, and the only skip is `test_nuclear_research_route.py:7`.
- Mutant matrix (`r5gate/mutplug5.py`): 34 mutants plus the unmutated baseline, which gives `71 passed`. The 25 round-4 mutants and the 9 new `r9_*` mutants make 34. Of these, 31 are killed and 3 are equivalent.
  - 24 of the 25 round-4 mutants are still killed; the 25th, `role_pred`, stays EQUIVALENT (R-ENE-26);
  - `r9_stale_pre`: 3 failed; `r9_stale_current`: 1; `r9_reason_pre`: 3; `r9_status_pre`: 3; `r9_selected_pre`: 4; `r9_selected_review_ok`: 1; `r9_evrefs_pre`: 3;
  - `r9_reason_review_ok` and `r9_status_review_ok`: 71 passed (EQUIVALENT).
- pyflakes is clean on both files.
- Mechanical application of packet `ene_w2_nuclear_module_r5fix` to a fresh export of `fa4ebadbb9fe` gives files byte-identical to the sim: engine sha256 `716165bfae32d11b…`, test `abf611716b1fd390…` (4180 bytes).
- The scope is exactly two paths.

## R-ENE-28 — label-to-node binding gap (relay only; no Energy change)
- Rows print `subject.source_business_label` verbatim. The witness cohort keys on `subject.company_node_id`.
- The shared curation contract does not bind the label to the node id. So an assertion labelled "Cameco" that carries `co:us:SMR` passes the `reactor_technology` cohort and renders `rows ['Cameco']`. The round-4 closure review recorded this under GAPS, and the seat reproduced it with explicit NuScale/Cameco labels.
- This is input integrity for the shared curation/identity owner (#7870). It does not promote CCJ's node.
- Under R-ENE-09, Energy does not patch the base or add a private label check. The seat relays it to the #7870 owner together with R3-7, the lineage that names a rejected predecessor's revision (the family pattern at Robotics :1295-1320).
