# S1 — Theme-relative intraday descriptive strength (hypothesis proposal + registration draft)

**MAIN_PIN:** `77fc9b1c447ab8432284f5a6023dc4558f0d534a` (`git rev-parse origin/main` after `git fetch origin main` on 2026-10-06).  
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

**H-S1 (one sentence):** On each **decision session** (unit of independence), for live theme constituents versus an equal-weight theme benchmark with the constituent excluded, compute trailing-beta **hourly RTH residual returns** at the frozen **11:00 America/New_York** decision clock on clock-aligned vendor hourly bars; the study statistic is the **mean across matured sessions** of the **cross-sectional Spearman rank correlation** between (i) each constituent’s cumulative theme-relative residual return from the **first full RTH hourly bar** through the decision bar and (ii) its cumulative theme-relative residual over **K = 5** completed hourly RTH bars on the **same session** that **end at or before 16:00 America/New_York** (arithmetic: 11:00 + 5 h ≤ 16:00; overnight and next-session bars are out of scope) — **descriptive only**, no tradable-edge promise.

**Null (two-sided):** the mean session-level Spearman correlation equals zero (no systematic rank continuity from pre-decision to same-session forward residual strength).

**Support rule (a-priori):** the **95% two-sided one-sample t-interval** on the per-session Spearman values **excludes 0** (level **ASSUMED** conventional two-sided 95%; method **ASSUMED** session-level t-interval on independent sessions).

**Rejection rule (a-priori):** after maturity, the **same 95% t-interval lies entirely inside** the equivalence band **[−δ, +δ]** with **δ = 0.05** (**ASSUMED** magnitude floor: |ρ| < 0.05 is negligible rank association for cross-sectional theme baskets).

**Inconclusive rule (a-priori):** any other outcome for the interval (including overlap of 0 and the band edges) **or** maturity not met (§5); **session-validity exclusions** (coverage below floor) do not count as rejection.

---

## §2 Distinctness (not a rename)

### Trend Persistence (closed C1-NULL)

**Key line (MAIN_PIN):** `agentos/decisions/DEC-TREND-PERSISTENCE-STOPS-AT-WAVE-C.md:16-22` — Wave C group features on **eleven GICS sectors** with **20/60 session** forward returns vs SPY; C1-NULL, family stops.

**DNR:KILL-TREND-PERSISTENCE-SECTOR-GROUP-PERSISTENCE** — `research/DO_NOT_REBUILD.md:134` closes the eleven-GICS-sector group-persistence constructions (C1-NULL).

**DNR:KILL-TREND-PERSISTENCE-PATH-FEATURE-PROFILE** — `research/DO_NOT_REBUILD.md:133` closes path-shape drawdown-profile constructions (Wave B2 null).

**S1 difference:** Dynamic **theme** baskets, **hourly RTH** decision clock, **descriptive intraday residual rank-continuity statistic** — no sector-group persistence cells and no pre-registered 20/60-session SPY-relative outcome family.

### DNR:KILL-INTRADAY-CHRONICLE

**Key line (MAIN_PIN):** `research/DO_NOT_REBUILD.md:47` — forbids intraday **chronicle** writes in hourly jobs; not a ban on price bars.

**S1 difference:** Read-only use of gitignored `data/intraday/<T>.parquet` accrual and on-main `data/intraday_flow/ledger.parquet`; **no** `data/chronicle/*.jsonl` lane writes.

### Daily multi-window strength (S0 §Q3)

**Bounded absence (MAIN_PIN):** `git show origin/main:research/DO_NOT_REBUILD.md | grep -nE 'narrative_rotation|us_board_rank'` returns only `us_board_rank` inside unrelated kill-row text (line 126); **no** DNR key names `narrative_rotation` or daily multi-window intraday strength.

**Pins (display context only, not outcome basis):** `engine/narrative_rotation.py:851-854` daily basket `r10`; `engine/us_board_rank.py:1954-1977` **63-session daily total-return** z-scores for the leaders lane — neither scores hourly theme-relative residuals.

**S1 difference:** **Hourly RTH** same-session rank-continuity after **11:00 America/New_York**, not daily close/session windows.

### Prophet regime studies

**Key line (MAIN_PIN):** `agentos/workstreams/WS-PROPHET-REGIME-TIMEFRAME-RESEARCH.md:46` — “Any further theme-persistence work is a NEW pre-registration (09 §2 C1-W2 construction), never a re-run.”

**DEC:D-LANE-PARKED-AS-FORWARD-STUDY** — `agentos/decisions/DEC-D-LANE-PARKED-AS-FORWARD-STUDY.md:8-12` parks retrospective theme-conditioned Prophet conditioning; forward study only with honest membership floors.

