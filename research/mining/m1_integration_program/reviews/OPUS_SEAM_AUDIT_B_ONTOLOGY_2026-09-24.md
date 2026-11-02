# Opus READ_ONLY seam audit — Mining T01'/T04 against the shared GMI base

- Date: 2026-09-24 · MODE: READ_ONLY · ROUTE: review
- Refs consumed by exact sha: `origin/main` = `c00bb2fbdd90`; `refs/remotes/pr/7870` (Semiconductor B, DRAFT) = `dd5076fae5f4`;
  `refs/remotes/pr/7891` (Technology ex-Semis precedent) = `d933eaec69f6`; `origin/sol/mining-principal-research-20260923` = `eb6f05c097c1`.
  NOTE: the task brief named `origin/main` as `b38ba86e` — the fetched ref answers `c00bb2fbdd90`. The seat must
  re-resolve main at lane start (R-IND-22) and never cite the brief's sha.
- Short names below: PLAN = `docs/superpowers/plans/2026-09-24-mining-economic-dossier-implementation.md@eb6f05c0`;
  ADD = `docs/superpowers/plans/2026-09-24-mining-integration-plan-addendum.md@eb6f05c0`;
  SPEC = `docs/superpowers/specs/2026-09-24-mining-shared-foundation-economic-dossier-design.md@eb6f05c0`;
  SEM = `engine/market_ontology/semiconductor_theme_research.py@pr/7870`;
  SEMS = `contracts/market_ontology/semiconductor_theme_research.v1.schema.json@pr/7870`;
  TECH = `engine/market_ontology/technology_economic_change.py@pr/7891`.

## 1. Findings

### F1 — BLOCKER — the frozen plan's T01 commissions the base build the addendum forbids
PLAN:57 lists `engine/market_ontology/theme_research.py — proposed shared` and PLAN:120 instructs
"Extract the shared kernel once"; PLAN:89 hands Mining `compose_theme_research`/`select_theme_evidence`
authorship (PLAN:78-85 code block). ADD:25-27 revokes exactly this: "The original T01 says to extract a shared
kernel ... That is a proposed solution, not a Mining worker's assignment to implement the base. **Replacement
assignment for T01:** consume the accepted shared profile/definition interface ... It may not create or copy
`engine/market_ontology/theme_research.py`, a generic response schema, shared route, private publisher, client
framework or foundation test harness on its own initiative."
CORRECTION: the T01' packet pastes ADD:23-33 verbatim as its governing assignment and carries a literal
DO-NOT-CREATE list (`engine/market_ontology/theme_research.py`, `contracts/market_ontology/theme_research.v1.schema.json`,
any `app/theme_research*.py`, any `site/assets/js/theme-research*.js`). PLAN §3 lines 96-122 must be quoted in the
packet only under a "SUPERSEDED BY ADD:27 — do not implement" header, never as the checklist. A packet that ships
PLAN §3's checklist un-annotated will produce a fork of #7870 in one round.

### F2 — BLOCKER — "the shared kernel validates its output against the selected closed schema" is false on pr/7870
PLAN:89 states the kernel "validates its output against the selected closed schema; passing a Python type hint is
not validation." On the actual head, `_compose` (SEM:967-1015) builds and returns a dict with **no** schema check;
the module's entire import block (SEM:52-61) contains no `jsonschema` and the string `jsonschema` appears nowhere
in SEM (grep over all 1072 lines). `SCHEMA_ID = "semiconductor_theme_research.v1"` (SEM:63) is an ECHOED STRING
in the payload (SEM:985), not a validation binding. The precedent does it the other way: TECH:298-318 lazily
imports `jsonschema`, builds `Draft202012Validator` over its own `CONTRACT_PATH` (TECH:89) and exports
`validate_dossier` in `__all__` (TECH:81).
CORRECTION: `engine/market_ontology/mining_theme_research.py` owns `validate_mining_research(payload) -> None`
on the TECH:298-318 idiom and `compose_mining_research` calls it on every return path. Do not assume, and do not
ask #7870 to add, kernel-side validation.

