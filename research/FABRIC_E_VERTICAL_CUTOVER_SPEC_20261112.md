# Fabric E-Vertical Cutover Spec — FROZEN (2026-11-12)

Status: FROZEN SPEC awaiting principal adjudication. Census was read-only; the only
artifact of the census is this file. Build is commissioned separately.

Census base: worktree HEAD `91fdfbfc3eac` (branch `claude/ssd-t3-4f13be30-c10bfe70bd1901fc`,
minted from the principal's `t3/aibrief-vps-capacity-fabric` tree). Adapter verified
against PR **#11160** head `claude/fabric-client-brief-20261112` @ `84ddb94716b4`
(OPEN, armed, awaiting CI). `lib/fabric_client.py` is **not present at census HEAD**
— every packet below depends on #11160 merging first.

All file:line citations were read in this checkout unless explicitly marked
"(PR #11160)" for the adapter/pattern/test references.

---

## 0. Frozen adapter surface (verified against PR #11160, do not redesign)

From `lib/fabric_client.py` @ `84ddb94716b4`:

- `is_configured() -> bool` (l.146) — true when `FABRIC_ROUTER_TOKEN` set (`TOKEN_ENV`, l.43).
- `resolve_model(*, model, provider, difficulty, lane)` (l.151) — precedence
  `model > provider > difficulty > lane` (default lane `fast`).
- `complete(messages, *, model=None, provider=None, difficulty=None, lane="fast", max_tokens, system=None, project_id=..., client=..., session_id=..., agent_id=..., parent_agent_id=...) -> Completion` (l.286).
  `Completion` (l.128): `text, model_served, route_id, provider, usage, raw`.
- `stream(...)` (l.321) — SSE deltas.
- `FabricUnavailable(RuntimeError)` (l.116) — raised when no token or the **anthropic SDK
  cannot import** (`_make_client`, l.184–199: the adapter is an `anthropic.Anthropic`
  client pointed at `DEFAULT_BASE_URL = "http://127.0.0.1:8313"`, l.42; override
  `FABRIC_ROUTER_BASE_URL`, l.44). This means every existing Anthropic-SDK site below
  can adopt it with zero new dependencies, and the raw-urllib admin site degrades
  safely (FabricUnavailable → legacy) on hosts without the SDK.
- Provider map: `deepseek→deepseek-v4.1-flash`, `glm→glm-5.3`, `kimi→kimi-k3.1-pro`,
  `qwen→qwen3.8-max`, `claude→claude-opus-5-5`, `gpt→gpt-6.1-sol`.
  Difficulty: `flash|easy→fabric/fast`, `balanced|medium→fabric/balanced`,
  `frontier|hard→fabric/frontier`.
- **Never retry, never fail over at the caller** — the router owns the ladder.
  A served failure degrades exactly like a legacy failure. `FabricUnavailable` is the
  one exception: nothing left the host, so the caller falls to legacy.
- **No tool-use parameter exists in the frozen API** (messages + system + max_tokens
  only). Consequence for R9 below.

### 0.1 The proven cutover pattern (from the #11160 brief writer)

`engine/master_brain.py` @ PR head adds (diff verified): `_FABRIC_BRIEF_STAGES =
frozenset({"macro","china","btc"})`, `_FABRIC_PROJECT_ID = "macro-dashboard"`,
`_fabric_brief_enabled(cfg)` (kill-switch env `MACRO_BRIEF_FABRIC == "0"` → off;
stage must match; `fabric_client.is_configured()`), `_fabric_brief_call(...)` (one
`complete()` with `lane="fast"`, `session_id=f"macro-brief-{stage}"`, served
telemetry `served["provider"]="fabric"`, `served["model"]=comp.model_served`,
`stop_reason==max_tokens → "truncated"`), and in `_call_model`: fabric branch first,
`except fabric_client.FabricUnavailable:` → log + fall through to the legacy ladder.
Test mirror: `tests/test_master_brain_fabric_cutover.py` (273 lines: `fabric_on` /
`fabric_off` fixtures monkeypatching `fc.is_configured` / `fc.complete`; tests:
configured→fabric fast lane, served-by recorded, error degrades without retry,
empty reply not retried, unconfigured→legacy ladder, kill-switch=0→legacy even when
configured).

### 0.2 Conventions for every E packet

- **Additive branch at the writer's own call site.** Taken only when
  `fabric_client.is_configured()` AND the per-vertical kill-switch env ≠ `"0"`.
  When off (unconfigured or killed) the legacy code path runs **byte-identical**:
  the gate reads one env and one boolean before any legacy statement; no legacy
  line is edited, moved, or re-indented.
- Import shape: `from lib import fabric_client` and call attribute access
  (`fabric_client.complete`) so tests can monkeypatch the module, exactly like the
  #11160 fixtures.
- `project_id="macro-dashboard"` everywhere. `client="Python client"`.
  `session_id` per vertical (each packet names it).
- **One fabric attempt per logical call.** No caller-side retry/failover. Served
  exception → the site's existing degraded return (`None`/`"llm_error"`/keep-English
  etc.). `FabricUnavailable` → legacy path, logged.
- **Ledger continuity** (sites that call `lib.ai_costs.record_response_usage`
  today): the fabric branch records the same `lane=` with `provider="fabric"` using
  `comp.usage`; on FabricUnavailable nothing is recorded. Do not pass router URLs
  through `ai_costs.infer_provider` on the fabric branch.