**Handoff pins:** `research/prophet_v4/astra_regime_indicator_handoff_20261004/09_WAVE1_SYNTHESIS_AND_PRODUCT_IMPLICATION.md:24` names **C1-W2** as a **different state-variable construction** (63/126-session rank-stability candidates) against a frozen control; `:43` lists **D forward study** under `DEC:D-LANE-PARKED-AS-FORWARD-STUDY` — not intraday theme residuals.

**Session fact (not a regime study):** `engine/prophet_entry_policy.py:58-66` holds US RTH open/close and bounded **2026** early-close table only.

**S1 difference:** S1 is **not** C1-W2 rotation-state construction, **not** a Prophet timeframe-transposition study, and **not** lane-D theme-conditioned event outcomes; it is a **standalone intraday descriptive** registration on hourly theme residuals.

### Daily residual momentum owners (`engine/residual_alpha.py`, `engine/residual_momentum.py`)

**Key lines (MAIN_PIN):** `engine/residual_alpha.py:1-8` — **daily** sector-neutral residual momentum, medium horizon, wired to leaders context; `engine/residual_momentum.py:1-8` — **multi-window daily** multi-factor generalization. Docstrings record which horizons reversed or worked historically; **S1 does not import those findings** as direction or thresholds.

**S1 difference:** S1 uses **hourly RTH** theme-equal-weight residuals with **daily-estimated trailing beta** (§3 row 3) for a **same-session descriptive correlation**; it does **not** inherit sector-neutral daily ranking scores or multi-window factor tables as the hypothesis statistic.

### WS:TEMPORAL-GRAIN-INTELLIGENCE (active)

**Key line (MAIN_PIN):** `agentos/workstreams/WS-TEMPORAL-GRAIN-INTELLIGENCE.md:101` — Technical Opportunity owns U.S.-equity **data/clock/session**; this workstream **consumes** rather than duplicates it.

**Reuse map:** `research/prophet_v4/astra_regime_indicator_handoff_20261004/02_SOURCE_CENSUS_AND_REUSE_MAP.md:116` requires distinct **`4H-CLOCK`** vs **`195M-RTH`** definitions; no pooling across constructions.

**S1 difference:** S1 **fixes one grain** — **Polygon clock-aligned hourly bars** filtered to RTH in the study layer — and does **not** select among signal grains or session partitions; alignment with TOI clocks is an **S2 audit**, not an S1 claim.

### DNR:KILL-OFFHORIZON-VERDICTS (forbidden overlap)

**Key line (MAIN_PIN):** `research/DO_NOT_REBUILD.md:46` — verdicts only at registered `horizon_role` rulers.

**S1 difference:** Prospective registration fixes **one** same-session forward window (five hourly RTH bars ending by 16:00 ET) before any scoring; no ad-hoc horizon ladder.

---

## §3 Frozen parameters (S0 §Q6 rows + coverage)

Each row closes the S0 §Q6 pin or fills the named GAP. No value is justified by historical outcomes, backtests, or realized performance scans.

