# STSI-1 Sector Federation and Technology Dossier Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ship one production-capable Technology-sector intelligence dossier that composes existing Sector Central, subsector, theme, heatmap, and Neural Web facts into a source-bound, freshness-aware, contradiction-explaining journey without creating a new score, graph, publisher, or trading authority.

**Plan compatibility census:** Macro `main@e0dc4946cd53234e1a3479d872adabd81680f744`; movement after the architecture base on `scripts/build_site.py` and `.github/ci/legacy-jobs.yml` is confined to unified-dashboard market-state bindings and its existing test registration, disjoint from the sector-page builder and named STSI-1 CI owners. Hard dependency heads remain #7211 `9b01c9bcae2b12f23ab0a2ab3a5054f81dcade02` and #7526 `cdad0d3ec3f09f53425906ed2b532fed4507ed12`, both open/unmerged at plan freeze.

**Architecture:** A pure `engine.neuralweb.sector_federation` composer receives already-produced owner artifacts and emits one atomic `sector_dossier_read_model.v1` document. The document nests a valid `sector_intelligence_packet.v1`, `lobe_run.v1`, and `authority_manifest.v1`, so the existing governance seam is operational rather than referenced by invented IDs. The existing focused Sector Intelligence publisher writes the dossier after Sector Central, the incumbent sector page hydrates it through a small governed JavaScript consumer, and Sector Central links directly to the dossier.

**Tech Stack:** Python 3.12+, JSON Schema 2020-12, existing `engine.sector_intelligence.contracts`, Jinja2, vanilla JavaScript, pytest, Node syntax checks, Playwright/Chromium for controlled browser proof, existing GitHub Actions/sector-intelligence publication workflow.

---

## 0. Source, authority, and execution gates

### Governing source

- Architecture: `docs/superpowers/specs/2026-09-20-sector-theme-subtheme-intelligence-system-design.md`
- Architecture carrier: Macro PR `#7577`
- Architecture commit: `2007020130da0703e3e7c1ece0614484015f28d5`
- Protected Sol Skillpack: `mastermindx-market-intelligence/Mastermind@3e66e43258f34db240d5bff76f54148c7af84ee4`
- Reference vertical: `sector:xlk` / native Sector Central id `xlk` / security `XLK`

### Hard implementation prerequisites

Do not start source implementation until all of the following are true:

1. Chairman has approved PR `#7577`'s architecture and this STSI-1 plan.
2. PR `#7211` or its accepted successor has merged, because it owns the focused publisher, strict build order, and generation-freshness validator that STSI-1 must extend rather than duplicate.
3. PR `#7526` or its accepted successor has merged, because STSI-1 consumes the corrected Theme Intelligence semantics and must not copy its held implementation.
4. A fresh collision census confirms no active writer owns the exact STSI-1 paths listed below.
5. Implementation begins from fresh `origin/main` in a new worktree and new branch; do not continue coding on PR `#7577`'s architecture branch.

### Additive dependencies

These carriers are optional inputs in STSI-1 and must fail closed when not yet accepted:

- `#7455` — closed-session subtheme leadership observations.
- `#7508` — fail-closed group/member entry context.
- `#7252` — source-bound group/member observation contract.
- `#7283` — House Theme Atlas; STSI-1 links to it later but does not consume its UI code.

Absence of an optional accepted artifact is represented as `UNAVAILABLE` with a source-specific warning. It is never zero-filled and never blocks the already-valid sector/child/theme dimensions.

### Frozen authority

Every STSI-1 output remains facts/explanation only:

```json
{
  "max_authority": "A1_EXPLAIN",
  "allowed_actions": ["observe", "explain"],
  "forbidden_actions": [
    "originate_signal",
    "raise_authority_from_llm",
    "rank_security",
    "select_security",
    "size_position",
    "gate_decision",
    "execute_trade"
  ],
  "llm_may_originate_signals": false,
  "may_modify_prophet": false
}
```

No implementation task may change Sector Central conviction, fast-rotation ordering, Subsector Confluence tiers, ThemeState lanes, Board V2 membership/order, Prophet selection, position sizing, or portfolio authority.

---

## 1. Reference vertical and expected real-state behavior

Technology is the only admitted STSI-1 sector. The admission is deliberate because the current committed artifacts exercise every required conflict class without synthetic market claims:

- Sector Central: `XLK` is `Cautious` on the slow clock while its fast tape is `TOP WATCH`; `split_view=true`.
- Sector participation: Technology breadth is approximately 41%, so cap-weighted strength is not broad participation.
- Semiconductors: fresh `T1` / `entry_now`, high reliability, but regime `EXTENDED` / avoid chasing.
- ThemeState: AI Semiconductors, Memory & Storage, and Semiconductor Equipment remain distinct canonical themes with different basket health and a common semiconductor relationship.
- Subsector members show substantial dispersion; a group-level fresh trigger does not make every member eligible.

The first real dossier must therefore explain, in plain words:

> Technology has a constructive fast tape but a cautious slow clock. Semiconductor timing has refreshed, yet the group is already extended and sector participation remains narrow. Treat this as selective leadership, not broad sector confirmation.

That sentence is a deterministic composition of owner states. It is not an LLM-generated conclusion and it does not become a score.

---

## 2. Final file and interface map

### New source files

- `contracts/sector_intelligence/sector_dossier_read_model.v1.schema.json`
- `data/sector_intelligence/fixtures/sector_dossier_read_model.v1.valid.json`
- `tests/fixtures/sector_federation/technology_split_view.v1.json`
- `engine/neuralweb/sector_federation.py`
- `scripts/build_sector_dossiers.py`
- `templates/sector_dossier.js`
- `site/sector_dossier.js`
- `tests/test_sector_dossier_contract.py`
- `tests/test_sector_federation.py`
- `tests/test_build_sector_dossiers.py`
- `tests/test_sector_dossier_page.py`
- `tests/test_sector_dossier_browser.py`

### Existing source files modified

- `engine/sector_intelligence/contracts.py`
- `scripts/build_sector_intelligence.py`
- `scripts/check_sector_intelligence_freshness.py`
- `scripts/build_site.py`
- `templates/sector.html.j2`
- `templates/sector_central.html.j2`
- `config/synapse.yml`
- `.github/workflows/sector-intelligence.yml`
- `.github/ci/legacy-jobs.yml`
- `tests/test_sector_intelligence_page.py`
- `tests/test_nightly_liveness.py`
- `tests/test_sector_central_gate.py`

### Generated outputs

- `site/sectordata/sector_dossiers/xlk.json`
- `site/sectors/XLK.html`
- `site/sector_central.html`

Generated files are produced through existing builders. Never hand-edit them.

### Stable public route and fetch contract

```text
Page:     /sectors/XLK.html
Payload:  /sectordata/sector_dossiers/xlk.json
Hub link: /sector_central.html -> /sectors/XLK.html
```

The page remains useful when the payload is unavailable: the existing ETF cycle/timing content stays server-rendered, while the federation section shows an honest typed-unavailable fallback.

---

## 3. Contract design

The new top-level contract is `sector_dossier_read_model.v1`. It is one atomic JSON document so packet, governance, explanation, and page view cannot publish as split generations.

### Required top-level shape

```json
{
  "contract_id": "sector_dossier_read_model.v1",
  "schema_version": "1.0.0",
  "dossier_id": "dossier:sector:xlk:0123456789abcdef01234567",
  "dossier_version": 1,
  "generated_at": "2026-09-18T20:00:00Z",
  "knowledge_cutoff": "2026-09-18T20:00:00Z",
  "common_as_of": "2026-09-18",
  "identity": {},
  "headline": {},
  "dimensions": [],
  "material_changes": [],
  "children": [],
  "connected_themes": [],
  "participation": {},
  "concentration": {},
  "conflicts": [],
  "watch_conditions": [],
  "freshness": {},
  "quality": {},
  "input_receipts": [],
  "governance": {
    "packet": {},
    "lobe_run": {},
    "authority_manifest": {}
  },
  "authority_caps": {},
  "hash_scope": "canonical_payload_excluding_dossier_hash",
  "dossier_hash": "0000000000000000000000000000000000000000000000000000000000000000"
}
```

### Identity object

```json
{
  "entity_id": "sector:xlk",
  "native_id": "xlk",
  "ticker": "XLK",
  "name_en": "Technology",
  "name_zh": "科技",
  "representation": "spdr_sector_etf",
  "benchmark_ticker": "SPY",
  "page_href": "sectors/XLK.html",
  "source_refs": [
    "config/rotation_universe.json#/instruments/xlk",
    "site/sectordata/sector_central.json#/sectors/xlk"
  ]
}
```

Do not mint another sector identity. `sector:xlk` already exists in Neural Web; `xlk` remains the native Sector Central id; `XLK` remains the security ticker.

### Headline object

```json
{
  "state": "selective_leadership",
  "summary_en": "Technology has a constructive fast tape but a cautious slow clock. Semiconductor timing has refreshed, yet the group is already extended and sector participation remains narrow.",
  "summary_zh": "科技板块快线偏强，但慢周期仍保持谨慎。半导体择时已重新转强，但该组已偏延伸，板块参与度仍然有限。",
  "posture_en": "Selective leadership — participate carefully; do not treat it as broad sector confirmation.",
  "posture_zh": "选择性领涨——谨慎参与，勿视为板块全面确认。",
  "reason_codes": [
    "FAST_TAPE_CONSTRUCTIVE",
    "SLOW_CLOCK_CAUTIOUS",
    "SEMICONDUCTOR_ENTRY_REFRESHED",
    "SEMICONDUCTOR_EXTENDED",
    "SECTOR_BREADTH_NARROW"
  ]
}
```

`state` is a closed display vocabulary: `broad_confirmation`, `selective_leadership`, `early_improvement`, `late_or_crowded`, `deteriorating`, `mixed_or_incomplete`, `unavailable`. It is deterministic presentation synthesis only and carries no admission, ranking, sizing, or trading semantics.

### Dimension object

Every owner read uses this exact grammar:

```json
{
  "dimension_id": "sector_slow_clock",
  "owner": "engine.sector_central",
  "scope": "sector",
  "horizon": "multi_year_cycle",
  "state": "cautious",
  "label_en": "Slow clock",
  "label_zh": "慢时钟",
  "summary_en": "Cautious — the long cycle is rolling over.",
  "summary_zh": "谨慎——长期周期正在回落。",
  "value": {
    "conviction_score": 40,
    "cycle_phase": "Downturn"
  },
  "as_of": "2026-09-18",
  "coverage_state": "complete",
  "source_ref": "site/sectordata/sector_central.json#/sectors/xlk",
  "authority": {
    "is_context_only": true,
    "may_rank": false,
    "may_gate": false,
    "may_size": false,
    "may_escalate": false,
    "may_trade": false,
    "may_modify_prophet": false
  }
}
```

The schema permits JSON scalar/object values but never executable expressions or HTML.

### Child object

```json
{
  "child_id": "subsector:semiconductors",
  "native_key": "semiconductors",
  "name_en": "Semiconductors",
  "name_zh": "半导体",
  "href": "../subsector/semiconductors.html",
  "relationship_basis": "structural_child",
  "class": "entry_now",
  "entry_tier": "T1",
  "regime_state": "EXTENDED",
  "reliability": "high",
  "n_priced": 14,
  "n_members": 14,
  "as_of": "2026-09-18",
  "source_ref": "site/marketdata/subsector_confluence.json#/subsectors/semiconductors"
}
```

`relationship_basis` must be an accepted explicit relation. No fuzzy name matching is permitted.

### Connected-theme object

```json
{
  "theme_id": "ai_semiconductors",
  "name_en": "AI Semiconductors",
  "name_zh": "AI半导体",
  "href": "../basket/ai_semiconductors.html",
  "relationship_basis": "theme_crosswalk.subsector_keys",
  "matched_child_key": "Semiconductors",
  "primary_basket_id": "ai_semiconductors",
  "stage": "WATCH",
  "entry_ready": false,
  "as_of": "2026-09-18",
  "source_refs": [
    "config/theme_crosswalk.yml#/themes/ai_semiconductors",
    "site/neuralwebdata/theme_state.json#/themes/ai_semiconductors"
  ]
}
```

Only exact `theme_crosswalk.yml` relationships are admissible. Overlap or token similarity alone must return no relation.

### Participation and concentration

Participation uses the existing Sector Central heat record:

```json
{
  "method": "advancing_member_share",
  "state": "measured",
  "value_pct": 41.0,
  "n_advancing": 20,
  "n_declining": 29,
  "n_total": 49,
  "as_of": "2026-09-18",
  "source_ref": "site/sectordata/sector_central.json#/sectors/xlk/heat",
  "display_only": true
}
```

