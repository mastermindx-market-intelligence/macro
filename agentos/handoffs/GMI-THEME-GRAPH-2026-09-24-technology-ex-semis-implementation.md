---
workstream: "WS:GMI-THEME-GRAPH"
session: fable/technology-ex-semis-implementation-20260924
model: fable
ended_because: checkpoint
mission: >
  Integrate the approved Technology ex-Semiconductors Economic Change first vertical from the
  saved plan and verification supplement on one fresh current-main implementation carrier,
  consuming incumbent Company/Earnings, shared GMI, private-publication and shared-page
  owners rather than duplicating them; Sol remains principal for unresolved admission rulings
  and final end-to-end acceptance.
state_before: >
  Fable packet PREPARED_ADMISSION_HELD at #7793 head d1f28763; no receiver, START, carrier,
  watcher or product effect existed. The Chairman delivered the concrete Fable receiver
  assignment on 2026-09-24; PICKUP_ACK recorded as #7793 issuecomment-5808685385.
changed:
  - path: agentos/handoffs/GMI-THEME-GRAPH-2026-09-24-technology-ex-semis-implementation.md
    what: "Created the implementation-operation working checkpoint: receiver identity, packet/procedure pins, current-main custody reconciliation, observed G1-G7 dispositions, Fable custody rulings TR1-TR5, wave plan and exact next action."
verified:
  - claim: "No open Macro PR modifies the T2/T3/T5 target paths; the only adjacent live modifiers are #7870 (engine/company_intelligence/guidance_history.py, shared theme_graph curation assertion) and #7426 (engine/company_intelligence/event_workspace.py)."
    command: "gh pr list --state open --json files over PRs updated since 2026-09-03, filtered to engine/company_intelligence, earnings private publisher, app/earnings.py, the three templates, theme_graph and market_ontology contracts/engines; git cat-file -e origin/main:<path> for every plan Create path."
    result: "All plan Create paths absent on main 0ae0bbe4; #7870 is the sole PR touching theme_graph curation_assertion paths; #7426 touches only event_workspace.py; no PR touches private_publication.py, publish_earnings_private_store.py, app/earnings.py or the three templates."
  - claim: "Sol's Company/Earnings source-owner ruling on #7331 (2026-09-21T10:03Z) accepted the exact interface the saved plan's T4 consumes."
    command: "gh issue view 7331 --json comments; grep origin/main and refs/pull/7426/head for extract_release_guidance / event_type= in event_workspace_build.py and issuer_profiles.py."
    result: "Accepted: aliases_for(..., event_type=...) and CompanyEvent.create(..., event_type=...) forwarding; separately typed extract_release_guidance(*, bound, document_id, event_id, fiscal_period) -> list[guidance_item.v1]; forecast update != documentary correction != actual; ruling section 7 assigns implementation to the incumbent #7331/#7426 owner. Not yet implemented on main or #7426 head 7bc04876."
  - claim: "The shared GMI curation assertion contract exists as one module/schema on #7870, not on main."
    command: "git show refs/pull/7870/head:contracts/theme_graph/curation_assertion.v1.schema.json | python json keys; git show ...:engine/theme_graph/curation_assertion.py | grep def/class."
    result: "#7870 head 45eb37bb: schema id theme_graph.curation_assertion.v1 with 14 required sections plus optional industrial_context; module symbols validate_assertion, curation_revision, encode_assertion, decode_assertion, source_ref_for, revision grammar gmirca_[0-9a-f]{32}; #7669 released generic research-mount shell custody to #7870 (issuecomment-5807781684)."
unverified:
  - claim: "Any G2-G6 gate is closed for a live/product path."
    what_would_verify: "Exact owner receipts named in the supplement section 3: accepted assertion revision on main, R4 private-binding ruling on #7780, DDOG issuer/source/metric/perimeter admission on #7331, private role/version + writer-fencing acceptance, delivered shared mount."
  - claim: "An Executive OS runtime pickup/START receipt exists for this operation."
    what_would_verify: "A QUEUED/START record through the authenticated Executive connector; that connector is unauthorized in this non-interactive seat, so lifecycle is recorded on this carrier and #7793 only."
