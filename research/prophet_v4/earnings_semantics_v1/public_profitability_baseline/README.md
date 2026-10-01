# Profitability selection is not market protection — public baseline

**COMPLETED EXPLORATORY BASELINE, NOT A PROPHET MODEL PROMOTION.**

This third phase followed the connected earnings-brief/profitability implementation
rather than treating its commit as whole-program completion. It answers one narrow
investment question using an existing public research-portfolio dataset. It is NOT
the previously refused daily-vs-monthly trend experiment, does not add a risk-switch
rule, reads no native H1/Cycle outcomes, and does not register or amend Gate E.

## Outcome-blind setup

The protocol was written and SHA256-bound BEFORE downloading/calculating returns:
`3e931f5a98e3b1002971e4ef2b36378bb50654b37037b4032dcfdbdc6833c2bd`.

Source: Kenneth French's25portfolios formed on Size and Operating Profitability:
https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/tw_5_ports_me_op.html
https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/25_Portfolios_ME_OP_5x5_CSV.zip

Use only the first MONTHLY VALUE-WEIGHTED return table. Within each of5size
quintiles compare lowest, middle and highest operating-profitability quintiles;
equally weight the5matched size cells in each arm each month. No optimized
weight, factor blend, regime label, trend rule, replacement stock or future-risk
condition. Sample July1963–August2026, **758months**. Fixed eras1963–1989,
1990–2009 and2010–August2026. All monthly observations must be present/finite;
missing data never becomes zero. The cell labels, date continuity, identical
size weights and column-order invariance are checked explicitly.

The source's operating-profitability variable is annual revenues less cost of
goods sold, interest and selling/general/administrative expenses, divided by
book equity, formed under the source's June sort and prior fiscal-year convention.
It is NOT our operating-margin-growth calculation and NOT Novy-Marx's gross
profits/assets measure. Firms with negative book equity and other source-ineligible
accounting data are excluded. Do not generalize this sample to every potential
Prophet stock, especially distressed or newly listed firms.

## Results: gross theoretical portfolios, not executable customer returns

| Fixed profitability group | CAGR | Annualized monthly volatility | Maximum monthly-observed drawdown | Worst month |
|---|---:|---:|---:|---:|
| Low |9.44%|21.40%|−71.11%|−30.19%|
| Middle |12.85%|16.61%|−50.41%|−24.46%|
| High |13.16%|18.91%|−59.44%|−27.76%|

High minus low's annualized ARITHMETIC mean return difference is **2.8650percentage
points**. The fixed12-month moving-block exploratory95%interval is **0.1672to
6.1677points**,4000replications/seed20260930. Candidate blocks overlap; starts
are sampled independently with replacement. This is descriptive uncertainty,
not a newly validated alpha, a guarantee of block-bootstrap coverage, or a
multiplicity-adjusted native model test. The CAGR difference is a different
quantity and is not substituted for this declared primary contrast.

All five size-matched high-minus-low mean contrasts are positive over the full
sample; that pattern does not prove a causal profitability effect or robustness
after every other risk/valuation exposure. Full results are in the JSON file.

## The recent subperiod prevents a simplistic scoring conclusion

January2010–August2026, fixed before outcomes:

| Group | CAGR | Maximum monthly-observed drawdown | Worst month |
|---|---:|---:|---:|
| Low |11.84%|−42.21%|−17.63%|
| Middle |13.96%|−31.36%|−21.41%|
| High |12.42%|−34.53%|−23.60%|

The highest-profitability group did NOT have the highest return or lowest risk
in that era. High-minus-low arithmetic mean advantage was only about0.0510points
per year in this subperiod. Middle's observed superiority is a diagnostic result,
NOT permission to select the middle bin after looking at results. No second
threshold search or new recommended stock portfolio follows from this table.

The defensible conclusion is narrower: profitability deserves qualified study
as a selection dimension, but a high-profitability label is not a market-risk
shield or automatic high-conviction rule. Average return, tail behavior and entry
price remain distinct. These results do not establish that any single factor
makes individual stock picks safe or solves Prophet's timing problem.

## Build implication for the existing Earnings/Leadership/Cycle programme

Keep three distinct inputs: profitability LEVEL, comparable profitability CHANGE,
and price/valuation paid. The new accounting bridge explains change; it does not
supply a profits/assets or profits/equity denominator or a calibrated return model.
For an admitted native experiment, test the incremental contribution of level
and change separately against existing price/sector controls, preserving universe,
source availability, costs, entry behavior and original trial history. Restrict
interaction complexity rather than turn these related numbers into independent
votes. Assess tail/market permission through its native policy owner separately.

No rank weights, C1 member, B4 rule, market label, portfolio target, trading signal
or user alert was changed by this public analysis. Profitable companies can still
have poor entry economics; scenario price discipline and market permission must
not be bypassed by an attractive financial statement.

## Reproducibility and limitations

Input archiveSHA256:
`b365749f6f1bfad2484b8f539197d3fc8874863bf49067ffb70c7fe8ec9bfafc`.
ResultSHA256:
`777d9ff1e83bce61f962e6a9ec6aa876691da0451e2380d79e36132a7aefc209`.
Original result independently reran byte-identically using that retained archive;
`reproduction_receipt.json` binds code/protocol/input/output. The only subsequent
script change was input/output ergonomics and refusing another data vintage;
no numerical procedure or hypothesis changed after the result.

Run the committed script with a NEW output directory and optional exact archive:

```
python3.12 public_profitability_baseline.py --output-dir <new-evidence-directory> \
  --archive <exact-captured-25_Portfolios_ME_OP_5x5_CSV.zip>
```

Without --archive it downloads only the named public file and refuses if its
hash differs from this study's vintage. It will not overwrite an existing result.
The raw third-party portfolio history is retained only in the existing session
evidence directory, not copied into the product's source/data stores. Committed
results are aggregated derived statistics with source attribution.

This is the current revised research vintage, not proof of historical ingestion
or live point-in-time stock availability. Returns are gross: no fee, turnover,
capacity, spread or underlying reconstitution model. The5size-cell mixture is not
a market-cap-weighted index. It theoretically rebalances those source portfolios
monthly. Monthly drawdowns omit intramonth excursions. Source construction and
CIZ-format methodological changes are inherited, not repaired by this analysis.
No new native price adapter, collector, registry, experiment grader or model-owner
plane was created. A public diagnostic is not a replacement for the existing
native financial evaluation gates.
