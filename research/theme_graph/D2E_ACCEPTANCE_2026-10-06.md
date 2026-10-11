# D2E — D2 acceptance record (WS:GMI-THEME-GRAPH)

operation: `gmi-theme-accept-d2e-20260827-sol-001`  
PIN (Phase 1): `cbfa20a45d8401f1cf1cc9fc48155455f1d612fb`  
PIN2 (Phase 2): `e061209069a1bc05157d9078cd394e9ce1d96cc9`  
PIN3 (PHASE-1 composition): `ebe35dc916de5aae556371a5aa963c6692175c9c` (PR #8544 squash) / #8543 merge: `527243be5c03c79c016d8731179307f6ff03bf1d`  
GEN (Phase 1): `2026-10-06T08:07:45Z` / DATA_COMMIT (P1): `f7dd82910f315e82f376144388f2b38490c94ffe`  
GEN2: `2026-10-06T13:27:04Z` nightly / observed / belief_time `2026-10-06`  
DATA_COMMIT (natural): `f9ccad3e50f671499893f8113ba96ae2910ab5e7`  
RUN_ID: `37404125352` / ENGINE_JOB_ID: `112118780036` / TRIGGER_COMPUTED_AT: `2026-10-06T13:27:04Z`  
lane host/model (pin3/pin3r/pin3s): Cursor bounded fabric builder (ubuntu1, composer-2.5) — META-CEO commission rounds pin3, pin3r, pin3s  
written-at UTC: `2026-10-06T18:30:06Z`  
repair round: `r1d` (Phase 1 harness); `r2` (Phase 2 natural receipt + PIT readers at PIN2); `r2b` (N5 probe + verdict composition); `r2c` (P3 review fixes); `pin3` (PIN3 re-measure); `pin3r` (numbered repair list after review); `pin3s` (R0.2 literal + Appendix C anchors + closed heredocs)

**Round r1b (repair) — harness corrections by orchestrator E:** D1 materializes `data/reference/security_master.parquet` so R1.B/R2 are not run against a degraded guard. D5 moves MarketOntology half-B docket tests to non-gating R1.X and limits R1.F to theme-graph rights tests. D6 censuses `evidence.source_ref` only via `family_for_source_ref`. D7 treats `site/factordata/us_standouts.json` as intentionally unmapped (PASS when `None`).

**D1 (r1d):** C5/V3 restored to the R-A7 newest-generation population (direct `identity_resolution.parquet` read at `max(computed_at)`, not `store.read_identity_resolution(latest=True)`).

**Round r2b (repair) — harness corrections by seat orchestrator E:** D8 N5 probe amended: GitHub job logs render `::group::` as `##[group]`; probe now matches both forms. D9 round r2 composed PHASE-2/D2E from the first HOLD (N5) although FAIL rows (R1.A, R3.2) existed; rule takes the first FAIL row first.


**Round pin3 (re-measure) — harness corrections by seat orchestrator E:** D11 pin3: re-measure at PIN3 ebe35dc9 (#8544); R0.2 mirrors -> #8543 527243be; C6 /rows restored to GEN1 truth; §6 recomposed (PHASE-2 PENDING:GEN3).

**Round pin3r (repair) — harness corrections by seat orchestrator E:** D12 pin3r: exact PIN3 command per row + verbatim PIN3 probes in Appendix C (m1); R1.A delta lifecycle detail + canonical rule (m2); md D11 (m3); header PIN3/#8543/lane/written-at (m4); rows_pin3 R1.A stale PIN1 failure fields removed (review MAJOR 1); C6 PIN3 owner/repair/gate (review minor 5); §6.C GEN3 must-show made literal (review minor 6).

**Round pin3s (repair) — harness corrections by seat orchestrator E:** D13 pin3s: R0.2 exact command and literal output (the 40-char-sha grep printed no WS line; the WS record cites 12-char shas at :58/:70/:82); every Appendix C anchor referenced from §6.A / command_ref resolves (§-headers); the four verbatim probe heredocs are closed (copy-paste runnable).

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
| R0.2 | Agent OS acceptance trace | commission §1 | `git grep` agentos D2C/D2D accept | at PIN1 no line cited both (HOLD); satisfied by #8543 merge 527243be5c03c79c016d8731179307f6ff03bf1d (2026-10-06T11:54:25Z): WS-GMI-THEME-GRAPH.md:58 D2C squash 0b1fe8873054, :70 D2D squash 79b566f5c0cc, :82 "D2C and D2D are MERGED (0b1fe8873054, 79b566f5c0cc)"; #8543 merge is an ancestor of PIN3 (rc=0) | PASS | — | — |
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
| R0.1 | Predecessor ancestry | commission §1 | `git merge-base --is-ancestor` ×5 (exact: App. C §PROBE_R0_1) | PIN3: 0b1fe88730547207475ad3c04118d2e771a9b949 rc=0; 79b566f5c0ccba878ab963084a239993d3116aa9 rc=0; 192a46de8be8c694e47a1f2ab60b396d7dbb4f7f rc=0; 527243be5c03c79c016d8731179307f6ff03bf1d rc=0; ebe35dc916de5aae556371a5aa963c6692175c9c rc=0 | PASS | — | — |
| R0.2 | Agent OS acceptance trace | commission §1 | `git grep` WS + #8543 merge (exact: App. C §PROBE_R0_2) | PIN3: agentos/workstreams/WS-GMI-THEME-GRAPH.md:58: MERGED 2026-10-06T09:50:19Z as squash 0b1fe8873054 at head f5b9a42b91fb, under Sol's | agentos/workstreams/WS-GMI-THEME-GRAPH.md:70: MERGED 2026-10-06T10:42:10Z as squash 79b566f5c0cc at head 69a1aa7d90cb (ci.yml | agentos/workstreams/WS-GMI-THEME-GRAPH.md:82: D2C and D2D are MERGED (0b1fe8873054, 79b566f5c0cc), so acceptance is live as a | 527243be_rc=0 — reading: at PIN1 no line cited both (HOLD); satisfied by #8543 merge 527243be5c03c79c016d8731179307f6ff03bf1d (2026-10-06T11:54:25Z): WS-GMI-THEME-GRAPH.md:58 D2C squash 0b1fe8873054, :70 D2D squash 79b566f5c0cc, :82 "D2C and D2D are MERGED (0b1fe8873054, 79b566f5c0cc)"; #8543 merge is an ancestor of PIN3 (rc=0) | PASS | — | — |
| R0.3 | No overlapping D2E carrier | commission §2 | `gh pr list --search D2E` (exact: App. C §PROBE_R0_3) | PIN3: open #8540 (D2E acceptance carrier) + blueprint #8324 only | PASS | — | — |
| R0.4 | Owner-action authority #8507 | commission §2 | `gh pr view 8507`; grep (exact: App. C §PROBE_R0_4) | PIN3: state=MERGED mergeCommit=cbfa20a45d8401f1cf1cc9fc48155455f1d612fb; OWNER_ACTION grep matches=5 | PASS | — | — |
| R1.A | D2A identity resolution | D2A | `pytest` identity_resolution + identity (exact: App. C §PROBE_R1_A) | PIN3: 121 passed in 5.22s; tests/test_theme_graph_identity_resolution.py: 56 passed in 5.17s; tests/test_theme_graph_identity.py: 65 passed in 0.57s | PASS | — | — |
| R1.A-CI | D2A data lane (INFO) | informational | `data-health.yml` run list (exact: App. C §PROBE_R1_A_CI) | PIN3: no data-health.yml run on a head containing PIN3 yet | INFO | — | — |
| R1.B | D2B lifecycle hostile matrix | D2B | `pytest` test_theme_graph_lifecycle.py (exact: App. C §PROBE_R1_B) | PIN3: 57 passed in 2.96s | PASS | — | — |
| R1.C | D2C PIT vintage | D2C #8432 | basket PIT pytest bundle (exact: App. C §PROBE_R1_C) | PIN3: 143 passed, 14 warnings in 3.16s | PASS | — | — |
| R1.D | D2D ontology/probation | D2D #8435 | crosswalk/local_plane/structural/exposure pytest (exact: App. C §PROBE_R1_D) | PIN3: 576 passed in 10.58s | PASS | — | — |
| R1.E | Materialize + contracts | store contract | materialize + contracts pytest (exact: App. C §PROBE_R1_E) | PIN3: 132 passed in 7.01s | PASS | — | — |
| R1.F | Rights tests (theme graph) | rights gate | rights_use + theme_sources pytest (exact: App. C §PROBE_R1_F) | PIN3: 31 passed in 0.75s | PASS | — | — |
| R1.X | MarketOntology half-B rights docket | F00C ledger (non-gating) | half_b_rights_docket pytest (exact: App. C §PROBE_R1_X) | PIN3: 3 failed, 16 passed in 0.53s | FAIL-INFO | MarketOntology CEO A | reconcile docket vs F00C closure ledger CSV |
| R2 | Strict contract guard | CI guard | `check_theme_graph_contracts` (exact: App. C §PROBE_R2) | PIN3: selftest rc=0; strict rc=0 | PASS | — | — |
| C1 | Lifecycle standing | D2B3 §3 | pandas `node_lifecycle` probe (exact: App. C §PROBE_D2B3) | PIN3: co:us:GOLD retired 2025-12-02 identity_break; co:us:IBIT retired 2026-08-22 entity_type_conflict; co:us:VMRK merged_into co:us:EQR | PASS | — | — |
| C2 | GOLD edge closure | D2B3 §4 | pandas GOLD MEMBER_OF (exact: App. C §PROBE_D2B3) | PIN3: GOLD belief_rows 2; open gold_miners 12 GOLD_in False | PASS | — | — |
| C3 | IBIT refusal fence | D2B3 §6 | pandas IBIT + `_meta` refusals (exact: App. C §PROBE_D2B3) | PIN3: IBIT MEMBER_OF annulled valid_from=valid_to=2023-05-09; IBIT refusal 1; live co:us:IBIT MEMBER_OF 0 | PASS | — | — |
| C4 | Retired-consistency | D2B3 §12 | retired-like/merged vs live MEMBER_OF (exact: App. C §PROBE_D2B3) | PIN3: violations: 0 (7797 live MEMBER_OF edges, 3 retired-like/merged nodes, 0 offenders) | PASS | — | — |
| C5 | Identity sidecar R-A2 | D2B3 §13 | NEWEST `identity_resolution` generation (exact: App. C §PROBE_D2B3) | PIN3: US 1237 RESOLVED=1211 NOT_IN_MASTER=25 DEFERRED=1 ENTITY_TYPE_CONFLICT=0; RESOLVED share 0.978981; NEWEST sum=2805 | PASS | — | — |
| C6 | Generation provenance at PIN3 | receipt timing | `git log` + merge-base vs GEN2/engine (exact: App. C §PROBE_C6) | PIN3: GEN2 natural generation f9ccad3e50f671499893f8113ba96ae2910ab5e7 (2026-10-06T13:27:04Z) + #8544 correction rows; D2C/D2D ancestry rc=0 vs engine 640e3e237eede62351b6f657c8e13ad20274585c; sole post-GEN2 data/theme_graph commit ebe35dc916de5aae556371a5aa963c6692175c9c (#8544) | PASS | — | — |
| C7 | Nightly `_meta` history | informational | `git log -5` `_meta.json` (exact: App. C §PROBE_C7) | PIN3: 5/5 _meta commits carry node_lifecycle>=2 and IBIT refusal | PASS | — | — |
| R3.1 | Registry table | rights gate #2 | `config/theme_sources.yml` (exact: App. C §PROBE_R3V) | PIN3: finviz_themes/ths_concepts internal_only; all families rights_class set | PASS | — | — |
| R3.2 | Source-ref census | display tier | `family_for_source_ref` on evidence (exact: App. C §PROBE_R3V) | PIN3: 23 rows / 18 distinct refs; ths_concepts 12; mastermind_curated 9; finviz_themes 2; None 0 | PASS | — | — |
| R3.3 | Spot checks | #8499 | two `family_for_source_ref` calls (exact: App. C §PROBE_R3V) | PIN3: probation → mastermind_curated; site/factordata/us_standouts.json → None (intentional) | PASS | — | — |
| V1 | Node prefix census | coverage | `nodes.parquet` (exact: App. C §PROBE_R3V) | PIN3: total=3882; co:us=1239; co:cn=1021; ltheme=644; basket=358 | PASS | — | — |
| V2 | Capability generations | coverage | `store.read_capability()` vs newest gen (exact: App. C §PROBE_R3V) | PIN3: read_capability=644; file 34704 rows / 54 generations; newest gen 643 rows | PASS | — | — |
| V3 | Identity generations | coverage | sidecar NEWEST vs `_meta` (exact: App. C §PROBE_R3V) | PIN3: NEWEST=2805; latest-per-node=2807; _meta.counts.identity_resolution=2807; file 157075 rows / 56 gens | PASS | — | — |
| V4 | THS mapping arithmetic | coverage | `_meta` crosswalk + local_plane (exact: App. C §PROBE_R3V) | PIN3: ths concepts=375; mapped 61 + unknown 0; unmapped_concept_count=314 | PASS | — | — |
| V5 | Probation proposals | coverage | `proposals.jsonl` status (exact: App. C §PROBE_R3V) | PIN3: proposals lines=236 proposed=234 rejected=2 | PASS | — | — |
| V6 | PIT vintage + edge era | coverage | `_meta.per_suite` + edges era (exact: App. C §PROBE_R3V) | PIN3: edges observed=12424 reconstruction=12677 (reconstruction not observed proof) | PASS | — | — |
| V7 | Refusal/negative categories | coverage | `_meta` negative buckets (exact: App. C §PROBE_R3V) | PIN3: company_mint_refusals=1; NOT_IN_MASTER=195; UNSUPPORTED_MARKET=233 | PASS | — | — |

### §6.B R1.A delta 2807→2806

Frozen D2A pin (`tests/test_theme_graph_identity_resolution.py:99-120`): physical company nodes = **2806** frozen + post-freeze merged duplicates; canonical = physical `kind==company` minus nodes whose **latest** `node_lifecycle` status is `merged` (canonical company set). canonical_rule: canonical = physical kind=='company' nodes minus those whose LATEST node_lifecycle status == 'merged' (post-freeze merged duplicates; co:us:GOLD and co:us:IBIT are latest-status 'retired' and are inside the frozen 2806, so they are not subtracted). computed_at (store): `2026-10-06T13:27:04Z`.

| measure | GEN2 (`f9ccad3e50f671499893f8113ba96ae2910ab5e7`) | PIN3 (`ebe35dc916de5aae556371a5aa963c6692175c9c`) |
| --- | --- | --- |
| physical `kind==company` | 2807 | 2807 |
| canonical (exclude latest `merged`) | 2807 | 2806 |

Symmetric difference on canonical sets: **left** `co:us:VMRK` (latest lifecycle `merged`, `merged_into=co:us:EQR`, `ratified_by=DEC:THEME-GRAPH-RENAME-REMINT-MERGES-INTO-INCUMBENT-NODE`); **entered** ∅. `co:us:EQR` remains a live company node. Counts at PIN3: physical 2807; canonical (minus merged) 2806; minus-all-RETIRED_LIKE 2804.

### §6.C PHASE-2 status

PENDING:GEN3 first natural daily.yml engine run whose checkout contains ebe35dc916de5aae556371a5aa963c6692175c9c (cron 22:30Z; seat GEN3 check ~2026-10-07T14:07Z)

GEN3 must show (literal):
(i) the run is a natural `schedule`-event daily.yml run (not workflow_dispatch / rerun) — the FIRST such run whose engine-job checkout contains ebe35dc916de5aae556371a5aa963c6692175c9c;
(ii) for its engine-job checkout sha X: `git merge-base --is-ancestor ebe35dc916de5aae556371a5aa963c6692175c9c X` rc=0;
(iii) the theme-graph build and guard log groups end rc=0;
(iv) the natural data commit's data/theme_graph/_meta.json computed_at equals the generation computed_at the run logged;
(v) R1.A pytest 0 failed with physical company nodes 2807 and canonical 2806 (co:us:VMRK latest lifecycle status merged, merged_into co:us:EQR);
(vi) R3.2 family_for_source_ref None = 0 over every distinct evidence source_ref;
(vii) N1–N7 and Q1–Q4 re-run on that checkout.
D2E cannot read PASS before the seat records PHASE-2 PASS at GEN3.

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

**PIN3 worktree:** `git worktree add --detach ../mo-ext-pin3m-8540 ebe35dc916de5aae556371a5aa963c6692175c9c`; hydrate tracked `data/theme_graph/*`, `data/reference/security_master.parquet`, `data/china_search/closes.parquet`, `data/theme_graph/probation/*` from git bytes when sparse.

**§PROBE_R0_1 — R0.1** — command:
```
for c in 0b1fe88730547207475ad3c04118d2e771a9b949 79b566f5c0ccba878ab963084a239993d3116aa9 192a46de8be8c694e47a1f2ab60b396d7dbb4f7f 527243be5c03c79c016d8731179307f6ff03bf1d ebe35dc916de5aae556371a5aa963c6692175c9c; do git merge-base --is-ancestor "$c" HEAD; echo "$c rc=$?"; done
```
output: `PIN3: 0b1fe88730547207475ad3c04118d2e771a9b949 rc=0; 79b566f5c0ccba878ab963084a239993d3116aa9 rc=0; 192a46de8be8c694e47a1f2ab60b396d7dbb4f7f rc=0; 527243be5c03c79c016d8731179307f6ff03bf1d rc=0; ebe35dc916de5aae556371a5aa963c6692175c9c rc=0`

**§PROBE_R0_2 — R0.2** — command:
```
git grep -n -E '0b1fe887|79b566f5' agentos/workstreams/WS-GMI-THEME-GRAPH.md | grep -F MERGED; git merge-base --is-ancestor 527243be5c03c79c016d8731179307f6ff03bf1d HEAD; echo 527243be_rc=$?
```
output (literal at PIN3 worktree):
```
agentos/workstreams/WS-GMI-THEME-GRAPH.md:58:      MERGED 2026-10-06T09:50:19Z as squash 0b1fe8873054 at head f5b9a42b91fb, under Sol's
agentos/workstreams/WS-GMI-THEME-GRAPH.md:70:      MERGED 2026-10-06T10:42:10Z as squash 79b566f5c0cc at head 69a1aa7d90cb (ci.yml
agentos/workstreams/WS-GMI-THEME-GRAPH.md:82:      D2C and D2D are MERGED (0b1fe8873054, 79b566f5c0cc), so acceptance is live as a
527243be_rc=0
```
recorded tail: `PIN3: agentos/workstreams/WS-GMI-THEME-GRAPH.md:58: MERGED 2026-10-06T09:50:19Z as squash 0b1fe8873054 at head f5b9a42b91fb, under Sol's | agentos/workstreams/WS-GMI-THEME-GRAPH.md:70: MERGED 2026-10-06T10:42:10Z as squash 79b566f5c0cc at head 69a1aa7d90cb (ci.yml | agentos/workstreams/WS-GMI-THEME-GRAPH.md:82: D2C and D2D are MERGED (0b1fe8873054, 79b566f5c0cc), so acceptance is live as a | 527243be_rc=0` — reading: at PIN1 no line cited both (HOLD); satisfied by #8543 merge 527243be5c03c79c016d8731179307f6ff03bf1d (2026-10-06T11:54:25Z): WS-GMI-THEME-GRAPH.md:58 D2C squash 0b1fe8873054, :70 D2D squash 79b566f5c0cc, :82 "D2C and D2D are MERGED (0b1fe8873054, 79b566f5c0cc)"; #8543 merge is an ancestor of PIN3 (rc=0)

**§PROBE_R0_3 — R0.3** — command:
```
gh pr list -R mastermindx-market-intelligence/macro --state open --search "D2E" --json number,title,headRefName --limit 20
```
output: `PIN3: open #8540 (D2E acceptance carrier) + blueprint #8324 only`

**§PROBE_R0_4 — R0.4** — command:
```
gh pr view 8507 -R mastermindx-market-intelligence/macro --json state,mergeCommit; git grep -c OWNER_ACTION_AUTHORITY_UNAVAILABLE HEAD -- engine scripts tests
```
output: `PIN3: state=MERGED mergeCommit=cbfa20a45d8401f1cf1cc9fc48155455f1d612fb; OWNER_ACTION grep matches=5`

**§PROBE_R1_A — R1.A** — command:
```
TZ=UTC COLLECT_LANE=nightly /home/longr/lanes/tmp/d2e-venv/bin/python -m pytest -p no:cacheprovider -q -rfEs tests/test_theme_graph_identity_resolution.py tests/test_theme_graph_identity.py
```
output: `PIN3: 121 passed in 5.22s; tests/test_theme_graph_identity_resolution.py: 56 passed in 5.17s; tests/test_theme_graph_identity.py: 65 passed in 0.57s`

**§PROBE_R1_A_CI — R1.A-CI** — command:
```
gh run list -R mastermindx-market-intelligence/macro --workflow data-health.yml --branch main -L 5 --json databaseId,headSha,conclusion,status
```
output: `PIN3: no data-health.yml run on a head containing PIN3 yet`

**§PROBE_R1_B — R1.B** — command:
```
TZ=UTC COLLECT_LANE=nightly /home/longr/lanes/tmp/d2e-venv/bin/python -m pytest -p no:cacheprovider -q -rfEs tests/test_theme_graph_lifecycle.py
```
output: `PIN3: 57 passed in 2.96s`

**§PROBE_R1_C — R1.C** — command:
```
TZ=UTC COLLECT_LANE=nightly /home/longr/lanes/tmp/d2e-venv/bin/python -m pytest -p no:cacheprovider -q -rfEs tests/test_basket_membership_pit.py tests/test_us_basket_membership_pit.py tests/test_theme_graph_membership_lifecycle.py tests/test_gmi_history_integrity.py
```
output: `PIN3: 143 passed, 14 warnings in 3.16s`

**§PROBE_R1_D — R1.D** — command:
```
unset GMI_STATE_OWNER_WORKSPACE; TZ=UTC COLLECT_LANE=nightly /home/longr/lanes/tmp/d2e-venv/bin/python -m pytest -p no:cacheprovider -q -rfEs tests/test_theme_graph_crosswalk.py tests/test_theme_graph_local_plane.py tests/test_theme_graph_structural_owner_binding.py tests/test_market_ontology_exposure_map.py
```
output: `PIN3: 576 passed in 10.58s`

**§PROBE_R1_E — R1.E** — command:
```
TZ=UTC COLLECT_LANE=nightly /home/longr/lanes/tmp/d2e-venv/bin/python -m pytest -p no:cacheprovider -q -rfEs tests/test_theme_graph_materialize.py tests/test_theme_graph_contracts.py
```
output: `PIN3: 132 passed in 7.01s`

**§PROBE_R1_F — R1.F** — command:
```
TZ=UTC COLLECT_LANE=nightly /home/longr/lanes/tmp/d2e-venv/bin/python -m pytest -p no:cacheprovider -q -rfEs tests/test_theme_graph_rights_use.py tests/test_theme_sources_registry.py
```
output: `PIN3: 31 passed in 0.75s`

**§PROBE_R1_X — R1.X** — command:
```
TZ=UTC COLLECT_LANE=nightly /home/longr/lanes/tmp/d2e-venv/bin/python -m pytest -p no:cacheprovider -q -rfEs tests/test_market_ontology_half_b_rights_docket.py
```
output: `PIN3: 3 failed, 16 passed in 0.53s`

**§PROBE_R2 — R2** — command:
```
TZ=UTC /home/longr/lanes/tmp/d2e-venv/bin/python -m scripts.check_theme_graph_contracts --selftest; TZ=UTC /home/longr/lanes/tmp/d2e-venv/bin/python -m scripts.check_theme_graph_contracts --strict
```
output: `PIN3: selftest rc=0; strict rc=0`

**§PROBE_C1 — C1** — command:
```
/home/longr/lanes/tmp/d2e-venv/bin/python - <<'PROBE_D2B3'
```
output: `PIN3: co:us:GOLD retired 2025-12-02 identity_break; co:us:IBIT retired 2026-08-22 entity_type_conflict; co:us:VMRK merged_into co:us:EQR`

**§PROBE_C2 — C2** — command:
```
/home/longr/lanes/tmp/d2e-venv/bin/python - <<'PROBE_D2B3'
```
output: `PIN3: GOLD belief_rows 2; open gold_miners 12 GOLD_in False`

**§PROBE_C3 — C3** — command:
```
/home/longr/lanes/tmp/d2e-venv/bin/python - <<'PROBE_D2B3'
```
output: `PIN3: IBIT MEMBER_OF annulled valid_from=valid_to=2023-05-09; IBIT refusal 1; live co:us:IBIT MEMBER_OF 0`

**§PROBE_C4 — C4** — command:
```
/home/longr/lanes/tmp/d2e-venv/bin/python - <<'PROBE_D2B3'
```
output: `PIN3: violations: 0 (7797 live MEMBER_OF edges, 3 retired-like/merged nodes, 0 offenders)`

**§PROBE_C5 — C5** — command:
```
/home/longr/lanes/tmp/d2e-venv/bin/python - <<'PROBE_D2B3'
```
output: `PIN3: US 1237 RESOLVED=1211 NOT_IN_MASTER=25 DEFERRED=1 ENTITY_TYPE_CONFLICT=0; RESOLVED share 0.978981; NEWEST sum=2805`

**§PROBE_C6 — C6** — command:
```
git log -4 --oneline -- data/theme_graph/_meta.json; git log f9ccad3e50f671499893f8113ba96ae2910ab5e7..HEAD --oneline -- data/theme_graph; for c in 0b1fe88730547207475ad3c04118d2e771a9b949 79b566f5c0ccba878ab963084a239993d3116aa9; do git merge-base --is-ancestor "$c" 640e3e237eede62351b6f657c8e13ad20274585c; echo "$c vs engine rc=$?"; done
```
output: `PIN3: GEN2 natural generation f9ccad3e50f671499893f8113ba96ae2910ab5e7 (2026-10-06T13:27:04Z) + #8544 correction rows; D2C/D2D ancestry rc=0 vs engine 640e3e237eede62351b6f657c8e13ad20274585c; sole post-GEN2 data/theme_graph commit ebe35dc916de5aae556371a5aa963c6692175c9c (#8544)`

**§PROBE_C7 — C7** — command:
```
/home/longr/lanes/tmp/d2e-venv/bin/python - <<'PROBE_C7'
```
output: `PIN3: 5/5 _meta commits carry node_lifecycle>=2 and IBIT refusal`

**§PROBE_R3_1 — R3.1** — command:
```
/home/longr/lanes/tmp/d2e-venv/bin/python - <<'PROBE_R3V'
```
output: `PIN3: finviz_themes/ths_concepts internal_only; all families rights_class set`

**§PROBE_R3_2 — R3.2** — command:
```
/home/longr/lanes/tmp/d2e-venv/bin/python - <<'PROBE_R3V'
```
output: `PIN3: 23 rows / 18 distinct refs; ths_concepts 12; mastermind_curated 9; finviz_themes 2; None 0`

**§PROBE_R3_3 — R3.3** — command:
```
/home/longr/lanes/tmp/d2e-venv/bin/python - <<'PROBE_R3V'
```
output: `PIN3: probation → mastermind_curated; site/factordata/us_standouts.json → None (intentional)`

**§PROBE_V1 — V1** — command:
```
/home/longr/lanes/tmp/d2e-venv/bin/python - <<'PROBE_R3V'
```
output: `PIN3: total=3882; co:us=1239; co:cn=1021; ltheme=644; basket=358`

**§PROBE_V2 — V2** — command:
```
/home/longr/lanes/tmp/d2e-venv/bin/python - <<'PROBE_R3V'
```
output: `PIN3: read_capability=644; file 34704 rows / 54 generations; newest gen 643 rows`

**§PROBE_V3 — V3** — command:
```
/home/longr/lanes/tmp/d2e-venv/bin/python - <<'PROBE_R3V'
```
output: `PIN3: NEWEST=2805; latest-per-node=2807; _meta.counts.identity_resolution=2807; file 157075 rows / 56 gens`

**§PROBE_V4 — V4** — command:
```
/home/longr/lanes/tmp/d2e-venv/bin/python - <<'PROBE_R3V'
```
output: `PIN3: ths concepts=375; mapped 61 + unknown 0; unmapped_concept_count=314`

**§PROBE_V5 — V5** — command:
```
/home/longr/lanes/tmp/d2e-venv/bin/python - <<'PROBE_R3V'
```
output: `PIN3: proposals lines=236 proposed=234 rejected=2`

**§PROBE_V6 — V6** — command:
```
/home/longr/lanes/tmp/d2e-venv/bin/python - <<'PROBE_R3V'
```
output: `PIN3: edges observed=12424 reconstruction=12677 (reconstruction not observed proof)`

**§PROBE_V7 — V7** — command:
```
/home/longr/lanes/tmp/d2e-venv/bin/python - <<'PROBE_R3V'
```
output: `PIN3: company_mint_refusals=1; NOT_IN_MASTER=195; UNSUPPORTED_MARKET=233`

**§PROBE_D2B3 (verbatim)** — C1–C5 (shared)
```
/home/longr/lanes/tmp/d2e-venv/bin/python - <<'PROBE_D2B3'
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
    mi = r.get("merged_into")
    extra = f" merged_into={mi}" if pd.notna(mi) and str(mi) else ""
    print(f"  {r['node_id']}: status={r['status']} retire_date={r.get('retire_date')} reason={r.get('reason')}{extra}")

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
retired_like = set(lc_latest.loc[lc_latest["status"].isin(["retired","merged"]),"node_id"].astype(str))
ordered = hist.sort_values(["edge_id","belief_time","computed_at"], kind="stable")
current_edges = ordered.drop_duplicates(subset=["edge_id"], keep="last")
live_mo = current_edges[(current_edges["type"]=="MEMBER_OF") & current_edges["valid_to"].map(pd.isna)]
offenders = sorted(set(live_mo["src"].astype(str)) & retired_like)
print("violations:", len(offenders), f"({len(live_mo)} live MEMBER_OF edges, {len(retired_like)} retired-like/merged nodes, {len(offenders)} offenders)")

idres = pd.read_parquet("data/theme_graph/identity_resolution.parquet")
mx = idres["computed_at"].max()
nw = idres[idres["computed_at"] == mx]
us = nw[nw["market_scope"].astype(str) == "us"]
vc = us["resolution_state"].value_counts()
print("C5 NEWEST computed_at", mx)
print("US", len(us), dict(sorted(vc.items())))
print("RESOLVED share", round(vc.get("RESOLVED", 0) / len(us), 6))
print("NEWEST sum", len(nw))
PROBE_D2B3
```

**§PROBE_R1A_DELTA (verbatim)** — §6.B delta
```
/home/longr/lanes/tmp/d2e-venv/bin/python - <<'PROBE_R1A_DELTA'
import json
import pandas as pd
from engine.theme_graph import store

nodes = pd.read_parquet("data/theme_graph/nodes.parquet")
physical = nodes[nodes["kind"].astype(str) == "company"]
physical_count = len(physical)
lc = store.read_node_lifecycle(latest=True)
merged_ids = set(lc.loc[lc["status"] == "merged", "node_id"].astype(str))
canonical = physical[~physical["node_id"].astype(str).isin(merged_ids)]
canonical_count = len(canonical)
retired_like = set(lc.loc[lc["status"].isin(["retired", "merged"]), "node_id"].astype(str))
minus_retired = physical[~physical["node_id"].astype(str).isin(retired_like)]
print("physical", physical_count)
print("canonical_minus_merged", canonical_count)
print("minus_all_RETIRED_LIKE", len(minus_retired))
meta = json.loads(open("data/theme_graph/_meta.json").read())
computed_at = meta.get("computed_at")
for nid in ["co:us:VMRK"]:
    row = lc[lc["node_id"].astype(str) == nid].iloc[0]
    merged_into = str(row.get("merged_into"))
    target_live = merged_into in set(canonical["node_id"].astype(str))
    print("VMRK", row["status"], "merged_into", merged_into, "ratified_by", row.get("ratified_by"), "computed_at", row.get("computed_at"), "merged_into_is_live_company", target_live)
PROBE_R1A_DELTA
```

**§PROBE_R3V (verbatim)** — R3.1–R3.3, V1–V7 (shared)
```
/home/longr/lanes/tmp/d2e-venv/bin/python - <<'PROBE_R3V'
import json, yaml
import pandas as pd
from collections import Counter
from engine.theme_graph.rights import family_for_source_ref
from engine.theme_graph import store
import pathlib

with open("config/theme_sources.yml") as f:
    ts = yaml.safe_load(f)
fams = ts.get("families", {})
for k in ["finviz_themes", "ths_concepts", "mastermind_curated"]:
    print(k, fams.get(k, {}).get("rights_class"), fams.get(k, {}).get("internal_only"))
print("all_have_rights", all("rights_class" in fams[k] for k in fams))

ev = pd.read_parquet("data/theme_graph/evidence.parquet")
row_counts = Counter()
for r in ev["source_ref"].astype(str):
    row_counts[family_for_source_ref(r)] += 1
refs = ev["source_ref"].dropna().astype(str).unique()
print("R3.2 rows", len(ev), "distinct", len(refs), "counts", dict(row_counts), "None", row_counts[None])

for ref in ["data/theme_graph/probation/relation_events.v2.jsonl#x", "site/factordata/us_standouts.json"]:
    print("spot", ref, "->", family_for_source_ref(ref))

nodes = pd.read_parquet("data/theme_graph/nodes.parquet")
co_us = sum(1 for n in nodes["node_id"].astype(str) if n.startswith("co:us:"))
co_cn = sum(1 for n in nodes["node_id"].astype(str) if n.startswith("co:cn:"))
ltheme = sum(1 for n in nodes["node_id"].astype(str) if n.startswith("ltheme:"))
basket = sum(1 for n in nodes["node_id"].astype(str) if n.startswith("basket:"))
print("V1 total", len(nodes), "co:us", co_us, "co:cn", co_cn, "ltheme", ltheme, "basket", basket)

cap = store.read_capability()
cap_file = pd.read_parquet("data/theme_graph/capability.parquet")
mx = cap_file["computed_at"].max()
print("V2 read_capability", len(cap), "file_rows", len(cap_file), "gens", cap_file["computed_at"].nunique(), "newest_gen_rows", len(cap_file[cap_file["computed_at"]==mx]))

idres = pd.read_parquet("data/theme_graph/identity_resolution.parquet")
mx2 = idres["computed_at"].max()
nw = idres[idres["computed_at"]==mx2]
lp = idres.sort_values("computed_at", kind="stable").drop_duplicates("node_id", keep="last")
meta = json.load(open("data/theme_graph/_meta.json"))
print("V3 NEWEST", len(nw), "latest_per_node", len(lp), "_meta.counts.ir", meta["counts"].get("identity_resolution"), "file", len(idres), "gens", idres["computed_at"].nunique())

cw = meta.get("per_suite", {}).get("crosswalk", {})
ths = meta["local_plane"]["ths"]
print("V4 concepts", ths["concepts"], "mapped", cw.get("ths_codes_mapped"), "unknown", cw.get("ths_codes_unknown"), "unmapped", meta.get("ths_unmapped_concept_count"))

props = pathlib.Path("data/theme_graph/probation/proposals.jsonl").read_text().strip().splitlines()
st = Counter(json.loads(line).get("status") for line in props)
print("V5 lines", len(props), dict(st))

edges = pd.read_parquet("data/theme_graph/edges.parquet")
print("V6 edges observed", int((edges["era"]=="observed").sum()), "reconstruction", int((edges["era"]=="reconstruction").sum()))
isc = meta.get("identity_resolution_state_counts",{})
print("V7 refusals", len(meta.get("company_mint_refusals",[])), "NOT_IN_MASTER", isc.get("NOT_IN_MASTER"), "UNSUPPORTED", isc.get("UNSUPPORTED_MARKET"))
PROBE_R3V
```

**§PROBE_C7 (verbatim)** — C7
```
/home/longr/lanes/tmp/d2e-venv/bin/python - <<'PROBE_C7'
import json, subprocess
shas = subprocess.check_output(["git","log","-5","--format=%H","--","data/theme_graph/_meta.json"], text=True).strip().splitlines()
ok=0
for sha in shas:
    raw = subprocess.check_output(["git","show",f"{sha}:data/theme_graph/_meta.json"], text=True)
    m=json.loads(raw)
    lc=m.get("counts",{}).get("node_lifecycle",0)
    ref=any("IBIT" in json.dumps(x) for x in m.get("company_mint_refusals",[]))
    if lc>=2 and ref:
        ok+=1
print("C7", ok, "/", len(shas))
PROBE_C7
```

**§PROBE_R1_A_FILES** — per-file pytest (PIN3 worktree `ebe35dc916de5aae556371a5aa963c6692175c9c`):
```
TZ=UTC COLLECT_LANE=nightly /home/longr/lanes/tmp/d2e-venv/bin/python -m pytest -p no:cacheprovider -q -rfEs tests/test_theme_graph_identity_resolution.py
56 passed in 5.17s
TZ=UTC COLLECT_LANE=nightly /home/longr/lanes/tmp/d2e-venv/bin/python -m pytest -p no:cacheprovider -q -rfEs tests/test_theme_graph_identity.py
65 passed in 0.57s
TZ=UTC COLLECT_LANE=nightly /home/longr/lanes/tmp/d2e-venv/bin/python -m pytest -p no:cacheprovider -q -rfEs tests/test_theme_graph_identity_resolution.py tests/test_theme_graph_identity.py
121 passed in 5.22s
```

**tests/test_theme_graph_identity_resolution.py:99-120 (PIN3)** — POST_FREEZE_MERGED_DUPLICATES, merged lifecycle assertions for co:us:VMRK.

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



## Prospective evidence-window amendment — ADOPTED PROSPECTIVE RULE ONLY

Candidate ID: `D2E-PROSPECTIVE-NATURAL-WITNESS-20261008`. Sole carrier: existing
Macro PR #8540, original record head `52d57f34aad6956b3ddb697fff34c82588e791af`.
This appendix and the matching `prospective_evidence_window_candidate` JSON
subtree record the adopted prospective evidence-window rule only. They grant no acceptance or
execution authority. All text above and every pre-existing JSON subtree remain
historical evidence, including their then-current verdicts, counts and commands.
Their preservation does not turn a historical PASS into a current result.

**Adoption status: ADOPTED_PROSPECTIVE_RULE_ONLY.** Principal adjudicator
`ceo-sol` adopted only this prospective evidence-window rule in
[#8540 comment 6071188794](https://github.com/mastermindx-market-intelligence/macro/pull/8540#issuecomment-6071188794), created_at `2026-10-08T23:38:32Z`.
External final R6 independent review PASS receipt SHA256 `c831dd818eb9bec065fc0346e7e04b55bc596a92ecd577d2b8d3e729514531f3`
binds the frozen pre-adoption content identified below. The original attempt-1
workflow-run `run_started_at` must be strictly later than that designated
comment `created_at`; all other frozen selection and proof laws remain.
No actual replacement run, effective checkout, publication commit or Phase-2/P3
acceptance is asserted. This author's implementation and deterministic proof
contributions are not independent review. The inherited acceptance law and all
gates remain unchanged; W3B remains held.

### Reason and historical boundary

GEN3 natural run `37558610387`, engine job `112633282165`, used code
`07db8e5931d93a08d5c92022373e7a3a60ab2c76` and published data
`856c5939858fe6adcf41bfc2e10787a21de649a3`. Retained historical logs cannot prove
N4's logged-final-metadata equality or N5's natural build/guard completion.
**Historical GEN3 N4 and N5 remain UNPROVEN.** The deterministic checks recorded
in #8540 comment `6068374556` do not replace those observations. The final metadata
clock `2026-10-07T08:00:17Z` and materialization-row clock `08:00:10Z` are different
clocks; their seven-second difference is preserved, not repaired into equality.

Oct 8 run `37716729584`, engine job `113158877653`, remains only a later N5
candidate. It is not reclassified as complete N4/N5 evidence or selected by this
amendment. No historical run receives a retroactive PASS. This amendment neither
reruns production nor changes any historical ledger, source datum or result.

### Frozen prerequisites and selection rule

Before adoption, root must resolve and record every actual squash merge, exact
reviewed PR head, principal release receipt and post-merge owned-source verification.
The source-release facts below are now resolved; they are not D2E adoption or generation acceptance:

| Dependency | Frozen reviewed head | Verified squash merge binding |
|---|---|---|
| C4 #8629 | `a4deb82387895dae58bb77404faeeb851450c174` | Verified squash `123eda091dfd0d83c4c303f7f138d4c8a2c7e128`; principal release comment `6070151039`; post-merge parity receipt below |
| M1 #8651 | `0b331ec68f26ef2decbcf67eabb9cac38b415fc9` | Verified squash `11b48b2304ecda38bc4f78594af58cc8bfafd871`; principal release comment `6069579052`; four-owned-blob post-merge parity receipt below |
| Witness retention #8653 | `ebd4382fdafdfecf55029305baddfa95b60f863a` | Verified squash `c44aae5f131a59571ad0afcd7197e3d8696bc2b9`; principal release comment `6070969336`; binding CI and five-owned-blob post-merge parity below |

C4's root post-merge receipt SHA256 is
`68dc86e87015722c6a62e2e6e24dd4e03c5cf77d706f15e7f9ecdb9752823b18`,
recorded `2026-10-08T22:37:50.349280Z`, observing main
`8a35d8b62494a84b2448182aaa561edea83fe54f`; the merge-ancestor probe returned rc 0.
Public post-merge proof is #8629 comment `6070559424`. The actual integrated
`.github/ci/legacy-jobs.yml` blob is
`b9e71767b7d1fc3ffe0de7dc981be31f0ee2fc31`: it preserves the already-landed
upstream PB-D #8654 squash `d2eec4732abee359ebb578b245fa7359b3c01a7d`, and adds
only C4's approved two population-test lines against the actual parent. The
other four C4 owned blobs match their reviewed bytes. Integration-review receipt
SHA256 `fd28cbb230b5b60c7fc874add65ac25856481976b4fdcf56a52e42834e8dd9c2`
records this conservation; it does not pretend the older whole-CI snapshot is
identical to the integrated merge. M1's root four-owned-blob post-merge receipt
SHA256 is `1b28c4aa215b46578053059cd2f285787439b50348785d340a2eb551af80862c`,
recorded `2026-10-08T21:40:51.683216Z`. These are dependency source-release facts,
not D2E generation observations or adoption.

The witness head was explicitly rebound from parent
`7df186a7553c8494bd846c8b06454f2fe3f222b3` to
`c40ea096a5116e5394ea4c0eaa3a6df5fe3e34fe` after independent exact-head review
PASS. Root reports the original four implementation/test blobs unchanged and
only one additional CI-trigger line in a fifth changed file. The independent
reviewer `gmi_dependency_audit` explicitly approved this changed-head binding.
This records source-review lineage, not a squash merge, CI release or adoption.

The current witness head `ebd4382fdafdfecf55029305baddfa95b60f863a` has parent
`c40ea096a5116e5394ea4c0eaa3a6df5fe3e34fe`. Under #8653 repair ruling
`6070559640`, it changes only the witness-ID export line to avoid the unchanged
DAG parser's embedded-brace collision, preserving all other band bytes and the
five-file PR scope. The frozen repair patch SHA256 is
`9e4ee11c771ef89787b0561ef41bf5292cd3edbc4b301cf61149ca5c83ea99df`, with
independent source-review PASS receipt
`9bf26eaf30998b0e8d7ff6af67bdab4a2f7d9963d4080f2a1b9ee86e7fff0c96`.
Independent exact-pushed-head review PASS receipt
`691290cdba78c4c1bd64fd941237e470523acd4c1d3bbe857c6ba6960e7309d1`
confirms sole parent c40, only the shell's one-line delta, the other four PR files
unchanged, and the native/push receipt hashes below.
Root's native validation receipt `witness-dag-repair-native-validation.json`,
SHA256 `87d8de97a673b7044314dbfacad5551576d1145a468e3f8c850bb86a5ca90af8`,
records nine pre-repair DAG mismatches and checker selftest PASS, followed by
27 lanes rc 0 with the same two inherited suspects, shell syntax PASS, ten
witness-ID parity cases and 114 tests passed with zero skips/failures. Root's
ordinary-push receipt `witness-dag-repair-commit-push.json`, SHA256
`eae620b3ed34edce2c9514ff1d3328acf3a94a8534a6b07933bdc08d6a12cc9b`, binds the
new head. Independent R4 review PASS receipt
`d2ca3707e269bd22e2404e29b06a77a288d22b2264a4945f18e9ba9c4b8b57e5`
accepted the ebd D2E head rebinding and the actual C4/M1 facts while final witness
CI/merge/release/parity were still pending. Those historical source/native/push
receipts retain their original scope.

Witness binding CI run `37855935397` completed with all 12 packs and applicable
gate, contract-delta, ci-plan, active main authority, fences, grader-manifest and
capability-broker checks successful. The inactive pilot authority context is not
silently relabeled successful; its failure is recorded as inactive base context.
Principal engineering/source release is #8653 comment `6070969336`. Accepted head
`ebd4382fdafdfecf55029305baddfa95b60f863a` was squash-merged as
`c44aae5f131a59571ad0afcd7197e3d8696bc2b9`, actual first parent
`53914368416d3350684887b3cc45070a3ad5700a`. Root's completed native receipt
`witness-post-merge.json`, SHA256
`0b10c9635fd886f8344bb1e44a83f63c7cc6ad88b8e065ccbde299e01a8cf20e`,
recorded `2026-10-08T23:20:32.267715Z`, observed that exact squash on main with
fetch and merge-ancestor rc 0, a clean witness workspace and native process
`36808` completed rc 0. Public postproof is #8653 comment `6070995691`.

All five integrated owned blobs were verified: producer `dc051c176b797f8f684fe0b7be599d922d42d05d`,
regional band `e59f2c2a43300b7e35a1e4b9719cafe286c3ff5d`, daily workflow
`26731b7c6bf05a18f818e16e8139c51418d0f0ce`, materialization test
`0eada6503e673ba3f5dcff2c675d81aac1ad6ec0`, and integrated CI
`178cbb69586301cd47da98e5400b023a2a977c36`. The complete integrated CI file,
minus only the approved witness trigger line, equals actual-parent CI blob
`b9e71767b7d1fc3ffe0de7dc981be31f0ee2fc31`, preserving C4 and upstream PB-D.
Independent actual-GitHub merge/source/CI/release PASS receipt
`bc908f46d7984330d7fcc64d3e68f9be115e461a581ad8a4b084ce43aa75f0bb`
binds those GitHub facts; the independent reviewer separately read and
hash-verified the native postreceipt. These are source-release facts only.

Independent R5 review PASS receipt
`c9fa7849975e7ef97ce918e4eac9ccc44b231bbcad466dfa9875c22bd9ba6558`
reviewed the narrow source-only no-execution clarification below. Draft
clarification #8540 comment `6070802215` is explicitly **not adoption**.
The frozen pre-adoption revision R6 received external independent source/rules
review PASS from `/root/gmi_dependency_audit`, receipt SHA256 `c831dd818eb9bec065fc0346e7e04b55bc596a92ecd577d2b8d3e729514531f3`.
It binds cumulative patch SHA256 `1e679a3055f688a25b5db5bd387db8f1e96f69b7f4e89da50b85886070ad46f0`,
R5-to-R6 patch SHA256 `904b7164da6565e3f09f52d3c0aca8b5681c059c384740ccb35b469d5dc0905e`,
pre-adoption Markdown Git blob `1be5eadf5896f1ad6dd7d85c0baf613070bd5176` and
pre-adoption JSON Git blob `e5a61b3e51c399f8973b384de021ac781218011e`.
Formal adoption is #8540 comment `6071188794`, created_at `2026-10-08T23:38:32Z`.
This control-only delta binds those actual external facts without a recursive
self-hash. Generation observations and Phase-2/P3 acceptance remain unset.

If any frozen reviewed head changes, root must obtain explicit review of the
changed amendment/dependency binding before adoption. A newer head, a mergeable
flag or branch-name match is not a substitute. Resolve C4 and witness squash
SHAs before adoption and any evidence composition; do not guess them from their
PR heads. If overlapping source paths exist, the recorded expected parity is the
principal-reviewed integrated content, with each dependency's effect accounted for.

The adopted replacement window is **the first original `schedule`-event run of
`.github/workflows/daily.yml`, attempt 1, whose original workflow-run
`run_started_at` is strictly later than the designated formal adoption comment
`created_at`, and whose
actual effective producer checkout contains all three verified squash merges and
the original predecessors, and whose immutable workflow-definition revision
contains the reviewed witness upload wiring**. Workflow-definition eligibility
is independent of effective producer checkout ancestry: pulling newer source
inside an older queued workflow does not add an upload step to that workflow.
Record event SHA and the actual workflow-definition commit, path and Git blob
separately from the effective producer checkout. Inspect the immutable definition
for the reviewed step/output/upload wiring. A definition known to lack that wiring
is ineligible. Missing or unknown definition proof is UNKNOWN and cannot justify
skipping the run. Upload success is not an eligibility condition; after a run is
selected, a failed or missing upload holds that selected window without rollover.
The original predecessor set remains:

```text
0b1fe88730547207475ad3c04118d2e771a9b949  D2C
79b566f5c0ccba878ab963084a239993d3116aa9  D2D
192a46de8be8c694e47a1f2ab60b396d7dbb4f7f  original R0.1 predecessor
527243be5c03c79c016d8731179307f6ff03bf1d  D2C/D2D acceptance trace
ebe35dc916de5aae556371a5aa963c6692175c9c  PIN3 duplicate/rights correction
```

For the adoption cutoff, bind the original attempt-1 **workflow-run
`run_started_at`** and the explicitly designated formal #8540 adoption comment's
**`created_at`**, and require the former to be strictly greater. Workflow-run
`created_at` serves only to order candidates (then run ID as a deterministic
tie-break); it does not substitute for `run_started_at`. Engine, job, checkout,
producer or witness start never substitutes. A workflow started before or at
adoption is ineligible even if its engine or witness starts later. Missing or
ambiguous original-attempt `run_started_at` is UNKNOWN and cannot justify either
skipping the candidate or selecting it. Record engine/producer timing and actual
checkout separately. The designated formal adoption comment is `6071188794`,
created_at `2026-10-08T23:38:32Z`. No observed run time is set here.
The principal records the inspected candidate-run list and why each earlier run
was ineligible. Missing source evidence for an earlier candidate is UNKNOWN, not
permission to select a later convenient run. Freeze the selected run/attempt/job,
event SHA, workflow-definition commit/path/blob, effective source SHA, publication
commit, metadata hash and seven output hashes
before reader/test composition. Dispatches, reruns, manual graph rebuilds and
cross-run mixtures are ineligible. If the selected window fails or loses its
archive, hold it; selecting another window requires a new prospective ruling,
not silent rollover or cherry-picking a successful outcome.

**Narrow no-execution clarification (adopted prospective clarification only):** a
scheduled attempt is INELIGIBLE as conclusively gated off only when complete
immutable-workflow and same-run/attempt evidence proves that the existing
checkout-free `et_gate` completed successfully and actually published the literal
job output `run=false`, the engine's terminal conclusion was `skipped`, and no
engine steps, checkout or producer execution
occurred. Retain that proven disposition in the ordered candidate list; no
actual effective producer checkout or generation exists for that attempt.
This is positive proof of non-execution, not missing evidence. A cron/date
prediction, missing gate output, missing log or artifact, an errored gate (which
is fail-open), a canceled engine, or any started-engine/setup/producer failure does not establish
this exception. Incomplete or ambiguous proof remains UNKNOWN and cannot justify
skipping the candidate. Upload success is not an eligibility condition. A
failed/missing archive on an otherwise selected run remains HOLD with no rollover.
This clarification does not change the future-adoption boundary or select any
actual run.
A bare `run=false` log notice is insufficient: the notice precedes the
`GITHUB_OUTPUT` write, so successful output evidence must be proved separately.
Whole-workflow SUCCESS is not required for this exception. An unrelated overall
workflow failure or cancellation does not by itself change a fully proved
successful-gate/false-output/engine-skipped/no-execution disposition. Ambiguous,
canceled or errored gate or engine evidence cannot satisfy the exception; any
started engine remains outside it.
Failure to establish this exception does not override independently proved
ineligibility under the other unchanged R4 rules.

### Proof required on the one frozen replacement generation

Every original gate and its gating/non-gating classification remains, including
R0, R1.A–F, R2, R3, C1–C7 and the coverage/negative categories. Original command
recipes remain historical references; rebind their source/data inputs and record
actual new outputs. No historical rc, count, PASS or local fixture result is
copied into a replacement observation. Execute the original test/read obligations
with the selected effective code and the exact canonical published data, recording
any narrowly required committed-fixture hydration separately. Do not regenerate
the graph or write historical ledgers to obtain a reader result.

| Clause | Required replacement evidence |
|---|---|
| N1 | GitHub run/attempt/event/workflow and engine job identity; original schedule event, attempt 1; original workflow-run `run_started_at` strictly greater than the designated formal adoption comment `created_at`, both fields recorded and bound to that original attempt; workflow-run `created_at` orders candidates only, engine/job/producer/witness start never substitutes, and missing/ambiguous original-attempt start is UNKNOWN with no skipping or selection; first-eligible selection proof. Record event SHA and immutable workflow-definition commit/path/Git blob separately from the effective producer checkout; prove that definition contains the reviewed witness upload wiring. Known absent wiring is ineligible; missing/unknown definition proof is UNKNOWN, not permission to skip. Apply the narrow no-execution clarification only with complete immutable-workflow and same-run/attempt proof of successful complete checkout-free et_gate execution, actual literal run=false output, terminal engine skipped and no executed engine steps, checkout or producer; retain that ineligible disposition in the ordered list. A bare log notice, cron/date prediction, missing/ambiguous/canceled/errored gate or engine evidence, or any started-engine/setup/producer failure cannot establish that exception. Whole-workflow SUCCESS is not required; unrelated overall workflow failure/cancellation alone does not change a fully proved no-execution disposition. Upload success is not an eligibility condition; selected-run archive failure remains HOLD without rollover. Report overall job conclusion separately, including later unrelated failure. |
| N2 | Actual effective producer `git rev-parse HEAD` after checkout/pull and at witness start, distinguished from event `GITHUB_SHA` and immutable workflow-definition commit/path/Git blob; repository/run/attempt/job binding and retained source hashes. Verify each identity independently: a newer producer checkout or its retained daily.yml hash cannot prove an older queued workflow definition contained the upload step. |
| N3 | Recorded `git merge-base --is-ancestor` rc 0 for every original predecessor and each resolved exact-head squash against the actual producer checkout; post-merge source parity and no unreviewed reversal of prerequisite effects. |
| N4 | The producer's post-write marker final metadata `computed_at` and SHA256 equal the exact canonical published `data/theme_graph/_meta.json` clock and byte hash. Its run-bound archive copy must agree. Record the separate materialization clock. Bind publisher/data commit, commit timing, source ancestry and publication provenance to this run, not a later main snapshot. All seven archived output hashes must match that same canonical data publication. |
| N5 | Native graph build and native advisory guard each completed with retained rc 0 and valid elapsed-seconds evidence; their run-bound log groups/sidecars agree. Inspect both full retained band logs for warning/error annotations (raw and rendered forms) and logged failures; zero warning/error evidence is required. A caught builder exception or absent post-write marker is not success. Local strict rc 0 cannot replace native evidence. |
| N6 | Existing guard `--selftest` and `--strict` at the frozen source/data pair, both rc 0, without breach or INDETERMINATE; retain commands and outputs. |
| N7 | Re-run R-A8 edge-stability comparison and the GOLD/IBIT correction/PIT probes against the original baselines. Preserve correction beliefs and endpoints; reconcile any new structural rows individually to accepted C4 scope. Report measured totals/append counts, never copy historical totals or use count padding. Any unexplained protected-edge/history change holds the gate. |
| Q1 | Strict stored metadata matches the selected published metadata: nightly lane/mode, observed era, correct belief time and exact final metadata identity. Reconstruction is not observed proof. |
| Q2 | Native strict `RepositoryStore` readers succeed on nodes, lifecycle, edges and proposals; record actual measured populations and all negative categories. The old total 3,882 is historical, not a target after structural additions. |
| Q3 | Native identity resolutions: `co:us:NVDA` RESOLVED; `co:us:B` and `co:us:GOLD` DEFERRED_IDENTITY_EXCEPTION; `co:us:IBIT` ENTITY_TYPE_CONFLICT. |
| Q4 | Execute every explicit dated tuple below with native `compose_neighborhood`; all return `availability.state=OK`, with the specified presence, absence and future-belief exclusion. |

The seven output paths, relative to `data/theme_graph/`, are `nodes.parquet`,
`node_lifecycle.parquet`, `edges.parquet`, `evidence.parquet`,
`capability.parquet`, `identity_resolution.parquet` and
`probation/proposals.jsonl`. Retain exactly the native graph/guard `.log`, `.rc`
and `.sec` files plus final metadata from the fresh run-bound witness directory.
Check the witness manifest's repository, run, attempt, event, job, effective HEAD,
source hashes, unique witness ID, file hashes and capture errors against the
actual archive and canonical source/data bytes. At minimum the four retained
source hashes cover producer, contract guard, regional band and daily workflow;
record the remaining owned prerequisite-source parity separately. That retained
daily-workflow hash identifies the checkout copy, not necessarily the immutable
workflow definition used to schedule the job; N1/N2 require the latter separately.

**R1.A is unchanged:** zero failed identity tests; physical company nodes 2,807
and canonical company nodes 2,806 under the original frozen rule: subtract only
latest lifecycle `merged` duplicates, not every retired-like node. VMRK must stay
merged into live `co:us:EQR` under the original ratifier, absent from canonical
company enumeration and fresh identity materialization; no live VMRK membership
may escape suppression. GOLD/IBIT lifecycle, edge closure/refusal and PIT behavior
remain required. A changed company population requires explicit adjudication,
not silently relaxing these frozen company constraints. C4 structural nodes may
change the total-node count without changing that company law.

**R3.2 is unchanged:** evaluate every distinct evidence `source_ref`, report row
and distinct-reference denominators, and require `family_for_source_ref` None = 0.
Preserve the existing registry, internal-only Finviz/THS restrictions, refusal
categories and purpose-specific rights fences. A family mapping is not permission
for public display or a new source capability.

### Explicit Q4 tuples to freeze

These tuples are copied from the preserved deterministic GEN3 summary
(`gmi_state_gen3_summary_20261008.json`, SHA256
`11fcd1bcf0d75e3f470f8776736995ba583c48120e2a44a0b7b47a299e807e87`).
They make the prospective queries reproducible. They do **not** claim to recover
the unspecified a–e literals of the older acceptance record. Their earlier local
results are historical; each must be re-executed on the replacement generation.

| GEN3 explicit tuple | Node | `asof` | `knowledge_cutoff` | Required result in addition to OK |
|---|---|---|---|---|
| a | `basket:baskets:gold_miners` | `2025-12-01` | `2026-10-07` | `co:us:GOLD` present |
| b | `basket:baskets:gold_miners` | `2025-12-02` | `2026-10-07` | `co:us:GOLD` absent |
| c | `basket:baskets:gold_miners` | `2026-08-20` | `2026-08-20` | `co:us:GOLD` present; `future_beliefs_excluded >= 1` |
| d | `basket:baskets:crypto_rails` | `2026-08-20` | `2026-10-07` | `co:us:IBIT` absent; `etf:IBIT` present |
| e | `basket:baskets:crypto_rails` | `2026-10-07` | `2026-10-07` | `co:us:IBIT` absent; `etf:IBIT` present |

### Composition and retained holds

An archive missing, incomplete or inconsistent with its selected run/data is
UNKNOWN/incomplete evidence, never PASS. `capture_status=complete` means retained
evidence is available; it does not mean D2E acceptance. Any gating FAIL blocks
composition; missing gating proof holds it. Informational rows retain their
original classification and routing, including R1.X and R1.A-CI.

After all replacement observations are recorded, a reviewer independent of the
producer and evidence composer must perform P3 against the exact composed packet
and frozen identities. The principal then records the explicit Phase-2 ruling
and supporting receipt on #8540/the incumbent acceptance trace. **W3B stays held
until principal Phase-2 PASS**; release is not automated by an artifact, test or
merged implementation. This amendment does not create another state producer, store,
queue, service, workflow or carrier, and authorizes no E1 outcome look, performance
experiment or downstream scoring/trading capability.
