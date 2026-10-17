# W2 Treasury auction context primitives

Isolated deterministic math leaf for the existing Macro auction/event/data owners.
It is not wired to market feeds, collectors, user surfaces or decision consumers.
No real market inputs or live settlement amounts have been invented. Every test
value below is a **synthetic golden fixture**.

## Interface and eligibility

`engine/treasury_auction_primitives.py` uses only the Python standard library.
Test command, from this directory:

```bash
python -m unittest discover -s tests -v
```

`Observation` carries value, exact unit, explicit currency (or `None` for years),
aware `known_at` receipt and observation `as_of`, source reference, input method,
and an explicit role. Input roles distinguish externally qualified values,
synthetic fixtures and auction results. The upstream owner must actually qualify
the values/clock evidence; a label is not source verification. Neither issue
date nor date-only publication evidence can be passed as a qualified receipt.
No parser silently turns dates into midnight timestamps.

Finite `int`, `float`, and `Decimal` are accepted. Booleans, numeric strings,
NaN/infinity, negative magnitudes, invalid units, currency/cohort mismatches and
malformed clocks raise `ValueError`. Missing observations, values, receipt or
observation clocks, and future inputs produce `NOT_COMPUTABLE` (or
`NOT_SCORED`) with a reason and null quantitative outputs. Observed zero is
eligible and distinct from missing. Floats are interpreted through their
shortest decimal representation; use `Decimal` or integer USD for exact source
values. Output values are `Decimal`, timestamps remain typed Python objects and
enums subclass `str`; a consuming owner must deliberately serialize these
without loss, e.g. decimal strings and ISO timestamps. No JSON publisher exists.

### DV01

`calculate_dv01` consumes externally supplied market value and duration; the
caller must give a measure basis. Nominal Note/Bond and Bill/CMB use
`NOMINAL_YIELD_MODIFIED`, value unit `USD` and duration unit
`MODIFIED_DURATION_YEARS`. TIPS use `REAL_YIELD_MODIFIED`, market value unit
`INDEXED_USD` (already reflecting indexed principal and price), and supplied
real-yield modified duration. FRNs require duration unit
`EFFECTIVE_RATE_DURATION_YEARS` and an explicit supplier effective-rate measure
basis. There is no legal-maturity duration fallback or implicit two-year default.
Result-role inputs are ineligible for this ex-ante capability.

The calculation is `market_value_USD × supplied_duration_years / 10,000` and
returns positive sensitivity magnitudes in USD/bp and million USD/bp. Sums and
products of finite decimal inputs use exact rational intermediates, so caller
decimal precision does not round cash offsets or DV01. Separate axes identify
`NOMINAL_YIELD`, `REAL_YIELD` and `FRN_EFFECTIVE_RATE`; no aggregation method
exists to accidentally call their sum nominal equivalent.

| Synthetic input | Hand calculation | Expected output |
|---|---|---|
| Nominal $100mm value, duration 8 | +50bp = +0.005 yield; linear value change = −100mm × 8 × .005 = −$4mm; divide loss magnitude by 50bp | $80,000/bp = $0.08mm/bp |
| Bill $100bn value, duration .08 | 100bn × .08 / 10,000 | $0.8mm/bp |
| Bond $20bn value, duration 18 | 20bn × 18 / 10,000 | $36mm/bp; smaller face, larger supplied-duration burden |
| TIPS $100mm face, index ratio 1.10, par indexed price, real duration 7 | Indexed market value supplied as $110mm; 110mm × 7 / 10,000 | $77,000 per real-yield bp |
| FRN $100mm value, supplied effective duration .02 | 100mm × .02 / 10,000 | $200 per effective-rate bp |

The +50bp check is a linear duration approximation. It does not model convexity,
cashflow repricing or price-yield changes. Coupon/yield/settlement pricing engines,
inflation-index sourcing, FRN reset/discount-margin modeling and market input
acquisition are deferred; provided-duration math is the sufficient frozen slice.
There is no tolerance or fallback that converts unqualified face into market value.

### Private settlement cash

`settlement_cash` requires one named cohort/date/currency, explicit completeness
certification by the upstream owner, and three inventories of `CashComponent`:
private proceeds already excluding SOMA, private marketable redemptions, and
funded buyback cash outlays. All input amounts are **nonnegative cash magnitudes**;
typed component kinds create separately exposed signed cash amounts (+/−/−).
Each category needs known components or a sourced explicit zero component.
An empty list is not observed zero. Missing component observations and late
receipts block net accounting. Duplicate component IDs and mismatched currency,
kind, cohort or settlement date raise.

Synthetic golden cash: proceeds $120bn − private redemptions $80bn − funded
buyback cash $5bn = **$35bn net private cash**. Gross offered face $125bn and
separate SOMA context $12bn are explanatory only and never enter this equation.
Changing the SOMA context to $20bn leaves the net $35bn. A known zero buyback
instead yields $40bn; missing buybacks yield unknown net. Negative net cash is
valid. `reserve_pressure` is always `None`, and scope/limits explicitly disclaim
TGA change, reserve drain, funding-source attribution and debt reduction.

The math cannot discover an omitted auction, redemption, outside-offering cash,
or funded operation. Completeness certification is an owner assertion, not proof
created by this leaf. The optional gross face/SOMA observations do not block
net cash when absent; they are not necessary components of already private cash.

### Context importance

`importance_percentile` handles one supplied nonnegative magnitude axis only:
nominal DV01, real DV01, FRN effective DV01, or absolute net private cash.
Funding uses a distinct USD axis; sensitivities use USD/bp. Its comparison key
contains security class, explicit original-tenor cohort, metric axis, unit and
measure basis. Bills/CMBs/Notes/Bonds/TIPS/FRNs are never mixed by raw notional.
For duration measures the caller must use the same duration convention/basis
for current and historical rows; the supplied basis is part of comparison.

Only distinct historical event IDs whose event time precedes **both** current
event and decision time, and whose observation and receipt are known by the
decision, enter the baseline. Current/future events and result-role values are
excluded. Duplicate IDs raise so revisions cannot inflate sample size; upstream
must choose the eligible vintage. Unknown observations are excluded, not zero.
The minimum is 20 eligible events.

Percentile = `100 × (count_strictly_less + 0.5 × count_equal) / n`.
For synthetic history `[1..10] + four 11s + six 12s` and current magnitude 11,
`less=10`, `ties=4`, `n=20`, so the percentile is exactly **60**. All tied
observations yield percentile 50. Nonterminating percentiles are deterministically
rounded half-even to 40 significant decimal digits, independent of caller
decimal precision/rounding. `WATCH ≥75`, `HIGH ≥90`, otherwise
`ROUTINE` are versioned **product choices**, not fitted or validated thresholds.
Insufficient/unknown percentile remains `NOT_SCORED` with null label. Outputs
always have `is_context_only=true`, method version, comparison drivers and input
provenance; no forecast or policy fields are produced.

There is no multi-axis score, aggregate cluster math, fragility multiplier,
historical data backfill, expectation-surprise estimate, risk probability, true WI
tail, decision sizing, exit logic or provider dependency. Integration remains
blocked until exact source-owner-qualified inputs and custody are established.
