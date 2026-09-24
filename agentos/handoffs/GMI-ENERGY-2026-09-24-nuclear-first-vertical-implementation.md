---
workstream: "WS:GMI-THEME-GRAPH"
session: claude/energy-nuclear-value-capture-impl
model: fable
ended_because: ci_handoff
mission: >
  Implementation carrier and cumulative working checkpoint for
  gmi-energy-fable-ceo-e2e-20260923-chairman-001: ship the first production-proven
  Nuclear Value Capture Energy vertical inside the existing GMI Themes workflow through
  the existing GMI / Company-Earnings / rights / F04 / private-publication / Macro-API
  owners, orchestrated by one Fable principal with bounded fabric children; then expand
  Energy (Power-Demand, hydrocarbons, renewables/storage, transition families, expectations
  overlays, sector projection) through the same accepted architecture.
state_before: >
  Research/design/plan/packet truth existed only on draft/HOLD PR #7791 at
  68e815d88fc8123a67167ae27b213078fe5339f7 (packet blob f628167227613175cc3ede088f40423add7252fb,
  checkpoint blob a710755c126fe23a0bad8d57f36f272dfd6f5d9b, design blob d6dac80bead5a028da8d757b419c896b1b8437ed,
  plan blob f7dc93621532b06e2478f90ef3876d6c31236242). No implementation carrier, no PICKUP_ACK,
  no START, no product code. Macro main at pickup d7711a0a08db8008ffe5975bfb3e6b242e4c70bd;
  carrier base (then-current main at branch creation) 33c73dd9f5e65936f0052cb28f4ece4880b51a43.
changed:
  - path: agentos/handoffs/GMI-ENERGY-2026-09-24-nuclear-first-vertical-implementation.md
    what: "Created the implementation-operation working checkpoint: pickup receipts, procedure pin, current-main/custody reconciliation, G1-G9 dispositions, Fable custody rulings R-ENE-01..06, frozen shared economic_change_dossier.v1 wire shape, frozen Energy adapter input types, witness identity/source-rights freeze, wave plan and exact next action."
  - path: research/energy/nuclear_program/rulings/R-ENE-2026-09-24-wave1.md
    what: "Citable seat rulings record for wave 1 (R-ENE-01..06) with the evidence each ruling rests on."
