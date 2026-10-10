# Q05 VERDICT — INSUFFICIENT_DATA

**Question.** Is the OA-3 exact-contract option outcome sensitive to latency, displayed size and execution cost when the quote ruler stays fixed?

**Verdict: INSUFFICIENT_DATA.** No empirical comparison was computed. This is the result the preregistered stop rule requires (PREREG §13). The rules in force are `PREREG.md` plus `PREREG_AMENDMENT.md` (amendment 1, independent-audit fixes), both hash-frozen in `FREEZE.log`.

## Exact missing input

The comparison needs retained exact-contract OPRA NBBO tick quotes from Theta `/v3/option/history/quote`. Each quote must carry:

- bid, ask, bid_size and ask_size
- condition and exchange
- acquisition clocks

The quotes must cover the OA-3 entry window (60 s from `expression.available_at`) and the exit window (+60 min, 60 s wide). They must also be bound to `complete` expression receipts under `oa3.long_single_leg_h60_nbbo/v1`.

None of this exists locally. The OA-3 policy is `preregistered_inactive`, so no receipt has been produced. No raw quote path has been retained either.

## Evidence

Source: `evaluate.py`, run 2, exit 0, logged in `RUNS.log`. This was the single re-run after the audit fixes. Run 1 came before the amendment and gave the same verdict.

The census covered the read-only data vintage at cdab6268 (`/Users/chriswong/Documents/Cluade/macro-main/data`):

- 64,714 files scanned (text and parquet).
- 2,210,000,829 bytes of json, jsonl, ndjson, csv and txt searched in full. This includes 16 `.gz` text files, decompressed and streamed (41,355,764 bytes after decompression).
- Skipped extensions, with counts:
  - `.svg` 2,453
  - `.png` 2,010
  - `.pdf` 1,744
  - `.fired` 572
  - `.md` 107
  - `.html` 26
  - no extension 20
  - `.xlsx` 12
  - `.yml` 8
  - `.lock` 2
  - `.xls` 2
  - `.1` 1
  - `.version` 1
- No scanned text file contains any of: `oa3.long_single_leg_h60_nbbo/v1`, `oa3_exact_option_outcome`, `/v3/option/history/quote`, `nbboobs_`, `bid_size` or `ask_size`.
- Eligible candidate inputs: 0 OA-3 policy files, 0 quote-endpoint files, and 0 ledger rows that are complete with a quote basis. The amendment A6 `NOT_IMPLEMENTED` branch was therefore not triggered.

Option outcome ledgers. Every row is `unavailable / no_executable_nbbo_quote_path`, and none has a quote basis.

| Ledger | Rows | sha256 |
|---|---|---|
| `options_signal_episode/outcomes_h60.jsonl` | 25,338 | `617039e5…` |
| `options_signal_episode/outcomes_session.jsonl` | 30,327 | `fc02c3f6…` |
| `options_signal_campaign/outcomes.jsonl` | 28,423 | `bfde356d…` |

Parquet. Only one file has bid/ask size columns: `flow_signals/ledger.parquet` (sha256 `c14b99cf…`).

- It holds `options.trade_nbbo_microstructure/v1` print-level medians.
- 16,052 of its 92,574 rows have size medians, across 7 sessions. The latest session is 2026-09-25.
- It has no exchange or condition column, no per-contract quote path and no exit-window quotes.
- It is therefore **ineligible**. It was not used as a proxy, because using it would relax the quote ruler.

Eligible counts:

- 0 OA-3 episodes and 0 session blocks.
- The stop rule needs at least 20 holdout session blocks and at least 60 episodes.

Baseline reproduction:

- The baseline OA-3 return population is empty locally. That absence is proven by the census above.
- Formula-level req1 holds: the module's `ruler_net_return_pct` equals `engine.options_nbbo_cohort.net_return_pct` bit-for-bit on all 182 price pairs (0 mismatches). The cohort fee is 0.65 per side.
- Live selection parity: the module's `select_quote` was compared with the incumbent `engine.options_nbbo_cohort.parse_quote_response` on 18 synthetic Theta-shaped cases, with 0 mismatches.
  - The incumbent received exact 13-field rows for a canonical SPY call.
  - The session window is the incumbent's own `_session_window` for the vintage's latest session.
  - The cases cover:
    - crossed-then-valid
    - an ask = 0 exit and a bid = 0 entry (valid)
    - a bid = 0 exit (invalid)
    - exchange 74 and condition 2 on the traded side and on the untraded side
    - conflicting and identical duplicates
    - a malformed size
    - a malformed condition on a crossed row
    - a pre-arrival quote
    - a quote near the close and a quote after the close

Freeze integrity:

