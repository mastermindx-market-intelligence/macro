# D2E pre-acceptance census — 2026-10-05 (read-only)

**WS:GMI-THEME-GRAPH** Wave E / D2E prep (`gmi-theme-accept-d2e-20260827-sol-001`).  
**Carrier branch:** `claude/gmi-d2e-precensus-20261005` (report only; no code changes).  
**Scratch composition:** local detached merge (never pushed).

---

## C0

### C0(a) — carrier tip SHAs

```text
$ git fetch origin main claude/gmi-d2-membership-ontology-lifecycle-20261004-astra-001 claude/gmi-d2d-structural-owner-binding-20261004-astra-001
origin/main:  20eb503a09aef8bc2ccc8945f1ea140bdc9aeace
#8432 head:   54d17ebcb1c11471fffbbdea6888f97db6c9fbbb  (matches expected)
#8435 head:   7429a3e5f6da9b66787ead24119a238a2a36858d  (matches expected)
```

### C0(b) — scratch composition

```text
$ git worktree add --detach ../d2e-scratch origin/main
$ cd ../d2e-scratch && git merge --no-edit 54d17ebcb1c11471fffbbdea6888f97db6c9fbbb
Merge made by the 'ort' strategy. (12 files, D2C membership lifecycle)

$ git merge --no-edit 7429a3e5f6da9b66787ead24119a238a2a36858d
CONFLICT (content): Merge conflict in .github/ci/legacy-jobs.yml
$ git merge --abort

scratch HEAD after #8432 only: a58905e0da4de0f191acb81c54c1fda4317c2e27
```

**Deviation:** census executed on **main + #8432** only; **#8435 not composable** without resolving `legacy-jobs.yml` (both carriers touched the same job block).

### C0(c) — D2B3 natural proof pointer

```text
$ grep -rn "D2B3" research/ agentos/ docs/ --include='*.md' | head
research/theme_graph/THEME_GRAPH_END_TO_END_COMPLETION_FREEZE_2026-08-27.md:136: ... Reconcile D2B3 natural proof ...
research/prophet_v4/d2/D2B3_FROZEN_CONTRACT_2026-08-21.md:1:# V4-D2B3 — GMI Identity Correction Lineage ...
agentos/workstreams/WS-GMI-THEME-GRAPH.md:74: ... Reconcile D2B3 natural proof ...
docs/superpowers/plans/2026-08-28-gmi-theme-f04-end-to-end-completion.md:116: ... Reconcile D2B3 natural proof against its exact acceptance clauses ...
```

**Natural proof (what D2E must reconcile):** post-correction **natural GMI nightly** survival graded against `research/prophet_v4/d2/D2B3_FROZEN_CONTRACT_2026-08-21.md` (AMENDMENT R-A7: US identity_resolution counts, GOLD/IBIT lifecycle, `_meta.json` / sidecar law). Implementation handoff: `agentos/handoffs/PROPHET-US-V4-RECOVERY-2026-08-22-D2B3-IMPL.md` — **natural nightly on real production artifacts was explicitly unverified at ship**; receipt anchor on **canonical main** is `data/theme_graph/_meta.json` (`computed_at` **2026-10-05T07:55:06Z**, `lane`: nightly) plus `identity_resolution.parquet` / `node_lifecycle.parquet` listed under `data/theme_graph/` on GitHub main.

---

## T1 — unit evidence (scratch: `a58905e0da`)

**Command (spec):**

```text
TZ=UTC python -m pytest tests/test_basket_membership_pit.py tests/test_theme_graph_local_plane.py \
  tests/test_theme_graph_materialize.py tests/test_theme_graph_membership_lifecycle.py \
  tests/test_theme_graph_structural_owner_binding.py tests/test_theme_graph_rights.py \
  -q -p no:cacheprovider
```

**Host note:** `python` → `python3` on this runner; deps via worktree-local `.venv-census` (not committed).

