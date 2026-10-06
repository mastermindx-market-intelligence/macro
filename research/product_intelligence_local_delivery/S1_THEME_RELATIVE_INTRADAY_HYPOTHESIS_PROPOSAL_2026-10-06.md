# S1 — Theme-relative intraday descriptive strength (hypothesis proposal + registration draft)

**MAIN_PIN:** `1e3299d7b75202be9a951d0b877388d243cd5ba5` (`git rev-parse origin/main` after `git fetch origin main` on 2026-10-06).  
**Label:** `mi_s1_hypothesis_proposal_r1` · **Branch:** `claude/mi-s1-intraday-hypothesis-proposal-20261006`  
**Inputs (read-only on MAIN_PIN):** `research/product_intelligence_local_delivery/S0_INTRADAY_ESTATE_CENSUS_2026-10-06.md` + `.json` (CONFIRMED_GAP, §Q6 skeleton).

## Package S (verbatim, binding)

## S — Optional genuinely new intraday/theme-relative research

Commission only after the existing source/consumer census confirms the gap and the product owner accepts the distinct hypothesis. This is not a reopening of Trend Persistence or a rename of completed regime studies.

**Route:** standard research/data engineer for interval/session/data audit and baseline fixtures; independent research reviewer for registration; frontier only for unresolved identification. **Inputs:** existing residual/tape/market-data owners, canonical PIT memberships, source-specific allowed intervals/rights and the existing evaluator. The current intraday bar/quote estate and any adjusted/unadjusted/session definitions must be positively recovered rather than presumed from vendor subscriptions.

Freeze the decision time, open/regular/extended session boundaries, trailing-only beta/volatility estimation, benchmark overlap, constituent self-inclusion, stale/missing/zero-return treatment, halts/corporate actions, membership cutoff, raw and residual baselines, coverage and realistic observations/costs. Distinguish descriptive strength and recovery depth from claims about hidden fund inflows or ease of holding.

Use a new prospective registration for genuinely new theme/intraday hypotheses, untouched future formation dates, consolidated trial accounting and stated rejection/inconclusive rules. No outcome scan before registration and no new rank/gate/size authority. Return a source-qualified descriptive feature proposal and a valid study verdict when its sample matures; do not promise a positive edge or premature end-to-end scientific completion.

---

## §0 Acceptance ask (product owner)

**Ask:** Do you accept commissioning Package S2 prospective registration for **theme-relative intraday descriptive strength** on **hourly regular-trading-hours (RTH) bars** under the frozen parameters in §3, as a research-only lane that does not reopen Trend Persistence?

**If yes, this unlocks:** an S2 registration commit (formation dates strictly after acceptance), prospective accrual on **existing** API keys and workflows (`POLYGON_API_KEY` / `MASSIVE_API_KEY` hourly accrual per `.github/workflows/intraday.yml:55-60`), and consolidated trial accounting through `engine/trial_ledger.py:126-151` (`log_trial` append-only writes).

**If yes, this does NOT unlock:** new data-provider purchase, new collectors or daemons, rank/gate/size authority, capital deployment, minute-bar claims, or any outcome scan before registration lands.

---

## §1 H-S1 (testable descriptive hypothesis)

**H-S1 (one sentence):** For each live theme constituent versus its equal-weight theme benchmark (with the constituent excluded from that benchmark’s weights), **descriptive strength** is the sum of trailing-beta **residual** hourly returns on **RTH** bars over the **five** completed hourly bars immediately after the frozen decision timestamp (the last completed hourly bar whose end is no later than 16:00 America/New_York on the decision session), using **trailing-only** beta and volatility estimated only from completed sessions strictly before the decision session — **descriptive only**, with no promise of tradable edge.

**Rejection rule (a-priori):** For a formation session, if fewer than **80%** of the scheduled constituent×hour cells in that five-bar forward window have non-missing split-adjusted hourly RTH returns on existing store keys, assign session verdict **reject** for that date.

**Inconclusive rule (a-priori):** If coverage is at least **50%** but below **80%** of those cells, assign session verdict **inconclusive** for that date; otherwise proceed to descriptive scoring when maturity is met (§5).

---

## §2 Distinctness (not a rename)

### Trend Persistence (closed C1-NULL)