unresolved:
  - "G2/G3: shared assertion acceptance on main and the R4 private native binding (DECISION_REQUEST #7780 issuecomment-5807772681) — Technology registered as dependent."
  - "G4: DDOG issuer/source/metric/fiscal/clock/perimeter admission and who carries the generic release-guidance seam on the incumbent Company boundary."
  - "G5: private manifest v2 role/version registration, compatible reader rollout and cross-process writer exclusion proof."
  - "G6: delivered shared research mount identity (#7870 shell, basket_detail frozen pending #7669) and browser/CI owner."
next_actions:
  - "Write START on #7793 naming this carrier for the first modifying action: T2/T3 pure contract/calculator units with synthetic inputs via fabric lanes; T5 fixture composition in parallel."
  - "Post consumption/custody notices on #7331 (Company seam + DDOG admission request), #7870 (consume shared assertion + mount, no re-authoring) and #7780 (register Technology as R4 dependent)."
  - "Integrate returned units after second-environment gate and independent READ_ONLY review; then T6/T7 fixture-only; T4/T8/T9 only when their gates close."
do_not_redo:
  - "Do not repeat R1-R6, the approved design or the saved plan; do not turn #7793 into the implementation branch."
  - "Do not re-author the shared curation assertion, add a Technology store/publisher/queue/template/control plane, or edit #7426/#7870/#7669 paths from this carrier."
danger_areas:
  - "A fixture-complete calculator is not the first complete vertical; 93.546 is a development oracle, not a production constant."
  - "Full-fidelity paid assertion data must never enter this public carrier, evidence.parquet, site/ or R2 public paths."
---

# Technology ex-Semiconductors — implementation operation working checkpoint

OPERATION: `gmi-technology-ex-semis-fable-integration-20260924-chairman-001` (child of research operation `gmi-technology-ex-semis-research-20260923-sol-001`; parent `WS:GMI-THEME-GRAPH`).
RECEIVER: Claude Fable 5.1 (`claude-fable-5-1`), Claude Desktop Code session `9e061294-a0cd-4d2f-a40c-764d2fbe4d6c`, Mac-Studio (m2) seat. PICKUP_ACK: #7793 issuecomment-5808685385.
PACKET: `agentos/handoffs/GMI-TECHNOLOGY-EX-SEMIS-FABLE-INTEGRATION-PACKET-2026-09-23.md` at `b989fefa01b43b22c281e77a489f0fde6cf4665a`; plan blob `febe42f1ff24fdfe7c50dd69784239992acf65ee`; supplement blob `b99bb290aa3c983a730b38b11b2e3b446441690c`; design at `26a3c4c6b3c20b2ebe7fbd469cae320b4ad0eb96`; verified checkpoint head `d1f28763b28bab0a0b903600e1556b7a00f5fa8a`.
PROCEDURE PIN: Mastermind `bab1291ba7163bf091354181066ab26cf8a0c0ea` (ACTIVE_EXECUTION Skillpack 1.0.1/bootstrap 1; AGENT_DIALOGUE_SESSION_CLOSE_LAW), compatible with packet pin `a7d2b3049e5dcdc523e91e61a6e9d70a1cb911157`.
CARRIER BASE: Macro `main` `0ae0bbe482efcb6cddee399e0e1603435c5cdbb3`; branch `claude/ssd-technology-ex-semis-impl-c887181119dd2aaf` (SSD worktree per policy).

STATE AT THIS COMMIT: `PRE_START` (PICKUP_ACK only); `TECHNOLOGY_FIRST_VERTICAL: NOT_BUILT`; `MISSION_COMPLETE: false`; `EFFECT_UNKNOWN: none`.

## Fable custody rulings inside the approved architecture (TR = Technology ruling)

