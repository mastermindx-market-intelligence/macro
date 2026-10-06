# GMI completion ruler audit — 2026-10-05 (Wave G, read-only)

Independent integrator audit for **WS:GMI-THEME-GRAPH** Wave G. Commission: Fable Meta-CEO seat `6f14c2da`, Master Plan PR #8324, Sol handoff comment `5991777960`. Lane cwd evidence: `git rev-parse --show-toplevel` → `/home/longr/lanes/wt/mo-ext-fix-gmi_g_audit_r1`. Audit UTC pin collected at `2026-10-05T11:27:09Z`.

---

## 0. PIN (C0)

| Carrier | state | draft | headRefOid | mergeable | updatedAt | newest ci.yml (id / conclusion) | newest fences.yml (id / conclusion) |
|---------|-------|-------|------------|-----------|-----------|--------------------------------|-------------------------------------|
| **origin/main** | — | — | `20eb503a09aef8bc2ccc8945f1ea140bdc9aeace` | — | — | no run on this exact head (`gh run list --commit 20eb503… --workflow ci.yml` → `[]`) | in_progress run `37302917973` on head `20eb503a09…` (`gh run list --workflow fences.yml --branch main --limit 1`) |
| **#8324** Master Plan | OPEN | true | `0a74706819a2cdf276b8d278182c8b468c481d93` | MERGEABLE | 2026-10-05T09:42:10Z | `37116714909` / success | `37116714787` / success |
| **#8455** Wave A state-owner | OPEN | true | `029fe5b17f0f94ab7cdd1dad19444149f0d4a9a6` | MERGEABLE | 2026-10-05T11:06:23Z | `37300796142` / **in_progress** (empty conclusion at read) | `37300795721` / success |
| **#8417** D1/W3C seams | OPEN | true | `d02ebf451f1d53699499994825362cb23c85af73` | UNKNOWN | 2026-10-05T10:58:20Z | `37299950277` / **in_progress** | `37299949088` / success |
| **#8485** Wave C rights_use | OPEN | false | `74467f24300a310106242cba2e4f0becbe19c8e8` | MERGEABLE | 2026-10-05T11:11:33Z | `37299976182` / **in_progress** | `37299975695` / success |
| **#8432** D2C PIT/ontology | OPEN | true | `54d17ebcb1c11471fffbbdea6888f97db6c9fbbb` | UNKNOWN | 2026-10-04T13:53:11Z | `37206291268` / success | `37206291123` / success |
| **#8435** D2D structural binding | OPEN | true | `7429a3e5f6da9b66787ead24119a238a2a36858d` | UNKNOWN | 2026-10-05T00:07:35Z | `37242875242` / success | `37242875046` / success |
| **#8486** Wave D2 selection reads | OPEN | true | `2e2bcd75ca62e10a12c99afc60707c32ee6895ad` | MERGEABLE | 2026-10-05T11:19:37Z | **none** (`gh run list --commit 2e2bcd75…` → `[]`) | **none** |

**main pin command:**

```text
$ git fetch origin main && git rev-parse origin/main
20eb503a09aef8bc2ccc8945f1ea140bdc9aeace
```

**Newest completed `daily.yml` on main (success):**

```text
$ gh run list -R mastermindx-market-intelligence/macro --workflow daily.yml --branch main --limit 3 --json databaseId,conclusion,createdAt,status
[{"conclusion":"cancelled","createdAt":"2026-09-29T12:10:26Z","databaseId":36566370352,"status":"completed"},
 {"conclusion":"success","createdAt":"2026-09-29T02:38:34Z","databaseId":36513549389,"status":"completed"},
 {"conclusion":"cancelled","createdAt":"2026-09-29T02:13:04Z","databaseId":36511549800,"status":"completed"}]
```

**Newest completed `closing-bell.yml` on main (success):** run `37080966553`, `2026-10-03T00:11:03Z` (`gh run list --workflow closing-bell.yml --branch main --limit 2`).

---

## 1. One incumbent graph/state/publication authority; no duplicate control planes

**VERDICT:** PARTIAL

**EVIDENCE:**

```text
$ git ls-tree --name-only origin/main engine/theme_graph/ | wc -l
17
```

`engine/theme_graph/theme_state.py` on main declares shadow-only, non-publishing authority (`AUTHORITY` block: `may_publish: False`; module docstring lines 1–6).