**Key line (MAIN_PIN):** `agentos/decisions/DEC-TREND-PERSISTENCE-STOPS-AT-WAVE-C.md:16-22` — Wave C group features on **eleven GICS sectors** with **20/60 session** forward returns vs SPY; C1-NULL, family stops.

**DNR:KILL-TREND-PERSISTENCE-SECTOR-GROUP-PERSISTENCE** — `research/DO_NOT_REBUILD.md:134` closes the eleven-GICS-sector group-persistence constructions (C1-NULL).

**DNR:KILL-TREND-PERSISTENCE-PATH-FEATURE-PROFILE** — `research/DO_NOT_REBUILD.md:133` closes path-shape drawdown-profile constructions (Wave B2 null).

**S1 difference:** Dynamic **theme** baskets, **hourly RTH** decision clock, **descriptive intraday residual strength** — no sector-group persistence cells and no pre-registered 20/60-session SPY-relative outcome family.

### DNR:KILL-INTRADAY-CHRONICLE

**Key line (MAIN_PIN):** `research/DO_NOT_REBUILD.md:47` — forbids intraday **chronicle** writes in hourly jobs; not a ban on price bars.

**S1 difference:** Read-only use of gitignored `data/intraday/<T>.parquet` accrual and on-main `data/intraday_flow/ledger.parquet`; **no** `data/chronicle/*.jsonl` lane writes.

### Daily multi-window strength (S0 §Q3)

**Pin:** S0 §Q3 — `engine/narrative_rotation.py:851-854` builds **10-session daily** basket `r10` after daily `allocate()`; `engine/us_board_rank.py:1954-1977` uses **63-session daily** trailing return z-scores — none consume hourly equity bars for theme-relative research.

**S1 difference:** **Hourly RTH** residual strength after a **frozen intraday decision time**, not daily close/session windows.

### Prophet regime studies

**Pin:** S0 §Q2 — `engine/prophet_entry_policy.py:58-66` governs US RTH execution policy for Prophet entry surfaces; regime studies remain **daily** strength/rotation tables in S0 §Q3.

**S1 difference:** Optional **intraday descriptive** feature for themes; does not extend Prophet regime verdict machinery or grant new promotion authority.

### DNR:KILL-OFFHORIZON-VERDICTS (forbidden overlap)

**Key line (MAIN_PIN):** `research/DO_NOT_REBUILD.md:46` — verdicts only at registered `horizon_role` rulers.

**S1 difference:** Prospective registration fixes **one** forward window (five hourly RTH bars) before any scoring; no ad-hoc horizon ladder.

---

## §3 Frozen parameters (S0 §Q6 rows + coverage)

Each row closes the S0 §Q6 pin or fills the named GAP. No value is justified by historical outcomes, backtests, or realized performance scans.

