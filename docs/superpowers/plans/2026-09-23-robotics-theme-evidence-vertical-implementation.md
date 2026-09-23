# Robotics Theme Evidence Vertical Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (\`- [ ]\`) syntax for tracking.

**Goal:** Ship the first evidence-bound Robotics research vertical so an entitled reader can move from Theme Tracker or the existing Robotics detail page into Precision Motion / Perception research, distinguish catalog capability from documented inclusion or forward arrangements, inspect dated source evidence and uncertainty, and return to the incumbent stock/theme workflow without changing any ranking, entry, sizing, basket or trade behavior.

**Architecture:** Extend the existing Theme Graph evidence owner with one optional, canonical-JSON \`theme_graph.curation_assertion.v1\` payload and validate/round-trip it through the incumbent evidence store. Add an explicit Evidence Foundation owner subtype for that payload, compose a deterministic F04 read-only Robotics dossier from accepted evidence plus existing identity-resolution rows, and expose the result only through the existing paid Macro API boundary. Both existing pages receive a public shell plus one shared public JavaScript/CSS client that hydrates the private payload through \`theme.js\` / \`MDXAuth\`; full-fidelity current research never ships in static HTML or public JSON.

**Tech Stack:** Python 3.14, FastAPI, pandas/pyarrow, jsonschema Draft 2020-12, pytest, Jinja2 static templates, vanilla browser JavaScript/CSS, existing Theme Graph readers/writer, existing Evidence Foundation contracts, existing Macro API \`site_full\` entitlement boundary.

**Spec:** \`docs/superpowers/specs/2026-09-23-robotics-theme-evidence-vertical-design.md\`

## Global Constraints

- Protected procedure pin for this plan: Mastermind \`89582a372aa2a57ec500868ce6d79cd156219445\`, Skillpack 1.0.1/bootstrap 1.
- Macro interface pin used to write this plan: \`a6314d0192e0884f2fab29042c6143f2e1f74ad6\`.
- Research/design carrier: draft/HOLD PR #7773 / \`sol/robotics-bom-research-20260923\`; implementation code starts on a fresh implementation carrier from then-current \`main\` after the collision gates below, not on this 11-commit-behind research branch.
- Preserve the existing Theme Graph, ThemeState, Evidence Foundation, F04, identity, auth, publication, correction, queue and scheduler owners. Do not create a robotics database, second graph, second latest-state file, second evidence ledger or new watcher service.
- \`curation_assertion\` is optional and additive. Every legacy evidence row remains valid with the field absent/null.
- Store the assertion as canonical JSON text in the flat evidence parquet column; decode and validate it before any consumer use. A schema-only field that \`EVIDENCE_COLUMNS\` drops is a failure.
- First accepted assertion types are exactly: \`PRODUCT_CAPABILITY\`, \`DOCUMENTED_PRODUCT_INCLUSION\`, \`ANNOUNCED_DEVELOPMENT_AGREEMENT\`, \`DEPLOYMENT_TARGET\`, \`REPORTED_DEPLOYMENT\`, \`OWNERSHIP_EVENT\`, \`REPORTED_FINANCIAL_MEASURE\`, \`REPORTED_OPERATING_MEASURE\`.
- First statement modes are exactly: \`REPORTED_FACT\`, \`CATALOG_DESCRIPTION\`, \`ANNOUNCED_ARRANGEMENT\`, \`FORWARD_TARGET\`, \`ATTRIBUTED_INTERPRETATION\`.
- Keep upstream publication, observation, retention, review, curation publication and business-effective clocks distinct. Unknown source publication is never replaced by observation/review time.
- Products/configurations/business units remain source-scoped descriptions in v1. Similar labels never mint or merge a global product identity.
- Existing GMI/Data-OS identity resolution is the only security/listing bridge. An unresolved company may render attributed source text but receives no valuation, price, portfolio or live-stock enrichment.
- K1 remains a reference layer; the new curation subtype has all authority flags false and may not create a cross-type bridge.
- BOM quantities require an explicit basis such as \`per_robot\`, \`per_joint\`, \`per_hand\`, \`per_cell\`, or \`per_installation\`; no implicit multiplicity.
- The first product view is unweighted. No component-cost Sankey or bottleneck composite ships unless comparable cost/scarcity evidence exists.
- Full-fidelity current research must not be committed to public Git, Pages, public R2, source maps or static HTML. Code/contracts/tests may be public; live detailed assertion admission is held until the incumbent private publication path proves that the payload cannot escape.
- Paid API responses and all paid error paths use \`Cache-Control: private, no-store\`, \`Vary: Authorization\`, \`X-Content-Type-Options: nosniff\`, and \`X-Robots-Tag: noindex, noarchive\`.
- No first-unit change to basket membership, basket weights, theme recommendation, Theme Tracker lane, member ranking, Prophet admission, entry gates, sizing, alerts or trading.
- No live data admission or deployment proof may proceed while the private publication gate is unproven. Code may be tested with fixtures without converting that gap into a success claim.
- Collision gate A: #7462 currently owns \`engine/theme_graph/store.py\` at head \`31706d7322af55696dc7b2e746ec511b08bd51d7\`. Before Task 2 touches that path, reconcile #7462 to terminal/accepted state or obtain current source-writer release; never edit its branch.
- Collision gate B: #7669 currently touches \`templates/basket_detail.html.j2\` at head \`2c28d950aa9448fc878bb64d92b228a8f1952bde\`. Before Task 6 touches that path, reconcile its exact accepted successor/current main. Do not transplant an old template hunk.
- #7664 currently owns \`scripts/build_state_of_themes.py\`, but this plan intentionally does not modify that file; Theme Tracker research hydration is client-side.
- #7455 and #7633 do not overlap the planned write paths at this plan pin; re-check only if their heads or planned files change materially.
- Every task uses TDD: failing discriminating test → prove red → minimal implementation → prove green → focused regression → commit.
- Production completion requires real accepted source → native qualification → entitled API → visible existing-page result plus alternate-mirror negative proof; CI green or a schema alone is not completion.

## Review Focus

1. **Same URL/date but changed source bytes or two separate statements:** identities must remain distinct and corrections append instead of mutating the prior assertion. Task 1 tests both.
2. **Unauthorized paid fetch:** entitlement denial must happen before Theme Graph/private publication access and every denial/error must preserve private-no-store headers. Task 5 tests this explicitly.
3. **Generation/configuration drift:** a component quantity documented for one robot/configuration must not silently propagate to a newer generation. Task 4 tests configuration matching and typed non-applicability.
4. **Announcement versus completed operating fact:** future deployment targets and announced ownership events must not render as installed units or completed ownership. Tasks 1 and 4 test statement mode and effective-date behavior.
5. **Assembly/quantity double counting:** integrated actuator plus contained motor/reducer/encoder and per-hand→per-robot arithmetic must refuse rather than produce a plausible total. Task 4 tests both.

---

## File Map

### Native evidence owner
- Create \`contracts/theme_graph/curation_assertion.v1.schema.json\` — closed payload schema for one reviewed source-scoped assertion.
- Create \`engine/theme_graph/curation_assertion.py\` — canonical JSON, deterministic curation revision/source selector, validation, encode/decode, and evidence-row helpers.
- Modify \`contracts/theme_graph/evidence.v1.schema.json\` — optional nullable \`curation_assertion\` field.
- Modify \`engine/theme_graph/store.py\` — append \`curation_assertion\` to \`EVIDENCE_COLUMNS\`; no new path/key/writer.
- Modify \`scripts/check_theme_graph_contracts.py\` — validate any non-null encoded assertion using the new contract.
- Create \`tests/test_theme_graph_curation_assertion.py\` and extend \`tests/test_theme_graph_contracts.py\`.

### Evidence Foundation binding
- Modify \`contracts/evidence_foundation/vocabulary.v1.json\` — add \`theme_graph.curation_assertion\` owner subtype over the existing physical evidence reader.
- Extend \`tests/test_evidence_foundation_contract.py\` — positive subtype reference plus lost-clock/authority/cross-type hostile cases.
- Do not modify \`lib/evidence_foundation.py\` unless a failing generic-contract test proves the existing validator cannot represent the accepted nested clock binding.

### F04 composition
- Create \`contracts/market_ontology/robotics_theme_research.v1.schema.json\` — private consumer payload contract.
- Create \`engine/market_ontology/robotics_theme_research.py\` — pure, deterministic owner-reader composer.
- Create \`tests/test_market_ontology_robotics_theme_research.py\`.

### Paid transport
- Create \`app/robotics_research.py\` — entitled read-only endpoint and private headers.
- Modify \`app/main.py\` — unconditional router import/include, matching paid-route fail-loudly precedent.
- Create \`tests/test_robotics_research_api.py\`.
- Extend \`tests/test_site_access_boundary.py\` only if the new route exposes a policy regression; \`/api/*\` already belongs to macro-api.

### Existing-page UI
- Create \`site/assets/js/robotics-theme-research.js\` — shared auth/fetch/hydration logic; no embedded data.
- Create \`site/assets/css/robotics-theme-research.css\` — shared accessible layout/diagram/table styling.
- Modify \`templates/state_of_themes.html.j2\` — Robotics-only public shell/link and shared asset includes.
- Modify \`templates/basket_detail.html.j2\` — generic hidden research mount, activated only for \`robotics_automation\`, plus shared asset includes.
- Create \`tests/test_robotics_theme_research_ui.py\`.

### Qualification
- Do not commit live detailed assertions into \`data/theme_graph/evidence.parquet\` while the repository-backed store remains publicly readable.
- Production admission uses only an already-approved private owner/publication binding proven during execution; if that binding is absent, stop at the explicit privacy gate and do not invent another storage plane.
- Browser evidence and source/mirror checks live under the incumbent acceptance/evidence owner chosen at execution time; do not create another latest-state directory in this plan.

---

### Task 1: Freeze and Validate the Native Curation Assertion Contract

**Files:**
- Create: \`contracts/theme_graph/curation_assertion.v1.schema.json\`
- Create: \`engine/theme_graph/curation_assertion.py\`
- Create: \`tests/test_theme_graph_curation_assertion.py\`

**Interfaces:**
- Consumes: source-scoped reviewed research values from the approved spec.
- Produces:
  - \`validate_assertion(payload: Mapping[str, Any]) -> dict[str, Any]\`
  - \`curation_revision(payload: Mapping[str, Any]) -> str\`
  - \`encode_assertion(payload: Mapping[str, Any]) -> str\`
  - \`decode_assertion(value: object) -> dict[str, Any] | None\`
  - \`source_ref_for(payload: Mapping[str, Any]) -> str\`
  - revision grammar: \`gmirca_[0-9a-f]{32}\`

- [ ] **Step 1: Write the failing schema/identity tests**

Create fixtures inline in \`tests/test_theme_graph_curation_assertion.py\`; the smallest valid assertion must include these exact shapes:

\`\`\`python
def valid_assertion(**overrides):
    row = {
        "schema": "theme_graph.curation_assertion.v1",
        "curation_revision": None,
        "review": {
            "disposition": "accepted",
            "reviewed_at": "2026-09-23T07:00:00Z",
            "reviewer": "sol",
            "review_due_at": None,
        },
        "source": {
            "publisher": "Orbbec",
            "source_uri": "https://www.orbbec.com/case-studies/example",
            "locator": "NarGo configuration paragraph",
            "published_at": None,
            "published_at_grain": "unknown",
            "observed_at": "2026-09-23T06:00:00Z",
            "retained_at": "2026-09-23T06:05:00Z",
            "retention_ref": "research-vault://source/orbbec-nargo",
            "native_digest": None,
        },
        "subject": {
            "company_node_id": "co:us:ORBBEC_PRIVATE_EXAMPLE",
            "source_business_label": "Orbbec",
            "source_product_label": "Gemini 335",
            "source_platform_label": None,
            "configuration": None,
        },
        "object": {
            "source_product_label": "NarGo order-picking robot",
            "configuration": "described case-study configuration",
        },
        "predicate": "DOCUMENTED_PRODUCT_INCLUSION",
        "statement_mode": "REPORTED_FACT",
        "scope": {
            "canonical_theme_id": "robotics_automation",
            "application": "warehouse_robotics",
            "technology_facet": "perception",
            "region": None,
            "period": None,
            "denominator": None,
        },
        "observation": {
            "value": 2,
            "value_high": None,
            "unit": "camera",
            "quantity_basis": "per_robot",
            "gross_net_basis": None,
            "stock_flow": None,
            "estimate_status": "reported",
            "precision": "integer",
        },
        "temporal": {
            "business_valid_from": None,
            "business_valid_to": None,
        },
        "limitations": {
            "establishes": ["two cameras in the described configuration"],
            "does_not_establish": ["price", "annual shipments", "all generations"],
            "coverage": "single described configuration",
            "source_dependence": "publisher_statement",
            "expiry_trigger": "new configuration or corrected source",
        },
        "correction": {
            "predecessor_revision": None,
            "reason": None,
        },
        "authority": {
            "can_rank": False,
            "can_gate": False,
            "can_size": False,
            "can_originate": False,
            "can_open_entry": False,
        },
    }
    row.update(overrides)
    return row
\`\`\`

Tests must pin: unknown publication stays null; \`FORWARD_TARGET\` cannot pair with \`REPORTED_DEPLOYMENT\`; quantities reject NaN/inf/negative/basis-free values; unresolved company_node_id may be null; authority is literal all-false; two assertions with different locators produce different revisions; changing retained/source bytes produces a new revision; predecessor correction does not change the prior revision.

- [ ] **Step 2: Run the new tests and prove they fail**

Run:

\`\`\`bash
python3 -m pytest tests/test_theme_graph_curation_assertion.py -q
\`\`\`

Expected: import/schema failures because the module/schema do not exist.

- [ ] **Step 3: Implement the closed schema**

The schema must use \`additionalProperties:false\` at every object layer, require the fields above, encode the closed assertion/statement/quantity vocabularies from Global Constraints, allow nullable source/business dates, reject non-finite JSON numbers by semantic validation, and require the all-false authority object.

Freeze \`curation_revision\` as either null during revision computation or \`^gmirca_[0-9a-f]{32}$\` after materialization.

- [ ] **Step 4: Implement canonical revision and codec**

Use canonical UTF-8 JSON with sorted keys and compact separators. Revision input is the complete validated payload with \`curation_revision\` removed; do not omit locator, retention, scope, review or correction fields.

\`\`\`python
SCHEMA = "theme_graph.curation_assertion.v1"
_REVISION_RE = re.compile(r"^gmirca_[0-9a-f]{32}$")

def _canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")

def curation_revision(payload: Mapping[str, Any]) -> str:
    candidate = dict(payload)
    candidate.pop("curation_revision", None)
    validate_assertion(candidate, allow_unstamped=True)
    return "gmirca_" + hashlib.sha256(_canonical_bytes(candidate)).hexdigest()[:32]

def encode_assertion(payload: Mapping[str, Any]) -> str:
    candidate = dict(payload)
    expected = curation_revision(candidate)
    stamped = {**candidate, "curation_revision": expected}
    validate_assertion(stamped)
    return _canonical_bytes(stamped).decode("utf-8")

def decode_assertion(value: object) -> dict[str, Any] | None:
    if value is None or value == "":
        return None
    payload = json.loads(str(value))
    validate_assertion(payload)
    if payload["curation_revision"] != curation_revision(payload):
        raise CurationAssertionError("curation_revision_mismatch")
    return payload

def source_ref_for(payload: Mapping[str, Any]) -> str:
    stamped = decode_assertion(encode_assertion(payload))
    return f"gmi-curation://robotics/{stamped['curation_revision']}"
\`\`\`

- [ ] **Step 5: Run focused contract tests**

\`\`\`bash
python3 -m pytest tests/test_theme_graph_curation_assertion.py -q
\`\`\`

Expected: PASS.

- [ ] **Step 6: Commit the isolated contract**

\`\`\`bash
git add contracts/theme_graph/curation_assertion.v1.schema.json \
        engine/theme_graph/curation_assertion.py \
        tests/test_theme_graph_curation_assertion.py
git commit -m "feat(theme-graph): define robotics curation assertions"
\`\`\`

---

### Task 2: Round-trip the Optional Assertion Through the Existing Theme Graph Evidence Store

**Files:**
- Modify: \`contracts/theme_graph/evidence.v1.schema.json:8-66\`
- Modify: \`engine/theme_graph/store.py:67-76\`
- Modify: \`scripts/check_theme_graph_contracts.py\`
- Modify: \`tests/test_theme_graph_contracts.py\`

**Interfaces:**
- Consumes: \`encode_assertion()\` / \`decode_assertion()\` from Task 1.
- Produces: the existing \`store.read_evidence()\` / \`store.write_evidence()\` surface with one additive \`curation_assertion\` column; no new writer or key.

**Collision gate:** reconcile #7462 before the first edit to \`engine/theme_graph/store.py\`. If it is still active, do not edit its branch; continue only path-disjoint plan tasks until custody is released.

- [ ] **Step 1: Add failing round-trip and hostile-store tests**

Extend \`_evidence_row()\` with \`curation_assertion=None\`, then add tests that:
- a legacy row with null assertion still passes;
- \`write_evidence(..., lane="nightly")\` preserves encoded assertion bytes through parquet readback;
- malformed assertion JSON breaches;
- a valid JSON object with wrong revision breaches;
- unknown extra keys inside the assertion breach;
- the evidence writer does not silently drop the new column.

Use a monkeypatched \`evidence_path()\` temp path; do not touch repository data.

- [ ] **Step 2: Run the exact failing tests**

\`\`\`bash
python3 -m pytest \
  tests/test_theme_graph_contracts.py \
  -q
\`\`\`

Expected: the new column/semantic tests fail before implementation.

- [ ] **Step 3: Extend the evidence schema and flat column list**

Append this optional property to \`evidence.v1.schema.json\`:

\`\`\`json
"curation_assertion": {
  "type": ["string", "null"],
  "description": "Canonical JSON for one validated theme_graph.curation_assertion.v1 payload. Null on every legacy/non-curation evidence row."
}
\`\`\`

Append \`"curation_assertion"\` to the END of \`EVIDENCE_COLUMNS\`. Do not alter \`EVIDENCE_KEY\`, \`evidence_path()\`, \`write_evidence()\` or the nightly lane gate.

- [ ] **Step 4: Make the contract guard decode and validate non-null payloads**

In the evidence-row audit, call \`decode_assertion(row.curation_assertion)\`. Convert \`CurationAssertionError\`, JSON parse errors and schema errors into a named breach such as:

\`\`\`python
breaches.append(
    f"evidence {evidence_id} curation_assertion invalid: {exc}"
)
\`\`\`

Do not treat null as a violation.

- [ ] **Step 5: Prove focused and legacy store tests**

\`\`\`bash
python3 -m pytest \
  tests/test_theme_graph_curation_assertion.py \
  tests/test_theme_graph_contracts.py \
  -q
\`\`\`

Expected: PASS with the existing legacy contract cases unchanged.

- [ ] **Step 6: Commit the owner-store extension**

\`\`\`bash
git add contracts/theme_graph/evidence.v1.schema.json \
        engine/theme_graph/store.py \
        scripts/check_theme_graph_contracts.py \
        tests/test_theme_graph_contracts.py
git commit -m "feat(theme-graph): round-trip curation assertions"
\`\`\`

---

### Task 3: Add an Explicit Evidence Foundation Binding for the Curation Subtype

**Files:**
- Modify: \`contracts/evidence_foundation/vocabulary.v1.json:30-39\`
- Modify: \`tests/test_evidence_foundation_contract.py\`
- Modify \`lib/evidence_foundation.py\` only if a discriminating test proves the generic validator lacks the required representation.

**Interfaces:**
- Consumes: the same physical \`engine.theme_graph.store.read_evidence\` owner reader.
- Produces: owner-store key \`theme_graph.curation_assertion\` with native identity \`{evidence_id, curation_revision}\`; no cross-type company/security join.

- [ ] **Step 1: Write the failing positive binding test**

Construct one \`EvidenceRef\` fixture with:
- \`owner_store="theme_graph.curation_assertion"\`;
- native identity \`{"evidence_id":"ev:0123456789abcdef","curation_revision":"gmirca_" + "1"*32}\`;
- subject \`theme_evidence_id=ev:0123456789abcdef\`;
- clocks for \`source.published_at\`, \`source.observed_at\`, \`source.retained_at\`, \`review.reviewed_at\`, \`review.review_due_at\`, \`temporal.business_valid_from\`, \`temporal.business_valid_to\`, and \`computed_at\`, with unknown values explicit where allowed;
- all-false authority.

Assert \`validate_reference()\` accepts it.

- [ ] **Step 2: Add hostile clock/identity tests**

Tests must reject:
- omitting any registered native clock;
- relabeling observed time as source publication;
- using a company/security subject instead of \`theme_evidence_id\`;
- caller-authored company join data;
- any authority bit true.

- [ ] **Step 3: Run the Evidence Foundation suite red**

\`\`\`bash
python3 -m pytest tests/test_evidence_foundation_contract.py -q
\`\`\`

Expected: unknown owner-store failure.

- [ ] **Step 4: Register the subtype without changing legacy bindings**

Add one owner entry:

\`\`\`json
"theme_graph.curation_assertion": {
  "native_identity_fields": ["evidence_id", "curation_revision"],
  "native_identity_types": {"evidence_id": "string", "curation_revision": "string"},
  "native_schemas": ["theme_graph.curation_assertion.v1"],
  "native_identity_grammars": {
    "evidence_id": {"kind": "regex", "pattern": "^ev:[a-f0-9]{16}$"},
    "curation_revision": {"kind": "regex", "pattern": "^gmirca_[a-f0-9]{32}$"}
  },
  "object_classes": ["world_observation"],
  "subject_key_types": ["theme_evidence_id"],
  "subject_native_parity": {
    "theme_evidence_id": {"kind": "native_field_equal", "field": "evidence_id"}
  },
  "coverage_classes": ["append_only_bitemporal"],
  "replay_capabilities": {
    "live": ["owner_native"],
    "historical_replay": ["owner_native"]
  },
  "clock_bindings": {
    "source.published_at": {"class": "source_published", "grains": ["date"]},
    "source.observed_at": {"class": "observed", "grains": ["datetime"]},
    "source.retained_at": {"class": "system_recorded", "grains": ["datetime"]},
    "review.reviewed_at": {"class": "system_recorded", "grains": ["datetime"]},
    "review.review_due_at": {"class": "review_due", "grains": ["date"]},
    "temporal.business_valid_from": {"class": "world_valid", "grains": ["date"]},
    "temporal.business_valid_to": {"class": "world_valid", "grains": ["date"]},
    "computed_at": {"class": "belief_or_build", "grains": ["datetime"]}
  },
  "synapse_asof_field": "computed_at",
  "reader": "engine.theme_graph.store.read_evidence",
  "reader_kind": "collection",
  "pointer_template": "data/theme_graph/evidence.parquet#evidence_id={evidence_id}&curation_revision={curation_revision}"
}
\`\`\`

If the vocabulary validator refuses \`unknown\` as a clock grain, represent unknown as the existing reference wire's explicit unknown value under a permitted date/datetime grain; do not add a new global clock class or silently substitute observation time.

- [ ] **Step 5: Prove subtype and legacy K1 behavior**

\`\`\`bash
python3 -m pytest tests/test_evidence_foundation_contract.py -q
\`\`\`

Expected: PASS, including pre-existing AAPL refusal behavior and all-false authority tests.

- [ ] **Step 6: Commit**

\`\`\`bash
git add contracts/evidence_foundation/vocabulary.v1.json \
        tests/test_evidence_foundation_contract.py
git commit -m "feat(evidence): bind theme curation assertions"
\`\`\`

If and only if a generic-library change was required by the red test, include \`lib/evidence_foundation.py\` in the same commit and retain all existing owner entries unchanged.

---

### Task 4: Build the Pure F04 Robotics Dossier Composer

**Files:**
- Create: \`contracts/market_ontology/robotics_theme_research.v1.schema.json\`
- Create: \`engine/market_ontology/robotics_theme_research.py\`
- Create: \`tests/test_market_ontology_robotics_theme_research.py\`

**Interfaces:**
- Consumes:
  - \`engine.theme_graph.store.read_evidence()\`;
  - \`engine.theme_graph.store.read_identity_resolution(latest=True)\`;
  - \`decode_assertion()\`.
- Produces:
  - \`compose_robotics_theme_research(asof: date, knowledge_cutoff: date, *, evidence_rows=None, identity_rows=None) -> dict[str, Any]\`;
  - schema \`market_ontology.robotics_theme_research/v1\`;
  - deterministic arrays ordered by stable textual identity, never by a score.

- [ ] **Step 1: Write the discriminating composer tests**

Build test evidence for:
- Orbbec/Twinny two-camera documented inclusion;
- Parker frameless-motor \`PRODUCT_CAPABILITY\` with unknown source publication date;
- Schaeffler/Hexagon separate \`ANNOUNCED_DEVELOPMENT_AGREEMENT\` and \`DEPLOYMENT_TARGET\`;
- Zebra/PTC ownership-event effective-date cases;
- Sanhua robotics revenue null/not-separately-disclosed;
- HDS orders/backlog/sales with stock-vs-flow fields.

Assert:
- catalog capability never becomes a named supply contract;
- future target never enters \`reported_deployments\`;
- quantity is tied to exact configuration;
- no newer configuration inherits an old quantity;
- unresolved identity gets \`security: null\` and no market enrichment;
- backlog/sales is not labeled lead time;
- official rounded total/residual survives;
- no total combines integrated assembly plus contained components;
- per-hand quantity cannot be multiplied to per-robot without multiplicity evidence;
- no \`score\`, \`rank\`, \`alpha\`, \`signal\`, \`conviction\`, \`target_price\`, \`position_size\` or trade action key appears anywhere.

- [ ] **Step 2: Run the composer suite red**

\`\`\`bash
python3 -m pytest tests/test_market_ontology_robotics_theme_research.py -q
\`\`\`

Expected: module/contract missing.

- [ ] **Step 3: Freeze the consumer contract**

Top-level fields:

\`\`\`json
{
  "schema": "market_ontology.robotics_theme_research/v1",
  "theme_id": "robotics_automation",
  "as_of": "YYYY-MM-DD",
  "knowledge_cutoff": "YYYY-MM-DD",
  "availability": "OK|NO_ACCEPTED_ASSERTIONS|STORE_UNAVAILABLE|RIGHTS_RESTRICTED|SOURCE_STALE",
  "facets": [],
  "companies": [],
  "relationships": [],
  "constraints": [],
  "evidence": [],
  "limitations": [],
  "authority": {
    "can_rank": false,
    "can_gate": false,
    "can_size": false,
    "can_originate": false,
    "can_open_entry": false
  }
}
\`\`\`

Each evidence item carries its evidence ID, curation revision, publisher, locator, source/business clocks, predicate, statement mode, limitations and source-dependence class. Do not embed source document bodies.

- [ ] **Step 4: Implement owner-reader composition**

Default readers are imported lazily. Filter to decoded assertions where \`scope.canonical_theme_id == "robotics_automation"\`, review disposition is accepted, curation/source clocks are eligible for the requested cutoffs, and current rights permit display.

Resolve company links only from current validated \`identity_resolution\` rows in state \`RESOLVED\`. Source-only objects remain useful but never acquire security data.

Relationship rendering is a view of assertion predicates, not a new Theme Graph edge write.

- [ ] **Step 5: Add arithmetic safety helpers**

Expose internal helpers with direct tests:

\`\`\`python
def safe_quantity(value: object, basis: object) -> tuple[float, str] | None: ...
def compatible_financial_basis(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool: ...
def non_overlapping_cost_items(items: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]: ...
\`\`\`

\`non_overlapping_cost_items\` must raise/refuse when both an assembly and a declared contained child are selected for the same cost boundary.

- [ ] **Step 6: Prove deterministic/hostile behavior**

\`\`\`bash
python3 -m pytest tests/test_market_ontology_robotics_theme_research.py -q
\`\`\`

Expected: PASS including reversed-input-order byte-equivalent JSON.

- [ ] **Step 7: Commit**

\`\`\`bash
git add contracts/market_ontology/robotics_theme_research.v1.schema.json \
        engine/market_ontology/robotics_theme_research.py \
        tests/test_market_ontology_robotics_theme_research.py
git commit -m "feat(themes): compose robotics evidence dossier"
\`\`\`

---

### Task 5: Serve the Dossier Through the Existing Paid Macro API Boundary

**Files:**
- Create: \`app/robotics_research.py\`
- Modify: \`app/main.py:2243-2317\` near the other unconditional paid routers
- Create: \`tests/test_robotics_research_api.py\`

**Interfaces:**
- Consumes: \`compose_robotics_theme_research()\`.
- Produces: \`GET /api/themes/v1/robotics\`.
- Auth: \`require_user\` + \`app.paywall.enforce_site_full(..., always=True)\`.
- Response headers: exact private header set from Global Constraints.

- [ ] **Step 1: Write API tests before the route exists**

Tests must cover:
- entitlement denial before composer/store invocation;
- entitled 200 \`OK\` payload;
- entitled typed unavailable payload without converting missing data to \`[]\`;
- invalid \`as_of\` / \`knowledge_cutoff\` returns 400 with private headers;
- composer/storage exception returns generic 503 without source/internal details;
- every 200/400/401/403/404/503 response carries the private headers;
- production \`app.main.app.openapi()\` includes \`/api/themes/v1/robotics\`;
- router import is unconditional, not swallowed by \`try/except ImportError\`.

- [ ] **Step 2: Run the API suite red**

\`\`\`bash
python3 -m pytest tests/test_robotics_research_api.py -q
\`\`\`

Expected: import/route missing.

- [ ] **Step 3: Implement the router using the established paid pattern**

Core shape:

\`\`\`python
router = APIRouter()
_PRIVATE_HEADERS = {
    "Cache-Control": "private, no-store",
    "Vary": "Authorization",
    "X-Content-Type-Options": "nosniff",
    "X-Robots-Tag": "noindex, noarchive",
}

def require_site_full_user(authorization: str | None = Header(default=None)) -> dict:
    from app.main import require_user
    from app.paywall import enforce_site_full
    try:
        return enforce_site_full(require_user(authorization), always=True)
    except HTTPException as exc:
        raise _private_error(exc.status_code, exc.detail, exc.headers) from None

@router.get("/api/themes/v1/robotics")
def robotics_theme_research(
    response: Response,
    as_of: str | None = None,
    knowledge_cutoff: str | None = None,
    _user: dict = Depends(require_site_full_user),
) -> JSONResponse:
    del _user
    # parse caller dates; default only to the composer's accepted current date source,
    # never datetime.now() inside the pure composer.
    payload = compose_robotics_theme_research(...)
    return JSONResponse(content=payload, headers=_PRIVATE_HEADERS)
\`\`\`

Do not cache full payloads in browser-visible/static artifacts. A short server process cache is allowed only if it keys on the exact owner generation/cutoffs and never bypasses rights/corrections; omit it in v1 unless measured API cost requires it.

- [ ] **Step 4: Mount the router fail-loudly**

In \`app/main.py\`:

\`\`\`python
from app.robotics_research import router as robotics_research_router  # noqa: E402
app.include_router(robotics_research_router)
\`\`\`

Keep it outside an optional-import try/except.

- [ ] **Step 5: Prove API/auth behavior**

\`\`\`bash
python3 -m pytest \
  tests/test_robotics_research_api.py \
  tests/test_earnings_api.py \
  tests/test_site_access_boundary.py \
  -q
\`\`\`

Expected: PASS; existing Earnings/private boundary remains unchanged.

- [ ] **Step 6: Commit**

\`\`\`bash
git add app/robotics_research.py app/main.py tests/test_robotics_research_api.py
git commit -m "feat(api): serve private robotics research"
\`\`\`

---

### Task 6: Hydrate Theme Tracker and Robotics Detail Without Moving Existing Analytical Owners

**Files:**
- Create: \`site/assets/js/robotics-theme-research.js\`
- Create: \`site/assets/css/robotics-theme-research.css\`
- Modify: \`templates/state_of_themes.html.j2:460-590,651\`
- Modify: \`templates/basket_detail.html.j2:1177-1435,1760\`
- Create: \`tests/test_robotics_theme_research_ui.py\`

**Interfaces:**
- Consumes: \`GET /api/themes/v1/robotics\` through \`theme.js\`'s existing \`window.MDXAuth\`.
- Produces:
  - Theme Tracker Robotics shell selector: \`[data-robotics-research-summary]\`;
  - Detail mount selector: \`[data-robotics-research-detail]\`;
  - no new page route and no new static research JSON.

**Collision gate:** reconcile #7669/current accepted template before editing \`basket_detail.html.j2\`.

- [ ] **Step 1: Write static-source/UI contract tests**

Assert:
- Theme Tracker renders a research shell only under \`theme_id == "robotics_automation"\`;
- detail template exposes one hidden mount but the JS activates only when \`DETAIL.basket.id === "robotics_automation"\`;
- both templates load \`robotics-theme-research.css\` and \`robotics-theme-research.js\` with the correct relative path;
- JavaScript uses \`window.MDXAuth.client().then(sb => sb.auth.getSession())\`;
- request carries \`Authorization: Bearer <token>\`, \`credentials:"same-origin"\`, \`cache:"no-store"\`;
- no API payload, source URL list or assertion body is baked into either template;
- on auth failure the shell remains useful/locked and does not expose an error detail;
- EN/ZH values come from payload pairs or typed strings, not machine translation in browser;
- diagram edges have text relationship labels and synchronized table rows;
- CSS has keyboard focus styles and never relies on color alone.

- [ ] **Step 2: Run the UI tests red**

\`\`\`bash
python3 -m pytest tests/test_robotics_theme_research_ui.py -q
\`\`\`

Expected: missing assets/mounts.

- [ ] **Step 3: Add the public shells**

Theme Tracker: inside the Robotics drawer, add only:

\`\`\`html
<section class="rtr-shell" data-robotics-research-summary hidden>
  <div class="rtr-status" aria-live="polite"></div>
  <div class="rtr-summary"></div>
  <a class="rtr-open" href="basket/robotics_automation.html">
    <span class="en">Open Robotics research →</span>
    <span class="zh">打开机器人研究 →</span>
  </a>
</section>
\`\`\`

Robotics detail: add one generic hidden mount outside the incumbent \`#app\` re-render region so existing \`render()\` calls cannot erase it:

\`\`\`html
<section class="rtr-shell rtr-detail" data-robotics-research-detail hidden aria-live="polite"></section>
\`\`\`

Do not renumber or rewrite existing Timing, Score, Earnings, Holdings or Membership sections.

- [ ] **Step 4: Implement one shared authenticated client**

The client must:
1. wait for \`mdx-auth\` or settled \`MDXAuth\`;
2. return early unless the page is Theme Tracker Robotics or \`DETAIL.basket.id === "robotics_automation"\`;
3. obtain the current Supabase access token through \`MDXAuth.client()/auth.getSession()\`;
4. fetch only \`/api/themes/v1/robotics\`;
5. validate \`schema === "market_ontology.robotics_theme_research/v1"\`;
6. render facets, company/product evidence, labeled relationship rows, constraint observations, source/clock/limitation details;
7. keep \`FORWARD_TARGET\`, \`CATALOG_DESCRIPTION\`, \`REPORTED_FACT\` visibly distinct;
8. show typed unavailable/restricted states instead of empty tables;
9. never calculate ranking, cost share, bottleneck score, or financial ratios in browser.

- [ ] **Step 5: Implement the unweighted map plus complete table**

Use CSS grid/flex and DOM elements, not a force-directed library. Each line/row has:
- subject label;
- exact predicate display;
- object label;
- application/facet;
- quantity + basis when present;
- source publication/observed date distinction;
- review/current-applicability state;
- evidence expander.

No width/position encodes financial magnitude. The table contains every relationship shown on the visual map and remains visible when reduced-motion or JS drawing support is limited.

- [ ] **Step 6: Prove UI source tests and existing page contracts**

\`\`\`bash
python3 -m pytest \
  tests/test_robotics_theme_research_ui.py \
  tests/test_state_of_themes.py \
  tests/test_product_chrome.py \
  -q
\`\`\`

Expected: PASS with no legacy semantics changed.

- [ ] **Step 7: Commit**

\`\`\`bash
git add site/assets/js/robotics-theme-research.js \
        site/assets/css/robotics-theme-research.css \
        templates/state_of_themes.html.j2 \
        templates/basket_detail.html.j2 \
        tests/test_robotics_theme_research_ui.py
git commit -m "feat(themes): add robotics evidence explorer"
\`\`\`

---

### Task 7: Freeze Legacy Decision Non-Regression and the Private Publication Gate

**Files:**
- Create: \`tests/test_robotics_theme_non_regression.py\`
- Modify only the existing publication/deploy owner files if the private-binding proof identifies an already-approved extension point; do not pre-authorize a new store or workflow here.

**Interfaces:**
- Consumes: the complete first vertical.
- Produces: explicit proof that the research vertical does not alter decision outputs and that live detail cannot leak through static/public mirrors.

- [ ] **Step 1: Freeze legacy outputs before any live admission**

Use committed current inputs and compare before/after values for \`robotics_automation\`:
- basket members and weights;
- theme recommendation/lane/stage;
- entry/clean-entry fields;
- any member ordering/Prophet presence emitted by existing builders.

Test should compare exact JSON/value subsets, not screenshots.

- [ ] **Step 2: Add public-leakage tests**

Fail if any of these contain a live \`theme_graph.curation_assertion.v1\` body or private dossier:
- \`site/state_of_themes.html\`;
- \`site/basket/robotics_automation.html\`;
- \`site/**/*.json\`;
- source maps;
- tracked \`data/theme_graph/evidence.parquet\` in the implementation diff.

The last check is a release rule for live rows, not a ban on the additive column schema.

- [ ] **Step 3: Run the non-regression/privacy tests red/green**

\`\`\`bash
python3 -m pytest \
  tests/test_robotics_theme_non_regression.py \
  tests/test_robotics_theme_research_api.py \
  tests/test_robotics_theme_research_ui.py \
  -q
\`\`\`

Expected after implementation: PASS.

- [ ] **Step 4: Run the focused first-unit suite**

\`\`\`bash
python3 -m pytest \
  tests/test_theme_graph_curation_assertion.py \
  tests/test_theme_graph_contracts.py \
  tests/test_evidence_foundation_contract.py \
  tests/test_market_ontology_robotics_theme_research.py \
  tests/test_robotics_research_api.py \
  tests/test_robotics_theme_research_ui.py \
  tests/test_robotics_theme_non_regression.py \
  tests/test_state_of_themes.py \
  tests/test_earnings_api.py \
  tests/test_site_access_boundary.py \
  tests/test_product_chrome.py \
  -q
\`\`\`

Expected: zero failures.

- [ ] **Step 5: Run repository contract and diff guards**

Use the repository's current main-owned contract-delta command and \`git diff --check\`. If current main has renamed the CI/contract command, read the current owning job and run that exact successor instead of preserving a stale command by name.

\`\`\`bash
git diff --check
python3 scripts/check_theme_graph_contracts.py
\`\`\`

Expected: exit 0.

- [ ] **Step 6: Prove or stop at the private publication gate**

Before any real assertion is admitted, prove all of:
- the accepted source/curation body resides in an incumbent approved private retention path;
- the paid API can read the owner-qualified assertion without committing it to Git/Pages/public R2;
- denial occurs before private bytes are opened;
- a raw Git/Pages/public-R2 request cannot recover the payload.

If the current system cannot satisfy these statements without creating a second evidence/latest-state plane, classify this lane blocked and return to the architecture owner. Do **not** make a public-row exception and do not create \`data/robotics_research/\`, another bucket, another DB, or another scheduler.

- [ ] **Step 7: Commit the non-regression/privacy guard**

\`\`\`bash
git add tests/test_robotics_theme_non_regression.py
git commit -m "test(themes): fence robotics research authority and privacy"
\`\`\`

---

### Task 8: Qualify One Real Producer-to-Consumer Robotics Slice

**Files:**
- No new authority plane.
- Production assertion/review artifacts go only through the accepted existing owner/private path established in Task 7.
- Evidence screenshots/receipts use the repository's existing product/browser evidence convention chosen from current main at execution time.

**Interfaces:**
- Consumes: one accepted documented inclusion plus one accepted catalog capability.
- Produces: real entitled Theme Tracker + Robotics-detail visible result with exact source/clock/limitations and no legacy decision delta.

- [ ] **Step 1: Admit two bounded real cases through the accepted native path**

Use:
- Orbbec/Twinny as \`DOCUMENTED_PRODUCT_INCLUSION\`, quantity 2 cameras \`per_robot\`, tied only to the described NarGo configuration.
- Parker K-Series as \`PRODUCT_CAPABILITY\`, robotics application category, source publication unknown and observation date explicit.

Do not infer named Parker customer, Orbbec price, Orbbec revenue, exclusivity or applicability to another robot generation.

- [ ] **Step 2: Rebuild/serve through the actual owner → composer → API path**

No fixture substitution. Capture exact assertion revisions/evidence IDs and the owner generation used by the API.

- [ ] **Step 3: Browser-prove the existing-page journey**

Verify at desktop and mobile:
1. Theme Tracker Robotics entry shows the two facets and dated evidence state after entitlement.
2. Opening existing \`basket/robotics_automation.html\` shows the research module without disturbing incumbent timing/holdings.
3. Orbbec appears as documented inclusion with \`2 / per robot / described configuration\`.
4. Parker appears as catalog capability, not documented inclusion.
5. Source date unavailable versus observed date is visible for Parker.
6. Evidence details expose source/locator/limitations without leaking a private body into page source.
7. EN/ZH and dark/light show identical quantities/statuses/sources.
8. Keyboard-only navigation reaches every evidence expander/relationship row.

- [ ] **Step 4: Prove negative mirrors and unauthorized access**

Check anonymous/free:
- API is denied with private headers;
- page source contains shell only;
- public Git/Pages/R2/static JSON cannot retrieve the private payload;
- browser console/network shows no alternate unauthenticated payload endpoint.

- [ ] **Step 5: Re-run exact-head tests and independent review**

Run Task 7's focused suite on the final exact head, then obtain one independent exact-head semantic/code review. Repair on the same implementation carrier; after any repair, rerun the discriminating suites and refresh exact-head review.

- [ ] **Step 6: Publish through the incumbent release path and prove deployed bytes**

Only after required CI/review/release gates pass. Deployed acceptance repeats Steps 3–4 against the real site and records the release identity. Green CI/merge alone is not acceptance.

- [ ] **Step 7: Close the first vertical truthfully**

The first vertical is \`PROVEN_OUTCOME\` only when the real accepted source reaches both existing pages through the entitled production path, private mirrors remain closed, and frozen legacy decision outputs are unchanged. Otherwise retain the exact nonterminal capability state and next gate.

---

## Execution Order and Parallelism

1. Task 1 is path-disjoint and may start immediately after plan approval.
2. Task 2 waits for #7462 store-path reconciliation.
3. Task 3 can proceed after Task 1 and is path-disjoint from #7462.
4. Task 4 depends on Tasks 1–3.
5. Task 5 depends on Task 4 but not on template custody.
6. Task 6 waits for #7669 template reconciliation and depends on Task 5's API contract.
7. Task 7 runs before any live assertion admission.
8. Task 8 is the real-path acceptance slice and cannot use fixture substitution.

Do not add a new worker merely because tasks are listed separately. Tasks 1/3/4 are tightly coupled around the assertion interface; if using subagents, each fresh implementer receives the spec plus this plan, and each task gets a fresh reviewer before its dependent task starts.


## Spec/Acceptance Coverage Matrix

| Acceptance case | Owning task(s) |
|---|---|
| RBV-01 catalog capability ≠ supply contract | Task 4 |
| RBV-02 documented two-camera quantity/basis | Tasks 1, 4, 8 |
| RBV-03 no generation inheritance | Task 4 |
| RBV-04 future target ≠ delivered | Tasks 1, 4, 6 |
| RBV-05 reciprocal roles remain separate | Tasks 4, 6 |
| RBV-06 adjacent auto customer ≠ robotics customer | Task 4 |
| RBV-07 corporate plants ≠ robot capacity | Task 4 |
| RBV-08 undisclosed robotics revenue stays null | Task 4 |
| RBV-09 incompatible financial bases refuse | Task 4 |
| RBV-10 announcement ≠ completed ownership | Tasks 1, 4 |
| RBV-11 unresolved listing gets no market join | Task 4 |
| RBV-12 similar product labels do not auto-merge | Task 1 |
| RBV-13 unsupported K1 cross-type joins refuse | Task 3 |
| RBV-14 QLedger is not factual product evidence | Tasks 3, 4 |
| RBV-15 source publication ≠ observation/business clocks | Tasks 1, 3, 6 |
| RBV-16 same URL/day separate statements stay distinct | Task 1 |
| RBV-17 corrected same URL/day appends revision | Tasks 1, 2 |
| RBV-18 withdrawal/review expiry preserves history | Tasks 1, 4 |
| RBV-19 later-retained evidence cannot backdate knowledge | Tasks 3, 4 |
| RBV-20 date-only edge key is not intraday replay proof | Tasks 2, 3 |
| RBV-21 parent/contained cost double count refuses | Task 4 |
| RBV-22 per-hand ≠ per-robot without multiplicity | Task 4 |
| RBV-23 backlog/sales ≠ lead time | Tasks 4, 6 |
| RBV-24 published totals/residuals preserved | Task 4 |
| RBV-25 non-finite/negative/basis-free quantity refuses | Task 1 |
| RBV-26 syndicated copies are not independent confirmation | Tasks 1, 4 |
| RBV-27 partial rights stays restricted/partial | Tasks 4, 5, 6 |
| RBV-28 no public full-fidelity mirror | Tasks 7, 8 |
| RBV-29 private headers on denial/error | Tasks 5, 8 |
| RBV-30 desktop/mobile EN/ZH dark/light semantic parity | Tasks 6, 8 |
| RBV-31 legacy decision outputs unchanged | Tasks 7, 8 |
| RBV-32 UI build time cannot hide source-generation lag | Tasks 4, 6, 8 |

## Completion Law

The program is not complete when the contract exists, the API returns a fixture, the pages show a shell, CI is green or the PR merges. The first robotics vertical completes only when an accepted real primary-source assertion traverses the existing owner, F04 composer, paid private API and existing Theme Tracker/detail pages; the visible semantics preserve predicate, configuration, quantity basis, clocks and limitations; public mirrors cannot retrieve full-fidelity payload; and existing theme/member decision outputs remain byte/value-equivalent for the frozen comparison set.
