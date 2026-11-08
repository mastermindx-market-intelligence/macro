# Sector input/runtime audit and parent adjudication

Date: 2026-11-05.
Mission: https://github.com/mastermindx-market-intelligence/macro/issues/10779
Plan: [Always-on Macro migration](ALWAYS_ON_MACRO_MIGRATION_2026-11-05.md).
Source pins: Macro `0c4c28e4a3e1ba0b1dde3ebdd9774355822f1527`; Terminal `f9d3280a2a3ff28dd925b128231702b836c8a247`; protected Mastermind `49c2e1d93e5e080b1671c98087a845e5beb09dd5`.
Fabric run: `macro-always-on-20261105-c3-input-runtime-01`.
Complete response: 20309 bytes; response SHA-256 `adf6e96d9c9c11ed67895615497d8551b2b93b0858cfaaa6a320745180fde7f4`.
The response digest identifies the returned text, not a cryptographic attestation of the inspected repository or production.

## Parent ruling

The source census is useful and is retained below with these explicit qualifications. Worker recommendations are evidence for this ruling; they do not independently authorize a producer, publication, entitlement or source-owner change.

1. **Accepted source distinction:** the close-based Sector research pipeline still depends on repository-local Yahoo histories and additional regime, rotation, membership and research inputs. Existing quote, breadth, basket-pulse and heatmap runtime owners already operate separately. Reuse them.
2. **Purity claim rejected:** `engine/sector_central.py::compute()` has no direct output write, but reads the cycle spine, market context, closes, rotation and membership and calls `datetime.now()`. It is not a pure function. The next extraction must make these inputs and the evaluation date explicit and inspect helper call paths. A runtime must not call builder entry points that append grades, logs or notifications.
3. **Causal claim limited:** the November 5 checkout failure proves that one refresh stopped before computation. It does not establish the complete last-writer history or uniquely explain every November 3 watermark. Unknown causal attribution is not an unresolved modifying tool effect.
4. **Independent close data is necessary, not sufficient:** transferring Yahoo closes unlocks the price-derived spine. Fresh full research still requires the relevant context, rotation, themes and membership revisions. Do not mark all Sector fields current because one input advances.
5. **No redundant live wrapper:** do not copy basket-pulse, quote and heatmap outputs into another publisher merely to rename them. A new materialization needs a named calculation and consumer. Existing independently dated overlays remain distinct.
6. **Publication:** the current orchestrator's per-file rename does not make paired free/paid Sector artifacts one coherent generation. Use immutable candidate generation files plus one current-manifest promotion under the existing publisher when a multi-artifact consumer requires consistency. Resolve the manifest once per request.
7. **Access:** a new path under `/live/` does not automatically inherit the right entitlement. Current Caddy has explicit public allowlists and a separate registered/paywall path. Keep private generation files and metadata inaccessible through direct URLs; use explicit free/paid projections and the existing BFF/auth owner.
8. **Registry qualification:** the existing compiled registry contains 353 entries, including non-product/internal routes. Its v1 owner placeholder and empty `data_sources` field are intentionally incomplete metadata, not proof that the actual services lack owners. Extend the established registry/contract source when needed; do not create a second inventory authority.
9. **Consumer limitation:** current native Discover views do not implement the entire legacy Brief/Explore/Research/Watches and action-board journey. PR 1311 refreshes active existing feeds only. Full journey parity remains an explicit migration obligation.
10. **Evidence limitation:** this audit inspected source. It did not prove production publication, source freshness, authentication, installed code or browser behavior. Production observations are separately scoped in the evidence JSON.

11. **Complete Brief dependency clarified, November 6:** the original basket chart/theme leadership also requires the broad/smallcap/midcap history panels, extras, current theme scoring/allocation, explicit historical context and canonical board data. The retained worker claim below that a closes advancer alone completes daily Sector is not accepted. [Broader runtime evidence](ALWAYS_ON_BRIEF_INPUT_EVIDENCE_2026-11-06.json) and the master plan record the complete chain. Preserve the raw return as evidence, not current authority.

