# B04 Evidence Dossier Contract Census (2026-09-23)

## SOURCE_SHA

`8fda4f8779639ec571f02ef5e9689d34b14d48cd` — `git rev-parse origin/main` in this detached-head worktree. Citation convention: `path:line@8fda4f8779`. This is a read-only census; no data artifact was opened, no source adapter was changed, and no outcome, ledger, return, P&L, trial, or scoreboard artifact was read.

## Q1 THE PROJECTION TODAY

- **Entry point and closed envelope.** `build_earnings_intelligence_vector` accepts the episode, an exact `peg:<64 hex>` generation id, B1 `episode_known_at`, an `IssuerMaster`, an event-discovery callable, and a revision-reader callable at `engine/prophet_lab/intelligence_vector.py:1025-1033@8fda4f8779`. It returns one `prophet.intelligence_vector/v1` object whose top-level keys are closed by `_TOP_KEYS`: `schema`, `projection_id`, `episode_ref`, `decision_cut`, `adapter_set_version`, `evidence_families`, `economic_dependence_groups`, `semantic_heads`, `fusion_bindings`, `authority`, and `assembly_receipt` at `engine/prophet_lab/intelligence_vector.py:53-57@8fda4f8779`. `_build_envelope` creates those fields at `engine/prophet_lab/intelligence_vector.py:977-1018@8fda4f8779`; `_finish_family` and the projection id are content-addressed at `engine/prophet_lab/intelligence_vector.py:964-967` and `:1019-1021`.
- **Exact episode binding.** The builder checks the candidate-episode schema and B1 episode-id shape at `engine/prophet_lab/intelligence_vector.py:1040-1048@8fda4f8779`, and `_validate_b1_episode_identity` recomputes the canonical B1 id from security, identity epoch, structural anchor, and generation at `:261-291`. The response carries `episode_ref = {schema, episode_id, generation_id, identity_ref}` at `:980-985`; the closed key set is enforced at `:1676-1691`.
- **Per-field shape.** A family is closed by `_FAMILY_KEYS` at `engine/prophet_lab/intelligence_vector.py:58-65@8fda4f8779` and initialized by `_base_family` at `:452-492`. An observation is either `PRESENT` with a value, unit, source refs, roots, dependence group, and lineage state, or `ABSENT` with null value and one or more reasons at `_observation` `:813-849` and validator gates `:1516-1579`. Present values must have source and root lineage at `:1564-1567`; absent values cannot have value, unit, source refs, roots, groups, or quality flags at `:1552-1563`. The present native metrics are only `fact:revenue` and `guidance:revenue_yoy_pct` (`:869-907`); owner deltas appear in the single trajectory dimension (`:910-942`). Revenue can additionally carry a normalized `value_usd` (`:833-837`; normalization checked at `:1580-1591`). The unit-normalization tests pin these shapes at `tests/test_intelligence_vector_units.py:143-223@8fda4f8779`.
- **Clocks.** Every clock is `{state, value, interval, precision, basis, source_ref_ids}` (`_clock`, `engine/prophet_lab/intelligence_vector.py:386-396@8fda4f8779`). `_point_in_time` carries overall basis/admissibility plus seven clocks: named-null `source_effective_at`; source publication and owner observation; named-null capture; workspace computation; later correction; and decision time at `:399-449`. It is based on `SOURCE_VINTAGE` when any source/owner/computation clock is present (`:404-414`). The builder derives the decision cut as `episode.opened_at == max(anchor.time, known_at)` at `:1050-1062`; admissibility requires all three revision clocks to be on or before the cut at `:1223-1228`; a missing clock becomes a named `UNKNOWN`, never an absence (`:1188-1221`).
- **Later-revision receipt.** `_later_revision_receipt` emits `{later_revision_receipt_id, owner_subject_id, generation_id, workspace_receipt, source_sha256, source_available_at, observed_at, generated_at, disposition, source_ref_ids}` at `engine/prophet_lab/intelligence_vector.py:697-721@8fda4f8779`. Later revisions are selected only when an owner clock crosses the cut (`:1281-1292`), their generation must be strictly after the cut (`:1293-1308`), and their refs/receipts populate the correction block (`:1321-1345`). The validator requires valid clocks, a post-cut generation, a receipt-bound source hash, a disposition matching refs, and a content-addressed id at `:2035-2107`.
- **Owner-lane dispositions and adapted field paths.** `_owner_lane_dispositions` emits one assessment and exactly three lane rows — `DELTA_REVENUE`, `FACT_REVENUE`, `GUIDANCE_REVENUE_YOY_PCT` — each as `PRESENT|ABSENT` candidate state and `PROJECTED|UNPROJECTABLE|ABSENT` disposition, with the authenticated workspace manifest receipt at `engine/prophet_lab/intelligence_vector.py:630-694@8fda4f8779`. `_adapted_field_paths` binds accepted facts to `facts[n].{metric,unit,value,basis}`, guidance to `guidance[n].{metric,low,high,unit,status}`, and deltas to `deltas[n].{metric,basis_match,current.*,prior|consensus.{schema,state,reason}}` at `:724-756`. The closed path regular expression is at `:103-108`; `_source_refs` emits document id, generation, hash, those paths, and `render_policy: DERIVED_ONLY` at `:759-802`.
- **Assembly limits.** The receipt always says `source_reader: read_event_source_revisions`, `event_discovery_scope: CURRENT_GENERATION_ONLY`, `historical_event_set_reconstruction: false`, `identity_resolution_scope: CURRENT_REGISTRANT_ONLY`, `revision_visibility_scope: ISSUER_RELEASE_SOURCE_HASH_ONLY`, and discloses the owner 500-hop chain bound at `engine/prophet_lab/intelligence_vector.py:1006-1017@8fda4f8779`; those literals are enforced at `:2231-2248`.
- **Route.** `GET /api/prophet/lab/v1/episodes/{episode_id}/intelligence` is declared at `app/prophet_lab.py:254-258@8fda4f8779`. Its dependency is `require_site_full_user`, which authenticates first and then enforces site-full entitlement even in staging at `:81-98`; anonymous and free-tier behaviors are pinned by `tests/test_prophet_lab_api.py:371-401@8fda4f8779`. The route evaluates `PROPHET_LAB_DISABLED` per request and fails toward disabled for unrecognized values at `:144-156`; the handler returns a private 503 before B1 reads at `app/prophet_lab.py:260-267`.
- **Roots and exact generation.** The route resolves `PROPHET_LAB_EPISODE_STORE_ROOT` (default `data/us_prophet_rank/episodes`) and `PROPHET_LAB_SECURITY_MASTER_PATH` (default `data/reference/security_master.parquet`) at `app/prophet_lab.py:269-277@8fda4f8779`; neither may be unset. It loads one B1 snapshot, requires exactly one episode id and exactly one `OPENED` event with string `known_at`, then passes that atomic `snapshot.generation_id` and `episode_known_at` to the adapter at `:279-306`. Missing episodes return a private 404; duplicates, malformed OPENED state, and root/read failures become private 503 responses at `:280-321` (`app/prophet_lab.py:119-120` sets private no-store headers).
- **Integrity and transport.** `_source_integrity_failed` searches the assembly receipt for `WorkspaceChainIntegrityError`; the route converts that case to a private 503 rather than returning an apparently healthy projection at `app/prophet_lab.py:132-141` and `:301-321@8fda4f8779`. Route behavior is pinned by paid 200, 401/403, kill-switch, 404, corrupt-B1 503, integrity 503, and leakage tests at `tests/test_prophet_lab_api.py:352-560@8fda4f8779`.
- **Keys-only response skeleton.** Reconstructed from the code paths above:

```json
{
  "schema": [], "projection_id": [], "episode_ref": {
    "schema": [], "episode_id": [], "generation_id": [], "identity_ref": []
  },
  "decision_cut": {
    "opened_at": [], "opened_session": [], "anchor_time": [],
    "known_at": [], "tradable_at": {"state": [], "value": [], "basis": []}
  },
  "adapter_set_version": [],
  "evidence_families": [{
    "family_projection_id": [], "evidence_family_id": [],
    "family_contract_version": [], "owner_ref": [], "subject_binding": {
      "state": [], "episode_company_id": [], "earnings_company_id": [],
      "owner_subject_id": []
    },
    "semantic_head_ids": [], "method_version": [], "point_in_time": {
      "basis": [], "decision_admissibility": [], "missing_clocks": [],
      "source_effective_at": [], "source_published_at": [], "known_at": [],
      "captured_at": [], "computed_at": [], "corrected_at": [], "decision_at": []
    },
    "applicability": {"state": [], "basis": []},
    "coverage": {"state": [], "basis": []},
    "freshness": {"state": [], "basis": []},
    "rights": {"state": [], "profile_ref": []},
    "identity_state": [], "quality": {"flags": []},
    "source_refs": [{
      "source_ref_id": [], "owner_namespace": [], "object_schema": [],
      "object_id": [], "version_or_generation": [], "content_hash": [],
      "field_paths": [], "render_policy": []
    }],
    "evidence_roots": [{
      "evidence_root_id": [], "source_ref_id": [], "root_type": []
    }],
    "observations": [{
      "observation_id": [], "native_metric_id": [], "value_state": [],
      "value": [], "units": [], "value_usd": [], "method_class": [],
      "method_version": [], "source_ref_ids": [], "evidence_root_ids": [],
      "economic_dependence_group_ids": [], "quality_flags": [],
      "absence_reasons": [], "neutral_definition_ref": [],
      "correction_lineage_state": []
    }],
    "explanation_facts": [], "trajectory": {"state": [], "dimensions": []},
    "correction": {
      "state_at_decision": [], "decision_version_ref_ids": [],
      "later_correction_ref_ids": [], "later_revision_receipts": [],
      "later_revision_state": [], "current_state": []
    },
    "calibration": {"state": [], "registration_ref": []},
    "fusion_bindings": [], "authority": [],
    "owner_warnings": [], "owner_lane_dispositions": []
  }],
  "economic_dependence_groups": [],
  "semantic_heads": [], "fusion_bindings": [], "authority": [],
  "assembly_receipt": {
    "adapter": [], "assembled_at": [], "source_reader": [],
    "event_discovery_scope": [], "historical_event_set_reconstruction": [],
    "identity_resolution_scope": [], "revision_visibility_scope": [],
    "revision_chain_bound_disclosure": [], "event_id": [], "errors": []
  }
}
```

