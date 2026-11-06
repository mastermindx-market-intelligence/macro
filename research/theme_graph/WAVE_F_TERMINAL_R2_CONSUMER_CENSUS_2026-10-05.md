# Wave F — Terminal / R2 / site consumer census (ThemeState & CTE)

**Pins:** macro `origin/main` `81eb0c9b399327c6989c54a86fe99d2c542a7b3d`; PR #8455 head `029fe5b17f0f94ab7cdd1dad19444149f0d4a9a6`; PR #8417 head `d02ebf451f1d53699499994825362cb23c85af73` (branch `claude/gmi-cte-state-successor-20261004-astra-001`); Terminal `2ca21c44718a9f44c5ab74baaa42afbd14623399`.

## C0 — Site mirror writer (anchor)

**Writer:** `scripts/build_thematic_state.py` function `build()` calls `_atomic_write_json()` at `scripts/build_thematic_state.py:108-111` (`origin/main` `81eb0c9b3993`), which writes `site/neuralwebdata/theme_state.json` (mirror of `data/neuralweb/theme_state.json`). Payload is composed by `engine/neuralweb/thematic_state.py:448` `compose()` (`origin/main` `81eb0c9b3993`).

No other module opens that site path for write on main: `rg -n 'site/neuralwebdata/theme_state\.json' engine/ scripts/ --glob '*.py'` on `origin/main` hits only `scripts/build_thematic_state.py:44,111` and the `_SITE_OUT` constant in `engine/neuralweb/thematic_state.py:87` (compose-only; no write there).

## Q1 — Producers (macro main pin)

| Producer | Artifact(s) | Contract / schema | Workflow lane |
|---|---|---|---|
| `engine/neuralweb/thematic_state.py:448` `compose()` invoked by `scripts/build_thematic_state.py:65-111` | `data/neuralweb/theme_state.json`, `site/neuralwebdata/theme_state.json`, append `data/neuralweb/theme_phase_history.jsonl` via `append_phase_history` (`engine/neuralweb/thematic_state.py:571+`) | In-module `SCHEMA = "neuralweb.theme_state.v1"` (`engine/neuralweb/thematic_state.py:45`); **no** `contracts/theme_graph/` file for this lineage | `.github/workflows/daily.yml:4646` `run: python -m scripts.build_thematic_state ...` |
| `engine/neuralweb/theme_thesis.py:892` `run_stage()` (optional stage from `scripts/build_thematic_state.py:136-163`) | `site/neuralwebdata/theme_thesis.json` (`engine/neuralweb/theme_thesis.py:80,1024`) | Thesis ledger schema in-module (TIL W1) | Same nightly step as thematic state (optional stage after `build()`) |
| `engine/neuralweb/theme_pathways.py:591` `run_stage()` | `data/neuralweb/theme_pathways.json`, `site/neuralwebdata/theme_pathways.json` (`engine/neuralweb/theme_pathways.py:84`) | Pathways artifact ids in-module (TIL W2) | Same optional-stage dispatch |
| `engine/neuralweb/theme_asymmetry.py:1310` `run_stage()` | `site/neuralwebdata/theme_asymmetry.json` (`engine/neuralweb/theme_asymmetry.py:100`) | Asymmetry panel in-module (TIL W3) | Same optional-stage dispatch |
| `scripts/build_theme_graph.py:293-314` `main()` → `run()` → `engine/theme_graph/materialize.py` + `engine/theme_graph/store.py:472-522` writers | `data/theme_graph/{nodes,edges,evidence,capability,identity_resolution,node_lifecycle}.parquet`, `data/theme_graph/_meta.json` (declared `config/dag.yml:3857-3861`) | `contracts/theme_graph/*.v1.schema.json` (17 JSON schemas + README on main) | `.github/workflows/daily.yml:3244` `run: bash scripts/ci/daily_engine_regional_desk_builders.sh` → `scripts/ci/daily_engine_regional_desk_builders.sh:119` `scripts.build_theme_graph` |
| `scripts/build_company_theme_exposure.py:24+` `main()` → `engine/company_theme_exposure/views.py:259` `build_bundle()` | `data/company_theme_exposure/generations/<id>/...` (local tree; default `--out-dir`) | `engine/company_theme_exposure/contracts.py:18-19` `company_theme_exposure.v1` / manifest v1 (**not** under `contracts/theme_graph/`) | `.github/workflows/company-intelligence.yml:137` `python -m scripts.build_company_theme_exposure ...` |
| `scripts/publish_company_theme_exposure_r2.py:25` `PREFIX = "company_theme_exposure"` | R2 keys `company_theme_exposure/manifest.json`, `company_theme_exposure/generations/<id>/...` | Same CTE contracts as builder | `.github/workflows/company-intelligence.yml:143` `python -m scripts.publish_company_theme_exposure_r2 ...` |

