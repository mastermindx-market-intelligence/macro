# Rotation Core — Phase 2 plan (D4)

Phase 2 executes `protocol_header_v1.json` (sha256 `af2a0988…0f32`, commit `623f0a4623`). It does nothing the header
does not name. Nothing in it starts until the parent rules on §4.

## 1. Harness design (reuse first)

**New code.** `engine/rotation_core_evaluation.py` (pure functions), runner `scripts/run_rotation_core_v1.py` and
`tests/test_rotation_core_evaluation.py`. All on branch `fable/rotation-core-20261110`.

**Reused from the beta-first harness.** That harness is on branch `fable/prophet-beta-evaluation-20261110`, which is
unmerged, so these functions are ported with attribution: `verify_header`, `stationary_bootstrap_indices`, `holm`,
`capture`, `max_drawdown`, `beta_ols`, `point_metrics`. `simulate_book` is generalised to daily target weights, t+1
execution, per-side costs, cash accrual and drifted weights.

**From main.** `engine.validation` provides deflated Sharpe, called with `ledger=` per `epistemics.no_literal_ntrials`.
`engine.trial_ledger` provides the ledger. `engine.equity_alloc` and `engine.sector_signals` are used only for the
incumbent replays.

**Patterns from the sister team's lane 8 (PR #10924).** These are reused as patterns, not imports: the comparator
accounting (no-entry and no-fill counts, exposure-matched reference), year-block reporting, and `confirmed_at`
discipline.

**Pipeline:**
1. **Load.** Read the vendor cache and repo blobs into aligned panels. Every input's sha256 goes into the artifact.
2. **Signals.** Compute T, C, M, MTF, RS63, VEL, R12-1, R126 exactly as the JSON defines them.
3. **Books.** Run 36 configurations, each one continuous simulation.
4. **Metrics.** Compute the contrasts (F1–F5, FI), bootstrap, Holm and DSR.
5. **Pivots.** Compute episode and pivot tables.
6. **J4.** Run the cross-sectional module (statistical sector assignment, quintile selection, three bias treatments, coverage table).
7. **Write.** Produce `results_stage_D.json` and `RESULTS_STAGE_D.md`.

**Stage gate.** `--stage H` refuses to run unless `results_stage_D.json` is committed (git-tracked, clean). H statistics
are never computed in stage D.

**Tests** (synthetic, red → green):
- **No look-ahead:** perturbing data after t never changes decisions at or before t, checked for every signal.
- **Header guard:** a hash mismatch refuses to run.
- **Stage guard:** H output is blocked in stage D.
- **Cost accounting identity.**
- **Exposure-matched reference.**
- **Holm and p-value conventions.**
- **Pivot metrics** on a hand-built path.
- **J4 assignment** uses only prices up to t.

## 2. Worker split

The principal keeps the harness core, the review of every signal definition against the JSON, and adjudication. The
fan-out uses Fabric workers, each with a narrow brief, no repo pushes and no child agents.

| Worker | Model | Scope | Output |
|---|---|---|---|
| P2-W1 | GLM 5.3 high | Incumbent replays at the data pin. spvector daily glide weight 1993+, needing sparse-checkout of the repo stores it reads (`data/fred`, `data/regime`, `data/macro`…). Risk Radar v2 gross 2007+, or a precise `unavailable` reason. `sector_signals` daily states per SPDR. | Parquet weight and state series plus provenance, in scratch |
| P2-W2 | Deepseek V4.1 Flash (high) | J4 data repair. Re-run the `scripts/residual_alpha_pit.py` best-effort delisted fetch (Yahoo) into scratch for every S&P 500 PIT member since 1996. Produce a priced-coverage table by formation month. | `data/j4_prices/`, coverage CSV |
| P2-W3 | GLM 5.3 high | Descriptive tiers: French 12-industry and ^GSPC long-history panels; J3 proxy tier panels. Panels only, no strategy results. | Aligned panels |
| P2-W4 | Separate-context reviewer (GLM 5.3 high or Opus) | Read-only look-ahead and conformance review of the harness diff against the JSON **before Stage D runs**. Findings are returned and adjudicated by the principal. | Review findings |