- **TR1 — T2/T3 are path-disjoint and start now.** The five new Company-namespace files (comparison schema, contract, calculator, two suites) are touched by no open PR; #7870's `guidance_history.py` is adjacent and complementary (it explicitly consumes midpoints only through `native_derivations` receipts and computes none). Custody notice posted to the Company/Earnings carrier #7331; the incumbent may object there.
- **TR2 — the Company seam is consumed, never re-implemented here.** `issuer_profiles.py`/`event_workspace_build.py` changes for `event_type` forwarding and `extract_release_guidance` belong to the incumbent #7331/#7426 owner (ruling section 7). T4 (`datadog_profile.py`, `economic_change_inputs.py`) waits for that seam on main or an accepted pinned incumbent head plus G4 admission.
- **TR3 — one shared assertion, authored by #7870, consumed at a pinned head.** T5 imports `engine.theme_graph.curation_assertion` lazily; when absent on the carrier base it returns the typed refusal `shared_contract_unavailable`, and the real round-trip test is `xfail(strict=True)` pinned to #7870 head `45eb37bbf832e007e67ce2594674d6bfeeb3b880` until the contract lands on main. No copy of the schema or module into a Technology namespace.
- **TR4 — private binding = R4.** Technology's G3 is the same DECISION_REQUEST as Semiconductor B's R4 (#7780 issuecomment-5807772681). T5 live composition and T6 real writes wait for that ruling; T6/T7 proceed fixture-only after the custody notice with no publication.
- **TR5 — shared page = #7870 mount.** The generic hidden research mount and shared asset includes are #7870's (custody released by #7669); `basket_detail.html.j2` stays frozen pending #7669. T8 mounts Technology content only through the delivered shared mount; no second panel, no patch to generated stock HTML, `ci-terminal-upgrade` anchor untouched.

## Custody map (carrier base 0ae0bbe4)

| Path | Status | Owner / resolver |
|---|---|---|
| `contracts/company_intelligence/management_outlook_comparison.v1.schema.json`, `engine/company_intelligence/management_outlook_contract.py`, `engine/company_intelligence/management_outlook.py`, `tests/test_company_management_outlook_contract.py`, `tests/test_company_management_outlook.py` | new, free | T2/T3 (TR1) |
| `engine/company_intelligence/datadog_profile.py`, `engine/company_intelligence/economic_change_inputs.py` + two suites | new, held | T4 after seam + G4 (TR2) |
| `engine/company_intelligence/issuer_profiles.py`, `engine/company_intelligence/event_workspace_build.py` | **never edited here** | incumbent #7331/#7426 |
| `contracts/theme_graph/curation_assertion.v1.schema.json`, `engine/theme_graph/curation_assertion.py`, `engine/theme_graph/store.py` | **consume only** | #7870 (R1/R2), #7462 |
| `contracts/market_ontology/economic_change_dossier.v1.schema.json`, `engine/market_ontology/technology_economic_change.py`, `tests/test_market_ontology_technology_economic_change.py` | new, free | T5 fixture providers (TR3) |
| `engine/earnings_narrative/private_publication.py`, `scripts/publish_earnings_private_store.py`, `tests/test_earnings_private_economic_change.py` | existing, no live modifier; G5 owner extension required | T6 fixture-only after notice; real writes held |
| `app/earnings.py`, `tests/test_earnings_economic_change_api.py` | existing, no live modifier | T7 fixture-only after notice |
| `templates/state_of_themes.html.j2`, `templates/basket_detail.html.j2`, `templates/ticker.html.j2` | **held** (G6) | #7870 mount / #7669 |
| `site/assets/js/technology-economic-change.js`, `site/assets/css/technology-economic-change.css`, `tests/test_technology_economic_change_ui.py` | new, held | T8 after G6 |
| `data/theme_graph/evidence.parquet`, `site/`, public R2 | no full-fidelity payload ever | R4 |

## Observed gate dispositions (2026-09-24, this seat)

G1 reconciled for T2/T3/T5 new paths; held for incumbent files. G2 shape on #7870 only; NOT_ACCEPTED on main. G3 = R4 pending on #7780. G4 HELD: interface accepted on #7331, DDOG admission and seam implementation owed by Company/Earnings. G5 HELD (owner extension + writer fencing unproven). G6 HELD (mount custody #7870/#7669). G7 NOT_EXECUTED.

## Fabric surface and routing

Placement through the installed `pool` CLI remote lanes (m1, mb, mini2; the m2 seat is not a lane host). Seat decomposes, integrates, adjudicates and reviews; executors implement bounded packets carrying the LANE LAW preamble (no push/PR/labels/watchers), exact plan text, owned files, deterministic pytest gate and a fixed return format. Independent review is a READ_ONLY Opus audit distinct from the builder. Executive OS runtime receipts are unavailable to this seat (connector unauthorized); lifecycle facts live on this carrier and #7793.

## Wave plan

W1: T2+T3 (one lane, synthetic oracle F_A=4320, F_B=4460, P_A=P_B=1006.426, G_A_N=1075, X_B_N=1121.454 → 140; 46.454; 0; 2238.574; 2332.120; 93.546) and T5 fixture composition in parallel. W2: T6, T7 fixture-only. W3: T4 when the seam and G4 close; T8 when G6 closes; T9 when G1–G6 close for the exact candidate. Nothing merges or deploys automatically; #7793 stays research-only.
