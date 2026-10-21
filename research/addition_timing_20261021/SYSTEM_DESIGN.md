# Research decision record for ownership, recovery and funded additions

## Status and purpose

This is a **research-only design** for existing Mastermind/Macro surfaces. It specifies an inspectable decision record, not a new score service, deployment policy, or authority to rank, size, buy, sell, or delay contributions. Existing selection, context, lifecycle and validation owners remain responsible for their respective outputs.

The user's question is whether a worthwhile asset offers a useful, affordable entry. The record should explain why the asset is eligible, what condition has developed, what changed now, whether money is available, what would invalidate the setup, and what remains unknown. Those questions require different evidence.

## Accepted results constrain the design

The completed additions experiment supplies a negative primary result. With identical funding and SPY ownership, signal waiting finished approximately **$1,841 behind immediate purchases** and **$369 behind blind month-end purchases**, with effectively unchanged maximum drawdown versus immediate buying. A positive signal-funded subset did not compensate for the cost of waiting in deadline-funded months. These are constraints on the proposed behavior, not reasons to repair the historical rule until it wins. See the [assessment](REPORT.md), [account contrasts](results/account_contrasts.csv), and [frozen protocol](PROTOCOL.md).

The earlier [accepted ownership-recovery research, PR #9989](https://github.com/mastermindx-market-intelligence/macro/pull/9989), separated eventual recovery from reference-low survival. The core joint cohort had 67 positive endpoints among 74 observations, while the frozen low survived in only 39. Its stop analysis also weakened the explanation that most converted winners merely hit a stop above an untouched reference.

Consequently, the product must not equate a favorable ownership context, a durable low, an executable entry, and a funded opportunity. Evidence from selected surviving businesses also remains distinct from evidence that those businesses could have been selected contemporaneously.

## Six linked decisions

| Decision | Record content | Boundary |
|---|---|---|
| Ownership eligibility | Existing selector, reason to own, universe, source version, valuation/information qualifications | Price leadership alone does not establish business quality; current successful names do not establish historical eligibility. |
| Washout/watch state | Original definition, actual timeframe, activation and expiry rules, completed-bar timestamp, active/inactive/unknown state | A weekly or biweekly state is context only unless a specific decision policy has earned further authority. |
| Recovery trigger | Exact indicator species, input series, event timestamp, nominating instruments, next executable open | A fresh event differs from an already-positive state. MACD on RSI cannot silently become ordinary price MACD. |
| Funded opportunity | Contribution identifier, availability time, remaining cash, permitted purchase basket, previous spending, deadline | An alert cannot borrow a future contribution or reuse an already-spent budget. |
| Reference-low status | Frozen level and price basis, source window, strict/tolerant breach definition, first observed invalidation | A later profitable endpoint does not retrospectively restore a failed reference. Low invalidation and ownership-thesis failure are separate. |
| Business-information uncertainty | Original source, disclosure stage, fiscal horizon, metric/basis, availability precision, comparability and unresolved fields | Missing guidance is not unchanged guidance; a favorable annual headline does not necessarily improve the remaining-period outlook. |

These are separate fields rather than six votes. A legitimate record can say: ownership remains eligible; washout active; recovery not observed; contribution available; reference intact so far; forward outlook unresolved. It must not manufacture a single probability from that combination.

The general record supports higher-timeframe context. The next additions hypothesis must use the original source watch actually located and admitted; this design does not substitute a weekly/biweekly definition for the sector recovery calendar.

## Why sequence matters more than unanimous readings

Nested oscillators often transform overlapping observations of the same price history. Agreement may describe one movement repeatedly. A daily recovery within a weak weekly state can be the intended sequence: an older decline establishes context, and a newer event describes a possible repair. Requiring every timeframe to turn together can change the price paid and the age of the opportunity.

Preserve activation, first recovery, repeat recovery and expiry as chronological events. Do not count repeated alerts in one market episode as independent evidence. Completed weekly and biweekly bars require their actual availability clocks and anchors; a later completed bar cannot rewrite the earlier decision.

The record should show disagreement in plain terms, such as “shorter momentum improving; longer context remains weak.” It should not automatically resolve disagreement into a veto or confidence bonus. Any such behavior becomes part of the policy requiring evaluation.

## Positive return, entry utility and durable low

A purchase can become profitable after price makes another low. A low can remain intact while a late, expensive entry disappoints. A stop can reduce account damage while lowering the fraction of profitable positions. Each result answers a different question.

Research outcomes therefore need distinct labels: reference-low survival; return from an executable entry; adverse excursion; policy-specific stopped outcome; and capital-account wealth/drawdown. Preserve each denominator and common maturity date. An immature holding remains in account value even when it is absent from a completed-endpoint statistic.

For additions, compare every funded contribution with its scheduled alternative. Keep signal purchases, deadline purchases, pending cash and unfunded alerts visible. The [protocol's waiting decomposition](PROTOCOL.md#outcomes-and-attribution) separates acquisition timing, cash interest and unincurred fees. Favorable prices on selected deployed dollars cannot substitute for the wealth of all contributed dollars.

## Additions do not protect the existing book

Delaying a new contribution changes only that contribution's exposure. It does not sell, hedge or otherwise protect previously acquired holdings. With constant monthly funding, the waiting cash becomes a smaller fraction of an accumulating account.

The tested accounts began empty in January 2020. Early cash decisions could therefore materially affect a young account's drawdown. The month-end policy's lower maximum drawdown cannot be presented as persistent protection for a mature book. The [account paths and summaries](results/account_summary.csv) must be interpreted under that funding contract.

Use flow-adjusted unit NAV for drawdown and include all cash and holdings. If a future study adds a common legacy holding, report the additions ledger separately and calculate total-account risk explicitly. Constant purchase weights also do not create identical acquired share vectors when execution dates differ.

## Business information and exits require their own evidence

The [original-release measurement pilot](GUIDANCE_PILOT.md) shows why an annual guidance label is insufficient. Disclosure stage, business perimeter, accounting/currency basis, completed-period contribution and remaining-period expectations can differ. A later call cannot supply information to an earlier release-time decision. Preserve unresolved classifications and source coverage; no retrieved headline is not proof of no news.

Use the existing information audit to distinguish an available dataset from a qualified historical feature. Current or retrospective comparisons do not become point-in-time gates through persuasive interpretation. Source extraction and label review precede any investment-effect claim.

Exits also require separate objectives. The opposite oscillator reading does not automatically invalidate ownership. Thesis failure, reference failure, a capital constraint, opportunity expiry and optional profit protection need different evidence and policies. Evaluate downside avoided, upside forgone, execution costs, time out of market and re-entry together. [PR #9989](https://github.com/mastermindx-market-intelligence/macro/pull/9989) leaves symmetric top/exit claims unqualified; this design adds no automatic exit behavior.

## Decision log and research presentation

Each record should retain security and basket identity; source and rule versions; event, source-availability, observation and decision times; watch identity; frozen reference; trigger status; funding identifier; cash before/after any modeled purchase; selected branch; executable date; expiry; and explicit unknown reasons. Later corrections should reference the superseded record rather than erase what was knowable.

Display the explanation in decision order: **why own, current watch, new event, available budget, invalidation, unresolved information**. Put methods and source details behind that explanation. Keep descriptive context, exploratory associations, executed research policies and prospectively confirmed evidence visibly distinct.

The [next hypothesis](NEXT_HYPOTHESIS.md) is deliberately untested. It asks whether an original watch already active at funding can justify bounded waiting. The present negative result remains unchanged, and this record creates no performance promise or production behavior.