verified:
  - claim: "Current protected procedure is compatible and loaded from one pin."
    command: "cd Mastermind && git fetch origin master && git rev-parse origin/master; git show <sha>:docs/sol_skills/INDEX.md plus COLD_START, ACTIVE_EXECUTION, WEB_CEO_DELEGATION, RECONCILE_STATE, CLOSEOUT, COMMISSION_WAVE, WORKER_AVENUE_ROUTING, WATCHER_ACTION_LOOP, REVIEW_RETURN, docs/AGENT_DIALOGUE_SESSION_CLOSE_LAW.md, docs/EXECUTIVE_WORKER_ROUTING_CHAIRMAN_ADDENDUM.md at that sha"
    result: "Mastermind a7d2b3049e5cdc523e91e61a6e9d70a1cb911157; Skillpack mastermind.sol_skillpack.v1 1.0.1 / bootstrap 1; identical to the #7791 packet pin."
  - claim: "Delivered research pins match the live carrier."
    command: "gh pr view 7791 --json headRefOid; git rev-parse 68e815d8:agentos/handoffs/GMI-ENERGY-MASTER-FABLE-CEO-HANDOFF-2026-09-23.md 68e815d8:agentos/handoffs/GMI-ENERGY-RESEARCH-2026-09-23.md 68e815d8:docs/superpowers/specs/2026-09-23-energy-economic-change-dossier-design.md 68e815d8:docs/superpowers/plans/2026-09-23-energy-economic-change-first-vertical-implementation.md"
    result: "head 68e815d88fc8123a67167ae27b213078fe5339f7; blobs f6281672 / a710755c / d6dac80b / f7dc9362 as delivered; #7791 DRAFT, 0 comments before the ACK."
  - claim: "PICKUP_ACK is durably recorded on both carriers."
    command: "slack_send_message C0BSBM78V1N thread 1790224206.039539; gh pr comment 7791 --body-file ack_7791.md"
    result: "Slack reply ts 1790225775.934259; GitHub https://github.com/mastermindx-market-intelligence/macro/pull/7791#issuecomment-5807954708"
  - claim: "A real continuation watcher is armed on the exact Slack root and can read it."
    command: "mcp scheduled-tasks create_scheduled_task watch-gmi-energy-fable-ceo-e2e-20260923 (cron 23 * * * * local); list_scheduled_tasks; run_scheduled_task; list_task_runs; ccd list_events local_e3c5e245-9a11-43a2-998c-8d9a1f9ef71d"
    result: "cronExpression 23 * * * *, jitterSeconds 410, enabled true, nextRunAt 2026-09-24T05:29:50Z; first run succeeded (3 turns) and emitted NO_MATERIAL_CHANGE latest_ts=1790225775.934259."
  - claim: "No shared curation assertion or economic-change dossier contract exists on current main; nobody but Semiconductor B (#7870) holds an implementation carrier for the shared assertion."
    command: "ls contracts/theme_graph contracts/market_ontology; grep -rl curation_assertion|economic_change engine scripts app contracts templates tests .github; gh pr list --search 'economic_change_dossier OR curation_assertion OR market_ontology OR theme_graph'; git diff --stat origin/main...pr/7870"
    result: "contracts/market_ontology holds only exposure_map.v1; no code hit for either name; #7870 (Semiconductor B, Fable CEO f6dd4b82) carries engine/theme_graph/admission.py (new), rights.py (+86), guidance_history.py, tests; its checkpoint ruling R1 = B authors theme_graph.curation_assertion.v1 per Robotics names; T07/T08 = contracts/market_ontology/semiconductor_theme_research.v1.schema.json (domain-specific response), T09 = app/theme_research.py routes /api/themes/v1/research/{query,evidence}, T10 = site/assets/{js,css}/theme-research.* + state_of_themes/basket_detail mounts. #7793/#7773/#7788/#7796 carry research/design files only."
  - claim: "Sibling gates were refreshed at pickup."
    command: "gh api graphql (7 pullRequest nodes); gh api issues/7462/comments; issues/7669/comments"
    result: "#7462 draft@31706d73 (B's store.py custody question 5807268400 unanswered); #7664 ready@e43c7693; #7669 draft@2c28d950 (owner ruling 5807781684: ONE generic hidden research mount + shared theme-research asset includes approved on #7870, template byte-unchanged otherwise); #7777 ready@4122e3b7; #7773 draft@f1021165; #7793 draft@c120455b; #7788 draft@37436f8b; all OPEN/UNMERGED."
  - claim: "Witness identities resolve through accepted basket membership."
    command: "git show origin/main:data/baskets/membership.json | python3 (nuclear_power, uranium_miners); grep theme:nuclear_power config/theme_crosswalk.yml"
    result: "nuclear_power = CEG VST TLN NRG BWXT GEV OKLO SMR NNE; uranium_miners = CCJ UEC UUUU NXE DNN URG EU UROY LEU ASPI; crosswalk theme:nuclear_power primary nuclear_power, supplemental uranium_miners (ths 300238). BWXT/SMR/OKLO primary; CCJ/LEU supplemental."
  - claim: "Lane hosts and pools are available for wave 1."
    command: "ssh m1|mb|mini2 'ls ~/lanes/ext/active; uptime'; python3 $K/ext/pool_status.py"
    result: "05:01Z: m1 2/2 markers (load 7.5), mb 1/2 (load 3.3), mini2 0/2 (load 1.2); glm PASS, minimax DEMOTE (executor 0.10), cursor 0/3, grok 1/6."
unverified:
  - claim: "Semiconductor B's theme-research response envelope can carry a shared economic-change dossier section without a second route."
    what_would_verify: "B's T08/T09 landed shape on #7870 (schema semiconductor_theme_research.v1 top-level fields, /api/themes/v1/research/query request schema) read at its exact head; decision reserved to Task 7 (ruling R-ENE-04)."
  - claim: "The existing private publication family (engine/earnings_narrative/private_publication.py over engine/research_vault/r2_store) accepts a generic economic_changes role without an owner change."
    what_would_verify: "prepare_private_publication role vocabulary + B's R4 binding qualification outcome on #7870; Task 6 design read of validate_private_manifest/_artifact roles."
  - claim: "Real nuclear source bodies (S02 Cameco Q2 MD&A, S03-S07 Centrus, S08 BWXT, S09-S12 NuScale/Oklo) can be retained privately under the incumbent owner with production credentials."
    what_would_verify: "Task 10 admission run through the incumbent single-writer path with R2 credentials; EXACT_HUMAN_GATE if credentials are unavailable to the seat."
