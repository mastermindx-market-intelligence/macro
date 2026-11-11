# U1 theme-tree page — facts census (2026-10-17)

WS:GMI-THEME-GRAPH · seat 6f14c2da · READ-ONLY facts packet for the U1 design spec.
Worktree `g2w5-u1census-u3-20261017` @ `a33132b0cc53` (off origin/main), status clean.
`data/` IS present in this sparse tree — every real-graph number below is from an
actual run (`python3` from the worktree root). No fetches. Facts only; no design.

## Q1. Reader contract — `read_hierarchy_breadth`

Signature (`engine/theme_graph/hierarchy_breadth_display.py:234-235`):

```python
def read_hierarchy_breadth(node_id: str, *, nodes: pd.DataFrame | None = None,
                           edges: pd.DataFrame | None = None) -> dict
```

- Inputs: when `nodes`/`edges` are `None` it reads
  `store.read_nodes(current=True)` / `store.read_edges()` at call time, nothing
  cached across calls (`hierarchy_breadth_display.py:245-248`). The store reads
  parquets under `data/theme_graph/`: `nodes.parquet` (`engine/theme_graph/store.py:142`),
  `edges.parquet` (`store.py:146`); readers at `store.py:258` / `store.py:290`.
- Contract constants: `SCHEMA_VERSION = "gmi.hierarchy_breadth_display.v1"` (:47),
  `LABELS = ["house_curated"]` (:51), `QUALITY = "display_only"` (:53),
  `SOURCE = {owner: engine/theme_graph/store.py, artifact: data/theme_graph/nodes.parquet+edges.parquet, field: PARENT_OF}` (:57-61),
  `TIERS = ("macro_category", "theme", "sub_theme", "micro_theme")` (:64),
  `LEGAL_CHILD_TIERS` = macro→(theme), theme→(sub_theme, micro_theme),
  sub_theme→(micro_theme), micro→() (:70-75).