**R2 / site negatives (main pin):**

- No theme-graph parquet publisher to R2: `rg -n 'theme_graph' scripts/publish*.py scripts/publish_r2.py` → no matches (`origin/main` `81eb0c9b3993`).
- No `site/theme_graph/*` tree: `git ls-tree -r origin/main --name-only site/ | rg theme_graph` → empty.
- GMI shadow ThemeState composer `engine/theme_graph/theme_state.py:461` `read_theme_state()` exists on main but **no** `scripts/*` producer calls `compose_state` / `theme_state_production` on main (`rg -n 'theme_state_production|compose_state' scripts/` → no theme-graph publication script).

## Q2 — API endpoints (macro main pin)

| Route | Handler | Reads |
|---|---|---|
| `POST /api/ask`, `POST /api/ask/stream` | `app/main.py:1130-1176` → `engine/neuralweb/ask_brain.py:1547` `_tool_read_theme_state()` | `data/neuralweb/theme_state.json`; also `site/neuralwebdata/theme_thesis.json` for thesis tool siblings |
| `POST /api/brain/stream`, `GET /api/brain/*` (gateway) | `app/main.py:1199+` → `engine/neuralweb/brain_gateway.py` tool dispatch → `engine/neuralweb/cortex.py:1193` / `ask_brain.py:1547` for `read_theme_state` | Same `data/neuralweb/theme_state.json` |
| `GET /api/ontology/explorer/...` | `app/ontology_explorer.py:105-118` | Oil-inflation chain only (`ACCEPTED_CHAINS`); **no** theme-graph / CTE / selection cohort on main |

No FastAPI route on main serves GMI `theme_state/v2`, selection cohort JSON, or CTE bundles (CTE is R2-only via publish script).

## Q3 — Contract surface (#8455 / #8417 vs main)

**On main (`81eb0c9b3993`), `contracts/theme_graph/`:** README + 17× `*.v1.schema.json` (nodes, edges, evidence, capability, identity_resolution, node_lifecycle, theme_state.v1, structural/security/ontology/probation/cn_limit variants).

**Added/changed vs main (scoped diff):**

PR #8455 `029fe5b17f0f` (`git diff --stat 81eb0c9b3993..029fe5b17f0f -- contracts engine/theme_graph engine/neuralweb/theme_state*`):