unresolved:
  - "#7462 has not answered B's one-line EVIDENCE_COLUMNS custody question; Energy never touches engine/theme_graph/store.py in wave 1, so this gates only Task 2 (consume-the-assertion) and Task 5's evidence refs."
  - "No accepted shared economic_change_dossier.v1 existed anywhere at pickup; ruling R-ENE-02 registers it from this carrier as the shared contract (custody notices on #7793 and #7870)."
  - "Route/private-role custody for Tasks 6-7 depends on B's T09 and R4 outcomes (see unverified)."
next_actions:
  - "Dispatch wave 1 on the fabric against carrier commit <this file's commit>: ene_w1_t3_adapter (mini2, glm-codex glm-5.3): contracts/market_ontology/economic_change_dossier.v1.schema.json + engine/market_ontology/energy_economic_change.py + tests + new gate:code job energy-economic-change-dossier; ene_w1_t4_witnesses (mini2, glm-5.3): engine/company_intelligence/nuclear_value_profiles.py + synthetic fixtures + source-qualification tests (no CI edits); ene_w1_t9_nonreg (mb, glm-5.3): tests/test_energy_economic_change_non_regression.py membership/ThemeState freeze (no CI edits)."
  - "Opus READ_ONLY audit of the frozen wire shape (section 5) and adapter laws (section 6) in parallel; fold accepted findings into the lane packets as repair rounds."
  - "Integrate accepted lane commits into this carrier by cherry-pick -x; seat wires the T4/T9 suites into the energy-economic-change-dossier job; rerun tests/test_ci_pack.py + scripts/check_contract_delta.py --base origin/main; push; independent exact-head review; mark ready + merge-on-green for slice 1 only after review PASS (ruling R-ENE-03)."
  - "Fresh-read the Slack root (and #7870/#7793/#7462/#7669 for custody answers) before every substantive write; keep store.py, basket_detail.html.j2, state_of_themes.html.j2, app/theme_research.py and private_publication.py untouched until their owners' state is reconciled."
  - "Wave 2 after slice 1: Task 2 (consume B's landed assertion), Task 5 (compose), Task 6/7 (private role + route, decision R-ENE-04), Task 8 (UI on B's generic mount), Task 9 privacy half, Task 10 real proof."
do_not_redo:
  - "Do not repeat R1-R6 research, the 78-requirement design, the 11-task plan or the first-vertical choice (Nuclear first, Power-Demand next)."
  - "Do not implement on #7791, #7870, #7793, #7773, #7788, #7796, #7462 or #7669; do not transplant their hunks."
  - "Do not create an Energy-specific graph, evidence ledger, assertion contract, energy_economic_change_dossier.v1, estimate warehouse, private bucket/pointer/publisher/scheduler, route family /api/energy/*, ranker, entry, sizing or trade authority."
  - "Do not re-adjudicate the resolved Cameco Q1/Q2 source-link mismatch (S01 excluded, S02 is the Q2 Fuel Services source), the EOG July-24 chronology or the EQT/CPV commencement semantics."
  - "Do not fork Semiconductor B's shared curation assertion or its generic theme-research client/mount into Energy variants; consume the accepted versions (rulings R-ENE-01, R-ENE-04)."
danger_areas:
  - "Macro is public: no full-fidelity paid research bodies, source PDFs, credentials or private production captures on this carrier; fixtures are SYNTHETIC and never copies of live Cameco/Centrus/BWXT/NuScale/Oklo values."
  - "A synthetic-fixture green is not native admission; a schema, a fixture pass, a page shell, green CI or a merge is not first-vertical completion (15-point law, packet section 16)."
  - "Supplemental uranium_miners membership must never be rendered or persisted as nuclear_power primary membership; basket co-membership is never a relationship edge."
  - "Unknown stays unknown, unavailable never becomes zero/false: expectations.status=UNAVAILABLE carries estimate=null; milestones (NuScale SDA E04, Oklo Groves criticality E05) never become operating/commercial generation; Centrus nested backlog (O05) is never summed; Westinghouse equity-method sales (O04) are never added to consolidated revenue."
  - "Fabric executor first-pass acceptance is low (glm-5.3 ~0.29 on the last 20): every child carries an executable deterministic gate (RED/GREEN/mutants) and gets independent review before integration; executor self-reports are navigation, not acceptance."
  - "This is a SPARSE worktree (data/, site/ omitted): never git add -A; a write under data/ or site/ truncates committed artifacts."
prs: [7791]
---

# GMI Energy — Nuclear Value Capture first vertical: implementation operation working checkpoint