`value_pct` must equal `100 * n_advancing / (n_advancing + n_declining)` within rounding tolerance; zero is a valid measured value. Missing counts produce `state="unavailable"` and null values rather than fabricated breadth.

Concentration is a deterministic display-only derivative from the accepted S&P heatmap owner:

```python
def top_n_market_cap_share(member_sizes: list[float], n: int = 5) -> float | None:
    valid = sorted((float(x) for x in member_sizes if x is not None and x > 0), reverse=True)
    total = sum(valid)
    if len(valid) < n or total <= 0:
        return None
    return round(sum(valid[:n]) / total, 6)
```

The output must identify the method as `market_cap_top5_share`; it is structural concentration, not return contribution or predictive concentration.

```json
{
  "method": "market_cap_top5_share",
  "state": "measured",
  "value": 0.9,
  "n_members": 9,
  "source_ref": "site/marketdata/sp500_heatmap.json#/sectors/Technology",
  "display_only": true
}
```

When fewer than five valid market-cap sizes are available, `state="unavailable"` and `value=null`.

### Conflict object and classifier

```json
{
  "conflict_id": "conflict:xlk:slow-vs-fast",
  "class": "TIMEFRAME_SPLIT",
  "status": "open",
  "left_ref": "dimension:sector_slow_clock",
  "right_ref": "dimension:sector_fast_tape",
  "summary_en": "The fast tape is constructive while the slow clock remains cautious.",
  "summary_zh": "快线偏强，但慢周期仍保持谨慎。",
  "why_en": "The reads cover different horizons; neither invalidates the other.",
  "why_zh": "两项读数覆盖不同周期，彼此并不相互否定。",
  "source_refs": [
    "site/sectordata/sector_central.json#/sectors/xlk/conviction",
    "site/sectordata/sector_central.json#/sectors/xlk/rotation"
  ]
}
```

Allowed classes are closed:

```python
CONFLICT_CLASSES = {
    "ALIGNED",
    "TIMEFRAME_SPLIT",
    "SCOPE_SPLIT",
    "FRESHNESS_SPLIT",
    "COVERAGE_SPLIT",
    "AUTHORITY_SPLIT",
    "GENUINE_CONTRADICTION",
    "UNAVAILABLE",
}
```

The classifier rules are deliberately narrow:

1. `TIMEFRAME_SPLIT`
   - Sector Central explicitly sets `split_view=true`; or
   - a child has a fresh buyable tier while its regime is `EXTENDED`, `TOPPING`, or `SELL`.
2. `SCOPE_SPLIT`
   - parent breadth is below 50% while a high/medium-reliability child is `entry_now` or `tailwind`.
3. `FRESHNESS_SPLIT`
   - two compared required owner observations carry different as-of dates.
4. `COVERAGE_SPLIT`
   - one side is `low`, `partial`, `thin`, or missing while the comparison side is measured.
5. `AUTHORITY_SPLIT`
   - one owner is descriptive/context while the other has a separately governed decision role; this explains authority only and never upgrades either side.
6. `GENUINE_CONTRADICTION`
   - same entity, same scope, same horizon, fresh inputs, opposite owner states. Never infer this from different timeframes or scopes.
7. `UNAVAILABLE`
   - the comparison cannot be made because a required owner dimension is absent.
8. `ALIGNED`
   - same scope/horizon and compatible states. Alignment is explanatory, not confirmation of alpha.

### Material-change law

`material_changes` may include only explicit owner-observed transitions, such as:

- Sector Central `turn_since` / accepted fast-rotation state transition.
- Subsector Confluence `entry.fresh_bars` within the owner-defined fresh window.
- Accepted closed-session leadership state transitions from PR `#7455`.
- Accepted Theme Intelligence correction/history transitions from PR `#7526`.

The composer must not compare today's document with an unversioned previous file and call arbitrary field drift a material market change.

Each material change has this closed shape:

```json
{
  "change_id": "change:xlk:semiconductors-entry-refresh",
  "change_type": "ENTRY_REFRESH",
  "entity_ref": "subsector:semiconductors",
  "observed_at": "2026-09-18T20:00:00Z",
  "summary_en": "Semiconductor entry timing refreshed to T1.",
  "summary_zh": "半导体入场择时刷新至 T1。",
  "source_ref": "site/marketdata/subsector_confluence.json#/subsectors/semiconductors/entry",
  "authority": "context_only"
}
```

Allowed `change_type` values are `CYCLE_TURN`, `ROTATION_STATE_CHANGE`, `ENTRY_REFRESH`, `LEADERSHIP_CHANGE`, `THEME_STATE_CHANGE`, and `EVIDENCE_CORRECTION`.

### Watch-condition object

```json
{
  "condition_id": "watch:xlk:breadth-confirmation",
  "state": "open",
  "label_en": "Breadth confirmation",
  "label_zh": "广度确认",
  "condition_en": "Watch whether Technology participation rises above the current narrow reading while semiconductor leadership persists.",
  "condition_zh": "观察科技板块参与度是否在半导体领涨持续的同时走出当前窄幅状态。",
  "source_refs": [
    "site/sectordata/sector_central.json#/sectors/xlk/heat",
    "site/marketdata/subsector_confluence.json#/subsectors/semiconductors"
  ],
  "authority": "observation_only"
}
```

Watch conditions are deterministic descriptions of owner fields. They are not alerts, triggers, gates, predictions, or promises of future notification.

### Freshness object

```json
{
  "state": "fresh",
  "common_as_of": "2026-09-18",
  "oldest_required_source_at": "2026-09-18T20:00:00Z",
  "evaluated_at": "2026-09-18T20:00:00Z",
  "stale_source_ids": [],
  "degraded_source_ids": [],
  "unknown_source_ids": [],
  "future_source_ids": []
}
```

A non-empty `future_source_ids` list is invalid and prevents publication. `evaluated_at` is the focused transaction clock, not an independent wall clock.

### Quality object

```json
{
  "state": "degraded",
  "required_completeness": 1.0,
  "optional_dimensions_available": 0,
  "optional_dimensions_total": 2,
  "point_in_time_safe": false,
  "warnings": [
    "Subsector historical calculations use current membership and are descriptive, not PIT backtests."
  ]
}
```

`state` is `complete`, `degraded`, or `insufficient`. Any missing required source is `insufficient` and fails the builder before publication. `point_in_time_safe=false` is not itself a build failure; it is a mandatory product disclosure. Optional absence may degrade the read without changing `required_completeness`.

### Input-receipt object

```json
{
  "source_id": "site-sector-central",
  "path": "site/sectordata/sector_central.json",
  "sha256": "1111111111111111111111111111111111111111111111111111111111111111",
  "as_of": "2026-09-18",
  "observed_at": "2026-09-18T20:00:00Z",
  "clock_grain": "session",
  "freshness_role": "market_observation",
  "freshness_state": "fresh",
  "required": true,
  "state": "available"
}
```

A conflict `source_ref` is valid only when it equals an admitted receipt `path` or begins with `path + "#/"`. This prefix rule is deterministic and forbids opaque refs that cannot be traced to an input receipt.

### Governance bundle

The dossier nests three existing contracts:

```json
{
  "governance": {
    "packet": {
      "contract_id": "sector_intelligence_packet.v1",
      "sector": "xlk",
      "entity_refs": ["sector:xlk"],
      "security_refs": ["XLK"]
    },
    "lobe_run": {
      "contract_id": "lobe_run.v1",
      "sector": "xlk",
      "lobe_id": "sector_federation"
    },
    "authority_manifest": {
      "contract_id": "authority_manifest.v1",
      "sector": "xlk",
      "publication_tier": "DISPLAY",
      "max_authority": "A1_EXPLAIN"
    }
  }
}
```

Generation identities are deterministic and non-circular:

```python
source_identity = sorted(
    (row["source_id"], row["sha256"])
    for row in input_receipts
    if row.get("sha256")
)
generation_id = canonical_json_sha256({
    "sector": "xlk",
    "common_as_of": common_as_of,
    "code_version": code_version,
    "source_identity": source_identity,
})[:24]

packet_id = f"packet:sector:xlk:{generation_id}"
run_id = f"run:sector-federation:xlk:{generation_id}"
manifest_id = f"authority:sector-dossier:xlk:{generation_id}"
dossier_id = f"dossier:sector:xlk:{generation_id}"
```

The packet includes `run_id` and `manifest_id`, then receives its hash. The lobe run binds the final packet id/hash. The manifest binds the same packet id. The dossier nests all three documents and receives a final dossier hash over canonical bytes excluding `dossier_hash`.

#### Exact packet projection

The strict packet is a governance projection of the dossier, not a second analytical model:

```python
packet = {
    "contract_id": "sector_intelligence_packet.v1",
    "schema_version": "1.0.0",
    "packet_id": packet_id,
    "packet_version": 1,
    "sector": "xlk",
    "producer": {
        "service": "sector-federation",
        "code_version": code_version,
        "owner": "neural_web",
    },
    "generated_at": generated_at,
    "knowledge_cutoff": knowledge_cutoff,
    "entity_refs": ["sector:xlk"],
    "security_refs": ["XLK"],
    "portfolio_exposure": [],
    "current_fact_refs": [
        f"{dossier_id}#/dimensions/{row['dimension_id']}"
        for row in dimensions
    ],
    "material_change_event_refs": [
        f"{dossier_id}#/material_changes/{row['change_id']}"
        for row in material_changes
    ],
    "upcoming_event_refs": [],
    "contradictions": [
        {
            "claim_ref": row["left_ref"],
            "contradicts_claim_ref": row["right_ref"],
            "state": "open",
            "resolution_ref": None,
        }
        for row in conflicts
        if row["class"] == "GENUINE_CONTRADICTION"
    ],
    "freshness": packet_freshness,
    "quality": packet_quality,
    "feature_snapshot_refs": [],
    "prediction_refs": [],
    "evidence_claim_refs": [],
    "source_record_refs": [],
    "lobe_run_ref": run_id,
    "authority_manifest_ref": manifest_id,
    "authority_caps": {
        "max_authority": "A1_EXPLAIN",
        "allowed_actions": ["observe", "explain"],
        "forbidden_actions": [
            "originate_signal",
            "raise_authority_from_llm",
            "rank_security",
            "select_security",
            "size_position",
            "gate_decision",
            "execute_trade",
        ],
        "llm_may_originate_signals": False,
    },
    "hash_scope": "canonical_payload_excluding_packet_hash",
}
packet["packet_hash"] = canonical_json_sha256(packet)
```

Rules:

- `portfolio_exposure` remains empty; STSI-1 does not read tenant positions or watchlists.
- `source_record_refs` remains empty. The consumed JSON/YAML files are internal owner artifacts, not source-native `source_record.v1` objects. Their byte receipts live only in the dossier's `input_receipts`; STSI-1 must not mint synthetic source records to make packet provenance look fuller.
- `upcoming_event_refs`, `feature_snapshot_refs`, `prediction_refs`, and `evidence_claim_refs` remain empty until an existing canonical owner supplies such referenced objects.
- Only `GENUINE_CONTRADICTION` rows enter the packet's `contradictions`; timeframe, scope, freshness, coverage, and authority splits remain explanatory dossier conflicts.
- `quality.point_in_time_safe` is `false` while any required child/group dimension uses current-membership history. The warning names the exact non-PIT owner basis.
- `quality.completeness` measures required source availability, not predictive confidence.
- `freshness.oldest_required_source_at` is the oldest required observation clock, never the generation clock.

#### Exact lobe-run projection

```python
lobe_run = {
    "contract_id": "lobe_run.v1",
    "schema_version": "1.0.0",
    "run_id": run_id,
    "sector": "xlk",
    "lobe_id": "sector_federation",
    "producer": packet["producer"],
    "started_at": generated_at,
    "finished_at": generated_at,
    "knowledge_cutoff": knowledge_cutoff,
    "source_watermarks": source_watermarks,
    "input_hashes": sorted(row["sha256"] for row in input_receipts if row.get("sha256")),
    "output_artifacts": [{
        "artifact_ref": packet_id,
        "content_sha256": packet["packet_hash"],
        "row_count": 1,
    }],
    "warnings": lobe_warnings,
    "failures": [],
    "status": "degraded" if packet_quality["state"] != "complete" else "ok",
    "completeness": packet_quality["completeness"],
    "model_versions": [],
    "authority_manifest_ref": manifest_id,
}
```

`model_versions` is empty because STSI-1 performs deterministic composition only.

The authority manifest must use:

```json
{
  "contract_id": "authority_manifest.v1",
  "schema_version": "1.0.0",
  "manifest_id": "authority:sector-dossier:xlk:0123456789abcdef01234567",
  "sector": "xlk",
  "artifact_ref": "packet:sector:xlk:0123456789abcdef01234567",
  "artifact_type": "sector_intelligence_packet.v1",
  "publication_tier": "DISPLAY",
  "max_authority": "A1_EXPLAIN",
  "allowed_actions": ["observe", "explain"],
  "denied_actions": [
    "originate_signal",
    "raise_authority_from_llm",
    "rank_security",
    "select_security",
    "size_position",
    "gate_decision",
    "execute_trade"
  ],
  "consumers": ["sector_detail"],
  "issued_by": "neural_web_governance",
  "issued_at": "2026-09-18T20:00:00Z",
  "valid_from": "2026-09-18T20:00:00Z",
  "valid_to": null,
  "expires_at": "2026-09-21T20:00:00Z",
  "promotion_evidence_refs": [],
  "governance_decision_refs": [],
  "kill_switch": {
    "enabled": false,
    "owner": "neural_web_governance",
    "reason": null,
    "activated_at": null
  },
  "transaction_from": "2026-09-18T20:00:00Z",
  "transaction_to": null
}
```

A1 does not require promotion evidence. The manifest expires 72 hours after `generated_at`; a stale/expired dossier remains readable as historical context but the product surface must display its degraded state. Lobe warnings and failures use the existing `{code, source_id, detail, retryable}` issue shape; plain strings are invalid.

---

## 4. Task 1 — Add the strict dossier contract and semantic guards

**Files:**

- Create: `contracts/sector_intelligence/sector_dossier_read_model.v1.schema.json`
- Create: `data/sector_intelligence/fixtures/sector_dossier_read_model.v1.valid.json`
- Create: `tests/test_sector_dossier_contract.py`
- Modify: `engine/sector_intelligence/contracts.py`
- Modify: `.github/ci/legacy-jobs.yml`

### Step 1: Write failing contract tests

Create `tests/test_sector_dossier_contract.py` with these first tests:

```python
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.sector_intelligence.contracts import (
    ContractValidationError,
    canonical_json_sha256,
    validate_contract,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data/sector_intelligence/fixtures/sector_dossier_read_model.v1.valid.json"


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text())


def rehash(doc: dict) -> None:
    doc.pop("dossier_hash", None)
    doc["dossier_hash"] = canonical_json_sha256(doc)


def test_valid_sector_dossier_contract() -> None:
    validate_contract("sector_dossier_read_model.v1", load_fixture())


def test_dossier_hash_binds_canonical_payload() -> None:
    doc = load_fixture()
    expected = doc.pop("dossier_hash")
    assert canonical_json_sha256(doc) == expected


def test_dossier_rejects_authority_escalation() -> None:
    doc = load_fixture()
    doc["authority_caps"]["may_rank"] = True
    rehash(doc)
    with pytest.raises(ContractValidationError, match="authority"):
        validate_contract("sector_dossier_read_model.v1", doc)


def test_dossier_rejects_packet_binding_mismatch() -> None:
    doc = load_fixture()
    doc["governance"]["lobe_run"]["authority_manifest_ref"] = "authority:forged"
    rehash(doc)
    with pytest.raises(ContractValidationError, match="governance"):
        validate_contract("sector_dossier_read_model.v1", doc)


def test_dossier_rejects_unknown_conflict_class() -> None:
    doc = load_fixture()
    doc["conflicts"][0]["class"] = "MYSTERY_CONFLICT"
    rehash(doc)
    with pytest.raises(ContractValidationError):
        validate_contract("sector_dossier_read_model.v1", doc)


def test_dossier_preserves_null_concentration() -> None:
    doc = load_fixture()
    doc["concentration"].update(state="unavailable", value=None, n_members=3)
    rehash(doc)
    validate_contract("sector_dossier_read_model.v1", doc)
```

Run:

```bash
python -m pytest tests/test_sector_dossier_contract.py -q
```

Expected: failures because the schema/fixture/semantic validator do not exist.

### Step 2: Add the closed JSON Schema

Implement `sector_dossier_read_model.v1.schema.json` with:

- `additionalProperties: false` at every object level.
- Exact top-level fields from Section 3.
- Closed enums for conflict class, freshness state, quality state, relationship basis, reliability, and authority booleans.
- `$ref` bindings to:
  - `sector_intelligence_packet.v1.schema.json`
  - `lobe_run.v1.schema.json`
  - `authority_manifest.v1.schema.json`
- `dossier_hash` pattern `^[0-9a-f]{64}$`.
- `hash_scope` constant `canonical_payload_excluding_dossier_hash`.
- `sector`/native ids constrained to lower-case stable keys.
- bilingual display fields required together; values may be empty only where the owner genuinely lacks translation.

The new schema must not loosen any existing contract.

### Step 3: Add semantic validation

In `engine/sector_intelligence/contracts.py`:

1. Add a constant:

```python
_SECTOR_DOSSIER_CONTRACT_ID = "sector_dossier_read_model.v1"
```

2. Add `_sector_dossier_issues(document)` enforcing:

```python
- dossier_hash equals canonical_json_sha256(document without dossier_hash)
- packet.sector == lobe_run.sector == authority_manifest.sector == identity.native_id
- packet.lobe_run_ref == lobe_run.run_id
- packet.authority_manifest_ref == authority_manifest.manifest_id
- lobe_run.authority_manifest_ref == authority_manifest.manifest_id
- authority_manifest.artifact_ref == packet.packet_id
- lobe_run.output_artifacts contains packet.packet_id + packet.packet_hash
- nested packet/manifest/lobe each validate against their own contracts
- authority_caps are all false except is_context_only=true
- nested packet authority is no higher than A1_EXPLAIN
- every conflict source ref appears in `input_receipts` or one of the nested packet refs
```

3. Dispatch the semantic validator from the existing semantic-validation switch.

Do not special-case Technology in the contract validator; Technology is an implementation admission rule in the builder.

### Step 4: Create a valid fixture

Create a compact Technology fixture with:

- sector slow/fast split;
- one Semiconductor child;
- one AI Semiconductor connected theme;
- measured participation;
- unavailable concentration variant covered by a separate test;
- one `TIMEFRAME_SPLIT` conflict;
- all-false authority;
- internally consistent packet/lobe/manifest ids and hashes.

Generate fixture hashes with production helpers, not hand-calculated strings.

### Step 5: Run the contract pack

```bash
python -m pytest \
  tests/test_sector_dossier_contract.py \
  tests/test_sector_intelligence_contracts.py \
  -q
```

Expected: all pass; no existing contract test changes behavior.

### Step 6: Register in existing CI

Append `tests/test_sector_dossier_contract.py` to the existing `biocatalyst-contracts` command because that job already owns `tests/test_sector_intelligence_contracts.py`. Do not create a new workflow or CI control plane.

### Step 7: Commit the contract slice

```bash
git add \
  contracts/sector_intelligence/sector_dossier_read_model.v1.schema.json \
  data/sector_intelligence/fixtures/sector_dossier_read_model.v1.valid.json \
  engine/sector_intelligence/contracts.py \
  tests/test_sector_dossier_contract.py \
  .github/ci/legacy-jobs.yml
git commit -m "feat(sector-intelligence): add governed dossier contract"
```

---

## 5. Task 2 — Build the pure owner-preserving federation composer

**Files:**

- Create: `engine/neuralweb/sector_federation.py`
- Create: `tests/fixtures/sector_federation/technology_split_view.v1.json`
- Create: `tests/test_sector_federation.py`
- Modify: `.github/ci/legacy-jobs.yml`

### Step 1: Write the controlled input fixture

The fixture contains reduced owner records, not a new market-data source:

```json
{
  "sector_central": {
    "as_of": "2026-09-18",
    "sector": {
      "id": "xlk",
      "ticker": "XLK",
      "name": "Technology",
      "name_zh": "科技",
      "conviction": {"score": 40, "label_en": "Cautious", "label_zh": "谨慎"},
      "cycle": {"phase": "Downturn", "phaseLabel": "Rolling over"},
      "rotation": {"state": "TOP WATCH", "state_plain_en": "Money rotating in", "state_plain_zh": "资金流入"},
      "split_view": true,
      "split_copy_en": "Slow clock: cautious. Fast tape: money rotating in — split view.",
      "split_copy_zh": "慢周期谨慎，快线资金流入——视角分化。",
      "heat": {"breadth_pct": 41.0, "n_adv": 20, "n_dec": 29}
    }
  },
  "subsector_confluence": {
    "as_of": "2026-09-18",
    "subsectors": [
      {
        "key": "semiconductors",
        "label": "Semiconductors",
        "sector": "Technology",
        "class": "entry_now",
        "entry": {"tier": "T1", "buyable": true, "fresh_bars": 1},
        "regime": {"state": "EXTENDED", "side": "avoid"},
        "reliability": "high",
        "n_priced": 14,
        "n_members": 14,
        "as_of": "2026-09-18"
      }
    ]
  },
  "subsector_rotation": {
    "as_of": "2026-09-18",
    "themes": [
      {"theme": "Semiconductors", "quadrant": "improving"},
      {"theme": "Artificial Intelligence", "quadrant": "leading"}
    ]
  },
  "theme_state": {
    "as_of": "2026-09-18",
    "themes": [
      {
        "theme_id": "ai_semiconductors",
        "name_en": "AI Semiconductors",
        "name_zh": "AI半导体",
        "foresight": {"stage": "WATCH", "entry_ready": false},
        "subsector_keys": ["Semiconductors", "Artificial Intelligence"]
      }
    ]
  },
  "theme_crosswalk": {
    "themes": [
      {
        "id": "ai_semiconductors",
        "primary_basket_id": "ai_semiconductors",
        "subsector_keys": ["Semiconductors", "Artificial Intelligence"]
      }
    ]
  },
  "heatmap": {
    "Technology": [40.0, 20.0, 15.0, 10.0, 5.0, 4.0, 3.0, 2.0, 1.0]
  },
  "input_receipts": [
    {
      "source_id": "site-baskets",
      "path": "site/basketdata/baskets.json",
      "sha256": "0000000000000000000000000000000000000000000000000000000000000001",
      "as_of": "2026-09-18",
      "observed_at": "2026-09-18T20:00:00Z",
      "clock_grain": "session",
      "freshness_role": "market_observation",
      "freshness_state": "fresh",
      "required": true,
      "state": "available"
    },
    {
      "source_id": "site-action-board",
      "path": "site/basketdata/action_board.json",
      "sha256": "0000000000000000000000000000000000000000000000000000000000000002",
      "as_of": "2026-09-18",
      "observed_at": "2026-09-18T20:00:00Z",
      "clock_grain": "instant",
      "freshness_role": "market_observation",
      "freshness_state": "fresh",
      "required": true,
      "state": "available"
    },
    {
      "source_id": "site-sector-central",
      "path": "site/sectordata/sector_central.json",
      "sha256": "0000000000000000000000000000000000000000000000000000000000000003",
      "as_of": "2026-09-18",
      "observed_at": "2026-09-18T20:00:00Z",
      "clock_grain": "session",
      "freshness_role": "market_observation",
      "freshness_state": "fresh",
      "required": true,
      "state": "available"
    },
    {
      "source_id": "site-subsector-confluence",
      "path": "site/marketdata/subsector_confluence.json",
      "sha256": "0000000000000000000000000000000000000000000000000000000000000004",
      "as_of": "2026-09-18",
      "observed_at": "2026-09-18T20:00:00Z",
      "clock_grain": "session",
      "freshness_role": "market_observation",
      "freshness_state": "fresh",
      "required": true,
      "state": "available"
    },
    {
      "source_id": "site-subsector-rotation",
      "path": "site/marketdata/subsector_rotation.json",
      "sha256": "0000000000000000000000000000000000000000000000000000000000000005",
      "as_of": "2026-09-18",
      "observed_at": "2026-09-18T20:00:00Z",
      "clock_grain": "session",
      "freshness_role": "market_observation",
      "freshness_state": "fresh",
      "required": true,
      "state": "available"
    },
    {
      "source_id": "site-theme-state",
      "path": "site/neuralwebdata/theme_state.json",
      "sha256": "0000000000000000000000000000000000000000000000000000000000000006",
      "as_of": "2026-09-18",
      "observed_at": "2026-09-18T20:00:00Z",
      "clock_grain": "session",
      "freshness_role": "market_observation",
      "freshness_state": "fresh",
      "required": true,
      "state": "available"
    },
    {
      "source_id": "theme-crosswalk",
      "path": "config/theme_crosswalk.yml",
      "sha256": "0000000000000000000000000000000000000000000000000000000000000007",
      "as_of": null,
      "observed_at": "2026-09-18T20:00:00Z",
      "clock_grain": "static",
      "freshness_role": "static_config",
      "freshness_state": "not_applicable",
      "required": true,
      "state": "available"
    },
    {
      "source_id": "sp500-heatmap",
      "path": "site/marketdata/sp500_heatmap.json",
      "sha256": "0000000000000000000000000000000000000000000000000000000000000008",
      "as_of": "2026-09-18",
      "observed_at": "2026-09-18T20:00:00Z",
      "clock_grain": "session",
      "freshness_role": "market_observation",
      "freshness_state": "fresh",
      "required": true,
      "state": "available"
    }
  ]
}
```

