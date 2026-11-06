# Systematic Strategies — first integration contracts

Version: `systematic_research.v1`. Parent: Macro #10089.
This document freezes the first engine/UI boundary. It does not create a runtime, trial registry, book or promotion authority.

## 1. Scope

A read-only research artifact describes two existing fixed candidates, `tsmom_200` and `rsi2_oversold`. Historical results are labelled descriptive reconstructions. Prospective evidence and paper execution have NOT started. No capital recommendation/order is represented. The artifact is deterministic for the same explicit input/configuration/version/timestamps; build wall-clock time is injected, not hidden inside computation.

Source owners:
- `engine/validation.py`: additive strict next-open research calculation; incumbent legacy behavior unchanged.
- `engine/systematic_research.py`: input qualification and pure report compilation.
- `scripts/build_systematic_research.py`: offline explicit-path command boundary.
- `scripts/render_systematic_strategies.py`: pure rendering/explicit-path publication boundary.
- `templates/systematic_strategies.html.j2` and scoped CSS: content using shared product shell/theme/auth conventions.

## 2. JSON artifact

```json
{
  "schema": "systematic_research.v1",
  "generated_at": "<aware ISO-8601 timestamp>",
  "as_of": "<aware ISO-8601 report information cutoff>",
  "mode": "RESEARCH_ONLY",
  "live_orders_enabled": false,
  "status": "research_available or inputs_blocked",
  "source": {"code_revision": "<actual revision>", "data_revision": "<actual manifest/hash>"},
  "summary": {"candidate_count": 2, "evaluated_count": 0, "capital_eligible_count": 0},
  "strategies": [
    {
      "id": "tsmom_200",
      "name": "<source strategy name>",
      "family": "trend",
      "horizon_sessions": 63,
      "status": "research_only or blocked",
      "stance": "Observe only or Stand aside",
      "reason": "<plain language present interpretation>",
      "historical": {
        "state": "available or unavailable",
        "sample_start": null,
        "sample_end": null,
        "observations": 0,
        "net_sharpe": null,
        "net_cagr": null,
        "max_drawdown": null,
        "turnover": null,
        "cost_bps": null,
        "benchmark_sharpe": null,
        "limitations": []
      },
      "prospective": {"state": "not_started", "registered": 0, "graded": 0},
      "paper": {"state": "not_connected"},
      "capital_eligible": false,
      "blockers": [],
      "invalidation": [],
      "instruments": []
    }
  ],
  "data_health": {"state": "ready or blocked", "reasons": [], "last_session": null},
  "limitations": []
}
```

The strings containing `or`, angle-bracket placeholders, and the one-row abbreviated array above are documentation, NOT a fixture or valid payload. Production output contains both fixed candidates with their actual enum values and metadata. The RSI candidate's horizon is 5 sessions. Rows have stable order and identities.

### Types and invariants

- Strict finite JSON: no NaN, Infinity, duplicate JSON keys, stringified numerics or booleans masquerading as counts.
- All required fields exist. Unknown extra fields are ignored by the public renderer; they are never recursively dumped into HTML.
- `schema`, `mode` and `live_orders_enabled` must equal the exact literals. A true live flag, nonzero capital count, true row capital flag, unknown evidence mode or unsupported schema is rejected, not merely hidden.
- Candidate IDs are unique and from the frozen set. `candidate_count` equals array length; `evaluated_count` equals historical available rows; `capital_eligible_count` is exactly zero. For the initial compiler the frozen population is exactly two; do not silently drop a blocked row.
- Count values are nonnegative integers; horizons are positive integers. No candidate may claim prospective/paper maturity under v1. A future contract needs explicit producer and consumer changes.
- `generated_at >= as_of`; both are aware valid timestamps. Sample end cannot be after the information cutoff, start cannot exceed end, and available historical samples have positive observations. Invalid/future timestamps fail closed.
- No-data and failed evaluation produce `unavailable`, null metrics and an actionable reason. Real zero is rendered as zero only when an available, qualified computation measured it.
- `research_available` means at least one descriptive historical result exists, NOT investable or statistically validated. Partially blocked cohorts must disclose exclusions and must not market the reduced cohort as the original full universe.
- `data_health.ready` refers only to the declared input contract for this report. It does not certify point-in-time history, execution capacity, licensing or capital eligibility.
- Missing metric reason is carried in historical/root limitations or blockers. Reasons and source references are escaped untrusted text.

### Units

- Returns/CAGR/drawdown are decimal fractions, not percentages. Display 0.05 as 5%; preserve negative drawdown convention in [-1,0].
- Sharpe is annualized on a stated session convention and not a confidence/profit probability. Null when undefined or insufficient.
- `turnover` must state its convention (sum of absolute traded-notional/equity fractions over the reported sample unless the implementation explicitly documents another convention). It is not silently annualized.
- `cost_bps` is explicit one-way total assumed linear trading cost; round trip pays both sides. It does not imply borrow, funding, market impact, taxes or capacity are modeled.
- Historical sample/observation counts reflect the actually evaluated common dates, not the number of instruments times dates. Correlated names are not independent replications.