The `value_usd` key is legal only for a present `fact:revenue` observation (`engine/prophet_lab/intelligence_vector.py:1523-1536@8fda4f8779`).

## Q2 THE SIX DISCRIMINATING CASES

| Case | Code path that would meet it | Field / reason produced (or none) | Test that pins it | Status and evidence |
|---|---|---|---|---|
| 1. Published before cut but captured after | Admission filters all three revision clocks against the B1 cut at `engine/prophet_lab/intelligence_vector.py:1223-1228@8fda4f8779`; no admissible row becomes `NOT_CAPTURED_AT_DECISION` when an owner clock is after cut at `:1229-1241`. | `coverage = COVERED/verified_revision_chain`, `point_in_time.decision_admissibility = AFTER_DECISION_CUT`, and observation `value_state=ABSENT`, `value=null`, `absence_reasons=["NOT_CAPTURED_AT_DECISION"]`. | `tests/test_prophet_lab.py:3335-3342@8fda4f8779` builds the `after-decision-cut` outcome; `:3362-3375` checks it remains coherent after content re-addressing. | **COVERED** — the exact cut gate and typed absence are implemented and tested; D07 still owes the study-level replay label. |
| 2. Corrected current body | A later generation crossing any owner clock is receipted; only the pre-cut body supports decision values, and projected later refs mark `current_state=CORRECTED` at `engine/prophet_lab/intelligence_vector.py:1281-1345@8fda4f8779` and `:1425-1446`. | `correction.later_revision_receipts`, `later_correction_ref_ids`, `later_revision_state=PROJECTED`, `current_state=CORRECTED`, plus a post-cut `point_in_time.corrected_at`. | `tests/test_prophet_lab.py:3615-3632@8fda4f8779` accepts later generations when an owner clock crosses; `:3634-3648` rejects a non-post-cut generation; `:3650-3667` keeps later non-crossing bodies from replacing the decision body. | **PARTIAL** — the original body and correction receipt are covered, but no user-facing current-body projection exists. |
| 3. Missing historical event set | Event discovery is current-only and the assembly receipt explicitly states `CURRENT_GENERATION_ONLY` and `historical_event_set_reconstruction=false` at `engine/prophet_lab/intelligence_vector.py:1009-1012@8fda4f8779`; no historical event-set lookup exists. | A current missing event is `NOT_COVERED/no_current_generation_event` (`:1129-1136`); missing verified revisions are `NOT_COVERED/no_verified_revisions` (`:1179-1186`). There is no reason distinguishing “no event then” from “history not reconstructable”. | Current limitation: `tests/test_prophet_lab.py:1891-1894@8fda4f8779`. Absence proof: `grep -RInE 'historical_event_set|event_set_reconstruction|reconstruct.*event.*set' engine/prophet_lab app/prophet_lab.py tests/test_prophet_lab.py tests/test_prophet_lab_api.py` returned only the disclosure and its check at `engine/prophet_lab/intelligence_vector.py:1011,2235,2241` plus `tests/test_prophet_lab.py:1892`. | **BLIND** — no typed “event set unavailable at the historical cut” lane exists; this is a B04 blocker. |
| 4. Wrong issuer | CIK is resolved first (`engine/prophet_lab/intelligence_vector.py:1064-1075@8fda4f8779`); requested event, workspace event, workspace issuer, and resolved CIK must agree at `_validate_owner_workspace_binding` `:308-365`. Disagreement raises, and the route turns it into a private 503 at `app/prophet_lab.py:307-321@8fda4f8779`. | No user-facing field: contract error becomes `{error: prophet_episode_intelligence_unavailable, detail: Episode intelligence temporarily unavailable}` HTTP 503. | `tests/test_prophet_lab.py:2143-2151@8fda4f8779` parametrizes foreign event, foreign issuer, and generation disagreement; route blind-safe failure is pinned at `tests/test_prophet_lab_api.py:478-524`. | **PARTIAL** — integrity is fail-closed, but the user does not receive a dossier-level typed wrong-issuer/binding absence. |
| 5. Unlicensed fact | The closed lane allowlist ignores non-revenue/non-guidance text at `engine/prophet_lab/intelligence_vector.py:495-620@8fda4f8779`, and consensus can be typed `consensus_unlicensed` before admission (`:563-571`). But every emitted Earnings family is statically `rights = ALLOWED / event_workspace.v1:derived_only` at `:452-472`; no source-family posture gate reads the rights register. | Transcript guidance can be projected under the static ALLOWED profile; only owner warning `consensus_unlicensed` can surface, not a user-facing `RIGHTS_INTERNAL_ONLY` or `RIGHTS_NOT_A_SOURCE` fact absence. | Allowlist/leakage: `tests/test_prophet_lab.py:2154-2193@8fda4f8779`. Consensus warning: `:1859-1914`. Absence proof: `grep -RInE 'PROPHET_US_SOURCE_RIGHTS_REGISTER|internal-only|not-a-source|user-facing-with-limits' engine/prophet_lab app/prophet_lab.py` returned no output (rc 1). Validator only enforces the fixed ALLOWED pair at `engine/prophet_lab/intelligence_vector.py:1864-1871`. | **BLIND** — an internal-only family's derived fact is not blocked at the detail boundary; this is the top rights blocker. |
| 6. Conflicting spans / revisions | Exact one-candidate admission refuses duplicate acceptable facts, guidance, and deltas (`engine/prophet_lab/intelligence_vector.py:499-518`, `:530-560`, `:574-627@8fda4f8779`). Revisions are ordered by greatest source publication, then greatest observation; a remaining tie fails closed at `:1247-1271`. | No numeric winner: `coverage=UNKNOWN/unresolved_clock_tie`, `quality.flags=["unresolved_clock_tie"]`, correction states `CONFLICTED`, observation reason `CONFLICTED`; duplicate acceptable owner rows instead make the lane unprojectable and may leave `UNKNOWN/exact_source_lineage_unavailable` (`:1350-1414`). | One-candidate/lineage tests: `tests/test_prophet_lab.py:1991-2002` and `:2232-2285@8fda4f8779`; clock-tie outcome: `:2779-2842`; current-state mutations: `:3262-3375`. | **COVERED** — both candidate ambiguity and clock ties are typed fail-closed paths, although a product copy table is still owed in Q6. |

