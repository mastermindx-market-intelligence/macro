# Prophet US R6 wave-0 census C — Earnings/D5 dossier readiness (read-only)

Lane `pu_c_earnings`. Operation `prophet-us-fable-meta-ceo-20260923-001` (Macro #6805). Question: can the EXISTING Earnings/D5 evidence path deliver ONE real, source-backed issuer-event dossier (compatible observed quantities + typed absent expectations) through the real owner adapter — no new store, provider or model — and what exactly blocks it? Feeds D03/D07 and B08/B14 sequencing.

## SOURCE_SHA

`fc6db6c1f9a76cadc180c44e386ae928c1a9ccbc` — `git rev-parse HEAD`, detached, == `origin/main` after `git fetch origin`; subject `research(risk): reject expanding walk-forward probability refit (#7801)`, 2026-09-23 19:40:39 +0800. Citation convention below: `path:line@fc6db6c1f9a7` is the 12-char SOURCE_SHA form. Two other SHAs are cited where used: PR #7294 head `a3f3de78616a`, and E1P generation `f709a0a6ec514282d5769e7d`.

The worktree is SPARSE — `data/`, `mockups/`, `site/`, `verify_shots/` are not checked out (`scripts.worktree_sparse.missing_dirs()` → `['data', 'mockups', 'site', 'verify_shots']`). Nothing under `data/` was read or opted into; every claim needing a `data/` artifact is marked UNKNOWN with the missing artifact named.

**ONE-LINE VERDICT (OBSERVED).** Yes — exactly one real, source-backed issuer-event dossier is deliverable through the real owner adapter today: **AAPL FY2026 Q3** (`evt_cik0000320193_2026q3_results`) projects `COVERED / complete_allowlisted_owner_packet`, `decision_admissibility = ADMISSIBLE`, all three allowlisted lanes `PRESENT → PROJECTED`, carrying typed absent expectations for prior-period revenue and unlicensed consensus. The only injected seams are the owner's published marker and revision chain (`find_event_id`, `read_revisions`) — the two `data/`/R2 artifacts this sparse tree cannot reach. What blocks a *production* dossier is B1 episode population (#1) and the allowlist's one-issuer intersection with the real event population (#2) — not the adapter, not the identity bridge, and not the admission law, which are built, wired and tested.

---

## Q1 — The accepted D5 evidence allowlist, and the envelope-emitting adapter

**R6's statement is CONFIRMED, with two precisions.** (OBSERVED) The allowlist is exactly three owner lanes — `_OWNER_LANES = ("DELTA_REVENUE", "FACT_REVENUE", "GUIDANCE_REVENUE_YOY_PCT")` at `engine/prophet_lab/intelligence_vector.py:132-136@fc6db6c1f9a7` — projecting exactly three native metric ids: `fact:revenue` (`:870`), `guidance:revenue_yoy_pct` (`:885`), `metric_delta:revenue` (`:920`). The envelope is *closed* to one family: `validate_intelligence_vector` rejects any family count != 1 (`:1692-1693`) and any `evidence_family_id != "earnings.event"` (`:1695-1696`).

Precision 1 — "revenue-growth guidance" is specifically `metric == "revenue_yoy_pct"`, `unit == "percent"`, bounds `-100.0 .. 1000.0` (`:154-155`, `:528-539`), `status` in `{introduced, reiterated, raised, cut, withdrawn, absent}` (`:127`). Precision 2 — the accepted vocabulary is wider than "revenue" alone: `_DELTA_ABSENCE_REASONS` (`:128-131`) admits `not_available, consensus_unlicensed, no_span_addressable_evidence, missing_source, no_transcript, not_applicable, unknown`, and those typed absences ARE part of the delivered dossier (Q3 / §E7), not a failure of it.

Per-lane admission gates, all OBSERVED in code:
- **revenue fact** (`_candidate_fact` `:498-512`, `_accepted_fact` `:514-521`): `metric == "revenue"`; `unit in _REVENUE_UNITS = {"USD","usd_millions"}` (`:156`); value finite and in `[0, 1e15]` (`:153`, `_bounded_number` `:241-252`); `basis in {"reported","gaap"}`; EXACTLY ONE such fact in the workspace else the lane is refused (`:512`); and it must carry a span-addressable `source_span.document_id` passing `_safe_object_id` (`:494-496`, `:229-240`).
- **revenue delta** (`_candidate_delta` `:567-611`): `schema == "metric_delta.v1"`, `metric == "revenue"`, and `basis_match is not False` → **skipped**, i.e. only `basis_match: False` is ever admitted (`:577`); `current` must equal the accepted fact's value, unit AND basis (`:588-591`); `prior` AND `consensus` must both be typed absences with an allowlisted reason (`:556-565`).
- **guidance** (`_candidate_guidance` `:523-543`, `_accepted_guidance` `:545-553`): exactly one row, both bounds in range, `unit == "percent"`, `status` in the enum, plus a span-addressable document id.
- Field paths are separately allowlisted by regex `_FIELD_PATH_RE` (`:103-108`), and `_FORBIDDEN_KEYS` (`:66-70`) bans `score, rank, weight, confidence, conviction, evidence_count, entry_open, body, claims, transcript, private_path, path, url, workspace, source_span`.

**The adapter function that emits the evidence-family envelope.** (OBSERVED) `build_earnings_intelligence_vector(*, episode, episode_generation_id, episode_known_at, issuer_master, find_event_id=find_current_event_id_for_company, read_revisions=read_event_source_revisions) -> dict` — `engine/prophet_lab/intelligence_vector.py:1012-1020@fc6db6c1f9a7`. It delegates assembly to `_build_envelope` (`:957-1009`), which stamps `schema = "prophet.intelligence_vector/v1"` (`:39`), `adapter_set_version = "earnings-d5-adapter/1.0.0"` (`:41`), the single family from `_base_family` (`:451-491`; `owner_ref = "company_intelligence.event_workspace/v1"` at `:462`; family key set `_FAMILY_KEYS` `:58-65`), one semantic head `event_expectation` (`:987-990`), `fusion_bindings = []` (`:991`, enforced `:1690`), `authority = ALL_FALSE_AUTHORITY` (`:44-51`, `:992`, enforced `:1688`), and calls `validate_intelligence_vector(envelope)` before returning (`:1008`).

Inputs: a `prophet.candidate_episode/v1` mapping (schema checked `:1031-1032`, B1 identity checked `:1033` → `:260-292`); `episode_generation_id` matching `^peg:[0-9a-f]{64}$` (`:1029`, `:71`); `episode_known_at`, which must come from the B1 event stream (`:1034-1035`); an `issuer_master` exposing `cik_of_issuer` (`:1055`); and two injectable owner reads (`:1018-1019`).

As-of semantics: the decision cut is `episode["opened_at"]` (`:1037`) and it must EQUAL `max(structural_anchor.time, known_at)` exactly, else the build raises (`:1043-1049`). `decision_cut.tradable_at` is `NOT_ASSERTED` with basis `no_us_availability_owner_and_b4_not_built` (`:978-982`), per A8. The assembly receipt discloses its own limits (`:993-1004`): `source_reader: "read_event_source_revisions"`, `event_discovery_scope: "CURRENT_GENERATION_ONLY"`, `historical_event_set_reconstruction: False`, `identity_resolution_scope: "CURRENT_REGISTRANT_ONLY"`, `revision_visibility_scope: "ISSUER_RELEASE_SOURCE_HASH_ONLY"`, `revision_chain_bound_disclosure: "CALLER_INJECTED_READER_BOUND; OWNER_DEFAULT_MAX_HOPS=500"` (`:157-159`).

**What it emits when an adapter is UNBUILT — never zero, never neutral.** (OBSERVED) `research/prophet_v4/CONTRACT_AND_OWNER_MAP.md:53@fc6db6c1f9a7`: "**unbuilt specialist contract or unimplemented adapter** → family absent from `evidence_families[]`; readiness may be disclosed outside the envelope", reinforced at `:4` ("emits no placeholder family for an unbuilt adapter") and `:57` ("missing/not-covered/rights-blocked/stale/producer-degraded observations abstain from current E1 eligibility; they never become zero votes"). `:56` requires positive owner measurement under a named neutral definition before any `MEASURED_NEUTRAL`. The 2026-08-22 contract states the no-zero rule verbatim for the licensing case at `research/prophet_v4/flagship_cells/CELL_F_D5_EVIDENCE_TRANSLATION_AND_TRAJECTORY_CONTRACT_2026-08-22.md:694@fc6db6c1f9a7`: "Consensus is unlicensed in current production; therefore a beat/miss observation whose basis cannot be lawfully matched is **ABSENT**, with rights/coverage reason, not zero, neutral, or inferred from headline numbers." §16.4 `:708` adds "D5 emits no synthetic neutral and marks `NOT_COVERED`".

Mechanically, a BUILT adapter with no admissible evidence emits a typed absence, never a number: `_observation` forces `clean_value = None` whenever `value_state == "ABSENT"` (`:812-813`) and always sets `neutral_definition_ref: None` (`:834`); `_absence_observation` (`:932-948`) mints `native_metric_id = "earnings:event_workspace"`, `value_state = "ABSENT"`, `value = None`. The reason vocabulary is closed and each branch is a distinct typed state: `IDENTITY_UNRESOLVED` / `CONFLICTED` (`:1063-1072`), `UNESTIMABLE`+`CORRECTION_PENDING` on chain-integrity failure (`:1097-1099`, `:1143-1145`), `SOURCE_UNAVAILABLE` (`:1110`, `:1159`), `NOT_COVERED` (`:1119`, `:1169`), `UNKNOWN` with the missing clock NAMED (`:1197-1204`), `NOT_CAPTURED_AT_DECISION` (`:1225-1228`), `CONFLICTED` on an unbreakable clock tie (`:1252-1254`), `UNKNOWN` when no lane survives (`:1344-1348`).

**Production caller.** (OBSERVED) `app/prophet_lab.py:301-306@fc6db6c1f9a7` — route `GET /api/prophet/lab/v1/episodes/{episode_id}/intelligence` (docstring `:9-12`), site-full paywalled, failing closed to a 503 with a plain-sentence detail on any exception (`:309-321`).

---

## Q2 — The decision-time-safe read path, the admission conjunction, and the caller census

**The law.** (OBSERVED, quoted) `research/prophet_v4/flagship_cells/CELL_F_D5_CONTRACT_AMENDMENTS_2026-08-26.md:49-53@fc6db6c1f9a7` (A7 clause 1): "For any D5 **decision-time** observation in the Earnings family, the ONLY lawful access path is `read_all_event_source_revisions` / `read_event_source_revisions` …, which walks `previous_generation_id` and verifies each predecessor's bytes against `previous_manifest_sha256`." Clause 2 (`:54-62`) FORBIDS `read_event_workspace` and `read_current_event_workspace` "as the source of any decision-time observation BODY", permitting them only for "a separately and visibly labelled 'known now' research view, never `decision_admissibility = ADMISSIBLE`", and requires the non-point-in-time candidate-id SET limit to be "disclosed rather than silently inherited".

**The exact admission-conjunction lines.** (OBSERVED) Law — `CELL_F_D5_CONTRACT_AMENDMENTS_2026-08-26.md:63-78@fc6db6c1f9a7`, A7 clause 3: "**Admission is a CONJUNCTION over both clocks — never `source_available_at` alone.** A revision is admissible at cut `C` only if `source_available_at <= C` **AND** `observed_at <= C`; for a correction generation, also `generated_at <= C`." `:71-75` fixes the serialization of the `source_available_at <= C < observed_at` case: `value_state = ABSENT`, `absence_reasons = [NOT_CAPTURED_AT_DECISION]`, `decision_admissibility = AFTER_DECISION_CUT` — because §8.2's `value_state` is closed over `PRESENT | MEASURED_NEUTRAL | ABSENT`, "present but inadmissible" has no representation and must not be improvised. Clause 4 (`:79-84`) fixes selection: greatest `source_available_at`, tie-break greatest `observed_at`, else fail closed `CONFLICTED` — explicitly by clock, never by walk order or position. Clause 5 (`:85-93`) requires null/unknown clocks to be NAMED, never silently skipped. Clause 6 (`:94-105`) requires the typed `correction_lineage_state` (`OBSERVED | NONE_IN_CHAIN | NOT_OBSERVABLE`) and forbids rendering `NOT_OBSERVABLE` as "no correction". Clause 7 (`:106-113`) makes `WorkspaceChainIntegrityError` first-class and forbids falling back to `read_event_workspace`.

Implementation, verbatim — `engine/prophet_lab/intelligence_vector.py:1210-1215@fc6db6c1f9a7`:
```
admissible = [
    item for item in normalized
    if item["parsed"]["source_available_at"] <= cut
    and item["parsed"]["observed_at"] <= cut
    and item["parsed"]["generated_at"] <= cut
]
```
This is STRICTER than A7 clause 3, which conditions `generated_at <= C` on "for a correction generation"; the adapter applies it to every revision. Not a defect (a stricter gate cannot admit lookahead) but an undocumented divergence — carried as blocker #5.

Supporting lines: clock parsing and missing-clock collection `:1185-1195`; named-missing-clock refusal `:1197-1208`; the no-admissible-revision typed absence `:1216-1232` (`AFTER_DECISION_CUT` vs `UNVERIFIABLE` decided at `:1217`/`:1221`, reason at `:1226`); clock-ordered selection with `CONFLICTED` fail-closed `:1234-1258`; later-generation lineage `:1268-1307`; and the hard refusal when a "later" receipt's `generated_at` is not strictly after the cut `:1286-1295`. Owner side: the one-sided relation the owner actually enforces is `engine/company_intelligence/events.py:249-253@fc6db6c1f9a7` (`observed_at < source_available_at` → `EventError`), described at `:16-20` as "the point-in-time firewall"; the owner emits `None` clocks at `engine/company_intelligence/event_workspace.py:269-276@fc6db6c1f9a7`.

Reader seams: `read_all_event_source_revisions` `engine/neuralweb/company_intelligence_reader.py:1195@fc6db6c1f9a7`; `read_event_source_revisions` `:1304` (a thin single-event wrapper delegating to the former at `:1325-1327`, so both share ONE walk); `DEFAULT_MAX_CHAIN_HOPS = 500` `:912`; `WorkspaceChainNotPublished` `:885`; `WorkspaceChainIntegrityError` `:893`; `_receipt_from_revision` `:1150`; `_dedupe_carry_forward_hops` `:1181`; `find_current_event_id_for_company` `:1046`. The adapter binds the lawful reader as its DEFAULT (`intelligence_vector.py:25-31`, `:1019`).

**Caller census — does any current caller still use the forbidden pair for decision-time evidence? NO.** (OBSERVED; `grep -rn` across `app/ engine/ scripts/ lib/ worker/ collectors/ tools/ orch/ tests/`)

| Caller (production, non-test) | Line | Lane |
|---|---|---|
| `engine/prophet_lab/intelligence_vector.py` | `:1019` default binding, imported `:25-31` | `read_event_source_revisions` — D5 decision-time, the ONLY one |
| `scripts/refresh_event_workspaces.py` | `:824` | `read_event_source_revisions` — producer/refresh, not decision-time |
| `scripts/build_cycle_pattern_imce_prospective.py` | `:173` | `read_all_event_source_revisions` — IMCE prospective builder |
| `engine/company_intelligence/e3_shadow_compiler.py` | `:221` (labelled `:239-241`) | `read_event_workspace` — QA/calibration shadow, NOT decision-time |
| `app/company_intelligence.py` | `:631` loader, reached `:720` | `read_current_event_workspace` — public "known now" glance |
| `engine/security_state.py` `:646`,`:701`; `scripts/build_stock_library.py:4824`; `scripts/build_cycle_pattern_imce_prospective.py:141`,`:203`; `scripts/refresh_event_workspaces.py:493`,`:504` | — | `load_current_workspace` / `load_workspace_with_disposition` — a THIRD current-body seam A7 does not name |

`read_event_workspace` has exactly ONE production call site: `engine/company_intelligence/e3_shadow_compiler.py:221@fc6db6c1f9a7`, a QA/calibration shadow compiler whose own docstring says calibration "is bound to the frozen source SHAs, not to whatever generation the current marker now names" (`:216-218`). It emits no D5 family and no `decision_admissibility`. `read_current_event_workspace` has exactly ONE production caller: `app/company_intelligence.py:631@fc6db6c1f9a7` (lazy loader `_read_current_event_workspace` `:627-631`), reached from the public dossier glance route at `:720`. That IS the "known now" view A7 clause 2 permits, and it is visibly labelled and fail-closed: 429 with a plain retry sentence (`:713-719`), 503 detail "Verified event temporarily unavailable." (`:722-727`), and the payload is reduced through `_public_workspace_glance(result)` (`:729`) rather than returned as a body. No decision-time claim is made from it. The third seam is `load_current_workspace` (`company_intelligence_reader.py:1006`) / `load_workspace_with_disposition` (`:1022`, three-way `found | not_published | fetch_failed`); none of its callers feeds a D5 family, but it is flagged because A7 clause 2's list is now incomplete as a *grep target* — a builder told "don't call `read_event_workspace`" can still reach a current body there (blocker #10).

Test callers of the forbidden pair, listed for completeness (none decision-time): `tests/test_company_intelligence_event_workspace.py:246,254,256,268,427,518,532,551,561,836,852,867`; `tests/test_refresh_event_workspaces.py:800`; `tests/test_fundamental_forensics_financial_statement_service.py:1084-1087`; `tests/test_company_intelligence_api.py:447,529,576,607,631,647,670` (monkeypatching the app's own loader).

**A7-violating precedent still live, outside D5.** (OBSERVED) `scripts/build_cycle_pattern_imce_prospective.py:230-245@fc6db6c1f9a7` admits on `source_available_at` ALONE (`if dt > cutoff: continue`) and silently skips a null clock (`if not src: continue`) — the exact one-sided admission A7 clause 3 calls lookahead, and the exact silence clause 5 forbids (named at amendments `:91-93`). A7 clause 4 endorses this file's *ordering discipline* only. It is not a D5 caller, so it is not a D5 violation; recorded because B08/B14 sequencing must not copy it.

**A7's mandated acceptance test EXISTS and passes.** (OBSERVED) `tests/test_company_intelligence_workspace_chain.py:618-628@fc6db6c1f9a7` wires the REAL reader (`reader.read_event_source_revisions(event_id, base_url=BASE)`) into `_d5_project`, with the chain served from locally minted generations rather than a stub. Cases: two-generation chain with disagreeing facts driven to a 200 through the production route — `:1180` (`test_d5_body_only_decision_to_issuer_release_is_observed_and_endpoint_200`); body-only collapse to `NOT_OBSERVABLE`, never "no correction" — `:1353`; `source_available_at <= cut < observed_at` → `AFTER_DECISION_CUT` + `["NOT_CAPTURED_AT_DECISION"]`, asserted `:1399-1402` — `:1386`; missing clock typed and NAMED, parametrized over all three clocks — `:1405-1436`; equal clocks with distinct revisions → `CONFLICTED` — `:1444`; real-reader integrity failures never degrade to empty healthy evidence — `:1473`; chain-integrity → sanitized `UNESTIMABLE` receipt — `:1520`. Also `tests/test_prophet_lab.py:2351` (receipt clock drift refused), `:3106`/`:3137` (a later correction/generation clock must be strictly after the cut), `:3460`/`:3482` (a distinct visible source may not be relabelled `NONE_IN_CHAIN`), and `:1123` (same issuer-release hash → `NONE_IN_CHAIN`, not `OBSERVED`).

---

## Q3 — Issuer events in COMMITTED fixtures/tests that could serve as the one real dossier

### 1. AAPL FY2026 Q3 — **REAL** — the one viable candidate (OBSERVED)
Files: `tests/fixtures/company_intelligence/aapl_fy2026_q3_ex99_1.htm` (173,484 B, the real 8-K Exhibit 99.1), `aapl_fy2026_q3.json.gz` (17,187 B, the real transcript), `aapl_fy2026_q3_filing.json` (673 B), `aapl_edgar_8k_collector_legacy.json` (143 B). Filing metadata, read in full from `aapl_fy2026_q3_filing.json`: cik `0000320193`, accession `0000320193-26-000018`, form `8-K`, filing_date `2026-07-30`, acceptance `2026-07-30T16:30:00Z`, report_date `2026-06-27`, `canonical_event_id evt_cik0000320193_2026q3_results`, real `sec.gov` exhibit and 8-K URLs, `cie_alias cie_98e318c37ec1a2a1f83c45e1`, `narrative_alias AAPL/2026Q3`, `public_slug aapl-2026q3-call-record`. Issuer Apple Inc., `cik:0000320193`. Fiscal period FY2026 Q3, calendar_end `2026-06-27`. Basis **gaap**. Currency/units **usd_millions**. Value `109417.0`. Constants: `engine/company_intelligence/event_workspace.py:114` (`AAPL_CALL_DATE`), `:116` (`FLAGSHIP_EVENT_ID`), `:117` (`LIVE_CIE_ALIAS`), `:176` (`apple_registry`), `:196` (`flagship_fiscal_period`).

Already proven in a committed test through the REAL owner producer: `tests/test_prophet_lab.py:1950-1988@fc6db6c1f9a7` (`test_real_owner_built_workspace_projects_release_fact_delta_and_guidance`), building via `_d5_real_owner_workspace()` `:1642-1671` → `build_event_workspace(registry=apple_registry(), …)`, asserting `fact:revenue == 109_417.0 / usd_millions`, `guidance:revenue_yoy_pct == {low 9.0, high 11.0}`, `trajectory PARTIAL` with `current.basis == "gaap"`, `coverage COVERED`, and release document id `disclosure_document_19a10f4c…ae0e`. My own independent in-memory re-run (§E7) reproduces it and adds fields the test does not assert: `decision_admissibility ADMISSIBLE`; lanes `[(DELTA_REVENUE, PRESENT, PROJECTED), (FACT_REVENUE, PRESENT, PROJECTED), (GUIDANCE_REVENUE_YOY_PCT, PRESENT, PROJECTED)]`; guidance low 9.0 / high 11.0 percent, horizon `FY2026 Q4`, status `introduced`; typed absent expectations `prior = {state ABSENT, reason no_span_addressable_evidence}` and `consensus = {state ABSENT, reason consensus_unlicensed}`; `correction = NONE / NONE / CURRENT`; `source_refs` object_ids `[disclosure_document_19a10f4c…, tx:AAPL/2026Q3]`; authority all-false; `assembly_receipt.source_reader = read_event_source_revisions`.

### 2. DHI / PHM / KBH / TOL — **REAL filings, but NOT viable for the D5 allowlist** (OBSERVED for DHI)
`HOMEBUILDER_TICKERS = ("DHI","PHM","KBH","TOL")` at `engine/company_intelligence/issuer_profiles.py:73@fc6db6c1f9a7`; CIKs `:68-71` (DHI `0000882184`, PHM `0000822416`, KBH `0000795266`, TOL `0000794170`); reporting currency `USD` (`:81`). Real committed Ex-99.1 exhibits with full SEC provenance (accession, filingDate, reportDate, period end, original filename) documented at `tests/test_issuer_profiles_a5a.py:9-40@fc6db6c1f9a7`, all under `tests/fixtures/company_intelligence/`: `dhi_fy2026q3_ex99_1.htm` (630,636 B; `0000882184-26-000092`, filed 2026-07-21, period end 2026-06-30), `dhi_fy2026q2_ex99_1.htm` (612,163 B; `0000882184-26-000062`, 2026-04-21, 2026-03-31), `phm_fy2026q2_ex99_1.htm` (255,014 B; `0000822416-26-000034`, 2026-07-22, 2026-06-30), `phm_fy2026q1_ex99_1.htm` (210,178 B; `0000822416-26-000021`, filed 2026-04-23 / report 2026-04-22, 2026-03-31), `kbh_fy2026q2_ex99_1.htm` (258,407 B; `0000795266-26-000060`, 2026-06-23, 2026-05-31), `kbh_fy2026q1_ex99_1.htm` (202,012 B; `0000795266-26-000037`, 2026-03-24, 2026-02-28), `tol_fy2026q3_ex99_1.htm` (470,459 B; `0000794170-26-000096`, 2026-08-18, 2026-07-31).

**DHI FY2026 Q3 projected through the real producer + real adapter (my run, §E6):** the owner emits revenue as a TYPED ABSENCE — `fact_revenue_gaap` with `typed_absence.reason = no_span_addressable_evidence`, detail "Exhibit 99.1 did not yield a GAAP revenue figure" (`engine/company_intelligence/event_workspace_build.py:285-297@fc6db6c1f9a7`); `guidance == []` because a homebuilder profile returns none (`:388-392`); and the delta's `current == null` (`:360-380`). The D5 result: all three lanes `ABSENT`, `coverage = {state UNKNOWN, basis exact_source_lineage_unavailable}`, one `ABSENT` observation with reason `UNKNOWN`, `trajectory NOT_APPLICABLE`. The facts the owner DOES extract are real but outside the allowlist and are dropped: `net_orders 23084` (current) and `23071` (prior-year same quarter), unit `homes`, basis "DHI quarterly net sales orders (homes), as disclosed in Exhibit 99.1"; `cancellation_rate 20.0` / `17.0`, unit `percent`, basis "cancelled sales orders divided by gross sales orders (DHI convention)"; `questions_count` typed-absent `no_transcript`. Those facts carry owner-native verbatim basis strings, not a GAAP/adjusted tag, and their units are homes and percent — so there is no currency unit to carry. INFERRED for PHM/KBH/TOL: the same zero-lane outcome, since all four share the profile seam that returns no guidance and the same generic revenue-figure binding; not individually run (NOT_ESTABLISHED #4).

### 3. SYNTHETIC (by file)
- `tests/test_prophet_lab.py:1541-1615@fc6db6c1f9a7` `_d5_workspace()` — a hand-authored `event_workspace.v1` for `evt_cik0000320193_2026q3_results`: revenue `109_417_000_000`, unit **USD**, basis **reported** (BOTH differ from the real producer's `usd_millions`/`gaap`), guidance 9.0–11.0 percent `introduced` horizon FY2026 Q4, delta `basis_match: False` with prior `not_available` and consensus `consensus_unlicensed`, `warnings ["consensus_unlicensed"]`, `generation_id "1"*24`, `generated_at 2026-07-30T20:04:00Z`. **SYNTHETIC** — the numbers mimic AAPL but the bytes are hand-written; this is the fixture behind most D5 validator tests.
- `tests/fixtures/company_intelligence/golden_corpus_issuers.v1.json` — 130 issuers with real tickers and names, but it self-declares in its own `note` field: "CIKs are SYNTHETIC but format-valid (see cik_synthetic)"; e.g. Apple Inc. carries `cik_synthetic: 1632770` against the real `320193`. **SYNTHETIC**, therefore unusable for D5's CIK-anchored join. Same family: `golden_corpus_documents.v1.json`, `golden_corpus_edgar_identity.v1.json`, `golden_corpus_v1_contexts.v1.json`, `golden_corpus_v1_manifests.v1.json`.
- `tests/fixtures/evidence_foundation/earnings_workspace_valid.json` — **NOT an event workspace**: `schema == "evidence_foundation.reference.v1"` and it has no `facts`/`guidance`/`deltas` keys at all (top keys: schema, version, reference_id, object_class, owner_store, native_identity, native_schema, native_digest, coverage_class, subject, secondary_subjects, clocks, provenance, relations, missingness, correction, replay, authority, freshness, rights, authority_class). Not a D5 input. Same directory: `aapl_earnings_change_block_valid.json` is an evidence-foundation block, not an `event_workspace.v1` (field-level content not opened — NOT_ESTABLISHED #6).
- `tests/fixtures/earnings_release/ex99_1_release.htm` and `ex99_1_release_tampered.htm` (43,007 B each) — release-binding fixtures for `engine/earnings_release`, the tampered twin existing for hash verification. Provenance is not stated in the fixture: **UNKNOWN whether REAL or SYNTHETIC**. Either way they are not `event_workspace.v1` bodies and cannot serve as a D5 dossier.

### 4. Real event population under `data/` — **UNKNOWN** (sparse-omitted)
The producer's output root is `data/company_intelligence` (`scripts/refresh_event_workspaces.py:1346@fc6db6c1f9a7`); the published nest is keyed by `FLAGSHIP_EVENT_ID` (`:1345`) plus every homebuilder event, seeded by unconditional carry-forward (`:1430`) and updated per triggering ticker (`:1482`). The D5 route's production inputs are `data/us_prophet_rank/episodes` and `data/reference/security_master.parquet` (`app/prophet_lab.py:64-65@fc6db6c1f9a7`). All three are ABSENT in this worktree (§E8). **Missing artifacts:** `data/company_intelligence/` generation manifests + current marker (the real event_id set, generation ids, and the two lifecycle clocks); `data/us_prophet_rank/episodes/` (a real B1 generation and episode); `data/reference/security_master.parquet` (whether `issuer_cik` is actually populated for `ISS:US:320193`, which is what `cik_of_issuer` reads).

Historical measurement, not mine — `CELL_F_D5_CONTRACT_AMENDMENTS_2026-08-26.md:148-151@fc6db6c1f9a7`: measured 2026-08-26 against live production, `read_event_source_revisions("evt_cik0000320193_2026q3_results")` returned exactly ONE revision, `lifecycle_state = "complete"`, `source_available_at = 2026-07-30T20:30:28Z`. That clock DIFFERS from the committed fixture's `2026-07-30T16:30:00Z` — a live-vs-fixture divergence to disclose, not to reconcile here. Owner workstream state: `agentos/workstreams/WS-EARNINGS-INTELLIGENCE-OS.md:9@fc6db6c1f9a7` (`status: done`), `:63-68` (E1P done, "Live on generation `f709a0a6ec514282d5769e7d`"), `:74-81` (E2-D landed; public AAPL dossier v2 on that generation), `:16-19` (`next_action`: return to Sol for E3; do not begin E3 from this record). Two `do_not_redo` entries (`:37-46`) bear directly on this census: "Publish E1 test fixtures as production event_workspace truth" (`:42`) and "Treat a production-shaped reader test as proof the R2 object exists" (`:41`) — which is why §E6/§E7 are reported as adapter-proof, not as proof a published R2 object exists.

---

## Q4 — Where an explicit financing / per-share scenario would attach today

**NONE.** (OBSERVED) There is no field, owner or lane in the D5 envelope where a sector-economics → issuer-funding-schedule → original-share-value scenario can attach, and three independent bars exist. (1) The envelope is closed to one family — `intelligence_vector.py:1692-1696@fc6db6c1f9a7`; `_FAMILY_KEYS` (`:58-65`) contains no share-count, denominator, financing, runway or capacity field, and `_FORBIDDEN_KEYS` (`:66-70`) bans `score/rank/weight/confidence/conviction`. (2) The allowlist is revenue-only — `_OWNER_LANES` `:132-136`; `_candidate_fact` refuses any `metric != "revenue"` (`:501`). (3) The contract prohibits it explicitly — `CELL_F_D5_EVIDENCE_TRANSLATION_AND_TRAJECTORY_CONTRACT_2026-08-22.md:700@fc6db6c1f9a7`: D5 "must not mint the proposed generic `company_event.v1`, choose a 'current' share denominator, or manufacture fully diluted supply/runway/remaining-capacity fields that W4–W6 have not yet established."

**Nearest owner (existing — do NOT design a new store): Capital Structure.** `CELL_F_D5_EVIDENCE_TRANSLATION_AND_TRAJECTORY_CONTRACT_2026-08-22.md:698@fc6db6c1f9a7` names the source owner as `capital_structure.event.v1` plus immutable event versions/edges. The D5 row for that family already reserves the right vocabulary — Delta "amendment/issuance/share-count change", Persistence "active shelf/ATM/instrument life" (`:622`) — and `:702` states acceleration and financing-pressure decay are `NOT_APPLICABLE` or `ACCRUING` "unless the source owner later defines them". Runtime, all under `engine/capital_structure/`: the share-denominator truth plane `share_count_truth.py:28-33@fc6db6c1f9a7` (`capital_structure.share_count_observation.v1`, `…companyfacts_source_receipt.v1`, `…companyfacts_source_snapshot.v1`, `…share_count_snapshot_fact_observation.v1`, `…share_count_ledger.v1`, `…share_count_ledger_receipt.v1`), with `share_count_materializer.py`, `share_count_publication.py`, `share_count_retention.py`, `share_count_r2_concurrency.py`, `share_count_r2_conformance.py`; event/instrument planes `event_spine.py`, `event_versions_io.py`, `projection.py`, `verified_projection_generation.py`, `instrument_candidates.py`, `covenant_terms.py`, `document_terms.py`, `registration_lifecycle.py`, `companyfacts_authenticated_read.py`, `sec_discovery_clock.py`, `source_ledger_io.py`, `source_store.py`, `source_identity.py`; store root `config.data_dir()/"capital_structure"` (`biocatalyst_pit_adapter.py:63`, `spine_paths.py:16`); and an existing PIT read contract to model a D5 adapter on — `biocatalyst_pit_adapter.py:32-33` (`biocatalyst_capital_structure_pit_adapter.v1` / `biocatalyst_capital_structure_pit_read.v1`), `:175` (`read_biocatalyst_capital_structure_pit`), `:268` (`validate_capital_structure_pit_read`).

Two sub-questions have NO owner anywhere. **"Sector economics"** — the only sector-shaped axes in the estate are Context Vector's flattened `sector__*` columns, which sit on D5's prohibited-copy list (`CELL_F_D5_EVIDENCE_TRANSLATION_AND_TRAJECTORY_CONTRACT_2026-08-22.md:662@fc6db6c1f9a7`), and Context Vector is REUSE-UNCHANGED with zero authority for D5 (`research/prophet_v4/CONTRACT_AND_OWNER_MAP.md:33@fc6db6c1f9a7`); nearest owner is `WS:GMI-THEME-GRAPH` (`CONTRACT_AND_OWNER_MAP.md:13`), whose `theme_state/v1` is still unbuilt (`:46`). **"Original-share value"** (a per-share valuation quantity) — no per-share field exists in D5, and D5's authority block is all-false (`:44-51`, `:992`, enforced `:1688`) so it cannot originate a value; the nearest lawful attach point is a Capital Structure family envelope carrying an owner-native per-share fact, which requires (a) the owner defining it, (b) a D5 Capital Structure adapter, and (c) a contract amendment lifting `intelligence_vector.py:1695-1696` and `:700`. That is design work, explicitly out of scope for this census.

---

## Q5 — Blockers, ranked, each with owner and the smallest next bounded unit

1. **No real B1 episode generation is reachable, so the production D5 route cannot resolve an episode.** Owner: `WS:PROPHET-US-V4-RECOVERY` (`CONTRACT_AND_OWNER_MAP.md:19@fc6db6c1f9a7`). The route reads `data/us_prophet_rank/episodes` (`app/prophet_lab.py:64`) and fails closed without configured roots (`:276-277` → 503 `:315-321`). A11 status is MERGED / **BUILT_NOT_PROVEN**, clearing only on natural-production acceptance from the first qualifying ordinary scheduled `daily.yml` run — "not by dispatch, rerun, replay, or report mode" (`CELL_F_D5_CONTRACT_AMENDMENTS_2026-08-26.md:296-302`), with the load-bearing caveat that a run whose head SHA predates the B1 merge does not qualify (`:304-309`). The nightly writer step IS present now: `.github/workflows/daily.yml:5715` ("Prophet B1 — reconcile canonical candidate episodes (immutable generation + atomic HEAD)"), `:5727` (`python -m scripts.reconcile_us_candidate_episodes --nightly`), `:5800` (`git add data/us_prophet_rank/episodes`). Missing artifact: a published generation under `data/us_prophet_rank/episodes/`. **Smallest next bounded unit:** one read-only probe from a full checkout or the deploy box recording generation_id, episode count, and whether any episode's `company_id` resolves through `security_master` `issuer_cik`. No dispatch, no rerun, no replay.
2. **The D5 allowlist intersects the real event population at exactly ONE issuer.** Owner: `WS:EARNINGS-INTELLIGENCE-OS` (owns `engine/company_intelligence/**`, `agentos/workstreams/WS-EARNINGS-INTELLIGENCE-OS.md:20-26`). OBSERVED: AAPL projects all three lanes (§E7); DHI projects zero (§E6). The generic producer tries GAAP revenue for every issuer (`event_workspace_build.py:271`) but the homebuilder exhibits yield a typed absence (`:285-297`) and their profiles return no guidance (`:388-392`); the real facts those filings DO carry (`net_orders`, `cancellation_rate`) are outside the allowlist and are dropped. **Smallest next bounded unit:** a read-only per-exhibit census of the existing `figure("revenue", basis="gaap")` binding over the seven committed homebuilder exhibits, recording hit/miss and the miss reason — no new extractor, no allowlist change.
3. **Consensus estimates are unlicensed, so beat/miss is permanently ABSENT — and the family's `rights` block does not say so.** Owner: `WS:EARNINGS-INTELLIGENCE-OS` + rights governance. `basis_match: True` is refused outright and `beat`/`miss` keys are forbidden unless basis_match is true (`CELL_F_D5_CONTRACT_AMENDMENTS_2026-08-26.md:317-320`, citing `event_workspace.py:341-344`); the producer always emits `basis_match: False` with a `consensus_unlicensed` warning (`event_workspace_build.py:360-380`, `:398`); the contract rules the observation ABSENT "not zero, neutral, or inferred from headline numbers" (`CELL_F_D5_EVIDENCE_TRANSLATION_AND_TRAJECTORY_CONTRACT_2026-08-22.md:694`). Disclosure gap (OBSERVED): the family's `rights` is hardcoded `{"state": "ALLOWED", "profile_ref": "event_workspace.v1:derived_only"}` (`intelligence_vector.py:470`) and is never varied on any branch; the licensing block travels only as an `owner_warnings` string (`:1408-1410`) and the delta's typed consensus absence (`:556-565`, `:129`). **Smallest next bounded unit:** a doc-only adjudication of whether a family-level rights STATE must reflect `consensus_unlicensed`, or whether owner_warnings + typed absence is the accepted representation.
4. **The A13 identity-bridge blocker is CLOSED but its text still says UNRESOLVED.** Owner: Data OS spine (`CONTRACT_AND_OWNER_MAP.md:11`). A13 clause 1 states "The canonical reader does not expose it… Until that exists, the join is **UNRESOLVED**" (`CELL_F_D5_CONTRACT_AMENDMENTS_2026-08-26.md:363-369`) — now FALSE: `IssuerMaster.cik_of_issuer` exists at `lib/dataos/identity.py:929-946@fc6db6c1f9a7` (refuses rather than guesses on conflicting CIKs, `:941-945`; documented as current-registrant-only with no `asof`, `:930-936`), is consumed at `intelligence_vector.py:1055-1057`, and is proven by `tests/test_prophet_lab.py:2004-2017` (identity resolved BEFORE discovery) and `:2020-2030` (unresolved identity never discovers, never claims healthy-empty coverage). A13 clause 2's limit STANDS and is disclosed as `identity_resolution_scope: CURRENT_REGISTRANT_ONLY` (`intelligence_vector.py:999`). **Smallest next bounded unit:** a one-line amendment note recording clause 1 as closed by `cik_of_issuer`, leaving clause 2 as the surviving disclosure.
5. **Clock degradation, plus an undocumented strictness divergence in the adapter.** Owner: `WS:EARNINGS-INTELLIGENCE-OS`. `generated_at` collapses onto both lifecycle clocks on the live object, and equality is "a measurement degradation to disclose, not evidence that the clocks agree" (`CELL_F_D5_CONTRACT_AMENDMENTS_2026-08-26.md:75-78`, `:131-134`); the conjunction defect is therefore LATENT today. OBSERVED in my own run (§E7): the real producer set `generated_at == observed_at == 2026-07-30T20:03:00Z`. Separately, the adapter requires `generated_at <= cut` for EVERY revision (`intelligence_vector.py:1210-1215`) where A7 clause 3 conditions it on "for a correction generation" (`:63-65`) — stricter, so safe, but undocumented. **Smallest next bounded unit:** a doc-only ruling on whether the unconditional `generated_at <= cut` is intended, plus a note that the clock collapse persists.
6. **No real correction chain exists, so the correction path is unexercised in production.** Owner: `WS:EARNINGS-INTELLIGENCE-OS`. `CELL_F_D5_CONTRACT_AMENDMENTS_2026-08-26.md:147-159`: no published event carries a multi-generation chain, `DEFAULT_MAX_CHAIN_HOPS = 500` so the walk is not bounded early, and a builder developing against live data "would never meet a correction". Clause 6 (`:94-105`) compounds it — `_receipt_from_revision` derives `source_sha256` ONLY from a `kind == "issuer_release"` source (`company_intelligence_reader.py:1150`) and `_dedupe_carry_forward_hops` collapses consecutive identical hashes (`:1181`), so a body-only correction is invisible to the only permitted reader → `NOT_OBSERVABLE`, which must never render as "no correction". Covered in tests (`tests/test_company_intelligence_workspace_chain.py:1353`), not in production. **Smallest next bounded unit:** none for wave-0 — carry the disclosure.
7. **The rights/coverage registry row for Earnings is stale.** Owner: `WS:PROPHET-US-V4-RECOVERY` (doc). `research/prophet_v4/SOURCE_RIGHTS_AND_COVERAGE_REGISTRY.md:50@fc6db6c1f9a7` still reads "E0 in progress; E1/E2 todo" and publishes the earnings family as `ACCRUING` (null_reason `canonical_event_workspace_not_live`), contradicting `agentos/workstreams/WS-EARNINGS-INTELLIGENCE-OS.md:9`, `:63-68`, `:74-81`. The same row carries the hazard the adapter must not inherit: the Wire and Company-Intelligence planes disagree per-issuer (`DSC:EARNINGS-WIRE-AND-CI-DIVERGE-ON-THE-SAME-ISSUER`). **Smallest next bounded unit:** a doc-only correction of §4's status line and null_reason.
8. **A second, separate earnings source plane was restored one day before this census and is NOT the D5 source.** Owner: Prophet / EquityDesk lane. PR #7294 "fix(prophet): restore the governed EquityDesk earnings source on CI/deploy", MERGED 2026-09-22T19:47:18Z at head `a3f3de78616accd15f869316ee1e88e3af595330`, touching `engine/earnings_qual.py`, `engine/prophet_bridge.py`, `engine/prophet_stage_inputs.py`, `engine/prophet_stage_shadow.py`, `scripts/import_equitydesk_full.py`, `scripts/report_prophet_earnings_source.py`, `tests/test_prophet_earnings_source_restore.py`, `tests/test_prophet_earnings_split_brain.py` (§E4; also `docs/ACTIVE_BUILD_MAP.md:598@fc6db6c1f9a7`). It shares no code path with `event_workspace.v1` or the D5 adapter. Ranked as a blocker only for sequencing hygiene: D03/D07 and B08/B14 must not conflate the two planes — the precedents are `DSC:EARNINGS-WIRE-AND-CI-DIVERGE-ON-THE-SAME-ISSUER` and `DSC:TWO-CONSUMERS-OF-ONE-DATASET-DISAGREED-ABOUT-ITS-ADDRESS`. **Smallest next bounded unit:** name, in D03/D07, which plane each consumes.
9. **`fact:revenue` values are not comparable across issuers — units are admitted but never normalized.** Owner: `WS:PROPHET-US-V4-RECOVERY` (D5 contract). `_REVENUE_UNITS = {"USD", "usd_millions"}` (`intelligence_vector.py:156`) and `_bounded_number` (`:241-252`) scales nothing, so a raw-USD workspace and a usd_millions workspace are BOTH admitted and their values differ by 1e6. OBSERVED: the real producer emits `usd_millions` (§E7) while the synthetic fixture emits raw `USD` (`tests/test_prophet_lab.py:1555-1556`). `units` is carried per observation (`:826`), so this is a consumer-comparability hazard, not a correctness bug. **Smallest next bounded unit:** a doc-only ruling — normalize to one revenue unit, or forbid cross-issuer comparison of `fact:revenue` values.
10. **A7's clause-2 grep target is incomplete: a third current-body seam exists.** Owner: `WS:EARNINGS-INTELLIGENCE-OS` (reader) + V4 (contract text). `load_current_workspace` (`company_intelligence_reader.py:1006`) and `load_workspace_with_disposition` (`:1022`) return a CURRENT body and are not named in A7 clause 2; production callers are `engine/security_state.py:646`/`:701`, `scripts/build_stock_library.py:4824`, `scripts/build_cycle_pattern_imce_prospective.py:141`/`:203`. None feeds D5 today. **Smallest next bounded unit:** add both names to A7 clause 2's forbidden list (doc-only).
11. **No `agentos/handoffs/` record exists for #7294.** The spec's prescribed discovery command `grep -l 7294 agentos/handoffs/*.md` returns two files, but BOTH hits are coincidental digit substrings inside unrelated long numbers, not PR references: `agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-09-16-POST-7181-FOLD.md:407,418,549,649` (Sol root timestamps such as `1789590510.060009`, and child-root ids of the form `C0BSBM78V1N/1789590945.956889`) and `agentos/handoffs/FUNDAMENTAL-FORENSICS-2026-08-23-FF-1R-MANIFEST-TRANSPORT.md:76` (a sha256 fragment ending `4f7c97`). Neither file mentions PR #7294 or an earnings source restore. The real #7294 record lives at `docs/ACTIVE_BUILD_MAP.md:598`, `agentos/discoveries/DSC-A-MODULE-LEVEL-PATH-CONSTANT-ESCAPES-A-TEST-ROOT-PATCH.md:36`, `agentos/discoveries/DSC-TWO-CONSUMERS-OF-ONE-DATASET-DISAGREED-ABOUT-ITS-ADDRESS.md:55`, and `research/MASTERMIND_DATA_OS_V1_IMPLEMENTATION_PLAN.md:1504`. Missing artifact: an `agentos/handoffs/*` record for #7294. **Smallest next bounded unit:** none owed by this lane; recorded so a successor does not re-run the same dead grep.

**Non-blocker worth stating for B08/B14 sequencing.** D5 has zero authority by construction — `ALL_FALSE_AUTHORITY` (`intelligence_vector.py:44-51`), enforced at `:1688`, with `fusion_bindings` forced empty (`:991`, `:1690`). Per `CONTRACT_AND_OWNER_MAP.md:15@fc6db6c1f9a7`, "**D5 does not create Fusion votes:**" only an explicit binding to an accepted Conditional Fusion member/version makes an owner-native D5 observation eligible for E1. A delivered AAPL dossier is therefore display/reference work until that binding exists; it cannot move rank, gate, size or `ENTRY_OPEN`.

---

## EVIDENCE

All commands ran from `/Users/chriswong/lanes/wt/mo-ext-fix-pu_c_earnings` (this session worktree), read-only. No `engine/`, `scripts/`, `tests/`, `templates/`, `.github/` or `data/` file was modified; the only write is this record. No credential was read or printed. `gh` calls used: 2 of 12 allowed (`gh auth status`, `gh pr view 7294`); no CI polling; no full pytest suite; one test run at a time.

**E1 — SOURCE_SHA and sparse state.** rc=0.
```
$ git rev-parse HEAD
fc6db6c1f9a76cadc180c44e386ae928c1a9ccbc
$ git status --porcelain=v1 | head -20                       # (empty — clean tree)
$ git log -1 --format='%H %ci %s'
fc6db6c1f9a76cadc180c44e386ae928c1a9ccbc 2026-09-23 19:40:39 +0800 research(risk): reject expanding walk-forward probability refit (#7801)
$ git fetch origin -q && git rev-parse origin/main
fc6db6c1f9a76cadc180c44e386ae928c1a9ccbc
$ python3 scripts/worktree_sparse.py status | head -20
worktree-sparse: SPARSE checkout — omitting data, mockups, site, verify_shots
```

**E2 — the prescribed #7294 handoff grep, and why it is a dead end.** rc=0.
```
$ grep -l 7294 agentos/handoffs/*.md
agentos/handoffs/EXECUTIVE-CAPACITY-FABRIC-2026-09-16-POST-7181-FOLD.md
agentos/handoffs/FUNDAMENTAL-FORENSICS-2026-08-23-FF-1R-MANIFEST-TRANSPORT.md
$ grep -rn "#7294" . --exclude-dir=.git | head -10
./research/MASTERMIND_DATA_OS_V1_IMPLEMENTATION_PLAN.md:1504:   > **UPDATE 2026-09-18 (macro #7294).** …
./agentos/discoveries/DSC-A-MODULE-LEVEL-PATH-CONSTANT-ESCAPES-A-TEST-ROOT-PATCH.md:36:… PR #7294
./agentos/discoveries/DSC-TWO-CONSUMERS-OF-ONE-DATASET-DISAGREED-ABOUT-ITS-ADDRESS.md:55:… PR #7294
./docs/ACTIVE_BUILD_MAP.md:598:| #7294 | fix(prophet): restore the governed EquityDesk earnings source on CI/deploy | 2026-09-22 |
```

**E3 — production caller census (tails).** rc=0.
```
$ grep -rn "build_earnings_intelligence_vector" --include=*.py engine/ scripts/ app/ lib/ worker/ collectors/ | head
engine/prophet_lab/intelligence_vector.py:1012:def build_earnings_intelligence_vector(
engine/prophet_lab/intelligence_vector.py:2878:    "build_earnings_intelligence_vector",
app/prophet_lab.py:55:    build_earnings_intelligence_vector,
app/prophet_lab.py:301:        payload = build_earnings_intelligence_vector(
$ grep -rn "read_event_source_revisions\|read_all_event_source_revisions" --include=*.py . | grep -v '^./tests/'
./scripts/build_cycle_pattern_imce_prospective.py:173:    return ci_reader.read_all_event_source_revisions(event_ids)
./scripts/refresh_event_workspaces.py:824:        return list(ci_reader.read_event_source_revisions(event_id, base_url=base_url))
./engine/neuralweb/company_intelligence_reader.py:1195:def read_all_event_source_revisions(
./engine/neuralweb/company_intelligence_reader.py:1304:def read_event_source_revisions(
$ grep -rn "read_event_workspace\|read_current_event_workspace" --include=*.py app/ engine/ scripts/ lib/
app/company_intelligence.py:627:def _read_current_event_workspace(params: Mapping[str, Any]) -> Mapping[str, Any]:
app/company_intelligence.py:631:    return company_intelligence_reader.read_current_event_workspace(dict(params))
app/company_intelligence.py:720:        result = _read_current_event_workspace({"ticker": normalized})
engine/company_intelligence/e3_shadow_compiler.py:221:    result = reader.read_event_workspace({"event_id": EVENT_ID})
```

**E4 — PR #7294 metadata (1 `gh` call).** rc=0.
```
$ gh pr view 7294 -R mastermindx-market-intelligence/macro --json number,title,state,mergedAt,headRefOid,files
{"files":[".github/ci/legacy-jobs.yml",".github/workflows/daily.yml",
 "agentos/discoveries/DSC-A-MODULE-LEVEL-PATH-CONSTANT-ESCAPES-A-TEST-ROOT-PATCH.md",
 "agentos/discoveries/DSC-TWO-CONSUMERS-OF-ONE-DATASET-DISAGREED-ABOUT-ITS-ADDRESS.md",
 "engine/earnings_qual.py","engine/prophet_bridge.py","engine/prophet_stage_inputs.py",
 "engine/prophet_stage_shadow.py","research/MASTERMIND_DATA_OS_V1_IMPLEMENTATION_PLAN.md",
 "scripts/import_equitydesk_full.py","scripts/report_prophet_earnings_source.py",
 "tests/test_prophet_earnings_source_restore.py","tests/test_prophet_earnings_split_brain.py",
 "tests/test_prophet_stage_shadow.py","tests/test_prophet_stage_tilt.py"],
 "headRefOid":"a3f3de78616accd15f869316ee1e88e3af595330","mergedAt":"2026-09-22T19:47:18Z",
 "number":7294,"state":"MERGED",
 "title":"fix(prophet): restore the governed EquityDesk earnings source on CI/deploy"}
```

**E5 — named test runs (single files only; no full suite; one run at a time).** rc=0 each.
```
$ python3 -m pytest tests/test_prophet_lab.py -q -p no:cacheprovider -k "real_owner_built_workspace or d5 or D5"
1 passed, 252 deselected in 2.01s
$ python3 -m pytest tests/test_prophet_lab.py -q -p no:cacheprovider
253 passed in 1.05s
$ python3 -m pytest tests/test_company_intelligence_workspace_chain.py tests/test_prophet_lab_api.py -q -p no:cacheprovider
87 passed, 10 warnings in 3.60s
```
The 10 warnings are a pre-existing FastAPI duplicate-Operation-ID `UserWarning` originating in `app/paywall.py`, unrelated to this census; not fixed, not in scope.

**E6 — DHI FY2026 Q3 through the REAL owner producer and the REAL D5 adapter** (in-memory, nothing written to disk; real committed exhibit `tests/fixtures/company_intelligence/dhi_fy2026q3_ex99_1.htm`). rc=0.
```
EVENT_ID: evt_cik0000882184_2026q3_results
ISSUER: {"company_id": "cik:0000882184", "display_name": "D.R. Horton, Inc.", …}
FISCAL: {"year": 2026, "quarter": 3, "calendar_end": "2026-06-30"}
FACTS: {"fact_id":"fact_revenue_gaap","metric":"revenue","typed_absence":{"reason":"no_span_addressable_evidence",
        "detail":"Exhibit 99.1 did no[t yield a GAAP revenue figure]"}}
       {"fact_id":"fact_net_orders_current","metric":"net_orders","value":23084,"unit":"homes",…}
       {"fact_id":"fact_net_orders_prior_year","metric":"net_orders","value":23071,"unit":"homes",…}
       {"fact_id":"fact_cancellation_rate_current","metric":"cancellation_rate","value":20.0,"unit":"percent",…}
       {"fact_id":"fact_cancellation_rate_prior_year","metric":"cancellation_rate","value":17.0,"unit":"percent",…}
       {"fact_id":"fact_questions_count","metric":"questions_count","typed_absence":{"reason":"no_transcript",…}}
GUIDANCE: []
DELTAS: {"metric":"revenue","current":null,"prior":{"reason":"no_span_addressable_evidence",…}}
WARNINGS: ['collector_filing_unjoinable','consensus_unlicensed','reaction_not_joined','slides_absent','wire_record_not_found']
=== D5 PROJECTION ===
identity_state: RESOLVED | coverage: {"state":"UNKNOWN","basis":"exact_source_lineage_unavailable"}
point_in_time.decision_admissibility: ADMISSIBLE | missing_clocks: []
lanes: [DELTA_REVENUE ABSENT/ABSENT, FACT_REVENUE ABSENT/ABSENT, GUIDANCE_REVENUE_YOY_PCT ABSENT/ABSENT]
observations: [{"native_metric_id":"earnings:event_workspace","value_state":"ABSENT","value":null,
                "units":null,"absence_reasons":["UNKNOWN"]}]
trajectory: {"state":"NOT_APPLICABLE","dimensions":[]}
rights: {"state":"ALLOWED","profile_ref":"event_workspace.v1:derived_only"}
```

**E7 — AAPL FY2026 Q3 through the REAL owner producer and the REAL D5 adapter** (in-memory, nothing written to disk; real committed 8-K Ex-99.1 + real transcript + real EDGAR filing metadata, mirroring `tests/test_prophet_lab.py:1642-1671`). rc=0.
```
EVENT_ID: evt_cik0000320193_2026q3_results | generated_at: 2026-07-30T20:03:00Z
lifecycle: {"state":"complete","observed_at":"2026-07-30T20:03:00Z","source_available_at":"2026-07-30T16:30:00Z"}
REVENUE FACT: {"fact_id":"fact_revenue_gaap","metric":"revenue","value":109417.0,
               "unit":"usd_millions","period":"2026-06-27","basis":"gaap"}
GUIDANCE: [{"metric":"revenue_yoy_pct","low":9.0,"high":11.0,"unit":"percent",
            "horizon":"FY2026 Q4","status":"introduced","source_span":{"document_id":"tx:AAPL/2026Q3",…}}]
DELTA: {"schema":"metric_delta.v1","metric":"revenue",
        "current":{"value":109417.0,"unit":"usd_millions","basis":"gaap"},
        "prior":{"reason":"no_span_addressable_evidence","subject":"revenue_prior",…},"basis_match":False}
=== D5 PROJECTION ===
coverage: {"state":"COVERED","basis":"complete_allowlisted_owner_packet"} | decision_admissibility: ADMISSIBLE
lanes: [('DELTA_REVENUE','PRESENT','PROJECTED'),('FACT_REVENUE','PRESENT','PROJECTED'),
        ('GUIDANCE_REVENUE_YOY_PCT','PRESENT','PROJECTED')]
observations: [{"native_metric_id":"fact:revenue","value_state":"PRESENT","value":109417.0,
                "units":"usd_millions","absence_reasons":[],"correction_lineage_state":"NONE_IN_CHAIN"},
               {"native_metric_id":"guidance:revenue_yoy_pct","value_state":"PRESENT",
                "value":{"low":9.0,"high":11.0},"units":"percent","absence_reasons":[],
                "correction_lineage_state":"NONE_IN_CHAIN"}]
trajectory: PARTIAL | dimension REVISION_CHANGE / metric_delta:revenue,
            current {"value":109417.0,"unit":"usd_millions","basis":"gaap"},
            prior {"state":"ABSENT","reason":"no_span_addressable_evidence"},
            consensus {"state":"ABSENT","reason":"consensus_unlicensed"}
correction: {"state_at_decision":"NONE","later_revision_state":"NONE","current_state":"CURRENT"}
source_refs object_ids: ['disclosure_document_19a10f4c5c3120beb56ad21d812aa81582def5e564dbe8de7385266e7800ae0e',
                         'tx:AAPL/2026Q3']
authority: {"can_rank":false,"can_gate":false,"can_size":false,"can_originate_signal":false,
            "can_change_entry_open":false,"can_change_execution":false}
assembly_receipt.source_reader: read_event_source_revisions
```
Both probes injected ONLY `find_event_id` and `read_revisions`; the revision receipt was synthesized exactly as `tests/test_prophet_lab.py:1618-1639` does (`_canonical_bytes` + sha256 + byte count), and the workspace body itself came from the real owner producer. Identity resolution, the admission conjunction, allowlisting, lineage classification, trajectory, coverage and `validate_intelligence_vector` all ran the real code path.

**E8 — `data/` absence proof.** rc=0.
```
$ python3 -c "from pathlib import Path; [print(p,'->','EXISTS' if Path(p).exists() else 'ABSENT') for p in ['data/us_prophet_rank/episodes','data/reference/security_master.parquet','data/company_intelligence']]"
data/us_prophet_rank/episodes -> ABSENT
data/reference/security_master.parquet -> ABSENT
data/company_intelligence -> ABSENT
$ python3 -c "import scripts.worktree_sparse as w; print(w.missing_dirs())"
['data', 'mockups', 'site', 'verify_shots']
$ grep -n "_CANDIDATE_EPISODE_STORE_ROOT\s*=\|_SECURITY_MASTER_PATH\s*=" app/prophet_lab.py
64:_CANDIDATE_EPISODE_STORE_ROOT = _REPO_ROOT / "data" / "us_prophet_rank" / "episodes"
65:_SECURITY_MASTER_PATH = _REPO_ROOT / "data" / "reference" / "security_master.parquet"
```

---

## BLOCKED

Nothing blocked this census. Every spec item was answered from SOURCE_SHA or from a command I ran and captured. Two lanes were *unreachable by design* and are reported as UNKNOWN rather than BLOCKED, because the spec directs exactly that for `data/`-only artifacts:
- `data/company_intelligence/` — the published event-workspace nest (real event_id set, generation ids, the two lifecycle clocks). Sparse-omitted; not opted into, per lane instructions.
- `data/us_prophet_rank/episodes/` and `data/reference/security_master.parquet` — the B1 episode generation and the production `issuer_cik` population. Sparse-omitted.

No `engine/`, `scripts/`, `tests/`, `templates/`, `.github/` or `data/` file was modified. The two in-memory probes (§E6, §E7) imported production modules and wrote nothing to disk.

---

## NOT_ESTABLISHED

Each item names the missing artifact.

1. **Whether a real published event-workspace generation exists TODAY, and its clocks.** UNKNOWN — missing artifact: `data/company_intelligence/` generation manifests + current marker (or the R2 mirror the reader fetches). The only live measurement available is dated 2026-08-26 (`CELL_F_D5_CONTRACT_AMENDMENTS_2026-08-26.md:148-151`), and its `source_available_at` (`2026-07-30T20:30:28Z`) differs from the committed fixture's (`16:30:00Z`).
2. **Whether B1 has produced a natural-production generation since A11 was written.** UNKNOWN — missing artifact: `data/us_prophet_rank/episodes/`. The writer step exists (`.github/workflows/daily.yml:5715,5727,5800`) but its output is not in this tree, and CI was not polled (prohibited).
3. **Whether production `security_master.parquet` populates `issuer_cik` for `ISS:US:320193`.** UNKNOWN — missing artifact: `data/reference/security_master.parquet`. `cik_of_issuer` returns `None` when unobserved (`lib/dataos/identity.py:938-940`), which the adapter renders as `identity_state = UNRESOLVED` (`intelligence_vector.py:1063-1069`) — so a real production dossier could still fail at the bridge even though the bridge code is built and tested.
4. **PHM / KBH / TOL D5 projections.** INFERRED to be zero-lane like DHI (same profile seam, same generic revenue binding), NOT individually run. Missing artifact: nothing structural — only the three probe runs. Deliberately not run, to keep CPU modest; blocker #2's smallest next unit would establish all four at once.
5. **Whether `tests/fixtures/earnings_release/ex99_1_release.htm` is REAL or SYNTHETIC.** UNKNOWN — missing artifact: a provenance note in or beside the fixture (contrast `tests/test_issuer_profiles_a5a.py:9-40`, which documents accession numbers and fetch dates for every homebuilder exhibit). Either way it is not an `event_workspace.v1` body.
6. **Field-level content of `tests/fixtures/evidence_foundation/aapl_earnings_change_block_valid.json`.** UNKNOWN — not opened; it is an evidence-foundation block, not an event workspace, so it cannot be a D5 dossier input regardless. Missing artifact: none needed unless a later lane wants evidence-foundation blocks as D5 sources, which no current contract permits.
7. **Whether the live object's `generated_at` still collapses onto both lifecycle clocks.** UNKNOWN for the live object — missing artifact: a published generation's manifest. OBSERVED only for the fixture-built workspace, where the real producer set `generated_at == observed_at` (§E7), consistent with the degradation recorded at `CELL_F_D5_CONTRACT_AMENDMENTS_2026-08-26.md:131-134`.
8. **Whether A7's two-generation correction chain has ever occurred in production.** Not established and, per `CELL_F_D5_CONTRACT_AMENDMENTS_2026-08-26.md:147-159`, not expected: no published event carried a multi-generation chain at that measurement. Missing artifact: a real correction generation in `data/company_intelligence/`.
9. **Terminal-side rendering of a D5 dossier.** Out of this lane's scope and not investigated; the Terminal repository (`/Users/chriswong/Documents/Cluade/charting-app`) was not read. Missing artifact: a Terminal-side consumer of `GET /api/prophet/lab/v1/episodes/{episode_id}/intelligence`.
