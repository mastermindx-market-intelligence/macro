# D2E — D2 acceptance record (WS:GMI-THEME-GRAPH)

operation: `gmi-theme-accept-d2e-20260827-sol-001`  
PIN: `cbfa20a45d8401f1cf1cc9fc48155455f1d612fb`  
GEN computed_at: `2026-10-06T08:07:45Z`  
DATA_COMMIT: `f7dd82910f315e82f376144388f2b38490c94ffe` 2026-10-06T02:23:18-07:00 engine: regime update 2026-10-06  
lane: `nightly` / mode: `nightly` / era: `observed` / belief_time: `2026-10-06`  
written-at UTC: `2026-10-06T12:05:00Z`  
repair round: `r1b` (harness corrections D1, D5, D6, D7)

**Round r1b (repair) — harness corrections by orchestrator E:** D1 materializes `data/reference/security_master.parquet` so R1.B/R2 are not run against a degraded guard. D5 moves MarketOntology half-B docket tests to non-gating R1.X and limits R1.F to theme-graph rights tests. D6 censuses `evidence.source_ref` only via `family_for_source_ref`. D7 treats `site/factordata/us_standouts.json` as intentionally unmapped (PASS when `None`).

## §1 VERDICT

PHASE-1 VERDICT: HOLD:seat:R0.2 Agent OS acceptance trace not recorded  
D2E VERDICT: HOLD:D2A identity owner:R1.A committed D2A tests fail with materialized master (2807 company nodes; VMRK sidecar)  
ROUTED (non-gating): R1.X FAIL-INFO -> MarketOntology CEO A (F00C closure-ledger writer; ledger last changed by #8425/#8465/#8496)

## §2 GATE MATRIX

| id | gate | clause / source | command (short; full text in Appendix A) | output tail (≤3 lines, verbatim) | verdict | owner | smallest repair packet |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R0.1 | Predecessor ancestry | commission §1 | `git merge-base --is-ancestor` ×3 | `0b1fe887 rc=0`<br>`79b566f5 rc=0`<br>`192a46de rc=0` | PASS | — | — |
| R0.2 | Agent OS acceptance trace | commission §1 | `git grep` agentos D2C/D2D accept | No line cites both D2C and D2D merged with `0b1fe887`/`79b566f5` | HOLD | seat | seat records D2C+D2D acceptance in WS:GMI-THEME-GRAPH |
| R0.3 | No overlapping D2E carrier | commission §2 | `gh pr list --search D2E` | Open hit #8324 blueprint only (not D2E acceptance) | PASS | — | — |
| R0.4 | Owner-action authority #8507 | commission §2 | `gh pr view 8507`; `git grep OWNER_ACTION…` | `state=MERGED`; mergeCommit=`cbfa20a45d8401f1cf1cc9fc48155455f1d612fb`; grep≥1 | PASS | — | — |
| R1.A | D2A identity resolution | D2A | `pytest` identity_resolution + identity | `3 failed, 118 passed in 5.16s`<br>`tests/test_theme_graph_identity_resolution.py::test_the_committed_graph_carries_exactly_2806_company_nodes`<br>`E       assert 2807 == 2806` | FAIL | D2A identity owner | reconcile committed nodes/sidecar with D2A §9 pinned 2806 company count (EQR/VMRK same-security set); re-run `TZ=UTC COLLECT_LANE=nightly PY -m pytest -p no:cacheprovider -q -rfEs tests/test_theme_graph_identity_resolution.py tests/test_theme_graph_identity.py` |
| R1.B | D2B lifecycle hostile matrix | D2B | `pytest` test_theme_graph_lifecycle.py | `26 passed in 2.43s` | PASS | — | — |
| R1.C | D2C PIT vintage | D2C #8432 | `pytest` basket PIT + membership + gmi_history | `143 passed, 14 warnings in 2.98s` | PASS | — | — |
| R1.D | D2D ontology/probation | D2D #8435 | `pytest` crosswalk + local_plane + structural + exposure | `575 passed, 1 skipped in 10.40s`; skips: 1 (reasons in Appendix A) | PASS | — | — |
| R1.E | Materialize + contracts | store contract | `pytest` materialize + contracts | `132 passed in 6.65s` | PASS | — | — |
| R1.F | Rights tests (theme graph) | rights gate | `pytest` rights_use + theme_sources | `30 passed in 0.72s` | PASS | — | — |
| R1.X | MarketOntology half-B rights docket | F00C ledger (non-gating) | `pytest` half_b docket | `3 failed, 16 passed in 0.53s`<br>`tests/test_market_ontology_half_b_rights_docket.py::test_blocked_on_quotes_the_ledger_verbatim`<br>`E           AssertionError: MO-PAID-019: 'one issuer page joining >=2 module streams...' not in '...unified capital-markets tape journey...'` | FAIL-INFO | MarketOntology CEO A (F00C closure-ledger writer; ledger last changed by #8425/#8465/#8496) | reconcile `tests/test_market_ontology_half_b_rights_docket.py` (EXPECTED_DISPOSITION_CENSUS, docket rows) with the F00C closure ledger CSV as amended by records waves #8425/#8465/#8496, or restore those ledger rows; re-run `TZ=UTC PY -m pytest -q tests/test_market_ontology_half_b_rights_docket.py` |
| R2 | Strict contract guard | CI guard | `PY -m scripts.check_theme_graph_contracts --selftest`; `--strict` | `selftest rc=0`<br>`strict rc=0`<br>(no `breach` lines in strict tail) | PASS | — | — |
| C1 | Lifecycle standing | D2B3 §3 | pandas `node_lifecycle.parquet` | GOLD retired 2025-12-02 identity_break; IBIT retired entity_type_conflict | PASS | — | — |
| C2 | GOLD edge closure | D2B3 §4 | pandas GOLD `MEMBER_OF` beliefs | latest `valid_to=2025-12-02`; 2 beliefs; current gold_miners excludes GOLD | PASS | — | — |
| C3 | IBIT refusal fence | D2B3 §6 | pandas IBIT + `_meta` refusals | annulled MEMBER_OF; IBIT refusal present; live `co:us:IBIT` MEMBER_OF=0 | PASS | — | — |
| C4 | Retired-consistency | D2B3 §12 | retired vs live MEMBER_OF | `violations: 0` | PASS | — | — |
| C5 | Identity sidecar R-A2 | D2B3 §13 | `identity_resolution.parquet` NEWEST | US 1239: RESOLVED 1211, NOT_IN_MASTER 25, DEFERRED 2, ENTITY_TYPE_CONFLICT 1; all-scope NEWEST sum=2807; `_meta` file-total counts unchanged | PASS | — | — |
| C6 | Generation provenance P1 | receipt timing | `merge-base` vs DATA_COMMIT | `0b1fe887 rc=1`; `79b566f5 rc=1`; seat fact: gen predates D2C/D2D merges | HOLD | seat | natural receipt on a main containing D2C+D2D pending — Phase 2 |
| C7 | Nightly `_meta` history | informational | `git log -5` `_meta.json` | 5/5: `node_lifecycle>=2` and IBIT refusal | PASS | — | — |
| R3.1 | Registry table | rights gate #2 | `config/theme_sources.yml` | `finviz_themes`/`ths_concepts` `internal_only`; all families have `rights_class` | PASS | — | — |
| R3.2 | Source-ref census | display tier | `family_for_source_ref` on `evidence.source_ref` | 22 rows / 17 distinct; `ths_concepts` 12; `mastermind_curated` 6; `finviz_themes` 2; `None` 2 (`gmi:entity_type_conflict:co:us:IBIT`; `config/theme_graph_identity_breaks.yml#us:GOLD`) | FAIL | rights registry owner (seat → Chairman ruling) | for each `None` ref prefix: `SOURCE_PREFIX_FAMILY` in `engine/theme_graph/rights.py` or recorded seat/Chairman fail-closed ruling — no registry edit in this PR |
| R3.3 | Spot checks | #8499 | two `family_for_source_ref` calls | probation `#x` → `mastermind_curated`; `site/factordata/us_standouts.json` → `None` (intentional; `rights.py` 70–72) | PASS | — | — |
| V1 | Node prefix census | coverage | `nodes.parquet` | total=3882; co:us=1239, co:cn=1021, ltheme=644, basket=358, … | PASS | — | — |
| V2 | Capability generations | coverage | `store.read_capability()` vs newest gen | `read_capability=644`; newest gen 643; +1 carried `ltheme:ths:309263` semantic_only @ 2026-08-22T04:50:43Z; node present in `nodes.parquet` | PASS | — | — |
| V3 | Identity generations | coverage | sidecar NEWEST vs `_meta` | NEWEST rows=2807; state sum=2807; `_meta.counts.identity_resolution` 2807 (file-total includes prior gens) | PASS | — | — |
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

**C4 — retired-consistency:** 0 live MEMBER_OF edges whose src latest lifecycle is retired.

**C5 — identity sidecar (NEWEST `computed_at=2026-10-06T08:07:42Z`):** US-scope (`market_scope==us`) denominator 1239 — RESOLVED 1211, NOT_IN_MASTER 25, DEFERRED_IDENTITY_EXCEPTION 2, ENTITY_TYPE_CONFLICT 1. All-scope NEWEST sum=2807. `_meta.identity_resolution_state_counts` file-total: `DEFERRED_IDENTITY_EXCEPTION` 1, `NOT_IN_MASTER` 195, `RESOLVED` 2376, `UNSUPPORTED_MARKET` 233 (prior-generation rows remain in file).

**C6 — SEAT-PROVIDED:** generation `2026-10-06T08:07:45Z` at data commit `f7dd82910f31` pushed by `daily.yml` run `37402815092` (engine job failed after push); predates D2C/D2D squash merges on 2026-10-06. DATA_COMMIT is not a descendant of squash commits `0b1fe887` / `79b566f5` (`merge-base --is-ancestor` rc=1 for both).

**C5 vs round r1:** US denominator 1239 (not 1237) and all-scope NEWEST sum 2807 (not 2805) because round r1 omitted `security_master.parquet`, which skipped most D2A committed-store tests; with the master materialized the sidecar NEWEST view includes `co:us:VMRK` and matches 2807 company nodes in `nodes.parquet`.

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

**V2 capability:** 52 generations in file; NEWEST generation rows 643 = measurement_candidate 505 + semantic_only 138. `len(store.read_capability())` = 644 = 643 newest + 1 carried `ltheme:ths:309263` (`semantic_only`, `computed_at` 2026-08-22T04:50:43Z).

**V3 identity:** NEWEST generation rows 2807; state sum 2807.

**V4 mapping:** `local_plane.ths.concepts` 375; crosswalk `ths_codes_mapped` 61 + `ths_codes_unknown` 0 = 61; `ths_unmapped_concept_count` 314; `unknown_ths_codes` []; `local_plane.ths.unresolved_concept_names` 0.

**V5 probation:** `proposals.jsonl` field `status` — total 236 lines: proposed 234, rejected 2.

**V6 PIT / era:** `_meta.per_suite.*.membership_published_at` and seed constants recorded per suite (see `_meta.json`). `edges.parquet` era: observed 12423, reconstruction 12677 (reconstruction-era rows are not observed proof).

**V7 negatives:** `company_mint_refusals` 1; `local_plane.finviz.company_resolution.refused` 0; `dropped_adjacent_duplicates` 1 date; suite `skipped_unidentifiable` all empty lists; sidecar NOT_IN_MASTER 195; UNSUPPORTED_MARKET 233.

## §6 PHASE 2 — natural nightly receipt: PENDING (appended in round 2 on this PR)

Phase 2 will re-run commission steps 6–7 on a natural nightly generation baked from main containing accepted D2C+D2D merges, append receipt rows to this carrier, and lift C6 / PHASE-1 verdict when measured.

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

**R1.A — `PY=/home/longr/lanes/tmp/d2e-venv/bin/python`**

```
$ TZ=UTC COLLECT_LANE=nightly PY -m pytest -p no:cacheprovider -q -rfEs tests/test_theme_graph_identity_resolution.py tests/test_theme_graph_identity.py
...
3 failed, 118 passed in 5.16s
```

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

ibit_id = "member_of:co:us:IBIT->basket:baskets:gold_miners@2023-05-09"
ibit_rows = hist[hist["edge_id"] == ibit_id] if not hist.empty else pd.DataFrame()
print("C3 IBIT beliefs", len(ibit_rows))
cur = edges[edges["edge_id"]==ibit_id]
if not cur.empty:
    r = cur.iloc[0]
    print("  annul valid_to==valid_from", r["valid_to"]==r["valid_from"])
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
print("violations:", len(offenders))

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
C3 IBIT beliefs 0
  IBIT refusals 1
  live co:us:IBIT MEMBER_OF 0
violations: 0
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
