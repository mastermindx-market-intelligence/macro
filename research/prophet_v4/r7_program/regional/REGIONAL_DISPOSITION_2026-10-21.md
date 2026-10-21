# Prophet Stage 5 — regional disposition (China · Hong Kong · Canada · shared)

As of 2026-10-21 ~03:30Z (updated as lanes return). BASE = macro main `e5dd30c6344e4b62a0beba054ac4da97e00bab36`.
Commission: Prophet seat 69eb9a1c, Stage 5 (masterplan §10, Appendix A4). Orchestrator: Opus 5.5, ROUTE orchestration.
This page assigns a status to each obligation. It grants no merge, release, rights or rank authority.

**Verdicts.** READY = custody is clear, dependencies are met and a frozen next lane exists. BLOCKED-CUSTODY = an incumbent PR/branch/writer holds the artifact, so route to it. BLOCKED-DATA = a missing accepted input, rights ruling or receipt. BLOCKED-ORDER = waits on the accepted adoption order (#8444 → HK → China) or an upstream package. NEEDS-FABLE-DECISION = a reserved parameter or priority call. ACCEPTED = accepted with evidence (DO_NOT_REDO). STANDING = a law or constraint that holds and is not a work item.
These map onto masterplan A4's valid dispositions: ACCEPTED = accepted with evidence; READY = still required; the BLOCKED-* verdicts = blocked by a precise dependency or owner. Nothing here is "deferred" without an authority.

**PR facts.** One batched GitHub read at 03:10Z; table in seat scratchpad `regional_prs.tsv`:
- #8444 is an open draft (sol/ branch). It changed 10-20 and spans 71 files. Its only regional files are `templates/canada.html.j2`, `site/canada-stock-v36.js` and the Canada mobile layout JSON. It touches no China or HK files and not `build_canada.py`.
- #6871 is an open draft with the Sol hold label and REQUEST_CHANGES. It touches only `research/cn_prophet_recovery/*` and `tests/test_cn_prophet_recovery_r0.py`.
- #8714 is an open research draft at efab78a1, with 476 research files.
- #7018 is an open draft on a sol/ branch. Its hunks in `build_canada.py` sit at the import (~37) and in `main()` (~1471).
- #7286, #7288, #7385, #7303, #7248 and #6996 are open drafts. #7499 is an open draft on a sol/ branch.
- #7277 merged 09-25 at 39f3fcb2. #7163 closed unmerged 09-25. #6872 merged 09-24 (WTI Live Trace, merge ac61896d).
- #8184 is open on a sol/ branch and touches `templates/china.html.j2`.

**Residual custody risk.** The file census of older open PRs failed (HTTP 502 twice). Collision checks therefore cover the named incumbents plus the 100 most recently updated open PRs. Before any build lane is merged, a fresh file-collision check is owed.

## 1. China Prophet correctness (§10.1; A4 "China Prophet correctness")

| id | obligation | current evidence | owner / custody | DO_NOT_REDO | verdict | next lane / owner |
|---|---|---|---|---|---|---|
| CN-P0 | Original truth: immutable originals, typed append-only corrections, source/basis/session identity | #8714 `IMPLEMENTATION_HANDOFF.md:66-78` (efab78a1; pin 3d90aad6) freezes the values: quarantine the 08-26/08-27/09-04/09-15/09-18 bakes instead of overwriting; 133/289 stays the original accounting and 129/289 is a separately named comparison; append-only corrections with reason, target and a strictly later recording time; OHLC retention. Its first line is "Start on the incumbent R0 carrier after fresh custody reconciliation". Census `cnscout` (`CN_CORRECTNESS_CENSUS_2026-10-21.md` on lane commit f18ef8a8): keep-first is PRESENT (`engine/china_prophet_shadow.py:614-617`, `engine/china_standout_track.py:861`, `engine/cn_prophet_audit.py:55-56`); there is no CN corrections store; quarantine is ABSENT, and `board.parquet` still holds all five bakes (113/116/145/85/105 rows); 133/289 is absent at BASE because accounting is recomputed (`engine/cn_prophet_audit.py:566-584`); OHLC is PRESENT via `collectors/_stock_ohlc.py` | The R0 carrier is #6871 (open draft with the Sol hold label and REQUEST_CHANGES, head 51ddb898; files are research plus `tests/test_cn_prophet_recovery_r0.py`). P0's main paths include `scripts/build_china_library.py`, which the CN-P1 lane also edits | The 104 producer and 86 independent vintage controls; 39/683 and 21 disagreements; R0 economics stay disputed | **BLOCKED-CUSTODY**. The spec is decided. The carrier is held | Seat reconciles P0 custody with the #6871 incumbent (F3a). The build starts only after that, and after CN-P1 lands, because both edit `build_china_library.py` |
| CN-P1 | Canonical pack: read the board once, measured zero, full-universe tradability, archive the armed pack | #8714 §P1 (`IMPLEMENTATION_HANDOFF.md:79-93`) plus `repairs/integration_contract/REPAIR_DECISIONS.md:59,70` plus `tradability_lab/DECISION_MEMO.md`. Each part at BASE: **(i) projection (dead in production; found by the orchestrator, missed by the census)**: `scripts/build_cn_live_pack.py:45-79` `load_frozen` reads only `site/china_standouts.json` / `data/china_standouts.json` with a `lanes`/`names` schema, while the nightly writes `site/factordata/china_standouts.json` (`scripts/build_china_library.py:4544,5058`) with the four primary arrays plus the `watch` alias and a nested `prophet.score`/`board_rank`/`score_rank`. The production frozen map is therefore `{}`: no frozen score or rank reaches the pack, and the tests inject `frozen=` (`tests/test_cn_live_pack.py:80`). The BASE board (as_of 10-16) has 108 unique primary tickers, and `watch` (84) is exactly the union of the last three arrays. **(ii) tradability**: the predicate is at `scripts/build_china_library.py:72`; the nightly applies it at `:2529-2542` with inline maps at `:2202-2272`; the pack's `main()` never passes `tradable` (`build_cn_live_pack.py:205-225`) and `build()` fails open (`:97-98`). **(iii) archive**: ABSENT; `--publish` overwrites the single key (`:229`; `engine/prophet_live/r2io.py:38,110`) | No open PR touches `build_cn_live_pack.py`, `engine/prophet_live/cn_pack.py`, `build_china_library.py` or `tests/test_cn_live_pack.py` (named incumbents incl. #8444 71 files and #7669 all 471, plus the 100 newest open PRs) | #8714's 77 offline checks and its 180-name positive control; do not re-run the lab | **READY**: (i) and (ii) as two lanes on separate functions of one file; (iii) READY but sequenced after (i)+(ii) | Lanes `cnp1proj` (packet written; owns `load_frozen` body, `cn_pack.py`, new `tests/test_cn_live_pack_frozen.py`, one `express-render-guards` CI line) and `cnp1trad` (packet written). After both: packet `cnp1arch` (content-addressed archive before the key replace, with source-board identity and intended session) |
| CN-P2 | Natural event lifecycle: spool consumed by the scheduler, zero-event snapshot, atomic reconciliation | #8714 `IMPLEMENTATION_HANDOFF.md:94-110` uses the archived pack from P1 and needs an owner decision on the natural quote contract first. Census: `.github/workflows/asia-close.yml:468-470` passes only `--asia --pack`; `--events` defaults to None (`scripts/reconcile_cn_live.py:165`); `pack_path` is dead (`:91`); nothing reads `CN_EVENTS_PREFIX` (`engine/prophet_live/r2io.py:40`); a zero-event run is byte-equivalent to a missing run (`scripts/reconcile_cn_live.py:127-131`) | Asia-close owns the scheduler and the data planes. No open PR | The 136/59/80 controls | **BLOCKED-ORDER** (it needs the P1 archive) plus **NEEDS-FABLE-DECISION** F3b (natural quote basis and the 60 s provider-quote future allowance) | After `cnp1arch` lands and F3b is decided: a P2 build packet covering the reconciler's spool default, the zero-event snapshot and the validation before the atomic write. It must not change `asia-close.yml` until durable refusal and idempotence have been exercised (handoff step 3) |
| CN-P3 | Publication: expired/non-OK display, resume, sequencing, request lifetime, bilingual SSR + paired JS | #8714 `IMPLEMENTATION_HANDOFF.md:112-122` plus the candidate patch in `repairs/display_contract/REPAIR_DECISIONS.md`. Census, against `templates/cn_prophet_live.js`: a non-OK response other than 401/403 does not tear down the chips (`:168-171`); expiry is keyed to `artifact_written_at` (`:78`, `MAXAGE :22`, check `:88`), as the handoff intends, but has no inclusive boundary and no check on resume; there is no request sequence identity and no timeout or AbortController (`:165`); `POLL 120000` (`:20`); the comment says 45 min (`:6-7`); there is no SSR live fallback age (`templates/_prophet_card.html.j2:626-632`) | `templates/_prophet_card.html.j2` is in #8444 (incumbent shared producer). `templates/china.html.j2` is in #8184 (sol/ branch, open, not draft). #7669 touches no China publication path (all 471 files checked); the handoff's "coordinate with #8444/#7669" is semantic | #8714's 30 producer and 38 independent checks: a new P3 "test matrix" lane would redo them, so it was not launched | JS half **NEEDS-FABLE-DECISION** F2 (30 s request lifetime). SSR fallback-age half **BLOCKED-ORDER** behind #8444 | After F2: a JS-only build packet owning `templates/cn_prophet_live.js` and `tests/test_cn_live_surface.py` (CI `unrun-site-surfaces`). The SSR age follows #8444 |
| CN-P4 | Clocks/generations through joins and retractions | Census Q11: clocks are PRESENT and there is no generation id. #8714 `:126-142` includes the margin source-window repair (`intelligence_lab/MARGIN_HORIZON_TRACE.md`). Its defect is still at BASE: `collectors/china_margin_detail.py:156` `dates[max(0, ci - LOOKBACK_TD - 2): ci - LOOKBACK_TD + 1] or dates[:1]` (synthetic, not a current-data incident). Generation receipts span `engine/china_extras.py`, `china_altdata.py`, `china_intel_hub.py`, `china_intel_interest.py`, `china_signal_lab.py` | No open PR touches `collectors/china_margin_detail.py`. `china_intel_hub` borders China Alpha | The 56 principal and 79 independent checks | Margin window **READY**. Generations BLOCKED-ORDER, behind P1 and P3 paths (handoff step 4: in parallel only where paths don't collide) | Lane `cnp4margin` (build; packet written, owns the collector plus `tests/test_china_alpha_w3c_infra.py`, CI `unrun-intl-collectors`). The generation receipts are a later packet |
| CN-P5 | Rank challenger (separate scientific gate) | Masterplan §10.1: a separate gate, only after P0–P4 | — | No adjusted-tape studies (KILL-CN-ADJUSTED-TAPE-LEGAL-LIMIT, `research/DO_NOT_REBUILD.md:132`); no subsector gate (`:92`); the 186-feature search gives no promotion | BLOCKED-ORDER (needs P0–P4) | out of scope for this commission |
| CN-R0 | Disputed R0 replay custody (#6871) | #6871 is an open draft with the Sol hold label and REQUEST_CHANGES, last updated 10-04. `WS-CHINA-ALPHA-INTELLIGENCE.md:394-400` says it stays at its carrier until reconciled by that incumbent route | the #6871 incumbent (sticky to the same writer) | 172/172 and "healthy shadow" stay disputed; never an accepted CIE03/L0 comparator | BLOCKED-CUSTODY | route to the #6871 incumbent via the seat; no lane |
| CN-LAW | Asia-close owns China data planes; a daily.yml reset is no witness | `WS-CHINA-ALPHA-INTELLIGENCE.md:120-123` (lane correction: asia-close.yml writes the China plane, and daily.yml resets `data/china*`) | — | — | STANDING | every China receipt must name an asia-close run |

## 2. China Alpha (§10.2; A4 "China Alpha")

| id | obligation | current evidence | owner / custody | verdict | next |
|---|---|---|---|---|---|
| CNA-G0 | G0 foundations | `WS-CHINA-ALPHA-INTELLIGENCE.md:101-102` done (CN-G0 #5943, seat packet #5933) | WS owner fable | ACCEPTED | — |
| CNA-P1 | P1/P1-R3A institutional visit tape | `:236` DONE / PROVEN_LIVE by receipt `research/china_alpha_intelligence/receipts/P1_R3A_NATURAL_RUN_RECEIPT_2026-08-23.md` (asia-close 32626503385; Sol 08-24) | fable | ACCEPTED (repeating the natural P1 proof is out of scope) | — |
| CNA-RIGHTS/ID | RIGHTS-0, PR-0D identity | `:125-127` rights0 done; `:134-135` pr0d done (adopted from D2B2-CN-HK) | fable | ACCEPTED | — |
| CNA-CIE04-06 | Versioned PIT evidence + real company workflow | The bounded CIE-04/05/06 slice merged in #8366 (e570025b). Natural publisher run asia-close 37200037578, with production desktop/mobile receipt `research/china_alpha_intelligence/receipts/cie06-production-browser/2026-10-04/README.md`. That receipt says full CIE-06 is PARTIAL; for example, change-since-previous-observation semantics are owed | fable (WS) via Data OS/GMI/Hub owners | bounded slice ACCEPTED; full CIE-06 BLOCKED-DATA: the CIE-00..19 obligation list lives in the "CIE package" pin `1b0f2ee2` cited by the receipt. That pin is not in macro (`git grep CIE-06` at BASE finds only the receipt, `engine/china_intel_hub.py:994,1152,1211` and the WS) and is not resolvable in the local Mastermind primary | Decision F4: seat supplies the CIE package path; then a remaining-obligation census lane |
| CNA-CIE02/03 | CIE-02 outcome/serving provenance gates CIE-03/L0 inference | `WS-CHINA-ALPHA-INTELLIGENCE.md:398-400`. No accepted CIE-02 record found at BASE: `git grep "CIE-02"` hits only that line and `docs/AGENT_OS_STATE.md:36` | fable | BLOCKED-DATA (CIE-02 acceptance absent) | name the CIE-02 owner and acceptance (Decision F4) |
| CNA-L0 | Full-pool canonical outcomes from `china_standout_track` primitives | `:356-358` todo | fable; shares `engine/china_standout_track.py` with CN-P0 | BLOCKED-DATA (CIE-02) + BLOCKED-ORDER (after CN-P0 settles original-truth semantics in the same file) | after CN-P0 + CIE-02 |
| CNA-P1B | Institutional discovery + prospective accrual | `:359-362` todo, depends_on [p1, l0] | fable | BLOCKED-ORDER (L0) | — |
| CNA-P2 | Analyst research effort state + dossier (shadow) | `:363-366` todo, depends_on [rights0] (done). Rights: `research/china_alpha_intelligence/RIGHTS_REGISTRY.md:99-110` shows report_rc, china_reports and china_analyst are OWNED, with internal accrual SATISFIED and commercial display NOT_BUILT | fable | NEEDS-FABLE-DECISION (dependency-ready; priority vs China correctness) | Decision F5 |
| CNA-R1 | Announcement corpus + first event family | `:367-370` todo, depends_on [pr0d] (done) | fable | NEEDS-FABLE-DECISION (dependency-ready; priority) | Decision F5 |
| CNA-R2 | Government/SOE demand via WS:CN-SOE-DEMAND | `agentos/workstreams/WS-CN-SOE-DEMAND.md:8` status blocked. blocked_by: an explicit CSG C1 use-class ruling from the rights/Data OS owner | grok-cn-c (WS owner) | BLOCKED-DATA (rights use-class ruling) | rights owner ruling; no lane |
| CNA-L2 | Equal-family shadow challenger | `:376-378` todo, depends_on [l0, p1b] | fable | BLOCKED-ORDER (L0, P1B, L1 evidence) | — |
| CNA-LAW | No second company master, grader or candidate store; no network/LLM in live rank; TuShare compliance SATISFIED (not reopened) | masterplan §10.2; #8714 §7 | — | STANDING | — |

## 3. Hong Kong (§10.3; A4 "Hong Kong")

| id | obligation | current evidence | owner / custody | verdict | next |
|---|---|---|---|---|---|
| HK-7277 | Integrate #7277 as screen/shadow; reconcile stale WS TODOs | Merged at 39f3fcb2. On BASE, four HK challengers are registered at `scripts/build_hk_library.py:2272-2290` (BNRS, H3, X1 rank_fn; discovery_fn), and `write_shadow(..., market="HK")` runs at `:2296` (gated by asia_advance). WS-PROPHET-HK-CA-REVAMP still lists hk-intel as todo | WS owner fable | PENDING `hkscout` Q1–Q3 | — |
| HK-7385 | Projection through the served HK consumer | open draft, head 27985cb8 | incumbent branch `claude/hk-opportunity-projection-20260919-sol` | PENDING `hkscout` Q4 | — |
| HK-7288 | Evaluator/scheduler + prospective accrual | open draft, head d4fee89c | incumbent draft | PENDING `hkscout` Q5 | — |
| HK-7163 | Resolve link destinations; #7163 not shipped | closed unmerged 09-25 | — | PENDING `hkscout` Q6 | — |
| HK-PARITY | Grid→Table→Grid population/order parity | → `hkscout` Q7 | — | PENDING | — |
| HK-AUTH | Official BUY authority preserved; no challenger in `hk_standouts.json` before promotion | WS landmine; masterplan §10.3 | — | STANDING | — |
| HK-PROMO | Separate promotion | needs a governed evaluator and matured accrual. DO_NOT_REDO: no H3/X1 promotion below DSR 0.90; no Southbound-delta promotion | — | BLOCKED-ORDER (HK-7288 + accrual) | — |

## 4. Canada (§10.4; A4 "Canada")

| id | obligation | current evidence | owner / custody | verdict | next |
|---|---|---|---|---|---|
| CA-ZB | Zero-buy liveness: full-pool shadow capture must survive an empty official buy subset | `scripts/build_canada.py:685-687` returns early when `buy` is empty. That skips the watch-strip calls, `append_board`, the `board_track` scorecard attach (the code comment says the panel "must render honestly-empty, never be absent"), the track-ledger emit, and `board_shadow.write_shadow` at `:804`. With #7286, both CA challengers register in-process before this call (`build_canada.py:1457` calls `build_canada_library.main`, and #7286's head `scripts/build_canada_library.py:1324` registers after `_write_canada_standouts`). Lane B (discovery) uses the full research population, so skipping `write_shadow` erases full-pool capture on zero-buy days. On BASE no CA challenger is registered yet, so `write_shadow` reports `no_challenger_registered`; the fix must land before or with #7286 | no open PR touches `_canada_board_ledger` (#7018 hunks at ~37/~1471; #7286 and #8444 do not touch `build_canada.py`); WS owner fable = seat | READY | lane `pro-regional-cazb-20261021-r1` (build; owned `scripts/build_canada.py` `_canada_board_ledger` + `tests/test_board_shadow.py`; CI job `board-shadow-substrate`) |
| CA-7018 | Opportunity map through current consumers | open draft on a sol/ branch (never touch); overlaps #8444 on `templates/canada.html.j2` and `site/canada-stock-v36.js` | Sol-owned carrier | BLOCKED-CUSTODY + BLOCKED-ORDER (#8444) | → `cascout` Q4 for hunk overlap |
| CA-7286 | Full-pool discovery shadow | open draft, head 00645e06, branch `claude/ssd-ca-discovery-shadow-20260918-sol-...`; 4 files, +920/−4 against the merge-base | incumbent draft | BLOCKED-CUSTODY (route to incumbent; needs CA-ZB first) | → `cascout` Q5 |
| CA-AUTH | authority=screen, official_pick_authority=false; no invented Plans/counts; Plan-owner typed unavailable via P1a | masterplan §10.4 | — | STANDING (verify via `cascout` Q2) | — |
| CA-ENTRY | Timing buy_now/partial label must not give an unaligned candidate ENTRY_OPEN | → `cascout` Q3 | — | PENDING | — |
| CA-EVAL | Map + full pre-alignment pool into #7288 evaluation | → `cascout` Q6 | #7288 incumbent | PENDING | — |
| CA-PIT / ACCRUAL / PROMO | PIT replay resolution; sector/name/rank accrual; separate promotion | → `cascout` Q7 | — | PENDING | — |
| CA-JOURNEY | Scheduler readback + authenticated map/action journeys | needs CA-7018 landed | — | BLOCKED-ORDER | — |

## 5. Shared regional obligations (§10.5; A4 "Shared regional delivery")

| id | obligation | current evidence | verdict | next |
|---|---|---|---|---|
| SH-ORDER | Shared card/count/Plan adoption: P1a #8444 → HK → China | #8444 is an open draft on a sol/ branch, updated 10-20 | BLOCKED-ORDER (#8444 acceptance) | HK adoption packet only after #8444 is accepted; China after HK acceptance plus a fresh source-collision check |
| SH-7499 | Replacement reference and reference integrity | open draft on a sol/ branch | PENDING `cascout` Q8 | — |
| SH-7303 | Sparse-card readability vs current shared-shell geometry | open draft | PENDING `cascout` Q9 | — |
| SH-7248 | Continuity documentation only | open draft | PENDING `cascout` Q10 | — |
| SH-6996 | Entry-copy specimen | open draft | PENDING `cascout` Q10 | — |
| SH-6872 | Replace the #6872 citation with the actual main source of the Prophet integrity restart dependency | #6872 = WTI Live Trace, merged 09-24 | PENDING `cascout` Q11 | — |
| SH-PROOF | Per-region proof set: identity, tz/session, basis, source-ordered preview/entitlement, stale/empty/outage, complete entitled population, exact/related/unavailable Plan semantics, action readback, privacy, correction, natural refresh; HK Grid→Table→Grid; CA zero-buy visibility; outage ≠ exit; 320px Chinese reflow | proof obligations that follow adoption | BLOCKED-ORDER | qualified per region after adoption |

## 6. Appendix A4 crosswalk
- China Prophet correctness: P0–P4 → CN-P0..CN-P4; P5 → CN-P5; disputed R0 → CN-R0.
- China Alpha:
  - Corporate Reality / Asymmetry milestones → CNA-CIE04-06, CNA-CIE02/03;
  - G0/P1 → CNA-G0, CNA-P1;
  - L0 / P1B / P2 / R1 / R2 / L2 → the matching CNA rows;
  - CIE provenance gates → CNA-CIE02/03, CNA-LAW.
- Hong Kong:
  - official vs discovery/attention → HK-AUTH, HK-7385;
  - native intelligence/races → HK-7277;
  - opportunity consumer → HK-7385;
  - governed evaluator → HK-7288;
  - accrual/promotion → HK-7288, HK-PROMO.
- Canada:
  - Branch-B truth/era → CA-AUTH;
  - authority split → CA-AUTH, CA-ENTRY;
  - opportunity map → CA-7018;
  - zero-buy-safe shadow → CA-ZB, CA-7286;
  - rank/sector-name accrual, PIT replay, evaluator, promotion → CA-PIT/ACCRUAL/PROMO, CA-EVAL;
  - typed Plan-owner limitation → CA-AUTH.
- Shared regional delivery:
  - accepted shared-interface adoption sequence → SH-ORDER;
  - source-ordered preview/entitlement, Grid/Table/search identity parity, local language and mobile, source outage versus healthy empty, exact/related/no-Plan behavior, and publication/correction continuity → SH-PROOF (per region, after adoption), with HK-PARITY and CN-P3 as the region-specific parts;
  - reference integrity and copy → SH-7499, SH-7303, SH-7248, SH-6996, SH-6872.

## 7. Decisions for Fable

Each decision is a reserved parameter or priority call. The seat holds the workstream for HK/CA (`WS-PROPHET-HK-CA-REVAMP`, owner fable) and the Prophet commission. Where the seat does not hold the call, the decision is to name the owner.

| id | decision | why it is reserved | recommendation |
|---|---|---|---|
| F1 | Canada zero-buy day semantics: (a) no watch-only rows in the board ledger; (b) the full-pool shadow capture and the track-ledger emit still run; (c) the health row keeps today's SKIP text, so "no official buys" stays distinct from an outage | It changes what a zero-buy day records. Masterplan §10.4 names the hole but not the record shape | Ratify (a)–(c) as frozen in lane `cazb`. A watch-only ledger append would mix screen rows into the official-call history, which `authority=screen` forbids |
| F2 | China P3 publication timings: 30 s request lifetime and 60 s future allowance, as proposed by #8714 | Both are product parameters, and #8714 left them unratified | Ratify both for the P3 build, with an explicit constant and a named test each. If the seat does not hold China publication, name the owner (#8714's commissioner) |
| F3 | China P0 and P2 owner calls. (a) **Custody**: #8714 `IMPLEMENTATION_HANDOFF.md:66-78` tells the P0 build to start on the incumbent R0 carrier, #6871 (Sol hold, REQUEST_CHANGES), after a fresh custody reconciliation. The P0 values themselves (quarantine of the 08-26/08-27/09-04/09-15/09-18 bakes, 133/289 original versus 129/289 named comparison, append-only corrections with a strictly later recording time) are already frozen there. (b) **Natural quote contract** for P2 (`:94-110`): which quote basis the natural lifecycle reads, plus the 60 s future provider-quote allowance as its own clock-policy parameter | (a) The seat does not hold #6871, and a hold binds every merge path. (b) This product/clock parameter is left open by #8714 | (a) The seat reconciles with the #6871 holder once. Either the holder releases P0 code to a new carrier with the #8714 values unchanged, or the holder keeps it and the seat routes the frozen packet to them. Do not reopen the values. (b) Adopt #8714's proposed natural quote basis and 60 s allowance as two named constants with a test each, decided together with F2 so P2 and P3 share one clock policy |
| F4 | CIE package location (pin `1b0f2ee2`), and the owner who accepts CIE-02 | Full CIE-06, CIE-02/03 and L0 cannot be censused or started without the package. Accepting CIE-02 gates CIE-03/L0 under the activation law | The seat supplies the package path or its Mastermind PR, then commissions one remaining-obligation census lane. Until then, China Alpha stays at its accepted bounded slice |
| F5 | Priority of China Alpha P2 (shadow) and R1 relative to China Prophet P0–P4 | Both compete for the same China scheduler and data planes, and the masterplan sets no order between them | China Prophet P0 → P1 → P3 first. Start China Alpha P2 as a shadow-only census after the P0 and P1 lanes are running. Keep R1 behind F4 |
| F6 | Pre-existing reds on `unrun-picks-boards` at BASE: `tests/test_prophet_board_since.py:626` (expects one `_us_board_cards` include; BASE has two, from #9517/#9550 on 10-17) and `:377` (Canada laggards tokens) | A CA-ZB or CN-P1 PR touches a path trigger of that job (`build_canada.py`, `build_china_library.py`), so it would inherit a red the lane cannot fix inside its owned files | Route both asserts to the owner of #9517/#9550 (US board cards) before shipping CA-ZB/CN-P1, or ship with the reds named as inherited under the sweeper's inherited-red rule. Do not widen the regional lanes to fix them |

Further decisions from the HK/CA scouts are appended as F6+ when they return.

## 8. Lanes

Fabric lanes under the seat launcher. Every run id is unique. Branch `lane/<run id>` lives in `~/lanes/wt/<run id>` on the host, base = BASE. Nothing is pushed: the seat ships.

| run id | class | host | STATUS | result |
|---|---|---|---|---|
| pro-regional-cazb-20261021-r1 | build | mmx-ubuntu0 | PARTIAL: the spec is met; the only failures are the inherited `unrun-picks-boards` reds (F6) | commit c9a6553bbab: `scripts/build_canada.py` +18/-6, `tests/test_board_shadow.py` +186. The T6 check fails on BASE as expected |
| pro-regional-cnscout-20261021-r1 | census | mmx-ubuntu0 | DONE | commit f18ef8a8ea7: `research/prophet_v4/r7_program/regional/CN_CORRECTNESS_CENSUS_2026-10-21.md` |
| pro-regional-hkscout-20261021-r1 | census | mmx-ubuntu3 | RUNNING | — |
| pro-regional-cascout-20261021-r1 | census | mmx-ubuntu3 | RUNNING | — |

Packets written and waiting for a slot (seat scratchpad `pk/`): `pro-regional-cnp1proj-20261021.md`, `pro-regional-cnp1trad-20261021.md`, `pro-regional-cnp4margin-20261021.md`.