### F3 — BLOCKER — a bare closed `limitations` enum rejects the codes the plan itself requires
The three vocabularies collide:
- SEMS:251-254 `properties.limitations` is **not** an enum — it is `{"type":"array","items":{"type":"string",
  "pattern":"^[a-z0-9_]+(?::[A-Za-z0-9_.-]+)?$"}}`: a deliberately open, colon-suffixable string set.
- The kernel mints colon-suffixed members: `assertion_invalid:<index>` (SEM:278) and `omitted:<name>` (SEM:287).
- ADD:15 records that the shared guidance helper "now appends `definition_unqualified:<field>` when both prior
  and actual lack a basis, currency, perimeter or definition", and ADD:57 makes a test of exactly that case
  mandatory ("the helper emits `definition_unqualified:definition`").
A closed `"enum": ["stream_threshold_unknown","missing_derivation","definition_unqualified", ...]` therefore
FAILS validation on the one case IR-01 orders tested.
CORRECTION (verbatim, for the Mining schema):
```json
"limitations": {"type": "array", "uniqueItems": true, "items": {"anyOf": [
  {"enum": ["stream_threshold_unknown","missing_derivation","missing_basis","missing_issuer",
            "source_only","internal_transfer","partial_coverage","graph_truncated",
            "availability_unknown_excluded"]},
  {"pattern": "^definition_unqualified:(basis|currency|perimeter|definition)$"},
  {"pattern": "^assertion_invalid:[0-9]+$"},
  {"pattern": "^omitted:[a-z0-9_]+$"}]}}
```
That is still closed (no free strings) and survives the kernel's own emissions.

### F4 — MAJOR — nothing on pr/7870 refuses an unknown slice or a wrong theme/slice pair
PLAN:119 requires "Unknown slice, wrong theme/slice, bool pagination, missing replay cutoff and competing
generation tests must also fail for the intended reasons". On the head:
- `slice_key: Literal['hbm_packaging','sic_gan_specialty']` (SEM:98) is a **typing** annotation — no runtime effect.
- `_validate_query` (SEM:171-181) checks only `limit` bounds (incl. the `bool` trap, SEM:172-174), `offset`,
  `expected_generation_required` (SEM:178) and `replay_cutoffs_required` (SEM:181). It never inspects
  `slice_key` or `anchor_theme_id`.
- A wrong anchor is silently non-selective: `_Selection.__init__` merely skips assertions whose
  `scope.canonical_theme_id != query.anchor_theme_id` (SEM:280, comment "out of scope: ignored, not counted"),
  yielding `authorized_coverage.status == "unavailable"` (SEM:1008) — an empty 200, not a raise.
CORRECTION: the refusal is MINING-OWNED. `mining_theme_research.py` holds the two-row closed definition table and
raises before any composition: `unknown_slice`, `slice_theme_mismatch`. The RED test in
`tests/test_mining_shared_contract.py` asserts those code strings against Mining's own exception class, never
against SEM. Do not file this as a #7870 defect — it is a wrapper responsibility by the precedent's design.

