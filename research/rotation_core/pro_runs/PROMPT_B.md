COMMISSION PRO-RUN B - long-history study of risk pivots and defensive rotation, 1926 to 2019

COGNITION_ROUTE: CHAT_INCLUDED_DEFAULT
CHAT_REASONING_MODE: PRO_MODE_EXCEPTION
WHY_PRO_MODE: a pre-specified, multi-decade, multi-rule empirical study with code, statistics and an honest verdict in one pass.
WHY_NON_PRO_INSUFFICIENT: the study needs sustained design, data assembly, execution and self-audit; the Chairman directed this class of study to Pro sessions on 2026-11-11.
PRO_MODE_TASK_CLASS: LONG_HORIZON_FRONTIER_REASONING
EXPECTED_DURATION_MINUTES: 120
STOP_CONDITION: one comment posted on macro issue #11014 beginning "PRO-RUN B", or the full report returned in this chat if posting is impossible.

Commissioned by the Prophet programme CEO under the Chairman's direction of 2026-11-11 that deep research runs go to Pro sessions and post results to GitHub. Research only. Authorized: one comment on issue #11014 and, if you have write access, one new branch pro-run/rotation-b-20261111 in mastermindx-market-intelligence/macro holding code and small result tables under research/rotation_core/pro_runs/B/. No pull request. Do not commit raw vendor price files or any FRED series.

THE QUESTION
Mastermind's thesis is that money is almost always rotating - between sectors, between equities and other assets, into cash and treasuries - and that the value lies in recognising the turn: getting out of high-beta growth when conditions stop favouring it, into the defensives that lead when it falls, and back in after a real washout. We are not trying to catch falling knives. Before we believe this, we want to know what nine decades of public data say. Over 1926 to 2019, which simple signals, fixed in advance, would have told an investor when to cut equity risk, when to rotate from cyclical/growth industries into defensive ones, and when to return - and what did each cost in missed upside?

HYPOTHESES TO TEST (the Chairman's, stated plainly)
H1. Risk-off and risk-on pivots can be identified by a confluence of trend, credit and macro signals better than by any one alone.
H2. When high-beta cyclical/growth industries roll over, defensives (consumer staples, health care, utilities) lead, and rotating between the two groups is where a rotation edge lives.
H3. Breadth deteriorating inside a leading group while its price still rises warns of a top; a breadth washout marks a durable bottom.
H4. Interest rates, real rates and credit spreads condition which side of the growth/defensive seesaw leads.
H5. The yardstick matters: a cap-weighted index dominated by its largest names is a different opponent from the equal-weighted market.

DATA (public only)
Ken French data library: daily market, size and momentum factors; 12, 17 and 49 industry portfolios, value- and equal-weighted, from 1926-07. Use the 49 industries as the members of each group for breadth. Shiller's data for long rates and CPI. FRED or ALFRED for the Baa-Treasury spread, bill rate and unemployment (use real-time vintages for anything revised; if you cannot, say so and lag conservatively). S&P 500 index levels. State every source and its start date.

RULES OF THE STUDY - these matter more than the result
1. Write down every rule before computing any outcome, and put that list first in the report. At most 12 rules in total, every variant counted. No tuning afterwards. If you look at an outcome and then change a rule, say so and count it as a new trial.
2. Decide at the close of day t, trade at the close of t+1. Costs 5 bp per side from 1975, 25 bp before; show 2x as a stress.
3. Score every rule against three references: the cap-weighted market, the equal-weighted market, and a mix of market and bills matched to the rule's own average equity exposure computed causally. Holding less equity is not rotation skill.
4. Three eras reported separately: 1926-1959, 1960-1989, 1990-2019. A rule that works in one era only is reported as that.
5. NOTHING dated 2020-01-02 or later may be computed, plotted or mentioned as evidence. That period is our sealed hold-out.
6. Block-bootstrap confidence intervals, a multiple-testing correction across all rules, and the minimum effect this history could detect at all.
7. A negative result is a valid and useful outcome. Do not rescue a hypothesis.

WHAT TO RETURN
One comment on https://github.com/mastermindx-market-intelligence/macro/issues/11014, first line "PRO-RUN B" (or the same text as your final message here):
- The pre-specified rules, exactly.
- A results table per rule and era: annual return, volatility, worst drawdown, up-capture and down-capture, excess over each of the three references with intervals, turnover, corrected p-value.
- An episode table for 1929-32, 1937, 1962, 1966, 1969-70, 1973-74, 1980-82, 1987, 1990, 2000-02, 2007-09 and late 2018: for each rule, days from the peak to its exit, days from the trough to its re-entry, drawdown avoided, upside missed, and false pivots per calm year.
- For H2 and H4: what defensives did relative to cyclical/growth industries in each episode, and whether any signal led that relative move or only followed it.
- A blunt verdict on each hypothesis: supported, not supported, or untestable with this data - and why.
- The three to five rules, with exact definitions, that deserve a place in a frozen second protocol, and the ones that should be dropped.
- Code location, and every limitation you know of.