## Input ownership and first independent canary

The current source points to repository-local `data/yahoo/` histories. `lib/config.py` does not provide the proposed runtime data-root override; inventing an environment variable or mutating global cached configuration would leave undeclared fallback reads.

The next bounded implementation must preserve default callers while accepting an explicit input snapshot through the selected calculation. Declare close history, membership, cycle/context/rotation dependencies and effective session. Repeated computation over the same substantive inputs and calculation version must be deterministic. Isolated-input tests must fail on repository-data fallback, clock reads and ledger/grader effects.

Transfer the existing Yahoo collection/store semantics into an existing runtime lane only after identifying and fencing every incumbent writer for the transferred lineage. Existing Git builders may consume a pinned immutable snapshot as a compatibility transport; they must not silently resume independent Yahoo collection during an outage. Retain source revision, adjustment basis, coverage and correction behavior. Existing intraday bars are not interchangeable with this history without proof.

The first useful canary is a newly completed session reaching specifically named close-derived Sector fields without a Git commit or frontend deploy. If broader context still uses a prior baseline, display both dates and narrow the freshness claim. Preserve nightly ledger/grade ownership. Full research independence and native Brief/Watches/action-board parity remain subsequent required work.

## Relationship to the existing Git-store decision

`DEC:VPS-MACRO-GIT-STORE-KEPT-TIER-NIGHTLY-REPACK-AND-PULL-GUARD` explicitly says off-Git data publication is a pipeline decision still to be made; it is not a decision to keep Git as the permanent data authority. The Chairman's present assignment authorizes that migration. Its pull guard, maintenance, fixed shallow history and issuer revision requirements remain binding while the checkout exists. This program does not re-shallow or move the clone, alter credentials, or claim a disk-capacity purchase. Use incumbent object/domain storage where qualified, not an orphan force-push transport or a second database by default.

## Minimum acceptance for the first independent daily slice

- Source-linked before/after producer map, all fenced old writers, selected snapshot consumers and unchanged nightly finalization owner.
- Existing runtime receipt for a newly completed session with provider clocks, coverage, price-adjustment semantics and immutable snapshot identity.
- A named Sector calculation consuming that snapshot and its declared baseline dependencies with no undeclared repository fallback or ledger effects.
- Same-session correction changes the substantive result and reaches the active consumer.
- New data reaches an already-open authenticated beta view while its frontend deployment is unchanged and the runtime does not need GitHub data publication.
- Outage retains the last accepted generation with truthful qualification; incomplete candidates do not move the pointer; access and rollback proofs hold.
- Remaining legacy product journeys stay reachable and explicitly accounted for.

## Complete worker return (qualified by the ruling above)

All tracing is complete. Final report follows.

---

# Always-on Macro Sector — input/runtime extraction evidence

