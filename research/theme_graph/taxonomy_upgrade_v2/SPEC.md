# PROGRAM SPEC — GMI TAXONOMY V2 (FROZEN 2026-10-12, seat 6f14c2da)

> Record of issue. Date 2026-10-12 · Workstream WS:GMI-THEME-GRAPH · Decision DEC:GMI-TAXONOMY-UPGRADE-V2 (population rule DEC:GMI-SUB-THEME-POPULATION-KEEP-ADD) · Seat 6f14c2da.
> The sections below are the text issued verbatim to every Taxonomy V2 build lane; "you" addresses the build lane. Where this text and the merged code or tests differ, the code and tests are the authority.

## §0 Context, invariants, exclusions
- Program WS:GMI-THEME-GRAPH. Taxonomy V2 adds (a) an optional `sub_theme` tier between `theme` and `micro_theme` in the GMI theme graph, and (b) a family of display-tier CLASSIFICATION AXES (SEC industry, geography, macro sensitivity, business model, lifecycle, value chain) read on demand as uniform `AxisCell` records. Downstream canonical consumer: MarketOntology F04 (it will consume these readers later; you do not wire it).
- Everything is DISPLAY/CONTEXT tier: no weights, shares, scores, ranks, exposure percentages, composites, trade sizing, or gate authority. A missing value is a typed null with a reason, never a zero and never a guess.
- Axes are PURE READERS over incumbent artifacts (Gate #8): they never write files, never persist state, never call the network, never call an LLM.
- Theme ids are house vocabulary only. `ltheme:finviz:*` / `ltheme:ths:*` (vendor local themes) and the suites `finviz_themes` / `ths_concepts` are INTERNAL-ONLY (Gate #2) and are never a subject, input, or output of anything in this program.
- `micro_theme` is NOT renamed. Existing node ids, edge ids, proposal ids and materialized bytes for a crosswalk WITHOUT sub_themes must be byte-identical before/after your change.

## §1 sub_theme tier (FROZEN)
- Tiers of a kind=theme node: `macro_category`, `theme`, `sub_theme` (NEW, optional), `micro_theme`.
- PARENT_OF adjacency (parent→child), exactly these four pairs: (macro_category,theme), (theme,sub_theme), (sub_theme,micro_theme), (theme,micro_theme). Every other pair is refused (e.g. macro_category→sub_theme, sub_theme→theme, sub_theme→sub_theme, micro_theme→sub_theme, macro_category→micro_theme). A theme→micro_theme edge WITHOUT a sub_theme stays valid forever.
- sub_theme nodes: kind=theme, market_scope global, provenance `crosswalk:config/theme_crosswalk.yml`, house curated (licensing `mastermind_curated`, evidence `operator_curation`), like micro_theme. No EXPRESSES / MEMBER_OF edges ever point to or from a sub_theme or micro_theme id (NEW_TIER_IN_EXPRESSES_MAP).
- Crosswalk block `hierarchy.sub_themes` (a list, optional). Row keys: allowed `id, name_en, name_zh, asserted_on, nominated_from, note, value_chain_position`; required `id, name_en, name_zh, asserted_on, nominated_from`. `hierarchy.micro_themes` rows gain the OPTIONAL key `value_chain_position`. `hierarchy.categories` rows do NOT accept it (unknown key → BLOCK_SHAPE).
- `value_chain_position` ∈ {`upstream`, `midstream`, `downstream`, `enabler`}; any other value → reason `VALUE_CHAIN_POSITION`. It is a DISPLAY ATTRIBUTE stored in the node's `source_meta` JSON only when present — never an edge, never a score, never a weight.
- Validation reasons that already exist extend to sub_themes unchanged in meaning: DUPLICATE_ID (across categories+sub_themes+micro_themes), CROSS_TIER_REUSE (a sub id equal to a legacy crosswalk theme id), UNDECLARED_ENDPOINT, CYCLE, NON_ADJACENT_TIERS, TOO_MANY_PARENTS (>3), NEW_TIER_IN_EXPRESSES_MAP, SLUG_GRAMMAR, ASSERTED_ON_MISSING, ASSERTED_ON_PRE_EPOCH, and the nominated_from reasons (delegated to `probation.nominated_from_errors` — a vendor or malformed nominator still fails).
- Declaration / validation / emission order: categories → sub_themes → micro_themes.
- `validate_theme_hierarchy` return dict carries a `sub_themes` key ONLY when the hierarchy mapping itself contains the key `sub_themes` (present-key semantics; an absent block returns exactly the three legacy keys — existing count assertions depend on this).
- Emitted sub_theme / micro_theme node `source_meta` = `{"nominated_from": <row value>}` plus `"value_chain_position": <value>` only when the row carries it. A micro_theme row without value_chain_position emits exactly the legacy `{"nominated_from": …}`.
- Probation (hierarchy proposals): `child_tier` may be `theme`, `sub_theme` or `micro_theme`. An LLM-originated proposal may PROPOSE but never ratify (existing probation law, unchanged).

## §2 AxisCell v1 contract (FROZEN) — home `engine/classification_axes/cell.py` + `contracts/classification_axes/axis_cell.v1.schema.json`
An AxisCell is a JSON-serialisable dict with EXACTLY these keys (no others):
- `schema_version`: const `"axis_cell.v1"`.
- `axis`: one of `sic_industry`, `geography`, `macro_sensitivity`, `business_model`, `lifecycle`, `value_chain` (constant `AXES` tuple in cell.py, this order).
- `subject_id`: a subject id per §3.
- `status`: one of `available`, `unknown`, `unavailable`, `stale`, `not_applicable`, `rights_blocked`.
- `reason_code`: null iff status is `available`; otherwise exactly one of the codes allowed for the status:
  available → null · unknown → `value_missing` | `history_not_supported` · unavailable → `owner_missing` | `owner_unavailable` | `owner_degraded` · stale → `owner_stale` · not_applicable → `not_applicable` | `retired_entity` | `superseded_entity` · rights_blocked → `rights_blocked`.
- `value`: REQUIRED non-null when `available`; MAY be non-null (the last known value) when `stale`; MUST be null for every other status. Any JSON value (str, int, finite float, bool, list, dict with str keys). No dict key at any depth whose lower-cased name contains `weight`, `share`, `score`, `rank` or `exposure_pct`. Counts are allowed.
- `unit`: str or null.
- `observed_at`, `effective_at`: null or an ISO date `YYYY-MM-DD` or ISO datetime (first 10 chars a date).
- `as_of`: REQUIRED `YYYY-MM-DD` (the caller's point-in-time). Point-in-time law: an `available` or `stale` cell whose `observed_at` or `effective_at` date (first 10 chars) is AFTER `as_of` is invalid — a reader must instead return `unknown`/`history_not_supported`.
- `freshness`: null or `{"age_days": int >= 0, "max_age_days": int >= 1}`.
- `quality`: const `"display_only"` (not a parameter; always set by the constructor).
- `labels`: sorted list of unique strings ⊂ {`proxy_not_micro_membership`, `NO_MAPPING`, `source_local`, `house_curated`, `read_time_composition`} (empty list allowed).
- `source`: `{"owner": non-empty str, "artifact": non-empty str, "field": str or null}` — owner = the incumbent module/producer, artifact = repo-relative path or reader function, field = column/key read.
- `provenance`: list of non-empty strings (order preserved).
- `rights_context`: null or `{"license_class": non-empty str, "basis": non-empty str}` — a STATIC per-source constant declared by the reader module, NEVER computed by a resolver (Gate #8).
Python API in `engine/classification_axes/cell.py` (exact names):
- `SCHEMA_VERSION`, `AXES`, `STATUSES`, `REASON_CODES` (dict status → tuple of allowed codes; available → `()`), `LABELS` (frozenset), `FORBIDDEN_VALUE_KEY_WORDS = ("weight", "share", "score", "rank", "exposure_pct")`.
- `class AxisCellError(ValueError)` carrying `.problems: list[str]`.
- `validate_cell(cell: object) -> list[str]` — returns `[]` for a valid cell and one human-readable problem string per violation otherwise; NEVER raises for any input (None, list, garbage).
- `make_cell(*, axis, subject_id, status, as_of, source, value=None, reason_code=None, unit=None, observed_at=None, effective_at=None, freshness=None, labels=(), provenance=(), rights_context=None) -> dict` — builds the dict (labels sorted+deduped, provenance as list, quality set), runs `validate_cell`, raises `AxisCellError` if non-empty, else returns it.
- `available(*, axis, subject_id, value, as_of, source, **optional) -> dict` and `missing(*, axis, subject_id, status, reason_code, as_of, source, **optional) -> dict` — thin wrappers over `make_cell` (`missing` refuses status `available`).
- `parse_subject(subject_id: str) -> tuple[str, str]` → `(kind, rest)` per §3; raises `AxisCellError` for anything else.
- `company_parts(subject_id: str) -> tuple[str, str, int | None]` → `(market, symbol, epoch_or_None)` for a valid `co:` id; raises `AxisCellError` otherwise.
- `to_json(cell) -> str` — `json.dumps(cell, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))`.
The JSON schema (draft 2020-12, `additionalProperties: false`) must accept every cell `make_cell` can return and reject the status/reason/value/quality/schema_version/as_of/labels violations expressible in JSON Schema (use `allOf` + `if/then` per status). The forbidden-key and point-in-time rules are Python-only (document that in the schema `description`).

## §3 Subject ids (reuse `engine/theme_graph/identity.py`; NEVER copy its regexes)
- `co:<market>:<SYMBOL>[#n]` — valid iff `identity.COMPANY_ID_RE.fullmatch(subject_id)`.
- `theme:<slug>` — slug grammar `^[a-z0-9][a-z0-9_]{1,62}$` (the house theme-id grammar used by `scripts/check_theme_graph_contracts.py` THEME_NODE_ID_RE; define it once in cell.py as `THEME_SUBJECT_RE` with that citation — scripts/ is not importable from engine/).
- `basket:<suite>:<basket_id>` — valid iff `identity.basket_node_id(suite, basket_id) == subject_id` (it raises for unknown suites and for `identity.NON_BASKET_SUITES`); additionally refuse any suite containing `finviz_themes` or `ths_concepts`.
- `etf:<SYMBOL>` — valid iff `identity.etf_node_id(symbol) == subject_id`.
- `ltheme:*` and every other prefix → `AxisCellError` (Gate #2: vendor local themes are never subjects).

## §4 Reader conventions (lanes L05–L10; L00 only defines the cell)
- One module per axis: `engine/classification_axes/<axis>.py` exposing `AXIS`, `SOURCE_OWNER`, `SOURCE_ARTIFACT`, `MAX_AGE_DAYS` (int or None), `RIGHTS_CONTEXT` (dict or None), `SUBJECT_KINDS` (tuple of §3 kinds it covers) and exactly one public reader `read_<axis>(subject_id, *, as_of, root=None, <named injected inputs>=None) -> dict`.
- Every return passes `validate_cell` (build through `cell.available` / `cell.missing`).
- Status mapping: subject kind not in `SUBJECT_KINDS` → not_applicable/not_applicable · default artifact absent → unavailable/owner_missing · artifact unreadable/corrupt → unavailable/owner_degraded · subject absent from artifact → unknown/value_missing · artifact cannot answer an `as_of` earlier than its own observation → unknown/history_not_supported · age > MAX_AGE_DAYS → stale/owner_stale (value = last known) · retired/merged entity → not_applicable/retired_entity | superseded_entity.
- Inputs: default paths resolve under `root` (default = repo root derived from `Path(__file__).resolve().parents[2]`), READ-ONLY. Tests pass injected in-memory inputs or fixtures under `tests/fixtures/classification_axes/<axis>/` (owned by that lane only). Never read `data/**` in tests.
- Never import `engine.intelligence_workspace`, `engine.market_ontology`, `engine.company_intelligence`, another axis reader, or any `scripts/*` module.
- Deterministic: no wall-clock (`as_of` is the clock), no caching across calls, stable ordering inside `value`.

## §5 Reuse mandates
- Theme graph data comes only through `engine/theme_graph/store.py` readers (`read_nodes(current=True)`, `read_edges`, `read_node_lifecycle`, …) or an injected equivalent; `RETIRED_LIKE_STATUSES` decides retired/merged.
- Identity grammar comes only from `engine/theme_graph/identity.py`.
- Incumbent owners named in a lane spec are extended or wrapped, never duplicated or replaced.
