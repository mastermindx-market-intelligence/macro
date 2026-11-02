# Q05 PREREG — option outcome sensitivity to latency, available size and execution cost

Status: preregistered research reference. Nothing here is wired, scheduled, promoted or gating.
Reference module: `engine/options_execution_sensitivity.py` (pure functions, `RESEARCH_ONLY = True`).
Evaluator: `evaluate.py` in this directory. It refuses to run unless sha256(PREREG.md) equals the hash in `FREEZE.log`.

## 1. Question

Does the measured outcome of an OA-3 exact-contract long single-leg option expression keep its sign and size when execution is made less favourable in shared, frozen ways? The three ways are later arrival (latency), a minimum displayed size on the traded side, and higher per-side cost or slippage. The quote ruler stays fixed: entry at the ask, exit at the bid. Or does any apparent benefit rely on the baseline fill convention, which makes it execution-fragile?

## 2. Non-duplication

Incumbents found by grepping `_base/` at d252f919 (the read-only snapshot):

- `engine/options_alpha_exact_option_outcome.py`: the OA-3 evaluator. Its policy `oa3.long_single_leg_h60_nbbo/v1` is in state `preregistered_inactive`, with frozen policy sha256 `00b9eb94a97233215dff416975e42a8705cb4fc3c9a3524f9168ee66645098bf`. It sets the fill rules (ask entry, bid exit, 60 s entry window, exit at +60 min with a 60 s window, 1 contract, multiplier 100, USD 0.65 per side, min displayed contracts 1, same NYSE RTH session) and makes no executable-fill claim.
- `engine/options_nbbo_cohort.py`: the OPRA NBBO quote parser (`parse_quote_response`, first valid firm/known-exchange quote at or after the boundary) and the `net_return_pct` ruler.
- `engine/options_focused_quote.py`: vendor bid/ask snapshot with no size, venue or condition. It cannot support an executable-quote claim.
- `engine/options_flow.py` and the flow ledger (`data/flow_signals/ledger.parquet`): print-level flow detection with aggregate NBBO microstructure medians.
- `engine/options_signal_episode.py` and `engine/options_signal_campaign.py`: the episode and campaign outcome ledgers.
- `engine/options_payoff*.py`, `options_structure*.py` and `options_scenario_surface.py`: payoff and structure tools, unrelated to fill sensitivity.

Collision check: grepping `_base/engine`, `_base/tests`, `_base/scripts` and `_base/research` for `execution_sensitivity|latency_sensitivity|option_execution|fill_latency|execution_fragile|execution-fragile` matched only `research/winners/cases/NVDA_2015.md`, a narrative case file. `engine/options_execution_sensitivity.py` and `tests/test_options_execution_sensitivity.py` do not exist in `_base`.

The narrow relation I stay inside: this work is a downstream sensitivity layer on the OA-3 ruler only. It consumes OA-3-shaped episodes and the raw quote paths they cite. It re-evaluates those episodes under shared frozen scenarios and keeps gross, ruler, scenario and actual-fill layers separate.

EXCLUSIONS. This work is NOT:

- a package or flow detector;
- a broker or execution integration;
- a new outcome ledger;
- a revised OA-3 definition (the OA-3 ruler, windows and forbidden substitutes are reused unchanged);
- a signal, score or gate.

Packages, 0DTE and short options are excluded. Charm, DOI and skew nulls stay negative evidence and are not revisited. DNR keys respected: KILL-OUTCOME-AUDITION (the grid is frozen here, never chosen by outcome), KILL-LLM-ORIGINATION, KILL-FUSED-COMPOSITE, KILL-POSITIONING-FUSION, KILL-REGIME-SCORECARD, KILL-COMPOSITE-REGIME-RELIABILITY-MONITOR, KILL-CAUSAL-DAG-ALPHA, HOLD-PSS-AF1-FINRA, HOLD-PSS-CD1-CROWDING.

## 3. Estimand, unit and clocks

- **Unit:** one OA-3-eligible expression episode, meaning one exact contract, long, single leg, 1 contract per baseline.
- **Estimand:**
  1. Holdout mean OA-3 ruler net return in percent under the baseline scenario.
  2. The same quantity under the designated decision scenario, together with the paired per-episode change (scenario minus baseline) on episodes complete under both.
  3. Population loss: the fraction of baseline-complete episodes that become unavailable under each scenario.
- **Input clock:** `expression.available_at` is the boundary. Scenario arrival = boundary + latency. Only quotes with event time ≥ arrival are eligible.
- **Output clock:** the exit target is the selected entry quote's event time + 3600 s + latency, with a 60 s window. The exit must lie in the same NYSE RTH session, otherwise the leg is `unavailable / exit_outside_session`.
- **Fill selection:** the first base-valid quote in the window decides the leg. Base-valid means in session, not crossed, firm condition, known exchange, and price > 0 and size > 0 on the traded side. If that quote's displayed size is below the scenario requirement, the leg is `unavailable / insufficient_displayed_size`. The selector never searches later quotes, a neighbouring contract, the mid, the last print, the EOD mark, intrinsic value or a model price.

## 4. Cohort and eligible data

An episode is eligible only when BOTH of these hold:

- (a) a retained record bound to policy `oa3.long_single_leg_h60_nbbo/v1` has status `complete`;
- (b) the retained raw exact-contract OPRA NBBO tick path (Theta `/v3/option/history/quote`: bid, ask, bid_size, ask_size, condition, exchange, and acquisition clocks) covers its entry window and, for every latency in the grid, its exit window.