**Status count: 2 COVERED · 2 PARTIAL · 2 BLIND.**

## Q3 ORIGINAL VS CURRENT VIEW

- **Original identity today.** The exact original view is identified jointly by canonical B1 `episode_id`, atomic `episode_generation_id`, B1 `OPENED known_at`, episode `opened_at`/structural anchor, and content-addressed `projection_id`: inputs are bound at `engine/prophet_lab/intelligence_vector.py:1025-1062@8fda4f8779`, response identity at `:977-985`, and the snapshot route passes the loaded generation and OPENED clock at `app/prophet_lab.py:279-306`.
- **Workspace identity.** The selected decision body is additionally bound by owner event id, workspace generation id, and the workspace manifest receipt `{sha256, bytes}` in `owner_lane_dispositions` (`engine/prophet_lab/intelligence_vector.py:630-694@8fda4f8779`). Later generations carry their own `generation_id`, workspace receipt, source hash, clocks, and `later_revision_receipt_id` (`:697-721`).
- **Content ids.** Source refs are `src:<sha256>` over owner namespace, schema, object id, generation, hash, exact field paths, and derived-only policy (`engine/prophet_lab/intelligence_vector.py:759-802@8fda4f8779`). Roots, observations, lane receipts, later receipts, families, and the projection are likewise content-addressed (`:181-183`, `:697-721`, `:964-967`, `:1019-1021`). Thus a projection id changes with owner receipt or projected semantic changes, but not merely because assembly receipt errors change: the projection-id semantic excludes `assembly_receipt` at `:1019`.
- **Can the route serve two distinct views? No.** There is no `view`, original, or current route parameter. `grep -RInE 'view.*original|view.*current|original_view|current_view' engine/prophet_lab app/prophet_lab.py tests/test_prophet_lab_api.py` returned only unrelated Lab board comments in `engine/prophet_lab/response.py:178` and `engine/prophet_lab/boards.py:210`, not this detail route. The current endpoint always projects the pre-cut selected body; later current bodies appear only as receipts/refs, not as a second set of current facts.
- **What a correction looks like now.** The response keeps decision observations/trajectory sourced to decision refs only, while `correction.later_revision_receipts` carries post-cut generations and `later_correction_ref_ids` names only projectable later source refs (`engine/prophet_lab/intelligence_vector.py:1281-1345@8fda4f8779`). With a projectable later body, `later_revision_state=PROJECTED`, `current_state=CORRECTED`, and `point_in_time.corrected_at` is asserted and bound to those refs (`:1377-1446`; derivation checked at `:2109-2145`). With a visible but unprojectable later body, the receipt is retained with `OBSERVED_UNPROJECTABLE`, no later source refs, and `current_state=UNKNOWN` (`:1425-1445`; `tests/test_prophet_lab.py:3418-3460`).
- **Tests.** Exact B1 generation and route identity are pinned at `tests/test_prophet_lab_api.py:352-368@8fda4f8779`; canonical identity/cut at `tests/test_prophet_lab.py:1859-1895` and `:2560-2615`; receipt/current correction outcomes at `:2779-2842`, `:3378-3460`, and `:3581-3667`. There is no test for a separately requested or simultaneously served current view (grep above).