| # | Field | Frozen value | Basis label | Basis (one line) | Closes |
|---|--------|--------------|-------------|------------------|--------|
| 1 | Decision time | **11:00 America/New_York** on an hourly bar boundary; `decision_at` offset-aware ISO at the **end** of the completed 10:00–11:00 ET hourly bar; forward **K = 5** same-session RTH bars with bar **ends** ≤ 16:00 ET (**11:00 + 5 h ≤ 16:00**) | ASSUMED | Wall-clock chosen before data read; matches Package S “freeze the decision time” | S0 §Q6 decision-time GAP |
| 2 | Session boundaries | **RTH only** 09:30–16:00 America/New_York; **exclude** early-close sessions per `engine/prophet_entry_policy.py:58-66` (`_RTH_EARLY_CLOSE_ET`, `_EARLY_CLOSE_DATES`, `_SUPPORTED_SESSION_YEARS = frozenset({2026})` at line 62) because the forward window cannot complete before **13:00** ET; **exclude** any session year **not** in `_SUPPORTED_SESSION_YEARS` until the policy owner extends that frozenset (**INHERITED** explicit policy mutation rule at lines 64–65); `lib/nyse_calendar.py:10-13` does **not** model early closes | INHERITED + PHYSICS | Prophet entry policy + physics of shortened RTH; calendar module gap acknowledged | S0 §Q6 session pin |
| 3 | Trailing-only beta/volatility | **63** completed **daily** RTH sessions of returns strictly before the decision session; OLS beta vs theme benchmark on **daily** returns; apply that beta to **hourly** bar residuals (slow-moving exposure); vol from same pre-decision daily window only | ASSUMED + INHERITED | **63** names `engine/us_board_rank.py:1954` `LEADERS_MOMENTUM_SESSIONS` as a **trailing-return** window, **not** a beta window — S1 borrows the **length** only; daily beta on hourly residuals is an a-priori slow-factor approximation | S0 §Q6 trailing beta/vol GAP |
| 4 | Benchmark overlap | Theme benchmark = equal-weight return of live theme members on the same hourly bar; residual = constituent return minus beta×benchmark return on that bar; **departs** from `engine/residual_alpha.py` sector-neutral daily construction (§2) | STATED | Package S benchmark overlap; hourly theme scope | S0 §Q6 benchmark overlap GAP |
| 5 | Constituent self-inclusion | Constituent **excluded** from its theme benchmark weights on every bar | PHYSICS | Including the name in its own equal-weight benchmark mechanically correlates the residual with its own return at weight **1/N** | S0 §Q6 self-inclusion GAP |
| 6 | Stale/missing/zero-return | Missing hourly bar → omit cell; **zero-volume** bar → omit; **zero return with positive volume** → omit cell (**ASSUMED** bad tick); **repeated identical closes** across **three or more consecutive** positive-volume bars → **exclude session** (**ASSUMED** stale-print guard); corrupt per-ticker store → absent per `scripts/build_polygon_intraday.py:171-185` | INHERITED + ASSUMED | Collector fail-soft read plus explicit stale/repeated-close and zero-return rules | S0 §Q6 stale/missing GAP |
| 7 | Halts/corporate actions | **Split-adjusted** hourly OHLCV (`adjusted: true` at `scripts/build_polygon_intraday.py:135-136`); **dividends** follow vendor split-adjusted policy (**ASSUMED** vendor-defined inside adjusted aggregates — **S2 audit**); same-session window **excludes overnight ex-date jumps**; sessions with no post-delay RTH bars omitted | INHERITED + ASSUMED + PHYSICS | Receipt fields + session physics | S0 §Q6 halts GAP |
| 8 | Membership cutoff | At each formation date, `engine/basket_membership_pit.py:694-705` `members_asof(..., suite="baskets")`; **exclude** sessions where `pit=False`; S2 records git blob sha of `data/baskets/membership.json` at registration metadata when needed | INHERITED | Canonical US PIT reader; `scripts/build_intraday_flow.py:324-325` is load path only | S0 §Q6 membership pin |
| 9 | Raw and residual baselines | **Raw:** hourly RTH simple return; **Residual:** trailing-beta-adjusted vs theme benchmark per rows 4–5; **departs** from daily `engine/residual_momentum.py` multi-window factor table | STATED | Package S raw vs residual; not daily residual-momentum scores | S0 §Q6 baselines GAP |
| 10 | Costs | Signal Foundry battery declares **8 bps** for **excess_return / absolute_return + single_series** cost-aware evaluations (`engine/signal_foundry/harness.py:13-14`) — a **declared assumption**, not estimated from outcomes, and **not** an intraday round-trip cost; **no** cost applied to the §1 descriptive Spearman statistic; optional display-tier sensitivity only | INHERITED | Accurate harness scope | S0 §Q6 costs GAP |
| 11 | Coverage | **Session-validity:** if fewer than **80%** of scheduled constituent×hour cells in the forward window are present, **exclude** that session from the matured sample (not a thesis rejection); universe = tickers under existing hourly accrual (`.github/workflows/intraday.yml:55-60`) | STATED + INHERITED | Package S coverage on existing keys; validity separate from §1 interval rules | S0 §Q5 estate gap |

**Stale-print note:** sessions flagged for **repeated** identical closes are excluded before maturity accrual (row 6).

**Dividend note:** same-session windows omit overnight ex-date jumps; vendor **dividend** handling inside `adjusted: true` bars is row 7.

**Bar alignment (collector, MAIN_PIN):** `scripts/build_polygon_intraday.py:262-263` requests Polygon aggregates with `adjusted: true` and **no RTH/session filter at write**; bars are clock-aligned UTC timestamps. The **09:00–10:00 ET** bar **mixes pre-market and RTH** under clock alignment — **ASSUMED** “first full RTH hourly bar” means the bar **ending 10:00 ET** until an **interval/alignment audit** (Package S / TOI W2) positively recovers RTH-only hourly labels (**S2 prerequisite**).