Add a provenance note in the test module: values are a controlled reduction of the September 18 Technology split, not a current market artifact.

### Step 2: Write failing composer tests

Create `tests/test_sector_federation.py`:

```python
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from engine.neuralweb.sector_federation import (
    FederationInputs,
    UnsupportedSector,
    compose_sector_dossier,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/sector_federation/technology_split_view.v1.json"


def inputs() -> FederationInputs:
    raw = json.loads(FIXTURE.read_text())
    return FederationInputs.from_mapping(raw)


def compose(**overrides) -> dict:
    kwargs = {
        "inputs": inputs(),
        "sector_id": "xlk",
        "common_as_of": "2026-09-18",
        "generated_at": "2026-09-18T20:00:00Z",
        "code_version": "test-sha",
    }
    kwargs.update(overrides)
    return compose_sector_dossier(**kwargs)


def test_composes_existing_sector_identity() -> None:
    dossier = compose()
    assert dossier["identity"]["entity_id"] == "sector:xlk"
    assert dossier["identity"]["native_id"] == "xlk"
    assert dossier["identity"]["ticker"] == "XLK"


def test_slow_fast_split_is_timeframe_split() -> None:
    dossier = compose()
    conflicts = {row["conflict_id"]: row for row in dossier["conflicts"]}
    assert conflicts["conflict:xlk:slow-vs-fast"]["class"] == "TIMEFRAME_SPLIT"


def test_fresh_entry_but_extended_group_is_timeframe_split() -> None:
    dossier = compose()
    conflicts = {row["conflict_id"]: row for row in dossier["conflicts"]}
    row = conflicts["conflict:xlk:semiconductors-entry-vs-regime"]
    assert row["class"] == "TIMEFRAME_SPLIT"
    assert "extended" in row["summary_en"].lower()


def test_narrow_parent_with_strong_child_is_scope_split() -> None:
    dossier = compose()
    conflicts = {row["conflict_id"]: row for row in dossier["conflicts"]}
    assert conflicts["conflict:xlk:parent-breadth-vs-semiconductors"]["class"] == "SCOPE_SPLIT"


def test_connected_themes_require_exact_crosswalk_relation() -> None:
    dossier = compose()
    assert [row["theme_id"] for row in dossier["connected_themes"]] == ["ai_semiconductors"]

    raw = json.loads(FIXTURE.read_text())
    raw["theme_crosswalk"]["themes"][0]["subsector_keys"] = ["Almost Semiconductors"]
    disconnected = compose(inputs=FederationInputs.from_mapping(raw))
    assert disconnected["connected_themes"] == []


def test_group_entry_does_not_qualify_member_stocks() -> None:
    dossier = compose()
    assert "member_candidates" not in dossier
    assert all("members" not in child for child in dossier["children"])
    assert dossier["authority_caps"]["may_rank"] is False


def test_missing_optional_leadership_is_typed_unavailable() -> None:
    raw = json.loads(FIXTURE.read_text())
    raw.pop("optional_leadership", None)
    dossier = compose(inputs=FederationInputs.from_mapping(raw))
    leadership = next(row for row in dossier["dimensions"] if row["dimension_id"] == "closed_session_leadership")
    assert leadership["state"] == "UNAVAILABLE"
    assert leadership["value"] is None


def test_missing_optional_entry_context_is_typed_unavailable() -> None:
    raw = json.loads(FIXTURE.read_text())
    raw.pop("optional_entry_context", None)
    dossier = compose(inputs=FederationInputs.from_mapping(raw))
    group_entry = next(row for row in dossier["dimensions"] if row["dimension_id"] == "group_entry_context")
    assert group_entry["state"] == "UNAVAILABLE"


def test_concentration_uses_positive_market_cap_sizes() -> None:
    dossier = compose()
    assert dossier["concentration"]["method"] == "market_cap_top5_share"
    assert dossier["concentration"]["value"] == pytest.approx(90 / 100)


def test_thin_cap_coverage_preserves_null() -> None:
    raw = json.loads(FIXTURE.read_text())
    raw["heatmap"]["Technology"] = [40.0, 30.0, 20.0]
    dossier = compose(inputs=FederationInputs.from_mapping(raw))
    assert dossier["concentration"]["state"] == "unavailable"
    assert dossier["concentration"]["value"] is None


def test_different_required_as_of_dates_emit_freshness_split() -> None:
    raw = json.loads(FIXTURE.read_text())
    raw["subsector_confluence"]["as_of"] = "2026-09-17"
    raw["subsector_confluence"]["subsectors"][0]["as_of"] = "2026-09-17"
    receipt = next(row for row in raw["input_receipts"] if row["source_id"] == "site-subsector-confluence")
    receipt.update(as_of="2026-09-17", observed_at="2026-09-17T20:00:00Z", freshness_state="degraded")
    dossier = compose(inputs=FederationInputs.from_mapping(raw))
    assert dossier["freshness"]["state"] == "degraded"
    assert any(row["class"] == "FRESHNESS_SPLIT" for row in dossier["conflicts"])


def test_future_required_receipt_is_rejected() -> None:
    raw = json.loads(FIXTURE.read_text())
    receipt = next(row for row in raw["input_receipts"] if row["source_id"] == "site-subsector-confluence")
    receipt.update(as_of="2026-09-19", observed_at="2026-09-19T20:00:00Z")
    with pytest.raises(ValueError, match="future"):
        compose(inputs=FederationInputs.from_mapping(raw))


def test_genuine_contradiction_requires_same_scope_horizon_and_freshness() -> None:
    raw = json.loads(FIXTURE.read_text())
    raw["same_horizon_owner_read"] = {
        "scope": "sector",
        "horizon": "multi_year_cycle",
        "state": "constructive",
        "as_of": "2026-09-18",
        "source_ref": "fixture#/same_horizon_owner_read"
    }
    dossier = compose(inputs=FederationInputs.from_mapping(raw))
    assert any(row["class"] == "GENUINE_CONTRADICTION" for row in dossier["conflicts"])


def test_composition_is_byte_deterministic() -> None:
    first = compose()
    second = compose()
    assert first == second
    assert first["dossier_hash"] == second["dossier_hash"]


def test_duplicate_source_receipts_are_rejected() -> None:
    raw = json.loads(FIXTURE.read_text())
    raw["input_receipts"].append(copy.deepcopy(raw["input_receipts"][0]))
    with pytest.raises(ValueError, match="duplicate source_id"):
        FederationInputs.from_mapping(raw)


def test_malformed_source_hash_is_rejected() -> None:
    raw = json.loads(FIXTURE.read_text())
    raw["input_receipts"][0]["sha256"] = "not-a-sha"
    with pytest.raises(ValueError, match="sha256"):
        FederationInputs.from_mapping(raw)


def test_only_reference_sector_is_admitted() -> None:
    with pytest.raises(UnsupportedSector):
        compose(sector_id="xlf")
```

Run:

```bash
python -m pytest tests/test_sector_federation.py -q
```

Expected: import/module failures before implementation.

### Step 3: Implement the pure composer

Create `engine/neuralweb/sector_federation.py` with this public interface:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


class FederationError(RuntimeError):
    pass


class UnsupportedSector(FederationError):
    pass


@dataclass(frozen=True)
class FederationInputs:
    sector_central: Mapping[str, Any]
    subsector_confluence: Mapping[str, Any]
    subsector_rotation: Mapping[str, Any]
    theme_state: Mapping[str, Any]
    theme_crosswalk: Mapping[str, Any]
    heatmap: Mapping[str, Sequence[float]]
    optional_leadership: Mapping[str, Any] | None = None
    input_receipts: tuple[Mapping[str, Any], ...]
    optional_leadership: Mapping[str, Any] | None = None
    optional_entry_context: Mapping[str, Any] | None = None
    same_horizon_owner_read: Mapping[str, Any] | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "FederationInputs":
        """Validate typed owner payloads and builder-supplied source receipts."""
        ...


def compose_sector_dossier(
    *,
    inputs: FederationInputs,
    sector_id: str,
    common_as_of: str,
    generated_at: str,
    code_version: str,
) -> dict[str, Any]:
    ...
```

Implementation decomposition:

```python
_REFERENCE_SECTOR = "xlk"
_ENTITY_ID = "sector:xlk"
_TICKER = "XLK"


def _find_sector(...): ...
def _technology_children(...): ...
def _connected_themes(...): ...
def _participation(...): ...
def _concentration(...): ...
def _dimensions(...): ...
def _conflicts(...): ...
def _headline(...): ...
def _material_changes(...): ...
def _watch_conditions(...): ...
def _quality_and_freshness(...): ...
def _governance_bundle(...): ...
def _finalize_dossier_hash(...): ...
```

Rules:

- No filesystem reads.
- `input_receipts` are mandatory builder evidence. `from_mapping` rejects duplicate `source_id`, malformed/non-null hashes, unavailable required sources, unknown clock/freshness enums, and receipts whose path does not match the admitted source registry.
- `common_as_of` must be an ISO date supplied by the builder. Required auxiliary market receipts may be equal to or older than it; future receipts are rejected. The composer never chooses a different common date.
- The composer sorts input receipts by `source_id` and uses their `(source_id, sha256)` pairs for generation identity. It never reconstructs a file hash, path, or observation clock from parsed domain payloads.
- No implicit current time; all clocks are supplied.
- No owner signal calculation or re-scoring.
- Preserve source-native states and values inside `value`.
- Translate only through fixed bilingual copy maps in this module.
- Sort children by canonical key, themes by canonical theme id, dimensions by a fixed explicit order, conflicts by `conflict_id`, and input receipts by source id.
- Never sort groups or themes by a magnitude inside the federation.
- Validate the nested packet, lobe, manifest, and final dossier before returning.
- Reject NaN, infinity, malformed timestamps, duplicate source ids, and unknown conflict classes.

The fixed dimension order is:

```python
_DIMENSION_ORDER = (
    "sector_slow_clock",
    "sector_fast_tape",
    "sector_participation",
    "sector_concentration",
    "subsector_entry",
    "closed_session_leadership",
    "theme_health",
    "group_entry_context",
)
```

### Step 4: Implement deterministic headline composition

Use a finite copy matrix. Do not call an LLM and do not concatenate internal enum names directly.

```python
def _headline(sector: Mapping[str, Any], participation: Mapping[str, Any], children: list[dict]) -> dict:
    split = bool(sector.get("split_view"))
    breadth = participation.get("value")
    semis = next((row for row in children if row["native_key"] == "semiconductors"), None)
    if split and semis and semis.get("class") == "entry_now" and semis.get("regime_state") == "EXTENDED" and breadth is not None and breadth < 50:
        return {
            "state": "selective_leadership",
            "summary_en": (
                "Technology has a constructive fast tape but a cautious slow clock. "
                "Semiconductor timing has refreshed, yet the group is already extended "
                "and sector participation remains narrow."
            ),
            "summary_zh": (
                "科技板块快线偏强，但慢周期仍保持谨慎。半导体择时已重新转强，"
                "但该组已偏延伸，板块参与度仍然有限。"
            ),
            "posture_en": "Selective leadership — participate carefully; do not treat it as broad sector confirmation.",
            "posture_zh": "选择性领涨——谨慎参与，勿视为板块全面确认。",
        }
    ...
```

Every fallback case must be explicitly tested. Unknown combinations render `state="mixed_or_incomplete"` and neutral copy; they never guess.

### Step 5: Validate and run the composer pack

```bash
python -m pytest \
  tests/test_sector_federation.py \
  tests/test_sector_dossier_contract.py \
  tests/test_thematic_state.py \
  tests/test_subsector_confluence.py \
  -q