**Lane** `macro-always-on-20261105-c3-input-runtime-01` (parent `macro-always-on-shared-shell-20261105-c3`). **Pins:** Macro `0c4c28e4a3e1ba0b1dde3ebdd9774355822f1527` (= PR #10780 exact head), Terminal `f9d3280a2a3ff28dd925b128231702b836c8a247`, law `49c2e1d9`. Citations below are all `git show` at those SHAs (`macro@<sha>:path:line`, `terminal@<sha>:path:line`). **No runtime/production read was performed** in this audit; production facts come only from the pin's own evidence JSON. Read-only throughout; extraction workspace `/tmp/aon-sector-input-audit/pin/` holds byte-exact pin copies.

---

## Q1 — Authoritative input trace: Sector page vs basket_pulse live plane

**A. Displayed Sector artifacts (all Git-published; served from `/opt/macro/site.served`)**

| Artifact (site-relative) | Producer (writer) | Schedule / trigger | Source clock | Git dependency |
|---|---|---|---|---|
| `sectordata/sector_central.json` + `sector_central_data.js` + `sector_central.html` + `premiumdata/sector_central.json` | `scripts/build_sector_central.py main(strict=True)` (writes at :714–742, premium :626–637) — engine `engine/sector_central.py::compute`:983 | `sector-intelligence.yml` cron `15 3,12,17,22 * * 1-5` (:12) + push triggers (:15–32); also daily.yml engine step 3755 | `as_of` = cycle `meta.asOf` = **last SPY close in the data/yahoo store** (`engine/sector_cycles.py:1536–1546`) | **Yes** — reads git-tracked inputs, commits outputs back to main (workflow :117–191) |
| `basketdata/baskets.json` (incl. `theme_intel` = theme/industry ranking) + `basketdata/si_handoff.json` (hero verdict, factor season, flow verdict, member registry — written :641–648) | `scripts/build_baskets.py main(sector_intelligence_only=True)` (:239; theme_intel via `engine/theme_scoring.compute_theme_intel`:1011) | SI sequence step 1 (`build_sector_intelligence.py:41–43`); daily.yml band step 3450 | `theme_intel.as_of` (close-matrix session; also reads last committed sector_central.json as T‑1, `theme_scoring.py:229–233,1474`) | Yes |
| `basketdata/action_board.json` — **two writers, two shapes** | bound shape: `scripts/build_sector_action_board.py:53–75` (pins `baskets_sha256`, atomic); bare shape: `scripts/build_site.py:6946–6949` (`{"action_board": ...}`, no as_of/hash) | bound: SI step 2; bare: daily.yml engine job (build_site precedes build_sector_central) | inherits baskets.json as_of (bound shape only) | Yes |
| `sectordata/sector_cycles.json` (**this is the Terminal "history" feed**) + `sector_cycles_data.js` | `scripts/build_sector_cycles.py:297–313`; engine spine shared with central; **nightly-gated forward-log append** :261–262 → `engine/cycle_forward_log.py:271–273` | daily.yml band step 3450 (`scripts/ci/daily_engine_regional_desk_builders.sh:181`) + `render.yml:974` | cycle asOf (SPY closes) | Yes |
| Leadership/history research displays | `engine/sector_central_grader.py` — ledger `data/sector_central/calls.parquet` (:31, write :301–309, **append nightly-gated** :265–270, gate `engine/ledger_lane.py:35–36`); grades vs nightly freeze `data/basket_levels/us.parquet` (:208–228) | nightly only (daily.yml engine, `COLLECT_LANE: nightly` at 2290–2291) | PIT call dates + matured horizons | Yes |

**B. Engine inputs consumed by `compute()`** (`engine/sector_central.py:983–1116`)

| Input | Path (line) | True producer | Clock | Git dep |
|---|---|---|---|---|
| Cycle spine + closes (TR & price basis) | `data/yahoo/*.parquet` via `engine/inputs.py:115–134`, `lib/store.py:469–472` | **DataOS `collectors/yahoo.py` YahooAdapter** (name/group "yahoo", :124–125) run by `scripts/collect.py:160`, driven by `daily.yml` collect job cron 22:30/23:30 UTC (:36–37, step 326/run 403, `COLLECT_LANE=nightly` :380) + `backfill_yahoo_universe` (:489) + `check_price_store_freshness --heal` self-heal (daily :2466, close-pass 20:25, closing-bell 20:05, `refresh_regime_if_stale` in intraday-fastpath `*/30 11-21`/`1-8`); committed to main (daily.yml :663/:737/:920) | last benchmark session | **Yes — 6,738 tracked parquets**; git store by decision (`agentos/decisions/DEC-VPS-MACRO-GIT-STORE-...md:175,183–190`, object-storage option explicitly untaken) |
| Regime anchor | `data/regime/latest.json` (`sector_central.py:111`) | `engine/run.py:1059` (atomic write); daily engine step 2655 (`daily_engine_regime_dashboard.sh:29`), closing-bell :255, earlyclose :200, engine-render :218; `regime-self-heal.yml` 14:05 commit; `render.yml` deliberately does not re-run | daily (session) | Yes |
| Heat (display context) | `{site}/marketdata/sp500_heatmap.json` (`sector_central.py:252–254`) | **Dual plane**: git copy from `intraday-fastpath.yml:123` (committed); live overlay from VPS fast lane `scripts/vps_live_orchestrator.py:419–427` → `/var/lib/macro-live/public/marketdata/` | VPS ~10-min (13–21 UTC); git copy CI cadence | Build-time input = git copy |
| Rotation artifact (fast lens) | `data/us_sector_rotation/latest.json` (:719), session-gated by `engine/sector_generation_guard.py::session_alignment`:62, applied :1069–1084 | `engine/us_sector_rotation.py::compute_and_write` (write :886–890) via `scripts/build_us_sector_rotation.py:26–27`; **only producer: daily.yml step 3746**, before build_sector_central 3755; its own forward_log.jsonl append nightly-gated (:837) | settled daily session | Yes |
| Membership | `data/baskets/membership.json` (:1022) | seed/verify scripts; slow-changing | static-ish | Yes |
| Crowding / narrative rotation calibration | `data/finra/short_interest.parquet`, `data/strategies/thematic_rotation_phase0.json`, `baskets_calibration.json` (`narrative_rotation.py:613–627,845`) | collectors + calibration workflows | slow | Yes |
| Phase-age history | `data/sector_cycles/forward_log.parquet` (`engine/cycle_phase_age.py:62`) | `cycle_forward_log` — **nightly sole advancer** (:268–273) | nightly | Yes |

**C. Existing live plane (VPS, already GitHub-independent) — do not duplicate**

| Artifact | Producer | Cadence | Clock |
|---|---|---|---|
| `state/quotes_full.json` (private) + `public/live/quotes.json` | `scripts/build_live_quotes` (orchestrator :433–442 fast :340–357) | snapshot ~5 min / fast ~60 s | quote `meta.source_asof`, coverage-validated (:439–441, :85–120) |
| `public/live/basket_pulse.json` (+`_lastgood`) / `basket_pulse_hk.json` | `scripts/build_basket_pulse --quotes state/quotes_full.json` (orchestrator :460–479); schema `basket_pulse.v1` (:1219), mode machine live/delayed/last_rth/eod (:42–49), honest delay (:302–307) | snapshot ~5 min | quote clocks + ET/HK session machine (:160–212) |
| `public/marketdata/sp500_heatmap.json` | `scripts/build_sp500_heatmap` (orchestrator :419–427) | fast lane, minute%10==7, 13–21 UTC | live |
| `public/live/staleness.json` | `scripts/freshness_sentinel.py` (30-min timer; sector surface added at this pin :716–725, two-pass `read_sector_generation` :817–860) | macro-sentinel :12/:42 | observation |
| Lane health | `scripts/check_vps_live_health.py` (lane ages only :99–244; **no Sector surface**) via `vps-live-heartbeat.yml` `*/10` | 10 min | — |

**D. beta consumer chain (observed at Terminal pin):** one BFF `terminal@f9d3280a:app/api/sector-intelligence/route.ts` (PATHS :17–32 — `sector` `sectordata/sector_central.json` :18, `history` `sectordata/sector_cycles.json` :24, **`intraday` `/live/basket_pulse.json` :31**, `heatmap` `/marketdata/sp500_heatmap.json` :21; `private, no-store` + Vary Cookie :13–15; fail-closed Supabase auth :112–124; 60/min limit :104; 6 s timeout :154; 4 MiB cap :33; origin pinned :138–149). Workspace `components/sector-intelligence/SectorIntelligenceWorkspace.tsx`: per-feed fetch :140–142, **5-min revalidation of `sector`+`heatmap` only when visible (:172–182)**, content-hash dedupe :163–165, owner-change discard :100. Mount: `DiscoverWorkspace.tsx:7,42,48,100`. **No Brief/watchlist consumer of Sector exists** (0 hits); **no consumer of `action_board.json` or `premiumdata/sector_central.json` in Terminal at all**. Brief research on the Macro side is the row-level `research_handoff` digest binding (`engine/sector_research_handoff.py::attach_handoffs`:220) + nightly grader scorecard — both ledger-derived, daily.

**Net:** every displayed Sector field except the already-live `intraday` (basket_pulse) and `heatmap` sources inherits the git closes store as its clock. The Nov 3 freeze is the closes store being 2 sessions behind after the failed checkout (evidence JSON `workflow_failure`, `served_generation.as_of=2026-11-03, sessions_behind=2`), not a missing publisher.

## Q2 — Smallest safe extraction boundary

**OBSERVED:** `engine.sector_central.compute()` (`sector_central.py:983–1116`) is already the pure, read-only calculation — verified zero writes across the whole module; every side effect lives in `scripts/build_sector_central.py`, `scripts/build_baskets.py`, `scripts/build_sector_cycles.py`. That is the boundary; nothing smaller exists.

- **Daily baseline** = the git-published generation: leadership order, cycle phase/conviction, theme_intel ranking, action board, grader scorecard, history (`rs_history`), research handoffs — all stamped `as_of` (closes session). **Cannot honestly advance intraday.**
- **Live overlay** = fields with independent quote-clock semantics: per-ETF/per-basket last price & 1D %chg, EW pulse (`basket_pulse.v1` already computes this), heat color/breadth (`sp500_heatmap.json`), delay/coverage/mode/staleness state.
- **Runtime generator (proposed):** a new pure assembly module that joins the accepted baseline doc + `state/quotes_full.json` + `public/live/basket_pulse.json` + `public/marketdata/sp500_heatmap.json` into one `sector_generation` doc carrying **two explicit clocks** (baseline `as_of` untouched; overlay quote clock + generation id + coverage), published through the **existing** orchestrator `module()`/`atomic_publish` path (:207–310, :65–83) into `/live/` (already in the Caddy `@vps_external` matcher, `app/deploy/Caddyfile:226–231`; needs one entitlement-list entry, `config/site_access.yml:359–374` pattern). No graders, no ledgers, no HTML, no basketdata/sectordata/premiumdata writes, no new quote scheduler/aggregator/publisher.
- **Side effects that must be avoided** (call-site evidence): `build_sector_central.py:492–499` grader append+grade, :503–511 relative-trend emit, :626–637 premium payload, :714–742 JSON/JS/HTML writes, :752–777 asset copies + holdings-coverage emit; `build_baskets.py` SI-mode **ungated** `data/` writes (themes/emergence alerts+state, `data/baskets/latest.json`, allocation snapshots, EDGAR 8-K enrichment, fear_greed parquet, ai_tag parquets) and a **conditional live ops notification** (Telegram/Discord dispatch, build_baskets :257 → alert_triage :1645/:1740) — so `build_baskets --sector-intelligence` must **never** run on a runtime lane; `build_sector_cycles.py:261–262` forward-log append (nightly-gated; skip anyway).
- **Named consumers (existing):** Terminal BFF `route.ts` (one PATHS addition, existing auth/cache/limit semantics) + `SectorIntelligenceWorkspace.tsx` revalidation (extend the `sector`+`heatmap` refresh set :172–182); Macro sentinel surface (L4a pattern :716–725).

## Q3 — Which producer must move to the VPS

**The closes-store advancer is the only producer whose move is required for a GitHub-independent *daily* Sector advance.** Evidence chain: every Sector artifact's `as_of` = last SPY close in `data/yahoo/` (`sector_cycles.py:1536–1546`); that store advances only in GitHub-hosted runners (`daily.yml` collect 22:30/23:30 UTC + self-heal lanes) and reaches the VPS via deploy (`app/deploy/update.sh:395` rsync `site/`; `/opt/macro` is "code + canonical checked-out inputs", VPS doc :80). The Nov 5 failure was exactly this: refresh died at checkout before computation (`evidence JSON workflow_failure.failed_step=actions/checkout@v4`).

- **Closes — possible but not free:** the collector module itself is runner-agnostic (`collectors/yahoo.py` + `collectors/base.py::run_adapter`:596 → `store.upsert`:663 / `capture_yahoo_observation`), and the VPS already runs network collectors with locks/timeouts/validators and already owns a VPS-local mutable store (`/var/lib/macro-live/data/intraday`, orchestrator bars lane :481–505 — precedent). But the canonical store is a **git store by recorded decision** (62,805 blob versions / 1.28 GB; object-storage option documented as untaken, `DEC-VPS-MACRO-GIT-STORE-...md:183–190`), and writing into `/opt/macro/data/yahoo` would race the deploy's `rsync --delete` and the git writer. A safe supply is a **bounded Sector-slice collector** (SPY + 11 SPDRs + basket members) writing a **VPS overlay store** with explicit deploy-time reconciliation — an L4c writer-transfer with fence, deliberately *not* required by the overlay packet in Q5.
- **Regime — do not move.** `engine.run` needs the yahoo closes panel **and** FRED parquets (`engine/inputs.py::build_features`:162–166, `_fred`:97–112); the VPS doc explicitly keeps the regime-pointer self-heal off the VPS ("not an ephemeral display artifact", :53–57) and `regime-self-heal.yml` stays the canonical 14:05 writer. Regime is daily-quad-scale; moving it doubles the producer surface for no honesty gain.
- **Cycles — nothing to move.** `engine.sector_cycles.compute()` is pure over the closes store; it advances automatically once closes advance. Cycle page artifacts + forward log stay nightly (ledger law, `cycle_forward_log.py:268–273`).
- **Keep off the runtime lane entirely:** all of `build_baskets` (ungated writes + ops notification, §Q2), `build_sector_central.main()` as a whole, `build_sector_cycles.main()`.

## Q4 — Existing owners (reuse, don't rebuild)

Scheduling/supervision: systemd timers + `vps_live_orchestrator.py` (per-lane locks :556–563, timeouts, validators, staging discipline :220–243). Publication: `atomic_publish` + Caddy existence matchers with `/opt/macro/site.served` fallback (doc :88–97; Caddyfile :84,:1135,:184–186 "prevents a main-branch pull/rsync from rolling a fresh tick back"). Validation gate: `check_sector_intelligence_freshness.evaluate` (shared by build gate and sentinel). Observer: `freshness_sentinel.py` sector surface :716–860 + `staleness.json` + `check_vps_live_health.py` + `vps-live-heartbeat.yml`. API/BFF/identity: Terminal route + `lib/sectorIntelligence.ts` contracts (`rotation_events.v1` display-authority tier :177–178, `feedSourceStamp` :242–245) + Supabase cookie gating + `config/site_access.yml` premium enforcement. Quote service & pulse: `build_live_quotes`, `build_basket_pulse`. Nightly canonical writers & ledger lane law: `engine/ledger_lane.py:24–38`, daily.yml `COLLECT_LANE: nightly`. Route registry: compiled page registry + `sharedShellRoutes.ts` (no sector route registered — page-path projections only). DAG inventory: `config/dag.yml` (lanes/steps inventory, **not** a scheduler — :3–9). R2 owners: `publish_r2.py` covers OHLC/stockdata families only — **no yahoo, no sector payloads on R2** (0 hits); `data/yahoo` is a git store.

## Q5 — Next bounded write-set, tests, open overlaps

**Packet (Macro, existing carrier `sol/web-macro-always-on-shared-shell-20261105-c3`, normal protected release):**
1. New `engine/sector_live_overlay.py` — pure join: accepted baseline doc + quotes snapshot + `basket_pulse.v1` + heatmap → `sector_generation.v1` doc (baseline block byte-faithful + overlay block + generation id = sha256 over pinned input digests + publication record). No writes.
2. New `scripts/build_sector_live_generation.py` — runtime CLI: reads VPS paths (`state/quotes_full.json`, `public/live/basket_pulse.json`, `public/marketdata/sp500_heatmap.json`, baseline from `/opt/macro/site.served/sectordata/sector_central.json`), fail-closed on partial/malformed inputs, stages output only.
3. `scripts/vps_live_orchestrator.py::snapshot` — add one `sector_overlay` task after the basket pulses (:460–479), validator = schema + non-vacuous + clock checks, timeout ≈90 s, publish `public/live/sector_generation.json` (+ `_lastgood` sidecar, reusing lastgood conventions).
4. One entitlement-list entry for `/live/sector_generation.json` (`config/site_access.yml:359–374` pattern; Caddy `@vps_external` already matches `/live/*`).
5. One `freshness_sentinel.SURFACES` entry observing the generation (source clocks/coverage; L4a pattern :716–725); optionally one lane-age surface in `check_vps_live_health.py`.
6. Explicit non-writes: no grader/ledger calls, no `build_baskets`, no basketdata/sectordata/premiumdata/HTML writes, no additions to `sector-intelligence.yml` triggers.

**Terminal (separate carrier, its own release rules):** one PATHS entry `sector_generation: "/live/sector_generation.json"` in `route.ts:17–32` + optional qualification; extend the workspace refresh set to the new feed with its own clock display (`lib/sectorIntelligence.ts` contract + `SectorIntelligenceWorkspace.tsx:172–182`).

**Tests (meaningful, discriminating):** (a) parity/golden — `compute()` on pinned representative inputs reproduces the accepted baseline doc (reuse accepted evidence; rerun only what changes); (b) side-effect discriminator — tmpdir run with fs snapshot: zero writes outside staged outputs; grader/ledger/site writers monkeypatched to raise must never be invoked; (c) atomic generation validation — partial bundle or malformed quotes ⇒ refuse pointer/publish, previous accepted generation retained; (d) upstream outage/correction — missing/stale `quotes_full.json` ⇒ overlay mode `delayed`/`unavailable` with true age and unchanged baseline `as_of`; same-session corrected closes ⇒ new generation id, reader-side hash/generation compare invalidates (mirrors `feedSourceStamp`/content-hash dedupe, Terminal tests under `lib/__tests__/`); (e) independent browser refresh — sentinel two-pass stable read of the new surface + Terminal 5-min/visibilitychange behavior with separate clocks (mirror `sectorOwnerGateway.test.ts` / e2e `sector-intraday-pulse` fixtures). **Acceptance:** generation advances on the VPS with the GitHub path removed (simulated), zero ledger/HTML writes proven, BFF private/no-store + entitlement unchanged, open-tab update within the existing ≤5-min cadence plus visibility revalidation, sentinel observes it, and nightly graded ledgers stay single-writer (KILL-INTRADAY-CHRONICLE preserved).

**Unresolved questions / active writer overlap (no historical owner assigned as approver):**
1. `action_board.json` dual writer — bare `build_site.py:6946–6949` vs bound `build_sector_action_board.py:53–75`; the served production file's missing-metadata shape matches the bare writer (evidence JSON marks exact attribution unproven — **EFFECT_UNKNOWN preserved**). Fence before any cutover touching that path; never add a third writer.
2. `sp500_heatmap.json` dual-plane writers (GitHub `intraday-fastpath.yml:123` vs VPS fast lane); precedence is documented at the serving layer (Caddyfile :226–231), but build-time heat freshness on the macstudio workspace is unverified.
3. The closes-store carrier decision (git vs object storage) is owned by `DEC-VPS-MACRO-GIT-STORE-...`; a VPS closes writer must reconcile with that decision and the deploy `rsync --delete` — the real L4c writer transfer, larger than this packet.
4. GitHub's `intraday-fastpath.yml` still produces basket_pulse/heatmap/regime-heal alongside the VPS — two existing writers on those artifacts; writer-transfer must fence, not add a third.
5. Terminal consumes neither `action_board.json` nor `premiumdata/sector_central.json` — premium withheld rows cannot reach beta today; entitlement/product decision outside this packet.

**Durable copy:** `/tmp/aon-sector-input-audit/REPORT.md` + byte-exact pin extracts under `/tmp/aon-sector-input-audit/pin/`. **Marked throughout: OBSERVED = read at the pinned SHAs; INFERRED = reasoning over those reads; no runtime read performed; no production or completion claim.**