### F5 — MAJOR — resolved: DEFINE the Mining query/bundle dataclasses locally; do not import from #7870
The precedent is unambiguous. TECH imports **no** dataclass from the semiconductor module; it defines
`DossierScope`, `NativeContext`, `IdentityReceipt`, `CoverageSpec` locally (TECH:170-226) and accepts
`DossierScope | Mapping[str, Any]` at the boundary (TECH:1039-1045). The only shared-base coupling is a LAZY
import of `engine.theme_graph.curation_assertion` guarded by a callability probe (TECH:343) that degrades to a
typed `shared_contract_unavailable` section refusal (TECH:1113, doctrine at TECH:14-19). R-IND-17 pins that same
per-sector shape for Industrials.
CORRECTION: Mining defines `MiningResearchQuery` / `MiningOwnerBundle` in its own module with the field names and
meanings PLAN:72/74 enumerate (`revision_tuple, rights_revision, assertions, identity_results, event_workspaces,
financial_packets, interpretation_blocks, native_refs, omissions`; `anchor_theme_id, slice_key, view, time_mode,
source_cutoff, recorded_cutoff, offset, limit, expected_generation` — identical to SEM:96-118) and accepts
`MiningResearchQuery | Mapping`. The public entry name stays `compose_mining_research(query, bundle)` so the
plan's two verbatim tests (PLAN:107-117, PLAN:191-201) compile unchanged. `from engine.market_ontology.
semiconductor_theme_research import ResearchQuery, OwnerBundle` is FORBIDDEN in Mining code and in Mining tests.

### F6 — MAJOR — the delivered mount cannot carry a colon-bearing canonical theme id
`templates/_theme_research_mount.html.j2@pr/7870:22-30` accepts `theme_research_anchor` only if every character is
in `'abcdefghijklmnopqrstuvwxyz0123456789_'` — a `:` sets `_ok.value = 0` and the mount emits NOTHING. But the
canonical ids the plan binds carry the prefix: `theme_node_id: "theme:copper_steel_electrify"`
(`config/theme_crosswalk.yml@main:285`) and `"theme:rare_earth_critical_min"` (:268); the assertion contract
documents `canonical_theme_id` as e.g. `theme:semiconductors`
(`contracts/theme_graph/curation_assertion.v1.schema.json@pr/7870:140-143`); the composer compares raw equality
against it (SEM:280); and the client posts `anchor_theme_id: ANCHOR_THEME_ID` verbatim from the mount attribute
(`site/assets/js/theme-research.js@pr/7870:348,560`). So either the render context supplies a prefixless id and
some unwritten layer re-prefixes, or the mount grammar is wrong. Neither ref resolves it.
CORRECTION: T06 packet states the open question to the shared owner; T04 pins the KERNEL-side form
(`theme:copper_steel_electrify`) in its own schema/tests and does not adopt the mount's grammar.

### F7 — MAJOR — the page can hold exactly ONE theme-research mount
`theme-research.js@pr/7870:345` is `var MOUNT = document.querySelector('[data-theme-research-mount]');` —
singular — and the semiconductor partial hardcodes `id="theme-research"` plus
`data-slices="hbm_packaging,sic_gan_specialty"` (mount:33). `_basket_intelligence_mounts.html.j2@pr/7870:9` is a
one-line router (`{% include "_theme_research_mount.html.j2" ignore missing %}`), so a second sector registers by
adding ONE sibling include line — but if both partials ever render on the same page the second mount is dead and
the DOM id duplicates. Registration point for Mining: one new `templates/_mining_theme_research_mount.html.j2`
plus one `{% include ... ignore missing %}` line appended in `_basket_intelligence_mounts.html.j2`. Blocking ref
for T06; do not resolve it inside T04.

### F8 — MAJOR — the copper witness has no basket page to mount on
`config/theme_crosswalk.yml@main:279` gives `copper_steel_electrify` `primary_basket_id: null` (its only
`basket_ids` entry is `reshoring`, :280-281), while `rare_earth_critical_min` has
`primary_basket_id: critical_minerals` (:262). The delivered mount is a basket-page partial (its asset prefix is
`../assets/...` and its own header says "Basket pages live under site/basket/", mount:12-14). So W-C's entry
surface does not exist today, and the fallback (`reshoring`) is a shared page that can host only one anchor (F7).
Name this in the T06 packet as a gate; T04 must not assume a live entry.

### F9 — MAJOR — the shared POST route family exists on neither ref (T01' `route_unbound` is correct)
`git ls-tree -r --name-only origin/main app/ | grep -i theme` → empty; same for `refs/remotes/pr/7870`. PLAN:65
describes "Existing shared `app/theme_research.py`" — it does not exist. This reproduces R-IND-20 and the
Industrials correction "plan §2 'accepted `app/theme_research.py`' → exists nowhere". The mount declares the route
paths `/api/themes/v1/research/query` and `/api/themes/v1/research/evidence` (mount:33) and the client POSTs JSON
with `credentials: 'same-origin'` (js:594-598, 701-705) — declarations, not an implementation.
CORRECTION: T01' `client()` returning a typed `route_unbound` refusal with `read_count == 0` is binding and
matches R-IND-06 verbatim. To stay inside ADD:27 ("may not create ... a client framework"), the harness lives
ONLY under `tests/`, exports no production symbol, performs no network call, and its refusal object is the whole
of its behaviour.

### F10 — MINOR — `industry_total` is a field of `authorized_coverage`, not a `neighborhood` slot
PLAN:206 says "Keep incomplete neighborhood counts scoped and `industry_total` unknown". On the head the only
carrier is `authorized_coverage` (SEM:1007-1013), whose schema (SEMS:239-249) pins
`"industry_total": {"type": "null"}` (:247) and
`"note": {"const": "counts only what this principal may know exists"}` (:248).
No `neighborhood` key exists anywhere. Mining's schema should mirror `authorized_coverage` and must not mint a
top-level `neighborhood` key no consumer reads (the client renders from the closed section list).

### F11 — MAJOR — CI recipe: new job at END of the file, `scope: exclusive`, paths ⊇ run line
Donor block: `prophet-us-b4-prereg-registration` at `.github/ci/legacy-jobs.yml@main:13451-13480+`
(VERIFIED by line: job name :13451, `if: ${{ false }}` :13462, `gate: code` :13463, `scope: exclusive` :13468,
`paths:` :13469-13472). The file is 16,777 lines on main and is contested
by ≥6 open PRs — append a contiguous block at the END and reorder nothing (R-IND-19, R-IND-22).
`CURATED_EXCLUSIVE` opens at `tests/test_ci_pack.py@main:3508` (the finance lane precedent
`"finance-intelligence"` is at :3528, its comment at :3527) and the set-equality assertion that makes the
declaration binding is `assert declared == CURATED_EXCLUSIVE` at :3765 — the new name lands in the SAME PR.
Note the precedent chose the other form: #7891 minted NO job, appending steps to existing jobs
(`.github/ci/legacy-jobs.yml@pr/7891:10662-10663` and :10600-10601). For Mining, R-IND-19 already ruled the
new-job form for the sibling vertical — mirror R-IND-19, not #7891, and keep `scope: exclusive` honest by
listing every path the suites read.

### F12 — MINOR — pin the unmerged base with a STRICT xfail, not a skip
The accepted precedent does exactly this: "one strict xfail pins the shared curation_assertion round-trip to
#7870" (`.github/ci/legacy-jobs.yml@pr/7891:10660-10661`). A `skip` would stay green forever after the base
lands; `xfail(strict=True)` flips RED the day it does, which is the wanted alarm.

### F13 — MINOR — keep `synthetic_case`, adopt the rest of R-IND-21
R-IND-21 ruled the Industrials loader `load_case(name)` with a `case = load_case` alias. Mining's verbatim tests
call `synthetic_case` (PLAN:112, PLAN:194) and PLAN:132 freezes its contract; renaming would break the frozen
tests. Adopt the transferable half: the loader is DUPLICATED with a source citation, never imported from B's
unmerged helper, and it refuses any fixture whose `synthetic is not True`.

### F14 — MINOR — T04's stated dependency is stale once T01 shrinks to a harness
PLAN:288 says "T04 needs the accepted T01 profile seam and T03 inputs for positive proof", written when T01 owned
the kernel. Under ADD:27 T04's real prerequisites are the casebook (PLAN:132) plus Mining's own schema/module.
The packet must say so explicitly or the lane will block on a seam that no longer exists.

## 2. Seam table

| Plan name (PLAN §2) | origin/main `c00bb2fb` | pr/7870 `dd5076fa` | pr/7891 `d933eaec` | Binding candidate for Mining |
|---|---|---|---|---|
| `engine/market_ontology/theme_research.py` (shared kernel) | absent | absent | absent | **DO NOT CREATE** (F1/ADD:27) |
| `contracts/market_ontology/theme_research.v1.schema.json` | absent | absent | absent | **DO NOT CREATE** |
| Semiconductor composer | absent | `semiconductor_theme_research.py` (1072 ln) | n/a | read-only reference; never imported |
| `ResearchQuery`/`OwnerBundle` | absent | SEM:96-118 | own dataclasses TECH:170-226 | **define locally** (F5) |
| Response schema | absent | SEMS, 14 required keys, `additionalProperties:false` | `technology_economic_change.v1` | Mining mints its own closed schema |
| Assertion contract | absent | `engine/theme_graph/curation_assertion.py` (jsonschema Draft202012, :81-82) | lazy import + typed refusal | LAZY import, typed refusal, never widen v1 |
| Rights registry | `config/theme_sources.yml` (no `sec_edgar`) | + `sec_edgar` family, `rights_class: direct_display_ok`, `auth_class: keyless_public` | n/a | consume; no Mining registry edit |
| Shared POST route | absent | absent (declared only in mount:33) | n/a | `route_unbound` (F9, R-IND-06) |
| Mount aggregator | absent | `_basket_intelligence_mounts.html.j2:9` | n/a | one new partial + one include line (F7) |
| Client JS | absent | `site/assets/js/theme-research.js` (single mount, :345) | n/a | reuse as-is; no second client |
| CI job | donor :13451; `CURATED_EXCLUSIVE` :3508 | n/a | steps appended :10662 | new END-of-file job (F11, R-IND-19) |
| Theme ids | crosswalk:268/285, thesis registry :1182/:1251, pathways :871/:927 | n/a | `_THEME_REF_RE` TECH:148 accepts `theme:` | `theme:copper_steel_electrify`, `theme:rare_earth_critical_min` |

## 3. FROZEN SPEC — T01' (consumption harness)

```
OWNED FILES (create; nothing else):
  tests/mining_casebook.py
  tests/fixtures/mining_economic_dossier/*.json          (11 files, one per case name)
  engine/market_ontology/mining_dependency_binding.py
  tests/test_mining_shared_contract.py
  .github/ci/legacy-jobs.yml   (ONE appended job block at EOF)
  tests/test_ci_pack.py        (ONE line inside CURATED_EXCLUSIVE)
FORBIDDEN: engine/market_ontology/theme_research.py, contracts/market_ontology/theme_research.v1.schema.json,
  any app/**, any site/assets/js/**, any edit to engine/market_ontology/semiconductor_theme_research.py,
  any edit to engine/theme_graph/**, any edit to config/theme_sources.yml.        [ADD:27; F1; F9]
SIGNATURES:
  def synthetic_case(name: str, **overrides) -> MiningCase        # dataclass: query, bundle, expected, account_generation
  CASE_NAMES = ("copper_complete","rare_earth_complete","missing_basis","missing_issuer","source_only",
    "missing_stream_threshold","changed_source","signed_loss","same_horizon_revision","denied_source",
    "page_generation_change")                                     # PLAN:132 — exactly 11, closed
  # unknown name -> raise KeyError(f"unknown case {name!r}; known: {', '.join(CASE_NAMES)}")
  def validate_delivery_inputs(inputs: Mapping[str, Any]) -> dict[str, Any]   # closed dict, no extra keys
  def publication_harness() -> Harness ; Harness.client() -> RouteUnbound      # test-only, no network
  # RouteUnbound: .code == "route_unbound", .read_count == 0, .detail names the two declared paths
IMPORT LAW: the casebook imports NOTHING from engine/market_ontology/semiconductor_theme_research.py.
  The shared assertion contract is imported LAZILY inside the function that needs it, guarded by a
  callable probe, degrading to code "shared_contract_unavailable".                [TECH:14-19,343,1113; F5]
FIXTURE LAW: every fixture carries "synthetic": true and clearly fictional issuer text; a loader that reads a
  fixture whose `synthetic is not True` REFUSES. No real filing body, no real digest, no production registry
  status. Fixtures are the only source of bytes; no network, no clock.            [PLAN:132; R-IND-21]
RED  : python -m pytest tests/test_mining_shared_contract.py -q   # expect KeyError-listing + route_unbound reds
GREEN: python -m pytest tests/test_mining_shared_contract.py -q
MUTANT: delete one CASE_NAMES entry -> KeyError message test fails; make client() return a 200 stub ->
  read_count assertion fails; import ResearchQuery from the semiconductor module -> import-law test fails.
CI BLOCK (append verbatim at EOF of .github/ci/legacy-jobs.yml, donor :13451):
  mining-economic-dossier:
    if: ${{ false }}
    gate: code
    scope: exclusive
    paths:
      - "tests/mining_casebook.py"
      - "tests/test_mining_shared_contract.py"
      - "tests/test_mining_composition.py"
      - "tests/fixtures/mining_economic_dossier/**"
      - "engine/market_ontology/mining_dependency_binding.py"
      - "engine/market_ontology/mining_theme_research.py"
      - "contracts/market_ontology/mining_theme_research.v1.schema.json"
    timeout-minutes: 8
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: install deps for the Mining economic-dossier suites
        run: pip install pytest jsonschema
      - name: mining economic dossier — shared-contract harness + composition
        run: TZ=UTC python -m pytest tests/test_mining_shared_contract.py tests/test_mining_composition.py -q
CURATED_EXCLUSIVE line (tests/test_ci_pack.py:3508 block, same PR):
    "mining-economic-dossier",
```

## 4. FROZEN SPEC — T04 (Mining composer + its own closed schema)

```
OWNED FILES: contracts/market_ontology/mining_theme_research.v1.schema.json
             engine/market_ontology/mining_theme_research.py
             tests/test_mining_composition.py
ENTRY (name frozen by PLAN:113/PLAN:194 — do not rename):
  def compose_mining_research(query: MiningResearchQuery | Mapping[str, Any],
                              bundle: MiningOwnerBundle | Mapping[str, Any]) -> dict[str, Any]
  def select_mining_evidence(query, bundle, assertion_ref: str) -> dict[str, Any]
  def validate_mining_research(payload: Mapping[str, Any]) -> None     # lazy jsonschema, own CONTRACT_PATH
LOCAL DATACLASSES (never imported from #7870 — F5):
  MiningResearchQuery(anchor_theme_id, slice_key, view, time_mode, source_cutoff, recorded_cutoff,
                      offset=0, limit=50, expected_generation=None)          # mirrors SEM:96-106
  MiningOwnerBundle(revision_tuple, rights_revision, assertions, identity_results, event_workspaces,
                    financial_packets, interpretation_blocks, native_refs, omissions)   # SEM:109-118
CLOSED DEFINITIONS (exactly two rows; no caller-supplied dicts — PLAN:74/89):
  "mining_copper_economics"     -> anchor "theme:copper_steel_electrify"
  "mining_rare_earth_economics" -> anchor "theme:rare_earth_critical_min"
  refusals (Mining-owned, since the kernel has none — F4): unknown_slice, slice_theme_mismatch,
  limit_out_of_range, offset_negative, expected_generation_required, replay_cutoffs_required,
  generation_changed  (bool is not an int: reject `True` for limit/offset, SEM:172-176)
SCHEMA top-level keys (closed, additionalProperties:false, all required):
  schema, definition_version, generation, request, native_subjects, summary, companies, industrial_views,
  economics, expectations, evidence_refs, authorized_coverage, limitations, authority
  # same 14 as SEMS; `authorized_coverage.industry_total` is {"type":"null"} and no `neighborhood` key (F10)
  # `economics` adds `native_blocks` for reported_economic_context (PLAN:93) — Mining's schema, not #7870's
LIMITATIONS (closed but colon-aware — F3): use the anyOf block in §1 F3 verbatim.
AUTHORITY: {"can_rank":false,"can_gate":false,"can_size":false,"can_originate":false,"can_open_entry":false}
  echoed literally on every response and every evidence object.                     [SEM:70-76]
PRESENTATION LAW: IR-01 (ADD:55-57) — a `definition_unqualified:*` limitation may coexist with a
  `comparable` classification; NO badge, headline, "beat/miss/improvement" word or model-readable
  confirmed-surprise field may be emitted from it. Management point estimate stays a point estimate; no
  invented lower/upper range (ADD:59-61). Order rows by stable source identity, never by magnitude (PLAN:203).
RED  : python -m pytest tests/test_mining_composition.py -q
GREEN: python -m pytest tests/test_mining_composition.py -q  (8 MGD tests, §6)
MUTANT: flip one authority flag true -> MGD-34 red; set authorized_coverage.industry_total to an int ->
  schema red; emit "definition_unqualified" without its :field suffix -> IR-01 test red; sort economics rows
  by value -> ordering test red; return the payload without validate_mining_research -> contract test red.
CI: no new job — the T04 suites ride the T01' `mining-economic-dossier` block above (paths already list them).
```

## 5. R-IND transfer table (main:`research/industrials/first_vertical_program/rulings/R-IND-2026-09-24-wave1.md`)

| Ruling | Mining T01'/T04 | Why |
|---|---|---|
| R-IND-06 | **TRANSFERS** verbatim | route family absent on both refs (F9); `client()` -> typed `route_unbound`, never a stub route |
| R-IND-10 | DOES-NOT-APPLY to T01'/T04 | Company-Intelligence profile idiom — binds Mining T02 (Auditor A) |
| R-IND-11 | DOES-NOT-APPLY | `IssuerProfile`/`IssuerIdentity` field law — T02 |
| R-IND-12 | DOES-NOT-APPLY (name for T02) | serialization behind #7905/#7870 |
| R-IND-13 / R-IND-14 / R-IND-15 | DOES-NOT-APPLY | rights profile, closed absence reasons, document binding — T02/T03 |
| R-IND-16 | DOES-NOT-APPLY to T01'/T04 seam | comparison-receipt constructor — binds Mining T03 |
| R-IND-17 | **TRANSFERS-WITH-EDIT** | Mining mints its OWN `mining_theme_research.v1` schema + module on the #7891 precedent; #7870's contract is const-pinned and never a target. EDIT: Mining's plan keeps the Semiconductor section name `industrial_views` (PLAN:91) — either rename to a Mining vocabulary or record a seat ruling that the reuse is deliberate |
| R-IND-18 | **TRANSFERS-WITH-EDIT** | `guidance_history.py` exists only on B: delegate `management_sequence` only when importable, else a typed refusal. EDIT: use one Mining-owned code name (recommend `shared_contract_unavailable`, TECH:1113) rather than Industrials' `projector_unbound` |
| R-IND-19 | **TRANSFERS** | END-of-file contiguous job block, donor :13451, `scope: exclusive`, `paths` ⊇ run line, `CURATED_EXCLUSIVE` same PR |
| R-IND-20 | **TRANSFERS** | T05/T06 HELD on the shared route owner; T01' `client()` refusal stands |
| R-IND-21 | **TRANSFERS-WITH-EDIT** | duplicate the loader with a citation + `synthetic is not True` refusal; EDIT: Mining's frozen name is `synthetic_case`, not `load_case` (F13) |
| R-IND-22 | **TRANSFERS** | branch from freshly fetched `origin/main`, consume #7870 by exact sha; the brief's `b38ba86e` already disagrees with the fetched `c00bb2fb` |

## 6. MGD -> task map (`research/mining/MINING_IMPLEMENTATION_TRACE_2026-09-24.json@eb6f05c0`, 40 rows)

- **T01 (2)** — MGD-01 `tests/test_mining_shared_contract.py::test_single_shared_kernel`;
  MGD-04 `…::test_legacy_sector_parity`.
- **T04 (8)** — MGD-08 `tests/test_mining_composition.py::test_two_positive_economic_paths`;
  MGD-09 `::test_security_without_issuer_refuses_financial_join`;
  MGD-10 `::test_current_identity_not_historical_ownership`;
  MGD-11 `::test_source_only_business_stays_useful`;
  MGD-12 `::test_shared_asset_not_duplicate_supply`;
  MGD-18 `::test_missing_threshold_keeps_contract_explanation`;
  MGD-34 `::test_authority_literal_false`;
  MGD-39 `::test_coverage_not_global_census`.
- **T07 (5)** — MGD-24 `tests/test_mining_updates.py::test_retrospective_not_system_replay`;
  MGD-26 `::test_target_not_aged_into_fact`; MGD-27 `::test_new_fact_does_not_reuse_old_interpretation`;
  MGD-28 `::test_pagination_revision_tuple_coherent`; MGD-35 `::test_incumbent_market_outputs_unchanged`.
- Others (context, not this audit): T02 {13,14,25}; T03 {15,16,17,19,20,21,22,23}; T05 {29,30,31,33};
  T06 {3,5,32,36}; T08 {2,6,7,37,38,40}.
- NOTE: MGD-01's text is "One accepted shared assertion schema/validator is imported; no Mining copy or
  alternative identity generator exists" — an IMPORT-LAW test, which is exactly what survives the T01 -> T01'
  shrink. MGD-04 (`test_legacy_sector_parity`) cannot run until #7870 merges: mark it
  `xfail(strict=True)` (F12), not skip.

## 7. Blocking refs for T05 / T06 (named only — out of scope)

- **T05** — `app/theme_research.py` does not exist on `origin/main` or `refs/remotes/pr/7870`
  (`git ls-tree -r --name-only <ref> app/ | grep -i theme` -> empty). Declared route paths live only in
  `templates/_theme_research_mount.html.j2@pr/7870:33`
  (`/api/themes/v1/research/query`, `/api/themes/v1/research/evidence`), and the POST shape only in
  `site/assets/js/theme-research.js@pr/7870:594-598` / `:701-705` (`credentials: 'same-origin'`).
  R-IND-20 names the only alternative (a bounded owner-approved extension of `app/earnings.py`) as a later
  ruling, not a packet.
- **T06** — (a) mount aggregator `templates/_basket_intelligence_mounts.html.j2@pr/7870:9`;
  (b) single-mount law `site/assets/js/theme-research.js@pr/7870:345` (F7);
  (c) anchor grammar `templates/_theme_research_mount.html.j2@pr/7870:22-30` vs
  `config/theme_crosswalk.yml@main:268,285` (F6);
  (d) copper has no primary basket page, `config/theme_crosswalk.yml@main:279` (F8).

## 8. What this audit could NOT verify

1. No `gh` calls were permitted, so every #7870/#7891 comment id quoted in ADD (`5809602368`, `5809358801`,
   `5809893850`, `5810041817`) is UNVERIFIED here — the seat must confirm before treating any as an owner
   assignment (ADD:29: "A response that says only 'boundary accepted' is not that assignment").
2. #7870's live head may have moved past `dd5076fa`; ADD:15 cites candidate `c6c67c87` for
   `engine/company_intelligence/guidance_history.py`. The three identities (`b256aa6a`, `c6c67c87`, `dd5076fa`)
   were not reconciled. Re-resolve at lane start (R-IND-22).
3. What the render context sets `theme_research_anchor` to on a basket page was not traced to its producer
   (only the consumer side was read), so F6 is stated as an unresolved contradiction, not as a proven defect
   in either ref.
4. (closed on re-verification) SEMS `properties.limitations` :251-254 and `properties.authorized_coverage`
   :239-249 were confirmed by line at `dd5076fa`.
5. `pip install` contents for the new CI job were reasoned from the suites' imports (pytest + jsonschema), not
   measured on a runner; R-IND-19 requires the pip line measured per suite before the job is armed.
6. (closed on re-verification) `tests/test_ci_pack.py:3765` reads `assert declared == CURATED_EXCLUSIVE,
   sorted(declared ^ CURATED_EXCLUSIVE)` — a set-equality gate, so a job block added without its
   `CURATED_EXCLUSIVE` line (or vice versa) reds this suite in the same PR.
7. Tool-call budget: 19 calls total (report written at call 17, verified at 18, corrected at 19); limit 28,
   zero `gh` calls, zero writes inside the worktree.