```

Expected: all pass; incumbent owner outputs and policies remain unchanged.

### Step 6: Register the composer tests in existing CI

Append `tests/test_sector_federation.py` to the existing `neural-web-core` job. Do not create a new workflow or independent federation job.

### Step 7: Commit the composer slice

```bash
git add \
  engine/neuralweb/sector_federation.py \
  tests/fixtures/sector_federation/technology_split_view.v1.json \
  tests/test_sector_federation.py \
  .github/ci/legacy-jobs.yml
git commit -m "feat(sector-intelligence): compose Technology federation dossier"
```

---

## 6. Task 3 — Add the single atomic dossier builder

**Files:**

- Create: `scripts/build_sector_dossiers.py`
- Create: `tests/test_build_sector_dossiers.py`
- Modify: `config/synapse.yml`
- Modify: `.github/ci/legacy-jobs.yml`

### Step 1: Write failing builder tests

```python
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import build_sector_dossiers as builder


def seed_required_inputs(root: Path) -> None:
    ...  # copy the controlled fixture into the exact repository paths the builder reads


def test_required_missing_input_fails_without_overwrite(tmp_path: Path) -> None:
    out = tmp_path / "site/sectordata/sector_dossiers/xlk.json"
    out.parent.mkdir(parents=True)
    out.write_text('{"sentinel":true}')
    assert builder.build(tmp_path, generated_at="2026-09-18T20:00:00Z", code_version="test") == 1
    assert json.loads(out.read_text()) == {"sentinel": True}


def test_valid_inputs_write_one_contract_valid_dossier(tmp_path: Path) -> None:
    seed_required_inputs(tmp_path)
    assert builder.build(tmp_path, generated_at="2026-09-18T20:00:00Z", code_version="test") == 0
    payload = json.loads((tmp_path / "site/sectordata/sector_dossiers/xlk.json").read_text())
    assert payload["contract_id"] == "sector_dossier_read_model.v1"
    assert payload["identity"]["entity_id"] == "sector:xlk"


def test_builder_is_idempotent_for_fixed_inputs_and_clock(tmp_path: Path) -> None:
    seed_required_inputs(tmp_path)
    builder.build(tmp_path, generated_at="2026-09-18T20:00:00Z", code_version="test")
    first = (tmp_path / "site/sectordata/sector_dossiers/xlk.json").read_bytes()
    builder.build(tmp_path, generated_at="2026-09-18T20:00:00Z", code_version="test")
    assert (tmp_path / "site/sectordata/sector_dossiers/xlk.json").read_bytes() == first


def test_optional_leadership_field_absence_is_not_global_failure(tmp_path: Path) -> None:
    seed_required_inputs(tmp_path)
    path = tmp_path / "site/marketdata/subsector_rotation.json"
    rotation = json.loads(path.read_text())
    rotation.pop("closed_session_leadership", None)
    for row in rotation.get("themes", []):
        row.pop("leadership_observation", None)
    path.write_text(json.dumps(rotation))
    assert builder.build(tmp_path, generated_at="2026-09-18T20:00:00Z", code_version="test") == 0
    payload = json.loads((tmp_path / "site/sectordata/sector_dossiers/xlk.json").read_text())
    row = next(x for x in payload["dimensions"] if x["dimension_id"] == "closed_session_leadership")
    assert row["state"] == "UNAVAILABLE"


def test_builder_refuses_unadmitted_sector(tmp_path: Path) -> None:
    seed_required_inputs(tmp_path)
    with pytest.raises(builder.BuildError, match="xlk"):
        builder.build(tmp_path, sector_id="xlf", generated_at="2026-09-18T20:00:00Z", code_version="test")
```

Run:

```bash
python -m pytest tests/test_build_sector_dossiers.py -q
```

Expected: missing module/import failures.

### Step 2: Implement exact input ownership

Required inputs:

```text
site/basketdata/baskets.json
site/basketdata/action_board.json
site/sectordata/sector_central.json
site/marketdata/subsector_confluence.json
site/marketdata/subsector_rotation.json
site/neuralwebdata/theme_state.json
config/theme_crosswalk.yml
site/marketdata/sp500_heatmap.json
```

Optional accepted input:

```text
site/basketdata/theme_lanes.json  # only when its accepted schema carries entry_context dimensions
```

Lane C leadership is not a second file: after #7455 acceptance it is embedded under `closed_session_leadership` and per-theme `leadership_observation` inside the required `subsector_rotation.json`. The builder extracts those optional fields from the already-hashed owner artifact; absent fields produce an unavailable dimension rather than a missing-source failure.

#### Common semantic date

The builder inherits, rather than invents, the focused publisher's common date:

```python
core_dates = {
    "baskets": baskets["as_of"],
    "theme_intel": baskets["theme_intel"]["as_of"],
    "action_board": action_board["as_of"],
    "sector_central": sector_central["as_of"],
}
if len(set(core_dates.values())) != 1:
    raise BuildError(f"focused generation vintage split: {core_dates}")
common_as_of = next(iter(core_dates.values()))
```

The final #7211 freshness checker remains responsible for proving that premium projection and `sector_central.html` carry this same date. Auxiliary required inputs—Subsector Confluence, rotation, ThemeState, and heatmap—may be older than `common_as_of`; they remain visible and generate `FRESHNESS_SPLIT` plus degraded freshness. An auxiliary receipt newer than `common_as_of` is a future/split-generation error and fails publication. Static configuration is excluded from market-age calculations.

Do not read generated page HTML as a data source.

### Step 3: Implement raw-byte input receipts

For every required and present optional source:

```python
raw = path.read_bytes()
source_hash = hashlib.sha256(raw).hexdigest()
payload = parse(raw)
input_receipts.append(build_input_receipt(spec, payload, source_hash))
```

The builder passes the immutable `tuple(input_receipts)` into `FederationInputs`. The composer owns semantic joins and governance projection; the builder alone owns filesystem paths, raw-byte hashes, and file-derived observation receipts. `build_input_receipt` is a dossier-local receipt helper, not an implementation of `source_record.v1`.

The dossier `input_receipts` carries:

```json
{
  "source_id": "site-sector-central",
  "path": "site/sectordata/sector_central.json",
  "sha256": "1111111111111111111111111111111111111111111111111111111111111111",
  "as_of": "2026-09-18",
  "observed_at": "2026-09-18T20:00:00Z",
  "clock_grain": "session",
  "freshness_role": "market_observation",
  "freshness_state": "fresh",
  "required": true,
  "state": "available"
}
```

Allowed `clock_grain` values are `instant`, `session`, and `static`. Allowed `freshness_role` values are `market_observation`, `static_config`, and `optional_context`. `freshness_state` is one of `fresh`, `degraded`, `stale`, `unknown`, or `not_applicable`; only static configuration may use `not_applicable`. Static configuration is hash-bound but excluded from market-freshness age calculations.

Aggregation law:

- all required market receipts fresh and aligned → packet freshness `fresh`;
- any required market receipt older than `common_as_of` or owner-marked degraded → `degraded` and a `FRESHNESS_SPLIT`;
- any owner-marked stale required receipt → `stale`;
- unknown clocks without a stale/degraded determination → `unknown`;
- an optional missing dimension degrades quality but does not create a required-source freshness failure;
- `oldest_required_source_at` is the minimum `observed_at` across required market receipts;
- required-source completeness is a ratio of available required receipts, never predictive confidence.

For U.S. session-date artifacts, convert `as_of` to a UTC observation instant with the existing DST/early-close-aware owner:

```python
from datetime import date, timezone
from engine.session_digest import session_window_et


def _session_close_utc(as_of: str) -> str:
    _open_et, close_et = session_window_et(date.fromisoformat(as_of))
    return close_et.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
```

Never stamp a date-grain market artifact at midnight UTC or reuse the dossier build time as its observation time. `knowledge_cutoff` remains the focused transaction's accepted `generated_utc` upper bound; input receipts preserve the earlier market clocks.

Missing required source: builder returns non-zero and preserves prior output bytes.
Missing optional source: builder emits a source row with `state="unavailable"`, `sha256=null`, and the associated dimension is unavailable.

### Step 4: Implement atomic publication

```python
def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(temp, path)
```

Validate all nested contracts and the dossier contract before `_atomic_write`.

### Step 5: Implement CLI

```bash
python -m scripts.build_sector_dossiers \
  --root . \
  --reference-sector xlk \
  --generated-at 2026-09-18T20:00:00Z \
  --code-version "$(git rev-parse HEAD)"
```

CLI rules:

- `--reference-sector` defaults to `xlk` and refuses any other value in STSI-1.
- `--generated-at` is a test/replay override. Production defaults to the accepted `action_board.generated_utc` from the focused transaction and refuses a missing or malformed stamp; it never invents a second build clock.
- `--code-version` defaults to `git rev-parse HEAD`; failure to resolve is fatal.
- Success prints one GitHub notice starting at column 0 with dossier id, common as-of, source count, and conflict count.
- Failure prints one GitHub error starting at column 0 and returns non-zero.

### Step 6: Register producer ownership without creating a second execution path

Do **not** add `scripts.build_sector_dossiers` as a standalone daily DAG step. Its only production invocation is inside `scripts.build_sector_intelligence.py`, between Sector Central and the focused validator. Adding it to the broad nightly DAG would create a second publication path and violate the one-publisher ruling.

In `config/synapse.yml`, register the artifact using the registry's complete shape:

```yaml
site-sector-dossier-xlk:
  path: site/sectordata/sector_dossiers/xlk.json
  format: json
  producer: scripts/build_sector_dossiers.py
  known_extra_writers: []
  owner_program: neural-web
  cadence: sector-intelligence-focused
  storage: git
  asof_field: common_as_of
  freshness_sla_hours: 30
  schema: sector_dossier_read_model.v1
  tier: display
  horizon_role: context
  weights: none
  scored_path_surfaces: []
  consumers:
    - templates/sector_dossier.js
    - scripts/check_sector_intelligence_freshness.py
  external_consumers: []
  notes: >
    STSI-1 read-only Technology sector dossier. Written atomically only by the
    focused Sector Intelligence transaction. Nested authority is A1_EXPLAIN;
    may_rank/may_gate/may_size/may_escalate/may_trade/may_modify_prophet are false.
```

No wildcard directory writer, external consumer, daily DAG step, or alternate publisher is added.

### Step 7: Run builder and ownership tests

```bash
python -m pytest \
  tests/test_build_sector_dossiers.py \
  tests/test_sector_federation.py \
  tests/test_synapse_registry.py \
  tests/test_synapse_registry_contract.py \
  -q
```

### Step 8: Register the builder tests in existing CI

Append `tests/test_build_sector_dossiers.py` to `neural-web-core`, which already owns Neural Web composition code. Do not create a new job or route the producer into the broad nightly DAG.

### Step 9: Commit

```bash
git add \
  scripts/build_sector_dossiers.py \
  tests/test_build_sector_dossiers.py \
  config/synapse.yml \
  .github/ci/legacy-jobs.yml
git commit -m "feat(sector-intelligence): publish atomic Technology dossier"
```

---

## 7. Task 4 — Extend the incumbent focused publisher and freshness gate

**Prerequisite:** PR `#7211` or its accepted successor is merged. Reconcile its actual merged interfaces before editing; the snippets below express required behavior, not permission to overwrite a changed owner contract.

**Files:**

- Modify: `scripts/build_sector_intelligence.py`
- Modify: `scripts/check_sector_intelligence_freshness.py`
- Modify: `.github/workflows/sector-intelligence.yml`
- Modify: `tests/test_sector_intelligence_page.py`
- Modify: `tests/test_nightly_liveness.py`

### Step 1: Add failing publisher-order tests to the incumbent owner suite

Extend `tests/test_sector_intelligence_page.py`, where #7211 already keeps the focused-generation tests:

```python
def test_focused_builder_orders_dossier_after_central_before_validator() -> None:
    from scripts import build_sector_intelligence as target

    names = [name for name, _invoke in target.default_steps()]
    assert names == [
        "scripts.build_baskets",
        "scripts.build_sector_action_board",
        "scripts.build_sector_central",
        "scripts.build_sector_dossiers",
        "scripts.check_sector_intelligence_freshness",
    ]


def test_run_steps_stops_on_dossier_failure() -> None:
    from scripts.build_sector_intelligence import run_steps

    calls: list[str] = []
    steps = [
        ("central", lambda: calls.append("central") or 0),
        ("dossier", lambda: calls.append("dossier") or 1),
        ("validate", lambda: calls.append("validate") or 0),
    ]
    assert run_steps(steps) == 1
    assert calls == ["central", "dossier"]
```

Run:

```bash
python -m pytest tests/test_sector_intelligence_page.py -q
```

Expected: the order test fails because the focused lane does not yet invoke the dossier builder.

### Step 2: Extend the existing semantic-generation fixture and tests

