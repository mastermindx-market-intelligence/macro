# D2E — D2 acceptance record (WS:GMI-THEME-GRAPH)

operation: `gmi-theme-accept-d2e-20260827-sol-001`  
PIN: `cbfa20a45d8401f1cf1cc9fc48155455f1d612fb`  
GEN computed_at: `2026-10-06T08:07:45Z`  
DATA_COMMIT: `f7dd82910f315e82f376144388f2b38490c94ffe` 2026-10-06T02:23:18-07:00 engine: regime update 2026-10-06  
lane: `nightly` / mode: `nightly` / era: `observed` / belief_time: `2026-10-06`  
written-at UTC: `2026-10-06T11:34:00Z`

## §1 VERDICT

PHASE-1 VERDICT: HOLD:seat:multiple gate rows not PASS (see matrix)  
D2E VERDICT: HOLD:D2B identity owner:1168 identity_resolution biconditional breach on committed store

## §2 GATE MATRIX

| id | gate | clause / source | command (short; full text in Appendix A) | output tail (≤3 lines, verbatim) | verdict | owner | smallest repair packet |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R0.1 | Predecessor ancestry | commission §1 | `git merge-base --is-ancestor` ×3 | `0b1fe887 rc=0`<br>`79b566f5 rc=0`<br>`192a46de rc=0` | PASS | — | — |
| R0.2 | Agent OS acceptance trace | commission §1 | `git grep` agentos D2C/D2D accept | No line cites both D2C and D2D merged with `0b1fe887`/`79b566f5` | HOLD | seat | seat records D2C+D2D acceptance in WS:GMI-THEME-GRAPH |
| R0.3 | No overlapping D2E carrier | commission §2 | `gh pr list --search D2E` | Open hit #8324 blueprint only (not D2E acceptance) | PASS | — | — |
| R0.4 | Owner-action authority #8507 | commission §2 | `gh pr view 8507`; `git grep OWNER_ACTION…` | `state=MERGED`; mergeCommit=`cbfa20a45d8401f1cf1cc9fc48155455f1d612fb`; grep≥1 | PASS | — | — |
| R1.A | D2A identity resolution | D2A | `pytest` identity_resolution + identity | `65 passed, 56 skipped in 0.81s` | PASS | — | — |
| R1.B | D2B lifecycle hostile matrix | D2B | `pytest` test_theme_graph_lifecycle.py | `1 failed, 25 passed in 2.34s`<br>`tests/test_theme_graph_lifecycle.py:802` | FAIL | D2B identity owner | repair through the existing owner, re-run `TZ=UTC COLLECT_LANE=nightly PY -m pytest -p no:cacheprovider -q -rs tests/test_theme_graph_lifecycle.py` |
| R1.C | D2C PIT vintage | D2C #8432 | `pytest` basket PIT + membership + gmi_history | `143 passed, 14 warnings in 2.88s` | PASS | — | — |
| R1.D | D2D ontology/probation | D2D #8435 | `pytest` crosswalk + local_plane + structural + exposure | `575 passed, 1 skipped in 10.29s` | PASS | — | — |
| R1.E | Materialize + contracts | store contract | `pytest` materialize + contracts | `132 passed in 6.84s` | PASS | — | — |
| R1.F | Rights tests | rights gate | `pytest` rights_use + theme_sources + half_b docket | `3 failed, 46 passed in 1.03s`<br>`tests/test_market_ontology_half_b_rights_docket.py:140` | FAIL | rights registry owner (seat → Chairman ruling) | repair through the existing owner, re-run `TZ=UTC COLLECT_LANE=nightly PY -m pytest -p no:cacheprovider -q -rs tests/test_theme_graph_rights_use.py tests/test_theme_sources_registry.py tests/test_market_ontology_half_b_rights_docket.py` |
| R2 | Strict contract guard | CI guard | `PY -m scripts.check_theme_graph_contracts --selftest`; `--strict` | `selftest rc=0`<br>`strict rc=0`<br>`::warning title=theme graph contract breach::1168 identity_resolution…` | FAIL | D2B identity owner | repair identity_resolution biconditional on committed store; re-run `PY -m scripts.check_theme_graph_contracts --strict` |
| C1 | Lifecycle standing | D2B3 §3 | pandas `node_lifecycle.parquet` | GOLD retired 2025-12-02 identity_break; IBIT retired entity_type_conflict | PASS | — | — |
| C2 | GOLD edge closure | D2B3 §4 | pandas GOLD `MEMBER_OF` beliefs | latest `valid_to=2025-12-02`; 2 beliefs; current gold_miners excludes GOLD | PASS | — | — |
| C3 | IBIT refusal fence | D2B3 §6 | pandas IBIT + `_meta` refusals | annulled MEMBER_OF; IBIT refusal present; live `co:us:IBIT` MEMBER_OF=0 | PASS | — | — |
| C4 | Retired-consistency | D2B3 §12 | retired vs live MEMBER_OF | `violations: 0` | PASS | — | — |
| C5 | Identity sidecar R-A2 | D2B3 §13 | `identity_resolution.parquet` NEWEST | US 1237: RESOLVED 1211, DEFERRED `{B}`, ETC 0; all-scope matches `_meta` | PASS | — | — |
| C6 | Generation provenance P1 | receipt timing | `merge-base` vs DATA_COMMIT | `0b1fe887 rc=1`; `79b566f5 rc=1`; seat fact: gen predates D2C/D2D merges | HOLD | seat | natural receipt on a main containing D2C+D2D pending — Phase 2 |
| C7 | Nightly `_meta` history | informational | `git log -5` `_meta.json` | 5/5: `node_lifecycle>=2` and IBIT refusal | PASS | — | — |
| R3.1 | Registry table | rights gate #2 | `config/theme_sources.yml` | `finviz_themes`/`ths_concepts` `internal_only`; all families have `rights_class` | PASS | — | — |
| R3.2 | Source-ref census | display tier | `family_for_source_ref` over censused columns | `distinct=5900`; `none=5885` (as-of GEN) | FAIL | rights registry owner (seat → Chairman ruling) | mint registry family row / SOURCE_PREFIX_FAMILY entry for unmapped prefix (do not edit registry here) |
| R3.3 | Spot checks | #8499 | two `family_for_source_ref` calls | probation `#x` → `mastermind_curated`; `site/factordata/us_standouts.json` → `None` | FAIL | rights registry owner (seat → Chairman ruling) | mint a registry family row / SOURCE_PREFIX_FAMILY entry for `site/factordata/us_standouts.json` |
| V1 | Node prefix census | coverage | `nodes.parquet` | total=3882; co:us=1239, co:cn=1021, ltheme=644, basket=358, … | PASS | — | — |
| V2 | Capability generations | coverage | `capability.parquet` | NEWEST gen 643 (505+138); `_meta.counts.capability=644` vs sum 643 | HOLD | seat | reconcile `counts.capability` 644 vs newest-generation 643 |
| V3 | Identity generations | coverage | sidecar NEWEST vs `_meta` | NEWEST rows=2805; file total `_meta` 2807 (+2 prior-gen rows) | PASS | — | — |
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