## 3. Input and clock semantics

### Source frame

Required columns for the strict fill model: positive finite `open`, `high`, `low`, `close`; any volume/ADV requirement is explicit. A datetime index maps to ordered unique exchange sessions. Preserve instrument/venue/currency identity and actual data/code revisions. Columns share a declared corporate-action adjustment basis. Missing executable values block the affected calculation; no synthetic opens from closes or implicit executable-price forward fill.

Metadata is an explicit caller contract, never inferred from filenames alone. At minimum it conveys the source identity/revision, adjustment basis, actual observation/availability timestamp, universe limitations and expected last completed session where freshness is asserted. The implementing compiler's exact sidecar keys and CLI must be documented with its return; review checks semantics, not a guessed vendor field.

### Three different clocks

1. `session`: which trading interval a bar describes.
2. `available_at`: when this exact observation/version became available to the system.
3. `as_of`: latest information allowed in this report.

Reject records known only after `as_of`. A current full-history adjusted capture may support a **current-vintage retrospective reconstruction**, but its receipt time does not establish that each past value was known at an old simulated decision. Such a run must state that limitation, remain RESEARCH_ONLY, and cannot pass a historical point-in-time qualification gate. Historical event date is not a substitute for availability time. Do not fabricate per-bar receipt timestamps to unlock a run.

Later prospective decisions require the actual then-available source snapshot and cutoff for every feature. Corrections produce new generations with lineage; they do not alter prior decisions.

## 4. Strict next-open mechanics

Decision from completed close t can first trade at executable open t+1. Existing shares receive the close-t to open-(t+1) move; newly bought shares do not. After rebalancing, carried/new shares receive the open-to-close move. Sell decisions keep their overnight risk until the sale. Costs are charged on traded notional and included in cash feasibility.

Conservation: `ending_equity = ending_cash + ending_shares * mark`; changes in equity reconcile to market exposure, income if explicitly supported, and costs. Cash and shares cannot imply leverage or shorting in v1. The cost of entering full exposure cannot create hidden negative cash. No fills occur before source availability or in missing/untradable intervals.

Terminal convention is explicit: marked inventory is not an executed liquidation. Do not subtract imaginary closing costs or omit required final liquidation costs while labelling both simulations identically. Benchmark uses compatible dates/fills/costs; any asymmetric convention is disclosed and prevents an apples-to-apples alpha claim.

No capacity estimate without qualified volume/ADV, size and impact inputs. Missing/nonpositive ADV cannot become zero impact. Flat-bps results remain descriptive assumed-cost research.

## 5. Required falsifiers

| Test | Failure it must catch |
|---|---|
| Close100 -> next open110 -> close110, new entrant | Capturing the 10% pre-fill gap is forbidden. |
| Existing holder across the same gap | Overnight exposure must not vanish on a sell decision. |
| Initial purchase and later sale | Both cost legs charged; cash/shares reconcile. |
| Full allocation with positive fees | No negative-cash hidden leverage. |
| Append future price/metadata rows | Earlier decisions/results at the prior cutoff unchanged. |
| Current capture of old data | Reconstruction labelled; no fabricated historical availability. |
| Duplicate/unordered sessions, invalid OHLC | Typed block, not silent repair into a successful trial. |
| Missing opens, costs or required metadata | Null metrics/explicit blocker; no invented defaults. |
| Zero/missing/nonpositive ADV | Capacity unavailable, never free liquidity. |
| Missing/NaN/Infinity metrics | UI never displays a zero or validated badge. |
| True live/capital flag or unsupported schema | Reject unsupported authority state. |
| Untrusted HTML/source/extra account fields | Escaped text and allowlisted output; no private leak. |
| Repeated frozen report and renderer invocation | Deterministic artifacts and no account/QLedger/network effect. |
| Legacy evaluator fixture comparison | No incumbent result/behavior drift from the additive helper. |

## 6. Product acceptance

Overview stance: Observe only / Stand aside. No strategy approved for capital. The next unmet prerequisite is visible, not a fake buy/sell action. Candidate evidence shows historical, prospective and paper separately. Scope limitations and actual versions are accessible. No fabricated chart, target return or live account balance.

Use shared shell/theme/SEO and existing access policy; no duplicated header, auth or global navigation writer in worker scope. Keyboard disclosures work, 390px and 1440px layouts have no clipped text/page overflow, light/dark contrast is legible. Neutral borders only; no colored container edge. Source credentials, shares, fills and account economics are excluded from any public projection.

Paper remains a separate deliverable: connected file is unsafe due to size warning, and create_file is not admitted. Until a safe exact document is bound and edited through the same approved carrier, implementation/preview remains NOT_APPLIED_TO_PAPER.

## 7. Release boundaries

Compiler and renderer are explicit offline commands first, not scheduled by import. No workflow, production artifact, QLedger, portfolio, broker or Terminal mutation follows automatically. Integrator owns source review, negative effects tests, appropriate publication, actual user-path proof and the next wave. A built research UI is not an approved strategy and a passing synthetic test is not economic evidence.