Workstream single-owner claim:

```text
$ head -20 agentos/workstreams/WS-GMI-THEME-GRAPH.md
objective: >
  Own one canonical theme/local-theme semantic graph ... one ThemeState authority
owns_paths:
  - engine/theme_graph/
  - data/theme_graph/
```

Parallel theme-state publication path (Neural Web, not `engine/theme_graph/`):

```text
$ head -8 scripts/build_thematic_state.py
Writes:
    data/neuralweb/theme_state.json          (primary; git-committed)
    site/neuralwebdata/theme_state.json      (site mirror)
Display/context tier only. Authority block: is_context_only=True
```

Graph materialization writer on main:

```text
$ git cat-file -e origin/main:scripts/build_theme_graph.py && echo EXISTS
EXISTS
```

**GAP:** No production proof that runtime consumers route exclusively through the incumbent owners; Neural Web `theme_state.json` remains a second committed publication surface for “thematic state” wording.

**NEXT:** Seat maps every consumer read path (Macro site, CTE, Terminal resolver) to either `engine/theme_graph/*` or explicit display-tier Neural Web — **seat act**; Sol gates any merge that arms overlapping producers (**Sol gate**).

---

## 2. D2C/D2D/D2E and required PIT/ontology/history integrity

**VERDICT:** HELD_BY_AUTHORITY

**EVIDENCE:**

Main already has PIT owner module:

```text
$ git cat-file -e origin/main:engine/basket_membership_pit.py && echo EXISTS
EXISTS
```

Held carriers carry unreleased integrity repairs (not on main):

```text
$ git cat-file -e origin/main:engine/theme_graph/selection_cohort_reads.py 2>&1 | tail -1
fatal: path 'engine/theme_graph/selection_cohort_reads.py' does not exist in 'origin/main'
```

#8432 head diff stat (PIT/ontology lifecycle):

```text
$ git diff --stat origin/main...origin/claude/gmi-d2-membership-ontology-lifecycle-20261004-astra-001 | tail -1
 12 files changed, 2281 insertions(+), 71 deletions(-)
```

#8432 body (excerpt): “No main merge or runtime activation is claimed”; “natural ontology-action authority resolver remains **UNWIRED**”; release ownership on comment `5978637197` under #8324.

#8435 head diff stat (structural owner binding):

```text
$ git diff --stat origin/main...origin/claude/gmi-d2d-structural-owner-binding-20261004-astra-001 | tail -1
 6 files changed, 5858 insertions(+), 43 deletions(-)
```

`WS-GMI-THEME-GRAPH.md` lists D2C/D2D/D2E waves `status: todo` with Sol sequencing (`depends_on`, placement gates).

**GAP:** D2E acceptance and natural nightly proof not evidenced on main at pin; held PRs are source+CI, not merged law.

**NEXT:** Sol releases integration order per #8324 comments — **Sol gate**; do not arm/merge held drafts (#8432, #8435, #8417, #8455).

---

## 3. Local + canonical W3B state and finalized US/China W3C with exact source reasons/clocks/coverage

**VERDICT:** HELD_BY_AUTHORITY

**EVIDENCE:**

W3C/CTE successor modules absent on main:

```text
$ git cat-file -e origin/main:engine/theme_graph/selection_cohort.py 2>&1 | tail -1
fatal: path 'engine/theme_graph/selection_cohort.py' does not exist in 'origin/main'
$ git cat-file -e origin/main:engine/company_theme_exposure/successor.py 2>&1 | tail -1
fatal: path 'engine/company_theme_exposure/successor.py' does not exist in 'origin/main'
```

#8417 carries 13 paths vs merge-base (includes `selection_cohort*.py`, CTE successor, build script hooks). Body: “No main merge or natural publication is claimed”; “W3C remains its own original requirement”; effect gates on comment `5978488558`.

#8455 adds generation/production readers not on main:

```text
$ git cat-file -e origin/main:engine/neuralweb/theme_state_generation.py 2>&1 | tail -1
fatal: path 'engine/neuralweb/theme_state_generation.py' does not exist in 'origin/main'
```

Main shadow composer only:

```text
$ git cat-file -e origin/main:engine/theme_graph/theme_state.py && echo on_main
on_main
```