## Q4 RIGHTS GATE IN THE PROJECTION

- **Current gate.** The only projection right is fixed to `{"state":"ALLOWED","profile_ref":"event_workspace.v1:derived_only"}` at `engine/prophet_lab/intelligence_vector.py:471@8fda4f8779`, and the validator rejects any other pair at `:1864-1871`. Source refs also carry `render_policy=DERIVED_ONLY` (`:785`, checked `:1509-1510`). This safely blocks raw bodies, URLs, paths, spans, and non-allowlisted fields (`_FORBIDDEN_KEYS`, `:66-70`; leakage tests `tests/test_prophet_lab.py:2154-2193`), but it does not distinguish source-family rights postures.
- **User-facing.** A user-facing family may project a closed derived fact/absence with source id, content hash, generation, exact field paths, and no full-document duplication (`engine/prophet_lab/intelligence_vector.py:759-802@8fda4f8779`).
- **User-facing with limits.** A limited family may project only the same closed derived values and must carry the machine code plus plain-language limitation (for example SEC citation/trademark handling) in the proposed dossier rights note; commercial terms themselves are not copied into the response.
- **Internal-only.** A derived internal-only fact must not enter a user-facing observation. Today nothing performs that source-family check: the static ALLOWED assignment is at `engine/prophet_lab/intelligence_vector.py:452-472@8fda4f8779`, the validator requires ALLOWED at `:1864-1871`, and the grep `grep -RInE 'PROPHET_US_SOURCE_RIGHTS_REGISTER|internal-only|not-a-source|user-facing-with-limits' engine/prophet_lab app/prophet_lab.py` returned no output. This is a B04 blocker, ranked #3 in Q7.
- **Not-a-source.** The dossier must show only a typed absence and must not name the rejected value. Consensus is the established model: the owner can mark `consensus_unlicensed`, the projection preserves the owner warning, and the rights register records “permanently absent” (`engine/prophet_lab/intelligence_vector.py:563-571`, `:1421-1423`; `tests/test_prophet_lab.py:1570-1574`, `:1859-1914`; rights register summary at `research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md:185-193@8fda4f8779`).
- **Register postures.** The summary lists user-facing/feed-conditional Massive, user-facing first-party baskets/theme graph, internal-only FRED/Census/Yahoo expectations and Basket-SPY/Earnings-call/Finnhub/Finviz-THS/transcripts/press families, and not-a-source Nasdaq storage/model/redistribution, S&P Kensho/Theia, and consensus estimates at `research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md:217-233@8fda4f8779`. SEC is user-facing with citation and trademark limits at `:113-121`.
- **Two-plane boundary.** The EquityDesk/Earnings-call plane and D5 company-intelligence plane remain separate; EDGAR-anchored releases are the issuer-fact plane, while expectations remain context and unlicensed consensus remains typed absence (`R6-D03-01_SOURCE_READINESS_SCOPE_2026-09-23.md:71-74@8fda4f8779`; A14 summary at `PU_W1_C_D5_DOC_TRUTH_SESSION_2026-09-23.md:7-10`).

## Q5 D07 HOOKS