OPERATION: `gmi-energy-fable-ceo-e2e-20260923-chairman-001`
PARENT RESEARCH OPERATION: `gmi-energy-sector-research-20260923-sol-001` (carrier #7791, research/design/plan only — HOLD, never product code)
RECEIVER: Claude Fable 5.1, Claude Desktop Code session `8955bbc3-eb16-43cb-b087-bf5cacf2ffcf`, account claude8, host Mac Studio (m2)
ASSIGNMENT EDGE: deliberate live Chairman delivery (DIRECT_TARGETED) 2026-09-24; PICKUP_ACK Slack `C0BSBM78V1N/1790224206.039539` reply `1790225775.934259` and #7791 comment 5807954708
PROCEDURE PIN: Mastermind `a7d2b3049e5cdc523e91e61a6e9d70a1cb911157`, Skillpack 1.0.1 / bootstrap 1
CARRIER BASE: Macro `main` `33c73dd9f5e65936f0052cb28f4ece4880b51a43` (branch `claude/energy-nuclear-value-capture-impl`)
STATE AT THIS COMMIT: `PICKED_UP`; `WATCH_ARMED` (native scheduled condition watch, first run proven); START emitted separately on the Slack root only after this carrier was pushed; `NUCLEAR_VALUE_CAPTURE: NOT_BUILT`; `MISSION_COMPLETE: false`; `EFFECT_UNKNOWN: none`.

## 1. Gate refresh at pickup (G1–G9)

| Gate | Disposition at this commit | Consequence for wave 1 |
|---|---|---|
| G1 store custody | #7462 OPEN/DRAFT @31706d73 holds `engine/theme_graph/store.py`; B's one-line EVIDENCE_COLUMNS question (5807268400) unanswered | Energy writes nothing under `engine/theme_graph/`; Task 2 frozen until B's T02 lands |
| G2 shared assertion | Not on main; Semiconductor B authors `theme_graph.curation_assertion.v1` on #7870 (its ruling R1, lane T02 in flight) | R-ENE-01: consume, never clone; Energy roles use synthetic typed inputs until landed |
| G3 shared dossier | Not on main; Technology #7793 proposes `economic_change_dossier.v1` (research only); B's T07/T08 schema is `semiconductor_theme_research.v1` (domain-specific) | R-ENE-02: this carrier registers the ONE shared `contracts/market_ontology/economic_change_dossier.v1.schema.json` (Technology's name, generic sections); notices on #7793 and #7870 |
| G4 sector dossier | #7777 ready@4122e3b7, unmerged | Optional; not consumed in the first vertical |
| G5 public builder | #7664 ready@e43c7693 touches `scripts/build_state_of_themes.py` | Never a private data plane; Energy does not touch it |
| G6 basket detail | #7669 draft@2c28d950; owner ruling 5807781684 approved ONE generic hidden research mount + shared asset includes on #7870 | R-ENE-04: Energy mounts inside B's generic mount when landed; no second mount, no template write in wave 1 |
| G7 company/private route | `app/earnings.py` (site_full + private headers) is the precedent; B's `app/theme_research.py` (T09) pending | R-ENE-04 reserved decision at Task 7; no route write in wave 1 |
| G8 rights | R1/R4 sources are locators + paraphrases only (register rights_policy); no retention rights established | R-ENE-05: synthetic fixtures; real admission = Task 10 through the incumbent owner (credential act) |
| G9 release | — | Slice-1 merge only after independent exact-head review + concluded green CI (R-ENE-03); first-vertical completion only by the 15-point law |

## 2. Seat rulings (citable as R-ENE-NN; record `research/energy/nuclear_program/rulings/R-ENE-2026-09-24-wave1.md`)

- **R-ENE-01 — shared curation assertion is consumed from Semiconductor B.** B's carrier #7870 ruling R1 makes B the author of the one shared `theme_graph.curation_assertion.v1` (Robotics names). Energy's Task 2 consumes the exact landed version; until then Energy roles are represented through synthetic typed inputs to the pure adapter and no real admission occurs. Energy provides its assertion requirements (ENE-04, 07–11, 22, 39–43, 56–62) to B by custody notice rather than authoring a variant.
- **R-ENE-02 — this carrier registers the shared `economic_change_dossier.v1`.** No accepted shared dossier contract exists and no implementation carrier holds one. The Energy seat, as a Fable CEO seat inside `WS:GMI-THEME-GRAPH`, registers `contracts/market_ontology/economic_change_dossier.v1.schema.json` under Technology's proposed name with the generic section set of #7793 §7 (scope, input receipts, clocks, definition, observation, comparison, mechanism, coverage, native context, authority, publication) expressed through the frozen wire shape in §5 below; domain vocabularies (role kinds, unavailable codes) are pluggable by `*_vocabulary` identifiers so Technology, Healthcare, Basic Materials, Robotics and Semiconductors consume it without an Energy flavour. The contract is *accepted* only when independently reviewed and merged; until then it is a candidate. Custody notices are posted on #7793 and #7870 before the first write.
- **R-ENE-03 — slice merges are permitted; completion is not implied.** Slice 1 (shared contract, pure Energy adapter, synthetic witness profiles, non-regression freeze) is decision-neutral, path-disjoint from every held sibling path and carries no live data; after independent review and concluded-green CI it may be merged so siblings consume an accepted contract and main stays proven. Later slices (private publication, route, UI, real proof) ride fresh carriers from then-current main. No merge is a first-vertical completion claim; completion is ruled only by the 15-point law.
- **R-ENE-04 — presentation and transport reuse B's generic surfaces.** Energy renders inside B's generic `theme-research.js/css` client and the #7669-approved generic hidden mount on `basket_detail.html.j2` plus the `state_of_themes.html.j2` entry once landed; Energy adds no second mount, client or stylesheet family. Transport is a reserved decision at Task 7: consume `/api/themes/v1/research/*` if B's landed envelope admits a dossier section keyed by the shared contract; otherwise register one shared generic `app/economic_change.py` route (never `/api/energy/*`).
- **R-ENE-05 — rights and fixtures.** Every fixture value is synthetic. Real source retention (S02 Cameco Q2 MD&A, S03–S07 Centrus, S08 BWXT, S09–S12 NuScale/Oklo) happens only through the incumbent private owner in Task 10 and is an `EXACT_HUMAN_GATE` if production credentials are unavailable to the seat. S01 (misdirected Q1 web highlight) is excluded per the resolved Q1/Q2 issue.
- **R-ENE-06 — routing.** Labor runs on the external fabric (`remote_lane_v8.sh`, glm-codex glm-5.3, hosts mini2/mb/m1 via the admission-wait dispatcher); Opus native children only as READ_ONLY auditors; the seat freezes interfaces, integrates by `cherry-pick -x`, wires CI, rules on returns and owns every carrier post, label, ready and merge act. WHY NOT FABLE for lanes: every wave-1 slice is fully specified below and passes the draft-and-review test.

## 3. Frozen witness identity and source table

| Witness | Security | Basket relation | Roles (R4 C0x) | Sources (R4 S/E) | Admitted facts in fixtures (synthetic values, real DEFINITIONS) |
|---|---|---|---|---|---|
| Cameco | `co:us:CCJ` | supplemental_member (uranium_miners) — never primary | uranium production/procurement; fuel services; equity-accounted Westinghouse (C01) | S02 (Q2 2026 MD&A, 2026-07-30); S01 EXCLUDED | O01 Fuel Services realized price vs unit cost (CAD/kgU, blended mix, cost includes depreciation); O02 Fuel Services revenue/EBT/adjusted EBITDA (CAD m); O03 sales classification fixed vs market (CAD k); O04 Westinghouse displayed revenue + full elimination (equity method) |
| Centrus | `co:us:LEU` | supplemental_member | fuel supply/trading; current technical services; future enrichment expansion (C02) | S03 Q2 (2026-08-05); S04/S05 offering (2026-09-09/11); S06 close (2026-09-15); S07 Antares (2026-09-17); S26 Radiant | O05 nested backlog total/LEU/technical/contingent/definitive-within-contingent — never summed, no funded remainder by subtraction; O06/O07 instruments (common, prefunded, warrant series strikes) — not present cash; E01 financing_close (net cash not established); E02 contract_signed (no delivered volume) |
| BWXT | `co:us:BWXT` | primary_member (nuclear_power) | government manufacturing; commercial components/services; medical perimeter (C03) | S08 Q2 (2026-08-03) | O08 segment revenue current/prior (USD m; consolidation needed; PCG acquisition E03 closed 2026-07-01, not in Q2, not organic); O09 government operating income current/prior |
| NuScale | `co:us:SMR` | primary_member | reactor technology; engineering/licensing; commercialization partner dependency (C04) | S09 Q2 (2026-08-05); S10 SDA; S11 product page | E04 standard_design_approval 2025-05-29 with `site_operating_license=false`; E06 commercial_negotiation with `definitive_ppa_established_by_source=false`; LWR fuel capability ≠ measured fuel consumption |
| Oklo | `co:us:OKLO` | primary_member | advanced nuclear development; isotope test-reactor milestone (C05) | S12 (2026-08-06) | E05 first_criticality 2026-08-06 (Groves test reactor) with `proves_aurora_grid_operation=false`; expectations UNAVAILABLE |

Identity binding: the five securities are current members of the accepted baskets (membership.json on the carrier base); node ids follow `engine.theme_graph.identity.COMPANY_ID_RE` (`co:us:<TICKER>`). Any source company that does not bind stays `identity_state=unresolved` with `security_link_allowed=false`.

## 4. Frozen wire shape — `market_ontology.economic_change_dossier/v1`

File `contracts/market_ontology/economic_change_dossier.v1.schema.json`; `$id` `https://mastermind-x.com/contracts/market_ontology/economic_change_dossier.v1.schema.json`; JSON Schema 2020-12; `additionalProperties:false` everywhere; conventions mirror `exposure_map.v1` (bilingual `{en,zh}` text, typed-null `unavailable` records, `authority_ceiling` const). Decimal values are JSON **strings** (no floats). Every list is ordered by its id, never by magnitude.

Top level (all required): `schema` const `market_ontology.economic_change_dossier/v1`; `definition_version` string (semver of the composer definition); `domain_profile` string (`energy` | `technology` | `healthcare` | `basic_materials` | `consumer_defensive` | `semiconductors` | `robotics` | `other`); `asof` date; `knowledge_cutoff` date (≤ asof); `authority_ceiling` const `research_display_only`; `display_only` const `true`; `authority` object with `can_rank`,`can_gate`,`can_size`,`can_originate`,`can_open_entry` each const `false`; `scope`; `subjects` (1..5); `roles` (0..12); `changes` (0..40); `bridge` (list); `capital_ownership` (list); `expectations` (list, one per subject); `counterevidence` (list); `relationships` (0..80); `coverage`; `unavailable` (list of typed nulls, may be empty); `provenance`.

- `scope`: `canonical_theme_id` string|null (`theme:` grammar); `primary_basket_id` string|null; `supplemental_basket_ids` [string]; `research_facet` {label bilingual, `authority` const `research_facet_only`, `source_refs` [string]}|null; `geography` string|null; `currency` string|null.
- `subject`: `subject_id` (`co:` grammar or `unresolved:<slug>`); `issuer_label` bilingual; `identity_state` enum `resolved|unresolved|ambiguous`; `basket_relation` enum `primary_member|supplemental_member|none|unknown`; `security_link_allowed` bool (must be false unless resolved); `structural_classification` {provider, version, code, label}|null.
- `role`: `role_id`; `subject_id`; `role_vocabulary` string (e.g. `energy_mechanism_families.v1`); `role_kind` string `^[a-z][a-z0-9_]{2,63}$`; `business_label` bilingual; `relationship_basis` enum `source_backed|hypothesis`; `source_refs` (≥1 unless status unavailable); `limitations` [string]; `status` enum `ready|degraded|unavailable|refused`.
- `change`: `change_id`; `subject_id`; `kind` enum `reported_measure|contract|financing|milestone|ownership_event|guidance|correction`; `status` enum `observed|forward|contingent|historical`; `clocks` {publication, observation, business_valid_from, business_valid_to, retention, review, recorded — each date|datetime|null}; `definition` {metric_id, label bilingual, unit, currency|null, scale|null, basis enum `reported|reported_terms|adjusted|proportionate|consolidated|common_shareholder`, perimeter string|null, period string|null, prior_period string|null}|null; `value` {kind enum `point|range|text|null`, point string|null, low string|null, high string|null, text string|null, precision int|null, preliminary bool}; `milestone_flags` object|null (closed keys: `site_operating_license`, `commercial_generation`, `operating_generation`, `included_in_period_revenue`, `future_warrant_cash_as_current`, `definitive_agreement_established`, `delivered_volume_known` — each bool|null); `rights_state` enum `admitted|restricted|unavailable`; `evidence_grade` enum (R5 grades) | null; `supersedes` change_id|null; `source_refs` [string]; `limitations` [string].
- `bridge_step`: `subject_id`; `step_kind` enum `demand|commercial_exposure|unit_economics|operating_contribution|capital_financing|ownership_claims|shareholder_cash`; `state` enum `observed|forward|unavailable|restricted`; `value_ref` change_id|null; `narrative` bilingual|null; `source_refs`; `assumptions` [string]. Missing steps are emitted as `unavailable`, never guessed.
- `capital_ownership` item: `subject_id`; `item_kind` enum `consolidated_vs_proportionate|project_vs_corporate_debt|common_vs_convertible_warrant|repurchase_authorized_vs_retired|customer_advance|sale_proceeds_vs_future_cash|contributed_asset|investee_equity_method`; `state`; `value_refs` [change_id]; `narrative` bilingual|null; `source_refs`.
- `expectation`: `subject_id`; `status` enum `AVAILABLE|UNAVAILABLE|RESTRICTED|INCOMPATIBLE`; `evidence_grade` enum `PRE_EVENT_TIMESTAMPED_VALUE|ISSUER_PROCESS_PLUS_ARCHIVE|ARCHIVAL_CONTEXT_ONLY|POST_EVENT_ONLY|UNAVAILABLE`; `metric_definition` string|null; `fiscal_horizon` string|null; `ownership_basis` string|null; `aggregate_method` string|null; `contributor_count` int|null; `panel_turnover` string|null; `estimate` {value string, unit, currency|null}|null; `first_known_at` datetime|null; `source_ref` string|null; `limitations` [string]. Rule: `status != AVAILABLE ⇒ estimate == null`.
- `counterevidence` item: `counter_id`; `subject_id`|null; `against_ref` (role_id | change_id | `bridge:<subject_id>:<step_kind>`); `kind` enum `demand_revised_lower|cost_outpaces_price|contingent_or_unfunded|existing_output_not_new_supply|temporary_item|acquisition_or_dilution|competed_away|test_asset_not_commercial|duration_costs_capital|already_public|missing_requirement|other`; `narrative` bilingual; `source_refs`; `state` enum `observed|hypothesis`.
- `relationship`: `relationship_id`; `src`, `dst` subject/role ids; `kind` enum `physical_containment|commercial_relationship|ownership|conditional_transmission_hypothesis|supply_exposure`; `basis` enum `source_backed|hypothesis`; `magnitude` null | {value string, unit, source_ref} (null unless comparable evidence); `source_refs`. Basket co-membership is never a basis.
- `coverage`: `subjects_selected`, `subjects_ready`, `subjects_unavailable`, `changes_admitted`, `changes_restricted`, `rights_blocked`, `unresolved_identities` ints; `generation` string (deterministic content fingerprint of inputs + definition_version).
- `unavailable` item: `code` enum `IDENTITY_UNRESOLVED|RIGHTS_RESTRICTED|SOURCE_UNAVAILABLE|PERIOD_MISMATCH|DEFINITION_INCOMPATIBLE|MILESTONE_NOT_OPERATING|CONTINGENT_NOT_FUNDED|EXPECTATIONS_UNAVAILABLE|EVIDENCE_GRADE_INSUFFICIENT|CONFOUNDED_EVENT|OVERSIZE_SELECTION|SUPERSEDED|CONFLICTING_SOURCES|PRIVATE_BINDING_UNAVAILABLE|AUTHORITY_BIT_REJECTED|ROLE_KIND_UNKNOWN|UNIT_INCOMPATIBLE`; `reason` bilingual; `subject_id` string|null; `detail` string|null.
- `provenance`: `composer` string (module.function); `engine_version` string; `input_receipts` [{owner, object, schema, version, digest, selector string|null, role}]; `interpretation_authorship` enum `deterministic|model_attributed`; `model_attribution` string|null.

Bounds: subjects ≤5, roles ≤12, changes ≤40, relationships ≤80; an oversize selection yields a dossier whose `unavailable` carries `OVERSIZE_SELECTION` and empty sections — never silent truncation; no pagination in v1.

## 5. Frozen Energy adapter (Task 3)

Module `engine/market_ontology/energy_economic_change.py`; pure; no clock, network, LLM, filesystem, store read or `data/` write; imports nothing from the scoring core; `role_vocabulary = "energy_mechanism_families.v1"` with the closed `ROLE_KINDS` = the 27 R6 §3.2 families as snake_case identifiers plus `other`. Public interface:

`compose_energy_profile(selection, *, owner_inputs, as_of, knowledge_cutoff) -> dict` (validates against the shared schema; raises `EnergyProfileError` only for caller-programming errors; every data-availability problem is a typed `unavailable` record).

Frozen input types (frozen dataclasses, `Decimal` for numbers): `EnergySelection(canonical_theme_id, primary_basket_id, supplemental_basket_ids, subject_ids, domain_profile='energy')`; `EnergySubject(subject_id, issuer_label_en, issuer_label_zh, identity_state, basket_relation, membership_receipt)`; `EnergyRole(role_id, subject_id, role_kind, business_label_en/zh, relationship_basis, source_refs, limitations)`; `EconomicChange(change_id, subject_id, kind, status, clocks, definition, value, milestone_flags, rights_state, evidence_grade, supersedes, source_refs, limitations)`; `EconomicBridgeStep(subject_id, step_kind, state, value_ref, narrative_en/zh, source_refs, assumptions)`; `CapitalOwnershipItem(...)`; `ExpectationContext(subject_id, status, evidence_grade, metric_definition, fiscal_horizon, ownership_basis, aggregate_method, contributor_count, panel_turnover, estimate, first_known_at, source_ref, limitations)`; `Counterevidence(...)`; `Relationship(...)`; `OwnerInputs(subjects, roles, changes, bridge, capital_ownership, expectations, counterevidence, relationships, input_receipts)`.

Fail-closed laws (each is a named test): non-finite or float numerics; incompatible units in a comparison; unknown `role_kind`; `basket_relation` inconsistent with `membership_receipt` (supplemental never becomes primary; no reverse inference); a `milestone` change with `status=observed` whose flags claim `commercial_generation`/`operating_generation` true without an operating asset ⇒ `MILESTONE_NOT_OPERATING`; a `contingent` change referenced by a bridge step in state `observed` ⇒ `CONTINGENT_NOT_FUNDED`; source-less numerical value ⇒ refused; any authority bit true ⇒ `AUTHORITY_BIT_REJECTED`; unresolved identity with `security_link_allowed` true ⇒ refused; expectation `AVAILABLE` without compatible grade/definition/horizon/basis ⇒ `EVIDENCE_GRADE_INSUFFICIENT`; `UNAVAILABLE` expectation emits `estimate=null` (never 0); nested backlog components are never summed into a total; equity-method investee revenue is never added to consolidated; every subject with an `observed`/`forward` bridge step carries ≥1 counterevidence or a `missing_requirement` entry; relationships never derived from co-membership; oversize refuses; `knowledge_cutoff > as_of` refused.

## 6. Wave plan and placement

| Wave | Task | Lane / host / engine | Owned files | Gate |
|---|---|---|---|---|
| W1 | T3 contract + adapter | `ene_w1_t3_adapter` mini2, glm-codex glm-5.3 | `contracts/market_ontology/economic_change_dossier.v1.schema.json`, `engine/market_ontology/energy_economic_change.py`, `tests/test_market_ontology_energy_economic_change.py`, `.github/ci/legacy-jobs.yml` (one new job `energy-economic-change-dossier`), `tests/test_ci_pack.py` (CURATED_EXCLUSIVE entry) | RED→GREEN, 3 mutants, jsonschema validate, contract-delta 0 introduced |
| W1 | T4 witness profiles | `ene_w1_t4_witnesses` mini2, glm-5.3 | `engine/company_intelligence/nuclear_value_profiles.py`, `tests/energy_nuclear_fixtures.py`, `tests/test_company_nuclear_value_profiles.py` | RED→GREEN, 3 mutants, wrong-period/duplicate/incompatible/rights/correction cases |
| W1 | T9 (membership/ThemeState half) | `ene_w1_t9_nonreg` mb, glm-5.3 | `tests/test_energy_economic_change_non_regression.py`, `tests/fixtures/energy_non_regression/*.json` | frozen snapshot of nuclear_power + uranium_miners membership/weights and ThemeState fields; passes on carrier base |
| W1 | audit | Opus `reviewer`, READ_ONLY | this checkpoint §4–§5 | findings folded into packets |
| W2 | T2 consume assertion; T5 compose; T6 private role; T7 route; T8 UI; T9 privacy; T10 real proof | after B's T02/T09/T10 land and R-ENE-04 is decided | — | — |

## 7. Exact next action

Push this carrier, open the Draft/HOLD PR, post custody notices on #7870 and #7793, fresh-read the Slack root, emit `WATCH_ARMED` + `START` there, dispatch the three W1 lanes against this commit, launch the Opus READ_ONLY audit, and continue principal work on the Task 6/7 owner qualification (private role vocabulary, B's envelope) while lanes run.