| # | Field | Frozen value | Basis label | Basis (one line) | Closes |
|---|--------|--------------|-------------|------------------|--------|
| 1 | Decision time | Offset-aware ISO `decision_at` at the end of the last **completed** hourly RTH bar on the decision session, with no bar ending after 16:00 America/New_York | INHERITED | `engine/prophet_entry_policy.py:86-95` requires canonical offset-aware `decision_at`; session law `engine/prophet_entry_policy.py:58-66` | S0 §Q6 decision-time GAP |
| 2 | Session boundaries | **RTH only:** 09:30–16:00 America/New_York on US equity session dates; early-close dates in `engine/prophet_entry_policy.py:58-66`; **no** extended-hours bars in scope | INHERITED | `engine/prophet_entry_policy.py:58-66` + calendar existence via `lib/nyse_calendar.py:10-13` (early-close split acknowledged in S0 §Q2) | S0 §Q6 session pin |
| 3 | Trailing-only beta/volatility | **63** completed RTH sessions of daily returns strictly before the decision session; OLS beta of constituent vs theme benchmark; vol from the same pre-decision window only | ASSUMED | Chosen before any S1 data read; no peek at decision-day or forward-window returns | S0 §Q6 trailing beta/vol GAP |
| 4 | Benchmark overlap | Theme benchmark = equal-weight return of live theme members on the same hourly bar; residual = constituent return minus beta×benchmark return on that bar | STATED | Package S requires benchmark overlap frozen; descriptive theme-relative residual, not SPY group persistence | S0 §Q6 benchmark overlap GAP |
| 5 | Constituent self-inclusion | Constituent **excluded** from its theme benchmark weight on every bar | ASSUMED | Standard theme-relative bookkeeping chosen a priori | S0 §Q6 self-inclusion GAP |
| 6 | Stale/missing/zero-return | Missing hourly bar → omit cell; **zero-volume** bar → omit; per-ticker corrupt store → tolerate as absent file per collector (`scripts/build_polygon_intraday.py:171-185`) | INHERITED | `scripts/build_polygon_intraday.py:171-185` fail-soft read; study rule extends GAP honestly | S0 §Q6 stale/missing GAP |
| 7 | Halts/corporate actions | **Split-adjusted** hourly OHLCV only (`adjusted: true`); no separate halt tape — sessions with no RTH bars after vendor delay are omitted | INHERITED | `scripts/build_polygon_intraday.py:135-136` adjusted flag; halt handling GAP closed as “omit session” rule | S0 §Q6 halts GAP |
| 8 | Membership cutoff | Theme membership from `data/baskets/membership.json` resolved PIT as of the last completed US **daily** session before `decision_at` (`scripts/build_intraday_flow.py:324-325`) | INHERITED | `scripts/build_intraday_flow.py:324-325` membership.json load path | S0 §Q6 membership pin |
| 9 | Raw and residual baselines | **Raw:** hourly RTH simple return; **Residual:** trailing-beta-adjusted vs theme benchmark per row 4 | STATED | Package S requires raw and residual baselines distinguished | S0 §Q6 baselines GAP |
| 10 | Costs | **8** basis points applied once per full round-trip turnover assumption for any optional tradability sensitivity table (display-tier only) | INHERITED | House cost stub cited in `engine/signal_foundry/harness.py:9-14` documentation band (not an outcome scan) | S0 §Q6 costs GAP |
| 11 | Coverage | Universe = tickers already accreted under existing `POLYGON_API_KEY` / `MASSIVE_API_KEY` hourly job (`.github/workflows/intraday.yml:55-60`); no new vendor keys | INHERITED | S0 CONFIRMED_GAP: only runner-local hourly store; coverage honest on existing keys only | S0 §Q5 estate gap |

---

## §4 Data reality (no minute-level claims)

| Claim | Evidence on MAIN_PIN |
|--------|----------------------|
| Hourly US bars, 15-minute delayed, split-adjusted | `scripts/build_polygon_intraday.py:1-14` (STANDARD delayed aggregates); receipt fields `scripts/build_polygon_intraday.py:135-136` |
| Store not on main tree | `git ls-tree -r origin/main --name-only data/intraday/` → empty; `.gitignore:70` ignores `data/intraday/` |
| Accrual workflow | `.github/workflows/intraday.yml:10-15` cron during US hours; step `.github/workflows/intraday.yml:55-60` runs `scripts/build_polygon_intraday` |
| Flow ledger on main | `git ls-tree origin/main data/intraday_flow/ledger.parquet` → blob present (listing only; no byte read) |
| RTH hourly labeling expectation | `engine/intraday_flow.py:43-44` (regular 09:30–16:00 ET hourly buckets) |
| Daily theme context (not intraday strength) | `engine/narrative_rotation.py:843-854` daily `r10` display tape |

**Grain law:** S0 §Q5 CONFIRMED_GAP — finest **positively recovered** US single-name equity grain is **hourly**, not minute. S1 makes **no** minute-level or sub-hourly claims.

**Forbidden data actions for S2 until registered:** reading `data/intraday/*.parquet` bytes for threshold tuning; any vendor API call beyond existing scheduled accrual.

---

## §5 Prospective registration plan (draft)

| Element | Rule |
|---------|------|
| Start | First formation `decision_at` date **strictly after** product-owner acceptance timestamp recorded in the S2 registration commit |
| Maturity | **120** distinct decision sessions with per-session coverage ≥ **80%** (reject rule in §1) |
| Rejection | §1 **80%** coverage floor → session **reject** |
| Inconclusive | §1 **50%–80%** band → session **inconclusive** |
| Accounting | All configs and declared budgets logged through **`engine/trial_ledger.py:126-151`** (`log_trial` / `log_declared_budget` append to `data/trial_ledger.jsonl`) **before** any forward descriptive scoring job runs (same discipline as `engine/signal_foundry/harness.py:9-14`) |
| Outcome scan | **Forbidden** before registration merge; no rank/gate/size promotion |

