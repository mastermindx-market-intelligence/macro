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
| CN-P0 | Original truth: immutable originals, typed append-only corrections, source/basis/session identity | Requirements frozen by #8714 `IMPLEMENTATION_HANDOFF.md` (on efab78a1 only; pin 3d90aad6): quarantine the 08-26/08-27/09-04/09-15/09-18 bakes; 133/289 stays the original accounting, with 129/289 as a separately named comparison; append-only corrections; OHLC retention; 104 producer + 86 vintage controls. Code state at BASE: → scout `cnscout` Q1–Q4 | #8714's research session wrote the spec; no open PR touches P0 code (#6871 is research + one test only) | #8714's 104/86 controls exist, so do not re-derive them; R0 economics stay disputed | PENDING `cnscout` | — |
| CN-P1 | Canonical pack: read once, measured zero, full-universe tradability, archive armed pack | #8714 §P1: 180-name positive control; 1,716/1,638/77/1 tradability census. Code: → `cnscout` Q5–Q6 | none open | #8714 census | PENDING | — |
| CN-P2 | Natural event lifecycle: spool consumed by the scheduler, zero-event snapshot, atomic reconciliation | #8714 §P2: the scheduled reconciler is called `--pack`-only and does not load event history. Controls 136/59/80. Code: → `cnscout` Q7–Q8 | none open | — | PENDING | — |
| CN-P3 | Publication: expired/non-OK display, resume, sequencing, request lifetime, bilingual SSR + paired JS | #8714 §P3: 30 producer + 38 independent checks and a candidate patch already exist. It proposes a 30 s request lifetime and 60 s future allowance, both unratified. Code: → `cnscout` Q9–Q10 | `templates/china.html.j2` is also touched by #8184 (sol/ branch, open) | #8714 checks exist, so a new "P3 test matrix" research lane would redo them | PENDING | — |
| CN-P4 | Clocks/generations through joins and retractions | → `cnscout` Q11 | none open | — | PENDING | — |
| CN-P5 | Rank challenger (separate scientific gate) | Masterplan §10.1: a separate gate, only after P0–P4 | — | No adjusted-tape studies (KILL-CN-ADJUSTED-TAPE-LEGAL-LIMIT, `research/DO_NOT_REBUILD.md:132`); no subsector gate (`:92`); the 186-feature search gives no promotion | BLOCKED-ORDER (needs P0–P4) | out of scope for this commission |
| CN-R0 | Disputed R0 replay custody (#6871) | #6871 is an open draft with the Sol hold label and REQUEST_CHANGES, last updated 10-04. `WS-CHINA-ALPHA-INTELLIGENCE.md:394-400` says it stays at its carrier until reconciled by that incumbent route | the #6871 incumbent (sticky to the same writer) | 172/172 and "healthy shadow" stay disputed; never an accepted CIE03/L0 comparator | BLOCKED-CUSTODY | route to the #6871 incumbent via the seat; no lane |
| CN-LAW | Asia-close owns China data planes; a daily.yml reset is no witness | `WS-CHINA-ALPHA-INTELLIGENCE.md:120-123` (lane correction: asia-close.yml writes the China plane, and daily.yml resets `data/china*`) | — | — | STANDING | every China receipt must name an asia-close run |

## 2. China Alpha (§10.2; A4 "China Alpha")

| id | obligation | current evidence | owner / custody | verdict | next |
|---|---|---|---|---|---|
| CNA-G0 | G0 foundations | `WS-CHINA-ALPHA-INTELLIGENCE.md:101-102` done (CN-G0 #5943, seat packet #5933) | WS owner fable | ACCEPTED | — |
| CNA-P1 | P1/P1-R3A institutional visit tape | `:236` DONE / PROVEN_LIVE by receipt `research/china_alpha_intelligence/receipts/P1_R3A_NATURAL_RUN_RECEIPT_2026-08-23.md` (asia-close 32626503385; Sol 08-24) | fable | ACCEPTED (repeating the natural P1 proof is out of scope) | — |
| CNA-RIGHTS/ID | RIGHTS-0, PR-0D identity | `:125-127` rights0 done; `:134-135` pr0d done (adopted from D2B2-CN-HK) | fable | ACCEPTED | — |
| CNA-CIE04-06 | Versioned PIT evidence + real company workflow | The bounded CIE-04/05/06 slice merged in #8366 (e570025b). Natural publisher run asia-close 37200037578, with production desktop/mobile receipt `research/china_alpha_intelligence/receipts/cie06-production-browser/2026-10-04/README.md`. That receipt says full CIE-06 is PARTIAL; for example, change-since-previous-observation semantics are owed | fable (WS) via Data OS/GMI/Hub owners | bounded slice ACCEPTED; full CIE-06 READY (still required) | a research census of the remaining CIE-06 obligations against `research/CHINA_ALPHA_INTELLIGENCE_MASTERPLAN.md`; packet `pro-regional-cie06rem` (see §8) |
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
| SH-PROOF | Per-region proof set: identity, tz/session, basis, stale/empty/outage, population, Plan semantics, action readback, privacy, correction, natural refresh; HK Grid→Table→Grid; CA zero-buy visibility; outage ≠ exit; 320px Chinese reflow | proof obligations that follow adoption | BLOCKED-ORDER | qualified per region after adoption |

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
- Shared → SH-*.

## 7. Decisions for Fable
(filled after lanes return)

## 8. Lanes
(filled as lanes return)