**GAP:** Finalized cohort readers, clocks, and coverage receipts are in open stacked carriers (#8417, #8455, #8486), not proven on `origin/main`.

**NEXT:** Integrate W3C packet after Sol release on #8417 thread — **Sol gate**; seat keeps #8486 stacked and does not merge ahead of hold (**seat act**, no merge).

---

## 4. Current per-use rights and revocation on real consumer paths

**VERDICT:** PARTIAL

**EVIDENCE:**

Registry authority on main:

```text
$ head -5 engine/theme_graph/rights.py
THE SINGLE AUTHORITY IS THE REGISTRY. ``config/theme_sources.yml``
```

Wave C carrier adds runtime capture module not on main:

```text
$ git diff --name-only $(git merge-base origin/main origin/claude/gmi-c-rights-use-20261005) origin/claude/gmi-c-rights-use-20261005
engine/theme_graph/rights_use.py
.github/ci/legacy-jobs.yml
tests/test_theme_graph_rights_use.py
```

#8485 is **OPEN**, not draft, but **unmerged**; ci on head in_progress at pin.

#8417/#8455 bodies state qualified-reader callbacks and capture “remain None / unavailable” until separate gates.

**GAP:** No evidence of live revocation on production consumer paths at pin; `rights_use.py` exists only on #8485 branch.

**NEXT:** Land #8485 only after Sol clears Wave C acceptance and stack order — **Sol gate** (do not arm while upstream holds remain).

---

## 5. Natural publication, refresh, correction and rollback receipts

**VERDICT:** CI_GREEN_NOT_PRODUCTION

**EVIDENCE:**

`data/theme_graph/` on main (GitHub API; no sparse checkout):

```text
$ gh api repos/mastermindx-market-intelligence/macro/contents/data/theme_graph?ref=main --jq '[.[].name, .[].size, .[].sha]'
["_meta.json","capability.parquet","edges.parquet","evidence.parquet","identity_resolution.parquet",
 "node_lifecycle.parquet","nodes.parquet","probation",3482,17952,292939,8381,207858,8049,137781,0,
 "523c8505cc51298de4f2275a3d107cd41c985103", ...]
```

Writer on main:

```text
$ rg -l "materialize, store" scripts/build_theme_graph.py
scripts/build_theme_graph.py
```

Nightly lane (stale relative to pin):

```text
daily.yml newest success: id 36513549389, createdAt 2026-09-29T02:38:34Z (six days before main pin)
closing-bell.yml newest success: id 37080966553, createdAt 2026-10-03T00:11:03Z
```

Held carriers explicitly disclaim natural publication (#8417, #8432 bodies).

**GAP:** No auditor-verified correction/rollback receipt chain tied to current main head `20eb503a09…`; nightly success predates recent main movement.

**NEXT:** Operator or nightly owner dispatches/watches `daily.yml` after main stabilizes — **lane** (`prophet_rescue` etiquette applies); Sol accepts natural proof window — **Sol gate**.

---

## 6. Accepted versioned state→CTE→R2/API→Terminal contract with real immutable publication and consumer verification

**VERDICT:** UNPROVEN

**EVIDENCE:**

Macro side: CTE successor and generation bridge files **not on main** (see §3). #8455 body cites synthetic pytest and pinned Terminal resolver scenarios but states PR “stays Draft/HOLD, unmerged”.

Terminal repo **not cloned** (spec). Pointer recorded:

- Repo: `mastermindx-market-intelligence/mastermind-terminal`
- Last pinned cutover-normalizer epoch: `2ca21c44718a9f44c5ab74baaa42afbd14623399`

```text
$ git cat-file -e origin/main:engine/theme_graph/theme_state_production.py 2>&1 | tail -1
fatal: path 'engine/theme_graph/theme_state_production.py' does not exist in 'origin/main'
```

**GAP:** End-to-end immutable publication + consumer verification requires Terminal live read and merged Macro carriers.

**NEXT:** Sol-owned cross-repo acceptance after #8455/#8417 release — **Sol gate**; Terminal lane verifies resolver against merged head — **lane** (separate repo).

---

## 7. Real human and machine consumers and required degraded/UI proof

**VERDICT:** UNPROVEN

**EVIDENCE:**

Macro read surfaces exist (e.g. `engine/intelligence_workspace/adapters/theme.py` references `data/theme_graph` on main), but no live URL or authenticated journey was exercised in this lane.

#8455 body claims CLI/Terminal resolver tests on a **candidate** head, not merged main.

Terminal consumption: **UNPROVEN** (no access).

**GAP:** Degraded-mode UI proof matrix (Macro dark+light, Terminal dark-only per `DEC:TERMINAL-SHELL-IS-DARK-ONLY-EVIDENCE-MATRIX-2026-09-06`) not produced at pin.

**NEXT:** Seat runs post-merge production proof on Macro routes; Terminal seat runs dark-only evidence — **seat acts** after Sol merge release.

---

## 8. Explicit acceptance or held verdicts for expanded economics/exposure/leadership and each predictive-use application

**VERDICT:** PARTIAL

**EVIDENCE:**

AgentOS GMI decisions present:

```text
$ ls agentos/decisions/DEC-GMI*
DEC-GMI-F04-BOUNDED-CHILD-ROUTING-2026-08-28.md
DEC-GMI-ROBOTICS-RELAND-ORDERING-AND-REGISTRATION.md
DEC-GMI-THEME-GRAPH-END-TO-END-COMPLETION-OWNERSHIP-SEQUENCING.md
```

Exposure probe concluded as research (not rank authority):

```text
$ rg "status: done" agentos/workstreams/WS-GMI-THEME-GRAPH.md -n | head -3
  - id: R1
    status: done
    pr: 5402
```

Hold on ticker exposure tags cited in W2 prereg:

```text
$ rg "DNR:HOLD-TICKER-EXPOSURE-TAGS" research/theme_graph/W2_EXPOSURE_AXES_PREREG.md
`DNR:HOLD-TICKER-EXPOSURE-TAGS` stands adjacent to any revival.
```

No `DEC-GMI-*` record found in-repo accepting expanded economics sizing or leadership semantics for production rank (grep `DEC-GMI` → three files only).

**GAP:** Per predictive-use application acceptance not enumerated as PROVEN; leadership/STSI migration remains plan text in #8324, not merged law.

**NEXT:** Sol issues explicit HELD/ACCEPTED DEC rows per application — **Sol/Chairman gate**; seat documents in AgentOS when merged.

---

## 9. Full current GitHub source/CI/security/release evidence and production proof for the exact accepted source

**VERDICT:** PARTIAL

**EVIDENCE:**

```text
$ gh run list --workflow ci.yml --branch main --limit 1 --json databaseId,conclusion,headSha
[{"conclusion":"failure","databaseId":36609455507,"headSha":"d7679296848443896e303e989ec35fa2541122cf"}]
```

Current pin head `20eb503a09…` has **no** completed `ci.yml` run on that exact commit at audit time.

Newest `fences.yml` on main at read: `37302917973` **in_progress** on `20eb503a09…`.

Held implementation carriers (#8432, #8435) show **success** on their heads at pin; #8455/#8417/#8485 ci **in_progress**.

**GAP:** Main at pin is not CI-proven; production proof not claimed for any accepted GMI completion source.

**NEXT:** Wait for fences/ci on `20eb503a09…` to conclude — **lane**; Sol rules whether main-red-repair needed — **Sol gate**.

---

## 10. AUTHORITY MAP

**Modules under `engine/theme_graph/` on `origin/main`:**

```text
$ git ls-tree --name-only origin/main engine/theme_graph/
engine/theme_graph/__init__.py
engine/theme_graph/capability.py
engine/theme_graph/change_report.py
engine/theme_graph/identity.py
engine/theme_graph/identity_resolution.py
engine/theme_graph/local_sources.py
engine/theme_graph/materialize.py
engine/theme_graph/membership_evidence.py
engine/theme_graph/ontology.py
engine/theme_graph/ontology_inventory.py
engine/theme_graph/probation.py
engine/theme_graph/proposal_worklist.py
engine/theme_graph/rights.py
engine/theme_graph/security_navigation.py
engine/theme_graph/store.py
engine/theme_graph/structural_navigation.py
engine/theme_graph/theme_state.py
```

**Also named in spec:** `engine/basket_membership_pit.py` — **EXISTS** on main.

**Scripts touching `data/theme_graph` / graph build (grep):**

```text
$ rg -n "data/theme_graph" scripts/ --glob "*.py" -l
scripts/build_security_master.py
scripts/correct_gmi_identity_lineage.py
scripts/build_theme_graph.py   # via engine.theme_graph.materialize/store
```

**`theme_state` Python files (spec command equivalent via ripgrep):**

```text
scripts/build_thematic_state.py
scripts/build_state_of_themes.py
scripts/build_company_theme_exposure.py
engine/theme_graph/theme_state.py
engine/neuralweb/thematic_state.py
engine/neuralweb/theme_thesis.py
engine/neuralweb/world_state.py
engine/neuralweb/mastermind_context.py
engine/neuralweb/cortex.py
engine/neuralweb/daily_brief.py
engine/neuralweb/brain_gateway.py
engine/neuralweb/brief_context.py
engine/neuralweb/ask_brain.py
(+ additional engine consumers: flow_observatory/*, credit_momentum.py, china_board_rank.py, company_theme_exposure/*, us_context_vector.py, postmortem.py)
```

**SECOND producer flag (ruler §1):** `scripts/build_thematic_state.py` → `data/neuralweb/theme_state.json` alongside `scripts/build_theme_graph.py` → `data/theme_graph/*` (both on main).

---

## 11. CARRIER INTERSECTION

Pairwise shared paths among #8455 / #8417 / #8432 / #8435 / #8485 / #8486 (merge-base vs `origin/main`):

| Pair | Shared paths (count) | Notes |
|------|---------------------|--------|
| 8455 ∩ 8417 | 13 | Includes `selection_cohort*.py`, CTE successor, china/site build scripts, tests |
| 8455 ∩ 8486 | 13 | Same W3C stack as 8417 plus 8486 adds `selection_cohort_reads.py` only on 8486 |
| 8417 ∩ 8486 | 13 | Stacked D2 on #8417 per #8486 title |
| 8455 ∩ 8432 / 8435 / 8485 | 1 each | **Only** `.github/ci/legacy-jobs.yml` |
| 8417 ∩ 8432 / 8435 / 8485 | 1 each | **Only** `legacy-jobs.yml` |
| 8432 ∩ 8435 / 8485 / 8486 | 1 each | **Only** `legacy-jobs.yml` |
| 8485 ∩ 8486 | 1 | **Only** `legacy-jobs.yml` |

`.github/ci/legacy-jobs.yml` shared across all carriers is **expected** (CI enrollment), not semantic collision.

---

## 12. DUPLICATE / REDO RISK

**#8432 vs main:** adds/changes `engine/basket_membership_pit.py`, `materialize.py`, `probation.py`, `local_sources.py` — modules **already exist on main**; carrier is a **large delta** (`+2281` lines), not a greenfield path. Risk: merge conflict with any parallel edit to same owners.

**#8435 vs main:** `structural_navigation.py` exists on main (173 lines); carrier version **556 lines** (`git show … | wc -l`). Same path, expanded implementation — **redo risk if main moved independently**; at pin, main copy is strict subset by line count.

**#8455 / #8417 / #8486:** introduce `selection_cohort*.py` and `company_theme_exposure/successor.py` **absent on main** — no duplicate module name on main, but **8455 vs 8417** share 13 files (stack/rebase hazard).

**#8485:** `rights_use.py` absent on main — no name collision.

---

## 13. HONEST SUMMARY

- **PROVEN:** 0 ruler items fully PROVEN to production acceptance at pin.
- **HELD_BY_AUTHORITY:** 2 items (§2, §3) via Sol-held unmerged carriers and explicit PR hold language.
- **PARTIAL / CI_GREEN / UNPROVEN:** remaining items; **UNPROVEN:** §6–§7 (Terminal and live consumers).
- **Critical path:** Sol-held integration of #8324 sequenced carriers (#8432, #8435, #8417, #8455) before W3B/W3C/rights/D2 can be treated as accepted source on `main`.
- **Seat today:** maintain carrier stack discipline, collision census, and this audit; **no arming/merging held PRs**.
- **Sol/Chairman only:** release holds, cross-repo Terminal proof, per-application economics/leadership DEC acceptance, merge order.

---

## Lane verify (audit artifact)

Commands to run after commit:

```text
git status --porcelain
git log --oneline origin/main..HEAD
wc -l research/theme_graph/GMI_COMPLETION_RULER_AUDIT_2026-10-05.md
```

**Tests:** None required by ruling (read-only audit); no pytest invoked.