- **No class exists in the detail projection.** `grep -RInE 'PUBLIC_INFO_REPLAY|observed-as-run|observed_as_run|retrospective|evidence_class' engine/prophet_lab app/prophet_lab.py` finds no class in the D5 adapter/route; its only `retrospective` hits are the separate Lab-board observation classification in `engine/prophet_lab/observation.py:6-14` and related files. The D5 envelope has no `evidence_class` key and D07 remains `OPEN_TECHNICAL_DECISION_FABLE_AUTHORIZED_TO_RESOLVE` with B04 blocked (`effective/DECISION_REGISTER.json:179-205@8fda4f8779`).
- **Binding prior law.** B4 requires `PUBLIC_INFO_REPLAY` as a named class, a declared acquisition lag and sensitivity analysis; it is never pooled with observed-as-run rows, has no promotion weight, and bodies are read only through `read_event_source_revisions`/`read_all_event_source_revisions` (`SEAT_RULING_R6-PREREG-01_2026-09-23.md:18-19@8fda4f8779`). D07 requires observed-as-run, point-in-time replay, or retrospective designation per study and says a document published before cut but captured after is not observed-as-run (`effective/DECISION_REGISTER.json:183-205`).
- **Least-surface proposal.** Add one top-level closed field `evidence_class: "OBSERVED_AS_RUN" | "PUBLIC_INFO_REPLAY" | "RETROSPECTIVE"` and one explicit caller argument of the same name to `build_earnings_intelligence_vector`. The value must come from the registered study, be included in projection-id semantics, and be checked against the enum plus the emitted clock/admissibility state. The route only propagates a registered value; until D07 closes, it should expose a typed `NOT_ASSERTED` dossier-level class rather than infer one.
- **Why this is not the forbidden shortcut.** D07 forbids treating date-filtered retrieval or masking as proof that modern model weights lack future knowledge (`effective/DECISION_REGISTER.json:183-185@8fda4f8779`). This proposal does not certify model vintage, convert filtering into eligibility, or merge classes. It labels the study and keeps its acquisition lag, sensitivity analysis, and model/source eligibility in D07's closure artifact. The existing three-clock conjunction remains necessary but not sufficient for `PUBLIC_INFO_REPLAY`.

## Q6 PROPOSED B04 CONTRACT

### (a) Minimal additions and closed reason vocabulary

Create a route-owned wrapper rather than duplicating the existing vector:

```json
{
  "schema": "prophet.episode_evidence_dossier/v1",
  "episode_ref": [],
  "evidence_class": {"state": [], "value": [], "basis": []},
  "views": {
    "original": {"state": [], "vector_projection_id": [], "view_basis": []},
    "current": {"state": [], "vector_projection_id": [], "view_basis": []}
  },
  "rights": [{"source_family": [], "state": [], "profile_ref": [], "note_code": []}],
  "missingness": [{"lane": [], "state": [], "reason_code": []}],
  "messages": {"reason_code": [], "language": [], "text": []}
}
```

Each `views.*` payload remains an unchanged all-false `prophet.intelligence_vector/v1`. `current` is always visibly labelled research/known-now and can never inherit original `decision_admissibility=ADMISSIBLE`.

Closed dossier reason codes (machine code then user meaning):

| Code | Meaning | Case closed | Plain EN | Plain ZH |
|---|---|---|---|---|
| `NOT_CAPTURED_AT_DECISION` | At least one required source clock is after the original decision cut, so the body was not available to the original run. | Late capture | This information was published before the decision, but we did not capture it until later. | 这条信息在决策前已经发布，但我们直到稍后才取得它。 |
| `CORRECTED_LATER` | A later source generation is visible and bound by receipt; only the original fields remain decision evidence. | Corrected current body | A later version changed this information after the original decision. | 在原始决策之后，新版本更改了这条信息。 |
| `HISTORICAL_EVENT_SET_UNAVAILABLE` | No source-dated historical event-set row can identify the event population at the requested cut. | Missing historical set | We cannot reconstruct the full event list that existed at that time. | 我们无法重建当时存在的完整事件列表。 |
| `IDENTITY_BINDING_CONFLICT` | Episode issuer, owner event, or workspace issuer bindings disagree. | Wrong issuer | The evidence does not all point to the same company. | 这些证据并非全部指向同一家公司。 |
| `RIGHTS_INTERNAL_ONLY` | The family may support private diagnostics but may not be shown to the user. | Unlicensed fact | We can use this source internally, but cannot show this fact. | 这个来源只能内部使用，不能向你展示这条事实。 |
| `RIGHTS_NOT_A_SOURCE` | The family is ruled out for storage, model, or redistribution use. | Unlicensed fact | This source cannot be used for this product fact. | 这个来源不能用于这项产品事实。 |
| `CONFLICTING_SOURCE_CLOCKS` | Two otherwise admissible revisions tie on the required ordering clocks. | Conflicting spans | The source versions disagree about which version came first. | 来源版本对先后顺序存在冲突。 |
| `EXACT_LINEAGE_UNAVAILABLE` | An owner candidate exists but its exact document field lineage cannot be projected. | Sparse source | The source exists, but we cannot point to the exact field used. | 来源存在，但我们无法指出所用的确切字段。 |