**Runtime.**
- **Compute is small.** 36 books × ≤ 7,300 sessions; 38 tests × 10,000 bootstrap draws × ~5,500 days, vectorised; J4 ≈ 300 months × ~500 regressions. Under 30 minutes in total.
- **Engineering:** about 1 day of principal work for the harness and tests.
- **Workers:** P2-W1 to P2-W3 run in parallel for ~2–4 hours. The P2-W4 review takes ~1 hour.
- **Staging:** Stage D, then commit, then Stage H, then commit. **Expected wall clock is 1.5–2 days to a Stage-H result.**

## 3. Honest prior

| Job | Prior on L1 | Why |
|---|---|---|
| J1 | ~10–15 % | Every trend or credit rule cuts drawdown. Clearing +1 pp/yr **timing return over an exposure-matched mix** after Holm is rare; the sister team's SPY > 200 d was −2.73 %/yr vs SPY over 2008–26. Confluence (J1-B) and crisis-only (J1-E) are the likeliest to pass the risk tests (G6) without a large CAGR cost. |
| J2 | ≤ 5 % | Sector-ETF momentum IC ≈ 0 over 27.9 years; cycle-state allocation is negative; stock-level velocity is anti-predictive. The 11 SPDRs are highly correlated and low-breadth. |
| J3 | ~10 % | Cross-asset momentum has the best literature support, but the repo TSMOM ≈ buy-and-hold, and the exposure-matched +1 pp hurdle is strict. |
| J4 | L0 cap (≈ 30 % chance the point estimate is even positive) | Coverage is below 85 %; survivorship bias runs in an unknown direction across the arms. |
| J5 | < 5 % | H-only, about 6.8 years, three episodes. |

**Most likely result:** drawdown control at a measurable return cost, and no rotation skill distinguishable from the
baselines. That is still decision-useful: it shows where the edge is not.

## 4. Decisions needed from the parent

1. **J4 delisted prices.** Authorise use of a licensed vendor credential (Massive/Polygon or Tiingo) for delisted
   S&P 500 / 1500 daily prices, if one exists for this purpose? Without it, J4 historical stays L0 and the prospective
   shadow is its only test. *Default: no credential; Yahoo best-effort only.*
2. **FRED content.** IMCE landmine (q) says "no store/cache/archive of FRED content in any database". DTB3,
   `SAHMREALTIME` and BAA are cached in scratch only and never committed. Acceptable, or should the repo stores / ^IRX
   be used exclusively? *Default: scratch cache, with repo stores where they exist (HY OAS, DBAA).*
3. **Hold-out opening.** Open Stage H automatically once Stage D is committed, or only after you adjudicate the Stage D
   results? *Default: automatic, because the candidates are locked by the header.*
4. **Prospective shadow (L2).** WS:GREY-DEER forbids a new risk-episode ledger; risk episodes belong to
   Chronicle / Reflex Registry / QLedger. Which owner should hold a nightly J1/J2/J3 shadow if anything reaches L1, and
   should J4's prospective formations begin accruing now (S&P 1500, near-complete coverage)? *Default: no writer in
   Phase 2; propose one in Phase 3.*
5. **Incumbent replays.** Accept the L0 cap for spvector, Risk Radar, `sector_signals` and TSMOM. Also accept that
   Risk Radar may be recorded "unavailable" if its replay cannot run from the repo stores.
6. **Overlap with the Leadership-Rotation programme.** WS:LEADERSHIP-ROTATION-INTELLIGENCE has LR-W6 (PREREG V3)
   pending. J2 is a different ETF-level construction. Confirm Rotation Core is not duplicating it, or name the owner to
   coordinate with.
7. **Publication.** Phase 1 is committed locally only (`623f0a4623`); no push or PR, per the brief. Say when to
   publish the header and census PR to Macro. The trial-ledger row is only durable for the organisation once merged.
