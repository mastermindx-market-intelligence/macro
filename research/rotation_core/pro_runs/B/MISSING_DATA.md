# Missing-data identifiability clarification — before strategy outcomes

The first historical execution stopped in input validation, before any strategy outcome table, on missing returns for already eligible industries. The official French TXT counterpart confirms the CSV omissions. No missing return is replaced by zero, an equal-weighted return, another industry, a monthly-implied return, or a chosen old vintage.

This clarifies the frozen instruction "invalidate the affected calculation"; it changes no allocation rule, parameter or trial count (still ten).

- Retain missing daily returns as unknown and permit independent M/RF rules to run. A full-era CAGR, drawdown or test spanning an unknown strategy return is unavailable.
- A known exact target-weight rebalance restores the normalized portfolio weights even if historical total wealth is unknown. Thus later daily returns can be identified without inventing the lost wealth or stitching a full-era NAV. Cost/turnover at the unknown-return close remain unknown.
- Gross signal indexes have arbitrary normalization across data gaps; their ratios/trends are usable only when EVERY observation in the required lookback is known. Relative126 requires 127 consecutive valid levels; return63 requires 64. No calculation crosses a gap by silently using endpoint ratios.
- R7 propagates all feasible states {C,D} after an ambiguous interval. A later observed divergence condition forces both paths to D, and a reopening condition forces both to C.
- R8 propagates {(C,false),(D,false),(D,true)} after ambiguity until observed rules synchronize feasible states. Output holdings only when every feasible state agrees. Never reset to C at an era boundary.
- If a scored era contains unknown strategy returns, keep its full-era inferential test unavailable and assign p=1 in Holm30. For useful description only, separately report the longest contiguous identified segment within that era (ties: earliest segment), with exact start/end and a PARTIAL label. All paired references use that same segment. Segment choice depends only on missingness, never return performance. Pooled summaries with gaps receive the same treatment and are not century-long results.
- A benchmark contrast spanning missing benchmark returns is unavailable; do not drop inconvenient dates to manufacture paired evidence. This particularly affects E49 in early history.
- An episode may have an identifiable exit/entry but an unavailable recovery or loss calculation. Evaluate these fields separately. No missing relative-return interval becomes a negative hypothesis result.
- The lead/follow table retains all window transitions and the designated PRE exit. A prior63 D-minus-C>0 is a follower regardless of the subsequent sign; next63 continuation is a separate field.

This is a material coverage limitation, not a repair that claims to complete missing historical evidence. The final report must distinguish requested full eras from the descriptive clean segments.