`UNKNOWN` remains the final closed fallback, rendered as “We do not yet know why this field is missing.” / “我们仍不知道这个字段缺失的原因。” Codes are never shown as user-facing text; the route returns the paired plain sentence.

### (b) All-false closure versus accepted dossier

- **Closed all-false** is a successful bounded answer, not a zero or neutral fact. It is used when an original/current view cannot be responsibly accepted because D07 class is unresolved, rights posture blocks the lane, historical event-set identity is unavailable, identity/event binding conflicts, source clocks conflict, or owner integrity fails. Authority remains all six false; every blocked expected lane carries one reason code; no present observation is emitted from a blocked lane; raw source material and commercial terms are absent.
- **Accepted evidence projection** requires: exact canonical B1 episode and one OPENED event; a registered D07 class; resolved source-family rights; one authenticated owner event and revision chain; unique selection or typed conflict; and for every expected lane either a present derived value with exact source/root lineage or a source-backed typed absence. A partial packet is accepted as a dossier only when every non-projected expected lane names its specific reason; `COVERED` requires all expected non-absent owner lanes projected, matching today's complete/partial rule (`engine/prophet_lab/intelligence_vector.py:1392-1414@8fda4f8779`).
- Acceptance never grants rank, gate, sizing, signal, entry, or execution authority; those booleans remain false in both views.

### (c) Original/current dual-view rule

1. `original` is the authoritative default and uses the exact B1 generation, OPENED `known_at`, decision cut, and only revisions whose source, observation, and generation clocks are all at or before that cut.
2. `current` uses the same owner event and immutable revision reader, but labels the latest visible generation as research/known-now. It must not overwrite original observations, inherit admissibility, or pool values with the original run.
3. The response carries both view states and projection ids. When current cannot be projected, it is a named unavailable view, never a copy of original.
4. A correction is explainable only by comparing the same adapted lane across the two views and citing each view's source refs/workspace receipts; no full documents or prose bodies are copied.

### (d) Rights gate rule

1. A compiled, versioned source-family posture map is loaded from the rights register, not hard-coded per adapter branch.
2. `USER_FACING` and `USER_FACING_WITH_LIMITS` may emit closed derived fields under `DERIVED_ONLY`, with limits represented by code plus plain language and without quoting commercial terms.
3. `INTERNAL_ONLY` and `NOT_A_SOURCE` emit no value, hash, document id, field path, prose, or full document for that family; they emit only the lane-level typed reason. Consensus remains permanently absent.
4. The gate is tested at the route boundary, not merely inside the adapter, so a future adapter cannot silently expose an internal-only derived value.

### (e) D07 class field

The dossier wrapper carries `evidence_class` as a typed `{state, value, basis}`. Until D07 resolves, `state=NOT_ASSERTED`, `value=null`, and `basis=D07_OPEN`; once registered, the route propagates `OBSERVED_AS_RUN`, `PUBLIC_INFO_REPLAY`, or `RETROSPECTIVE` and the underlying vector carries the same value. The field is included in projection identity and never inferred from date filtering or model availability alone.

### Smallest bounded build units

| Unit | Owned files | Tests to add | Discriminating case proved | Release limit respected |
|---|---|---|---|---|
| B04-1 reason-code census map | `engine/prophet_lab/intelligence_vector.py`, `app/prophet_lab.py` | Unit tests mapping every current outcome to exactly one closed code; no rendering yet | Late capture, conflicts, exact-lineage absence | No narrative waiver or user copy yet |
| B04-2 D07 class plumbing | `engine/prophet_lab/intelligence_vector.py`, `app/prophet_lab.py`, D07 registration artifact when available | Missing/unresolved class and registered-class propagation tests | Published-before-cut/captured-after class separation | Does not date-filter a model and call it replay |
| B04-3 dossier wrapper and dual view | `app/prophet_lab.py`; existing vector remains unchanged | Original/current key-set, separate projection ids, current non-admissibility, correction comparison | Corrected current body | No document duplication or new warehouse |
| B04-4 historical scope typed absence | `engine/prophet_lab/intelligence_vector.py`, `app/prophet_lab.py` | Current discovery with a pre-inception episode returns `HISTORICAL_EVENT_SET_UNAVAILABLE`, not “no event” | Missing historical event set | No backdated event set |
| B04-5 route rights gate | `app/prophet_lab.py`, existing source-family adapters | SEC derived fact allowed; transcript/internal fact blocked; consensus/not-a-source absent; route leakage scan | Wrong posture/unlicensed fact | No unlicensed prose or commercial terms |
| B04-6 EN/ZH plain-language renderer | `app/prophet_lab.py`, existing paired UI/test conventions | Every code has one plain EN/ZH sentence; machine code is not rendered; both languages equal | All six cases | Plain sentences, no slugs shown to users |