- PREREG.md sha256 is `f628aa875a95a22972142f26f6891d698c4397c705268ccbaecb7ee668d7e78c`, frozen at 2026-10-09T09:33:16Z.
- PREREG_AMENDMENT.md sha256 is `8c320a3e20ad1f058b5ee1fb9ce36c9433c3760cdf2c6842d740f86075ffaef6`, frozen at 2026-10-09T09:52:35Z. It was written before run 2 and before any outcome was read; none exists.
- `evaluate.py` refuses (exit 3) unless both hashes match.
- A tampered PREREG copy in staging scratch was refused with exit 3.

Outputs:

| File | sha256 |
|---|---|
| `results/census.json` | `71ecdd445f8bfbb1f9c82c4ea113ab6b5ed21d9fa652375fc2f6bfc8976fe623` |
| `results/evaluation.json` | `8ea79e62e2f310ed0e8f536eb247ee5aaced537bf4c000bf8be884a5c2804e65` |

## Latency horizon shift (amendment A5)

Latency delays **both** legs:

- The scenario entry arrival is `boundary + latency`.
- The exit target is `selected scenario entry event time + 3600 s + latency`.

The holding horizon of a delayed scenario is therefore measured from a later entry, and its exit is a further `latency` seconds late. The `ruler` layer carries the OA-3 policy id only at latency 0, where it is the OA-3 outcome. At latency > 0 it is labelled `oa3_cost_formula_on_delayed_scenario_quotes`, because those are no longer OA-3's quotes.

## What is delivered

`engine/options_execution_sensitivity.py` is a pure, frozen research reference. It is NOT wired. It specifies how the comparison must be computed once the missing input exists:

- **Session close (OA-3 Ruling D, amendment A1).**
  - At latency 0, an entry boundary outside RTH, `boundary + 60 s >= close`, `exit_window_end >= close` (equality included) and an exit target outside RTH are all `excluded`, exactly as OA-3 does it.
  - At latency > 0, a delayed window that reaches the close is `unavailable` and counts as population loss.
- **Quote validity mirrors the cohort parser (amendment A2).**
  - Crossed means `bid > 0 and ask > 0 and ask < bid`.
  - Validity is checked per traded side: price, size, firm OPRA condition and known Theta exchange.
  - A malformed integer field, a bool, a non-decimal price or a conflicting same-timestamp duplicate makes the leg `quote_response_invalid`.
  - The earliest valid quote decides. A size requirement is applied to it alone and never searched forward.
- **Clocks (amendment A4).**
  - A quote acquired before its event time, or after the leg's retrieval clock, is invalid.
  - A window ending after retrieval is `pending`.
- One shared frozen grid of 90 scenarios is applied to every name. The decision scenario is designated in advance: 5 s latency, size 1, fee 0.65, slippage 0.01.
- The gross (descriptive mid), ruler, scenario and actual-fill layers stay separate. Actual-fill is always unavailable.
- Population loss, a session-cluster bootstrap with honest block N, and the paired decision-minus-baseline delta.
- The break-even extra per-side cost is reported as a per-episode distribution with a session-cluster bootstrap CI (2,000 replicates, seed 5051).
- A chronological whole-session 60/40 split (`chronological_session_split`).
- **Frozen classifier (amendment A3).** The order is:
  1. insufficient_data
  2. no_benefit_under_ruler
  3. execution_fragile, if any of these holds:
     - the decision CI lower bound is ≤ 0;
     - the paired mean drop is ≥ 1.0 pp;
     - population loss is ≥ 10%;
     - the decision scenario falls below 20 blocks or 60 episodes.
  4. execution_robust

`tests/test_options_execution_sensitivity.py` has 47 hermetic tests. They pin:

- req1 through req6;
- parity against an independently transcribed OA-3 oracle: 22 parametrized paths, plus a check of the reason codes on boundary, crossed and zero-side cases;
- no-silent-activation.

## Limitations

- This is a negative-availability result, not a market finding. It says nothing about whether OA-3 expressions would or would not be execution-fragile.
- Before freezing, I probed status and reason counts and parquet schemas. PREREG §5 discloses this. No return value was ever read, and none exists.
- The `.md`, `.yml` and `.html` files in the vintage were skipped as documentation or configuration, not data. Their counts are listed above.
- The live parity check runs on synthetic rows. It proves that the selection rules agree, not that any real quote exists.
- No episode ingest adapter is built. If eligible inputs ever appear, `evaluate.py` returns `NOT_IMPLEMENTED` with `manual_review_required = true` instead of computing anything.
- `actual_fill` is structurally unavailable. Displayed size is not queue position, and a quote is not a fill. Even with tick data, the scenario layer remains a quote-ruler scenario, not realised execution.
