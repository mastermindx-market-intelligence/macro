# CEO B census — MarketOntology F06–F09 row-level evidence (wave 1, 2026-10-02)

Provenance: external fabric lane `mo_b_census_ba` (host mini2, MiniMax, read-only, admitted 2026-10-02T07:02Z, DONE rc=0 07:12Z) commissioned by CEO B (Fable seat `3add8c61`, carrier Macro #6819). Base: Macro `origin/main` 052e02d0. Terminal tree was NOT mounted on the lane host, so Terminal-side rows draw on the macro-side F00C reconciliation manifest (stated per row). Handed to CEO A's single F00 writer as row-level evidence; it is NOT a ledger write. Verbatim lane return follows.

---

## STATUS

Read-only census of MarketOntology ledger rows in families F06–F09 against Macro `origin/main` (052e02d0). 44 rows selected from the F00C CSV; per-row evidence below; counts by assessment; three lists (stale / unstarted-and-buildable / rights-gated); top-5 wave-2 candidates for this half. Lane does NOT echo a Net-new verdict — every row's `capability_state_c2` is echoed faithfully.

## RESULT

44 rows processed = 44 rows selected from CSV.

| Assessment | Count | Row IDs |
|---|---|---|
| PROVEN_LIVE | 9 | MO-PAID-020, MO-PAID-021, MO-DELTA-019, MO-DELTA-029, MO-PAID-060, MO-PAID-067, MO-DELTA-002, MO-DELTA-018, MO-PAID-059 (last three CORRECTED — see §CORRECTION) |
| BUILT_NOT_PROVEN | 7 | MO-DELTA-014, MO-DELTA-042, MO-PAID-028, MO-PAID-036, MO-DELTA-023, MO-PAID-064, MO-PAID-062 (CORRECTED) |
| PARTIAL | 10 | MO-DELTA-003, MO-PAID-027, MO-PAID-085, MO-DELTA-021, MO-DELTA-025, MO-PAID-019, MO-PAID-029, MO-PAID-040, MO-PAID-066, MO-PAID-026 (CORRECTED in; MO-PAID-059 moved to PROVEN_LIVE) |
| NOT_BUILT | 18 | MO-DELTA-017, MO-PAID-022, MO-PAID-035, MO-PAID-037, MO-DELTA-020, MO-DELTA-022, MO-DELTA-024, MO-DELTA-026, MO-DELTA-027, MO-DELTA-028, MO-DELTA-030, MO-PAID-030, MO-PAID-041, MO-PAID-061, MO-PAID-063, MO-PAID-065, MO-PAID-068, MO-PAID-069 |
| UNKNOWN | 0 | — |

## EVIDENCE

Per-row table (44 lines). Format: `id | family | ledger cap_state | next_bounded_child[:60] | evidence (≤3) | lane | why`.

| id | family | ledger cap_state | next_bounded_child (≤60) | evidence (≤3) | lane | why |
|---|---|---|---|---|---|---|
| MO-DELTA-002 | F06 | NOT_BUILT | filter-universe research-screener workflow | `engine/research_screener.py` + `scripts/build_research_screener.py` + `templates/research_screener.html.j2` on origin/main (`79f891133d3`, read 2026-10-04); live anonymous `GET /research_screener.html` → 200 (`.json` → 401 behind the paid gate); Sol's prod read (reading-list, AAPL valuation receipt) on #6819 | PROVEN_LIVE | CORRECTED on the carrier 2026-10-02 (#6819 c5966674775, confirms Sol) and in this doc 2026-10-04; residual = theme depth. The 10-02 cell searched for a "research-screener module" by the ledger's phrasing and missed the shipped file. |
| MO-PAID-020 | F06 | PROVEN_LIVE | a second issuer gets a real security_state.v1 + rendered page | engine/security_state.py@88KB compile_security_state :1447; #6920 merge history on main; #7122 d187c587c (renderer repair) merged per ledger | PROVEN_LIVE | security_state.py exists, AAPL+MSFT allowlist via issuer_cik :98/140/157; renderer repair #7122 merged; scoped to AAPL/MSFT (third issuer still allowlist-blocked) |
| MO-PAID-021 | F06 | PROVEN_LIVE | B1B ships a cockpit over frozen security_state.v1 for a second issuer | templates/ticker.html.j2@158KB on main; depends on #6920 / #7007 (961a9c3d) | PROVEN_LIVE | B1B panel substrate live; residual is chart-first B2-B6 (out of F06 scope) |
| MO-DELTA-017 | F07 | NOT_BUILT | full company workspace (statements+consensus+adjusted valuation) | B-REC-B5-X 2026-09-09 records consensus BLOCKED_RIGHTS via MO-PAID-035; FIF fixture-only | NOT_BUILT | consensus half rights-gated (see MO-PAID-035); FIF half unbuilt (fixture-only AAPL); compound dependency |
| MO-PAID-022 | F07 | NOT_BUILT | event->AssumptionChange->valuation path | engine/stock_fundamentals.py@121KB (nearest organ, fixture tier); DEC-F07-VALUATION-SOURCE-IS-SEC-COMPANYFACTS-V1.md on main | NOT_BUILT | nearest organ = fixture; no production consensus; valuation-source ruling required |
| MO-PAID-026 | F07 | NOT_BUILT | scenario engine over unbuilt valuation baseline | `engine/valuation_scenario.py` on origin/main ("Pure valuation-scenario calculator V1, FROZEN SPEC B-F07-1, emits `valuation_scenario.v1`") | PARTIAL | Engine BUILT; its consensus-valuation baseline input stays rights-gated via MO-PAID-022/035, so nothing is served. CORRECTED on the carrier 2026-10-02 (c5966674775, NEW) and in this doc 2026-10-04. |
| MO-PAID-035 | F07 | NOT_BUILT | DCF/comps over non-fixture issuer with rights-cleared consensus | engine/stock_fundamentals.py:1815 "Consensus ratings & price targets remain unwired" (verified verbatim) | NOT_BUILT | BLOCKED_RIGHTS via verified negative; consensus-ESTIMATE source nonexistent in repo |
| MO-PAID-037 | F07 | NOT_BUILT | n/a (triple dependency 022+026+035) | inherits from MO-PAID-035 | NOT_BUILT | pure inheritance; no independent path |
| MO-DELTA-003 | F08 | PARTIAL | role/weight/rebalance-trigger construction over canonical holdings | templates/calculators/portfolio_rebalancing.html.j2 (standalone public SEO); Terminal `master` MERGED: #552 (B-F08-B5-1 targets + drift bands), #580 (ledger flip — DDL 0022/0023 applied 2026-09-13; kit receipt 0023 apply 201 @ 2026-09-13T06:57:13Z), #586 (F08-13 weight targets / drift readout over 0023, tagged MO-DELTA-003); routes `api/portfolio/targets`, `api/portfolio/risk-history` → anonymous 401 (2026-10-04) | PARTIAL | WEIGHT half built on Terminal (targets, drift bands, readout); ROLE half absent per #7138; the SEO calc is not a constructor over canonical holdings. PARTIAL stands — evidence widened 2026-10-04. |
| MO-DELTA-014 | F08 | BUILT_NOT_PROVEN | signed-in risk-history journey over a non-empty holdings book | Terminal#524 efcd98aa (concentration/factor/liquidity) + Terminal#578 598b1a04 (Sharpe/Sortino/beta) per F00C manifest | BUILT_NOT_PROVEN | implementation merged; authenticated signed-in production proof still owed |
| MO-DELTA-042 | F08 | BUILT_NOT_PROVEN | signed-in production journey routed event→affected positions | Terminal#522 68b0d00a + Terminal#576 45a0e78e per F00C manifest | BUILT_NOT_PROVEN | event→positions schema + invalidation shipped; signed-in proof still owed |
| MO-PAID-027 | F08 | PARTIAL | a held position generates a material-change alert reaching a delivery channel | engine/alert_delivery_drain.py@58KB; engine/alerts.py@72KB; engine/alert_triage.py@92KB; drain_alert_outbox.py; Terminal `master` MERGED: #513 (B-F08-2 receipts + outbox, DDL 0013), #517 (B-F08-3 in-product alerts); routes `api/alerts`, `api/alerts/receipts` → anonymous 401 (2026-10-04) | PARTIAL | delivery path shipped (#6906/#6907, drain dormant) and the in-product alert surface shipped on Terminal; the user-book journey (held position → material-change alert → channel) is unbuilt end to end. PARTIAL stands — evidence widened 2026-10-04. |
| MO-PAID-028 | F08 | BUILT_NOT_PROVEN | event object resolves to the user positions it touches | Terminal#522 68b0d00a (event-impact) per F00C manifest; F08C reconciliation manifest pinned Terminal master dd7c6dec | BUILT_NOT_PROVEN | event→open-position mapping shipped; signed-in production readback still owed |
| MO-PAID-036 | F08 | BUILT_NOT_PROVEN | a user's actual holdings produce a concentration/factor/liquidity readout | Terminal#524 efcd98aa per F00C manifest | BUILT_NOT_PROVEN | concentration/factor shipped; Macro ticker-keyed liquidity thickness input still absent |
| MO-PAID-085 | F08 | PARTIAL | a set preference causes an actual send on the next matching alert | #6907 squash 715acf5f3c app/account_prefs.py@10.8KB (verified in git log); engine/portfolio_digest.py "SEND PATH IS OFF...DATED 2026-09-13" verbatim; Terminal `master` MERGED: #545 (B-F08-6 alert delivery prefs BFF), #551 (B-F08-7b pref-write fence); route `api/account/alert-prefs` → anonymous 401 (2026-10-04) | PARTIAL | prefs API + UI shipped on both sides; the mailer send path is explicitly unwired (deliberately), so a set preference causes no send. PARTIAL stands — evidence widened 2026-10-04. |
| MO-DELTA-018 | F09 | NOT_BUILT | debt-maturity schedule producer (XBRL EDGAR) | `engine/debt_maturity.py` + `scripts/build_debt_maturity.py` + `templates/_debt_maturity.html.j2` (rendered into ticker pages by `scripts/build_ticker_pages.py`) + EDGAR cache `data/debt_maturity/cache/CIK*.json` on origin/main; live anonymous `GET /stocks/AAPL.html` → 200 (2026-10-04); Sol's AAPL prod read ("Debt coming due" 6/6 buckets, $91.3B, SEC/XBRL) on #6819 | PROVEN_LIVE | The C6-1 attempt (2026-09-02) falsified the `document_terms.py` route, not the row — the producer was later built over public XBRL (reconciliation doc §F06–F09). CORRECTED on the carrier 2026-10-02 (c5966674775, confirms Sol) and in this doc 2026-10-04; residual = per-deal-term depth. |
| MO-DELTA-019 | F09 | PROVEN_LIVE | HY/IG gate live on ipo.html | engine/credit_window.py:343 window_state verified; engine/ipo_radar.py:79 window_context verified; templates/ipo.html.j2 #credit-window at :426-432 verified | PROVEN_LIVE | HY/IG window card live on ipo.html; follow-on equity is separate F09 work |
| MO-DELTA-020 | F09 | NOT_BUILT | licensed deal-flow feed | rights-blocked (DOCKETED_TERMINAL_HALF_B) | NOT_BUILT | BLOCKED_RIGHTS; no commercial deal-flow feed in repo |
| MO-DELTA-021 | F09 | PARTIAL | headroom computation follows producer + page | engine/capital_structure/covenant_terms.py:1-22 (source-first producer) verified; engine/covenant_headroom.py@48KB verified on main via 5-commit history (06c72062dd→8cc3b0ea25→981720cfc7→df75b4b54a→792e2be2b7); templates/capital_structure.html.j2 cs-covenant-room at L123 verified | PARTIAL | producer + page + headroom all on main; render lane red since 09-13 (PRs #7163/#7215 OPEN); substrate caveat — 0/2999 exhibits bound |
| MO-DELTA-022 | F09 | NOT_BUILT | valuation bridge depth (K2-C dependency) | none | NOT_BUILT | K2-C acceptance blocking; not buildable now |
| MO-DELTA-023 | F09 | BUILT_NOT_PROVEN | computed deal on #cs-premium | engine/special_situations_premium.py:388 featured_premium verified; templates/capital_structure.html.j2 #cs-premium at L63 verified; live honest-empty per ledger | BUILT_NOT_PROVEN | premium math + page shipped #6927; live computed deal still owed |
| MO-DELTA-024 | F09 | NOT_BUILT | ECM depth (IPO pricing history) | none | NOT_BUILT | ECM pricing history not sourced |
| MO-DELTA-025 | F09 | PARTIAL | comparison depth (per-issuer bond terms) | none (ETF-held par, not issuer outstanding per ledger repair) | PARTIAL | UNVERIFIED→CONFIRMED-ABSENT at instrument level; ETF-held quantity is not company debt |
| MO-DELTA-026 | F09 | NOT_BUILT | rating-agency licensing + ingestion source | none | NOT_BUILT | rights-gated (Moody's/S&P licensing not confirmed) |
| MO-DELTA-027 | F09 | NOT_BUILT | Material Flow Map | none | NOT_BUILT | pair-of MO-PAID-040; rights/source docket |
| MO-DELTA-028 | F09 | NOT_BUILT | entire maritime/AIS tracking | maritime/vessel/chokepoint grep clean per ledger | NOT_BUILT | BLOCKED_RIGHTS (commercial AIS vendor unaddressed) |
| MO-DELTA-029 | F09 | PROVEN_LIVE | coverage matrix capability | engine/commodity_coverage_matrix.py@9.3KB compute_coverage_matrix at :187 verified; commodities.html#coverage all 5 families per ledger | PROVEN_LIVE | coverage-matrix capability live 2026-09-19 |
| MO-DELTA-030 | F09 | NOT_BUILT | physical-vs-financial signals | none | NOT_BUILT | rights-blocked per F09 docket |
| MO-PAID-019 | F09 | PARTIAL | K1 frozen contracts (FIF/company-facts engines) | engine/companyfacts_authenticated_read.py on main per ledger | PARTIAL | FIF substrate present; K1 freeze blocks statement-level features |
| MO-PAID-029 | F09 | PARTIAL | FIF/company-facts engines (companyfacts_authenticated_read.py) | engine/companyfacts_authenticated_read.py on main per ledger | PARTIAL | substrate present; K1-frozen contracts |
| MO-PAID-030 | F09 | NOT_BUILT | sovereign-fund feed | none | NOT_BUILT | sovereign-fund grep zero hits; no licensed feed |
| MO-PAID-040 | F09 | PARTIAL | Material Flow Map | commodity coverage matrix at 9/11 modules per ledger | PARTIAL | layer-decomposition source CONFIRMED-ABSENT |
| MO-PAID-041 | F09 | NOT_BUILT | physical-vs-financial materials | none | NOT_BUILT | rights-blocked per docket |
| MO-PAID-059 | F09 | PARTIAL | debt-maturity schedule producer | same evidence as MO-DELTA-018 (producer + builder + partial + EDGAR cache on origin/main; Sol's AAPL prod read) | PROVEN_LIVE | Paired with MO-DELTA-018. CORRECTED on the carrier 2026-10-02 (c5966674775) and in this doc 2026-10-04. |
| MO-PAID-060 | F09 | PROVEN_LIVE | HY/IG window cards live | engine/ipo_radar.py:79 window_context verified; pipeline/listing readers verified at :189/193/278/305 | PROVEN_LIVE | engine + page live; HY/IG live; follow-on equity is separate F09 work |
| MO-PAID-061 | F09 | NOT_BUILT | licensed deal-flow feed | none | NOT_BUILT | BLOCKED_RIGHTS; compile script schema has no bookrunner/coupon/tenor/greenshoe |
| MO-PAID-062 | F09 | NOT_BUILT | covenant producer + headroom | `engine/capital_structure/covenant_terms.py` (Packet B-F09-5, emits `capital_structure.covenant_term_observation.v1` from SEC credit-agreement exhibits) + `engine/covenant_headroom.py` (B-F09-13 headroom view-model) + `mockups/evidence/b-f09-13-covenant-headroom/` (24 files) on origin/main | BUILT_NOT_PROVEN | Producer EXISTS; production wiring of the headroom surface belongs to `WS-CAPITAL-STRUCTURE-INTELLIGENCE-V2` (coo-fable; `DEC:MARKET-ONTOLOGY-POST-TIMEOUT-COMPLETION-ARCHITECTURE-2026-09-02` §6) — evidence only from this seat. CORRECTED on the carrier 2026-10-02 (c5966674775) and in this doc 2026-10-04. |
| MO-PAID-063 | F09 | NOT_BUILT | valuation bridge (compound dep) | none | NOT_BUILT | compound dependency: K2-C acceptance + capital-structure |
| MO-PAID-064 | F09 | BUILT_NOT_PROVEN | computed deal on #cs-premium | engine/special_situations_premium.py:388 + special_arb.py on main; templates/capital_structure.html.j2 #cs-premium at L63 | BUILT_NOT_PROVEN | paired with MO-DELTA-023; premium math + page shipped #6927; live computed deal still owed |
| MO-PAID-065 | F09 | NOT_BUILT | ECM depth (per-deal precedent) | ipo_radar.aftermarket_basket() adjacent ETF benchmark only per ledger | NOT_BUILT | ECM depth not built; not sourced |
| MO-PAID-066 | F09 | PARTIAL | per-issuer bond-terms comparison | UNVERIFIED→CONFIRMED-ABSENT at instrument level | PARTIAL | credit_momentum roster is index/aggregate+ETF only (L1645-1959); no per-issuer bond terms |
| MO-PAID-067 | F09 | PROVEN_LIVE | policy/foresight overlay | engine/policy_calendar.py@19.9KB + engine/foresight_cascade.py@35KB on main | PROVEN_LIVE | engine + page live; UNCHANGED |
| MO-PAID-068 | F09 | NOT_BUILT | capital-markets Outcome Spine / Eval OS | none | NOT_BUILT | rights-blocked per docket |
| MO-PAID-069 | F09 | NOT_BUILT | rating-action ingestion source | K1 frozen, no runtime per ledger | NOT_BUILT | rights-gated rating agency licensing absent |

Evidence command citations (excerpts):
- `git grep -l -F <id> origin/main -- agentos research docs engine scripts app templates` for every row (44 runs).
- `git cat-file -e origin/main:<path>` and `git show origin/main:<path>` for line anchors:
  - `engine/stock_fundamentals.py:1815` consensus-unwrap
  - `engine/portfolio_digest.py` "SEND PATH IS OFF...DATED 2026-09-13" (verbatim)
  - `engine/capital_structure/covenant_terms.py:1-22` (source-first slice)
  - `engine/capital_structure/document_terms.py` (registration-fee-table-only verified)
  - `engine/credit_window.py:343` window_state
  - `engine/ipo_radar.py:79` window_context; :189/193/278/305 pipeline/listing
  - `engine/special_situations_premium.py:388` featured_premium
  - `engine/security_state.py` compile_security_state :1447; ListingAlias/ListingKey/issuer_cik at :98/140/157/308/312/313/529/542
  - `engine/covenant_headroom.py` view model + 5-commit merge history on origin/main
  - `app/account_prefs.py` POST/GET /api/account/prefs at :131/:205
  - `engine/commodity_coverage_matrix.py` compute_coverage_matrix at :187
  - `templates/ipo.html.j2:426-432` #credit-window
  - `templates/capital_structure.html.j2` #cs-premium at L63, #cs-covenant-room at L123
  - `templates/calculators/portfolio_rebalancing.html.j2` standalone SEO - `git log origin/main --oneline -- <file>` for app/account_prefs.py (715acf5f3c = #6907), covenant_headroom.py (06c72062dd, 8cc3b0ea25, 981720cfc7, df75b4b54a, 792e2be2b7), templates/capital_structure.html.j2
- `research/market_intelligence_productization/F00C_TERMINAL_WAVE_RECONCILIATION_MANIFEST_2026-09-09.json` for Terminal master SHAs and PR merges (db69d0723… early, dd7c6dec… for #522/#576/#524/#578 rows)

## GAPS

- **Terminal tree not accessible.** The mission declares `TERMINAL READ-ONLY TREE: /Volumes/Mastermind/agent-workspaces/claude/5600d31ffa29643a/ceo-b-tctx-74a22c9d6da18edc` but that path does not exist on this host. Terminal-side verification for F08 rows (MO-DELTA-014, MO-DELTA-042, MO-PAID-028, MO-PAID-036) was made against Macro's pinned F00C reconciliation manifest (`research/market_intelligence_productization/F00C_TERMINAL_WAVE_RECONCILIATION_MANIFEST_2026-09-09.json`) rather than direct `Terminal origin/master`. Manifest pins Terminal master SHAs (`db69d0723…` early, `dd7c6dec…` for the BUILT_NOT_PROVEN rows) and merge SHAs (`522=68b0d00a`, `524=efcd98aa`, `576=45a0e78e`, `578=598b1a04`). No manifest entry exists for `terminal#552`/`#580` (F08 constructor / Portfolio context), so those PRs were NOT independently confirmed against a Terminal SHA — ledger text only.
- **No `engine/ticker_cik_collision_census.py` on origin/main.** The ledger (MO-PAID-020) names it as a producer but the file does not exist at that path. The renderer repair (`#7122 d187c587`) merged per the ledger; the census module cited in `state_delta` is therefore best read as a sibling (not on main as a tracked file under that exact path).
- **Substrate caveat for MO-DELTA-021.** `scripts/compile_capital_structure_covenant_terms.py` is real on main, but per the ledger's own substrate caveat it binds 0 of 2999 eligible exhibits (`data/capital_structure/health.json` state uncovered). The covenant-room panel therefore has no observations to show yet — the panel renders, but reads empty.
- **Render lane starved since 09-13.** Templates `site/capital_structure.html` (cs-covenant-room) and `am_edition.html` (F01, out of scope here) carry no cs-covenant-room live on www — guard `no-dead-site-references` + `ms-board-coherence` red since 09-13 per ledger; fix PRs #7163 + #7215 both still OPEN at the pinned commit. This blocks PROVEN_LIVE promotion for MO-DELTA-021 even though the page + headroom are on main.

## DEVIATIONS

- **Terminal tree path absent** (see GAPS). Evidence for F08 Terminal rows was sourced from Macro's F00C reconciliation manifest instead of direct Terminal master. Recorded transparently.
- **`engine/ticker_cik_collision_census.py` path check returned MISSING**, but this is the literal path the ledger cites (not a deviation from the packet's method — it's the packet's (c) step reporting truthfully). MO-PAID-020's PROVEN_LIVE is held on the security_state.py substrate + #6920 + #7122 chain rather than on the census file.
- **No `engine/covenant_terms.py`** at root (only `engine/capital_structure/covenant_terms.py`); the ledger points at the latter. MO-DELTA-021 evidence follows the ledger's real_producer path exactly. No deviation.
- **Single gh API call is in scope per the method, but was NOT used** — git log/grep/cat-file satisfied every evidence question without exceeding the `1 gh call per 10 rows` budget. No PR-search call was needed.
- **Final stdout path.** Per the binding placement override the record lives at `/Users/mini2/lanes/ext/lanes/mo_b_census_ba/record.md` (not the packet's seat-host path under `~/.claude/projects/...`). The sentinel line is the last line of both this file and the final stdout message.

## NEXT SEAT ACT

Seat (CEO A's single F00 writer) should:

1. **Adopt the 9 PROVEN_LIVE rows verbatim** (6 original + MO-DELTA-002 / MO-DELTA-018 / MO-PAID-059 per §CORRECTION): MO-PAID-020 (F06 AAPL/MSFT security_state), MO-PAID-021 (F06 B1B cockpit), MO-DELTA-019 + MO-PAID-060 (F09 HY/IG window), MO-DELTA-029 (F09 commodity coverage matrix), MO-PAID-067 (F09 policy/foresight overlay). These are already locked and require no F00C narrative re-write.
2. **Promote MO-DELTA-021 to a render-blocker healing task, NOT a re-build**: page + headroom + producer are all on origin/main; the gap is render lane (`ms-board-coherence` red since 09-13) and the substrate caveat (0/2999 exhibits bound). Healing means getting PRs #7163 and #7215 closed AND widening `compile_capital_structure_covenant_terms.py`'s cover-list — not new code.
3. **Wave-2 candidates for this half** (top 5):
   1. **MO-DELTA-018 / MO-PAID-059** (debt-maturity producer) — XBRL EDGAR is public, source-clear; a NEW bounded child for `engine/capital_structure/debt_maturity.py` reading `us-gaap:DebtInstrumentMaturityDate` / `LongTermDebtMaturitiesRepaymentsOfPrincipal*` is the buildable-now path. The C6-1 attempt falsified the *premise* (no producer exists), not the source rights.
   2. **MO-DELTA-023 / MO-PAID-064** (premium computed deal) — producer #6927 already on main; only a live computed `premium_pct` observation is owed (one acquired deal that crosses the producer's threshold). This is a "wait for a real deal" child, not a build.
   3. **MO-PAID-085** (send path completion) — prefs API + UI shipped (#6907 715acf5f3c); remaining is wiring `engine/portfolio_digest.py` into the existing drain (`engine/alert_delivery_drain.py`) per the legal mailer dispatch (or to a marketing-class path with email_prefs opt-in). Not rights-blocked.
   4. **MO-DELTA-002** (F06 research-screener) — not rights-blocked; depends on F07 valuation-posture inputs (per the ledger). Sequence AFTER MO-DELTA-018/059 lands; the screener becomes a thin filter over theme/catalyst/exposure/valuation-posture rather than a trade ranker (DNR ceiling).
   5. **MO-PAID-040** (Material Flow Map layer-decomposition) — 9/11 commodity families covered; the missing 2 families are the buildable half. Source-rights docket already ratifies; only the layer-decomposition source is absent per ledger. Sequence AFTER the debt-maturity wave.
4. **Wave-2 explicitly OUT of scope for this lane** (rights-gated): MO-DELTA-020/061 (deal-flow), MO-DELTA-026/069 (rating agency), MO-DELTA-028 (maritime/AIS), MO-DELTA-030/041 (physical-vs-financial), MO-PAID-022/035/037 (consensus), MO-PAID-030 (sovereign), MO-PAID-068 (cap-markets Eval OS). Each is BLOCKED_RIGHTS via the F09 docket; no seat action advances them without a Chairman/commercial act.
5. **No row's ledger capability_state_c2 contradicts verified evidence** — there are no STALE labels in this half to escalate. The ledger's stale-text annotations in `state_delta` (e.g., MO-PAID-027 "UNVERIFIED attempted") have all been re-evidenced to PARTIAL on the current main.
6. **Terminal-side verification owed** (DEFERRED): a future lane that has Terminal read access should independently re-verify Terminal #522, #524, #576, #578 at Terminal master `dd7c6dec712a5b7f40d371e3b83827c694dd8f90` and confirm signed-in production journeys; the current census treated the F00C manifest as authoritative.

---

### Record file verbatim

```markdown
---
workstream: W1-CENSUS-BA
session: mo_b_census_ba_2026-10-02
model: glm-5.3-flash
sha: 052e02d085b01f29baf499357e224c836d8eb224
VERDICT: READY_FOR_SEAT
---

## CORRECTION 2026-10-04 (seat 3add8c61) — the doc now matches the carrier reconciliation of 2026-10-02

- **Why this exists.** The 10-02 wave-1 census above was reconciled on the carrier the same day (#6819 comment 5966674775, after Sol's production reads): MO-DELTA-002 and MO-DELTA-018 / MO-PAID-059 → PROVEN_LIVE (confirming Sol), MO-PAID-062 → BUILT_NOT_PROVEN, MO-PAID-026 → PARTIAL. The comment moved the cells; this file did not, so a cold reader of `origin/main` saw four stale NOT_BUILT cells and one stale PARTIAL. This correction edits the summary table, the affected rows in both evidence tables, and the NEXT SEAT ACT count. No new judgment — every cell here was already ruled on the carrier.
- **Re-verified on origin/main `79f891133d3` (2026-10-04, `git ls-tree -r origin/main`):** `engine/research_screener.py`, `scripts/build_research_screener.py`, `templates/research_screener.html.j2`, `engine/debt_maturity.py`, `scripts/build_debt_maturity.py`, `templates/_debt_maturity.html.j2`, `data/debt_maturity/cache/CIK*.json`, `engine/capital_structure/covenant_terms.py`, `engine/covenant_headroom.py`, `mockups/evidence/b-f09-13-covenant-headroom/` (24 files), `engine/valuation_scenario.py`. Live anonymous probes (status codes only): `/research_screener.html` 200, `/research_screener.json` 401, `/capital_structure.html` 200; live anonymous `GET /stocks/AAPL.html` → 200 (2026-10-04).
- **Counts after correction:** PROVEN_LIVE 9 · BUILT_NOT_PROVEN 7 · PARTIAL 10 · NOT_BUILT 18 = 44.
- **Terminal-master sweep (the F12 lesson applied here, 2026-10-04):** `gh pr list --repo mastermindx-market-intelligence/mastermind-terminal --state merged --limit 100 --search "MO-B in:title"` returns packets tagged only B-F08-* and B-F12-*; a keyword title search (valuation, scenario, issuer, transaction tape, ECM, precedents, sovereign, debt maturity, arbitrage, source library) surfaces no F06/F07/F09 build. The remaining 18 NOT_BUILT cells are not Terminal-shipped work; they stay NOT_BUILT on both repos' evidence.
- **Still owed for the three new PROVEN_LIVE rows:** nothing from this seat — Sol's production reads are the live evidence; residuals (theme depth; per-deal-term depth) are recorded in the row notes, not as gates.

## HYGIENE 2026-10-04 (seat 3add8c61) — duplicated lane packet removed; F08 evidence widened; no state change
- The raw `mo_b_census_ba` lane return (STATUS…DEVIATIONS under `#` headings plus lane stdout noise such as `FLOCK_ACQUIRED` and the `READY_FOR_SEAT` sentinel) had been appended verbatim after NEXT SEAT ACT, repeating ~93 lines of the sections above. Removed. The census base is unchanged and still recorded above: macro `origin/main` `052e02d085b0` (Provenance line, STATUS, and the `sha:` field).
- F08 rows re-read against Terminal `master` on 2026-10-04 with the same method that caught the F12 blind spot: MO-DELTA-003 / MO-PAID-027 / MO-PAID-085 evidence cells now cite the merged Terminal packets (#552/#580/#586; #513/#517; #545/#551), the applied DDL (0022/0023; kit receipt 0023 apply 201 @ 2026-09-13T06:57:13Z) and anonymous 401 probes of `api/portfolio/targets`, `api/portfolio/risk-history`, `api/alerts`, `api/alerts/receipts`, `api/account/alert-prefs`. States unchanged: all three PARTIAL; 014/042/028/036 BUILT_NOT_PROVEN unchanged. Counts unchanged: 9 · 7 · 10 · 18 = 44. Terminal `master` carries MO-B packets only for F08 and F12 — F06/F07/F09 have no Terminal build.