Extend #7211's `_write_sector_intelligence_generation(...)` helper in `tests/test_sector_intelligence_page.py` so a complete generation writes a contract-valid `site/sectordata/sector_dossiers/xlk.json` from the valid fixture, with ids, source hashes, and common as-of rebound through production hash helpers.

Add:

```python
def test_semantic_freshness_rejects_missing_xlk_dossier(tmp_path: Path) -> None:
    _write_sector_intelligence_generation(tmp_path, action_asof="2026-09-14")
    (tmp_path / "site/sectordata/sector_dossiers/xlk.json").unlink()
    report = _evaluate_sector_intelligence(tmp_path)
    assert report["ok"] is False
    assert any("sector dossier" in error.lower() for error in report["errors"])


def test_dossier_common_as_of_must_match_focused_generation(tmp_path: Path) -> None:
    _write_sector_intelligence_generation(tmp_path, action_asof="2026-09-14")
    path = tmp_path / "site/sectordata/sector_dossiers/xlk.json"
    payload = json.loads(path.read_text())
    payload["common_as_of"] = "2026-09-13"
    _rewrite_dossier_hashes(payload)
    path.write_text(json.dumps(payload, separators=(",", ":")))
    report = _evaluate_sector_intelligence(tmp_path)
    assert report["ok"] is False
    assert any("common_as_of" in error for error in report["errors"])


def test_dossier_governance_binding_is_required(tmp_path: Path) -> None:
    _write_sector_intelligence_generation(tmp_path, action_asof="2026-09-14")
    path = tmp_path / "site/sectordata/sector_dossiers/xlk.json"
    payload = json.loads(path.read_text())
    payload["governance"]["lobe_run"]["authority_manifest_ref"] = "authority:forged"
    path.write_text(json.dumps(payload, separators=(",", ":")))
    report = _evaluate_sector_intelligence(tmp_path)
    assert report["ok"] is False
    assert any("governance" in error.lower() for error in report["errors"])


def test_optional_dimension_unavailable_is_valid(tmp_path: Path) -> None:
    _write_sector_intelligence_generation(
        tmp_path,
        action_asof="2026-09-14",
        optional_leadership=False,
    )
    assert _evaluate_sector_intelligence(tmp_path)["ok"] is True


def test_required_dossier_source_cannot_be_newer_than_common_as_of(tmp_path: Path) -> None:
    _write_sector_intelligence_generation(tmp_path, action_asof="2026-09-14")
    path = tmp_path / "site/sectordata/sector_dossiers/xlk.json"
    payload = json.loads(path.read_text())
    required = next(row for row in payload["input_receipts"] if row["required"])
    required["as_of"] = "2026-09-15"
    _rewrite_dossier_hashes(payload)
    path.write_text(json.dumps(payload, separators=(",", ":")))
    report = _evaluate_sector_intelligence(tmp_path)
    assert report["ok"] is False
    assert any("future source" in error.lower() for error in report["errors"])
```

`_rewrite_dossier_hashes` must call the production canonical hash helpers. It must not duplicate hash logic inside the test.

### Step 3: Extend nightly-liveness registration

In `tests/test_nightly_liveness.py`, extend #7211's Sector Intelligence registry expectations:

```python
expected = {
    "si_baskets": "site/basketdata/baskets.json",
    "si_action": "site/basketdata/action_board.json",
    "si_sector": "site/sectordata/sector_central.json",
    "si_dossier": "site/sectordata/sector_dossiers/xlk.json",
}
```

The vintage-split test includes `si_dossier` and requires the same accepted semantic as-of as the other three focused artifacts.

### Step 4: Insert the dossier builder into the single transaction

In `scripts/build_sector_intelligence.py::default_steps()`:

```python
from scripts import build_sector_dossiers

return [
    ("scripts.build_baskets", lambda: build_baskets.main(sector_intelligence_only=True)),
    ("scripts.build_sector_action_board", build_sector_action_board.main),
    ("scripts.build_sector_central", lambda: build_sector_central.main(strict=True)),
    ("scripts.build_sector_dossiers", lambda: build_sector_dossiers.main([])),
    (
        "scripts.check_sector_intelligence_freshness",
        lambda: check_sector_intelligence_freshness.main([]),
    ),
]
```

The dossier builder reads `generated_at` from the accepted `action_board.generated_utc` and resolves `code_version` from the checked-out git head. The CLI override exists only for deterministic tests/replays. Production does not call `datetime.now()` and cannot create a second publication clock.

### Step 5: Extend the incumbent validator

`check_sector_intelligence_freshness.py` must validate:

1. `site/sectordata/sector_dossiers/xlk.json` exists.
2. It validates as `sector_dossier_read_model.v1`, including nested governance contracts.
3. `identity.native_id == "xlk"`, `identity.entity_id == "sector:xlk"`, and `identity.ticker == "XLK"`.
4. `common_as_of` equals the focused generation's common semantic as-of.
5. Required input receipts are available, hashed, and not newer than `common_as_of`.
6. Source hashes equal current raw bytes for files published in the focused transaction.
7. Packet, lobe, manifest, and dossier generation identities are internally coherent.
8. `authority_caps` remain all false except `is_context_only=true`.
9. `site/sectors/XLK.html` declares the exact dossier URL and contract id.
10. Optional source/dimension unavailability is legal and does not become a global freshness failure.

Do not require a current source that the focused publisher does not own. External optional input dates affect dossier quality/freshness fields, not the transaction's ability to publish valid required facts.

### Step 6: Extend the existing workflow, not create another one

In `.github/workflows/sector-intelligence.yml`:

- Add the new source/test/config paths to the existing trigger list.
- Add `site/sectordata/sector_dossiers` and `site/sector_dossier.js` to the existing scoped `git add` set.
- Keep `site/sectors` on the same existing publisher; `build_sector_action_board` already calls the canonical `build_site.build_sector_pages` producer.
- Keep the same checkout, retry, commit, rebase, monotonicity, and publication owner.
- Do not add another schedule, push retry, cache, branch, or deploy step.

Add static workflow assertions to `tests/test_sector_intelligence_page.py` for the new step order, trigger paths, and staging paths.

### Step 7: Run the focused publisher pack

```bash
python -m pytest \
  tests/test_sector_intelligence_page.py \
  tests/test_nightly_liveness.py \
  tests/test_build_sector_dossiers.py \
  -q
```

Then execute the real focused path in a full checkout:

```bash
python -m scripts.build_sector_intelligence
python -m scripts.check_sector_intelligence_freshness
```

Expected:

- one coherent basket/action/Sector Central/dossier generation;
- valid `xlk.json` with matching common as-of;
- refreshed `site/sectors/XLK.html` through the incumbent action-board/sector-page producer;
- no unrelated full-site build;
- non-zero on any required split-vintage or hash mismatch.

### Step 8: Commit the focused-publication slice

```bash
git add \
  scripts/build_sector_intelligence.py \
  scripts/check_sector_intelligence_freshness.py \
  .github/workflows/sector-intelligence.yml \
  tests/test_sector_intelligence_page.py \
  tests/test_nightly_liveness.py
git commit -m "feat(sector-intelligence): bind dossier to focused publication"
```

---

## 8. Task 5 — Add the Technology dossier product experience

**Files:**

- Create: `templates/sector_dossier.js`
- Create: `site/sector_dossier.js`
- Create: `tests/test_sector_dossier_page.py`
- Modify: `templates/sector.html.j2`
- Modify: `scripts/build_site.py`
- Modify: `.github/ci/legacy-jobs.yml`

### Step 1: Complete required design preflight

Before authoring UI source:

1. Read `docs/DESIGN_DOCTRINE.md` from fresh implementation main.
2. Read `research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md` and the canonical specimen.
3. Use the repository's approved frontend-design skill/tool in the implementation environment.
4. Capture the current `sectors/XLK.html` baseline in dark/light × EN/ZH × 1440/390.
5. Record explicit art directions:
   - **Dark:** command-center instrument panel; restrained depth; no glowing dashboard clutter.
   - **Light:** research sheet; cool canvas; white material cards; hairline boundaries; shadow rather than glow.
6. Keep the existing global navigation family and `theme.css`; no third header or parallel token system.

### Step 2: Write failing static page tests

Create `tests/test_sector_dossier_page.py`:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates/sector.html.j2"
JS = ROOT / "templates/sector_dossier.js"


def test_sector_page_declares_federation_mount_and_contract():
    text = TEMPLATE.read_text()
    assert 'id="sector-federation"' in text
    assert '{% if s.sector_dossier and s.sector_dossier.enabled %}' in text
    assert 'data-contract="{{ s.sector_dossier.contract }}"' in text
    assert 'data-dossier-url="{{ s.sector_dossier.url }}"' in text
    assert 'data-sector-id="{{ s.sector_dossier.sector_id }}"' in text


def test_sector_dossier_script_is_external_and_shared():
    text = TEMPLATE.read_text()
    assert '<script src="../sector_dossier.js"></script>' in text
    assert "style.textContent" not in JS.read_text()


def test_page_has_bilingual_glance_and_typed_fallback_copy():
    text = TEMPLATE.read_text()
    assert "Sector intelligence" in text
    assert "板块情报" in text
    assert "Detailed read unavailable" in text
    assert "详细研判暂不可用" in text


def test_dossier_does_not_claim_ranking_or_trade_authority():
    combined = TEMPLATE.read_text() + JS.read_text()
    for forbidden in ("rank_security", "select_security", "size_position", "execute_trade"):
        assert forbidden not in combined
```

Add a Node parse test for `templates/sector_dossier.js` and paired-byte sync for its `site/` copy.

Run:

```bash
python -m pytest tests/test_sector_dossier_page.py -q
```

Expected: failures because the mount/script do not exist.

### Step 3: Add the server-rendered baseline shell

Insert after the current high-level timing/confluence context and before the detailed chart/holdings depth:

```html
{% if s.sector_dossier and s.sector_dossier.enabled %}
<section
  class="panel sd-shell"
  id="sector-federation"
  data-contract="{{ s.sector_dossier.contract }}"
  data-dossier-url="{{ s.sector_dossier.url }}"
  data-sector-id="{{ s.sector_dossier.sector_id }}"
  aria-labelledby="sector-federation-title">
  <div class="sd-head">
    <div>
      <p class="eyebrow">{{ t('Sector intelligence', '板块情报') }}</p>
      <h2 id="sector-federation-title">{{ t('What is happening inside Technology', '科技板块内部正在发生什么') }}</h2>
      <p class="sd-baseline">
        {{ t(
          'ETF timing and cycle context are available below. The deeper leadership, participation, theme and evidence read is loading.',
          '下方已有 ETF 择时与周期背景。内部领涨、参与度、主题与证据研判正在加载。'
        ) }}
      </p>
    </div>
    <span class="sd-state">{{ t('Loading governed read…', '正在加载治理研判…') }}</span>
  </div>
  <div class="sd-app" data-state="loading"></div>
  <noscript>
    <p>{{ t('Detailed read unavailable without JavaScript. The existing sector analysis below remains available.', '未启用 JavaScript，详细研判暂不可用；下方现有板块分析仍可使用。') }}</p>
  </noscript>
