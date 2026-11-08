# Yahoo close ownership census — parent adjudication, November 6

Mission: [always-on Macro migration #10779](https://github.com/mastermindx-market-intelligence/macro/issues/10779).
Original Fabric run: `macro-always-on-20261105-c3-close-owner-01`; original root: `macro-always-on-shared-shell-20261105-c3`.
Complete response: 20,694 bytes; SHA-256 `ef102e1d5ef85b4886d97c724bf3628599b2d0fd74978f28239ddfd2bd7e7d58`; terminal rc0, root verified, whole response consumed. Accepted only within the qualifications below. The report's internal lane alias does not replace the actual original run identity.

## Parent ruling

1. Accept the source-linked collector/reader census, dual price basis and whole-overlap correction semantics, existing Yahoo availability-capture mechanics, and separation of calculation from nightly ledger writes. Parent inspected `lib/store.py`, `collectors/base.py`, the dataset registry, and the current source ownership documents at the compatible pins.
2. Reject the proposed commercial licensing blocker. Protected [COMMERCIAL_DATA_RIGHTS.md](https://github.com/mastermindx-market-intelligence/Mastermind/blob/49c2e1d93e5e080b1671c98087a845e5beb09dd5/docs/COMMERCIAL_DATA_RIGHTS.md) and [the standing decision](../../agentos/decisions/DEC-COMMERCIAL-DATA-RIGHTS-CHAIRMAN-ATTESTATION-20261023.md) record APPROVED_BY_CHAIRMAN_ATTESTATION for the named incumbent Yahoo/yfinance route across assigned projects. The fixed nine ETFs are explicitly included; the wording does not establish an exclusive nine-symbol provider license. The older `vendor_terms_personal_use` registry annotation cannot reopen that settled commercial gate. This migration reuses the incumbent provider/adjusted-price route; it does not add a provider, invent a contract, establish PIT availability or override an observed access denial.
3. Correct the minimum cycle price dependency set: the report identifies 11 SPDRs plus SPY, QQQ and IWM, then proposes a 12-name cutover. Use all **14** when claiming the complete existing cycle calculation. Do not silently drop QQQ/IWM or substitute different adjustment bases.
4. Fresh ETF closes alone do not make theme baskets, market context, rotation history, phase-age history or the whole Sector product fresh. Each dependency needs its own identity, source date and qualification. The canary must name exactly which fields advance; original Brief/Explore/Research/Watches and theme coverage remain in scope.
5. Preserve the existing store, collection acceptance, R2 transport, runtime orchestrator and publication owners. The proposed file list is design input, not permission to introduce duplicate collectors/promoters or to use process-global `config.ROOT` mutation. Resolve explicit-root/source selection, old-writer fencing and deploy overwrite semantics before production transfer. No collector or live writer was enabled by this audit.
6. The worker could not independently verify the protected-law object and correctly remained read-only. The parent already holds the compatible verified protected pin. Accept the source evidence, not a claim of worker write admission or production proof.

## Original complete worker response

Census complete and saved to `/tmp/aon-yahoo-closes-census/REPORT.md`. Returning the report:

---

# Yahoo daily-close lineage — US SPDR sector cohort source-ownership census

Lane `macro-always-on-20261105-c3-yahoo-closes-census-01` (parent `macro-always-on-shared-shell-20261105-c3`). **Read-only throughout**: no source/config/data edit, no collector or provider call, no deploy/CI/push. All citations are `git show` reads at **Macro `86e8da1ff4c316affe402ae480cde0002550762b`** (`macro@86e8da1:<path>:<line>`). Parent adjudication + master plan read at the same pin and treated as qualified predecessors, not re-argued.

Law pin: protected Mastermind `49c2e1d9…` (skillpack 1.0.1). **PIN_VERIFICATION_UNVERIFIED_LOCALLY** — no local Mastermind git object for that SHA exists (lane copies of `docs/sol_skills/INDEX.md` are plain checkouts with matching `skillpack_version: 1.0.1`, not git-verifiable). Per the INDEX atomic-load law, read-only investigation continued with this explicit warning; no modifying workflow attempted.

## 0. Cohort identity (observed)

- 11 SPDRs `config.yml:7526` (`sectors: [XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY]`); SPY `config.yml:7529` (first of `extras`). Store: `data/yahoo/<T>.parquet`, git-tracked (6,738 files at pin; SPY/XLB/XLC/XLRE verified tracked).
- Dual basis: `close` = total-return (Adj Close), `close_price` = split-adjusted div-unadjusted (`collectors/yahoo.py:1-17`; `lib/dataos/price.py:257-258` TRADJ/SADJ), fetched `auto_adjust=False` (`collectors/yahoo.py:408`).
- **Adjustment semantics**: Yahoo re-adjusts the whole series each fetch — overlap governed by `store.basis_shifted` (`lib/store.py:562`) + `upsert_basis_tol` (`config.yml:7520`), rebased via period=`max` refetch (`collectors/yahoo.py:323`); `upsert(overwrite_overlap=True)` gives the fresh pull ownership of its whole span with stale-span refusal (`lib/store.py:500-561`). **A new-rows-only snapshot is not a valid unit of this lineage.**
- Aliases: `lib/ticker_aliases.py:14-18` (fetch under vendor symbol, store under membership key; cohort currently unaliased). Mutable alias: `lib/config.py:14,35-36` — `data_dir()` = `<repo>/data`, **no env/data-root override exists at this pin** (`.env` loader `:18-27` feeds secrets only). Sanitizer `lib/store.py:469-474` does not affect the 12 cohort names.

## Q1 — Complete writer/consumer enumeration

Every network writer funnels through `collectors.base.run_adapter(YahooAdapter())` (`collectors/base.py:596`) → us-session filter (`:647`; `lib/market_session.py:59-75`) → `store.upsert` (`:663-667`) → optional capture receipt (`:669-682`).

**Writers (collection writers)**

| # | Writer | Trigger / step | Note |
|---|---|---|---|
| W1 | `scripts.collect` yahoo registry entry (`collect.py:160` → `_run_one:108`) | `daily.yml` collect job cron `30 22`/`30 23 * * *` (`:36-37`), `COLLECT_LANE=nightly :380`, step `:326-404`; `--full-history` variant `backfill.yml:46-60` | primary nightly writer |
| W2 | `refresh_regime_if_stale.py::_repull_yahoo` (`:101-110`; conditional heal `:127-143`) | `intraday-fastpath.yml:66-79` (`*/30 11-21 * * 1-5`, RTH-gated) | conditional heal |
| W3 | `check_price_store_freshness --heal` (`:56-80`, calls `_repull_yahoo`) | `daily.yml:2478`; `close-pass.yml:301` (scratch — writes discarded, `close_pass_host_runner.py:434-444`); `closing-bell.yml:130`; `earlyclose.yml:117` | heal, 4 sites |
| W4 | `backfill_yahoo_universe.py` (`store.upsert :791`) | `daily.yml:489-512` `--cap 400 --refresh-all`; `config/dag.yml:63-77` | additive backfill |
| W5 | In-fetch fallbacks inside W1/W2/W4: Stooq extras fill (`collectors/yahoo.py:370-396`, `lib/stooq.py`), basis rebase (`:323`), delisted drop (`:40`) | same triggers | different-source bars can enter the same store |
| W6 | Manual/one-shot seeds: `seed_extra_tickers.py:51`; `spvector_baseline.py:55` (^GSPC); `backfill_price_basis.py` (one-time `close_price`, not via `store.upsert`, `:234`); `fetch_basket_extras.py::_seed_proxies` (`:173-182`, direct `to_parquet`, absent-only; PROXIES `:66-73` — no cohort names) | out-of-band | un-fenced dir writers |
| W7 | `heal_shallow_caches.py` (local donor copies into `data/yahoo`; `TARGET_DIRS :106`) | `daily.yml:6059 --nightly` | cohort practically inert (deep) but unfenced |
| — | `collect_sector_etf_ohlc.py` (exact 11+SPY UNIVERSE `:33-37`) | manual research | **compatibility copy** → `data/yahoo_ohlc/` (worktree-local, gitignored-by-convention `:6-7,:197`), not canonical |

Snapshot/receipt mechanism in the same owner: `store.capture_yahoo_observation` (`lib/store.py:163-180`) + `_capture_yahoo_images` (`:289-372`) → content-addressed immutable objects+receipts under `data/yahoo/.availability_capture/` (schema `yahoo.availability_capture.v1`; "no hook in upsert" `:342-343`; **not git-tracked** — verified). Cohort `YAHOO_CAPTURE_COHORT` (`lib/store.py:40`) = **nine only (XLB/XLE/XLF/XLI/XLK/XLP/XLU/XLV/XLY); XLC, XLRE, SPY outside it**.

Not writers: `asia-close.yml:276` `collect --group asia`; `weekly.yml:108` / `intl_etf.yml:45` `--only` exclude yahoo; `render.yml` runs "no collect" (`:780`), replay band runs builders only (`:974`).

**Consumers (cohort-relevant readers)**

| Reader | Access | Citation |
|---|---|---|
| `engine.inputs.yahoo_closes(basis)` — whole-universe panel | `store.read("yahoo", …)` | `engine/inputs.py:115-134`, `_yahoo_close :21-43` |
| `sector_cycles.compute` | TR + price panels | `engine/sector_cycles.py:1516-1533` |
| `sector_central.compute` | panel | `engine/sector_central.py:998-1005` |
| `us_sector_rotation.load_inputs` | panel | `engine/us_sector_rotation.py:723-727` |
| `sector_central_grader` (nightly canonical grading) | panel | `engine/sector_central_grader.py:196-199` (used `:62,:276,:555`) |
| SPY session anchors | SPY tip | `refresh_regime_if_stale.py:53-61`; `check_price_store_freshness.py:17-23`; `sector_cycles.py:1536-1546` |
| Freshness/audit guards | store reads | `check_yahoo_freshness` (`collectors/yahoo.py:513`; SPY in ENGINE_CRITICAL_SERIES `:508-512`); `audit_store_freshness :569` (called `collect.py:1123-1128`) |
| Compatibility copies | store → site/R2 | `build_chart_data.py:225` → `site/ohlc/<T>.json` (`build_site.py:8397`) → R2 `ohlc` family (`publish_r2.py:76-79`) |
| Basket tail-splice fallback | yahoo ranked 3rd | `engine/basket_index.py:195-230` |

## Q2 — Existing snapshot contracts; hosting owner without a new store/controller

- **Contracts**: `config/dataset_registry.yml:104-151` `equity.bars.daily.yahoo` (L1 PRODUCED, dual_basis, PRIMARY_ONLY, `licensing: vendor_terms_personal_use :124`); read modes CURRENT/RECONSTRUCT/REPLAY (`lib/dataos/read_contract.py`, D00.D1); correction-aware action-revision views (`lib/dataos/price_views.py` — V2 direction, **not wired to the yahoo store**); one-snapshot binding (`lib/dataos/basket_read.py`).
- **The only existing Yahoo-specific immutable materialization** is the availability-capture receipt (§Q1) — nine ETFs, content-addressed, decoupled from `upsert`.
- **`terminal_materialization.py` is not a Sector/Yahoo publisher** (verified): `OUTPUT_DATASET = terminal.bars.daily.ohlc_json`, `PRODUCER_PATH = ingest/build_polygon_universe.py` (`:27-30`) — a Polygon producer on the Terminal carrier. Disqualified as host; only its rows-codec+sha256 binding pattern is reusable.
- **R2**: `publish_r2.py`/`fetch_r2.py` are the existing store/controller pair for gitignored data-dir stores (`_DATA_DIRS :117-…`, incl. `odds_ohlcv` — explicitly yfinance deep history hydrated from R2 `:119-123`; restore→advance→gated publish-back wired `daily.yml:320`; shrink/bytes-floor fences `:229-260`). `data/yahoo` is in **neither** list (git-tracked).
- **Git store**: DEC:VPS-MACRO-GIT-STORE-KEPT-TIER — nightly repack + pull guard binding; moving `data/yahoo` off main is **option 1, explicitly needing its own PR, not decided** (`:180-190`).
- **VPS runtime stores**: `/var/lib/macro-live/data/intraday` bars-lane precedent (`vps_live_orchestrator.py:481-505`, locks/timeouts/validators `:507-581`); `/opt/macro` = "code + canonical checked-out inputs" (`docs/VPS_LIVE_ORCHESTRATION.md:77-84`).

**Determination**: without a new store/controller, the only owner that can host the accepted cohort snapshot for *both* runtime consumption and legacy Git builders + nightly grading is the **existing canonical seam `lib.store.read` over `data/yahoo/`**, fed by exactly one promoted producer. The snapshot is generated as an immutable candidate using the existing availability-capture conventions; the existing R2 `_DATA_DIRS` controller is the qualified off-Git transport *if and when* the cohort leaves git tracking (DEC option 1 — separate pipeline decision; a dir entry there is configuration of the existing controller, not a new store). VPS live data dir is the shadow/staging host; anything written under `/opt/macro/data/yahoo` must be deploy-reconciled against the `rsync --delete` race (prior audit's open question 3, still unresolved).

## Q3 — Minimal `sector_cycles` dependency trace and the explicit-input seam

`engine.sector_cycles.compute(asof=None)` (`:1507-1700+`), all observed: TR panel (`:1516-1521`); price panel, load failure degrades to labeled `tr_fallback` (`:1522-1531`); asOf = last **observed** SPY close, not raw calendar tip (`:1532-1546`, `_latest_cycle_session :1383`, emitted `:1647`); thematic membership `data/baskets/membership.json` (`:1290-1299`); amalgam membership `data/baskets_{nasdaq,russell}/membership.json` + QQQ/IWM benchmarks (`:1311-1314,:1330-1339,:1317+`); phase age from `data/sector_cycles/forward_log.parquet` read-only (`engine/cycle_phase_age.py:53-73`, consumed `:1600-1615`); rhythm + `hazard_parity.LIVE_HAZARD_PARITY` module constant (`:1616-1645`). **Not read by compute(): rotation, regime, heat, narratives, calibration** — those are `sector_central`/builder-side; rotation enters the *payload* at builder level (`build_sector_cycles.py:151-180`, site `rotation_events.json` + `sector_fragmentation.json`, session-aligned).

Side-effect boundaries (verified): `compute()` performs **zero writes**; the forward-log append lives in the builder (`build_sector_cycles.py:259-265` → `engine/cycle_forward_log.py:238+`, nightly-gated `:271-273` COLLECT_LANE/US_LANE). `us_sector_rotation.compute_and_write(asof)` writes `latest.json` (`:886-900`); its JSONL append is nightly-gated (`:157,:828-841`). Correction contract declared `none_native` (R3A-92, `:1683-1690`).

**Minimal close cohort of compute()**: 11 sectors + SPY + QQQ + IWM (thematic basket members read `data/baskets/ohlcv` primary and do not bind the yahoo slice).

**Seam**: partially existing — `compute(asof=…)` / `compute_and_write(asof=…)` accept an explicit evaluation date; `build_features(overrides=…)` (`engine/inputs.py:137-139`) is the house precedent for injected panels. Missing: `yahoo_closes()` has no explicit panel/root injection (reads the global store; no data-root override exists). Ledger-free advance = explicit panel/root injection (or canonical-store promotion, which needs no code seam) + calling `compute`/`compute_and_write` directly — never the builders (`build_baskets --sector-intelligence`, `build_sector_central.main`, `build_sector_cycles.main` carry ungated data/ writes + ops notification, unchanged at this pin). The seam is only named here; extraction implementation is the parent's separate underway workspace (not done).

## Q4 — Fences, cutover, rollback, correction identity

Target: the runtime cohort collector becomes the **single writer of record** for the 12 cohort series; the canonical store remains the compatibility snapshot transport for legacy builders + nightly grading (parent-sanctioned; no silent resume of independent collection during outage).

**Required old-writer fences**:

| Fence | Site | Change class |
|---|---|---|
| F1 | `daily.yml:326-404` + `collectors/yahoo.py::all_tickers :135`/`fetch :172` | cohort excluded from nightly fetch (or fetch converts to snapshot consume); keep the 70%-coverage tripwire (`:233`) and SPY freshness guard (`:508`) truthful |
| F2 | `refresh_regime_if_stale.py:101-110` + `intraday-fastpath.yml:66-79` | heal becomes snapshot consumer (or cohort-excluded re-pull); store-behind-market logic (`:113-143`) stays referee |
| F3 | `check_price_store_freshness --heal` at `daily.yml:2478`, `close-pass.yml:301`, `closing-bell.yml:130`, `earlyclose.yml:117` | same conversion; `data/quality/price_store_freshness.json` marker keeps recording |
| F4 | `backfill_yahoo_universe.py` (`daily.yml:489-512`) | skip cohort tickers |
| F5 | close-pass scratch heal (`close-pass.yml:301`; discard contract `close_pass_host_runner.py:434-444`) | keep scratch contract; cohort excluded or documented as discarded |
| F6 | `heal_shallow_caches.py` (`daily.yml:6059`) | explicit cohort skip guard |
| F7 | Deploy reconciliation | order `/opt/macro/data/yahoo` writes against deploy `rsync --delete` and the DEC's pull guard/repack; no clone-depth/credential change |

F1–F4 degrade the right way in outage: heals resolve to the last accepted snapshot with truthful qualification, never an independent re-fetch.

**Shadow-before-cutover**: produce the candidate via the existing capture conventions (immutable objects+receipts, decoupled from `upsert`, `lib/store.py:342-343`), validate parity vs the incumbent store tip (`store.basis_shifted`, `check_yahoo_freshness`, `audit_store_freshness`), then promote at exactly one site. **Compatibility reader changes: none** — `lib.store.read` consumers see the promoted tip unchanged; `render.yml:974` band stays off-lane.

**Rollback**: previous canonical parquet bytes (git history of `data/yahoo`; nightly repack two-week grace per DEC) are the rollback target; producer rollback = explicit unfence of F1–F4 via reconciliation, never a silent dual-writer resume. Pointer-side rollback reuses existing lastgood conventions.

**Correction identity (same session)**: no native revision field (R3A-92). Identity = content-addressed generation (merged-image sha256 in the receipt; prior generations retained) + consumer-side generation/hash compare (Terminal `feedSourceStamp`/content-hash). Substantive replacement = `upsert(overwrite_overlap=True)` full-span ownership with stale-span refusal (`lib/store.py:536-556`); basis drift re-routes to period=`max` rebase. Nightly forward logs keep FIRST per (date,id) — a corrected same-session value does not rewrite the logged nightly signal; that asymmetry is the declared contract. **Intraday substitution rejected** — the VPS Polygon bars lane is a different basis/session; no equivalence evidence.

## Q5 — Licensing/entitlement assumptions (existing source contracts only)

- `DEC:COMMERCIAL-DATA-RIGHTS-CHAIRMAN-ATTESTATION-20261023` (`:50-54`): APPROVED_BY_CHAIRMAN_ATTESTATION for the Research Factory incumbent Yahoo/yfinance adjusted-price route, "explicitly including **XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY**" — the fixed nine (= `YAHOO_CAPTURE_COHORT`; AGENTS.md "fixed nine sector ETFs").
- **XLC, XLRE, SPY are not named in the attestation.** For them the binding in-repo artifact remains `config/dataset_registry.yml:124` `vendor_terms_personal_use`, with the yahoo group's vendor terms recorded adverse-never-cleared (`DSC-COMMODITY-AND-FX-…:5-9`). **UNKNOWN** whether runtime-lane republication of XLC/XLRE/SPY is covered by any existing contract — qualify or type `rights_blocked`/`unknown` before cutover; not assumed.
- Unresolved independent of permission: the historical adjusted-price vintage/PIT gate (RF-T01; receipt `upstream_revision_history_complete: False`, `lib/store.py:355-360`). No secret values read; no new paid infrastructure proposed.

## Minimum file set for the next implementation (nothing written in this run)

1. **NEW** `scripts/vps_collect_sector_cohort.py` — cohort-bounded collector reusing `YahooAdapter._download/_extract` + `run_adapter` acceptance semantics (aliases, `auto_adjust=False` dual basis, us-session filter, basis guard, coverage tripwire), emitting accepted snapshot + capture receipts; fail-closed on partial results.
2. **EDIT** `scripts/vps_live_orchestrator.py` — one task in an existing lane (`module()` lock/timeout/validator pattern `:481-505`).
3. **EDIT** `lib/store.py` — extend `YAHOO_CAPTURE_COHORT :40` to the 12 names (gated on the Q5 qualification) or add a separate snapshot-receipt cohort.
4. **NEW** `scripts/promote_sector_snapshot.py` — staging → validation (`store.basis_shifted`, `check_yahoo_freshness`, `audit_store_freshness`) → single-site canonical promotion + receipt; deploy-reconciliation hook (F7).
5. **EDIT fences**: `collectors/yahoo.py`, `scripts/refresh_regime_if_stale.py`, `scripts/check_price_store_freshness.py`, `scripts/backfill_yahoo_universe.py`, `scripts/heal_shallow_caches.py`; `daily.yml:326,:2478`, `close-pass.yml:301`, `closing-bell.yml:130`, `earlyclose.yml:117`, `intraday-fastpath.yml:66-79`.
6. **EDIT** deploy ordering point (`app/deploy/update.sh`) — pull-guard/repack/shallow fences untouched.
7. **Tests**: NEW cohort-collector tests (parity golden, repository-fallback detector, zero-ledger-write discriminator with grader/ledger/site writers forced to raise, correction invalidation, outage/lastgood); EDIT `test_yahoo_availability_capture.py`, `test_check_price_store_freshness.py`, `test_refresh_regime_if_stale.py`, `test_close_pass_lane.py`. Collector edits trip the existing CI pack (`ci.yml:774-781`).
8. **EDIT** `config/dataset_registry.yml` (XLC/XLRE/SPY rights row once qualified; extend the established registry — **no second registry**), `config/dag.yml` producer row. **NO** new store/controller, scheduler, queue, or page registry (the 353-entry registry stays the inventory authority).

Runtime-lane non-writes: no grader/ledger calls, no `build_baskets`/`build_sector_central.main`/`build_sector_cycles.main`, no sectordata/premiumdata/HTML writes, no forward-log append (nightly gates stay sole advancers).

## Falsifiable acceptance

- **A1 — naturally new daily session.** After a completed NYSE session *D* never before observed, the runtime collector produces an accepted snapshot: effective session *D* (SPY tip = *D* under `lib.nyse_calendar`), coverage 12/12 with per-name provider clocks, both bases present, basis-drift check clean, immutable generation id (merged-image sha256 + receipt). After promotion, with no GitHub data commit and no frontend deploy, `sector_cycles.compute` `meta.asOf = D` with per-sector cycle/osc/RS-rank records re-stamped and `us_sector_rotation` timing states recomputed from the same panel. Falsified if any field shows *D−1* while claiming current, or any ledger/forward-log row lands outside `COLLECT_LANE=nightly`.
- **A2 — nightly consumes the same snapshot.** Next nightly: `sector_central_grader` (`:196-199`) reads the promoted tip (asOf *D*); fenced writers F1–F4 performed zero cohort fetches in the window (receipt/log-provable); non-cohort universe collection unchanged. Falsified if the nightly re-fetches any cohort name or grades a different tip.
- **A3 — same-session correction.** A provider correction to session *D* after acceptance yields a new generation (different sha256; prior receipt retained), changes the substantive *D* result measurably, invalidates consumers via generation/hash compare, and leaves the forward log's *D* rows keep-FIRST. Falsified by a silent same-generation absorb or a stale value surviving past revalidation cadence.
- **A4 — outage.** GitHub down + frontend build failing: runtime advance for *D* still completes and reaches the store; incomplete candidates never move the pointer; last accepted generation retained with truthful stale/degraded qualification. Falsified by any silent old-writer resume or vacuous pointer move.

**Preparatory vs production**: tests consuming a pre-seeded/pinned snapshot are preparatory (BUILT_NOT_PROVEN). True GitHub-independent production (A1+A4 under a GitHub-path-disabled drill, observed by an open authenticated beta consumer and the sentinel) is **not proven by this census**. No runtime/production state was read; only pinned source.

---

**Durable copy**: `/tmp/aon-yahoo-closes-census/REPORT.md`. DO_NOT_REDO respected: prior audit facts reused with citations, not re-derived; Sector fusion extraction untouched; no second registry created; prior action-writer/CI worktrees untouched. No completion or production claim; next dependency is the parent's decision on the F1–F7 fence ordering and the XLC/XLRE/SPY rights qualification.

