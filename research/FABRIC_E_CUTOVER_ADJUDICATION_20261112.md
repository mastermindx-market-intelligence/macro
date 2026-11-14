# Fabric E-vertical cutover — principal adjudication

Status: ADJUDICATED. Principal decisions on the frozen census spec
`research/FABRIC_E_VERTICAL_CUTOVER_SPEC_20261112.md` (merged #11173,
mergeCommit `6771fa1b`). This record closes the spec's §6 "open decisions for
the principal" and is the binding reference for the E-wave build commission.
The census was read-only; this adjudication changes no source. Build is
commissioned separately, packet by packet, under the conventions in spec §0.2.

## Gate dependency (blocking)

Every E1–E5 and R1–R13 packet imports `lib/fabric_client.py`, which exists only
on PR #11160 (`claude/fabric-client-brief-20261112`, head `84ddb947`). That PR is
held by the merge-on-green controller on the systemic ci-control-plane-census
red (#11154 orphan suite); the systemic-CI repair lane owns the fix. **No E
packet is commissioned until #11160 is merged to main.** The frozen adapter
surface (spec §0) is verified against #11160 head `84ddb947` and is the contract.

## Decisions on spec §6

1. **E3/E4 model class → `difficulty="balanced"`.** Open-models-first
   (glm-5.3 class) for both narrative-rotation tiers (E3) and the alt-data
   per-stock brain (E4). The opus-parity option is rejected: it would
   reintroduce the Claude-OAuth dependency this migration eliminates. Keep one
   evaluation cycle against the desks' graded track records before ratifying
   (house statistical-promotion law); a later frontier promotion is a separate,
   evidence-gated decision, not a default.

2. **E1 panel cost lever → analysts `flash`, adjudicator `balanced`.** The four
   analyst stances are structured JSON (flash-class, 4 of 5 calls); the
   desk-head adjudicator synthesizes the debate (balanced judgment). **Extend
   the same split to E2** (thematic desk, identical panel architecture):
   analysts `flash`, adjudicator `balanced`. This is the standing token-economy
   order (Flash for bulk generation, GLM for synthesis) applied to the desks.

3. **R9 orchestrator_chat → HOLD confirmed.** The frozen adapter has no tool
   schema parameter, so the read-only tool-use loop cannot be expressed; the
   credential waterfall shares the CORTEX key family (Astra-HOLD-adjacent).
   Revisit only when the router grows tool support AND Astra's cortex boundary
   is settled. No packet, no switch.

4. **R12 provider_production_modes → HOLD confirmed.** Metered PAYG lane with
   its own cost-identity/receipt contract; MiniMax has no fabric provider
   mapping. No edit. The GLM-only variant is noted but NOT commissioned now.

5. **§5 extra sites → split by mechanism:**
   - **E-wave-2 (direct raw writers, independent of llm_auth):**
     `whitehouse_brain`, `news_llm`, `regime_snap_veto`, `policy_intent_desk`,
     `catalyst_tone` (own creates :427/:430), `commodity_news`. Same writer-site
     pattern, ~1 packet each, commissioned AFTER core E1–E5 + R-packets land.
     These are Macro writers, not cortex — safe to cut without Astra.
   - **Phase F (llm_auth-consumer family):** `marketing/*` (copywriter,
     intelligence_llm, hot_tape_llm), `press/writer`, `risk_brain`,
     `uk_policy_brain`, `admin/prophet`, `codex_provider`, `influence/extract`,
     `news_impact/cascade`, `company_intelligence/e3_shadow_compiler`,
     `marketing/fomc_desk`, and the remaining ~65 llm_auth importers. These
     inherit ONE shared fabric rung inserted into `llm_auth.make_call`
     (phase F), coordinated with Astra, preserving cortex D8 DeepSeek-exclusion.
     One rung, not 65 divergent edits; no collision with the Astra-held client.

6. **ai_costs → `provider="fabric"` confirmed.** Record `comp.model_served` as
   the model and `comp.usage` for tokens, under each site's existing lane (keeps
   the spend drill-down; matches the proven #11160 master_brain pattern). Build
   requirement: the ai_costs pricing table must resolve provider `"fabric"` +
   the served-model slugs (additive ledger entry where missing) — part of each
   packet, not a separate approval. Price at the served model's known rate where
   the table has it; attribution is preserved by `model_served`.

## Additional principal findings (binding on the build)

- **R10 admin-venv dependency:** the admin venv ships no `anthropic` SDK, so
  `fabric_client` raises FabricUnavailable there and the raw-urllib →
  api.deepseek.com legacy path stays effective. To actually retire that legacy
  DeepSeek-key site (estate-migration outcome), the R10 packet MUST add
  `anthropic` to the admin venv requirements; otherwise the cutover is inert in
  admin. Include this dependency in the R10 build packet.

- **E5 MarketDesk is an external producer** (PDFs cleaned at ingest; no in-repo
  LLM call site). Connecting MarketDesk itself to the router is NOT a Macro code
  change — it is a separate producer-side action, out of this repo's scope. The
  in-repo research-lab writer (`research_intelligence/extractor.py`) IS cut as
  E5. Relay this scope clarification to the Chairman.

- **E4 stock dossier is deterministic composition** (`stock_dossier.py`, no
  LLM). The LLM-written per-stock content is `altdata_brain.py` (cut as E4),
  surfaced via `build_ticker_pages.py:514`. The Chairman's "stock dossier
  write-up" maps to E4/altdata_brain, not to stock_dossier.py.

## Preserved boundaries (unchanged)

- **ASTRA PRO HOLD:** `engine/neuralweb/*` (brain_gateway, cortex, ask_brain,
  key_pool, capability_broker) and Mastermind `brain/*` are owned by a separate
  Astra Pro session — untouched, census-only around them.
- **Phase F llm_auth rung** coordinates with Astra; **cortex D8
  DeepSeek-exclusion preserved**. E1–E5 cut at writer sites specifically to
  avoid the shared ladder.
- **R13 ollama_provider** is a llm_auth rung (sole importer) — phase F, no E
  edit, no switch.
- Adapter never retries/failovers; one fabric attempt per call;
  FabricUnavailable → byte-identical legacy. Kill-switch per vertical
  (`MACRO_<VERTICAL>_FABRIC`, default ON when configured).

## Commission readiness

When #11160 merges: commission E1–E5 + R1–R8, R10, R11 as bounded build packets
(each: writer-site fabric branch + kill-switch + test mirror
`tests/test_<module>_fabric_cutover.py` + ai_costs fabric ledger), referencing
this adjudication and spec §0.2. R9/R12 held; R13/§5-llm_auth-family → phase F;
§5 direct raw writers → E-wave-2. D metabolism cutover is a separate census (in
flight) under the same adapter, kill-switch `MACRO_METABOLISM_FABRIC`.

— Principal adjudication, 2026-11-12. Read-only except this record.
