# Pullback source / clock / basis / rights qualification — eligible-input manifest (O1 / T02)

**Program:** `WS:GREY-DEER-RISK-INTELLIGENCE` (MAS-258) · **Operation:** `risk-radar-pullback-20261009` ·
**Carrier key:** `grey-deer-fable-orchestration-20261003-001` · **Parent execution:** `grey-deer-20261003-astra-pickup-001` ·
**Task:** O1 / T02 (`GD-PB-T02`, predecessor `GD-PB-W0` = PR #8785 merged at `2dd5f5078cba`) ·
**Manifest version:** `1.0.0` (2026-10-11) · **Writer:** Fable seat (session `da1ad7ad`).

**Status: RECORDED — owner projection.** This file is the versioned eligible-input manifest the T02
packet asks for: for every input the pullback operation touches it records producer, source-use
receipt, available-at / vintage class, units, basis, market, cohort, missingness and allowed uses,
and gives one disposition — `recorded` or `source_unavailable` (with the exclusion reason). It is a
**projection over determinations that already exist on main**, not a source store and not a rights
grant: it creates no entitlement, quotes no commercial term, ratifies nothing outside the pullback
scope, and where the canonical register reads UNKNOWN the input is `source_unavailable` for that
use. Every disposition below cites the file and line it is read from; a successor re-pins those
lines before relying on them.

Read-only anchors (none of this code is copied here): the observation adapter
`lib/us_pullback_observation.py` (S08) and the causal feature contract
`research/grey_deer/PULLBACK_CAUSAL_FEATURE_CONTRACT_2026-10-10.md` (S10) exist only on PR #8721's
head `f28759c84e2e1d8be0d96706861f69418bff9ceb` (`sol/risk-radar-pullback-depth-20261009`, DRAFT, live
incumbent writer). `f28759c8` is **not** an ancestor of `origin/main`; this manifest cites those
blobs by pinned revision and never edits that branch.

---

## 0. Determinations in one screen

| # | Determination | Consequence for the pullback operation |
|---|---|---|
| D1 | The only licensed, historically-available US daily price store is the Massive `us_stocks_sip/day_aggs_v1` tape, and its history floor is a **rolling ~5-year window** — `EARLIEST_ENTITLED = date(2021, 7, 6)` (`collectors/massive_stock_day.py:150`; probe-verified 2026-07-03, days before the floor 403; "each month of delay permanently loses a month of whole-market history"). | Licensed historically-available evidence exists for **2021-07-06 → present only**. Every pre-2021 episode in the masterplan's sampling proposal (1998, 2000–02, 2007–09, 2011, 2015–16, 2018, 2020) has **no licensed historically-available price evidence** in this repo. |
| D2 | The Yahoo archive (`data/yahoo/*.parquet`, `collectors/yahoo.py`) is `vendor_terms_personal_use` (`config/dataset_registry.yml:63,104`), is re-adjusted at every fetch, and carries no recorded vintage. Witness: `origin/main:data/yahoo/SPY.parquet` (blob `9b306b508842`, sha256 `3c747f8dabd2e5a7…`) is already not the archive S07 was computed from (S07 source hash `6c785d556c22e20f85f89f55597b10469f0fc4c40a577b8efb04bc11964a3152`). | Yahoo-derived inputs are **not a source** for commercial fitting or publication (register lines 139–153); they stay `source_unavailable` for those uses and are allowed only as internal diagnostics. S07 (`PULLBACK_OOS_BASELINE_RESULT_2026-10-09.md`) is diagnostic, never authority-grade — its own lines 74–76 say so. |
| D3 | The live radar / leadership-crack / intl producers read Yahoo closes (`engine/risk_radar.py:429-436,669,684,688`; `engine/leadership_crack.py:87,140-143`; `engine/risk_radar_intl.py:63,101-102,120,126`) and the radar's own forward-log measure is calibrated on "empirical 2006-2026"; `scripts/build_risk_radar_probability_evidence.py:71` labels its evidence `reconstructed_historical`. | The existing probability evidence (`data/risk_radar/probability_evidence.json`, h10 base_rate 0.0823, Brier skill 0.0709) is **CURRENT_VINTAGE diagnostic**, internal-only. It may inform priors; it may not be published as a licensed-history result or relabelled as another market's odds (Alertful A13). |
| D4 | Massive rights are RECORDED by pointer only: register `research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md:16-20` → `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md` (acquisition `:8-11`; processing `:21-24`, `:31-35`; storage `:44-46`, `:21-22`; model use `:37-39`, "feed scope remains controlling"; user redistribution `:28-30`, "feed-specific written designation remains controlling"). Register line 10: determinations are recorded for the seat's ratification; "nothing here is a grant." | US SPY Massive closes are `recorded` for internal fitting/evaluation within the entitled feed scope. **User-facing publication of any derived pullback probability remains gated on the feed-specific written designation** (register line 20) — this manifest does not supply it. The entitlement record is cited, never quoted, never committed to a public surface. |
| D5 | Basis: the registry declares the Massive tape `adjustment: none` / `close_raw` (`config/dataset_registry.yml:134-152`; "MEASURED NVDA 2024-06-03 = 1150.00 — the price actually PRINTED"); `engine/close_pass/massive_close.py` fetches `adjusted=false`. S08 labels its input `split_adjusted_dividend_unadjusted_close` — Yahoo's `close_price` semantics (`collectors/yahoo.py:9-10`). The two coincide **only while no split-like event occurs**; S08's `_split_like_break` (`SPLIT_LIKE_RATIO = 0.75`) raises `SourceRefused("price_basis_discontinuity")`. Canonical vocabulary: `lib/dataos/price.py:71` `class AdjustmentBasis` (RAW / SADJ / TRADJ with `describes`, `lawful_for`, `unlawful_for`). | Declared basis for the qualified SPY sample is **RAW (`close_raw`)**; the adapter's SADJ-equivalence is a *conditional assertion* that fails closed on any discontinuity. Mixing a RAW origin with a TRADJ outcome (the leadership-crack `close` preference, `engine/leadership_crack.py:140-143`) is a basis mismatch and is refused, never silently reconciled. |
| D6 | China: `collectors/china_prices.py` downloads with `auto_adjust=True`; no CN rights record exists; `research/DO_NOT_REBUILD.md:132` `DNR:KILL-CN-ADJUSTED-TAPE-LEGAL-LIMIT` kills the adjusted-price CN tape. | CN inputs are `source_unavailable` for every use beyond internal diagnostics. The `510300.SS` benchmark labelling decision (continuation handoff line 81, open item O-d) is **recorded as open and routed to the data-source owner** — it is not assumed here. |
| D7 | `data/intl_etf/` (`collectors/intl_etf.py`, 23 iShares ETFs, `auto_adjust=True`), `data/breadth/` (`collectors/breadth.py:402`, yfinance `auto_adjust=True` batches), `data/cboe/` (`collectors/cboe_indices.py:43,101`, `cdn.cboe.com` CSV), and `data/baskets/ohlcv/` (`collectors/edgar_deadname_prices.py`, Stooq → Polygon → yfinance, `auto_adjust=True`) have **no row in `config/dataset_registry.yml`** (grep for `intl_etf`, `baskets/ohlcv`, `breadth`, `cboe` ids: empty). | Unregistered substrates are `source_unavailable` for fitting and publication until a registry row with a rights determination exists. They remain readable by the existing live producers (those producers are not this operation's to change) and usable as internal diagnostics. |
| D8 | Three evidence classes are distinct and never pooled (§2): CURRENT_VINTAGE (re-derivable from today's vendor state), HISTORICALLY_AVAILABLE (a store with a recorded first-available day and no re-adjustment at read), GENUINELY_ISSUED (the forward log the engine wrote at `asof`). | The minimal qualified fitting sample (§5) is HISTORICALLY_AVAILABLE only; forward logs grade the engine's own issued states and are not a fitting sample; CURRENT_VINTAGE results are diagnostics. |

Acceptance cases from the handoff assessment: **A03 (purpose-specific rights)** and **A04 (historical
availability)** were `NOT_EXECUTED_BY_THIS_ASSESSMENT`. This manifest closes the *determination*
half of both for the US SPY Massive input (D1, D4) and fails every other input closed; the cases
themselves are executed when the dependent fitting (T22 prereg → observed-move primitives) runs
against this manifest — see §6.

---

## 1. Scope and method

**Inputs in scope** = every series the pullback operation's declared inputs (S08, S10) read, plus
every series the three live producers that own `data/risk_radar/`, `data/risk_radar_intl/` and
`data/leadership_crack/` actually read today. Method: the producer source was read (not its docs),
the store's receipt on `origin/main` was read with `git cat-file -p origin/main:<path>` (this
worktree is sparse; `data/` is omitted), and rights were resolved only from files already on main
(the registry's `licensing:` fields and the Prophet US source-rights register). No vendor name, file
visibility or public URL was used to infer a commercial right (T02 acceptance rule).

**Dispositions.** `recorded` = a rights determination exists on main for the stated use AND the
store has a recorded first-available day AND basis/units/market/cohort are declared. Anything less
is `source_unavailable` with the first failing reason named. `source_unavailable` blocks only the
dependent fitting/publication of that input (T02 stop condition); it never blocks the measured-only
lanes (masterplan W4) and never triggers a Yahoo production fallback or fabricated historical
membership.

**Register posture used throughout** (`research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md`):
line 8 — eight source families; line 9 — determination kinds RECORDED / DETERMINED-FROM-PUBLISHED-TERMS /
UNKNOWN; line 10 — recorded for seat ratification, "nothing here is a grant"; line 12 — Massive
section; lines 26–30 — first-party curated baskets / theme graph (`config/theme_sources.yml:22-27`,
`rights_class: direct_display_ok`); line 100 — FRED model use UNKNOWN → "not a source"; lines
129–131 — Nasdaq not a source; lines 139–143 — Yahoo acquisition internal-only, model use /
redistribution not a source; lines 149–153 — basket/SPY closes acquisition RECORDED internal-only,
model use and user redistribution UNKNOWN → not a source.

---

## 2. Evidence classes

| Class | Definition | Who may use it for what | Coverage this manifest can attest |
|---|---|---|---|
| **CURRENT_VINTAGE** | A series re-derivable from the vendor's *current* state. Its values for past dates may differ from what was knowable on those dates (re-adjustment, restatement, survivorship). No first-known receipt. | Internal diagnostics, priors, sanity checks. **Never** a fitting sample for a published probability, never "first-known" evidence. | Yahoo archive (US, FX, intl), breadth matrix, intl ETF closes, baskets OHLCV, CN closes, `probability_evidence.json` (`reconstructed_historical`), S07's 96 origins. |
| **HISTORICALLY_AVAILABLE** | A store whose rows carry a recorded first-available day, are written as printed (no re-adjust at read), and whose coverage receipt names first/last day and missing runs. | Fitting and evaluation for the uses the rights determination records. | **US SPY Massive RAW closes, 2021-07-06 → 2026-10-07** (store receipt §4 row 1). FRED series and FRED vintages for internal use. Nothing else. |
| **GENUINELY_ISSUED** | The engine's own forward ledgers written at `asof` by the nightly (sole advancer of forward ledgers). | Grading the engine's issued states over their own window. Not a fitting sample (N is small, states are autocorrelated, the writer is the thing under test). | `data/risk_radar/forward_log.jsonl` 64 rows, asof 2026-06-23 → 2026-10-09; `data/leadership_crack/forward_log.jsonl` from asof 2026-07-17; `data/risk_radar_intl/<mkt>_forward_log.jsonl` per market. |

Masterplan §6.1's episode list (1998 … 2023 banking stress) is a **sampling proposal**, not evidence:
under D1 none of its pre-2021-07-06 episodes has a HISTORICALLY_AVAILABLE licensed price row.
"SPY outcomes do not supply semiconductor, bank, China or portfolio probabilities" (masterplan §6.2)
and "US probability cannot be relabeled as another country's odds" (Alertful A13) bind every class.

---

## 3. Fail-closed clock, market and basis rules

These are the rules the eligible-origin builder (§5) and any later primitive must satisfy; the
canonical helpers already exist and are cited rather than re-implemented.

1. **Observation date ≠ retrieval date.** `lib/market_observations.py` — `observation_date_allowed`
   (line 15), `filter_session_observations` (35), `snapshot_rejection_reason` (45),
   `current_adjusted_columns` (75), `provider_date_matches` (95): "Retrieval/heartbeat timestamps
   never become market observation dates." An origin's `available_at` is the store's first-processed
   session for that bar, never `updated_at`.
2. **Future revisions cannot enter earlier origins.** A row that is re-adjusted, restated or
   back-filled after origin `t` is unknown at `t`. For a CURRENT_VINTAGE source this cannot be
   proven, so such a source cannot supply an origin. For the Massive store the as-printed basis
   (D5) is what makes it provable.
3. **Malformed or future clocks fail closed.** Any `asof` later than the store's `latest_date`
   (`data/massive_stock_day/_manifest.json`: `latest_date 2026-10-07`, `updated_at
   2026-10-09T03:17:04.508990+00:00`), any non-session date, any row whose provider date does not
   match (`provider_date_matches`) is refused, not coerced.
4. **Wrong market / wrong basis fail closed.** Market is declared per input (§4); an origin and its
   outcome must share market, basis (`AdjustmentBasis`, `lib/dataos/price.py:71`) and units. The
   S08 discontinuity guard (`SourceRefused("price_basis_discontinuity")`) is the model: refuse, name
   the reason, never reconcile silently.
5. **Legal zero is distinct from absent.** A printed zero (a legitimate value, e.g. a zero-volume
   session or a 0.0 spread) is data; a missing row is `absent` and is recorded in missingness, never
   filled. The Massive receipt's `max_missing_run_weekdays 0` is a measured absence count, not an
   assertion of zeros.
6. **Timezone.** The Massive tape is `timezone: America/New_York`, `frequency: 1d`
   (`config/dataset_registry.yml:134-152`); session alignment for any non-US input (§4 rows
   8–12) is per-market and is one of the reasons those rows fail closed today.

---

## 4. The manifest

Columns: **Producer** (what writes it) · **Store / registry** (path; `config/dataset_registry.yml`
id or `UNREGISTERED`) · **Rights** (register / registry pointer) · **Available-at / vintage** (evidence
class and first/last day where a receipt exists) · **Units / basis / market / cohort** ·
**Missingness** · **Allowed uses** · **Disposition**.

| # | Input | Producer | Store / registry | Rights | Available-at / vintage | Units / basis / market / cohort | Missingness | Allowed uses | Disposition |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **US SPY daily close (Massive)** | `collectors/massive_stock_day.py` (`load_ticker` :736; canonical home R2, git holds JSON sidecars) | `data/massive_stock_day/{ticker}.parquet` · `equity.bars.daily.massive` (L1, PRODUCED, owner macro-dashboard, `conflict_policy PRIMARY_ONLY`, version 1.0.0; registry :134-152) | RECORDED by pointer: register :16-20 → entitlement record :8-11 / :21-24 / :31-35 / :44-46 / :21-22 / :37-39 / :28-30. Feed scope controlling; user-facing feed designation controlling. **No `licensing:` field on the registry row** (gap, routed §8). | HISTORICALLY_AVAILABLE. Store receipt `origin/main:data/massive_stock_day/_manifest.json`: `n_tickers 21697`, `coverage.first_day 2021-07-06`, `coverage.last_day 2026-10-07`, `n_processed_days 1372`, `recent_window_bdays 90`. Floor is rolling (D1). | USD · **RAW** (`close_raw`; SADJ-equivalent only absent a split event, fail-closed) · US (NY sessions) · single ticker SPY | `max_missing_run_weekdays 0`, `max_missing_run_weekdays_recent 0`, `missing_sample []` | Internal fitting / evaluation / diagnostics within feed scope. User-facing publication of derived probabilities: **only under the feed-specific written designation** (register :20) — not supplied here. | **`recorded`** (internal fitting + evaluation). `source_unavailable` for user-facing publication until the designation is recorded. |
| 2 | US SPY daily close (Yahoo) | `collectors/yahoo.py` (`close` = TRADJ Adj Close; `close_price` = SADJ, :8-12) | `data/yahoo/SPY.parquet` · Yahoo rows (registry :55-104; `licensing: vendor_terms_personal_use` :63, :104) | Register :139-143 (acquisition internal-only; model use / redistribution not a source); :149-153 (SPY closes model use UNKNOWN). | CURRENT_VINTAGE; re-adjusted at fetch; no vintage record (D2 witness hashes). | USD · TRADJ (`close`) or SADJ (`close_price`) · US · SPY | Not receipted | Internal diagnostic only; S07 reproduction; sanity cross-check against row 1. | **`source_unavailable`** — personal-use terms + unrecorded vintage. |
| 3 | HYG, TLT, `_MOVE` (credit / duration / rates-vol legs) | `collectors/yahoo.py` | `data/yahoo/{HYG,TLT,_MOVE}.parquet` · Yahoo rows | As row 2. | CURRENT_VINTAGE. | USD / index points · TRADJ · US · single tickers | Not receipted | Internal diagnostic (live radar legs `engine/risk_radar.py:684,688`). | **`source_unavailable`** (same reason as row 2). |
| 4 | DEXJPUS (JPY carry leg) | FRED collector | `data/fred/{series}.parquet` (registry :174; `licensing: public_domain` :188) | Register :100 — model use UNKNOWN → not a source for user-facing model use. | HISTORICALLY_AVAILABLE for the FRED release clock; **true vintages only via row 5**. | USD/JPY · n/a · FX · single series | Not receipted here | Internal fitting / diagnostics. | **`recorded`** (internal). `source_unavailable` for user-facing model use. |
| 5 | FRED vintages | FRED vintage collector | `data/fred_vintage/vintages.parquet` (registry :211; `licensing: public_domain` :225) | As row 4. | HISTORICALLY_AVAILABLE with explicit vintage columns — the only genuinely PIT macro store on main. | per series · n/a · US macro · per series | Not receipted here | Internal fitting / diagnostics; the PIT reference for any macro leg. | **`recorded`** (internal). |
| 6 | US breadth matrix (`build_nh_contraction`) | `collectors/breadth.py` (yfinance batches, `auto_adjust=True` :402) | `data/breadth/breadth_split.parquet` · **UNREGISTERED** | None recorded. Vendor terms as row 2. | CURRENT_VINTAGE (back-adjusted window merged over cache). | count / ratio · TRADJ constituents · US · evolving universe (membership not PIT) | Not receipted | Internal diagnostic. | **`source_unavailable`** — unregistered + Yahoo-derived + non-PIT membership. |
| 7 | COR1M (CBOE implied correlation) | `collectors/cboe_indices.py` (`cdn.cboe.com` history CSV :43, :101) | `data/cboe/cor1m.parquet` · **UNREGISTERED** | **None recorded** — no determination exists on main; public URL is not a right. | CURRENT_VINTAGE (full-history CSV re-pulled). | index points · n/a · US · single index | Not receipted | Internal diagnostic. | **`source_unavailable`** — no rights determination (routed §8). |
| 8 | Global breadth (23 iShares single-country ETFs) | `collectors/intl_etf.py` (`auto_adjust=True`, overwrite-overlap :94) | `data/intl_etf/*.parquet` · **UNREGISTERED** | None recorded; vendor terms as row 2. | CURRENT_VINTAGE. | USD · TRADJ · multi-market (US-listed proxies) · fixed 23-ticker list (verified 2026-07-02) | Not receipted | Internal diagnostic (`engine/risk_radar.py:460-462`). | **`source_unavailable`**. |
| 9 | Basket members OHLCV (leadership crack) | `collectors/edgar_deadname_prices.py` (Stooq → Polygon → yfinance, `auto_adjust=True` :156) | `data/baskets/ohlcv/{ticker}.parquet` · **UNREGISTERED** (first-party basket *definitions* are `direct_display_ok`, register :26-30 — the definitions, not the prices) | Mixed vendors; none recorded for the prices. | CURRENT_VINTAGE; survivorship explicit in the collector docstring (delisted names only via Stooq/Polygon). | USD · TRADJ · US · basket cohorts, **historical membership not reconstructable** (GD-1C: PIT membership unreconstructable) | Not receipted | Internal diagnostic. | **`source_unavailable`** — no fabricated historical membership (T02 stop). |
| 10 | CN closes incl. `510300.SS` | `collectors/china_prices.py` (`yf.download(..., auto_adjust=True)`) | `data/china*/` · CN rows carry no rights record | `DNR:KILL-CN-ADJUSTED-TAPE-LEGAL-LIMIT` (`research/DO_NOT_REBUILD.md:132`). | CURRENT_VINTAGE, adjusted. | CNY · TRADJ · CN (Shanghai sessions) · benchmark + sector ETFs | Not receipted | Internal diagnostic only. | **`source_unavailable`** — killed tape + no rights + no labelling decision (O-d open, §8). |
| 11 | CNH_F, DX-Y.NYB (intl FX legs) | `collectors/yahoo.py` | `data/yahoo/{CNH_F,DX-Y.NYB}.parquet` | As row 2. | CURRENT_VINTAGE. | FX / index · n/a · cross-market | Not receipted | Internal diagnostic (`engine/risk_radar_intl.py:101-102,120,126`). | **`source_unavailable`**. |
| 12 | Intl market closes (au, ca, cn, ez, gb, hk, in, jp, kr, tw, rri profiles) | per-market Yahoo collectors (`collectors/hk_prices.py`, etc.) | `data/yahoo/…` and per-market groups · Yahoo rows | As row 2; A13 — no relabelled US probability. | CURRENT_VINTAGE. | local ccy · TRADJ · per market · per-market index/ETF | Not receipted | Internal diagnostic; per-market forward logs (row 15) remain gradeable. | **`source_unavailable`** per market (masterplan W6: per-market clocks/rights/competence are each unresolved). |
| 13 | Security master / vendor aliases (cohort identity) | reference builders | `data/reference/security_master.parquet` (registry :257), `data/reference/vendor_aliases.parquet` (:381) | Registry rows; identity data, not prices. | Reference (versioned on main). | n/a · n/a · multi · identity | n/a | Cohort / ticker identity for every row above. | **`recorded`** (identity only). |
| 14 | US radar forward log | nightly `engine/risk_radar.py` | `data/risk_radar/forward_log.jsonl` (64 rows; first asof 2026-06-23, last 2026-10-09: state caution, `authority_tier advisory`, `confirmed_validated_legs ["credit_oas_roc"]`) | First-party output. | GENUINELY_ISSUED. | state / probability · n/a · US · engine states | Row-per-session; gaps = absent | Grading the engine's own issued states over 2026-06-23 → present. Not a fitting sample. | **`recorded`** (evaluation only). |
| 15 | Leadership-crack + intl forward logs | nightly `engine/leadership_crack.py`, `engine/risk_radar_intl.py` | `data/leadership_crack/forward_log.jsonl` (schema `leadership_crack.v1`, first asof 2026-07-17; `latest.json` asof 2026-10-08 INTACT); `data/risk_radar_intl/<mkt>_forward_log.jsonl` + `_contagion` / `_contagion_quarantine` (+ au `_s1_any95`, `_s3_ret10`, `_s3_ret21`) — 64 files | First-party output; **inputs** are rows 9–12 (`source_unavailable`). | GENUINELY_ISSUED. | states · n/a · US / per market · engine states | Row-per-session | Grading only; the states are derived from `source_unavailable` inputs, so the grades are internal. | **`recorded`** (evaluation only, internal). |
| 16 | Radar probability evidence | `scripts/build_risk_radar_probability_evidence.py` (`evidence_class "reconstructed_historical"` :71) | `data/risk_radar/probability_evidence.json` (h10 `base_rate 0.0823`, `brier_skill_score 0.0709`) | Derived from rows 2–8. | CURRENT_VINTAGE (Yahoo-era "empirical 2006-2026" calibration). | probability · n/a · US · SPY ≥5% pullback | n/a | Internal prior / diagnostic. | **`source_unavailable`** for publication as licensed-history evidence; `recorded` as an internal diagnostic. |
| 17 | S07 OOS baseline (PR #8721 head) | Sol's pullback lane | `research/grey_deer/PULLBACK_OOS_BASELINE_RESULT_2026-10-09.md` at `f28759c8…` (blob `d66f6c61…`); prereg at Macro `d8676764b846…` (blob `d16f06d10d8d…`) | Yahoo `close_price` basis; source hash ≠ main's archive (D2). | CURRENT_VINTAGE; "not an untouched confirmatory holdout"; N 291 train / 104 test / 96 paired (8 abstained); 21-session stride after 63-close warmup; coverage 42.71 % unconditional vs 39.58 % phase-conditioned. | — | — | Diagnostic reference for the primitive's shape; **not** an origin set for the qualified sample. | **`source_unavailable`** as evidence; cited as a read-only anchor. |

---

## 5. Eligible origins — the frozen minimal qualified sample

**Origin rule.** An origin `t` is eligible for a use `U` iff every input the use needs is
`recorded` for `U`, has `available_at ≤ t` under a HISTORICALLY_AVAILABLE receipt, shares market,
basis and units with its outcome series, and passes the §3 clock guards. Anything else is excluded
and the first failing reason is written next to the origin.

**Qualified sample v1.0.0 (internal fitting / evaluation):**

- Input: row 1 only — US SPY Massive RAW closes.
- Window: `coverage.first_day 2021-07-06` → `coverage.last_day 2026-10-07` (store receipt;
  `n_processed_days 1372` across the whole tape; the per-ticker SPY row count is re-measured from
  the store at freeze time with `load_ticker("SPY")` and written into the T22 preregistration with
  its sha256 — it is **not** asserted here).
- Outcome series: the same row (same basis, same market, same units) — the formula in masterplan
  §6.2, `total_episode_depth(A) = max(1 − trough/peak, 1 − (current/peak) × (1 − A))`, is evaluated
  on RAW closes and refused on any split-like discontinuity (D5).
- Episodes reachable inside the window: the 2022 drawdown and the 2023 banking stress only; the
  masterplan's 1998–2020 proposals are **excluded origins** (no licensed historically-available
  row; D1). This is a small, autocorrelated sample and is recorded as such — honest-N is counted in
  episodes, not sessions, at preregistration.
- Floor is rolling: a successor re-reads `EARLIEST_ENTITLED` and the store receipt before
  re-using this window; a later floor shrinks the sample and is never back-filled from a
  CURRENT_VINTAGE source.

**Excluded origins (named):** every pre-2021-07-06 date (D1); S07's 96 paired origins (Yahoo basis,
D2); any origin whose outcome would be read from a TRADJ series (D5); every non-US market origin
(rows 10–12); any origin requiring breadth, COR1M, intl ETF or basket inputs (rows 6–9).

**Legal zero vs absent inside the sample:** a session with a printed close of any value is data;
a session absent from the store is `absent` and is logged in the prereg's missingness block;
`max_missing_run_weekdays 0` is the current measured value and is re-measured at freeze.

---

## 6. Acceptance mapping (A03 / A04) and stop conditions

| Case | What this manifest supplies | What remains to execute | Status |
|---|---|---|---|
| A03 purpose-specific rights | Row 1 disposition by pointer to the recorded determinations (D4); every other input `source_unavailable` with reason. | The dependent fitting must read only `recorded` rows for its declared use and refuse otherwise; user-facing publication additionally needs the feed designation (register :20). | Determination RECORDED here; case executes at T22 / primitive. |
| A04 historical availability | Row 1 store receipt (first/last day, missing runs) and the rolling floor (D1); §5 origin rule. | Prereg freezes the measured SPY row count + sha256 before any outcome inspection (T22); the primitive enforces the §3 clock guards. | Determination RECORDED here; case executes at T22 / primitive. |

**Stop conditions honoured:** missing rights or history blocks only the dependent fitting /
publication of that input; no Yahoo production fallback is introduced (rows 2, 3, 11, 12 stay
diagnostic); no historical membership is fabricated (row 9). The measured-only lanes W1–W3 are not
blocked by any `source_unavailable` here (masterplan W4).

---

## 7. Contract for the observed-move primitive (what it must refuse)

Not code — the list the primitive's tests are written from, after T22:

1. Refuse any input whose manifest row is `source_unavailable` for the declared use.
2. Refuse an origin before `coverage.first_day` or after `latest_date`; refuse non-session dates.
3. Refuse an outcome series whose basis, market or units differ from the origin's row.
4. Refuse on `price_basis_discontinuity` (S08 guard) rather than re-adjusting.
5. Record `absent` sessions; never fill; never treat a printed zero as absent.
6. Emit the manifest version it was evaluated against (`1.0.0`) in every result artifact.

---

## 8. Open determinations routed to their owners (recorded, not assumed)

| Id | Gap | Owner | What closes it |
|---|---|---|---|
| G1 | `equity.bars.daily.massive` registry row has no `licensing:` field (registry :134-152). | dataset-registry owner | Add the field pointing at the entitlement record (by pointer, no terms). |
| G2 | Massive user-facing feed designation for derived pullback probabilities (register :20). | Chairman / entitlement holder | Feed-specific written designation recorded in `research/licenses/`. |
| G3 | CN rights determination + `510300.SS` labelling (handoff O-d). | data-source owner | A CN row in the register; the DNR kill stays. |
| G4 | COR1M / CBOE terms (row 7). | data-source owner | A determination recorded in the register; registry row for `data/cboe/`. |
| G5 | `intl_etf`, `breadth`, `baskets/ohlcv` registry rows (rows 6, 8, 9). | dataset-registry owner | Registry rows with producer, basis and rights. |
| G6 | FRED model-use determination (register :100). | rights owner | DETERMINED-FROM-PUBLISHED-TERMS row for model use. |

None of G1–G6 blocks the qualified sample in §5; each blocks exactly the row it names.

---

## 9. Versioning, anchors and DO_NOT_REDO

- **Version `1.0.0`** — first manifest. Bump the minor version when a row's disposition changes,
  the major version when the origin rule or an evidence class changes; every result artifact names
  the version it used.
- **Pinned anchors** (read-only; see `SOURCES.md` in the Chairman-delivered handoff): S02 WS record
  at `50a7771721618e373eeb6e91b92c5f07860ee9f4`; S03 Alertful masterplan at
  `8473e82a67c90823e8912a7bdf7219464246d11c` (line 166: "Existing historical reconstruction without
  true vintages is diagnostic, not authority-grade."; A3 fail-closed inputs; A13; A14 retention
  expiry; §6.1 denominator / corporate-action conventions); S07 / S08 / S09 / S10 at
  `f28759c84e2e1d8be0d96706861f69418bff9ceb` (blobs `d66f6c61…`, `5a5ce7ba…`, `bf3081ee…`,
  `30453c88…`).
- **Massive store receipt** read 2026-10-11 from `origin/main:data/massive_stock_day/_manifest.json`
  (top-level keys `store`, `n_tickers`, `latest_date`, `updated_at`, `coverage`, `anchor`).
- **DO_NOT_REDO:** no prior manifest exists for this operation (`agentos/` `do_not_redo` and
  `research/DO_NOT_REBUILD.md` checked; the only binding kill is `DNR:KILL-CN-ADJUSTED-TAPE-LEGAL-LIMIT`,
  honoured in row 10). GD-1C's "PIT membership unreconstructable" finding is honoured in row 9.
- **What this manifest is not:** not a source store, not a rights grant, not a ratification of the
  Prophet US register outside the pullback scope, not a change to any live producer, and not a
  fitting result.