**Clock owner consumption:** S1 follows **Technical Opportunity’s** U.S. equity clock/session ownership (`agentos/workstreams/WS-TEMPORAL-GRAIN-INTELLIGENCE.md:101`) and **does not** adopt `4H-CLOCK` or `195M-RTH` session partitions from `research/prophet_v4/astra_regime_indicator_handoff_20261004/02_SOURCE_CENSUS_AND_REUSE_MAP.md:116` until positively recovered.

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

**PIT membership search (bounded, MAIN_PIN):** `git ls-tree -r origin/main --name-only data/baskets/` lists `membership.json` and `membership_history.parquet`; `git grep -l membership_history origin/main -- scripts/ engine/` includes `engine/basket_membership_pit.py` (canonical `members_asof` reader).

---

## §5 Prospective registration plan (draft)

| Element | Rule |
|---------|------|
| Start | First formation `decision_at` date **strictly after** product-owner acceptance timestamp recorded in the S2 registration commit |
| Maturity | **120** distinct **valid** decision sessions (after session-validity exclusions) |
| Support / rejection / inconclusive | §1 interval rules on the mean session Spearman statistic |
| Session validity | Forward-window constituent×hour coverage **≥ 80%** — otherwise **exclude** session from sample |
| Accounting | All configs and declared budgets logged through **`engine/trial_ledger.py:126-151`** before any forward descriptive scoring job runs |
| Outcome scan | **Forbidden** before registration merge; no rank/gate/size promotion |

**A-priori parameter table (§1 + §5 numbers):**

| Parameter | Value | Basis label | A-priori reason |
|-----------|-------|-------------|-----------------|
| Decision clock | 11:00 America/New_York | ASSUMED | Freeze one intraday clock before data read |
| Forward bars K | 5 | STATED | Same-session window ending at regular close (11:00+5h≤16:00) |
| Coverage validity floor | 80% cells | ASSUMED | Conventional minimum usable panel per session |
| Interval level | 95% two-sided | ASSUMED | Standard reporting convention |
| Equivalence δ | 0.05 Spearman | ASSUMED | |ρ|<0.05 treated as negligible rank association |
| Maturity sessions | 120 valid sessions | ASSUMED | With **ASSUMED** per-session σ≈0.25, SE≈0.023, 95% half-width ≈0.045 separates 0 from δ without outcome tuning |

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
import re,subprocess
md=open('research/product_intelligence_local_delivery/S1_THEME_RELATIVE_INTRADAY_HYPOTHESIS_PROPOSAL_2026-10-06.md',encoding='utf-8').read()
cites=sorted(set(c for c in re.findall(r'([A-Za-z0-9_./-]+):(\d+)(?:-(\d+))?',md) if ('/' in c[0] or '.' in c[0]) and re.search('[A-Za-z]',c[0])))
miss=0
for p,a,b in cites:
    r=subprocess.run(['git','show','origin/main:'+p],capture_output=True,text=True)
    if r.returncode!=0: print('MISS-PATH',p,a,b); miss+=1; continue
    L=r.stdout.splitlines(); lo=int(a); hi=int(b or a)
    if lo<1 or hi<lo or hi>len(L) or not any(x.strip() for x in L[lo-1:hi]): print('MISS-LINE',p,a,b,'len',len(L)); miss+=1
    else: print('OK',p+':'+a+('-'+b if b else ''),'|',L[lo-1].strip()[:90])
print('CITES',len(cites),'MISS',miss)
PY
python3 - <<'PY2'
import re,subprocess
MD='research/product_intelligence_local_delivery/S1_THEME_RELATIVE_INTRADAY_HYPOTHESIS_PROPOSAL_2026-10-06.md'
t=open(MD,encoding='utf-8').read()+open(MD[:-3]+'.json',encoding='utf-8').read()
ks=set(re.findall(r'\b((?:KILL|LAW|HOLD)-[A-Z0-9]+(?:-[A-Z0-9]+)*)',t))|{'DEC-'+m for m in re.findall(r'\bDEC[-:]([A-Z0-9]+(?:-[A-Z0-9]+)*)',t)}
dnr=subprocess.run(['git','show','origin/main:research/DO_NOT_REBUILD.md'],capture_output=True,text=True).stdout
dec=subprocess.run(['git','ls-tree','--name-only','origin/main','agentos/decisions/'],capture_output=True,text=True).stdout.split()
ab=0
for k in sorted(ks):
    ok=('agentos/decisions/'+k+'.md' in dec) if k.startswith('DEC-') else ('| '+k+' |' in dnr)
    print('FOUND' if ok else 'ABSENT',k); ab+=0 if ok else 1
print('KEYS',len(ks),'ABSENT',ab)
PY2
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
