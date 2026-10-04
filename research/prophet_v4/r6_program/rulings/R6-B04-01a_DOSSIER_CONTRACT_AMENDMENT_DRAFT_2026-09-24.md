# R6-B04-01a — episode evidence dossier contract amendment A7–A12

SOURCE_SHA: `2c7436bea5d1fca9d2ad1778eed1a6b55fa9e8ea`

Authority: DEC:PROPHET-US-FABLE-META-CEO-DELEGATION — seat 48cdfd56 ratifies or repairs this draft as R6-B04-01a; DRAFT until then.

Operation: `prophet-us-fable-meta-ceo-20260923-001` (Macro #6805). This draft consumes the independent read-only review of R6-B04-01 (`APPROVE WITH REQUIRED REPAIRS`; `B04-A MAY START: NO`; 2 BLOCKER / 7 MAJOR / 4 minor) and amends the adopted B04 contract. Governing records remain `R6-B04-01_DOSSIER_CONTRACT_2026-09-24.md`, `wave2/B04_EVIDENCE_DOSSIER_CONTRACT_CENSUS_2026-09-23.md`, DEC:PROPHET-US-B04-EVIDENCE-DOSSIER-CONTRACT, `research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md`, and the B04 card in `effective/BUILD_PROGRAM.md`.

## A7 — publication and capture are different absence reasons

The wrapper applies the A7 split from the clocks already carried by the vector; the vector's internal reason ID and serialized identity are unchanged. The original vector applies its three-clock conjunction to `source_available_at`, `observed_at`, and `generated_at` (`engine/prophet_lab/intelligence_vector.py:1223-1227`). When no source-captured body survives that conjunction, its current late branch asks whether **any** parsed clock is after the cut (`engine/prophet_lab/intelligence_vector.py:1230`) and therefore uses `NOT_CAPTURED_AT_DECISION` even when the source itself was released after the decision (`engine/prophet_lab/intelligence_vector.py:1238-1240`).

The wrapper must split on `source_available_at ≤ cut`:

- If `source_available_at ≤ cut` and a source-capture or generated clock is after the cut, the lane is `NOT_CAPTURED_AT_DECISION`. This is exactly D07 step 1: public before the decision, captured afterward. Sentence EN: “This information was published before the decision, but we did not capture it until later.” Sentence ZH: “这条信息在决策前已经发布，但我们直到稍后才取得它。”
- If `source_available_at > cut`, the lane is `NOT_PUBLISHED_AT_DECISION`. Sentence EN: “This information was not yet public at the decision time.” Sentence ZH: “这条信息在决策时还没有公开。”

The wrapper derives the split from the clocks carried by the vector/revision receipt. It does not mutate `absence_reasons`, `point_in_time`, or any content-addressed vector field. `source_available_at` is itself retained exactly as carried by the vector; the decision is only a read. If `source_available_at` is missing or unparseable, A7 does not guess: the lane uses the A9 `missing_decision_clock` mapping.

## A8 — one gated projection and wrapper identity

Each view is referenced by `views.<name>.vector_projection_id` and rendered through one stated GATED PROJECTION. It is a wrapper-level function with this required order: rights gate, prohibited-field removal or redaction, content addressing of the projected view, wrapper assembly, then `dossier_id` content addressing over the finished gated wrapper. It must drop or redact every prohibited field before the projected `vector_projection_id` is computed, so no forbidden value, hash, document id, field path, source reference, evidence root, or prose can be recovered or retained as an oracle in a blocked lane. The wrapper emits `view_decision_admissible: false`; no projected current view carries a decision-admission answer from its inner vector.

The projection may touch only these vector fields, and only when a rights decision requires removal or redaction:

- Top level: `projection_id`, only to recompute identity after gated families change.
- An `evidence_families[]` member: `family_projection_id`, `source_refs`, `evidence_roots`, `explanation_facts`, and gated `observations`; within each gated observation, `observation_id`, `value`, and every value subobject containing a protected value, source/root identifier, field path, or protected prose.
- Recomputed content-addressed parent/child IDs that necessarily follow the listed gated fields.

The inner vector is otherwise unchanged. `authority` remains exactly the six all-false booleans, and no authority value may be recomputed (`engine/prophet_lab/intelligence_vector.py:44-51`). For the `current` view, the projection never emits inner `point_in_time.decision_admissibility`; the wrapper emits `view_decision_admissible: false` and `view_basis: RESEARCH_KNOWN_NOW`. The term `decision_admissibility` is not used as the wrapper key because the current vector can carry the string state `ADMISSIBLE` at a later cut (`engine/prophet_lab/intelligence_vector.py:1415-1417`), which is not the boolean contract required by R6-B04-01 A3. The `decision` view's inner vector remains byte-identical after gating: a lane that passes all rights checks is projected without mutation.

The existing embedded family right is static (`engine/prophet_lab/intelligence_vector.py:452-492`) and its validator accepts only `ALLOWED` (`engine/prophet_lab/intelligence_vector.py:1864-1871`), so rights can differ from that static value only at the wrapper. `evidence_class` belongs at the wrapper level only: it is not added to the vector and is not part of projection identity. The wrapper carries `dossier_id`, a content address computed after all view gating, wrapper-level rights decisions, reason resolution, and message assembly. Canonical JSON encoding and the hash algorithm are fixed by B04-A tests and are stable thereafter.

## A9 — closed outcome-to-code mapping

The dossier reason map is keyed by `(coverage basis, reason ID, lane)`. Reason IDs are the vector/owner reason IDs and their coverage bases, not display codes. Every listed reason ID appears in the table: `current_event_not_published`, `source_fetch_failed`, `correction_chain_integrity`, `missing_decision_clock`, `STALE`, `UNESTIMABLE`, `CORRECTION_PENDING`, `NOT_APPLICABLE`, `not_available`, `consensus_unlicensed`, `no_span_addressable_evidence`, `missing_source`, `no_transcript`, and `unknown`, plus the identity, clock-tie, capture, lineage, and wrapper reasons. Every key resolves to exactly one display code or `CORRECTED_LATER` annotation. `UNKNOWN` is reachable only for a reason ID absent from the table; because correction-integrity and not-applicable reasons are inventoried but deliberately resolve to `UNKNOWN`, the build-time coverage test may not treat `UNKNOWN` itself as failure. It instead fails on any unmapped key. At build time the table is committed as `config/prophet_dossier_reason_map.v1.json`.

The compound `WorkspaceChainIntegrityError` result carries `UNESTIMABLE` and `CORRECTION_PENDING` with coverage basis `current_manifest_integrity_failure` (`engine/prophet_lab/intelligence_vector.py:1096-1117`) or `correction_chain_integrity` (`engine/prophet_lab/intelligence_vector.py:1140-1166`). Because the closed eleven-code vocabulary has no correction-integrity code, both members map together to `UNKNOWN`; that is the sole unavoidable use of `UNKNOWN` for an inventoried reason. A present original value corrected later instead receives `annotations: ["CORRECTED_LATER"]` and is never reported as missing.

`source_fetch_failed` maps to `SOURCE_TEMPORARILY_UNAVAILABLE`, sentence EN: “We could not reach this source when the dossier was built; it will be retried.” sentence ZH: “我们在构建档案时无法访问这个来源；之后会重试。” It covers the read failures that currently produce `SOURCE_UNAVAILABLE` (`engine/prophet_lab/intelligence_vector.py:1118-1128`, `:1167-1177`) and is not evidence that the source is permanently unavailable.

`no_current_generation_event` means the current event-generation row does not publish the event (`engine/prophet_lab/intelligence_vector.py:1118-1136`). It is not proof that no event existed historically and does not by itself satisfy A11's `HISTORICAL_EVENT_SET_UNAVAILABLE`; the map resolves it to `HISTORICAL_EVENT_SET_UNAVAILABLE` for a historical cut, where no source-dated event-set row can establish the cut population. The vector vocabulary also permits `STALE` and `NOT_APPLICABLE` (`engine/prophet_lab/intelligence_vector.py:1543-1549`); those mintable reasons and all owner delta reasons in `engine/prophet_lab/intelligence_vector.py:128-131` are included below. `STALE` is mintable but has no present code occurrence in this adapter and therefore maps to `UNKNOWN`; `NOT_APPLICABLE` likewise maps to `UNKNOWN`, whose sentence is truthful because the lane is not shown as a supported product fact.

`CONFLICTED` is ambiguous in the inner vector. Identity ambiguity is minted at `engine/prophet_lab/intelligence_vector.py:1076-1085`; ordering ties separately mint `CONFLICTED` at `engine/prophet_lab/intelligence_vector.py:1258-1267`. The wrapper resolves ambiguity by coverage basis: identity bases map to `IDENTITY_BINDING_CONFLICT`; `unresolved_clock_tie` maps to `CONFLICTING_SOURCE_CLOCKS`. The reason map separately adds `CONFLICTING_SOURCE_SPANS` for two otherwise admissible source bodies that disagree about the period they cover. Sentence EN: “Two copies of this source disagree about which period they cover, so we do not show either.” Sentence ZH: “这个来源的两份内容对所覆盖的时间段不一致，因此我们不展示其中任何一份。” `CONFLICTING_SOURCE_CLOCKS` remains ordering-tie only. `EXACT_LINEAGE_UNAVAILABLE` remains sparse-source only (`engine/prophet_lab/intelligence_vector.py:1408-1414`).

## A10 — one precedence, one code per lane

When more than one mapped condition is present, the wrapper selects the first present display code in this total order:

1. `IDENTITY_BINDING_CONFLICT`
2. `RIGHTS_NOT_A_SOURCE`
3. `RIGHTS_INTERNAL_ONLY`
4. `SOURCE_TEMPORARILY_UNAVAILABLE`
5. `CONFLICTING_SOURCE_SPANS`
6. `CONFLICTING_SOURCE_CLOCKS`
7. `NOT_PUBLISHED_AT_DECISION`
8. `NOT_CAPTURED_AT_DECISION`
9. `HISTORICAL_EVENT_SET_UNAVAILABLE`
10. `EXACT_LINEAGE_UNAVAILABLE`
11. `UNKNOWN`

`CORRECTED_LATER` is not an absence code and never participates in precedence. When an original value is present and a later source generation is visible, the lane carries `annotations: ["CORRECTED_LATER"]` and remains present.

The rights posture axis for absence precedence is the register's `user_redistribution` dimension. A transcript lane that is internal-only for processing and not-a-source for redistribution therefore resolves to `RIGHTS_NOT_A_SOURCE` on every user-facing lane; the compound posture is preserved in the A11 lane-family map. The per-dimension map is not flattened into one family posture.

## A11 — route, exception typing, fixture matrix, and A1 posture map

### Route and typed identity conflict

B04-A adds `GET /api/prophet/lab/v1/episodes/{episode_id}/dossier`. The existing `GET /api/prophet/lab/v1/episodes/{episode_id}/intelligence` remains untouched (`app/prophet_lab.py:254-322`). No consumer contract changes until B04-C.

B04-A adds the exception class `IdentityBindingConflict(IntelligenceVectorContractError)` and raises `IdentityBindingConflict` from `_validate_owner_workspace_binding` for disagreement among the requested event, owner event, workspace issuer, and resolved earnings identity (`engine/prophet_lab/intelligence_vector.py:308-338`). The dossier route catches it and returns HTTP 200 with a complete dossier whose relevant lane has `IDENTITY_BINDING_CONFLICT`; the existing intelligence route continues its blind-safe 503 behavior (`app/prophet_lab.py:307-322`). It is the only identity failure converted to a dossier response; other contract failures remain fail-closed and do not expose exception text.

The route handler catches `IntelligenceVectorContractError`, then branches on `isinstance(exc, IdentityBindingConflict)`. That typed branch supplies the dossier response; every other `IntelligenceVectorContractError` takes the generic fail-closed branch. No exception class is inferred from a message.

`IdentityBindingConflict` replaces the three generic binding errors that establish a mismatch among resolved CIK, requested event, workspace event, or workspace issuer at `engine/prophet_lab/intelligence_vector.py:320-338`. Schema-shape, receipt, generation, clock, and source-hash failures keep the generic contract error and the fail-closed route branch.

### Historical event set and pre-inception

`HISTORICAL_EVENT_SET_UNAVAILABLE` is raised if and only if no source-dated point-in-time row exists for the requested event set at the cut. “Pre-inception” means such a row exists and its source date is after the cut: the event set was a later creation, not an unavailable historical population. “Unavailable” means there is no source-dated row from which the cut population can be reconstructed. This follows R6-D03-01 rule 1: history is admissible only where a source-dated point-in-time row exists, and absence of such a row is not evidence that the event was absent then.

### Fixture and test surface

Fixtures live under `tests/fixtures/prophet_lab_dossier/`. B04-A's contract test file is `tests/test_prophet_lab_dossier_b04a.py`. The committed matrix has one fixture for every display code, including `NOT_PUBLISHED_AT_DECISION`, `SOURCE_TEMPORARILY_UNAVAILABLE`, and `CONFLICTING_SOURCE_SPANS`, and one fixture for every rights posture, including `NOT_A_SOURCE` and `ABSENT`. The rights-gate tests run on serialized route JSON after gating and before content addressing.

### Lane-to-family posture map

B04-B commits `config/prophet_dossier_lane_families.v1.json`, fenced verbatim below. `lane` is the dossier evidence lane and `register_family` is the register family key. The `postures` object preserves every register compound posture by dimension: `user_redistribution`, `model_use`, `storage`, and `context` (processing/acquisition context). B04-A uses the map to establish expected families and lane joins; B04-B applies it at the route boundary before render. No register row is edited by this draft.

The build-time map test requires all 14 register family keys exactly once. An `ABSENT` family posture remains typed as `RIGHTS_INTERNAL_ONLY` until the register records a determination; no `RIGHTS_ABSENT` display code is created. The rationale is fail-closed: absence of a determination is not user-facing permission. For the dossier's user-facing precedence, the `user_redistribution` dimension selects `RIGHTS_NOT_A_SOURCE` or `RIGHTS_INTERNAL_ONLY`; other dimensions can block processing or storage and are preserved in the map for their owners.

## A12 — closed wrapper shape

The wrapper's closed enums are:

- `views.original.state` and `views.current.state`: `{PRESENT, ABSENT, GATED}`.
- `missingness[].state`: `{NONE, PARTIAL, FULL}`.
- `rights[].state`: `{ALLOWED, INTERNAL_ONLY, NOT_A_SOURCE, ABSENT}`.
- `evidence_class.state`: `{NOT_ASSERTED, ASSERTED}`.
- `messages[].code`: the eleven A10 absence codes plus the annotation-only value `CORRECTED_LATER`.

`messages` is a per-lane list of objects with exactly `{lane, code, en, zh}`. The route selects the sentence to show from `Accept-Language`, with `?lang=` taking precedence when present. Both EN and ZH sentences remain in every JSON payload. Machine codes are not shown as user-facing text.

Each `missingness` object carries `{view, lane, state, code}`; `view` is `original` or `current`. A lane absent in one view may be present in the other without changing the enum. `missingness[].code` is `null` for `NONE`, one A10 display code for `PARTIAL` or `FULL`, or the annotation-only `CORRECTED_LATER` when the original value is present and the missingness row marks a later current correction rather than absence.

The wrapper carries `authority` equal to `ALL_FALSE_AUTHORITY` and reuses `_FORBIDDEN_KEYS`; the exact authority keys are `can_rank`, `can_gate`, `can_size`, `can_originate_signal`, `can_change_entry_open`, and `can_change_execution` (`engine/prophet_lab/intelligence_vector.py:44-51`). The wrapper also carries `evidence_class`, `views`, `rights`, `missingness`, `messages`, and A8's `dossier_id`. No score, confidence number, narrative, commercial term, or true authority boolean is added.

## FINDING → AMENDMENT

| Finding | A-number | Disposition |
|---|---|---|
| B1 | A7 | Split released-after-cut from published-before/late-captured with two plain bilingual sentences. |
| B2 | A8 | Gate before content addressing, rename current-view admissibility, keep evidence class and dossier identity at the wrapper. |
| M1 | A9 | Add a closed `(coverage basis, reason ID, lane)` map covering `current_event_not_published`, `source_fetch_failed`, `correction_chain_integrity`, `missing_decision_clock`, and every other inventoried reason, including temporary source unavailability. |
| M2 | A9 | Add conflicting-span wording and reserve clock conflict for ordering ties. |
| M3 | A10 | Apply one total precedence and convert later correction to a present-lane annotation. |
| M4 | A11 | Fix the new route, typed identity conflict, historical-set definition, fixture matrix, tests, and lane-family postures. |
| M5 | A12 | Close view, missingness, rights, and evidence-class enums; pin message shape, language behavior, authority, and wrapper identity. |
| M6 | A8/A11 | Gate before content addressing; require posture fixtures and a 14-family compound lane map. |
| M7 | build order | Close B04 at JSON detail and route renderer; move the user-readable visual matrix to B20/B07. |
| m1 | build order | Narrow D07's B04 block to B04-D; the seat must ratify that narrowing because this lane does not edit the register. |
| m2 | A12 | Name all six exact all-false authority keys. |
| m3 | A7/A9/A12 | Use plain sentences and never expose internal state names to users. |
| m4 | build order | Require the B04-B rights gate before any user-facing transcript render and close the census:94 static-ALLOWED defect. |

## CLOSED TABLES

Reason map (verbatim future `config/prophet_dossier_reason_map.v1.json`; a `null` lane matches every lane, while an explicit lane is more specific):

```json
{
  "schema": "prophet.dossier_reason_map/v1",
  "display_codes": [
    "IDENTITY_BINDING_CONFLICT",
    "RIGHTS_NOT_A_SOURCE",
    "RIGHTS_INTERNAL_ONLY",
    "SOURCE_TEMPORARILY_UNAVAILABLE",
    "CONFLICTING_SOURCE_SPANS",
    "CONFLICTING_SOURCE_CLOCKS",
    "NOT_PUBLISHED_AT_DECISION",
    "NOT_CAPTURED_AT_DECISION",
    "HISTORICAL_EVENT_SET_UNAVAILABLE",
    "EXACT_LINEAGE_UNAVAILABLE",
    "UNKNOWN"
  ],
  "annotation_codes": [
    "CORRECTED_LATER"
  ],
  "sentences": {
    "IDENTITY_BINDING_CONFLICT": {
      "en": "The evidence does not all point to the same company.",
      "zh": "这些证据并非全部指向同一家公司。"
    },
    "RIGHTS_NOT_A_SOURCE": {
      "en": "This source cannot be used for this product fact.",
      "zh": "这个来源不能用于这项产品事实。"
    },
    "RIGHTS_INTERNAL_ONLY": {
      "en": "We can use this source internally, but cannot show this fact.",
      "zh": "这个来源只能内部使用，不能向你展示这条事实。"
    },
    "SOURCE_TEMPORARILY_UNAVAILABLE": {
      "en": "We could not reach this source when the dossier was built; it will be retried.",
      "zh": "我们在构建档案时无法访问这个来源；之后会重试。"
    },
    "CONFLICTING_SOURCE_SPANS": {
      "en": "Two copies of this source disagree about which period they cover, so we do not show either.",
      "zh": "这个来源的两份内容对所覆盖的时间段不一致，因此我们不展示其中任何一份。"
    },
    "CONFLICTING_SOURCE_CLOCKS": {
      "en": "The source versions disagree about which version came first.",
      "zh": "来源版本对先后顺序存在冲突。"
    },
    "NOT_PUBLISHED_AT_DECISION": {
      "en": "This information was not yet public at the decision time.",
      "zh": "这条信息在决策时还没有公开。"
    },
    "NOT_CAPTURED_AT_DECISION": {
      "en": "This information was published before the decision, but we did not capture it until later.",
      "zh": "这条信息在决策前已经发布，但我们直到稍后才取得它。"
    },
    "HISTORICAL_EVENT_SET_UNAVAILABLE": {
      "en": "We cannot reconstruct the full event list that existed at that time.",
      "zh": "我们无法重建当时存在的完整事件列表。"
    },
    "EXACT_LINEAGE_UNAVAILABLE": {
      "en": "The source exists, but we cannot point to the exact field used.",
      "zh": "来源存在，但我们无法指出所用的确切字段。"
    },
    "UNKNOWN": {
      "en": "We do not yet know why this information is missing.",
      "zh": "我们仍不知道这条信息缺失的原因。"
    },
    "CORRECTED_LATER": {
      "en": "A later version changed this information after the original decision.",
      "zh": "在原始决策之后，新版本更改了这条信息。"
    }
  },
  "map": [
    {"coverage_basis": "canonical_identity_ambiguous", "reason_id": "CONFLICTED", "lane": null, "code": "IDENTITY_BINDING_CONFLICT"},
    {"coverage_basis": null, "reason_id": "canonical_identity_ambiguous", "lane": null, "code": "IDENTITY_BINDING_CONFLICT"},
    {"coverage_basis": null, "reason_id": "canonical_identity_unresolved", "lane": null, "code": "IDENTITY_BINDING_CONFLICT"},
    {"coverage_basis": null, "reason_id": "current_manifest_integrity_failure", "lane": null, "code": "UNKNOWN"},
    {"coverage_basis": "canonical_identity_unresolved", "reason_id": "IDENTITY_UNRESOLVED", "lane": null, "code": "IDENTITY_BINDING_CONFLICT"},
    {"coverage_basis": null, "reason_id": "current_event_not_published", "lane": null, "code": "HISTORICAL_EVENT_SET_UNAVAILABLE"},
    {"coverage_basis": "current_manifest_integrity_failure", "reason_id": "UNESTIMABLE", "lane": null, "code": "UNKNOWN"},
    {"coverage_basis": "current_manifest_integrity_failure", "reason_id": "CORRECTION_PENDING", "lane": null, "code": "UNKNOWN"},
    {"coverage_basis": null, "reason_id": "correction_chain_integrity", "lane": null, "code": "UNKNOWN"},
    {"coverage_basis": "correction_chain_integrity", "reason_id": "UNESTIMABLE", "lane": null, "code": "UNKNOWN"},
    {"coverage_basis": "correction_chain_integrity", "reason_id": "CORRECTION_PENDING", "lane": null, "code": "UNKNOWN"},
    {"coverage_basis": "source_fetch_failed", "reason_id": "SOURCE_UNAVAILABLE", "lane": null, "code": "SOURCE_TEMPORARILY_UNAVAILABLE"},
    {"coverage_basis": null, "reason_id": "source_fetch_failed", "lane": null, "code": "SOURCE_TEMPORARILY_UNAVAILABLE"},
    {"coverage_basis": "no_current_generation_event", "reason_id": "NOT_COVERED", "lane": null, "code": "HISTORICAL_EVENT_SET_UNAVAILABLE"},
    {"coverage_basis": "no_verified_revisions", "reason_id": "NOT_COVERED", "lane": null, "code": "HISTORICAL_EVENT_SET_UNAVAILABLE"},
    {"coverage_basis": "missing_decision_clock", "reason_id": "UNKNOWN", "lane": null, "code": "UNKNOWN"},
    {"coverage_basis": null, "reason_id": "missing_decision_clock", "lane": null, "code": "UNKNOWN"},
    {"coverage_basis": "unresolved_clock_tie", "reason_id": "CONFLICTED", "lane": null, "code": "CONFLICTING_SOURCE_CLOCKS"},
    {"coverage_basis": "conflicting_source_spans", "reason_id": "CONFLICTING_SOURCE_SPANS", "lane": null, "code": "CONFLICTING_SOURCE_SPANS"},
    {"coverage_basis": "not_evaluated", "reason_id": "UNKNOWN", "lane": null, "code": "UNKNOWN"},
    {"coverage_basis": "exact_source_lineage_unavailable", "reason_id": "UNKNOWN", "lane": null, "code": "EXACT_LINEAGE_UNAVAILABLE"},
    {"coverage_basis": "verified_revision_chain", "reason_id": "NOT_CAPTURED_AT_DECISION", "lane": null, "code": "NOT_CAPTURED_AT_DECISION"},
    {"coverage_basis": "verified_revision_chain", "reason_id": "NOT_PUBLISHED_AT_DECISION", "lane": null, "code": "NOT_PUBLISHED_AT_DECISION"},
    {"coverage_basis": null, "reason_id": "not_available", "lane": null, "code": "UNKNOWN"},
    {"coverage_basis": null, "reason_id": "consensus_unlicensed", "lane": null, "code": "RIGHTS_NOT_A_SOURCE"},
    {"coverage_basis": null, "reason_id": "no_span_addressable_evidence", "lane": null, "code": "EXACT_LINEAGE_UNAVAILABLE"},
    {"coverage_basis": null, "reason_id": "missing_source", "lane": null, "code": "SOURCE_TEMPORARILY_UNAVAILABLE"},
    {"coverage_basis": null, "reason_id": "no_transcript", "lane": null, "code": "SOURCE_TEMPORARILY_UNAVAILABLE"},
    {"coverage_basis": null, "reason_id": "not_applicable", "lane": null, "code": "UNKNOWN"},
    {"coverage_basis": null, "reason_id": "unknown", "lane": null, "code": "UNKNOWN"},
    {"coverage_basis": null, "reason_id": "STALE", "lane": null, "code": "UNKNOWN"},
    {"coverage_basis": null, "reason_id": "NOT_APPLICABLE", "lane": null, "code": "UNKNOWN"}
  ],
  "wrapper_overrides": [
    {"condition": "source_available_at > cut", "from_code": "NOT_CAPTURED_AT_DECISION", "code": "NOT_PUBLISHED_AT_DECISION"},
    {"condition": "present original value with later visible generation", "code": null, "annotation": "CORRECTED_LATER"}
  ]
}
```

Lane-to-family map (verbatim future `config/prophet_dossier_lane_families.v1.json`):

```json
{
  "schema": "prophet.dossier_lane_families/v1",
  "postures": {
    "user_redistribution": [
      "USER_FACING",
      "USER_FACING_WITH_LIMITS",
      "INTERNAL_ONLY",
      "NOT_A_SOURCE",
      "ABSENT"
    ],
    "model_use": [
      "USER_FACING",
      "USER_FACING_WITH_LIMITS",
      "INTERNAL_ONLY",
      "NOT_A_SOURCE",
      "ABSENT"
    ],
    "storage": [
      "USER_FACING",
      "USER_FACING_WITH_LIMITS",
      "INTERNAL_ONLY",
      "NOT_A_SOURCE",
      "ABSENT"
    ],
    "context": [
      "USER_FACING",
      "USER_FACING_WITH_LIMITS",
      "INTERNAL_ONLY",
      "NOT_A_SOURCE",
      "ABSENT"
    ]
  },
  "families": [
    {"register_family": "massive_stock_day", "lanes": ["MARKET_DATA"], "postures": {"user_redistribution": "USER_FACING", "model_use": "USER_FACING", "storage": "USER_FACING", "context": "USER_FACING"}},
    {"register_family": "first_party_baskets_theme_graph", "lanes": ["THEME_MEMBERSHIP", "THEME_GRAPH"], "postures": {"user_redistribution": "USER_FACING", "model_use": "USER_FACING", "storage": "USER_FACING", "context": "USER_FACING"}},
    {"register_family": "fred_alfred", "lanes": ["MACRO_SERIES"], "postures": {"user_redistribution": "INTERNAL_ONLY", "model_use": "NOT_A_SOURCE", "storage": "INTERNAL_ONLY", "context": "INTERNAL_ONLY"}},
    {"register_family": "census_m3", "lanes": ["MACRO_SERIES"], "postures": {"user_redistribution": "INTERNAL_ONLY", "model_use": "INTERNAL_ONLY", "storage": "INTERNAL_ONLY", "context": "INTERNAL_ONLY"}},
    {"register_family": "sec_edgar", "lanes": ["FILING_FACT", "FILING_SPAN"], "postures": {"user_redistribution": "USER_FACING_WITH_LIMITS", "model_use": "USER_FACING", "storage": "USER_FACING", "context": "USER_FACING"}},
    {"register_family": "nasdaq_earnings_calendar", "lanes": ["EARNINGS_CALENDAR"], "postures": {"user_redistribution": "NOT_A_SOURCE", "model_use": "NOT_A_SOURCE", "storage": "NOT_A_SOURCE", "context": "INTERNAL_ONLY"}},
    {"register_family": "yahoo_expectations", "lanes": ["EARNINGS_EXPECTATIONS"], "postures": {"user_redistribution": "NOT_A_SOURCE", "model_use": "NOT_A_SOURCE", "storage": "INTERNAL_ONLY", "context": "INTERNAL_ONLY"}},
    {"register_family": "basket_spy_closes", "lanes": ["MARKET_DATA"], "postures": {"user_redistribution": "NOT_A_SOURCE", "model_use": "NOT_A_SOURCE", "storage": "INTERNAL_ONLY", "context": "INTERNAL_ONLY"}},
    {"register_family": "equitydesk_finnhub_call_scores", "lanes": ["EARNINGS_CALL_SCORE", "EARNINGS_CALL_CONTEXT"], "postures": {"user_redistribution": "NOT_A_SOURCE", "model_use": "NOT_A_SOURCE", "storage": "INTERNAL_ONLY", "context": "INTERNAL_ONLY"}},
    {"register_family": "finviz_ths", "lanes": ["THEME_MEMBERSHIP", "THEME_GRAPH"], "postures": {"user_redistribution": "NOT_A_SOURCE", "model_use": "NOT_A_SOURCE", "storage": "INTERNAL_ONLY", "context": "INTERNAL_ONLY"}},
    {"register_family": "sp_kensho_theia", "lanes": ["THEME_MEMBERSHIP", "THEME_GRAPH"], "postures": {"user_redistribution": "NOT_A_SOURCE", "model_use": "NOT_A_SOURCE", "storage": "NOT_A_SOURCE", "context": "NOT_A_SOURCE"}},
    {"register_family": "consensus_estimates", "lanes": ["EARNINGS_EXPECTATIONS"], "postures": {"user_redistribution": "NOT_A_SOURCE", "model_use": "NOT_A_SOURCE", "storage": "NOT_A_SOURCE", "context": "NOT_A_SOURCE"}},
    {"register_family": "transcripts_rp_public_primary_v1", "lanes": ["EARNINGS_GUIDANCE", "EARNINGS_CALL_CONTEXT"], "postures": {"user_redistribution": "NOT_A_SOURCE", "model_use": "INTERNAL_ONLY", "storage": "INTERNAL_ONLY", "context": "INTERNAL_ONLY"}},
    {"register_family": "press_narrative_search_trends", "lanes": ["PRESS", "NARRATIVE", "SEARCH", "GOOGLE_TRENDS"], "postures": {"user_redistribution": "INTERNAL_ONLY", "model_use": "NOT_A_SOURCE", "storage": "INTERNAL_ONLY", "context": "INTERNAL_ONLY"}}
  ],
  "absent_posture_display_code": "RIGHTS_INTERNAL_ONLY"
}
```

## BUILD ORDER (amended)

- **B04-A** — dossier wrapper, A9 reason map, A12 closed wrapper shape, A7 wrapper clock split, A8 gated projection skeleton, new dossier route, typed identity conflict, historical-event-set absence, and B04-A fixture/test matrix. It does not commission until this draft is ratified without repairs that alter its contract.
- **B04-B** — A11 lane-family map and complete route-boundary rights gate. The gate runs before any user-facing render of transcript-derived lanes, before removal/redaction, and before content addressing. The static `ALLOWED` transcript guidance noted by the census is a pre-existing defect that B04-B closes; until then it is not user-facing dossier evidence.
- **B04-C** — current view, correction comparison, EN/ZH route renderer, and consumer integration. It proves the full fixture matrix and language-selection behavior at the JSON route.
- **B04-D** — evidence-class propagation, still gated on D07. D07's block on B04 is narrowed to B04-D because A8 moves `evidence_class` to the wrapper; the seat must ratify that narrowing.
- **B20/B07** — every user-readable visual surface. B04 closes at JSON detail plus renderer sentences. The macro-site user surface owes dark/light × EN/ZH × desktop 1440/mobile 390 evidence; the Terminal shell owes dark-only evidence under DEC:TERMINAL-SHELL-IS-DARK-ONLY-EVIDENCE-MATRIX-2026-09-06. This is a card-scope narrowing from “user-readable detail” to route-owned JSON plus renderer sentences, and the seat must record it.