**Trial-accounting owner (canonical):** `engine/trial_ledger.py:126-151` — `TrialLedger.log_trial` performs append-only deduplicated writes to the consolidated JSONL ledger.

**Candidates considered and rejected:**

| Candidate | Reason rejected |
|-----------|-----------------|
| `engine/experiments_registry.py:1-27` | Display-only experiments manifest; explicitly does not size or register trials |
| `engine/research_factory/ledger.py:1-10` | Separate research-factory ledger, not the repo-wide multiple-testing memory |
| `engine/lab.py` (trial_ledger import sites) | Consumer/calibrator surface, not the canonical write owner |
| `engine/calibration_hub.py` | Calibration orchestration, not append-only family budgeting |
| `engine/intelligence_registry.py` | Intelligence metadata registry, not trial JSONL writer |

---

## §6 Forbidden (S1 and any gated S2)

1. Rank, gate, or size authority promotion from this hypothesis.  
2. Claims about hidden **fund inflows** or unobserved flow alpha.  
3. **Holdability** or ease-of-holding narratives tied to the descriptive feature.  
4. The **CI-enforced claim word** in user-facing copy (see the CI claim-word checker under `scripts/`).  
5. Front-facing **thesis-verdict vocabulary** (user cycle surfaces use projection windows per house design law).  
6. Outcome scans, threshold tuning on realized returns, or minute-bar assertions.

---

## §7 Explicitly not requested

- Running collectors, engines, or provider purchases.  
- Building dashboards, site templates, or Terminal UI.  
- Trend Persistence Wave C reopening or edits to `research/TREND_PERSISTENCE_PREREG_C1.md`.  
- End-to-end scientific completion promises or capital allocation.

---

## §8 Verify commands (paste-ready)

```bash
git fetch origin main && git diff --name-only origin/main...HEAD
MD=research/product_intelligence_local_delivery/S1_THEME_RELATIVE_INTRADAY_HYPOTHESIS_PROPOSAL_2026-10-06.md
JS=research/product_intelligence_local_delivery/S1_THEME_RELATIVE_INTRADAY_HYPOTHESIS_PROPOSAL_2026-10-06.json
W="valid""ated|已验""证|fal""sif|ref""ut|证""伪"; grep -ciE "$W" "$MD"
python3 -c "import json;json.load(open('$JS'));print('json ok')"; echo rc=$?
python3 - <<'PY'
import json,re
d=json.load(open('research/product_intelligence_local_delivery/S1_THEME_RELATIVE_INTRADAY_HYPOTHESIS_PROPOSAL_2026-10-06.json',encoding='utf-8'))
L={'STATED','PHYSICS','INHERITED','ASSUMED'}
keys=['hypothesis','decision_time','sessions','estimation','benchmark_overlap','self_inclusion','stale_zero_rule','halts_corporate_actions','membership_cutoff','baselines','coverage','costs']
objs=[(k,d.get(k)) for k in keys]+[('registration.'+k,(d.get('registration') or {}).get(k)) for k in ['start_rule','maturity_rule','rejection_rule','inconclusive_rule','accounting_owner_path']]
bad=[k for k,o in objs if not isinstance(o,dict) or o.get('basis_label') not in L or not str(o.get('basis','')).strip() or 'value' not in o]
pat=re.compile(r'backtest|hit[ -]?rate|\bIC\b|sharpe|in-sample|historical (outcome|return|performance)|optimi[sz]ed|tuned on|calibrated on|realized return',re.I)
ob=[k for k,o in objs if isinstance(o,dict) and pat.search(str(o.get('basis','')))]
print('MISSING_OR_BAD',bad); print('OUTCOME_BASIS',ob)
print('schema',d.get('schema'),'distinctness',len(d.get('distinctness',[])),'forbidden',len(d.get('forbidden',[])),'ask',bool(str(d.get('acceptance_ask','')).strip()))
print('PARAMS',len(objs),'BAD',len(bad),'OUTCOME_BASIS',len(ob))
PY
```

(Machine resolver loops for G2/G3 are run at delivery; see seat VERIFY block.)