- Envelope keys (every return, `_envelope` :168-179):
  - `schema_version` (str), `subject_id` (str, echoed input),
    `status` (str: `available` | `unknown` | `not_applicable`),
    `reason_code` (str|None: `value_missing` | `retired_entity` | `superseded_entity` | `not_applicable`),
    `value` (dict|None), `labels` (list[str]), `quality` (str), `source` (dict).
  - `value` keys when available (:218-226): `tier` (str ∈ TIERS);
    `parents` (sorted list[str] of ACTIVE parent ids); `children` (dict
    child-tier → sorted list[str], only tiers legal for the subject's tier);
    `child_counts` (dict tier→int, same keys as `children`);
    `descendant_micro_theme_count` (int, DISTINCT active micro_theme ids reachable
    via open `PARENT_OF` edges, cycle-safe walk :142-165);
    `has_sub_theme_layer` (bool: subject is tier `theme` AND has ≥1 active
    `sub_theme` child :225).
- Failure semantics (:182-198, :242-244): absent node → `unknown`/`value_missing`;
  `kind != "theme"` or out-of-contract tier → `not_applicable`; retired/merged →
  `not_applicable`/`retired_entity`|`superseded_entity`; vendor-internal ids
  (`ltheme:`, `finviz_themes`, `ths_concepts`) refused before any store read.
  Empty graph → same `unknown`/`value_missing` envelope (verified by run below).
  Counts/id-lists only — no weights/shares/scores anywhere (:7-10).
- Bulk sibling: `hierarchy_breadth_table(*, nodes=None, edges=None) -> list[dict]`
  (:254-275) — one envelope per ACTIVE theme-kind node, sorted by `subject_id`,
  store loaded at most once per call.
- REAL RUN (worktree, `read_hierarchy_breadth("theme:semiconductors_hardware")`),
  full output was 31 lines:

```json
{
  "schema_version": "gmi.hierarchy_breadth_display.v1",
  "subject_id": "theme:semiconductors_hardware",
  "status": "available",
  "reason_code": null,
  "value": {
    "tier": "macro_category",
    "parents": [],
    "children": {
      "theme": ["theme:ai_semiconductors", "theme:memory_storage", "theme:semicap_equipment"]
    },
    "child_counts": { "theme": 3 },
    "descendant_micro_theme_count": 10,
    "has_sub_theme_layer": false
  },
  "labels": ["house_curated"],
  "quality": "display_only",
  "source": { "owner": "engine/theme_graph/store.py", "artifact": "data/theme_graph/nodes.parquet+edges.parquet", "field": "PARENT_OF" }
}
```

## Q2. Real counts (actual run)

- `nodes.parquet` 3,975 rows × 16 cols; `edges.parquet` 13,349 × 24. Node kinds:
  company 2,809 · local_theme 645 · basket 358 · **theme 108** · etf 55.
- Theme-kind nodes per tier (all 108 are ACTIVE — none retired/merged):
  **macro_category 10 · theme 18 · sub_theme 12 · micro_theme 68**.
- micro_themes with ≥2 active parent chains (KEEP+ADD): **31 of 68**. Examples:
  `theme:copper_mining` ← copper_steel_electrify + copper_supply_chain;
  `theme:hbm_packaging` ← ai_semiconductors + memory_storage;
  `theme:glp1_api_manufacturing` ← glp1_obesity + glp1_supply_chain.
- theme-tier nodes with ≥2 macro_category parents: **3** —
  `theme:ai_semiconductors` ← semiconductors_hardware + technology_software;
  `theme:copper_steel_electrify` ← industrials_defense + materials_mining;
  `theme:data_center_power` ← energy_power + technology_software.
  (Hence 21 macro→theme edges over 18 distinct theme nodes.)
- macro_categories (10), children = `child_counts["theme"]`, micros = `descendant_micro_theme_count`:
  energy_power 4 themes / 12 micros · healthcare_lifesciences 3 / 14 ·
  industrials_defense 4 / 22 · materials_mining 3 / 11 ·
  semiconductors_hardware 3 / 10 · technology_software 3 / 11 ·
  financial_services 1 / 0 · **consumer_cyclical 0 / 0 · consumer_defensive 0 / 0 ·
  crypto_digital_assets 0 / 0 (three EMPTY macro categories — an honest-empty state
  will be needed)**.

## Q3. Page anatomy — `templates/state_of_themes.html.j2` (734 lines)

In order:

| Lines | Section | Heading (EN/ZH) | Mechanism |
|---|---|---|---|
| 1-30 | Jinja macros | — | `t(en, zh)` dual-span macro :1-3; `rp_date_en`/`rp_date_zh` :4/:13; `convline` spark :24 |
| 39-40 | SEO head | — | `{% include "_seo_head.html.j2" %}` :40 (title/desc/path set :39) |
| 41 | pre-paint script | — | sets `data-theme` + `data-lang` on `<html>` (localStorage/navigator/timezone) |
| 42 | CSS link | — | `<link rel="stylesheet" href="theme.css">` |
| 43-307 | page `<style>` | — | ALL page-local CSS lives here (265 lines) |
| 311 | nav | — | `{% include "_site_nav.html.j2" %}`; `<div class="wrap">` :313 |
| 337-410 | reading order | "What to look at first"/"先看哪些主题" (:338) | `<section class="rp">` :337; `<details>` explainer :398-412 |
| 413-437 | lifecycle ribbon | "Where every story sits"/"每个主题所处阶段" (:414) | `.ribbon` stage map `rb_cls` :416; `.rb-*` nodes |
| 438-602 | the board | "The board"/"主题看板" (:439) | `.filter-row` :441; per-lane `<section class="lane ...">` :451; `.theme-row` cards :458-601 |
| 604 | finance entry | — | `{% include "_finance_sector_deep_dive.html.j2" %}` (link-only) |
| 606-644 | fine print | "The fine print"/"细则与依据" (:607) | `.shelf` with two `<details>` :610, :632 |
| 645-649 | empty state | "No theme data available"/"暂无主题数据" (:647) | `{% else %}` branch of the data guard |
| 651-734 | page JS | — | `</div>{# /wrap #}` :651; `theme.js` :654; inline tooltip/observer JS :655-734 |

Context flow (`scripts/build_state_of_themes.py`, 1,990 lines):

- `compose(root)` :735 — "Build template context from live artifacts. Never
  raises." Loads `site/neuralwebdata/theme_{state,thesis,asymmetry,pathways}.json`,
  `data/neuralweb/theme_phase_history.jsonl`, `site/basketdata/{options_witness,clinical_pipeline,trade_flows,foresight_cascade}.json` (:737-753).
- Returns ONE flat ctx dict at **:1376-1402** (keys: `as_of`, `n_themes`,
  `lanes`, `ribbon`, `hero_en/zh`, `n_working/…`, `themes`, `weekly_*`,
  `collision_note_en/zh`, `research_priority`, …).
- `render(root, ctx=None)` :1405-1422 — Jinja `FileSystemLoader(templates/)`,
  `autoescape=True`; `main()` :1951 writes `site/state_of_themes.html` (:1957)
  and the `site/basketdata/theme_lanes.json` side-artifact from the SAME ctx
  (:1936; schema `THEME_LANES_SCHEMA = "theme_lanes.v1"` :354).
- **A new section's context is naturally assembled inside `compose()`**, added to
  the returned dict at `scripts/build_state_of_themes.py:1376` (artifact load
  alongside :737-753). No `read_hierarchy_breadth` import exists there today
  (`git grep hierarchy scripts/build_state_of_themes.py` → no match).

## Q4. Existing components

All page-local CSS is in the template's inline `<style>` (:43-307); none of it is
a shared partial. Cards/tables/collapsible/chips/tooltips:

- Cards: `.theme-row` (CSS :145-149, markup :458) + `.tc-top/.tc-name/.tc-story/.tc-meta`
  (CSS :150-158, markup :461-466); grid `.lane-grid` (CSS :132, markup :457);
  lane header `.lane-badge` (CSS :126-129, markup :453).
- Tables: `.fals-table` (CSS at :208-ish block; markup :526) — the only table class.
- Collapsible rows: native `<details>/<summary>` — `.shelf` (CSS :219-225, markup
  :610, :632) and `.rp details summary` (CSS :262-263, markup :398).
- Chips: `.chg-chip` (CSS :80-84), filter chips `.fchip` (CSS :116-118, row :115,
  markup :441), `.stage-pill` (CSS :153, markup :463).
- Tooltips: `data-tip-en`/`data-tip-zh` attributes + `.help-q` (:514) /
  `.ctx-tip-icon` (:549); a JS-built floating tip styled via `_tip.style.cssText`
  (:664), hover/focus wiring :659-700; also `.rb-pop` hover popovers (CSS :109-111).
- In `mockups/design_system/specimen.html` (present in tree; 371 `class=` hits):
  `data-tip-en` ×5 and the chip family ×13 (`.dd-chip` :62, `.dtp-chip` :206,
  `.chip-pos` :262) appear; **none** of `lane-badge`, `shelf`, `sec-head`,
  `help-q`, `fals-table`, `theme-row`, `sot-spark`, `rb-s-*`, `pnode` do — the
  page's section components are page-local, not design-system specimens.

## Q5. i18n (EN/ZH)

- Mechanism: the `t(en, zh)` macro emits DUAL SPANS `<span class="l-en">…</span><span class="l-zh">…</span>`
  (`templates/state_of_themes.html.j2:1-3`); card fields render bare `.l-en`/`.l-zh`
  spans (:463-466). Toggle = `html[data-lang]` set pre-paint (:41), CSS flips
  visibility — `[data-lang="zh"] .l-en{display:none}` / `.l-zh{display:inline}` /
  defaults :275-277 — plus a zh font stack (:278). JS reads it via `_lang()`
  (:668) and a `MutationObserver` on `data-lang` (:729) re-renders JS-drawn bits
  (tooltips).
- ZH theme names: YES — `name_zh` on theme nodes (nodes.parquet column
  `name_zh`, alongside `name_en`). Actual run: **0 of 108 active theme nodes
  missing `name_zh`** (e.g. `theme:semiconductors_hardware` → `半导体与硬件`).
- Guard: translated text must NEVER go in `title=` attributes or `t()` inside an
  attribute (`scripts/check_title_i18n.py:1-8`; the dual-span mechanism cannot
  operate inside an attribute). New tooltips use `data-tip-en`/`data-tip-zh`.

## Q6. Theme (light/dark)

- Switch: pre-paint script sets `document.documentElement[data-theme]` from
  `localStorage['theme']`, default **dark** (`templates/state_of_themes.html.j2:41`).
- Tokens from `templates/theme.css`: dark `--bg/--panel/--panel2/--text` (:63),
  `--muted` (:64), `--line` (:69), `--warn/--act/--ok` (:71), `--info/--link`
  (:78); light overrides under `html[data-theme="light"]` (:192, :211-229,
  :290, :367). The page re-maps accents inside its own `<style>`: `--good/
  --early/--warn/--bad/--quiet` (:54) and lane colors `--lc-watch/broad/rerate/
  accel/prec/corr` (:55), with light variants at :59-60.
- JS-injected styling: yes, one — the floating tooltip's `_tip.style.cssText=…`
  (:664). That is runtime style injection and is exactly what the ratchet guard
  counts (Q7).

## Q7. Tests and guards

Tests matching `state_of_themes` (`git grep -l state_of_themes -- 'tests/*.py'`):

- `tests/test_state_of_themes.py` (1,492 lines) — the page's suite: live-render
  matrix :94, graceful-missing-artifact :119/:157/:178/:693, `test_no_cjk_in_title_attrs` :223
  (+ new-section variants :742, :752), filter-chip counts :239, inline-JS parse :300,
  template/site sync :327, OW/clinical/trade-flow sections :528-:690.
- Mentions: `test_front_facing_register.py`, `test_navigation_refresh.py`,
  `test_nav_submenu_icons.py`, `test_builder_shim_writes.py`,
  `test_finance_entry_points.py`, `test_research_priority_ordering.py`,
  `test_theme_phase_history_generation_filter.py`,
  `test_energy_economic_change_non_regression.py`.

CI checks a new section would trip (each cited at its source and its wiring):

- `scripts/check_design_system.py` (:1-8) — raw colors/font stacks/hand-rolled
  cards/emoji in new markup; run `--mode report` at `.github/ci/legacy-jobs.yml:10415-10417`;
  NEW templates are born governed in `enforce-added`.
- `scripts/check_runtime_style_injection.py` (:1-15) — ratchet vs
  `config/runtime_style_injection_allowlist.json`; ANY new JS style-injection
  signature under `templates/`/`site/` is a hard fail (wired :10710-10711).
- `scripts/check_ui_visual_evidence.py` (:1-10) — changed CSS in an existing
  `<style>` block or a new inline style requires committed `EVIDENCE.yml`
  receipts (dark/light × EN/ZH × desktop/mobile) under `mockups/refs/` or
  `mockups/evidence/`; added `:hover`/`:focus*` needs interaction captures.
- `scripts/check_title_i18n.py` (:1-8) — run at `.github/ci/legacy-jobs.yml:1652-1654`;
  no CJK / `t()` inside `title=`.
- `scripts/check_template_site_sync.py` (:1-15, law `ui.template_site_sync`) —
  `site/state_of_themes.html` must byte-match its template (`.github/workflows/ci-main-heartbeat.yml:152-154`).
- Data contract (if U1 touches the graph): `scripts/check_theme_graph_contracts.py:1-4`.

## Q8. Neighbours — pages already showing theme parent/child

`git grep -ln "PARENT_OF\|sub_theme\|micro_theme" templates scripts` matches **no
template** — only two scripts:

- `scripts/check_theme_graph_contracts.py` — edge-contract guard over
  `contracts/theme_graph/` (law `theme_graph.edge_contract`); not a page.
- `scripts/theme_coverage_gaps.py` — coverage-gap diagnostic over instruments vs
  the concept vocabulary; not a page.

Broader sweep (`git grep -ln "theme_graph\|hierarchy" -- templates scripts`): all
hits are build/query tooling — `build_theme_graph.py`, `query_theme_ontology.py`,
`list_theme_ontology.py`, `explain_theme_changes.py`, `explain_theme_overlap.py`,
`build_thematic_state.py`, `build_site.py`, … — and
`scripts/build_state_of_themes.py` itself, which today imports nothing from the
hierarchy reader. **No page currently renders macro_category → theme →
sub_theme → micro_theme; U1 would be the first page surface for the hierarchy.**
