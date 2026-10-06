# D2E — D2 acceptance record (WS:GMI-THEME-GRAPH)

operation: `gmi-theme-accept-d2e-20260827-sol-001`  
PIN (Phase 1): `cbfa20a45d8401f1cf1cc9fc48155455f1d612fb`  
PIN2 (Phase 2): `e061209069a1bc05157d9078cd394e9ce1d96cc9`  
GEN (Phase 1): `2026-10-06T08:07:45Z` / DATA_COMMIT (P1): `f7dd82910f315e82f376144388f2b38490c94ffe`  
GEN2: `2026-10-06T13:27:04Z` nightly / observed / belief_time `2026-10-06`  
DATA_COMMIT (natural): `f9ccad3e50f671499893f8113ba96ae2910ab5e7`  
RUN_ID: `37404125352` / ENGINE_JOB_ID: `112118780036` / TRIGGER_COMPUTED_AT: `2026-10-06T13:27:04Z`  
lane host/model (Phase 2): Cursor/Grok bounded fabric builder — META-CEO commission repair round `r2`  
written-at UTC: `2026-10-06T15:35:00Z`  
repair round: `r1d` (Phase 1 harness); `r2` (Phase 2 natural receipt + PIT readers at PIN2); `r2b` (N5 probe + verdict composition); `r2c` (P3 review fixes); `pin3` (PIN3 re-measure)

**Round r1b (repair) — harness corrections by orchestrator E:** D1 materializes `data/reference/security_master.parquet` so R1.B/R2 are not run against a degraded guard. D5 moves MarketOntology half-B docket tests to non-gating R1.X and limits R1.F to theme-graph rights tests. D6 censuses `evidence.source_ref` only via `family_for_source_ref`. D7 treats `site/factordata/us_standouts.json` as intentionally unmapped (PASS when `None`).

**D1 (r1d):** C5/V3 restored to the R-A7 newest-generation population (direct `identity_resolution.parquet` read at `max(computed_at)`, not `store.read_identity_resolution(latest=True)`).

**Round r2b (repair) — harness corrections by seat orchestrator E:** D8 N5 probe amended: GitHub job logs render `::group::` as `##[group]`; probe now matches both forms. D9 round r2 composed PHASE-2/D2E from the first HOLD (N5) although FAIL rows (R1.A, R3.2) existed; rule takes the first FAIL row first.

**Round r2c (repair) — harness corrections by seat orchestrator E:** D10 P3 adversarial review fixes — B1 GEN1 capability generations 53; B2 phase-2 V2/V3 re-measured at GEN2; B3 R1.D CN-panel hydration artifact; M1 R1.A-CI is gate: data (data-health.yml), not a ci.yml pack; M2 pin/head note; m1–m4.

## §1 VERDICT