No build unit adds a provider, outcome join, model feature, promotion weight, or production DDL.

## Q7 BLOCKERS

1. **D07 remains open and supplies no per-study class.** Owner: Fable Meta-CEO with existing source/model owners (`effective/DECISION_REGISTER.json:179-205@8fda4f8779`). Smallest unit: B04-2 after the D07 registration artifact; until then expose `NOT_ASSERTED`, never guess.
2. **The route serves no distinct current view.** Owner: D5/Earnings route owner. Smallest unit: B04-3 wrapper plus original/current tests while preserving all-false vectors.
3. **No runtime source-family rights gate.** Owner: D5/Earnings plus source-rights owner. Smallest unit: B04-5 compiled posture map and route boundary tests; current static ALLOWED evidence is `engine/prophet_lab/intelligence_vector.py:471@8fda4f8779` and `:1864-1871`.
4. **Historical event-set missingness is conflated with current non-coverage.** Owner: existing source/event owners. Smallest unit: B04-4 typed limit without reconstructing history; binding rule is `R6-D03-01_SOURCE_READINESS_SCOPE_2026-09-23.md:73@8fda4f8779`.
5. **Machine outcomes have no paired plain-language EN/ZH rendering.** Owner: private product owner. Smallest unit: B04-6, after reason codes and rights postures are stable.

## EVIDENCE

All work stayed in the current worktree. No forbidden data path or outcome artifact was opened.

```text
$ git rev-parse origin/main
8fda4f8779639ec571f02ef5e9689d34b14d48cd

$ cat /Users/chriswong/.claude/projects/-Users-chriswong-Documents-Cluade-Macro-Dashboard/memory/MEMORY.md
cat: .../MEMORY.md: No such file or directory

$ python3 -m pytest tests/test_intelligence_vector_units.py -q -p no:cacheprovider
.........                                                                [100%]
9 passed in 1.28s

$ grep -RInE 'historical_event_set|event_set_reconstruction|reconstruct.*event.*set' \
  engine/prophet_lab app/prophet_lab.py tests/test_prophet_lab.py tests/test_prophet_lab_api.py
engine/prophet_lab/intelligence_vector.py:1011: ...
engine/prophet_lab/intelligence_vector.py:2235: ...
engine/prophet_lab/intelligence_vector.py:2241: ...
tests/test_prophet_lab.py:1892: ...

$ grep -RInE 'PROPHET_US_SOURCE_RIGHTS_REGISTER|internal-only|not-a-source|user-facing-with-limits' \
  engine/prophet_lab app/prophet_lab.py
<no matches; rc=1>

$ grep -RInE 'PUBLIC_INFO_REPLAY|observed-as-run|observed_as_run|retrospective|evidence_class' \
  engine/prophet_lab app/prophet_lab.py
engine/prophet_lab/observation.py:6-14: unrelated retrospective_seed board classification only
<no D5 adapter/route evidence-class matches>

$ grep -RInE 'view.*original|view.*current|original_view|current_view' \
  engine/prophet_lab app/prophet_lab.py tests/test_prophet_lab_api.py
engine/prophet_lab/response.py:178: unrelated diagnostic comment
engine/prophet_lab/boards.py:210: unrelated board current/closed split
<no detail-route view matches>
```

Source and prior-record reads used `git show 8fda4f8779...:<path>` plus targeted `nl -ba | sed -n` ranges; the census did not open `data/prophet/**`, `data/prophet_arena/**`, `data/prophet_stage_shadow/**`, `data/trial_ledger*`, or any outcome artifact.

## NOT_ESTABLISHED

- Whether any historical event set can be reconstructed for a particular old episode: D5 is explicitly current-generation-only and this read-only census did not opt into or inspect `data/`; only the code limitation is established.
- Whether transcript guidance comes from a rights-cleared subfamily in a particular workspace: the register is family-level and no runtime per-source contract exists.
- The final D07 designation, acquisition lag, or sensitivity analysis: D07 is open (`effective/DECISION_REGISTER.json:179-205@8fda4f8779`), so this census proposes plumbing but does not mint a class.
- Visual or browser usability: no UI was built or rendered; this card is a projection-contract census only.

## DEVIATIONS

- **Patch-tool runtime deviation.** The environment provided no `apply_patch` executable, although the developer instruction names it. The first two attempts therefore failed without creating the file; the closest one-command patch-compatible fallback (`patch -p0`) created the skeleton, followed immediately by commit, push, and draft PR #7850 as required. No other file changed. The first failed `git push` briefly created an empty remote branch at `origin/main`; the skeleton commit then fast-forwarded that same branch, so no force push or history rewrite occurred.
