# Q05 PREREG AMENDMENT 1: independent-audit fixes

Status: amendment to the frozen `PREREG.md`. `PREREG.md` itself is NOT edited.

- It stays at sha256 `f628aa875a95a22972142f26f6891d698c4397c705268ccbaecb7ee668d7e78c`, the value in `FREEZE.log`.
- This file is hashed into `FREEZE.log` as its own line.
- `evaluate.py` refuses to run unless both hashes match.

**Why.** An independent audit of the Q05 staging returned PASS_WITH_FIXES (blockers 0, majors 4, minors 7). Four of its findings show that the reference module departs from the OA-3 incumbent, which PREREG §7 says must be reproduced exactly, or from PREREG §9 and §11, which the classifier and the code did not implement. This amendment records each rule change and its reason.

**When.** It was written before any new outcome was read. No outcome exists yet: the only run before this amendment (RUNS.log, run 1) produced availability counts and verdict INSUFFICIENT_DATA. Every option outcome row in the vintage reads `unavailable / no_executable_nbbo_quote_path`, and no return value has ever been read.

**What does not change:**

- the frozen 90-scenario grid
- the decision scenario
- the bootstrap settings
- the stop rule
- the trial family

## A1. Session-close rule (resolves a conflict between PREREG §3 and §7)

PREREG §3 says an exit window outside the session is `unavailable / exit_outside_session`. PREREG §7 says the baseline must reproduce OA-3 exactly. OA-3 (Ruling D in `engine/options_alpha_exact_option_outcome.py`) instead **excludes** these cases, before any quote parsing for the entry checks and after entry selection for the exit checks:

| OA-3 condition | OA-3 result |
|---|---|
| `available_at` outside `[rth_open, rth_close)` | EXCLUDED `ENTRY_BOUNDARY_OUTSIDE_RTH` |
| `available_at + 60 s >= rth_close` | EXCLUDED `HORIZON_CROSSES_SESSION_CLOSE` |
| `exit_window_end = entry_event + 3600 s + 60 s >= rth_close` (equality also excluded) | EXCLUDED `HORIZON_CROSSES_SESSION_CLOSE` |
| exit target outside `[rth_open, rth_close)` | EXCLUDED `EXIT_BOUNDARY_OUTSIDE_RTH` |

§7 governs. The amended rule is:

- **Latency 0** (the baseline and every other latency-0 cell, since size, fee and slippage cannot move a session boundary): every condition above applies verbatim, with status `excluded`.
  - The two entry checks are properties of the episode alone, so they exclude the episode from every scenario.
- **Latency > 0:** a scenario whose delayed entry window (`boundary + latency + 60 s >= close`) or delayed exit window (`exit_window_end >= close`) reaches the close is `unavailable`, with reason `entry_outside_session` or `exit_outside_session`. The scenario caused the loss, so the episode counts in population loss (§12 attrition) instead of leaving the denominator.
- **Boundary equality** counts as crossing in both cases, as in OA-3.

## A2. Quote validity mirrors the OA-3 cohort parser (`engine/options_nbbo_cohort.parse_quote_response`)

PREREG §3 says "not crossed, firm condition, known exchange". That phrase is replaced by the incumbent's exact rules.

**Skipped quotes.** A quote is skipped when any of these holds:

- it is outside RTH;
- a price is negative;
- it is crossed, which means `bid > 0 and ask > 0 and ask < bid`;
  - one-sided quotes such as `ask = 0` with `bid > 0` are therefore NOT crossed;
  - an `ask = 0` quote is a valid exit (bid-side) quote.

**Per-side validity.** Validity is checked only on the traded side:

- entry: `ask > 0`, `ask_size > 0`, `ask_condition` in the firm OPRA set, `ask_exchange` in the known Theta set;
- exit: the same four checks on the bid side.

The two sets are transcribed verbatim:

- firm: `{0,1,3,4,5,7,8,12,13,14,15,16,42,48,49,50,51,52,53,54,56}`
- known: `1..77` minus `{74, 76}`

**Unavailable legs.** Two cases make the leg `unavailable` with reason `<leg>_quote_response_invalid`, matching OA-3's `QUOTE_RESPONSE_INVALID`:

- Two valid candidates in the window share a timestamp but differ.
- A size, exchange or condition field is malformed, meaning not a non-negative integer.

**Selection.** The earliest valid candidate is selected. The scenario's displayed-size requirement is then applied to that quote only. This rule is unchanged: a later quote is never searched for size.

## A3. Practical-effect bar and decision floor enter the frozen classifier (PREREG §9, §13, §15)

The classifier computed the decision CI on survivors only. It did not apply §9, and it did not apply the block and episode floor to the decision scenario.

**Inputs.** The amended `classify` takes four inputs:

- the baseline CI;
- the decision-scenario CI;
- the paired-delta CI, which is the session-cluster bootstrap of decision minus baseline over episodes complete under both;
- the decision `population_loss`.

**Rules,** evaluated in this order:

1. **`insufficient_data`:** the baseline holdout has fewer than 20 session blocks or fewer than 60 episodes (§13, unchanged).
2. **`no_benefit_under_ruler`:** the baseline CI lower bound is ≤ 0, or missing.
3. **`execution_fragile`** if ANY of these holds:
   - (a) the decision CI lower bound is ≤ 0, or missing (§6 H2);
   - (b) the paired mean delta is ≤ −1.0 percentage point (§9);
   - (c) the decision population-loss fraction is ≥ 0.10 (§9);
   - (d) the decision scenario leaves fewer than 20 session blocks or fewer than 60 episodes (the §13 floor applied to the decision CI). A benefit that cannot be shown at the preregistered floor once execution is made harder is not robust.
4. **`execution_robust`:** otherwise.

Verdict mapping (§15) is unchanged.

## A4. Acquisition and retrieval clocks (PREREG §4b)

- `Quote` carries an optional `acquired_t`. A quote acquired before its own event time is malformed (`<leg>_quote_response_invalid`).
- `Episode` carries optional per-leg retrieval clocks (`entry_retrieved_t`, `exit_retrieved_t`) and an optional `vintage` label.
- A scenario window that ends after its leg's retrieval clock is `pending` (`<leg>_window_not_matured_at_retrieval`), mirroring OA-3 Ruling C. A pending leg is not complete, so it counts as population loss.
- A quote acquired after its leg's retrieval clock is malformed.

## A5. Latency horizon shift and ruler-layer label (made explicit)

PREREG §3 and §14 already fix the exit target at the selected scenario entry's event time + 3600 s + latency. That rule stands: latency delays both the entry arrival and the exit arrival. It is now stated in VERDICT.md and REQUIREMENTS.md.

The `ruler` layer is labelled with the OA-3 policy id only at latency 0, where it equals the OA-3 outcome. At latency > 0 it is labelled `oa3_cost_formula_on_delayed_scenario_quotes`, because the quotes are no longer the OA-3 quotes.

## A6. Break-even, chronological split, and evaluator mechanics

**Break-even.** `break_even_extra_cost_usd` returns two things:

- the per-episode distribution of `net_pnl_usd / 2`, the extra symmetric per-side cost that zeroes that episode;
- its session-cluster bootstrap CI, with the §12 settings (2,000 replicates, seed 5051, 95%).

**Chronological split** (PREREG §11). The rule is implemented as `chronological_session_split`:

- unique session keys are sorted;
- the first `floor(3n/5)` sessions are training and the rest are holdout;
- no session spans both;
- the holdout is never below 40%.

**`evaluate.py` changes:**

- It verifies this amendment's hash.
- The census also decompresses and scans `.gz` text files, and scans `.txt`.
- It lists the counts of every extension it skipped.
- It runs a live parity check: the module's quote selection against the incumbent `parse_quote_response` on synthetic Theta-shaped rows. The session date and contract expiry are derived from the data vintage; no market values are read.
- If any eligible candidate input exists, it returns the distinct verdict `NOT_IMPLEMENTED` with `manual_review_required = true`, instead of a silent INSUFFICIENT_DATA. Eligible candidate inputs are: an OA-3 policy hit, a quote-endpoint hit, or a ledger row that is complete with a quote basis. The episode ingest adapter is not built.
