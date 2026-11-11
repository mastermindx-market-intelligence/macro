# Execution notes before outcomes

No strategy outcome has yet been computed. Ten synthetic accounting and integrity tests pass.

- Calm-year denominators require a complete calendar year of eligible strategy observations matching every French market session in that year. The partial initial data year is excluded.
- R7/R8 initialization requires every input used by the frozen state machine to be defined, including sleeve SMA200, breadth history, and minimum members. Start in C at the first fully eligible decision, then evaluate that close's signal; execution is at the next close.
- Data acquisition repair: the FRED CSV endpoint is `graph/fredgraph.csv`, not `graph/graph.csv`; the official Shiller workbook is linked from shillerdata.com. These fixes change transport, not candidate rules.
- A public S&P500 daily price series was obtained through Yahoo's chart endpoint with an explicit terminal timestamp. It is descriptive only; it never replaces French total-return M. Source bytes are retained only as excluded local inputs.
- The unauthenticated ALFRED vintage API request returned HTTP400. No full real-time panel was obtained. Current-vintage conservative-lag simulations remain explicitly limited as preregistered.