PHASE-1 VERDICT: PASS at PIN3 ebe35dc916de5aae556371a5aa963c6692175c9c (all gating rows, §6.A)
PHASE-2 VERDICT: PENDING:GEN3 first natural daily.yml engine run whose checkout contains ebe35dc916de5aae556371a5aa963c6692175c9c (cron 22:30Z; seat GEN3 check ~2026-10-07T14:07Z)
D2E VERDICT: HOLD:seat:PHASE-1 PASS / PHASE-2 PENDING:GEN3 (PIN3 ebe35dc916de5aae556371a5aa963c6692175c9c; W3B held until the seat records GEN3)
ROUTED (non-gating): R1.X FAIL-INFO -> MarketOntology CEO A (F00C closure-ledger writer; #8425/#8465/#8496); R1.A-CI INFO -> no data-health.yml run on a head containing PIN3 yet

## §2 GATE MATRIX — PIN1/GEN1 measurement (r1d), historical; PHASE-1 is composed at PIN3 in §6.A

| id | gate | clause / source | command (short; full text in Appendix A) | output tail (≤3 lines, verbatim) | verdict | owner | smallest repair packet |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R0.1 | Predecessor ancestry | commission §1 | `git merge-base --is-ancestor` ×3 | `0b1fe887 rc=0`<br>`79b566f5 rc=0`<br>`192a46de rc=0` | PASS | — | — |
| R0.2 | Agent OS acceptance trace | commission §1 | `git grep` agentos D2C/D2D accept | at PIN1 no line cited both (HOLD); satisfied by #8543 merge 527243be5c03c79c016d8731179307f6ff03bf1d (2026-10-06T11:54:25Z): WS-GMI-THEME-GRAPH.md:82 D2C MERGED 0b1fe88730547207475ad3c04118d2e771a9b949; :82 D2D MERGED 79b566f5c0ccba878ab963084a239993d3116aa9 | PASS | — | — |
| R0.3 | No overlapping D2E carrier | commission §2 | `gh pr list --search D2E` | Open hit #8324 blueprint only (not D2E acceptance) | PASS | — | — |
| R0.4 | Owner-action authority #8507 | commission §2 | `gh pr view 8507`; `git grep OWNER_ACTION…` | `state=MERGED`; mergeCommit=`cbfa20a45d8401f1cf1cc9fc48155455f1d612fb`; grep≥1 | PASS | — | — |
| R1.A | D2A identity resolution | D2A | `pytest` identity_resolution + identity | `3 failed, 118 passed in 5.09s`<br>`tests/test_theme_graph_identity_resolution.py::test_the_committed_graph_carries_exactly_2806_company_nodes`<br>`E       assert 2807 == 2806`<br>`tests/test_theme_graph_identity_resolution.py::test_every_company_node_gets_a_row`<br>`E       assert 2807 == 2806`<br>`tests/test_theme_graph_identity_resolution.py::test_r1_section_6_1_the_four_sidecar_assertions_against_the_committed_parquet`<br>`E       AssertionError: assert 'co:us:VMRK' not in {...}` | FAIL | seat (PR #8544) | PR #8544 (branch claude/gmi-vmrk-duplicate-mint-20261006; seat-accepted frozen P-R1A: merge rename re-mint co:us:VMRK into co:us:EQR + D2A re-pin under DEC-THEME-GRAPH-RENAME-REMINT-MERGES-INTO-INCUMBENT-NODE) — seat merges #8544, then ONE #8540 re-measure round at PIN3 = origin/main after #8544 re-runs R1.A, R3.2, R1.B–F, R2, C1–C7 |
| R1.A-CI | D2A data lane (INFO) | informational | `data-health.yml` run list | run `37407802317` (`event=workflow_run`, `headSha=2d3ab1e087a07d63b6dcf8c4682c7541c5386b73`, `conclusion=failure`) failing on `unrun-intl-libraries` D2A step | INFO | — | clears with R1.A |
| R1.B | D2B lifecycle hostile matrix | D2B | `pytest` test_theme_graph_lifecycle.py | `26 passed in 2.43s` | PASS | — | — |
| R1.C | D2C PIT vintage | D2C #8432 | `pytest` basket PIT + membership + gmi_history | `143 passed, 14 warnings in 2.98s` | PASS | — | — |
| R1.D | D2D ontology/probation | D2D #8435 | `pytest` crosswalk + local_plane + structural + exposure | `575 passed, 1 skipped in 10.40s`; skips: 1 (reasons in Appendix A); the 1 skip was a lane-checkout hydration artifact (CN panel tracked in git) — re-measured with the panel hydrated at PIN2 in r2c, see §6 R1.D | PASS | — | — |
| R1.E | Materialize + contracts | store contract | `pytest` materialize + contracts | `132 passed in 6.65s` | PASS | — | — |
| R1.F | Rights tests (theme graph) | rights gate | `pytest` rights_use + theme_sources | `30 passed in 0.72s` | PASS | — | — |
| R1.X | MarketOntology half-B rights docket | F00C ledger (non-gating) | `pytest` half_b docket | `3 failed, 16 passed in 0.53s`<br>`tests/test_market_ontology_half_b_rights_docket.py::test_blocked_on_quotes_the_ledger_verbatim`<br>`E           AssertionError: MO-PAID-019: 'one issuer page joining >=2 module streams...' not in '...unified capital-markets tape journey...'` | FAIL-INFO | MarketOntology CEO A (F00C closure-ledger writer; ledger last changed by #8425/#8465/#8496) | reconcile `tests/test_market_ontology_half_b_rights_docket.py` (EXPECTED_DISPOSITION_CENSUS, docket rows) with the F00C closure ledger CSV as amended by records waves #8425/#8465/#8496, or restore those ledger rows; re-run `TZ=UTC PY -m pytest -q tests/test_market_ontology_half_b_rights_docket.py` |
| R2 | Strict contract guard | CI guard | `PY -m scripts.check_theme_graph_contracts --selftest`; `--strict` | `selftest rc=0`<br>`strict rc=0`<br>(no `breach` lines in strict tail) | PASS | — | — |
| C1 | Lifecycle standing | D2B3 §3 | pandas `node_lifecycle.parquet` | GOLD retired 2025-12-02 identity_break; IBIT retired entity_type_conflict | PASS | — | — |
| C2 | GOLD edge closure | D2B3 §4 | pandas GOLD `MEMBER_OF` beliefs | latest `valid_to=2025-12-02`; 2 beliefs; current gold_miners excludes GOLD | PASS | — | — |
| C3 | IBIT refusal fence | D2B3 §6 | pandas IBIT + `_meta` refusals | annulled MEMBER_OF; IBIT refusal present; live `co:us:IBIT` MEMBER_OF=0 | PASS | — | — |
| C4 | Retired-consistency | D2B3 §12 | retired vs live MEMBER_OF | `violations: 0 (7798 live MEMBER_OF edges, 2 retired nodes, 0 offenders)` | PASS | — | — |
| C5 | Identity sidecar R-A2 | D2B3 §13 | `identity_resolution.parquet` NEWEST gen | US 1237: RESOLVED 1211, NOT_IN_MASTER 25, DEFERRED 1 (`co:us:B`), ENTITY_TYPE_CONFLICT 0; RESOLVED share 0.978981; all-scope NEWEST 2805 = `_meta.identity_resolution_state_counts` sum | PASS | — | — |
| C6 | Generation provenance P1 | receipt timing | `merge-base` vs DATA_COMMIT | `0b1fe887 rc=1`; `79b566f5 rc=1`; seat fact: gen predates D2C/D2D merges; cured: GEN2 natural receipt (§6.D N1–N5) and re-measured at PIN3 — see §6.A C6 | HOLD | seat | natural receipt on a main containing D2C+D2D pending — Phase 2 |
| C7 | Nightly `_meta` history | informational | `git log -5` `_meta.json` | 5/5: `node_lifecycle>=2` and IBIT refusal | PASS | — | — |
| R3.1 | Registry table | rights gate #2 | `config/theme_sources.yml` | `finviz_themes`/`ths_concepts` `internal_only`; all families have `rights_class` | PASS | — | — |
| R3.2 | Source-ref census | display tier | `family_for_source_ref` on `evidence.source_ref` | 22 rows / 17 distinct; `ths_concepts` 12; `mastermind_curated` 6; `finviz_themes` 2; `None` 2 (`gmi:entity_type_conflict:co:us:IBIT`; `config/theme_graph_identity_breaks.yml#us:GOLD`) | FAIL | seat (PR #8544) | PR #8544 (seat-accepted frozen P-R3.2: rights registry entries for the correction source_refs; orchestrator gate 4 on #8544 = 23 evidence rows / 18 refs / None 0) — re-measured in the same PIN3 round |
| R3.3 | Spot checks | #8499 | two `family_for_source_ref` calls | probation `#x` → `mastermind_curated`; `site/factordata/us_standouts.json` → `None` (intentional; `rights.py` 70–72) | PASS | — | — |
| V1 | Node prefix census | coverage | `nodes.parquet` | total=3882; co:us=1239, co:cn=1021, ltheme=644, basket=358, … | PASS | — | — |
| V2 | Capability generations | coverage | `store.read_capability()` vs newest gen | `read_capability=644`; newest gen 643; +1 carried `ltheme:ths:309263` semantic_only @ 2026-08-22T04:50:43Z; node present in `nodes.parquet` | PASS | — | — |
| V3 | Identity generations | coverage | sidecar NEWEST vs `_meta` | NEWEST rows=2805 (state sum 2805); `_meta.counts.identity_resolution`=2807 = latest-per-node 2807 = 2805 newest + 2 carried (`co:us:GOLD`, `co:us:IBIT`); file 154270 rows / 55 generations; `_meta.rows_appended.identity_resolution`=2805 | PASS | — | — |
| V4 | THS mapping arithmetic | coverage | `_meta` crosswalk + local_plane | concepts=375; mapped 61 + unknown 0; unmapped_concept_count=314 | PASS | — | — |
| V5 | Probation proposals | coverage | `proposals.jsonl` status | lines=236; proposed=234, rejected=2 (as-of GEN) | PASS | — | — |
| V6 | PIT vintage + edge era | coverage | `_meta.per_suite` + edges era | suite vintages recorded; edges observed=12423 reconstruction=12677 (reconstruction NOT observed proof) | PASS | — | — |
| V7 | Refusal/negative categories | coverage | `_meta` negative buckets | company_mint_refusals=1; NOT_IN_MASTER=195; UNSUPPORTED_MARKET=233; finviz refused=0 | PASS | — | — |

## §3 D2B3 clause detail (measured on committed generation)

**C1 — node_lifecycle (2 rows, as-of `2026-10-06T08:07:45Z`):**

| node_id | status | retire_date | reason |
| --- | --- | --- | --- |
| co:us:GOLD | retired | 2025-12-02 | identity_break |
| co:us:IBIT | retired | 2026-08-22 | entity_type_conflict |

**C2 — GOLD:** two belief rows on `member_of:co:us:GOLD->basket:baskets:gold_miners@2023-05-09`; latest `valid_to=2025-12-02`. Current gold_miners MEMBER_OF view (null `valid_to`): 12 members, excludes `co:us:GOLD`. `co:us:GOLD#*` nodes: 0. B↔GOLD edges (any type): 0.

**C3 — IBIT:** latest MEMBER_OF belief annulled (`valid_to=valid_from=2023-05-09`). `_meta.company_mint_refusals`: IBIT / etf_conflict / etf:IBIT. `etf:IBIT` present; two live TRACKS edges; live `co:us:IBIT` MEMBER_OF count 0.

**C4 — retired-consistency:** violations: 0 (7798 live MEMBER_OF edges, 2 retired nodes, 0 offenders).

**C5 — identity sidecar (NEWEST `computed_at=2026-10-06T08:07:42Z`, R-A7 population):** US-scope (`market_scope==us`) denominator 1237 — RESOLVED 1211, NOT_IN_MASTER 25, DEFERRED_IDENTITY_EXCEPTION 1 (`co:us:B`), ENTITY_TYPE_CONFLICT 0; RESOLVED share 0.978981 (threshold 0.97896). All-scope NEWEST sum=2805 matches `_meta.identity_resolution_state_counts` (`DEFERRED_IDENTITY_EXCEPTION` 1, `NOT_IN_MASTER` 195, `RESOLVED` 2376, `UNSUPPORTED_MARKET` 233). Latest-row-per-node view 2807 carries two fossils not in the newest generation: `co:us:GOLD` (2026-08-21T11:48:22Z, DEFERRED_IDENTITY_EXCEPTION) and `co:us:IBIT` (2026-08-22T04:50:43Z, ENTITY_TYPE_CONFLICT). vs the R-A2 frozen expectation 1,236 = 1,210/25/1/0 the newest generation carries +1 RESOLVED, which is `co:us:VMRK` (see R1.A).

**C6 — SEAT-PROVIDED:** generation `2026-10-06T08:07:45Z` at data commit `f7dd82910f31` pushed by `daily.yml` run `37402815092` (engine job failed after push); predates D2C/D2D squash merges on 2026-10-06. DATA_COMMIT is not a descendant of squash commits `0b1fe887` / `79b566f5` (`merge-base --is-ancestor` rc=1 for both).

**C5 vs round r1b:** round r1b reported 1239 / 2807 from the latest-row-per-node view (`store.read_identity_resolution(latest=True)`); that view carries the fossils `co:us:GOLD` and `co:us:IBIT` that R-A2 excludes from natural generations. The frozen R-A7 population (newest `computed_at` generation) is 1237 / 2805, which is what round r1 reported; r1d restores it.

## §4 Rights tables

**R3.1 families (`config/theme_sources.yml`, updated 2026-10-06):**

| family | rights_class |
| --- | --- |
| mastermind_curated | direct_display_ok |
| finviz_themes | internal_only |
| ths_concepts | internal_only |

**R3.2 evidence `source_ref` census (`family_for_source_ref`, denominators = 22 rows / 17 distinct refs):**

| family | distinct refs | row hits |
| --- | --- | --- |
| ths_concepts | 7 | 12 |
| mastermind_curated | 6 | 6 |
| finviz_themes | 2 | 2 |
| None (unmapped) | 2 | 2 |

None refs (verbatim): `gmi:entity_type_conflict:co:us:IBIT` (`evidence_id=ev:4d8651dc865b1205`); `config/theme_graph_identity_breaks.yml#us:GOLD` (`evidence_id=ev:59473e36961c6654`).

**SEARCH BOUNDS (excluded columns):** `nodes.provenance`, `nodes.source_meta`, `edges.source_class`, `edges.date_provenance` — (i) enum/id/metadata, not source references; `edges.evidence_refs` — (ii) `ev:*` ids resolving to `evidence.parquet` (e.g. `ev:7e043e2a120a8689`); `identity_resolution.source_native_symbol`, `identity_resolution.source_receipts` — (i); `probation/*.jsonl` — (iii) proposals not production evidence (`rights.py` 64–68).

**R3.3 spot checks:** `data/theme_graph/probation/relation_events.v2.jsonl#x` → `mastermind_curated`; `site/factordata/us_standouts.json` → `None`.

```text
#: * ``site/factordata/us_standouts.json`` is intentionally absent. Coverage-gap
#:   tooling may record it as selection-population provenance, but it is not a GMI
#:   graph-evidence source family and therefore must remain fail-closed at use gates.
```

## §5 Coverage census tables (as-of `2026-10-06T08:07:45Z`)

**V1 nodes (denominator 3882):** co:us 1239, co:cn 1021, ltheme 644, basket 358, co:ca 167, co:intl 233, co:hk 147, etf 55, theme 18.

**V2 capability:** 34061 rows / 53 generations in file; NEWEST generation rows 643 = measurement_candidate 505 + semantic_only 138. `len(store.read_capability())` = 644 = 643 newest + 1 carried `ltheme:ths:309263` (`semantic_only`, `computed_at` 2026-08-22T04:50:43Z).

**V3 identity:** NEWEST generation rows 2805 (state sum 2805); `_meta.counts.identity_resolution` 2807 = 2805 newest + 2 carried nodes; parquet file 154270 rows over 55 generations; `_meta.rows_appended.identity_resolution` 2805.

**V4 mapping:** `local_plane.ths.concepts` 375; crosswalk `ths_codes_mapped` 61 + `ths_codes_unknown` 0 = 61; `ths_unmapped_concept_count` 314; `unknown_ths_codes` []; `local_plane.ths.unresolved_concept_names` 0.

**V5 probation:** `proposals.jsonl` field `status` — total 236 lines: proposed 234, rejected 2.

**V6 PIT / era:** `_meta.per_suite.*.membership_published_at` and seed constants recorded per suite (see `_meta.json`). `edges.parquet` era: observed 12423, reconstruction 12677 (reconstruction-era rows are not observed proof).

**V7 negatives:** `company_mint_refusals` 1; `local_plane.finviz.company_resolution.refused` 0; `dropped_adjacent_duplicates` 1 date; suite `skipped_unidentifiable` all empty lists; sidecar NOT_IN_MASTER 195; UNSUPPORTED_MARKET 233.

## §6 PIN3 COMPOSITION (PIN3 `ebe35dc916de5aae556371a5aa963c6692175c9c`; store = GEN2 natural generation `2026-10-06T13:27:04Z` + #8544 ratified correction rows; PHASE-2 PENDING:GEN3)

### §6.A PIN3 gate matrix

| id | gate | clause / source | command | output tail | verdict | owner | smallest repair packet |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R0.1 | Predecessor ancestry | commission §1 | `git merge-base --is-ancestor` ×5 | PIN3: 0b1fe88730547207475ad3c04118d2e771a9b949 rc=0; 79b566f5c0ccba878ab963084a239993d3116aa9 rc=0; 192a46de rc=0; 527243be5c03c79c016d8731179307f6ff03bf1d rc=0; ebe35dc916de5aae556371a5aa963c6692175c9c rc=0 | PASS | — | — |
| R0.2 | Agent OS acceptance trace | commission §1 | `git grep` WS + #8543 merge | PIN3: at PIN1 no line cited both (HOLD); satisfied by #8543 merge 527243be5c03c79c016d8731179307f6ff03bf1d (2026-10-06T11:54:25Z): WS-GMI-THEME-GRAPH.md:82 D2C MERGED 0b1fe88730547207475ad3c04118d2e771a9b949; :82 D2D MERGED 79b566f5c0ccba878ab963084a239993d3116aa9 | PASS | — | — |
| R0.3 | No overlapping D2E carrier | commission §2 | `gh pr list --search D2E` | PIN3: open #8540 (D2E acceptance carrier) + blueprint #8324 only | PASS | — | — |
| R0.4 | Owner-action authority #8507 | commission §2 | `gh pr view 8507`; grep | PIN3: state=MERGED mergeCommit=cbfa20a45d8401f1cf1cc9fc48155455f1d612fb; OWNER_ACTION grep matches=5 | PASS | — | — |
| R1.A | D2A identity resolution | D2A | `pytest` identity_resolution + identity | PIN3: 121 passed in 4.93s | PASS | — | — |
| R1.A-CI | D2A data lane (INFO) | informational | `data-health.yml` run list | PIN3: no data-health.yml run on a head containing PIN3 yet | INFO | — | — |
| R1.B | D2B lifecycle hostile matrix | D2B | `pytest` test_theme_graph_lifecycle.py | PIN3: 57 passed in 2.68s | PASS | — | — |
| R1.C | D2C PIT vintage | D2C #8432 | basket PIT pytest bundle | PIN3: 143 passed, 14 warnings in 2.98s | PASS | — | — |
| R1.D | D2D ontology/probation | D2D #8435 | crosswalk/local_plane/structural/exposure pytest | PIN3: 576 passed in 10.53s | PASS | — | — |
| R1.E | Materialize + contracts | store contract | materialize + contracts pytest | PIN3: 132 passed in 6.68s | PASS | — | — |
| R1.F | Rights tests (theme graph) | rights gate | rights_use + theme_sources pytest | PIN3: 31 passed in 0.74s | PASS | — | — |
| R1.X | MarketOntology half-B rights docket | F00C ledger (non-gating) | half_b_rights_docket pytest | PIN3: 3 failed, 16 passed in 0.56s | FAIL-INFO | MarketOntology CEO A | reconcile docket vs F00C closure ledger CSV |
| R2 | Strict contract guard | CI guard | `check_theme_graph_contracts` | PIN3: selftest rc=0; strict rc=0 | PASS | — | — |
| C1 | Lifecycle standing | D2B3 §3 | pandas `node_lifecycle` probe | PIN3: co:us:GOLD retired 2025-12-02 identity_break; co:us:IBIT retired 2026-08-22 entity_type_conflict; co:us:VMRK merged_into co:us:EQR | PASS | — | — |
| C2 | GOLD edge closure | D2B3 §4 | pandas GOLD MEMBER_OF | PIN3: GOLD belief_rows 2; open gold_miners 12 GOLD_in False | PASS | — | — |
| C3 | IBIT refusal fence | D2B3 §6 | pandas IBIT + `_meta` refusals | PIN3: IBIT MEMBER_OF annulled valid_from=valid_to=2023-05-09; IBIT refusal 1; live co:us:IBIT MEMBER_OF 0 | PASS | — | — |
| C4 | Retired-consistency | D2B3 §12 | retired-like/merged vs live MEMBER_OF | PIN3: violations: 0 (7797 live MEMBER_OF edges, 3 retired-like/merged nodes, 0 offenders) | PASS | — | — |
| C5 | Identity sidecar R-A2 | D2B3 §13 | NEWEST `identity_resolution` generation | PIN3: US 1237 RESOLVED=1211 NOT_IN_MASTER=25 DEFERRED=1 ENTITY_TYPE_CONFLICT=0; RESOLVED share 0.978981; NEWEST sum=2805 | PASS | — | — |
| C6 | Generation provenance at PIN3 | receipt timing | `git log` + merge-base vs GEN2/engine | PIN3: GEN2 natural generation f9ccad3e50f671499893f8113ba96ae2910ab5e7 (2026-10-06T13:27:04Z) + #8544 correction rows; D2C/D2D ancestry rc=0 vs engine 640e3e237eede62351b6f657c8e13ad20274585c; sole post-GEN2 data/theme_graph commit ebe35dc916de5aae556371a5aa963c6692175c9c (#8544) | PASS | — | — |
| C7 | Nightly `_meta` history | informational | `git log -5` `_meta.json` | PIN3: 5/5 _meta commits carry node_lifecycle>=2 and IBIT refusal | PASS | — | — |
| R3.1 | Registry table | rights gate #2 | `config/theme_sources.yml` | PIN3: finviz_themes/ths_concepts internal_only; all families rights_class set | PASS | — | — |
| R3.2 | Source-ref census | display tier | `family_for_source_ref` on evidence | PIN3: 23 rows / 18 distinct refs; ths_concepts 12; mastermind_curated 9; finviz_themes 2; None 0 | PASS | — | — |
| R3.3 | Spot checks | #8499 | two `family_for_source_ref` calls | PIN3: probation → mastermind_curated; site/factordata/us_standouts.json → None (intentional) | PASS | — | — |
| V1 | Node prefix census | coverage | `nodes.parquet` | PIN3: total=3882; co:us=1239; co:cn=1021; ltheme=644; basket=358 | PASS | — | — |
| V2 | Capability generations | coverage | `store.read_capability()` vs newest gen | PIN3: read_capability=644; file 34704 rows / 54 generations; newest gen 643 rows | PASS | — | — |
| V3 | Identity generations | coverage | sidecar NEWEST vs `_meta` | PIN3: NEWEST=2805; latest-per-node=2807; _meta.counts.identity_resolution=2807; file 157075 rows / 56 gens | PASS | — | — |
| V4 | THS mapping arithmetic | coverage | `_meta` crosswalk + local_plane | PIN3: ths concepts=375; mapped 61 + unknown 0; unmapped_concept_count=314 | PASS | — | — |
| V5 | Probation proposals | coverage | `proposals.jsonl` status | PIN3: proposals lines=236 proposed=234 rejected=2 | PASS | — | — |
| V6 | PIT vintage + edge era | coverage | `_meta.per_suite` + edges era | PIN3: edges observed=12424 reconstruction=12677 (reconstruction not observed proof) | PASS | — | — |
| V7 | Refusal/negative categories | coverage | `_meta` negative buckets | PIN3: company_mint_refusals=1; NOT_IN_MASTER=195; UNSUPPORTED_MARKET=233 | PASS | — | — |

### §6.B R1.A delta 2807→2806

Frozen D2A pin (`tests/test_theme_graph_identity_resolution.py:99-107`): physical company nodes in `nodes.parquet` must equal **2806** after excluding nodes whose **latest** `node_lifecycle` status is `merged` (canonical company set).

| measure | GEN2 (`f9ccad3e50f671499893f8113ba96ae2910ab5e7`) | PIN3 (`ebe35dc916de5aae556371a5aa963c6692175c9c`) |
| --- | --- | --- |
| physical `kind==company` | 2807 | 2807 |
| canonical (exclude latest `merged`) | 2807 | 2806 |

Symmetric difference on canonical sets: **left** `co:us:VMRK` (latest lifecycle `merged`, `merged_into=co:us:EQR`, `ratified_by=DEC:THEME-GRAPH-RENAME-REMINT-MERGES-INTO-INCUMBENT-NODE`); **entered** ∅. `co:us:EQR` remains a live company node.

### §6.C PHASE-2 status

PENDING:GEN3 first natural daily.yml engine run whose checkout contains ebe35dc916de5aae556371a5aa963c6692175c9c (cron 22:30Z; seat GEN3 check ~2026-10-07T14:07Z)

GEN3 must show: N1–N7 and Q1–Q4 re-run on the GEN3 checkout (contains PIN3); natural generation preserves the #8544 correction (R1.A pass at canonical 2806; `co:us:VMRK` lifecycle merged into `co:us:EQR`; R3.2 `family_for_source_ref` None=0).

### §6.D PIN2/GEN2 measurement (r2–r2c) — historical, superseded for composition by §6.A

| id | gate | clause / source | command | output tail | verdict | owner | smallest repair packet |
| --- | --- | --- | --- | --- | --- | --- | --- |
| N1 | Natural run identity | D3(c) | `gh run view 37404125352` job `112118780036` | `event=schedule`; engine `name=engine` `status=completed` `conclusion=failure` | PASS | — | — |
| N2 | Effective code sha | D3(a) | job log grep checkout/pull | L111 `640e3e237eede62351b6f657c8e13ad20274585c`; L120 `Already up to date.` → EFFECTIVE_SHA same | PASS | — | — |
| N3 | Ancestry | D3(b) | `merge-base --is-ancestor` on CHECKOUT_SHA | `0b1fe887 rc=0`; `79b566f5 rc=0`; #8507 merged 11:28:40Z after job start 11:14:43Z — not required | PASS | — | — |
| N4 | Data-commit linkage | D3 timing | `git show f9ccad3…`; `merge-base CHECKOUT_SHA DATA_COMMIT` | `computed_at=2026-10-06T13:27:04Z`; job `11:14:43Z`–`14:42:06Z`; commit `13:40:52Z`; `rc=0` | PASS | — | — |
| N5 | Advisory guard in job | D3(d) | `grep -E '(::group::\|##\[group\])theme graph …'` on job log `112118780036` | L34798 `##[group]theme graph nightly materialization (build_theme_graph)  [8s, rc=0]`; L34814 `##[group]theme graph contract guard (check_theme_graph_contracts)  [3s, rc=0]`; guard body two `##[notice]` lines; `warning`/`error` count 0 | PASS | — | — |
| N6 | Strict guard (local) | D3(d) | `check_theme_graph_contracts --selftest/--strict` | `selftest rc=0`; `strict rc=0`; no breach/INDETERMINATE | PASS | — | — |
| N7 | R-A8 edge stability | D3(d) | edges probe P1_PIN vs HEAD | GOLD edge rows 2/2 identical latest belief; IBIT crypto_rails 2/2 identical; totals 25100 / latest-belief 12863; `rows_appended.edges=0` both | PASS | — | — |
| Q1 | PIT meta | step 7 | `_meta.json` | `computed_at=2026-10-06T13:27:04Z` nightly observed; `store_eq_rc=0` | PASS | — | — |
| Q2 | Strict readers | step 7 | `RepositoryStore` reads | nodes=3882 lifecycle=2 edges=25100 proposals=236 | PASS | — | — |
| Q3 | Identity | step 7 | `resolve_graph_node_identity` | NVDA RESOLVED; B/GOLD DEFERRED_IDENTITY_EXCEPTION; IBIT ENTITY_TYPE_CONFLICT | PASS | — | — |
| Q4 | Neighborhoods | step 7 | `compose_neighborhood` a–e | (a) GOLD present; (b) absent; (c) present `future_beliefs_excluded=1`; (d) co:us:IBIT absent, etf:IBIT present; (e) co:us:IBIT absent; all `availability.state=OK` | PASS | — | — |
| R0.1 | Predecessor ancestry | P1 §1 | `merge-base --is-ancestor` ×3 @ PIN2 | all `rc=0` | PASS | — | — |
| R0.2 | Agent OS trace | P1 §1 | `git grep` D2C/D2D merged | `WS-GMI-THEME-GRAPH.md:58` D2C MERGED `0b1fe887`; `:70` D2D MERGED `79b566f5` | PASS | — | — |
| R0.3 | No overlapping carrier | P1 §2 | `gh pr list --search D2E` | #8540 + blueprint #8324 only | PASS | — | — |
| R0.4 | #8507 authority | P1 §2 | `gh pr view 8507`; grep | MERGED `cbfa20a45d84`; grep≥1 | PASS | — | — |
| R1.A | D2A | D2A | `pytest` identity_resolution + identity | `3 failed, 118 passed in 5.21s` (2807 company nodes; `co:us:VMRK`) | FAIL | seat (PR #8544) | PR #8544 (branch claude/gmi-vmrk-duplicate-mint-20261006; seat-accepted frozen P-R1A: merge rename re-mint co:us:VMRK into co:us:EQR + D2A re-pin under DEC-THEME-GRAPH-RENAME-REMINT-MERGES-INTO-INCUMBENT-NODE) — seat merges #8544, then ONE #8540 re-measure round at PIN3 = origin/main after #8544 re-runs R1.A, R3.2, R1.B–F, R2, C1–C7 |
| R1.A-CI | D2A data lane (INFO) | informational | `data-health.yml` run list | run `37407802317` failure on `unrun-intl-libraries` D2A step (seat evidence) | INFO | — | clears with R1.A |
| R1.B | D2B lifecycle | D2B | `pytest test_theme_graph_lifecycle.py` | `26 passed in 2.49s` | PASS | — | — |
| R1.C | D2C PIT | D2C | basket PIT pytest bundle | `143 passed, 14 warnings in 3.01s` | PASS | — | — |
| R1.D | D2D ontology | D2D | crosswalk/local_plane/structural/exposure | `576 passed in 10.14s` | PASS | — | — |
| R1.E | Materialize/contracts | store | materialize + contracts pytest | `132 passed in 6.87s` | PASS | — | — |
| R1.F | Rights | rights | rights_use + theme_sources | `30 passed in 0.70s` | PASS | — | — |
| R1.X | MO half-B docket | non-gating | half_b_rights_docket pytest | `3 failed, 16 passed in 0.49s` | FAIL-INFO | MarketOntology CEO A | reconcile docket vs F00C closure ledger CSV |
| R2 | Strict guard | CI guard | `--selftest` / `--strict` | both `rc=0` | PASS | — | — |
| C1–C5 | D2B3 clauses | frozen contract | pandas probes @ GEN2 | unchanged PASS vs P1 on natural generation | PASS | — | — |
| C6 | Generation provenance | Phase 2 | N1–N5 composite | N1–N5 all PASS (N5 after corrected probe) | PASS | — | — |
| C7 | `_meta` history | informational | `git log -5` `_meta.json` | 5/5 `node_lifecycle=2` + IBIT refusal | PASS | — | — |
| R3.1 | Registry | rights | `theme_sources.yml` | finviz/ths `internal_only`; all families have `rights_class` | PASS | — | — |
| R3.2 | Source-ref census | display tier | `family_for_source_ref` on evidence | 22 rows / 17 refs; 2 `None` without recorded fail-closed grep hit | FAIL | seat (PR #8544) | PR #8544 (seat-accepted frozen P-R3.2: rights registry entries for the correction source_refs; orchestrator gate 4 on #8544 = 23 evidence rows / 18 refs / None 0) — re-measured in the same PIN3 round |
| R3.3 | Spot checks | #8499 | two spot calls + `rights.py` 70–72 | probation → `mastermind_curated`; us_standouts → `None` intentional | PASS | — | — |
| V1–V7 | Coverage census | steps 4–5 | probes @ GEN2 | reconcile PASS (V2 capability 644 / 34704 file rows / 54 generations; V3 2805/2807 / 157075 file rows / 56 generations) | PASS | — | — |

**Ancestry (Phase 2):** `CHECKOUT_SHA` = `640e3e237eede62351b6f657c8e13ad20274585c` (job log line 111, verbatim after `git log -1 --format=%H`). `EFFECTIVE_SHA` = same (line 120 `Already up to date.` — pull only fast-forwards). `git merge-base --is-ancestor 0b1fe887 640e3e237eede62351b6f657c8e13ad20274585c` → `rc=0`; `79b566f5` → `rc=0`. Natural trigger `event=schedule` on run `37404125352`.

## §7 W3B release handoff — DRAFT, NOT RELEASED

Target operation: `gmi-theme-state-w3b-20260827-sol-001`. Release condition: the seat records **PHASE-2 PASS at GEN3** in Agent OS (until then W3B stays held; do not implement W3B in this carrier).

Pinned inputs: PIN3 `ebe35dc916de5aae556371a5aa963c6692175c9c`; store composition GEN2 natural generation `2026-10-06T13:27:04Z` + #8544 correction rows; this record (`research/theme_graph/D2E_ACCEPTANCE_2026-10-06.md`).

Constraints W3B inherits: identity canonical company count **2806**, `co:us:VMRK` merged into `co:us:EQR` per #8544 DEC (R1.A / §6.B); PIT readers (Q1–Q4); probation/ontology (R1.C / R1.D); rights — `finviz_themes` and `ths_concepts` internal-only, never public display (R3.x / §4; R3.2 None=0); coverage §5 negative/unmapped/refusal categories preserved; non-gating R1.X routed to MarketOntology CEO A.

## Appendix A — commands and probe (output tail ≤25 lines each)

**S0 PIN / code equality**

```
$ git rev-parse HEAD
58640b01db0d501a7c704f77314d169dd135140e
$ git merge-base --is-ancestor cbfa20a45d8401f1cf1cc9fc48155455f1d612fb HEAD; echo rc=$?
rc=0
$ git diff --quiet cbfa20a45d8401f1cf1cc9fc48155455f1d612fb HEAD -- engine scripts tests config contracts data; echo code_eq_rc=$?
code_eq_rc=0
```

**S0 materialize store + security master**

```
$ git sparse-checkout add '/data/theme_graph/' '/data/reference/'
$ ls -la data/reference/security_master.parquet
-rw-rw-r-- ... 79371 ... data/reference/security_master.parquet
$ git ls-files data/theme_graph | wc -l
8
$ git status --porcelain -- data/
(empty)
```

**S0 GEN / DATA_COMMIT**

```
$ PY=/home/longr/lanes/tmp/d2e-venv/bin/python
$ PY -c "import json; ..."
2026-10-06T08:07:45Z nightly nightly observed 2026-10-06
$ git log -1 --format='%H %cI %s' HEAD -- data/theme_graph/_meta.json
f7dd82910f315e82f376144388f2b38490c94ffe 2026-10-06T02:23:18-07:00 engine: regime update 2026-10-06
```

**R0.1**

```
$ for c in 0b1fe887 79b566f5 192a46de; do git merge-base --is-ancestor $c HEAD; echo "$c rc=$?"; done
0b1fe887 rc=0
79b566f5 rc=0
192a46de rc=0
```

**R0.3 (gh call 1/3)**

```
$ gh pr list -R mastermindx-market-intelligence/macro --state open --search "D2E" --json number,title,headRefName --limit 20
[{"headRefName":"research/gmi-theme-subtheme-completion-blueprint-20261003","number":8324,"title":"research(gmi): audited v3 report, full master plan and Astra CEO handoff"}]
```

**R0.4 (gh call 2/3)**

```
$ gh pr view 8507 -R mastermindx-market-intelligence/macro --json state,isDraft,headRefOid,mergeCommit
{"headRefOid":"6d01445b12c13300e96fe98395cf7162c1b92a7e","isDraft":false,"mergeCommit":{"oid":"cbfa20a45d8401f1cf1cc9fc48155455f1d612fb"},"state":"MERGED"}
$ git grep -c OWNER_ACTION_AUTHORITY_UNAVAILABLE HEAD -- engine scripts tests
engine/theme_graph/probation.py:2
tests/test_theme_graph_local_plane.py:1
tests/test_theme_graph_relation_action_resolver.py:2
```

**R1.A — `PY=/home/longr/lanes/tmp/d2e-venv/bin/python` (round r1d)**

```
$ TZ=UTC COLLECT_LANE=nightly PY -m pytest -p no:cacheprovider -q -rfEs tests/test_theme_graph_identity_resolution.py tests/test_theme_graph_identity.py
...
FAILED tests/test_theme_graph_identity_resolution.py::test_the_committed_graph_carries_exactly_2806_company_nodes
FAILED tests/test_theme_graph_identity_resolution.py::test_every_company_node_gets_a_row
FAILED tests/test_theme_graph_identity_resolution.py::test_r1_section_6_1_the_four_sidecar_assertions_against_the_committed_parquet
3 failed, 118 passed in 5.09s
```

Cause: committed `nodes.parquet` carries 2807 company nodes including `co:us:VMRK` (EQR→VMRK rename duplicate; both `co:us:EQR` and `co:us:VMRK` RESOLVED → `SEC:US-XNYS-EQR`; first `co:us:VMRK` sidecar row `2026-09-04T11:52:38Z` per P-R1A); D2A pins 2806 and §6.1 assertion 3 forbids a `co:us:VMRK` node.

**R1.B**

```
$ TZ=UTC COLLECT_LANE=nightly PY -m pytest -p no:cacheprovider -q -rfEs tests/test_theme_graph_lifecycle.py
...
26 passed in 2.43s
```

**R1.C**

```
$ TZ=UTC COLLECT_LANE=nightly PY -m pytest -p no:cacheprovider -q -rfEs tests/test_basket_membership_pit.py tests/test_us_basket_membership_pit.py tests/test_theme_graph_membership_lifecycle.py tests/test_gmi_history_integrity.py
143 passed, 14 warnings in 2.98s
```

**R1.D**

```
$ unset GMI_STATE_OWNER_WORKSPACE
$ TZ=UTC COLLECT_LANE=nightly PY -m pytest -p no:cacheprovider -q -rfEs tests/test_theme_graph_crosswalk.py tests/test_theme_graph_local_plane.py tests/test_theme_graph_structural_owner_binding.py tests/test_market_ontology_exposure_map.py
575 passed, 1 skipped in 10.40s
```

**R1.D skips (count 1):**

```
      1 tests/test_theme_graph_local_plane.py:400: CN panel not materialised in this checkout
```

**R1.E**

```
$ TZ=UTC COLLECT_LANE=nightly PY -m pytest -p no:cacheprovider -q -rfEs tests/test_theme_graph_materialize.py tests/test_theme_graph_contracts.py
132 passed in 6.65s
```

**R1.F**

```
$ TZ=UTC COLLECT_LANE=nightly PY -m pytest -p no:cacheprovider -q -rfEs tests/test_theme_graph_rights_use.py tests/test_theme_sources_registry.py
30 passed in 0.72s
```

**R1.X**

```
$ TZ=UTC COLLECT_LANE=nightly PY -m pytest -p no:cacheprovider -q -rfEs tests/test_market_ontology_half_b_rights_docket.py
3 failed, 16 passed in 0.53s
$ git log --format='%h %cI %s' -3 HEAD -- research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv
543e651345 2026-10-05T17:05:42-07:00 records(marketontology): CEO A wave 14 — F13-WS natural run on 007, #820 on 054, #807 on 003 (D93–D94) (#8496)
c35996123e 2026-10-04T22:05:29-07:00 records(marketontology): CEO A wave 13 — W12 landed, FIXBIND-01 merged + proven (D90), #8434 facts + 027 note (D91), 007/003 evidence (D92) (#8465)
6dbfad8766 2026-10-04T03:10:45-07:00 records(marketontology): CEO A wave 12 — W11 landed, MO-DELTA-007 installed (D85), CEO B row evidence (D86), F12 056/038 → BUILT_NOT_PROVEN (D87), 055/084 → BUILT_NOT_PROVEN + 052 → PARTIAL (D88) (#8425)
```

**R2**

```
$ TZ=UTC PY -m scripts.check_theme_graph_contracts --selftest
check_theme_graph_contracts selftest: OK
$ echo rc=$?
rc=0
$ TZ=UTC PY -m scripts.check_theme_graph_contracts --strict
::notice title=theme graph — licensing snapshots — designed::3 evidence row(s) carry mint-time licensing...
::notice title=theme graph — identity resolution census::company nodes=2807, projection rows=2807, by state={...}
$ echo rc=$?
rc=0
```

Round r1 recorded `strict rc=0` alongside a breach line in a tree without `data/reference/security_master.parquet`; that exit status was not the guard’s own `--strict` result on a materialized tree and is superseded.

**D2B3 probe heredoc (verbatim)**

```
PY=/home/longr/lanes/tmp/d2e-venv/bin/python
PYTHONPATH=. PY <<'PYEOF'
import json
import pandas as pd
from pathlib import Path
from collections import Counter
from engine.theme_graph import store

BASE = Path("data/theme_graph")
meta = json.loads((BASE / "_meta.json").read_text())

lc = store.read_node_lifecycle(latest=True)
print("C1 node_lifecycle (latest):")
for _, r in lc.sort_values("node_id").iterrows():
    print(f"  {r['node_id']}: status={r['status']} retire_date={r.get('retire_date')} reason={r.get('reason')}")

edges = store.read_edges(latest_belief=True)
hist = store.read_edges(latest_belief=False)
gold_id = "member_of:co:us:GOLD->basket:baskets:gold_miners@2023-05-09"
gold_hist = hist[hist["edge_id"] == gold_id] if not hist.empty else pd.DataFrame()
print("C2 GOLD belief_rows", len(gold_hist))
gm = edges[(edges["type"]=="MEMBER_OF") & (edges["dst"].astype(str).str.contains("gold_miners"))]
open_gm = gm[gm["valid_to"].map(lambda x: pd.isna(x))]
gold_in = "co:us:GOLD" in set(open_gm["src"].astype(str))
print("  open gold_miners MEMBER_OF", len(open_gm), "GOLD_in", gold_in)

mo_hist = hist[(hist["src"]=="co:us:IBIT") & (hist["type"]=="MEMBER_OF")]
print("C3 co:us:IBIT MEMBER_OF edges:")
for eid in sorted(mo_hist["edge_id"].unique()):
    rows = mo_hist[mo_hist["edge_id"]==eid].sort_values(["belief_time","computed_at"], kind="stable")
    latest = rows.iloc[-1]
    print(f"  {eid} belief_rows={len(rows)} latest valid_from={latest['valid_from']} valid_to={latest['valid_to']}")
refusals = meta.get("company_mint_refusals", [])
print("  IBIT refusals", len([x for x in refusals if "IBIT" in json.dumps(x)]))
live_ibit_mo = edges[(edges["src"]=="co:us:IBIT") & (edges["type"]=="MEMBER_OF") & edges["valid_to"].map(pd.isna)]
print("  live co:us:IBIT MEMBER_OF", len(live_ibit_mo))

lc_latest = store.read_node_lifecycle(latest=True)
retired = set(lc_latest.loc[lc_latest["status"]=="retired","node_id"].astype(str))
ordered = hist.sort_values(["edge_id","belief_time","computed_at"], kind="stable")
current_edges = ordered.drop_duplicates(subset=["edge_id"], keep="last")
live_mo = current_edges[(current_edges["type"]=="MEMBER_OF") & current_edges["valid_to"].map(pd.isna)]
offenders = sorted(set(live_mo["src"].astype(str)) & retired)
print("violations:", len(offenders), f"({len(live_mo)} live MEMBER_OF edges, {len(retired)} retired nodes, {len(offenders)} offenders)")

idres = store.read_identity_resolution(latest=True)
us = idres[idres["market_scope"].astype(str)=="us"]
counts = Counter(us["resolution_state"].astype(str))
print("US resolution_state counts:", dict(counts), "denom=", len(us))
all_scope = Counter(idres["resolution_state"].astype(str))
print("all-scope NEWEST sum=", sum(all_scope.values()))
print("_meta:", meta.get("identity_resolution_state_counts"))
PYEOF
```

Probe tail:

```
C1 node_lifecycle (latest):
  co:us:GOLD: status=retired retire_date=2025-12-02 reason=identity_break
  co:us:IBIT: status=retired retire_date=2026-08-22 reason=entity_type_conflict
C2 GOLD belief_rows 2
  open gold_miners MEMBER_OF 12 GOLD_in False
C3 co:us:IBIT MEMBER_OF edges:
  member_of:co:us:IBIT->basket:baskets:crypto_rails@2023-05-09 belief_rows=2 latest valid_from=2023-05-09 valid_to=2023-05-09
  IBIT refusals 1
  live co:us:IBIT MEMBER_OF 0
violations: 0 (7798 live MEMBER_OF edges, 2 retired nodes, 0 offenders)
US resolution_state counts: {'RESOLVED': 1211, 'NOT_IN_MASTER': 25, 'DEFERRED_IDENTITY_EXCEPTION': 2, 'ENTITY_TYPE_CONFLICT': 1} denom= 1239
all-scope NEWEST sum= 2807
_meta: {'DEFERRED_IDENTITY_EXCEPTION': 1, 'NOT_IN_MASTER': 195, 'RESOLVED': 2376, 'UNSUPPORTED_MARKET': 233}
```

**R3.1**

```
$ PY -c "import yaml; ..."
updated 2026-10-06
mastermind_curated direct_display_ok None
finviz_themes internal_only None
ths_concepts internal_only None
```

**Verify after write**

```
$ PY -m json.tool research/theme_graph/d2e_acceptance_2026-10-06.json >/dev/null && echo JSON_OK
JSON_OK
```

**Round r1d setup**

```
$ git rev-parse HEAD
7671cce0227a649361f7740d1c138cac6603c3d9
$ git merge-base --is-ancestor cbfa20a45d8401f1cf1cc9fc48155455f1d612fb HEAD; echo rc=$?
rc=0
$ git diff --quiet cbfa20a45d8401f1cf1cc9fc48155455f1d612fb HEAD -- engine scripts tests config contracts data; echo code_eq_rc=$?
code_eq_rc=0
$ git sparse-checkout add '/data/theme_graph/' '/data/reference/'
$ ls -la data/reference/security_master.parquet data/theme_graph/identity_resolution.parquet data/theme_graph/_meta.json
-rw-rw-r-- ... data/reference/security_master.parquet
-rw-rw-r-- ... data/theme_graph/identity_resolution.parquet
-rw-rw-r-- ... data/theme_graph/_meta.json
$ git status --porcelain -- data/
(empty)
$ PY=/home/longr/lanes/tmp/d2e-venv/bin/python
```

**P-C5 (r1d)**

```
PY=/home/longr/lanes/tmp/d2e-venv/bin/python
$PY - <<'EOF'
import json
import pandas as pd
d = pd.read_parquet("data/theme_graph/identity_resolution.parquet")
print("file_rows", len(d), "generations", d["computed_at"].nunique())
mx = d["computed_at"].max()
nw = d[d["computed_at"] == mx]
print("NEWEST computed_at", mx, "rows", len(nw), "distinct_nodes", nw["node_id"].nunique())
print("all_scope_states", dict(sorted(nw["resolution_state"].value_counts().items())), "sum", len(nw))
us = nw[nw["market_scope"] == "us"]
vc = us["resolution_state"].value_counts()
print("us_total", len(us), "us_states", dict(sorted(vc.items())))
print("us_DEFERRED", sorted(us.loc[us["resolution_state"] == "DEFERRED_IDENTITY_EXCEPTION", "node_id"]))
print("us_ETC", sorted(us.loc[us["resolution_state"] == "ENTITY_TYPE_CONFLICT", "node_id"]))
print("RESOLVED_share", round(vc.get("RESOLVED", 0) / len(us), 6), "threshold 0.97896")
lp = d.sort_values("computed_at", kind="stable").drop_duplicates("node_id", keep="last")
carried = lp[~lp["node_id"].isin(set(nw["node_id"]))]
print("latest_per_node_rows", len(lp))
print("carried_not_in_newest", [(r.node_id, r.computed_at, r.resolution_state) for r in carried.itertuples()])
m = json.load(open("data/theme_graph/_meta.json"))
print("_meta.counts.identity_resolution", m["counts"].get("identity_resolution"))
print("_meta.rows_appended.identity_resolution", m.get("rows_appended", {}).get("identity_resolution"))
print("_meta.identity_resolution_state_counts", dict(sorted(m.get("identity_resolution_state_counts", {}).items())))
EOF
file_rows 154270 generations 55
NEWEST computed_at 2026-10-06T08:07:42Z rows 2805 distinct_nodes 2805
all_scope_states {'DEFERRED_IDENTITY_EXCEPTION': 1, 'NOT_IN_MASTER': 195, 'RESOLVED': 2376, 'UNSUPPORTED_MARKET': 233} sum 2805
us_total 1237 us_states {'DEFERRED_IDENTITY_EXCEPTION': 1, 'NOT_IN_MASTER': 25, 'RESOLVED': 1211}
us_DEFERRED ['co:us:B']
us_ETC []
RESOLVED_share 0.978981 threshold 0.97896
latest_per_node_rows 2807
carried_not_in_newest [('co:us:GOLD', '2026-08-21T11:48:22Z', 'DEFERRED_IDENTITY_EXCEPTION'), ('co:us:IBIT', '2026-08-22T04:50:43Z', 'ENTITY_TYPE_CONFLICT')]
_meta.counts.identity_resolution 2807
_meta.rows_appended.identity_resolution 2805
_meta.identity_resolution_state_counts {'DEFERRED_IDENTITY_EXCEPTION': 1, 'NOT_IN_MASTER': 195, 'RESOLVED': 2376, 'UNSUPPORTED_MARKET': 233}
```

**P-R1A (r1d)**

```
$PY - <<'EOF'
import pandas as pd
n = pd.read_parquet("data/theme_graph/nodes.parquet")
c = n[n["kind"].astype(str) == "company"]
print("company_nodes", len(c), "distinct", c["node_id"].nunique())
d = pd.read_parquet("data/theme_graph/identity_resolution.parquet")
nw = d[d["computed_at"] == d["computed_at"].max()]
for k in ["co:us:EQR", "co:us:VMRK"]:
    print(k, "in_nodes", k in set(c["node_id"].astype(str)), "first_seen", d.loc[d["node_id"] == k, "computed_at"].min())
    r = nw[nw["node_id"] == k]
    print("  newest", r[["resolution_state", "security_id", "issuer_id"]].to_dict("records"))
print("newest cells security_id == SEC:US-XNYS-VMRK:", int((nw["security_id"] == "SEC:US-XNYS-VMRK").sum()))
EOF
company_nodes 2807 distinct 2807
co:us:EQR in_nodes True first_seen 2026-08-19T11:03:21Z
  newest [{'resolution_state': 'RESOLVED', 'security_id': 'SEC:US-XNYS-EQR', 'issuer_id': 'ISS:US-XNYS-EQR'}]
co:us:VMRK in_nodes True first_seen 2026-09-04T11:52:38Z
  newest [{'resolution_state': 'RESOLVED', 'security_id': 'SEC:US-XNYS-EQR', 'issuer_id': 'ISS:US-XNYS-EQR'}]
newest cells security_id == SEC:US-XNYS-VMRK: 0
```

## Appendix C — PIN3 commands (output tail ≤25 lines each)

**PIN3 worktree:** `git worktree add --detach ../mo-ext-pin3m-8540 ebe35dc916de5aae556371a5aa963c6692175c9c`; hydrate tracked `data/theme_graph/*`, `data/reference/*`, `data/china_search/closes.parquet` from git bytes when sparse.

**R0.1:** `for c in D2C D2D 192a46de PR8543_MERGE PIN3; do git merge-base --is-ancestor $c HEAD; echo rc=$?; done` → all rc=0.

**R0.2:** `git grep -n -E 'D2C|D2D' agentos/workstreams/WS-GMI-THEME-GRAPH.md | grep 0b1fe887|79b566f5`; `git merge-base --is-ancestor 527243be… HEAD`; `git show 527243be… -- WS-GMI-THEME-GRAPH.md | grep '^\+.*0b1fe887|79b566f5'`.

**R1.A:** `TZ=UTC COLLECT_LANE=nightly PY=/home/longr/lanes/tmp/d2e-venv/bin/python -m pytest -p no:cacheprovider -q -rfEs tests/test_theme_graph_identity_resolution.py tests/test_theme_graph_identity.py` → `121 passed in 4.93s`.

**R1.B–F, R1.X, R2:** Appendix A command text @ PIN3 worktree; tails in §6.A.

**C1–C7, R3, V1–V7:** D2B3 probe heredoc (Appendix A) and rights/coverage probes @ PIN3; tails in §6.A.

**C6:** `git log -4 -- data/theme_graph/_meta.json`; `git log f9ccad3e..HEAD -- data/theme_graph`; `merge-base --is-ancestor D2C|D2D 640e3e237eed…` → D2C_rc=0 D2D_rc=0; sole post-GEN2 commit `ebe35dc916…` (#8544).

**R1.A-CI:** `gh run list --workflow data-health.yml --branch main -L 5` → no completed head containing PIN3 yet.

## Appendix B — Phase 2 commands (PIN2 merge + receipt + probes)

**T0(a)** `git fetch origin main` → `fetch_rc=0`; `git merge --no-edit origin/main` → `Merge made by the 'ort' strategy.`; `PIN2=e061209069a1bc05157d9078cd394e9ce1d96cc9`; `git diff --stat origin/main...HEAD` → two owned files only.

**T0(b)** `git sparse-checkout add data/theme_graph data/reference`; `security_master.parquet` present; `git ls-files data/theme_graph | wc -l` → 8; `git status --porcelain -- data/` → empty.

**T0(d)** GEN2 line: `2026-10-06T13:27:04Z nightly nightly observed 2026-10-06`; `store_eq_rc=0`.

**T1 N1 jq:** `{"event":"schedule","job":[{"name":"engine","status":"completed","conclusion":"failure"}]}`

**T1 N2:** log `wc -c` 2970107; checkout line 111 + pull line 120 as above.

**T1 N5 (corrected probe r2b):** `grep -n -E '(::group::|##\[group\])theme graph (nightly materialization|contract guard)'` → `34798:…nightly materialization (build_theme_graph)  [8s, rc=0]`; `34814:…contract guard (check_theme_graph_contracts)  [3s, rc=0]`; guard body verbatim: `##[notice]3 evidence row(s) carry mint-time licensing…historical snapshots, not breaches…`; `##[notice]company nodes=2807…`; `grep -c -E '::(warning|error)|##\[(warning|error)\]'` over guard body → `0`.

**T1 N6:** `selftest rc=0`; `strict rc=0`.

**T1 N7 / T2 / T3:** pytest and probe tails recorded in `/tmp/d2e_*.out` (R1.A `3 failed, 118 passed`; R1.B–F as §6 table).

*(Phase 1 Appendix A retained above for historical PIN `cbfa20a45d8401f1cf1cc9fc48155455f1d612fb`.)*

Phase 2 was measured in §6 (rounds r2/r2b/r2c) on the natural nightly generation GEN2.