**Result on scratch (adjusted for missing #8435-only files):**

```text
$ TZ=UTC .venv-census/bin/python -m pytest tests/test_basket_membership_pit.py \
  tests/test_theme_graph_local_plane.py tests/test_theme_graph_materialize.py \
  tests/test_theme_graph_membership_lifecycle.py tests/test_theme_sources_registry.py \
  -q -p no:cacheprovider
524 passed, 1 skipped in 11.11s
```

**Missing on scratch (absent until #8435 merges):** `tests/test_theme_graph_structural_owner_binding.py`, `tests/test_theme_graph_rights.py`, `tests/test_theme_graph_rights_use.py` (not present on main or #8432).

---

## T2 — contracts guard (scratch)

```text
$ python3 -m scripts.check_theme_graph_contracts --help
  --strict    return 1 on a breach (CI); default is advisory rc 0
  --selftest  rebuild each incident as a fixture and prove the guard sees it

$ python3 -m scripts.check_theme_graph_contracts
::notice title=theme graph indeterminate::theme graph store incomplete at .../data/theme_graph (missing: nodes, edges, evidence) — pre-first-run and sparse checkouts are INDETERMINATE, never a breach
rc=0

$ python3 -m scripts.check_theme_graph_contracts --strict
(same INDETERMINATE notice)
strict_rc=0

$ python3 -m scripts.check_theme_graph_contracts --selftest
check_theme_graph_contracts selftest: OK
```

Sparse worktree has no `data/theme_graph` parquets; guard correctly reports **INDETERMINATE**, not breach. CI on GitHub runs `--strict` against the **committed store** on full checkout (`legacy-jobs.yml` step “theme graph contract guard against the committed store”).

---

## T3 — coverage / eligibility census

**Reporters (read-only):**

| Module / script | Role |
|-----------------|------|
| `engine/theme_graph/capability.py` | `measurement_candidate` vs `semantic_only` (MIN_LIVE_MEMBERS=3); side-car `capability.parquet` |
| `engine/theme_graph/membership_evidence.py` | MEMBER_OF evidence from proposal-review exports (no graph discovery) |
| `engine/theme_graph/probation.py` | Typed proposal kinds + `STATUSES` `{proposed, ratified, rejected}`; relation events v2 schema on #8432 |
| `engine/theme_graph/ontology_inventory.py` | Read-only concept inventory; mapping/curation filters |
| `scripts/theme_coverage_gaps.py` | Case A co-occurrence + case D breadth; optional `--propose` → probation queue |

**`data/theme_graph/` on `origin/main` (gh api contents):**

| name | size | sha (short) |
|------|------|-------------|
| _meta.json | 3482 | 523c8505… |
| nodes.parquet | 137781 | 2dcac135… |
| edges.parquet | 292939 | 4b53aafd… |
| evidence.parquet | 8381 | 8b414dbb… |
| capability.parquet | 17952 | 2df59fd5… |
| identity_resolution.parquet | 207858 | 29dde1f6… |
| node_lifecycle.parquet | 8049 | 2a7219af… |
| probation/ | 0 (dir) | 5a4af8e1… |

**One-line findings:**

- **Node counts by kind:** from main `_meta.json`: **3882** nodes; capability split **505** `measurement_candidate` / **138** `semantic_only` (`python3` decode of gh api `_meta.json`).
- **MEMBER_OF / lawful null:** materialize + membership lifecycle tests on scratch pin bitemporal MEMBER_OF intervals and null `valid_to` semantics (`524 passed` includes `test_theme_graph_materialize.py`, `test_theme_graph_membership_lifecycle.py`).
- **Probation typing:** `probation.STATUSES` and `probation_relation_event.v2` contract shipped on #8432; local plane tests include `test_probation_decision_clock_contract_is_fail_closed`.
- **Many-to-many:** PIT store tests (`test_basket_membership_pit.py`) + materialize THS/CN paths preserve multiple intervals per edge id (scratch green).
- **Coverage-delta hooks:** `scripts/theme_coverage_gaps.py --source-artifact site/factordata/us_standouts.json#buy` documents provenance; on empty store: `::notice title=theme coverage gaps::theme graph store is empty — run scripts.build_theme_graph first`.

---

## T4 — rights / display tier

**Registry:** `config/theme_sources.yml` + `engine/theme_graph/rights.py`.

| Family | rights_class | display tier (emission) | emission_allowed |
|--------|--------------|-------------------------|------------------|
| mastermind_curated | direct_display_ok | public display permitted | yes |
| finviz_themes | unresolved | refused at gate (internal compute OK) | no |
| ths_concepts | unresolved | refused at gate | no |

**`family_for_source_ref` unmapped on scratch code paths:**

- `data/theme_graph/probation/relation_events.v2.jsonl#` (prefix table has no probation path) — **not** a `theme_sources.yml` family row issue; needs prefix map or evidence ref convention decision before strict guard on relation events.
- **`site/factordata/us_standouts.json`:** not an evidence `source_ref` in `local_sources.py` / `materialize.py`; used as **coverage-gap provenance** (`theme_coverage_gaps.py --source-artifact`). Prophet board artifact — **no GMI source family** unless a future emission path cites it; treat as **rights-unresolved for GMI structure** until registry/Chairman rules otherwise.

---

## T5 — ontology-action authority

```text
$ grep -r OWNER_ACTION_AUTHORITY_UNAVAILABLE engine/ scripts/ tests/ config/
(no matches on scratch composition main+#8432)
```

**Structural owner binding (#8435, not on scratch):** `engine/theme_graph/structural_navigation.py` loads **`config/theme_crosswalk.yml`** via `load_structural_owner()` (`unmapped_baskets` / `us_sector_*` keys). Wiring is present on main for read-only sector context; **#8435** adds `tests/test_theme_graph_structural_owner_binding.py` and a dedicated CI pytest step on its branch (blocked from this composition by merge conflict).

---

## T6 — strict graph guards (CI steps on scratch `legacy-jobs.yml`)

**Job steps whose names contain “theme graph” or “GMI” (name only):**

| Step name | pytest target |
|-----------|----------------|
| GMI history integrity and refusal before publication | `test_gmi_history_integrity.py`, `test_basket_membership_pit.py`, `test_theme_graph_membership_lifecycle.py`, … |
| GMI local and canonical state contract and cutoff reader | `test_theme_graph_state.py` |
| theme graph — permanent node identity and ratified epochs | `test_theme_graph_identity.py` |
| theme graph — bitemporal materialization from the membership documents | `test_theme_graph_materialize.py` |
| theme graph — contract guard (incident fixtures + annotation shape) | `test_theme_graph_contracts.py` |
| theme graph — V4-D2B3 node lifecycle correction lineage | `test_theme_graph_lifecycle.py` |
| theme graph — crosswalk v3 additive integrity | `test_theme_graph_crosswalk.py` |
| theme graph — V4-D2A identity-resolution bridge | `test_theme_graph_identity_resolution.py` |
| theme graph — W3A local-theme plane | `test_theme_graph_local_plane.py` |
| theme graph — source-rights registry shape + F20 grandfather pin | `test_theme_sources_registry.py` |
| market ontology — GMI exposure composer | `test_market_ontology_exposure_map.py` |
| theme graph contract guard against the committed store | `scripts.check_theme_graph_contracts --selftest` + `--strict` |

**`test -f` on scratch:** all listed test modules **exist** except **`tests/test_theme_graph_structural_owner_binding.py`** (on #8435 branch only; CI step exists there, not on scratch HEAD).

---

## DEFECTS (report-only)

| # | Defect | Owner |
|---|--------|-------|
| 1 | `main` + #8432 + #8435 **do not merge cleanly** (`legacy-jobs.yml` conflict) — full D2E composition blocked | #8435 / D2D carrier |
| 2 | `test_theme_graph_structural_owner_binding.py` missing until #8435 lands | #8435 |
| 3 | D2B3 **natural proof reconciliation** not executed in this read-only lane (needs clause-by-clause grade vs latest nightly `_meta.json` / identity_resolution) | WS:PROPHET-US-V4-RECOVERY / Sol D2E acceptance |
| 4 | D2E **dependency hold**: D2C (#8432) and D2D (#8435) not Sol-accepted on main | Sol / Chairman |

---

## DECISIONS REQUIRED (Chairman / Sol last)

1. **finviz_themes** — `unresolved` → approve `derived_display_ok` vs keep `internal_only` for new GMI emissions (registry notes W6 escalation).
2. **ths_concepts** — same decision bundled with finviz per W3A registry review rows.
3. **site/factordata/us_standouts.json** — if any GMI coverage/eligibility reporter treats Prophet board rows as a source family, mint registry row + rights class or explicitly exclude from GMI emission scope (today: provenance string only).
4. **probation relation_events `source_ref` prefix** — map `data/theme_graph/probation/...` in `SOURCE_PREFIX_FAMILY` or forbid as evidence refs (guard alignment).
5. **Release D2E execution** — Sol acceptance of **#8432** and **#8435** on main after resolving `legacy-jobs.yml` merge.

---

## HONEST SUMMARY

Once Sol releases D2C+D2D, D2E can run acceptance on a **merged** main with membership lifecycle + structural owner tests and a single `legacy-jobs.yml` story. **Today:** carrier SHAs match spec; **scratch is main+#8432 only**; unit tests green for that slice (**524 passed**); contract guard **INDETERMINATE** on sparse host, **selftest OK**; main natural store shows **3882** nodes and nightly `computed_at` **2026-10-05T07:55:06Z**. **Still missing:** clean three-way composition, D2B3 natural-proof clause reconciliation, and **unresolved vendor families** (finviz/THS). **Critical blocker:** **#8435 merge conflict** + **D2C/D2D not accepted** — D2E must not close until both clear.
