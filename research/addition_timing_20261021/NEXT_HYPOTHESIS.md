# Untested hypothesis: permit waiting only when a watch already exists

## Status and question

**Not run.** This is a proposed research contract, not a repaired result or deployment policy. The existing history and outcomes are exposed; another calculation on them cannot become out-of-sample confirmation.

The completed [additions assessment](REPORT.md) found that signal-funded benefits did not offset deadline-funded waiting costs. The next question is whether waiting is useful when the original qualifying washout watch is already active as the contribution arrives. Later signal occurrence cannot determine that funding-time classification.

## Source admission before execution

Locate and inspect the exact original watch implementation associated with the inherited recovery source. Pin its revision and dependencies; verify indicator species, inputs, timeframe, readiness, activation, persistence, invalidation, expiry, source aggregation and timestamp semantics. Replay only information available at funding. Do not invent a washout threshold, infer a persistent watch from a recovery event alone, or substitute a convenient weekly condition.

If the source defines only recovery events and no qualifying persistent watch, the hypothesis is not yet executable as reuse. An explicit definition must be separately designed and frozen before outcomes. The mapping between source instruments, watch state and the frozen recovery calendar must be unambiguous.

## Minimal comparison

Retain the [existing protocol](PROTOCOL.md): identical funding dates and amounts, purchase baskets and weights, frozen recovery calendar, completed-bar/next-open execution, month-end expiry, costs, cash scenarios, terminal accounting and common contribution maturity. No new stop, exit, leverage or future funding enters.

Compare immediate purchase for every contribution with one conditional policy:

- **Original watch demonstrably active at funding:** permit the existing bounded wait for an eligible recovery execution, with the unchanged expiry.
- **Watch inactive:** purchase immediately.
- **Watch unknown:** do not grant permission to wait; purchase under the immediate baseline, retaining UNKNOWN and its reason separately from known inactivity.

The immediate comparison remains essential **within active-watch contributions**. Oversold conditions may already provide an attractive purchase; recovery confirmation might surrender it. Freeze all branch semantics before calculation. Do not allow later watch activation to reclassify an already-funded contribution.

## Full-budget evidence and falsifiers

Include every contribution, deadline purchase, pending balance and unfunded alert. Report total wealth, flow-adjusted drawdown, waiting attribution, coverage and common-endpoint differences. An accepted-subset win rate cannot replace full-budget accounting. Identify shared episodes and preserve the existing ownership-selection qualifications from [PR #9989](https://github.com/mastermindx-market-intelligence/macro/pull/9989).

The hypothesis is weakened or rejected if waiting adds no useful benefit against immediate purchase within the active-watch state, if aggregate wealth/risk fails the objective frozen before outcomes, or if apparent gains require future information or dropping unavailable cases. A result concentrated in one episode remains a limited lead. Inadequate coverage or precision is inconclusive, not success.

Log funding time; original watch/source version; the actual observations available; active/inactive/unknown classification; branch reason; recovery nominations; executable purchase or expiry; cash and fees; and contribution-level outcome/attribution. Corrections preserve prior records.

Any subsequent confirmation requires genuinely unexamined, historically knowable data or prospectively matured observations. This document reports no new performance, changes no vendor or production behavior, and leaves the completed negative primary result intact.