- New schemas: `selection_cohort_read.v1`, `selection_cohort_source.v1`, `theme_state.v2`, `theme_state_generation.v1`, `theme_state_generation_read.v1`, `theme_state_generation_read.v2`, `theme_state_use_read.v1`.
- New/changed engine modules: `engine/theme_graph/selection_cohort.py`, `selection_cohort_publication.py`, `theme_state_production.py`, `theme_state_use_reader.py`; neuralweb adapter/generation modules under `engine/neuralweb/theme_state_*`.
- **Public read APIs (new on #8455 head):** `engine/theme_graph/theme_state_production.py:308` `read_subject`, `:333` `validate_read_receipt`; `engine/theme_graph/theme_state_use_reader.py:21` `read_subject_at_use`, `:52` `validate_read_receipt_at_use`; `engine/theme_graph/selection_cohort.py` `compose_selection_cohort` / `validate_selection_cohort`; publication `read_finalized_cohort`, `consume_us_source`, etc. (`selection_cohort_publication.py`).
- **Unchanged on #8455:** `engine/theme_graph/theme_state.py` `read_theme_state` (`git diff 81eb0c9b3993..029fe5b17f0f -- engine/theme_graph/theme_state.py` empty).

PR #8417 `d02ebf451f1d` adds the two `selection_cohort_*.v1.schema.json` files plus `selection_cohort.py` / `selection_cohort_publication.py` (subset of #8455’s engine surface).

**Schema versions introduced:** v1 selection cohort read/source; v2 theme_state (GMI graph plane); v1/v2 theme_state_generation_read; v1 theme_state_use_read; v1 theme_state_generation.

## Q4 — Terminal consumers (epoch `2ca21c44718a`)

| Path | Artifact / endpoint | Fields used |
|---|---|---|
| `terminal/lib/sectorIntelligence.ts:63,89-99` | `GET /api/sector-intelligence?source=themes` → upstream `/neuralwebdata/theme_state.json` | Envelope: `schema`, `themes[]`; rows: `theme_id`, `name_en`; `foresight.entry_ready`; `stale_legs` |
| `terminal/app/api/sector-intelligence/route.ts:16-17,79+` | Proxies `NW_BASE` + `/neuralwebdata/theme_state.json` | Transport + hash; delegates envelope rules to `readableOwnerEnvelope` |
| `terminal/lib/companyThemeExposure.ts:12-13,232-290,498-545` | R2 `company_theme_exposure/manifest.json`, generation manifests, per-ticker JSON | Full `company_theme_exposure.v1` including embedded `theme_state` receipt `{status, as_of, sha256}` |
| `terminal/app/api/company-theme-context/[symbol]/route.ts:9-10,44+` | `resolveCompanyThemeExposureFromR2` (`R2_BASE`) | Pass-through of normalized CTE payload |
| `terminal/components/fin/CompanyThemeContextCard.tsx:33-36,49,154,164` | Rendered CTE context | `theme_state.status`, `as_of`, `sha256`; warning codes |
| `terminal/app/api/brain/[...path]/route.ts:1-37` + `terminal/components/BrainWidget.tsx:163` | Macro `POST /api/brain/stream` (proxy) | Indirect: gateway tool `read_theme_state` reads macro repo `data/neuralweb/theme_state.json` |
| `terminal/lib/upstreams.ts:18` | `NW_BASE` default `https://mastermind-x.com/neuralwebdata` | Base URL for sector themes feed |

**Absences (Terminal epoch):** `rg -n 'theme_graph|selection_cohort' terminal/` → no production matches. Selection cohort has **no** Terminal consumer on this pin.

## Q5 — MATCH / DRIFT / UNKNOWN

| Consumer | Verdict | Reason |
|---|---|---|
| `terminal/lib/sectorIntelligence.ts:63` | MATCH | Requires `schema === "neuralweb.theme_state.v1"`; producer emits `SCHEMA = "neuralweb.theme_state.v1"` (`engine/neuralweb/thematic_state.py:45`) with `themes[].theme_id`, `name_en`, nested `foresight` (`thematic_state.py:426-429`). |
| `terminal/app/api/sector-intelligence/route.ts:16` | MATCH | Pass-through of same artifact bytes; envelope gate above. |
| `terminal/lib/companyThemeExposure.ts:265-271` | MATCH | Expects CTE `theme_state` receipt statuses produced by macro `engine/company_theme_exposure/views.py:32-65` from `neuralweb.theme_state.v1` payload (`schema`, `as_of`, `n_themes`, `themes`, `authority.is_context_only`). |
| `terminal/app/api/company-theme-context/[symbol]/route.ts:9` | MATCH | Normalizes same R2 CTE contract. |
| `terminal/components/fin/CompanyThemeContextCard.tsx:49` | MATCH | Displays receipt fields present in CTE bundle. |
| `terminal/app/api/brain/[...path]/route.ts` | MATCH | Tool handler reads same neuralweb artifact (`ask_brain.py:1563-1606`). |
| `terminal/lib/upstreams.ts:18` | MATCH | URL path aligns with site mirror producer. |
| GMI `theme_state/v2` / selection cohort (no Terminal reader) | UNKNOWN | No static consumer on Terminal epoch; cannot assess field-level match without a wired endpoint. |

**C0 DRIFT headline:** No production DRIFT on main pin between the neuralweb/CTE producers above and Terminal consumers listed; scope `terminal/lib`, `terminal/app/api`, `terminal/components/fin` @ `2ca21c44718a` vs macro producers @ `81eb0c9b3993`.

## Q6 — Human-facing site pages (main pin)

| Page | Artifact | Template / builder |
|---|---|---|
| `site/state_of_themes.html` | Build-time read of `site/neuralwebdata/theme_state.json`, `theme_thesis.json`, `theme_asymmetry.json`, `theme_pathways.json` | `scripts/build_state_of_themes.py:735-742` → `templates/state_of_themes.html.j2:460` (`data-theme-id="{{ th.theme_id }}"`) |
| `site/basketdata/theme_lanes.json` | Derived from same compose context | `scripts/build_state_of_themes.py:8120` `write_theme_lanes()` (called from `scripts/build_site.py:8110-8120`) |

No runtime `fetch('neuralwebdata/theme_state.json')` in `templates/` on main (`rg -n 'theme_state\.json' templates/` → no fetch sites). Macro pages using `mm_brain.js` consume theme state via `/api/brain` tools, not static JSON.

**Site negative:** no page embeds R2 `company_theme_exposure/*` (Terminal-only R2 client).

## Gaps and refusals

- PR #8417 branch name in commission text (`claude/gmi-d1-selection-cohort-20261005`) differs from GitHub head branch `claude/gmi-cte-state-successor-20261004-astra-001`; head SHA matches spec.
- Sparse worktree: `site/` not on disk; all site paths verified via `git ls-tree` / `git show origin/main:<path>`.
- No producer run executed (read-only lane).
