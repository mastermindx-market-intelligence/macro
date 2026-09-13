# Round 5 addendum: actual grader boundary and review-placement amendment

September 11, 2026 UTC; existing research parent
`prophet-absolute-downside-research-20260910-sol-001`, PR #7043.
This supplements `ROUND5_POPULATION_AND_SCORING_QUALIFICATION.md` at d405acf2.
It does not change the pilot, its preregistration, any model or product source.

## Existing grader, not a replacement

Static reads at Macro `4b1f8fddcc4eb6f36133fca4d42018678b74d30b`:

- `scripts/grade_us_board.py`, first430lines, blob
  `68ef9eb7620f0592e3cd02d66a3eae2ab0998dce`.
- `engine/grading.py`, first200lines, blob
  `1208a7aa597159969a0ed7ccd359972bc413941a`.

The board script declares one row per (as_of,lane,ticker,horizon), horizons
5/10/21/63 sessions, and `LEDGER_HORIZON=10` for its named Track-record popup.
The common `fill_index` returns the next bar strictly after the signal bar. Its
entry price convention is the next bar's close. `forward_metrics` measures the
strictly forward close window after that fill. The board's `mae_close_excess`
is a daily-close-path excursion relative to SPY, not an absolute intraday low.

These definitions can be correct for their declared purpose without validating
a morning entry's experience during the following session. A hypothetical session
that opens100, trades to92 and closes100 has an8% open-to-low excursion that a
next-close entry convention does not claim to measure. That is a target-boundary
illustration, not a real pick reconstruction or an executed grader result.

The script already contains `extend_prices_to_admitted`, price recovery from the
admitted-name store, unresolved-name reporting, and price-basis stamping. Preserve
and extend those owners rather than building another population or grading plane.
The adjusted-first ladder retains a disclosed unadjusted fallback, so adjusted-first
must not be restated as every row being adjusted. Historical coverage/performance
figures in comments were not reread as current statistics.

No outcome file, price dataset, canonical grader execution or W3 comparative result
was accessed in this static inspection. This does not establish a new defect in the
next-close convention or the current production completeness of its consumers.
The new tactical path study must use an explicit approved owner extension/comparison,
not silently rewrite the existing scorecard. The popup10-session constant belongs
to that consumer; it does not resolve P0C's still-unbound target by itself.

## Review placement: remove a self-imposed circular requirement

Exact child: `prophet-downside-pilot-independent-review-20260911-sol-001`.
Exact Slack root: C0BSBM78V1N/1789095597.875539. Frozen review subject remains
50a5bc1881aa29a51b2971cd241c0443f65e4d6c and its original six files only.

Return1789104967.772179 reported BLOCKED_PUBLIC_READ_CAPABILITY: the inspected
interaction was an unrelated Code session, and the former no-new-task plus
no-unrelated-prompt ceiling left no eligible Web interaction in which its public
reader could be invoked. No provider turn was sent. That does not prove the public
repositories are inaccessible.

SolCONTINUE1789105520.784709 accepted this finite finding and amended only that
self-imposed ceiling. The existing approved placement/provisioning mechanism may
create and deliver exactly one dedicated included-capacity, non-author Chat/Web
review interaction. Initial bounded pickup verifies actual current protected
procedure and the six fixed sources. ACK, source qualification and START remain
separate; a missing or refused read returns its exact blocker.

No second candidate, unrelated Code-task input, new credential, integration
enablement, paid fallback, downloader/proxy, new queue or refusal bypass is permitted.
The placement owner must reconcile its own prepared/queued/unknown effects before
creation. If its approved creation/delivery mechanism is absent, return that exact
blocker and stop the attempt. Both earlier safety-refused diagnostic scopes remain
excluded. This is the same unstarted review child, not a new worker assignment by
mere discovery of this document.

The ruling is not evidence that a conversation was created, a prompt delivered,
source access succeeded, or review began. The latest full-thread read after the
ruling had no later receiver or execution receipt. The existing aggregate and sibling
continuation sources remain untouched.

## Continuation and proof limits

The product step remains the existing owner's disposition of the closed-read
capsule and the wrong-kind horizon evidence on6817, then separately authorized
consumer/source review and real publication/browser proof. No adoption is inferred.
The research step is complete opportunity/clock qualification, not a new model on
the consumed pilot holdout. The25metadata checks and12synthetic scoring tests are
not full B1 validation, independent review or predictive validation.

Protected procedure remained068dcc1533776672844b36ffcde30fad68a4317f at the action
reread. Draft/HOLD stays. No source implementation, market-data write, ranking,
policy, portfolio, Runtime Job, Ready, merge or production effect was made here.