</section>
{% endif %}
```

The block is shown only when the builder sets `s.sector_dossier.enabled=true`, which occurs only for `s.fund == "XLK"` in STSI-1. Other sector pages remain byte-semantically unchanged except shared static assets if required.

### Step 4: Implement governed hydration

`sector_dossier.js` must:

1. Locate `[data-contract="sector_dossier_read_model.v1"]`.
2. Fetch only its declared relative URL with `cache: "no-store"`.
3. Verify the minimum browser-side envelope:
   - contract id/version;
   - `identity.native_id` matches mount sector;
   - authority caps are false;
   - `headline`, dimensions, children, themes, conflicts, freshness, and quality have expected types.
4. On failure, render the fixed bilingual typed fallback and leave every pre-existing sector panel untouched.
5. Never recompute scores, conflict classes, freshness, concentration, or relationships.
6. Never resort children/themes by magnitude; retain producer order.
7. Never inject a stylesheet, palette, or untrusted HTML.
8. Use text nodes / escaped string rendering for every source value.

Public rendering functions:

```javascript
function renderHeadline(doc) {}
function renderDimensionStrip(doc) {}
function renderParticipation(doc) {}
function renderChildren(doc) {}
function renderThemes(doc) {}
function renderConflicts(doc) {}
function renderEvidenceHealth(doc) {}
function renderUnavailable(root, reasonCode) {}
```

### Step 5: Implement the page information architecture

The dossier block order is fixed:

1. **Five-second read**
   - headline summary;
   - plain-word posture;
   - common as-of / quality / freshness chips.
2. **Why the reads differ**
   - active `TIMEFRAME_SPLIT`, `SCOPE_SPLIT`, freshness/coverage issues;
   - no front-facing falsifier/refutation vocabulary.
3. **Internal leadership**
   - subsector cards with entry tier, regime, reliability, member coverage, direct detail link.
4. **Breadth and concentration**
   - participation bar with numerator/denominator;
   - top-five market-cap concentration or typed unavailable.
5. **Connected themes**
   - canonical theme cards with relationship basis and direct theme-detail links.
6. **What changed / what to watch**
   - only owner-observed material changes and deterministic watch conditions.
7. **Evidence and clocks**
   - source count, oldest required source, stale/missing source disclosures, A1 display ceiling.

Glance-tier word budgets:

- headline: ≤ 34 English words / ≤ 44 Chinese characters where natural;
- posture: ≤ 18 English words;
- conflict summary: ≤ 18 English words;
- technical/internal states only in details/tooltips or evidence drawer.

### Step 6: Add explicit dark and light treatments

Use page-scoped CSS in `sector.html.j2` built from existing tokens.

Dark:

```css
html[data-theme="dark"] .sd-shell {
  background: linear-gradient(180deg,
    color-mix(in srgb,var(--panel) 92%,var(--info) 8%),
    var(--panel));
  border-color: color-mix(in srgb,var(--line) 72%,var(--info) 28%);
}
```

Light:

```css
html[data-theme="light"] .sd-shell {
  background: #fff;
  border-color: color-mix(in srgb,var(--line) 82%,#8792a8 18%);
  box-shadow: 0 10px 28px rgba(35,48,78,.08);
}
html[data-theme="light"] .sd-card {
  background: color-mix(in srgb,#fff 96%,var(--panel2) 4%);
  border-color: color-mix(in srgb,var(--line) 88%,#a5afc1 12%);
}
```

These are illustrative mechanics; the implementation designer owns final values within canonical tokens. The light result must be reviewed as a distinct research-workspace design, not merely a token-swapped dark panel.

### Step 7: Enforce mobile/accessibility behavior

At 390 px:

- single-column cards;
- no horizontal tables;
- source/evidence details collapse under `<details>`;
- conflict and child cards wrap without clipping;
- tap targets ≥ 44 px where interactive;
- heading order remains valid;
- status changes use an `aria-live="polite"` region;
- keyboard links and details controls work;
- no tooltip-only information is required to understand state.

### Step 8: Wire the existing sector builder

In `scripts/build_site.py::build_sector_pages`, add only the stable dossier URL metadata needed by the template:

```python
s["sector_dossier"] = {
    "enabled": fund == "XLK",
    "sector_id": "xlk" if fund == "XLK" else None,
    "contract": "sector_dossier_read_model.v1" if fund == "XLK" else None,
    "url": "../sectordata/sector_dossiers/xlk.json" if fund == "XLK" else None,
}
```

Do not read and inline the dossier into every sector page. The JSON is independently bound by the focused publisher and freshness validator.

### Step 9: Run static, JS, and render tests

```bash
python -m scripts.check_template_site_sync --fix
python -m pytest \
  tests/test_sector_dossier_page.py \
  tests/test_sector_intelligence_page.py \
  tests/test_sector_central_gate.py \
  -q
node --check templates/sector_dossier.js
node --check site/sector_dossier.js
python -m scripts.check_runtime_style_injection
python -m scripts.check_design_system --mode enforce-added
```

Use actual script CLI arguments from current main if they differ; do not skip the guard because a command signature moved.

### Step 10: Register UI tests in existing CI

- Add `tests/test_sector_dossier_page.py` to `express-render-guards`.
- Add the JS pair to existing site-JS / template-site-sync guards.
- Add no new workflow.

### Step 11: Commit

```bash
git add \
  templates/sector.html.j2 \
  templates/sector_dossier.js \
  site/sector_dossier.js \
  scripts/build_site.py \
  tests/test_sector_dossier_page.py \
  .github/ci/legacy-jobs.yml
git commit -m "feat(sector-intelligence): add Technology dossier experience"
```

---

## 9. Task 6 — Make Sector Central route sectors into their dossiers

**Files:**

- Modify: `templates/sector_central.html.j2`
- Modify: `tests/test_sector_intelligence_page.py`
- Modify: `tests/test_sector_central_gate.py`
- Modify: `.github/ci/legacy-jobs.yml` only if the existing owning command does not already select both tests

### Step 1: Add failing route tests

Extend the existing Sector Intelligence page tests:

```python
def test_sector_cards_link_to_sector_dossiers_not_only_cycle_anchors(rendered_sector_central):
    html = rendered_sector_central
    assert 'href="sectors/XLK.html"' in html
    assert 'href="sector_cycles.html#xlk"' in html


def test_basket_cards_keep_existing_theme_detail_routes(rendered_sector_central):
    html = rendered_sector_central
    assert 'href="basket/ai_semiconductors.html"' in html


def test_sector_link_requires_safe_ticker_shape(template_text):
    assert "sectors/" in template_text
    assert "encodeURIComponent" in template_text or "esc(" in template_text
```

Run:

```bash
python -m pytest tests/test_sector_intelligence_page.py tests/test_sector_central_gate.py -q
```

Expected: first test fails because sector names currently lead only to the cycle page.

### Step 2: Change only the sector-card route

Inside the existing `card(s)` renderer:

```javascript
var cycHref = 'sector_cycles.html#'+esc(s.id);
var sectorHref = 'sectors/'+encodeURIComponent(String(s.ticker||'').toUpperCase())+'.html';
var nameHtml = s.kind==='basket'
  ? '<a href="basket/'+esc(String(s.id).replace(/^b-/,''))+'.html">'+esc(nm)+'</a>'
  : '<a href="'+sectorHref+'" data-sector="'+esc(s.id)+'">'+esc(nm)+'</a>';
```

Keep the current deep cycle link and add a dossier link to the footer:

```javascript
'<a href="'+sectorHref+'">'+L('open sector read →','打开板块研判 →')+'</a>' +
'<span class="sep">·</span>' +
'<a href="'+cycHref+'" data-focus="'+esc(s.id)+'">'+L('cycle study','周期研究')+'</a>'
```

Rules:

- Sector card ordering and scores remain byte-semantically unchanged.
- Basket routing remains unchanged.
- Unsupported future sector ticker values fall back to the cycle link; never build an unsafe URL.
- No card fetches the dossier from Sector Central in STSI-1. The hub routes; the detail page explains.

### Step 3: Rebuild and test

```bash
python -m scripts.build_sector_central
python -m pytest tests/test_sector_intelligence_page.py tests/test_sector_central_gate.py -q
python -m scripts.check_template_site_sync --fix
```

Verify rendered `site/sector_central.html` contains both `sectors/XLK.html` and `sector_cycles.html#xlk`.

### Step 4: Commit

```bash
git add \
  templates/sector_central.html.j2 \
  tests/test_sector_intelligence_page.py \
  tests/test_sector_central_gate.py \
  site/sector_central.html
git commit -m "feat(sector-intelligence): route sectors to dossier detail"
```

Do not commit generated HTML until the repository's current source/generated-byte policy confirms it is tracked for this builder; if the focused publisher is the sole generated owner after #7211, let that lane generate it and omit manual generated bytes from the source commit.

---

## 10. Task 7 — Prove the real product journey in a browser

**Files:**

- Create: `tests/test_sector_dossier_browser.py`
- Create after execution: `research/sector_theme_subtheme_intelligence/evidence/STSI1_${UTC_DATE}/receipt.json`
- Create after execution: browser screenshots under the same evidence directory
- Modify: `.github/ci/legacy-jobs.yml` only if a current browser/UI-evidence owner exists and needs the new test selected

### Step 1: Write browser behavior tests before implementation acceptance

The browser test serves a controlled built site and intercepts only the dossier JSON when testing degraded states. It never labels fixture bytes as current market data.

Minimum cases:

```python
def test_real_built_xlk_dossier_happy_path(page, built_site):
    page.goto(f"{built_site}/sectors/XLK.html")
    expect(page.locator("#sector-federation")).to_be_visible()
    expect(page.locator("#sector-federation")).to_contain_text("Technology")
    expect(page.locator("#sector-federation")).to_contain_text("Semiconductors")
    expect(page.locator("#sector-federation")).to_contain_text("AI Semiconductors")


def test_missing_dossier_preserves_existing_sector_page(page, built_site):
    page.route("**/sectordata/sector_dossiers/xlk.json", lambda route: route.fulfill(status=404, body=""))
    page.goto(f"{built_site}/sectors/XLK.html")
    expect(page.locator("#sector-federation")).to_contain_text("Detailed read unavailable")
    expect(page.get_by_text("Entry setup")).to_be_visible()
    expect(page.get_by_text("Top 10 holdings")).to_be_visible()


def test_stale_or_degraded_dossier_discloses_quality_without_hiding_content(page, built_site, stale_fixture):
    ...


def test_mobile_has_no_horizontal_overflow(page, built_site):
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{built_site}/sectors/XLK.html")
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")


def test_sector_central_to_xlk_to_semiconductors_to_theme_journey(page, built_site):
    page.goto(f"{built_site}/sector_central.html")
    page.locator('a[href="sectors/XLK.html"]').first.click()
    expect(page).to_have_url(re.compile(r"/sectors/XLK\.html$"))
    page.locator('a[href="../subsector/semiconductors.html"]').click()
    expect(page).to_have_url(re.compile(r"/subsector/semiconductors\.html$"))
    page.go_back()
    page.locator('a[href="../basket/ai_semiconductors.html"]').click()
    expect(page).to_have_url(re.compile(r"/basket/ai_semiconductors\.html$"))
```

Use actual existing child slugs/hrefs from the produced dossier. A changed accepted owner route updates the test and producer together; do not preserve a stale guessed route.

### Step 2: Build a real current-source candidate

In a full checkout at the exact implementation head:

```bash
python -m scripts.build_sector_intelligence
```

The incumbent focused build already renders `site/sectors/*` through `build_sector_action_board` → `build_site.build_sector_pages`; do not run the full all-site builder for this proof.

Use the actual accepted focused-render CLI after fresh inspection. The required result is that the dossier is generated from current repository owner artifacts and the page is rendered through the real builder, not a hand-authored fixture.

Record:

- exact git head/tree;
- source artifact hashes and as-of dates;
- dossier id/hash;
- nested packet/run/manifest ids;
- generated page hash;
- required/optional source states;
- browser base URL;
- console/page errors.

### Step 3: Execute the visual evidence matrix

Capture and review:

| Theme | Language | Width | Required state |
|---|---|---:|---|
| dark | EN | 1440 | real current dossier |
| dark | ZH | 1440 | real current dossier |
| light | EN | 1440 | real current dossier |
| light | ZH | 1440 | real current dossier |
| dark | EN | 390 | real current dossier |
| dark | ZH | 390 | real current dossier |
| light | EN | 390 | real current dossier |
| light | ZH | 390 | real current dossier |

Additionally prove controlled degraded states:

- dossier 404/unavailable;
- dossier stale/degraded;
- optional leadership unavailable;
- optional entry context unavailable;
- required-source hash mismatch is rejected before publication, not rendered.

Every screenshot is labelled `real_current_source` or `controlled_degraded_fixture` in `receipt.json`.

### Step 4: Run product and browser proof

```bash
python -m pytest \
  tests/test_sector_dossier_browser.py \
  tests/test_sector_dossier_page.py \
  tests/test_sector_intelligence_page.py \
  -q
git fetch origin
git diff origin/main...HEAD > /tmp/stsi1-ui.diff
python -m scripts.check_ui_visual_evidence --diff-file /tmp/stsi1-ui.diff --repo-root .
```

Use the current accepted visual-evidence CLI. Browser cleanup warnings or skipped states are not silently counted as proof.

### Step 5: Review against the motivating user job

An independent reviewer must answer, from the exact screenshots and source contract:

1. Can a user explain why Technology, Semiconductors, and AI Semiconductors can show different states without treating one as a bug?
2. Is narrow leadership visibly different from broad sector confirmation?
3. Is fresh entry visibly different from an extended regime?
4. Can the user reach the sector, child subsector, canonical theme, and stock pages without dead ends?
5. Are freshness, coverage, and missing optional evidence honest but not overwhelming?
6. Do dark and light both look intentionally designed?
7. Does any page copy imply ranking, alpha, or trade authority not present in the contracts?

A review that only checks HTML correctness is insufficient.

### Step 6: Commit evidence after exact-head review

```bash
UTC_DATE="$(date -u +%F)"
git add \
  tests/test_sector_dossier_browser.py \
  "research/sector_theme_subtheme_intelligence/evidence/STSI1_${UTC_DATE}" \
  .github/ci/legacy-jobs.yml
git commit -m "test(sector-intelligence): prove Technology dossier journey"
```

---

## 11. Task 8 — Complete integration proof and publish through the incumbent lane

### Step 1: Run the exact affected suite

```bash
python -m pytest \
  tests/test_sector_dossier_contract.py \
  tests/test_sector_federation.py \
  tests/test_build_sector_dossiers.py \
  tests/test_sector_intelligence_page.py \
  tests/test_nightly_liveness.py \
  tests/test_sector_dossier_page.py \
  tests/test_sector_dossier_browser.py \
  tests/test_sector_intelligence_contracts.py \
  tests/test_sector_central_gate.py \
  tests/test_subsector_confluence.py \
  tests/test_thematic_state.py \
  tests/test_synapse_registry.py \
  -q
```

Then run:

```bash
python -m scripts.check_template_site_sync
python -m scripts.check_inline_js templates site
python -m scripts.check_site_js site
python -m scripts.check_runtime_style_injection
python -m scripts.check_design_system --mode enforce-added --root .
git fetch origin
git diff origin/main...HEAD > /tmp/stsi1-ui.diff
python -m scripts.check_ui_visual_evidence --diff-file /tmp/stsi1-ui.diff --repo-root .
git diff --check
```

Resolve actual command signatures from current main. Missing tools are named blockers; they are not silently omitted.

### Step 2: Prove invariants against before/after owner outputs

Capture signatures before and after STSI-1 using the same real inputs:

```python
INVARIANT_FIELDS = {
    "sector_central": [
        "sectors[].id",
        "sectors[].conviction",
        "sectors[].rotation",
        "sectors[].cycle",
        "sectors[].split_view",
    ],
    "subsector_confluence": [
        "subsectors[].key",
        "subsectors[].class",
        "subsectors[].entry",
        "subsectors[].regime",
        "double_gated",
    ],
    "theme_state": [
        "themes[].theme_id",
        "themes[].foresight",
        "themes[].basket_intel",
        "themes[].subsector_rotation",
    ],
}
```

Assert exact equality. Only new dossier output, page composition, and route links may differ.

Also assert:

- Board V2 candidates/order unchanged.
- Prophet artifacts unchanged.
- sector-central call ledger unchanged except incumbent build behavior already owned by its producer.
- no new scheduler, queue, store, graph, event ledger, or publication workflow.

### Step 3: Create the implementation PR as Draft/HOLD first

The PR body must include:

- exact architecture/plan refs;
- accepted dependency heads;
- exact base/head/tree;
- changed paths and owner collision proof;
- capability delta;
- real current-source Technology receipt;
- contract and authority proof;
- invariant proof;
- affected tests and CI job ownership;
- browser matrix and independent review;
- publication/deployment gates;
- explicit no-merge condition until exact-head CI/review/dependency gates clear.

Do not add `merge-on-green` while a source-owner hold or dependency hold remains.

### Step 4: Obtain exact-head independent review

Required review focuses:

1. Identity: `sector:xlk` / `xlk` / `XLK` are not conflated.
2. Governance: packet/lobe/manifest bindings and A1 ceiling are real, not decorative.
3. Conflict altitude: timeframe/scope differences are not mislabeled contradictions.
4. Data integrity: null, stale, partial, missing, and future dates behave correctly.
5. Ownership: no #7211/#7526/#7455/#7508/#7252/#7283 work is copied or bypassed.
6. Product: the page answers what changed, why, breadth, concentration, child leadership, themes, and what to watch.
7. No policy effect: ranking, admission, sizing, Prophet, portfolio, and trade outputs are invariant.

Any blocker/major finding returns to the same carrier for repair and rereview.

### Step 5: Merge source only after gates clear

Required before source merge:

- hard prerequisites merged/accepted;
- exact-head focused and hosted CI green, excluding only explicitly accepted spurious infrastructure contexts;
- independent semantic/product review pass;
- current-main collision recheck clean;
- no HOLD remains;
- generated/site bytes follow the accepted publisher policy.

Merge is `BUILT_NOT_PROVEN`, not production acceptance.

### Step 6: Dispatch the incumbent focused publication

After merge:

```bash
gh workflow run sector-intelligence.yml --ref main
```

Before dispatch, verify no same workflow run is queued/in progress. Never cancel a live production lane merely to accelerate this program.

The run must:

1. build baskets/action board/Sector Central/dossier in accepted order;
2. pass the freshness validator;
3. publish one scoped main commit through the incumbent retry/rebase contract;
4. stage dossier JSON and paired JS/page bytes;
5. conclude successfully.

A queued or started run is not publication proof.

### Step 7: Complete deployed browser proof

From cache-busted deployed origin bytes, verify:

```text
/sector_central.html
/sectors/XLK.html
/sectordata/sector_dossiers/xlk.json
/subsector/semiconductors.html
/basket/ai_semiconductors.html
```

Acceptance requires:

- deployed JSON dossier id/hash match published main bytes;
- page fetches the same contract and common as-of;
- no stale fallback or mixed generation;
- route journey works in a real browser;
- dark/light, EN/ZH, 1440/390 render correctly;
- no page/console/request errors;
- existing cycle, entry, chart, holdings, calibration and alerts remain usable;
- Sector Central card links to the dossier and retains cycle study access.

### Step 8: Require one natural follow-on generation

The next natural focused Sector Intelligence run must advance or truthfully retain the semantic horizon without manual repair. Verify:

- dossier ids/hashes change only when source/generation facts change;
- source byte hashes match the new generation;
- corrected same-date owner inputs replace, not double-count, evidence;
- expired manifest is replaced with the new generation's manifest;
- missing optional sources remain typed unavailable, not zero;
- no duplicate publication commit or retry loop.

Only then may STSI-1 be classified `PROVEN_LIVE`.

---

## 12. Failure handling and rollback

### Build failures

- Missing/malformed required owner artifact: fail the focused generation before overwriting the prior dossier.
- Missing optional artifact: publish with typed unavailable dimension and quality warning.
- Invalid packet/lobe/manifest/dossier: fail closed before atomic write.
- Source hash mismatch after read: fail; do not publish split bytes.
- Required source date ahead of common as-of: fail.
- Older valid deployed generation when a new build fails: retain old bytes, show their real clocks; never restamp them as fresh.

### Browser failures

- JSON 404/network/parse/envelope failure: fixed bilingual unavailable state; preserve all existing sector content.
- Expired/degraded dossier: render content with prominent freshness warning; do not silently hide it or claim current state.
- Unknown dimension/conflict enum: render that item unavailable and log one bounded console warning; do not reinterpret it client-side.

### Rollback

Rollback is one source revert plus disabling the dossier call in the existing focused lane. The previous sector pages and Sector Central remain intact because:

- no canonical owner store is migrated;
- no existing payload is repurposed;
- the dossier is additive;
- the page hydration fails soft;
- sector card cycle links remain available;
- no user state is stored in the dossier.

Do not delete history/evidence or create compensation data. Revert only the additive source and publication wiring.

---

## 13. Commit sequence

The implementation should land as reviewable, dependency-ordered commits:

1. `feat(sector-intelligence): add governed dossier contract`
2. `feat(sector-intelligence): compose Technology federation dossier`
3. `feat(sector-intelligence): publish atomic Technology dossier`
4. `feat(sector-intelligence): bind dossier to focused publication`
5. `feat(sector-intelligence): add Technology dossier experience`
6. `feat(sector-intelligence): route sectors to dossier detail`
7. `test(sector-intelligence): prove Technology dossier journey`
8. `docs(sector-intelligence): record STSI-1 exact-head acceptance`

Do not squash locally; GitHub ordinary squash merge remains the repository release mechanism after all gates clear.

---

## 14. Acceptance checklist

### Truth and identity

- [ ] Existing `sector:xlk`, `xlk`, and `XLK` identities are preserved distinctly.
- [ ] Every dimension has an owner, scope, horizon, clock, source ref, coverage state, and authority ceiling.
- [ ] Primary/supplemental theme-basket semantics are not reversed.
- [ ] Exact crosswalk relationships only; no fuzzy mapping.
- [ ] Missing, stale, partial, zero, false, and non-PIT states remain distinct.

### Intelligence

- [ ] Slow/fast difference is `TIMEFRAME_SPLIT`, not contradiction.
- [ ] Fresh semiconductor entry versus extended regime is explained.
- [ ] Narrow Technology breadth versus strong child is `SCOPE_SPLIT`.
- [ ] Participation and structural concentration are both shown and not conflated.
- [ ] Optional closed-session leadership and entry context fail closed.
- [ ] No universal/fused intelligence score is introduced.

### Product

- [ ] Sector Central → Technology dossier → Semiconductors/theme/stock journey works.
- [ ] Five-second viewport answers state, why, posture, freshness, and breadth.
- [ ] Existing sector timing/cycle/holdings content remains available.
- [ ] Dark and light are separately designed.
- [ ] EN/ZH and 1440/390 states pass.
- [ ] Typed degraded states pass.
- [ ] No horizontal mobile overflow or inaccessible hidden-only evidence.

### Authority and invariance

- [ ] Packet/lobe/manifest/dossier bindings validate.
- [ ] A1 observe/explain ceiling is explicit.
- [ ] Sector Central scores/order unchanged.
- [ ] Subsector gate/funnel unchanged.
- [ ] ThemeState lanes/content unchanged.
- [ ] Board V2 and Prophet outputs unchanged.
- [ ] No rank/gate/size/escalate/trade authority is added.

### Publication and proof

- [ ] #7211 owner path is reused; no new workflow/publisher.
- [ ] Exact-head CI and independent review pass.
- [ ] Focused publication concludes and deploys matching bytes.
- [ ] Deployed browser matrix passes.
- [ ] Natural follow-on generation passes.
- [ ] Agent OS/PR closeout records exact source, proof, unresolveds, and next STSI boundary.

---

## 15. Plan self-review and implementation review focus

### Requirements-to-task trace

| Requirement | Owning task |
|---|---|
| strict shared dossier/governance contract | Task 1 |
| owner-preserving composition and conflict explanation | Task 2 |
| deterministic atomic producer | Task 3 |
| one coherent focused publication | Task 4 |
| sector-detail product journey | Task 5 |
| Sector Central drill-down | Task 6 |
| real browser and design proof | Task 7 |
| merge/deploy/natural acceptance | Task 8 |

### Self-review result

- No unresolved marker, provisional path, or unnamed authority remains.
- Scope is one Technology vertical; other sectors, theme-detail integration, and subtheme pages remain later STSI waves.
- Contract types and JSON examples agree: missing values are `null`, unavailable state is explicit, and zero remains a valid measured value.
- Hard dependencies are explicit; optional inputs do not create circular merge waits.
- The plan reuses existing packet, lobe, manifest, publisher, page, graph, ThemeState, evaluation and CI owners.
- The plan contains one real producer, one real page consumer, hub routing, discriminating tests, production proof, and natural follow-on proof.
- No generated artifact or fixture is represented as production truth.

### Highest-risk review areas

1. **Governance binding:** nested packet/lobe/manifest hashes and references must be substantive, not decorative metadata.
2. **Conflict altitude:** different scopes/horizons must not become `GENUINE_CONTRADICTION`.
3. **Publisher integration:** #7211's accepted transaction and compensation behavior must remain sole owner.
4. **Identity:** `sector:xlk`, `xlk`, `XLK`, `Semiconductors`, and canonical themes cannot be joined by label guessing.
5. **Client boundary:** JavaScript renders only; it never classifies, scores, or restamps freshness.
6. **Product clarity:** the user must understand selective leadership without receiving an implied buy call.
7. **Light art direction:** functional token swapping is not acceptance.
8. **Policy invariance:** no upstream or downstream rank/admission/trade bytes move.

---

## 16. Exact continuation after plan approval

After Chairman approval:

1. Re-pin current protected Skillpack and fresh Macro main.
2. Verify #7211 and #7526 acceptance/merge state and reconcile their exact interfaces.
3. Run a fresh collision census over the STSI-1 paths.
4. Create a fresh implementation worktree/branch from `origin/main`.
5. Execute Task 1 first with TDD.
6. Continue task-by-task on the same implementation carrier, reviewing each commit against the invariant and authority gates.

Source implementation must not begin by editing PR #7577's architecture branch. PR #7577 remains the architecture/plan review carrier; the implementation receives a new operation identity and carrier after approval.
