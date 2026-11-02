# I0 integrated-answer gate census (read-only)

**MAIN_PIN:** `0beebb3bd1f246a13396c3bd8f996103a26c3b77` (`git fetch origin main && git rev-parse origin/main`, 2026-10-06).  
**Mastermind overlay pin:** `d1a8e672464d9a90dfe5b3608e071f8a730f3c95` (PR #1258).  
**Linear:** not reachable from this lane — MAS-* keys do not appear in macro `agentos/` / `research/` / `docs/` (`rg 'MAS-26[89]|MAS-27[0-4]' agentos research docs` → **0 hits**).

---

## C0 (answer first)

On **MAIN_PIN**, **H01 = ACCEPTED**, **H04 = BUILT_NOT_ACCEPTED**, **H05 = ABSENT**, **H06 = BUILT_NOT_ACCEPTED** — therefore **package-I gate = CLOSED** today (requires all four accepted plus integration permission; only H01 has a macro acceptance record).

| Dep | Label | Evidence (MAIN_PIN unless noted) |
|-----|--------|----------------------------------|
| **H01** | **ACCEPTED** | Kernel `engine/fundamental_forensics/query.py:1`; served query `app/forensics.py:841`. Acceptance `agentos/decisions/DEC-FIF-3A3-ACCEPTED-GOLDEN-QUERY-ON-MAIN.md:5-8`, `agentos/workstreams/WS-FINANCIAL-INTELLIGENCE-FABRIC.md:207`. |
| **H04** | **BUILT_NOT_ACCEPTED** | Display block `engine/expectation_state.py:1-37` (PIT SUE / pead drift). No C19 acceptance record; `research/product_intelligence_local_delivery/E0_EXPECTATIONS_ACCEPTANCE_PATH_2026-10-06.md` **absent** on main (`git show origin/main:…` fatal). K3E surface only on **held PR #8337** (`engine/k3e_expectation_surface.py` — `rg k3e engine/` on main → 0). |
| **H05** | **ABSENT** | Opt-in debt/share qualification (CS **W4/W6**) `agentos/workstreams/WS-CAPITAL-STRUCTURE-INTELLIGENCE-V2.md:203-214` **status: todo**, held behind W2. |
| **H06** | **BUILT_NOT_ACCEPTED** | Private/default-off publication plumbing `engine/fundamental_forensics/query_snapshots.py:62`, health clocks `engine/fundamental_forensics/health.py:11-14`; entitled read `app/forensics.py:147-148`. No `DEC:*MAS-273*` / C19 acceptance in agentos. |

---

## Q1 — Dependency gate table (H01–H07)

| ID | MAS | Label | Owner-native refs | Main code | Acceptance evidence |
|----|-----|--------|-------------------|-----------|---------------------|
| H01 | MAS-268 | ACCEPTED | WS:FINANCIAL-INTELLIGENCE-FABRIC, WS:FUNDAMENTAL-FORENSICS, PR #6352 | `engine/fundamental_forensics/query.py:1`, `app/forensics.py:841` | `DEC:FIF-3A3-ACCEPTED-GOLDEN-QUERY-ON-MAIN.md:5-8` |
| H02 | MAS-269 | BUILT_NOT_ACCEPTED | WS:TEMPORAL-GRAIN-INTELLIGENCE, TrialLedger / Eval OS | `engine/trial_ledger.py:1` | `rg req-4a8daf76317cfe92` → **0 hits**; only reuse law `DEC-TEMPORAL-GRAIN-OWNERSHIP-AND-ZERO-AUTHORITY.md:72` — **not** MAS-269 acceptance |
| H03 | MAS-270 | BUILT_NOT_ACCEPTED | WS:FUNDAMENTAL-FORENSICS | `engine/fundamental_forensics/health.py:1`, `app/forensics.py:147` | FF-0 live closure prose `WS-FUNDAMENTAL-FORENSICS.md:188` — **no** DEC acceptance for MAS-270 |
| H04 | MAS-271 | BUILT_NOT_ACCEPTED | WS:EARNINGS-INTELLIGENCE-OS, DEC:SRC-A1-* | `engine/expectation_state.py:1` | E0 acceptance path file **missing** on main; full expectations surface **#8337 only** |
| H05 | MAS-272 | ABSENT | WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2 W4/W6 | *(none)* | W4/W6 todo @ `WS-CAPITAL-STRUCTURE-INTELLIGENCE-V2.md:203-214` |
| H06 | MAS-273 | BUILT_NOT_ACCEPTED | WS:FUNDAMENTAL-FORENSICS | `engine/fundamental_forensics/private_state.py:1`, `query_snapshots.py:62` | Default-off publication posture in code; **no** acceptance record |
| H07 | MAS-274 | ABSENT | WS:ALPHA-INTELLIGENCE-INTEGRATION, Mastermind #1202 | *(no integrated composer on main)* | Package I text lives only on Mastermind overlay — macro has no MAS-274 carrier |

---

## Q2 — Existing product workflow surfaces

| Surface | Entitlement | Composes today | Owner WS | Live entitled READ? |
|---------|-------------|----------------|----------|---------------------|
| `app/company_intelligence.py:634` GET `/api/company-intelligence/{ticker}` | Anonymous + rate limit; **no** `require_user` | Latest CI v1 teaser via `read_company_intelligence` `:611-624` → reader `:630` | WS:EARNINGS-INTELLIGENCE-OS | **Partial** — public read, not full entitlement |
| `app/company_intelligence.py:693` GET `/api/event-workspace/{ticker}` | Anonymous + rate limit | `event_workspace_public_glance.v1` via `read_current_event_workspace` reader `:753` | WS:EARNINGS-INTELLIGENCE-OS | **Partial** — strips receipts/spans |
| `app/forensics.py:841` POST `/api/forensics/v1/financial/query` | `require_site_full_user` `:111` | Golden AAPL FIF query kernel | WS:FINANCIAL-INTELLIGENCE-FABRIC | **Yes** — paid site user; **not** composed with event/expectation/theme |
| `templates/finance_intelligence.html.j2:23` (+ `site/finance_intelligence.html`) | Authenticated product nav family; client `fi_read_url` | Sector finance dossier — not issuer integrated answer | WS:GMI-FINANCE-INTELLIGENCE | Display read — not package-I bundle |
| Terminal `company-theme-context/[symbol]` (L0 cites `:9-10` @ Terminal `e17622b1`) | Terminal auth + R2 | `engine/company_theme_exposure/views.py:259` `build_bundle` | WS:GMI-THEME-GRAPH | **Yes** on Terminal — theme/tape only |
| `app/dossier_quote.py`, `app/intelligence_hub_market_pulse.py` | **Public** quote-only | Quote Hub projection — no intelligence composition | Terminal market data | Quote read only |

**Templates on main** (`git ls-tree -r origin/main --name-only templates | rg -i 'company|dossier|intel'`): `china_intel.html.j2`, `finance_intelligence.html.j2`, `fund_dossier.html.j2`, `intelligence_hub.html.j2`, etc. — none expose a single entitled integrated nonbinding answer.

**Verdict:** No one existing workflow on macro main performs package-I composition (event + expectation + conditional economics + theme context + FIF) under one entitled read.

---

## Q3 — Deterministic conditional economics

| Module | Line | Owner | Basis / period metadata |
|--------|------|-------|---------------------------|
| **`engine/expectation_state.py`** | `:12-22` (`pead_drift_20d`, SUE, `_benchmark='SPY'`) | Long-hold / earnings display (`_display_only=True`, `_horizon_role='hold_thesis'` `:3-6`) | **Yes** — session windows, disclosed SPY divergence `:14-17` |
| `engine/transmission_calibration.py` | `:1-6` | Transmission / chain library | Regime-conditional **base rates** — not issuer event economics |
| `engine/vol_shock_scorecard.py` | `:444` `_f_event_window` | VSB scoring | Event-window **leg** — not earnings-integrated answer |

**Integrated-answer scope:** closest main owner is **`expectation_state.py`** (deterministic at build, display-only). Not wired into a golden-vertical integrated reader.

---

## Q4 — Theme / tape context (from L0 — not re-done)

| Role | Path:line (MAIN_PIN) |
|------|----------------------|
| Producer | `engine/theme_context.py:589` `compute_theme_context` |
| Reader | `engine/theme_context.py:891` `read_context` |
| Served artifact | `site/basketdata/theme_context.json` (+ `_cn.json`) via `git ls-tree origin/main` — **not** read from sparse disk |

Per-ticker leadership attach: `engine/company_theme_exposure/views.py:259` `build_bundle` (L0 Q3 / Wave F census).

---

## Q5 — Twelve package-I tests (covered / gap)

| # | Test | Covered by (MAIN_PIN) or GAP |
|---|------|--------------------------------|
| 1 | known-at vs decision-at | `tests/test_fundamental_forensics_query.py:187` |
| 2 | later correction under earlier cutoff | `tests/test_fundamental_forensics_financial_intelligence_packet_r2.py:70-118` |
| 3 | unit/period/basis mismatch | `tests/test_fundamental_forensics_query.py:626` |
| 4 | common-source duplication | `tests/test_fundamental_forensics_query.py:501` |
| 5 | missing/withdrawn source | same `:501` withdrawn vintage |
| 6 | current membership leakage | **GAP** (PIT cohort reads held #8486) |
| 7 | incompatible generations | `tests/test_fundamental_forensics_query_snapshots.py:841` |
| 8 | price-response circularity | **GAP** at integrated scope |
| 9 | raw-capture vs normalized baseline | `tests/test_fundamental_forensics_ixbrl_extraction.py:362` |
| 10 | unavailable financial component | `tests/test_fundamental_forensics_financial_intelligence_packet_r2.py:128` |
| 11 | private/public purpose leakage | `tests/test_fundamental_forensics_health.py:22` + `assert_no_private_leak` |
| 12 | trace to source span / calculation | `tests/test_fundamental_forensics_query.py:541` (FIF only) |

**Count: 9 covered / 3 gap** (package-I end-to-end tracing not on event/CI glance).

---

## Q6 — Persistent thesis insertion / contract owner

| Field | Value |
|-------|--------|
| **Owner WS** | `WS:EARNINGS-INTELLIGENCE-OS` (`agentos/decisions/DEC-EARNINGS-INTELLIGENCE-PROGRAM-OWNERSHIP.md:7-13`) |
| **DEC keys** | `DEC:EARNINGS-EVENT-WORKSPACE-PUBLICATION-CONTRACT`, `DEC:EARNINGS-INTELLIGENCE-PROGRAM-OWNERSHIP` |
| **Carrier** | Production `event_workspace.v1` under `company_intelligence/event_workspaces/`; reader `engine/neuralweb/company_intelligence_reader.py:586` `read_event_workspace` |
| **Contract shape on main** | `DEC:EARNINGS-EVENT-WORKSPACE-PUBLICATION-CONTRACT.md:7-13` + `engine/company_intelligence/event_workspace.py` schema/build (`tests/test_company_intelligence_event_workspace.py:1`) |

**Thesis insertion acceptance:** no separate “persistent thesis contract” acceptance beyond event-workspace publication — **mutation requires event-owner acceptance** per package I; enforcement is organizational (DEC/WS), not a dedicated insertion API on main.

---

## Q7 — Gate verdict and I1 freeze list (≤10)

**Verdict: CLOSED** for package-I ship (missing accepted H04/H05/H06 and no integration permission / composer).  
**Read-only census lane:** evidence supports future **OPEN_FOR_READ_ONLY_COMPOSITION** only after seat freezes below — not claimed as live today.

| # | Freeze before I1 composer lane | Pin or GAP |
|---|--------------------------------|------------|
| 1 | Target workflow identity (which existing READ surface is canonical) | **GAP** |
| 2 | Entitlement matrix (teaser vs `require_site_full_user` vs Terminal) | `app/company_intelligence.py:634`, `app/forensics.py:841` |
| 3 | H04 owner-native expectation IDs (SRC-A1 vs K3E) | `DEC:SRC-A1-*`; **GAP** K3E on main |
| 4 | H05 debt/share qualification (CS W4/W6) | **GAP** `WS-CAPITAL-STRUCTURE-INTELLIGENCE-V2.md:203-214` |
| 5 | H06 default-off publication seam | `engine/fundamental_forensics/query_snapshots.py:62` |
| 6 | Per-component degraded states in one answer | **GAP** bundle-level contract |
| 7 | Original/correction replay sources | FIF revision + `read_event_source_revisions` `:1309` — **GAP** unified replay |
| 8 | Trace-to-span on every conclusion | FIF receipts `:541`; **GAP** on public glance |
| 9 | Event-owner acceptance before thesis mutation | `DEC:EARNINGS-EVENT-WORKSPACE-PUBLICATION-CONTRACT` |
| 10 | MAS ↔ macro acceptance map | **GAP** (Linear-only IDs) |

---

## Held PR heads (not on main — read via fetch/show only)

| PR | Head | Note |
|----|------|------|
| #8454 | `049d8d7dae257234b53a99190af4c831dc572ef8` | `app/ticker_news.py` — DRAFT, not on main |
| #8337 | held | `engine/k3e_expectation_surface.py` — not on main |

---

## DO_NOT_REBUILD (grep ALPHA / WAREHOUSE / THESIS / RANKER)

Standing kills include `DNR:KILL-CAUSAL-DAG-ALPHA`, `DNR:KILL-THESIS-LOBE`, `DNR:KILL-ENTRY-21D-THESIS` (`research/DO_NOT_REBUILD.md` §1–2) — integrated answer must not mint a second warehouse, ranker, or thesis lobe.

---

## VERIFY commands (paste targets)

```text
python3 -c "import json;d=json.load(open('research/product_intelligence_local_delivery/I0_INTEGRATED_ANSWER_GATE_CENSUS_2026-10-06.json'));print('deps',len(d['dependencies']),'workflows',len(d['workflows']),'tests',len(d['tests']),'gate',d['gate']['verdict'],'freeze',len(d['freeze_list']))"
git status --porcelain
git diff --stat origin/main -- engine scripts app collectors site data templates .github agentos
git log --oneline origin/main..HEAD
```

**Test command for JSON schema sanity:** same `python3 -c` line above (no pytest — read-only lane).