- Kill-switch naming: `MACRO_<VERTICAL>_FABRIC`, default ON when configured
  (matches #11160's `MACRO_BRIEF_FABRIC` semantics).
- Test mirror per packet: new `tests/test_<module>_fabric_cutover.py` copying the
  #11160 shape (§0.1); every packet's Tests line below lists only its deltas.

---

## 1. Summary table

| # | Site | file:line (call) | Current provider/model | Lane (why) | Kill-switch | Flag |
|---|------|------------------|------------------------|------------|-------------|------|
| E1 | AI analyst desk (4-analyst debate) | `engine/ai_desk.py:580` panel, `:617` adj. (via `master_brain._call_model:1662`) | DeepSeek v4-pro via llm_auth ladder, 5 calls/run | `balanced` (judgment) | `MACRO_AI_DESK_FABRIC` | writer-site cutover; do NOT touch `_FABRIC_BRIEF_STAGES` |
| E2 | Thematic desk (sector/theme leans) | `engine/thematic_desk.py:405` panel, `:445` adj. (via `master_brain._call_model`) | DeepSeek v4-pro via llm_auth ladder, 5 calls/run | `balanced` | `MACRO_THEMATIC_DESK_FABRIC` | same |
| E3 | Narrative rotation writer | `engine/narrative_brain.py:177` (`make_call`; providers built `:148`) | opus (rotation) + sonnet (durability) OAuth ladder | `balanced`; rotation parity option `provider="claude"` | `MACRO_NARRATIVE_BRAIN_FABRIC` | goes through llm_auth inside its own `_make_call` — clean writer-site cut; cache_control delta noted |
| E4 | Per-stock "brain" (stock dossier write-up source) | `engine/altdata_brain.py:231` (`make_call`; providers `:213`) | opus-class reasoning via OAuth ladder | `balanced` (open-model first); parity option `provider="claude"` | `MACRO_ALTDATA_BRAIN_FABRIC` | feeds ticker-page dossier (`build_ticker_pages.py:514`); `stock_dossier.py` itself is deterministic — no cutover |
| E5 | Research-intelligence extractor (research-lab write-ups) | `engine/research_intelligence/extractor.py:201` (`make_call`; providers `:184`) | llm_auth ladder, `model_id` operator-chosen | `balanced` | `MACRO_RESEARCH_INTEL_FABRIC` | MarketDesk itself is an EXTERNAL producer (no in-repo call site) — see packet |
| R1 | Profile translation | `engine/translate.py:96` (client `:80`) | raw Anthropic SDK @ deepseek endpoint, `deepseek-chat`, 4000 tok | `flash` (mechanical) | `MACRO_TRANSLATE_FABRIC` | — |
| R2 | News translation (zh/en) | `engine/news_translate.py:353` / `:444` (client `:323`) | raw Anthropic SDK @ deepseek endpoint, `deepseek-chat`, 3000 tok; codex transport variant | `flash` | `MACRO_NEWS_TRANSLATE_FABRIC` | preserve codex branch byte-identical |
| R3 | Catalyst stock brief | `engine/catalyst_stock.py:360` (client from `catalyst_tone._client:374`) | raw Anthropic SDK @ deepseek endpoint, `deepseek-v4-pro`, 2000 tok | `balanced` | `MACRO_CATALYST_STOCK_FABRIC` | shares `catalyst_tone._client`; zh sub-pass uses R1 |
| R4 | US macro news brief | `engine/macro_news.py:1580` (client `:1573`) | raw Anthropic SDK, `deepseek-chat`, 220 tok | `flash` | `MACRO_MACRO_NEWS_FABRIC` | — |
| R5 | China news brief | `engine/china_news.py:1459` (client `:1454`) | raw Anthropic SDK, `deepseek-chat`, 220 tok | `flash` | `MACRO_CHINA_NEWS_FABRIC` | — |
| R6 | China news intel brief | `engine/china_news_intel.py:1028` (client `:1022`) | raw Anthropic SDK, `deepseek-chat`, 220 tok | `flash` | `MACRO_CHINA_NEWS_INTEL_FABRIC` | cited :1024 drifted → 1022–1028 |
| R7 | Special-situations extraction | `collectors/special_situations.py:600` (client `:561`) | raw Anthropic SDK, `deepseek-chat`, 420 tok | `flash` | `MACRO_SPECIAL_SITUATIONS_FABRIC` | **path drift**: `engine/collectors/` does not exist; coexists with existing `DISABLE_SPECIAL_SITUATIONS_LLM` (:552) |
| R8 | Qual extraction | `engine/qual_extraction.py:700/:707` (client `:135`) | raw Anthropic SDK, cfg model, 1500 tok, seed=0 | `flash` | `MACRO_QUAL_EXTRACTION_FABRIC` | — |
| R9 | Admin orchestrator chat | `admin/orchestrator_chat.py:458` (loop `:445`) | Anthropic tool-use loop, opus-4-8→sonnet-4-6 fallback, CORTEX key waterfall | n/a | `MACRO_ORCHESTRATOR_CHAT_FABRIC` | **HOLD**: tool schemas not expressible in frozen adapter API; cortex-adjacent waterfall |
| R10 | Admin log classifier | `admin/mastermind_logs.py:703–711` (URL `:90`) | raw urllib POST → `api.deepseek.com/anthropic/v1/messages`, `deepseek-v4-flash` | `flash` | `MACRO_LOGS_CLASSIFY_FABRIC` | cited :90 = URL constant ✓ |
| R11a | Earnings qual — Ollama rung | `engine/earnings_qual.py:506` (`_call_openai_compat_detailed`; cited :515 = docstring) | OpenAI-compat POST → `http://localhost:11434/v1`, `qwen3.5:9b`, 1200 tok | `flash` | `MACRO_EARNINGS_QUAL_FABRIC` | one switch for the module ladder |
| R11b | Earnings qual — Kimi rung | `engine/earnings_qual.py:615` (`_call_kimi`; cited :620 = key read `:621`) | OpenAI-compat POST → `api.moonshot.ai/v1`, `kimi-k2.6`, `MOONSHOT_API_KEY` | (ladder-level `flash`) | same switch | MOONSHOT key unused when fabric on |
| R12 | Production modes (MiniMax/Z.ai PAYG) | `engine/provider_production_modes.py:1140` (`call_mode`; cited :1001 drifted) | PAYG MiniMax (Anthropic SDK) + Z.ai GLM (OpenAI-compat), pinned models | `provider="glm"` only if cut | `MACRO_PRODUCTION_MODES_FABRIC` | **HOLD recommended**: PAYG cost-identity contract; MiniMax has NO fabric provider mapping |
| R13 | Ollama provider shim | `engine/ollama_provider.py:232/:257` | local Ollama `/api/chat` Anthropic-shaped shim | n/a | none | **PHASE F**: consumed only by `engine/llm_auth.py` — no E-vertical edit |

Count: 5 named-writer packets (4 Chairman names; "sector intelligence rotations"
splits into E2 + E3) + 12 packets covering the 14 enumerated raw sites
(R11 covers two cited lines; R13 is a flag, not an edit).

---

## 2. Named-writer packets

### E1 — AI analyst desk (4-analyst debate)

- **Current call shape** (verified): `engine/ai_desk.py` runs a four-role panel —
  `_PANEL_SYSTEMS` (:531–554; roles `opportunity`, `skeptic`, `base_rate`,
  `structural`) — in parallel (`_run_panel` :577–600, `ThreadPoolExecutor` :596),
  then a desk-head adjudicator (`_adjudicate` :615–623, `_ADJ_SYSTEM` :556).
  Every call is `fn = call or _mb._call_model` (:580, :617) — i.e.
  `engine/master_brain.py::_call_model` (:1662), which builds the
  `llm_auth.build_providers` ladder (:1700) and calls `llm_auth.make_call`
  (:1779). cfg defaults: `llm_model="deepseek-v4-pro"` (:97), `max_tokens=8000`
  (:98); `usage_stage:"ai-desk"` is stamped in `synthesize` (:630). **Five calls
  per run** (4 analysts + adjudicator; authorship comment :640–647). `served_by`
  telemetry flows from the `served` out-param (:672–674). Entry: `run()` (:761),
  built by `scripts/build_ai_desk_page.py`.
- **Fabric replacement**: writer-site wrapper, NOT a `_FABRIC_BRIEF_STAGES` addition
  (keeps #11160's file untouched and gives this vertical its own switch). In
  `synthesize`, before the panel: a module helper `_fabric_call(system, user, cfg,
  served=None)` mirroring `_fabric_brief_call`, gated by
  `_fabric_ai_desk_enabled(cfg)` = `MACRO_AI_DESK_FABRIC != "0"` AND
  `fabric_client.is_configured()` (also respect existing `enabled()` :112 gate).
  When enabled, both `_run_panel` and `_adjudicate` receive the fabric fn as their
  default `call`; when disabled or on FabricUnavailable, the exact `_mb._call_model`
  reference runs unchanged. Call:
  `fabric_client.complete([{"role":"user","content":user}], system=system, difficulty="balanced", max_tokens=int(cfg.get("max_tokens",8000)), client="Python client", project_id="macro-dashboard", session_id="macro-ai-desk")`.
- **Lane + why**: `difficulty="balanced"` — these are falsifiable market leans over
  trust-graded detector state with an adversarial falsifier role, not extraction;
  today's rung is deepseek-v4-pro (above flash class). Cost lever for the build:
  the four analyst stances are structured JSON and may drop to `"flash"` while the
  adjudicator stays `"balanced"` (4 of 5 calls are analysts) — principal may pick
  at commissioning; default spec keeps all five `balanced`.
- **Provider override**: none (router picks within balanced).
- **Attribution**: `session_id="macro-ai-desk"`, `project_id="macro-dashboard"`.
- **Legacy byte-identical when off**: gate is one env read + `is_configured()`; the
  `call=None` injection seam tests already use is preserved (fabric fn slots into
  the same parameter).
- **Served telemetry**: set `served["provider"]="fabric"`, `served["model"]=comp.model_served`
  so the page's `served_by` keeps working; `stop_reason=="max_tokens"` → `"truncated"`.
- **Tests** (`tests/test_ai_desk_fabric_cutover.py`): #11160 mirror plus
  (a) panel+adjudicator both route when configured (count `complete` calls == 5 on a
  synthesized run with panel enabled); (b) one analyst exception degrades that role
  only (existing :590 contract); (c) `served_by` records fabric + model.
- **Overlap flags**: none with Astra/cortex (this is the market desk, not
  neuralweb). Uses master_brain only as a library call — no llm_auth edit needed.
- **Difficulty**: needs-judgment (five-call semantics, thread pool, telemetry).

### E2 — Thematic desk (sector/theme leans — "sector intelligence rotations", US side)

- **Current call shape** (verified): `engine/thematic_desk.py` — same architecture
  as E1. `_PANEL_SYSTEMS` (:341–370; roles `trend_rider`, `crowding_skeptic`,
  `narrative_scout`, `macro_regime`), `_run_panel` (:403–440, `fn = call or
  _mb._call_model` :405), `_adjudicate` (:443–450), `synthesize` (:453+; model
  default `"deepseek-v4-pro"` :463; panel quorum logic :479–499). Header comment
  (:27): "LLM = DeepSeek via engine.master_brain._call_model". cfg is shared with
  ai_desk (`_cfg()` → `_ad._cfg()`, :66–67). **No `usage_stage` is set by this
  module** (verified) so #11160's stage gate leaves it legacy today.
- **Fabric replacement**: identical wrapper shape to E1, gate
  `MACRO_THEMATIC_DESK_FABRIC != "0"` AND `is_configured()`;
  `difficulty="balanced"`, `max_tokens=8000`, `session_id="macro-thematic-desk"`.
- **Lane + why**: `balanced` — theme-rotation leans with a falsifier and humility
  guardrails (:334–339); same class of judgment as E1.
- **Tests**: mirror E1's file (`tests/test_thematic_desk_fabric_cutover.py`),
  including a sub-quorum-panel case that must take the analyst-only fallback
  exactly as today (:474–499).
- **Overlap flags**: none (no llm_auth edit; no neuralweb).
- **Difficulty**: needs-judgment (quorum/fallback semantics must be preserved).

### E3 — Narrative rotation writer ("sector intelligence rotations", HK/global narrative)

- **Current call shape** (verified): `engine/narrative_brain.py::_make_call`
  (:130–184). Builds providers itself:
  `llm_auth.build_providers(cfg, opus_model=cfg.get("models",{}).get("rotation","claude-opus-4-8"))`
  (:148–149); `max_tokens` default 6000 (:152). Returns `call(model, system, user)`
  (:154) that overrides the model id only on Claude-endpoint rungs (:160–163),
  issues `client.messages.create` with a `cache_control`-ephemeral system block
  (:166–170), refusal/empty handling (:171–174), then
  `llm_auth.make_call(call_providers, _do_call, context="narrative_brain")`
  (:177–178). **Two model tiers**: `durability`=sonnet, `rotation`=opus (:138–141).
  Feeds the Narrative Rotation page (`allocation_hk.html.j2`, nav
  `templates/_navlinks.html.j2:162`) via `scripts/build_allocation.py`, plus
  radar/spine consumers.
- **Fabric replacement**: fabric branch at the top of `_make_call`: when
  `MACRO_NARRATIVE_BRAIN_FABRIC != "0"` AND `is_configured()`, return a fabric
  adapter with the same `call(model, system, user) -> (text|None, reason)`
  signature; on FabricUnavailable fall through to the existing body unchanged.
  Inside the adapter: rotation-tier calls (model id contains "opus") →
  `difficulty="balanced"` (recommended; parity option `provider="claude"`); durability-tier
  → `difficulty="balanced"`. `session_id="macro-narrative-rotation"`, `project_id`
  macro-dashboard, `max_tokens` from cfg (:152).
- **Lane + why**: both tiers land `balanced` under the standing open-models-first
  routing order (glm-5.3 class); the opus-parity option exists because the current
  rotation rung is OAuth-opus and its leans are graded — principal picks at
  commissioning (see §6).
- **Delta to flag (do not redesign around it)**: the legacy system block uses
  Anthropic `cache_control`; the frozen adapter takes a plain `system` string.
  Prompt-caching economics change; content contract does not.
- **Tests**: `tests/test_narrative_brain_fabric_cutover.py` — configured → both
  tiers call fabric, no `build_providers` invocation; kill-switch → legacy
  `build_providers` called; FabricUnavailable → legacy; error → `(None,"llm_error")`.
- **Overlap flags**: none (llm_auth used as a library inside its own function; no
  shared-rung edit).
- **Difficulty**: bounded.

### E4 — Per-stock "brain" (the stock-dossier write-up source)

- **Finding**: `engine/stock_dossier.py` is **deterministic composition only**
  (docstring :1–28: "every field surfaces ALREADY-COMPUTED keys… no new scoring") —
  no LLM, nothing to cut over. The LLM-written per-stock content that lands on the
  stock dossier / ticker pages is the alt-data brain: `scripts/build_ticker_pages.py:514`
  reads `intel.get("brain")`, produced by `engine/altdata_brain.py`, run by
  `scripts/build_alt_data.py`.
- **Current call shape** (verified): `_make_call` (:203–238):
  `llm_auth.build_providers(cfg, opus_model=_reasoning_model(cfg))` (:213; model
  pinned via `config["llm_models"]["reasoning"]`, :120–133), `max_tokens` default
  8000 (:216), `client.messages.create` (:220–224), `llm_auth.make_call(providers,
  _do_call, context="altdata_brain")` (:231–232). Returns `call(system, user)`.
  `enabled()` gate :199.
- **Fabric replacement**: fabric branch at the top of `_make_call`, gate
  `MACRO_ALTDATA_BRAIN_FABRIC != "0"` AND `is_configured()` AND `enabled()`.
  Adapter keeps the `call(system, user)` signature:
  `difficulty="balanced"` (recommended open-model default; parity option
  `provider="claude"` — current rung is opus-class and its actions are graded),
  `max_tokens` from cfg, `session_id="macro-altdata-brain"`.
- **Tests**: mirror + assert the brain's JSON action contract (WATCH/… vocabulary
  :416–417) still parses from a fabric reply; degrade → existing `None,"llm_error"`.
- **Overlap flags**: none.
- **Difficulty**: bounded.

### E5 — Research-intelligence extractor (the "research lab" write-ups)

- **Finding on "marketdesk"**: MarketDesk is an **external producer** — its write-ups
  arrive as PDFs and are cleaned at ingest (`engine/research_vault/sidecar.py:230`
  "The producer lives outside this repo (MarketDesk)"; also :153, :169, :482;
  `scripts/build_research_vault.py:97`). There is **no in-repo MarketDesk LLM call
  site**; connecting MarketDesk itself to the router is not a Macro code change
  (flagged for the principal). The Research Vault is the site surface
  ("Research Vault / 研报库", `templates/_navlinks.html.j2:271`).
  The in-repo AI writer in this vertical is the research-intelligence deep-read
  pipeline: `scripts/research_intelligence_vault_head.py` (reads the strict vault
  catalog, orders via press triage, "invokes W1/W2", model chosen by the operator
  `model_id=args.model` :166) → `engine/research_intelligence/extractor.py`.
- **Current call shape** (verified): `_default_call(system, user, *, model_id,
  max_tokens)` (:181–204):
  `llm_auth.build_providers({"usage_lane":"research-intelligence"}, opus_model=model_id)`
  (:184), `client.messages.create` (:192–195),
  `llm_auth.make_call(providers, do_call, context="research_intelligence")`
  (:201–203); `analyze_document(..., model_id, max_tokens=6000, call=None)` (:207–216)
  with an injectable `call` seam.
- **Fabric replacement**: fabric branch in `_default_call` (keep the injectable
  `call` parameter winning over both paths): gate
  `MACRO_RESEARCH_INTEL_FABRIC != "0"` AND `is_configured()`;
  `difficulty="balanced"` (deep-read selection + grounded-quote extraction with a
  frozen RIO — above flash, below frontier), `max_tokens` passthrough (default
  6000), `session_id="macro-research-intel"`. Return
  `(comp.text or "", "fabric", comp.model_served)` matching the existing
  `(raw, provider, served_model)` triple.
- **Tests**: mirror; plus the existing `call=` injection tests must keep passing
  untouched (they bypass both fabric and legacy).
- **Overlap flags**: press writer (`engine/press/writer.py`, llm_auth waterfall,
  no template fallback — docstring :1–27) sits in the same vault/press family but
  was not named; flagged in §5 for a follow-up commission, not specced here.
- **Difficulty**: bounded.

---

## 3. Raw direct-call packets (the 14 enumerated sites)

### R1 — `engine/translate.py` (profile translation)

- **Current** (verified): `_client(cfg)` (:67–84) — key from
  `cfg["api_key_env"]` default `DEEPSEEK_API_KEY` (:70), optional `base_url`
  (:78–81; **cited :80 = this client ctor**). Batch call `_translate_one_batch`
  (:87): `client.messages.create(model=cfg.get("model","deepseek-chat"),
  max_tokens=4000, system=_SYSTEM (:29), …)` (:96–101); ai_costs lane
  `"translate-profiles"` (:104). Degrade: keep-English (:107–119).
- **Fabric**: gate `MACRO_TRANSLATE_FABRIC != "0"` AND `is_configured()` inside
  `_translate_one_batch` before the SDK call (client build stays for legacy):
  `complete(payload-as-one-user-message, system=_SYSTEM, difficulty="flash",
  max_tokens=4000, session_id="macro-translate")`. Served failure → same
  keep-English `none` list; FabricUnavailable → legacy client call.
- **Lane why**: mechanical JSON-array translation, high volume — flash.
- **Ledger**: record lane `"translate-profiles"`, provider `"fabric"`, `comp.usage`.
- **Tests**: mirror (`tests/test_translate_fabric_cutover.py`); count-contract
  mismatch still fails the batch closed.
- **Difficulty**: easy/bounded.

### R2 — `engine/news_translate.py` (news zh/en translation)

- **Current** (verified): cfg defaults (:65–72): provider `deepseek`, base_url
  `https://api.deepseek.com/anthropic`, model `DEFAULT_DEEPSEEK_MODEL="deepseek-chat"`
  (:25). `_client` (:303–326; **cited :323 = `anthropic.Anthropic(**kw)`**) with a
  **codex transport variant** (:304–305) and poller `max_retries=0` (:318–322).
  Creates: zh `:353`, en `:444` via `_create_kwargs` (:178–192; max_tokens 3000,
  opt timeout). Systems `SYSTEM_ZH` :27 / `SYSTEM_EN` :35. Usage lane
  `"news-translate"` (:217).
- **Fabric**: gate `MACRO_NEWS_TRANSLATE_FABRIC != "0"` AND `is_configured()` AND
  `_provider(cfg) == "deepseek"` — **the codex branch stays byte-identical and is
  never fabric-routed**. `difficulty="flash"`, `max_tokens` from cfg,
  `session_id="macro-news-translate"`, system `SYSTEM_ZH`/`SYSTEM_EN` as
  applicable. FabricUnavailable → legacy deepseek transport.
- **Tests**: mirror + a codex-configured case that must NOT touch fabric.
- **Difficulty**: easy/bounded.

### R3 — `engine/catalyst_stock.py` (stock catalyst brief)

- **Current** (verified): `_call_model` (:353–374): client from
  `catalyst_tone._client` (imported :63; defined `engine/catalyst_tone.py:374`,
  default base `https://api.deepseek.com/anthropic` :384);
  `client.messages.create(model="deepseek-v4-pro", max_tokens=2000, system,
  …)` (**:360**–364); refusal/empty/truncated handling (:365–371). A zh
  sub-pass (:437–445) configures `engine.translate` with
  `deepseek-v4-flash` — that inherits R1's cutover, not this packet.
- **Fabric**: gate `MACRO_CATALYST_STOCK_FABRIC != "0"` AND `is_configured()` at
  the top of `_call_model`: `difficulty="balanced"` (per-stock catalyst reasoning,
  v4-pro today), `max_tokens=2000`, `session_id="macro-catalyst-stock"`.
  Return contract `(text|None, reason)` preserved incl. `"truncated"` on
  `stop_reason=="max_tokens"`.
- **Tests**: mirror.
- **Note**: `catalyst_tone.py` itself also has raw default + `make_call`
  (:427/:437) — see §5 extras.
- **Difficulty**: bounded.

### R4 — `engine/macro_news.py` (US macro news brief)

- **Current** (verified): `macro_brief` (:1556); `_llm_ready` (:1550–1553); key
  :1571; **client :1573–1574 (cited :1573 ✓)**;
  `create(model="deepseek-chat", max_tokens=220, system=BRIEF_SYSTEM)` (:1580–1582);
  ai_costs lane `"macro-news"` (:1585–1587); degrade → `None`.
- **Fabric**: gate `MACRO_MACRO_NEWS_FABRIC != "0"` AND `is_configured()`;
  `difficulty="flash"` (one-paragraph labeled context narration, 220 tokens),
  `session_id="macro-us-news-brief"`. Ledger: lane `"macro-news"`, provider
  `"fabric"`.
- **Tests**: mirror. **Difficulty**: easy/bounded.

### R5 — `engine/china_news.py` (China news brief)

- **Current** (verified): `news_brief` (:1440); **client :1454–1455 (cited :1454 ✓)**;
  create :1459–1461 (`deepseek-chat`, 220, `BRIEF_SYSTEM`); lane `"china-news"`
  (:1464); degrade → `None`.
- **Fabric**: gate `MACRO_CHINA_NEWS_FABRIC != "0"` AND `is_configured()`;
  `difficulty="flash"`, `session_id="macro-china-news-brief"`.
- **Tests**: mirror. **Difficulty**: easy/bounded.

### R6 — `engine/china_news_intel.py` (China intel news brief)

- **Current** (verified): `_llm_ready` (:1005–1010); `news_brief` (:1013);
  client :1022–1023 (**cited :1024 drifted; actual ctor 1022–1023**); create
  :1028–1030 (`deepseek-chat`, 220, `_BRIEF_SYSTEM`); lane `"china-news-intel"`.
- **Fabric**: gate `MACRO_CHINA_NEWS_INTEL_FABRIC != "0"` AND `is_configured()`;
  `difficulty="flash"`, `session_id="macro-china-news-intel"`.
- **Tests**: mirror. **Difficulty**: easy/bounded.

### R7 — special situations (path drift: `collectors/special_situations.py`)

- **Path correction**: the brief's `engine/collectors/special_situations.py` does
  not exist. The LLM site is top-level **`collectors/special_situations.py`**
  (`engine/special_situations.py` has no LLM; the china/intl/premium siblings have
  no LLM either — verified by grep).
- **Current** (verified): key gate :554 with **existing env kill
  `DISABLE_SPECIAL_SITUATIONS_LLM`** (:552); `_llm_client` (:557–563;
  **cited :560 ≈ ctor :561**; model default `"deepseek-chat"` :563);
  `_llm_prompt` (:588); `_llm_call` create :600 (`max_tokens=420`, system
  passed in); ai_costs lane `"special-situations"` (:602); parse fails closed
  to `{}` (:566–572).
- **Fabric**: gate `MACRO_SPECIAL_SITUATIONS_FABRIC != "0"` AND `is_configured()`
  AND the existing `DISABLE_SPECIAL_SITUATIONS_LLM` not set (both switches must
  allow); `difficulty="flash"` (filing-text → JSON classification, 420 tokens),
  `session_id="macro-special-situations"`. Ledger: lane kept, provider `"fabric"`.
- **Tests**: mirror + `DISABLE_SPECIAL_SITUATIONS_LLM=1` forces legacy-off exactly
  as today.
- **Difficulty**: easy/bounded.

### R8 — `engine/qual_extraction.py`

- **Current** (verified): `_client` (:135–151; **cited :135 ✓**; key :142; optional
  base :145–149). Extraction call (:688–712): kw = `{model, max_tokens 1500,
  system=_EXTRACTION_SYSTEM, messages}` with `seed=0` and a TypeError retry that
  drops seed (:695–707); lane `"qual-extraction"` (:702).
- **Fabric**: gate `MACRO_QUAL_EXTRACTION_FABRIC != "0"` AND `is_configured()`;
  `difficulty="flash"` (structured extraction), `max_tokens` from cfg,
  `session_id="macro-qual-extraction"`. No seed concept in the frozen API —
  determinism note for the build: extraction drift checks
  (`scripts/check_extraction_drift.py`) must be re-baselined if enabled.
- **Tests**: mirror. **Difficulty**: easy/bounded.

### R9 — `admin/orchestrator_chat.py` — **HOLD**

- **Line drift**: cited :189 is inside `_resolve_candidates` (:160–169). The model
  call is the tool loop `_run_loop` (:445–472; `client.messages.create(model,
  max_tokens=_MAX_TOKENS, system=_SYSTEM_PROMPT, tools=_TOOL_SCHEMA, messages)`
  :458–460). Constants: `_MODEL="claude-opus-4-8"` (:40),
  `_FALLBACK_MODEL="claude-sonnet-4-6"` (:41), `_MAX_TOKENS=1600` (:42). Key
  waterfall `CORTEX_ANTHROPIC_API_KEY → OAuth pool → attached Codex →
  ANTHROPIC_API_KEY` (:14–15, :163+). Keyless degraded mode + 20 msg/h cap
  (:16–19).
- **Why HOLD (no cutover spec)**: (1) the frozen adapter API has **no tools
  parameter** — the read-only tool-use loop cannot be expressed through
  `complete()`; (2) the credential waterfall mirrors `neuralweb/ask_brain`
  (docstring :11) and shares the CORTEX key family — Astra-HOLD-adjacent
  (cortex owns `CORTEX_ANTHROPIC_API_KEY`). Revisit when the router grows tool
  support and Astra's cortex boundary is settled. If ever cut over:
  `provider="claude"`, switch `MACRO_ORCHESTRATOR_CHAT_FABRIC`.
- **Difficulty**: n/a (held).

### R10 — `admin/mastermind_logs.py` (contradiction classifier)

- **Current** (verified): `_CLASSIFY_URL = "https://api.deepseek.com/anthropic/v1/messages"`
  (**:90 ✓**), `_CLASSIFY_MODEL="deepseek-v4-flash"` (:91), caps (:92–94). Raw
  urllib POST with `x-api-key` + `anthropic-version` headers (:703–711), verdict
  parse (:713–717), entry `classify_contradictions` (:720).
- **Fabric**: gate `MACRO_LOGS_CLASSIFY_FABRIC != "0"` AND `is_configured()`
  inside the classify helper before the urllib build:
  `complete([{user}], system=<existing classify system>, difficulty="flash",
  max_tokens=<existing cap>, session_id="macro-logs-classify")`. Note the admin
  venv deliberately ships no SDK — `fabric_client` raises FabricUnavailable there
  and the raw-urllib legacy path remains the effective default until the venv
  grows `anthropic`. Verdict vocabulary `("none","system_error","market_divergence","unclear")`
  (:95) unchanged.
- **Tests**: mirror (FabricUnavailable → urllib path asserted).
- **Difficulty**: easy/bounded.

### R11 — `engine/earnings_qual.py` (two cited sites, one module ladder)

- **Current** (verified): `_DEFAULT_CFG` provider_order
  `["openai_compat","deepseek","kimi","anthropic"]` (:140).
  - **Ollama rung (cited :515)**: `openai_compat` cfg → `base_url
    http://localhost:11434/v1`, `model qwen3.5:9b`, `LOCAL_LLM_API_KEY`,
    timeout 120, max_tokens 1200 (:141–150). The transport is
    `_call_openai_compat_detailed` (**def :506**; cited :515 lands in its
    docstring) and the legacy wrapper `_call_openai_compat` (:603).
  - **Kimi rung (cited :620)**: `_call_kimi` (**def :615**; cited :620 ≈
    `key_env` read :621) → `https://api.moonshot.ai/v1`, `kimi-k2.6`,
    `MOONSHOT_API_KEY`, max_tokens 1200 (:153–158, :615–628).
  - Global caps: `daily_cap 64`, `max_chars 48000`, prompt `equal-v3`
    (:160–164).
- **Fabric**: **one switch for the module ladder** — gate
  `MACRO_EARNINGS_QUAL_FABRIC != "0"` AND `is_configured()` at the ladder entry
  (where the provider_order walk begins), not per rung: a single
  `complete(..., difficulty="flash", max_tokens=1200,
  session_id="macro-earnings-qual")` replaces the whole local→deepseek→kimi→anthropic
  walk for that item (structured equal-v3 qualification over transcript text).
  Never walk to the Kimi rung after a served fabric failure — degrade with the
  existing reason vocabulary. MOONSHOT/LOCAL keys become unused while fabric is
  on; the daily_cap accounting stays (count fabric calls against it).
- **Tests**: mirror + assert no `_call_kimi`/`_call_openai_compat` invocation when
  fabric serves; kill-switch → full legacy walk with Ollama first, exactly as today.
- **Difficulty**: bounded.

### R12 — `engine/provider_production_modes.py` — **HOLD recommended**

- **Line drift**: cited :1001 is in the config/pinned-model region; the call entry
  is `call_mode(mode_id, system, user, *, max_tokens, env=None, transport=None)`
  (**:1140–1156**), transports = `earnings_qual._call_openai_compat_detailed` for
  GLM and the Anthropic SDK for MiniMax (:1151–1153); closed body overlay with a
  max_tokens ceiling (:221–231); pinned models `MINIMAX_PINNED_MODEL` /
  `GLM_PINNED_MODEL` (:38–40).
- **Why HOLD**: this module is a **metered PAYG lane with its own credential
  boundary, cost identity and receipts** (docstring :6–16, :36–45) — routing it
  through the fabric router changes billing identity, which the module's own
  contract forbids doing implicitly. Also **MiniMax has no mapping in the fabric
  provider map** (glm→glm-5.3 exists; minimax does not), so MiniMax modes cannot
  be served by the router today. If the principal wants it: GLM-only cutover via
  `provider="glm"`, switch `MACRO_PRODUCTION_MODES_FABRIC`, MiniMax modes stay
  PAYG. Default spec: no edit.
- **Difficulty**: n/a (held; GLM-only variant would be bounded).

### R13 — `engine/ollama_provider.py` — **PHASE F flag, no E edit**

- **Current** (verified): an Anthropic-compatible shim over local Ollama
  (`base_url/api/chat`): client class (:204), `create` (:232), POST (:257),
  `stream` (:295). **Consumed only by `engine/llm_auth.py`** (sole importer,
  verified) — `build_providers` inserts an Ollama rung only when a lane explicitly
  lists `ollama` in `provider_order` and sets `OLLAMA_BASE_URL`
  (llm_auth.py :952–968 docstring).
- **Disposition**: this is a rung inside the shared ladder, not a writer. It is
  superseded per-lane whenever a writer takes its fabric branch ahead of the
  ladder (E1–E5 do). Editing the ladder itself is **phase F** (coordinate with
  Astra; preserve cortex D8 DeepSeek-exclusion). No packet, no kill-switch.

---

## 4. HOLD / already-done / phase-F registry

| Item | Disposition |
|------|-------------|
| `engine/master_brain.py` brief writer | **DONE in #11160** (stages `macro|china|btc`, `MACRO_BRIEF_FABRIC`, FabricUnavailable→legacy). Not re-specced. Note: at census HEAD the PR is unmerged, so the file here still shows the legacy-only ladder — expected. |
| `engine/neuralweb/*` (brain_gateway, cortex, ask_brain, key_pool, capability_broker), Mastermind `brain/*` | **ASTRA PRO HOLD** — out of scope, untouched. |
| `engine/metabolism/*` + `scripts/metabolism_*` | separate census in flight — not specced. |
| `engine/llm_auth.py` shared fabric rung | **PHASE F** — coordinate Astra; preserve cortex D8 DeepSeek-exclusion. All E1–E5 cut at writer sites specifically to avoid this. |
| R9 orchestrator_chat, R12 production_modes | HOLD per packets above. |

## 5. Extra raw/llm_auth sites discovered (NOT in the commission — principal decision)

Endpoint-census finds beyond the 14 + named writers (all verified by grep this
checkout):

- `engine/whitehouse_brain.py` — default :50, call path :241 (deepseek anthropic-compatible).
- `engine/news_llm.py` — `DEEPSEEK_BASE` :59.
- `engine/regime_snap_veto.py` — default :68.
- `engine/policy_intent_desk.py` — default :90.
- `engine/catalyst_tone.py` — own creates :427/:430 and `llm_auth.make_call` :437 (shares `_client` with R3).
- `engine/commodity_news.py` — llm_auth importer (same family as catalyst_tone).
- `engine/marketing/*` — `copywriter.py` make_call :7422/:9347/:9400 (with template-fallback history), `intelligence_llm.py` :671, `hot_tape_llm.py` :1071/:1103 — llm_auth consumers (Intelligence Desk V2 / Hot Tape public write-ups).
- `engine/press/writer.py` — the press write-up writer via the llm_auth waterfall (:1–27; no template fallback by design).
- Other llm_auth importers (65 total): `risk_brain`, `uk_policy_brain`, `altdata_brain` (specced E4), `admin/prophet.py`, `engine/codex_provider.py`, `influence/extract`, `news_impact/cascade`, `company_intelligence/e3_shadow_compiler`, `marketing/fomc_desk` etc.

These need either E-vertical packets (same pattern, ~1 packet each) or the phase-F
rung; none are specced here.

## 6. Open decisions for the principal

1. **E3/E4 model class**: `difficulty="balanced"` (open-model-first, glm-5.3) vs
   `provider="claude"` (opus parity for graded ledgers). Spec default: balanced,
   one evaluation cycle against the desks' track records before keeping.
2. **E1 panel cost lever**: all five calls `balanced` (default) vs analysts
   `flash` + adjudicator `balanced`.
3. **R9**: hold until the router/adapter supports tool schemas (frozen API has none).
4. **R12**: hold (PAYG identity; MiniMax unmapped). GLM-only variant available.
5. **§5 extras**: commission a follow-up E-wave or fold into phase F.
6. **ai_costs**: fabric branch records `provider="fabric"` under existing lanes
   (recommended, keeps the spend drill-down); confirm the cost-basis mapping for
   router-served usage with whoever owns the ledger.

— Census leaf, 2026-11-12. Read-only except this file.