**C5 — identity sidecar (NEWEST `computed_at=2026-10-06T08:07:42Z`):** US-scope (`market_scope==us`, no separate company-only column beyond that filter) denominator 1237 — RESOLVED 1211, NOT_IN_MASTER 25, DEFERRED_IDENTITY_EXCEPTION 1 (`B`), ENTITY_TYPE_CONFLICT 0. All-scope NEWEST sums match `_meta.identity_resolution_state_counts`.

**C6 — SEAT-PROVIDED:** generation `2026-10-06T08:07:45Z` at data commit `f7dd82910f31` pushed by `daily.yml` run `37402815092` (engine job failed after push); predates D2C/D2D squash merges on 2026-10-06. DATA_COMMIT is not a descendant of squash commits `0b1fe887` / `79b566f5` (`merge-base --is-ancestor` rc=1 for both).

## §4 Rights tables

**R3.1 families (`config/theme_sources.yml`, updated 2026-10-06):**

| family | rights_class |
| --- | --- |
| mastermind_curated | direct_display_ok |
| finviz_themes | internal_only |
| ths_concepts | internal_only |

**R3.2 census bounds (column names containing `source`, `evidence_ref`, or `provenance`):** `nodes.provenance`, `nodes.source_meta`, `edges.source_class`, `edges.date_provenance`, `edges.evidence_refs`, `evidence.source_ref`, `identity_resolution.source_native_symbol`, `identity_resolution.source_receipts`, probation jsonl keys matching the same substrings.

| family | distinct refs / 5900 | row hits / 388624 |
| --- | --- | --- |
| mastermind_curated | 6 | 6 |
| finviz_themes | 2 | 2 |
| ths_concepts | 7 | 12 |
| None (unmapped) | 5885 | (remainder) |

**R3.3 spot checks:** `data/theme_graph/probation/relation_events.v2.jsonl#x` → `mastermind_curated`; `site/factordata/us_standouts.json` → `None`.

## §5 Coverage census tables (as-of `2026-10-06T08:07:45Z`)

**V1 nodes (denominator 3882):** co:us 1239, co:cn 1021, ltheme 644, basket 358, co:ca 167, co:intl 233, co:hk 147, etf 55, theme 18.

**V2 capability:** 52 generations in file; NEWEST generation rows 643 = measurement_candidate 505 + semantic_only 138. `_meta.capability_counts` sums to 643; `_meta.counts.capability` reports 644 (+1 vs newest generation — unreconciled).

**V3 identity:** NEWEST generation rows 2805; state sum 2805. `_meta.counts.identity_resolution` 2807 includes 2 rows from prior `computed_at` generations still in the parquet file.