A record with only option outcome statuses `unavailable / no_executable_nbbo_quote_path` is ineligible. Print-level aggregate NBBO medians (flow ledger) are ineligible, because they give no per-contract quote path and no exit-window quotes. Vendor snapshot quotes without sizes are also ineligible.

## 5. Source vintages (sha256; data vintage cdab6268, read-only)

| input | sha256 |
|---|---|
| data/options_signal_episode/outcomes_h60.jsonl | 617039e5e1a45f9e9a70682060e156b8e778a49c58a85d0a96bd89f8f4c69fa4 |
| data/options_signal_episode/outcomes_session.jsonl | fc02c3f6d224ada2179f89fcf09d63866567e4132d6d6738ccc90c012c9b6311 |
| data/options_signal_campaign/outcomes.jsonl | bfde356d4e54265164840e46f06e391afbed3c35449cda4786013eb95f432160 |
| data/flow_signals/ledger.parquet | c14b99cf92c29467d40a823a42e1b8974f018233c76b70d917b403f7a3898b62 |

`evaluate.py` hashes every other file its census touches and records the hashes in `results/census.json`.

Mastermind procedure docs, read-only, commit unknown:

- `INDEX.md`: 608aebc84a106f4e3c687f020a7f0e69af88f38e014d4664a376e2be2ddfa220
- `ACTIVE_EXECUTION.md`: fb6a89101ad75512b971b2457f3f419704eae136afa28bac5a646ae69a6ed0dc
- `SESSION_RELIABILITY.md`: 817366c630abe31308a09c18caa5249ea4c39c83d74c130496079bb151283076

Pre-freeze disclosure: before this freeze I ran eligibility probes. They read status and reason counts only, never returns, because no returns exist. Every option outcome row in the three ledgers above is `unavailable / no_executable_nbbo_quote_path` (25,338, 30,327 and 28,423 rows). A schema walk found only one file with bid/ask size columns: the flow ledger, which has aggregate medians on 16,052 of 92,574 rows across 7 sessions. No value from these probes is used for tuning. The grid below was fixed from the OA-3 policy alone.

## 6. Hypotheses

- **H0:** the holdout baseline mean ruler net return has a session-block CI that is not above 0 (no benefit under the ruler).
- **H1 (execution-robust):** both the baseline CI and the decision-scenario CI have lower bound > 0.
- **H2 (execution-fragile):** the baseline CI lower bound is > 0, but the decision-scenario CI lower bound is ≤ 0.

## 7. Baseline and competitors

- **Baseline:** the OA-3 ruler exactly, meaning latency 0, min displayed 1, fee 0.65 per side, slippage 0. Before any sensitivity term, the module's `ruler_net_return_pct` must equal `engine.options_nbbo_cohort.net_return_pct` bit-for-bit on a fixed price grid (req1). The baseline population is the set of OA-3 `complete` episodes; their recorded `net_return_pct` must be reproduced exactly from the retained quotes.
- **Competitors:** the full frozen grid below. A descriptive `gross` mid-to-mid layer is reported only as context and is never a fill or a competitor for the decision.

## 8. Frozen scenario grid (shared by every name; never selected per name or by outcome)

- latency_s ∈ {0, 1, 5, 15, 30}
- min_displayed_contracts ∈ {1, 5, 10}
- fee_per_side_usd ∈ {0.65, 1.30}
- slippage_per_share_usd ∈ {0, 0.01, 0.05}, applied adversely to both legs

That gives 90 scenarios. **Decision scenario (designated in advance):** latency 5 s, min displayed 1, fee 0.65, slippage 0.01. The other 89 are descriptive.

## 9. Practical effect bar

A sensitivity is material if the decision scenario lowers the paired mean ruler net return by ≥ 1.0 percentage point per trade, or if it makes ≥ 10% of baseline-complete episodes untradable.

## 10. Trial family

- One comparison: baseline versus the designated decision scenario on the holdout.
- One family of 90 scenarios, all reported, none selected.
- No repeated holdout search; the holdout is evaluated once.

## 11. Chronological split and preprocessing

- Order sessions by their session key and assign whole sessions.
- First 60% of sessions: training. Last 40%: holdout. No session spans both.
- The only preprocessing is validation and exclusion (packages, 0DTE, short), all rule-based and identical in both partitions. No parameter is fitted. If any preprocessing threshold were ever needed, it would be estimated on training only.

## 12. Uncertainty (dependence-aware)

- Session-cluster block bootstrap: resample whole sessions with replacement, 2,000 replicates, fixed seed 5051, 95% percentile CI.
- Honest N is the number of distinct sessions (blocks) and episodes, never rows.
- Attrition and support are reported per scenario: baseline-complete, scenario-complete, became-untradable, and reason counts.

## 13. Falsifier and stop rule

- **Falsifier:** if any benefit depends on a favourable fill convention, classify the candidate execution-fragile. This covers a benefit that exists only in the `gross` layer, only at latency 0, or only at size 1 with zero slippage. The quote ruler is never relaxed to rescue it.
- **Stop rule:** if the holdout has fewer than 20 session blocks or fewer than 60 eligible episodes, compute no comparison and give the verdict `INSUFFICIENT_DATA`, naming the exact missing input.
  - Zero eligible episodes stops the evaluation immediately after the census and the req1 ruler cross-check.

## 14. Outcome windows

- Entry: [arrival, arrival + 60 s].
- Exit: [entry_t + 3600 s + latency, that time + 60 s], within the same RTH session.

## 15. Verdict mapping

- `execution_robust` → KEEP (research reference only, still not wired).
- `execution_fragile` or `no_benefit_under_ruler` → REJECT.
- `insufficient_data` → INSUFFICIENT_DATA.
