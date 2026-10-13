# Value × profitability: joint support, not two automatic conviction bonuses

**Completed exploratory public diagnostic; no native ranking or policy promotion.**

This extends the prior profitability-only baseline with a fixed interaction
question, not a post-hoc search for the highest-return portfolio. Source:
https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/32_ports_me_beme_op.html
https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html

Protocol499ed313bfab7a9bc770b35f0a0cf5f8b08a3988997c7003232f77fac8885989
was saved before return calculations/download. The source's32Size×B/M×OP
portfolios use two size groups and four valuation/profitability groups within
each size. Every comparison here has50%Small/50%Big, rebalanced at the research-
portfolio level monthly. First monthly value-weighted table only, July1963 to
August2026,758complete months. No fitting, thresholds selected after returns,
regime switch, native H1/Cycle data, live allocations or substitute ticker basket.

The primary contrast is:

`(highOP-lowOP within highBM) - (highOP-lowOP within lowBM)`

Its annualized ARITHMETIC mean is−3.1508percentage points; the exploratory paired
12-month moving-block95%interval is−9.5149to+2.4395points,4000draws/seed20260930.
This wide interval includes zero. It does NOT establish a reliable interaction,
reject additivity, or warrant a new ranking coefficient. Other reported group
returns are diagnostics, not a second search for a winning strategy.

| Full-sample research arm | CAGR | Monthly-observed max drawdown |
|---|---:|---:|
| LowerB/M, lowerOP |4.28%|−86.22%|
| LowerB/M, higherOP |12.36%|−56.79%|
| HigherB/M, lowerOP |12.46%|−69.13%|
| HigherB/M, higherOP |13.18%|−77.89%|

Fixed2010–August2026 subperiod: lowerB/M+higherOP14.99%CAGR/−25.98%drawdown;
higherB/M+higherOP4.36%CAGR/−74.66%drawdown. Do not install the former after
seeing this result. Neither book-to-market nor operating profitability identifies
intrinsic value, expected upside, market permission or loss protection by itself.
B/M is an accounting-price characteristic, not a full economic valuation model.

## Crucial composition finding, not an ex-post exclusion

A subsequent source-quality inspection of the same archive's Number of Firms
panel found that BIG/HiBM/HiOP has full-sample median6firms and recent median4,
with fewer than10firms in188of200recent months and a minimum of1. SMALL/HiBM/HiOP
has recent median28firms. Contrast BIG/LoBM/HiOP's recent median141firms.

This count inspection was done AFTER the return result and is labeled as such;
it changes no sample, weights, endpoints or result. Counts do not measure weights
or capacity, and do not prove which firm caused the performance. They show why
an intersection of attractive labels can become a thin, different population
rather than independent diversified confirmation. A future qualified native
model needs declared joint support and concentration diagnostics, not a claim
that two factor names imply twice the evidence.

## Source-method precision

The detail page abbreviates OP's denominator as book equity. The Data Library's
August2018 revision note explicitly adds minority interest to that denominator.
That newer methodology note qualifies the shorthand in the earlier study. The
archive's methodology/vintage is inherited; this analysis does not recompute firm
fundamentals or correct historical data. OP is neither operating-margin growth
nor gross profits/assets, and its denominator differs from the B/M numerator when
minority interest is present. Do not count related accounting transforms as
independent economic signals.

Returns use the current revised CIZ research vintage, not recorded historical
system knowledge. Negative-book-equity/source-ineligible firms are excluded by
the source. The source portfolios' underlying values and membership change; no
company-level causal effect, execution model, fees, turnover or capacity is
established here. Monthly drawdowns omit intramonth loss. The size-balanced
mixture is not a capitalization-weighted index or actual investable ETF.

## Reproduction and exact limits

ArchiveSHA256 d199ecf6fa92fdd4cc6228baf0c0e8a3e95591bd7eb2b039e1abf7044da8b54f.
ResultSHA2563958f1162d1eadd4769291e18bb4958fd860f03d814a520421e105f045d4877b.
All32identities, common month support, fixed size weights, column-order invariance
and a synthetic additive-zero interaction passed in the executed analysis.
The initial run stopped at an ndarray-property typo before result calculation;
the correction did not change the hypothesis or numerical design.

```
python3.12 value_quality_interaction.py --protocol protocol.json \
 --archive <retained-exact-input.zip> --expected-archive-sha256 \
 d199ecf6fa92fdd4cc6228baf0c0e8a3e95591bd7eb2b039e1abf7044da8b54f \
 --output-dir <new-directory>
```

A further combined independent Decimal reproduction and native mutation-check
command was explicitly rejected before dispatch. Neither that reproduction nor
those extra fault tests ran; no such receipt is claimed. The primary calculation
and listed invariants did execute. Raw third-party histories are retained only
in the existing evidence directory, not in product data or this repository.

Build implication: keep profitability, price paid, source scope and joint support
separate. The connected scenario price/earnings hurdle in the same source wave
addresses a different mathematical question; these factor returns do not validate
its assumptions or turn its price ceiling into a buy instruction. Native selection
changes still require the existing admitted data and evaluation owners.