**V4 mapping:** `local_plane.ths.concepts` 375; crosswalk `ths_codes_mapped` 61 + `ths_codes_unknown` 0 = 61; `ths_unmapped_concept_count` 314; `unknown_ths_codes` []; `local_plane.ths.unresolved_concept_names` 0.

**V5 probation:** `proposals.jsonl` field `status` — total 236 lines: proposed 234, rejected 2.

**V6 PIT / era:** `_meta.per_suite.*.membership_published_at` and seed constants recorded per suite (see `_meta.json`). `edges.parquet` era: observed 12423, reconstruction 12677 (reconstruction-era rows are not observed proof).

**V7 negatives:** `company_mint_refusals` 1; `local_plane.finviz.company_resolution.refused` 0; `dropped_adjacent_duplicates` 1 date; suite `skipped_unidentifiable` all empty lists; sidecar NOT_IN_MASTER 195; UNSUPPORTED_MARKET 233.

## §6 PHASE 2 — natural nightly receipt: PENDING (appended in round 2 on this PR)

Phase 2 will re-run commission steps 6–7 on a natural nightly generation baked from main containing accepted D2C+D2D merges, append receipt rows to this carrier, and lift C6 / PHASE-1 verdict when measured.

## Appendix A — commands and probe (output tail ≤25 lines each)

**S0 PIN**

```
$ git rev-parse HEAD
cbfa20a45d8401f1cf1cc9fc48155455f1d612fb
```

**S0 materialize store**

```
$ git sparse-checkout add '/data/theme_graph/'
$ git ls-files data/theme_graph | wc -l
8
$ git status --porcelain -- data/
(empty)
```

**S0 GEN / DATA_COMMIT**

```
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
$ TZ=UTC COLLECT_LANE=nightly PY -m pytest -p no:cacheprovider -q -rs tests/test_theme_graph_identity_resolution.py tests/test_theme_graph_identity.py
...
65 passed, 56 skipped in 0.81s
```

**R1.B**

```
$ TZ=UTC COLLECT_LANE=nightly PY -m pytest -p no:cacheprovider -q -rs tests/test_theme_graph_lifecycle.py
...
1 failed, 25 passed in 2.34s
```

**R1.C**

```
$ TZ=UTC COLLECT_LANE=nightly PY -m pytest -p no:cacheprovider -q -rs tests/test_basket_membership_pit.py tests/test_us_basket_membership_pit.py tests/test_theme_graph_membership_lifecycle.py tests/test_gmi_history_integrity.py
143 passed, 14 warnings in 2.88s
```

**R1.D**

```
$ unset GMI_STATE_OWNER_WORKSPACE
$ TZ=UTC COLLECT_LANE=nightly PY -m pytest -p no:cacheprovider -q -rs tests/test_theme_graph_crosswalk.py tests/test_theme_graph_local_plane.py tests/test_theme_graph_structural_owner_binding.py tests/test_market_ontology_exposure_map.py
575 passed, 1 skipped in 10.29s
```

**R1.E**

```
$ TZ=UTC COLLECT_LANE=nightly PY -m pytest -p no:cacheprovider -q -rs tests/test_theme_graph_materialize.py tests/test_theme_graph_contracts.py
132 passed in 6.84s
```

**R1.F**

```
$ TZ=UTC COLLECT_LANE=nightly PY -m pytest -p no:cacheprovider -q -rs tests/test_theme_graph_rights_use.py tests/test_theme_sources_registry.py tests/test_market_ontology_half_b_rights_docket.py
3 failed, 46 passed in 1.03s
```

**R2**

```
$ PY -m scripts.check_theme_graph_contracts --selftest
check_theme_graph_contracts selftest: OK
$ echo rc=$?
rc=0
$ PY -m scripts.check_theme_graph_contracts --strict
::notice title=theme graph — licensing snapshots — designed::3 evidence row(s) carry mint-time licensing...
::notice title=theme graph — identity resolution census::company nodes=2807, projection rows=2807, by state={...}
::warning title=theme graph contract breach::1168 identity_resolution row(s) violate the state<->ids biconditional (first: 'co:cn:000001.SZ') — ...
$ echo rc=$?
rc=0
```

**D2B3 probe heredoc (verbatim structure; full output in §3 / `/tmp/d2b3_full.out` capture)**

```
PY - <<'PYEOF'
import json
import pandas as pd
from pathlib import Path
BASE = Path("data/theme_graph")
# ... reads node_lifecycle, edges, identity_resolution; prints C1–C5 measurements ...
PYEOF
```

Probe tail:

```
violations: 0
US resolution_state counts: {'DEFERRED_IDENTITY_EXCEPTION': 1, 'NOT_IN_MASTER': 25, 'RESOLVED': 1211} denom= 1237
all-scope NEWEST sum= 2805
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
