# Options Alpha OA-3 Exact-Option Outcome Ruler v1 — preregistration

**Date:** 2026-09-19  
**Operation:** `options-alpha-oa3-exact-option-ruler-20260919-sol-001`  
**Parent:** `mastermindx-market-intelligence/mastermind-terminal#599` / `options-alpha-product-integration-20260917-sol-001`  
**State:** `PREREGISTERED_INACTIVE` — records/contract only; no expression selection, quote capture, outcome write, score, rank, issue, sizing, trade, deployment, or production claim.  
**Protected procedure:** `Mastermind@ac6180d0ca9107daae54f9eea6bd4b8aef92d630`, Skillpack `mastermind.sol_skillpack.v1` / `1.0.1` / bootstrap `1`.  
**Macro semantic base:** `6ac3817e063ded1d5bc71662bff184151756d868`.  
**Decision:** `DEC:OPTIONS-ALPHA-EXACT-OPTION-OUTCOME-RULER`.  
**Machine policy:** `research/options_estate/options_alpha_exact_option_outcome_policy_v1.json`.  
**Schema:** `contracts/options/options.alpha_exact_option_outcome_policy.v1.schema.json`.

## 1. Purpose

OA-3 exists to answer one bounded question honestly:

> For one exact option expression that was independently selected before its outcome was knowable, what would a conservative one-contract long-option quote ruler show over the frozen H+60 horizon?

It does **not** answer whether the underlying moved correctly, whether the option could have been filled at the displayed quote, whether a package was profitable, whether another strike would have worked better, or whether the candidate should have been traded.

The existing episode/campaign outcome ledgers intentionally keep option P&L unavailable. That remains correct until an exact-option ruler is both registered and implemented under the existing outcome owner.

## 2. Reuse versus separation

The repository already contains private exact-contract NBBO machinery in `engine/options_nbbo_cohort.py`. OA-3 should reuse only the mechanics that are genuinely generic:

- exact OCC contract identity validation;
- firm OPRA quote-condition filtering;
- known-exchange filtering;
- exact tick quote timestamps;
- first qualifying quote selection;
- raw private source-response receipts;
- ask-in / bid-out arithmetic;
- the frozen research fee convention of USD 0.65 per contract per side;
- all-false research authority.

OA-3 must **not** inherit the MomoEdge benchmark's:

- `cohort_rule_id`;
- benchmark digest or benchmark freeze;
- producer/capture registries;
- same-window two-system coverage;
- competitor-session denominator;
- trigger-boundary semantics;
- 600-second live-capture availability fence;
- completion/surpass gates.

Those are benchmark policy, not generic quote mechanics.

In particular, `build_observation()` and `source_query()` from the benchmark implementation are **not** OA-3 contracts. They bind a live request clock to the event session and can start quote selection at an immutable trigger that predates source availability. OA-3 needs a dedicated wrapper around the reusable exact-contract/quote parser so historical retrieval after maturity does not change the frozen quote-event window.

## 3. Population: one independently frozen long single-leg expression

OA-3 v1 admits only an expression receipt that was frozen by a separately governed upstream owner **before any OA-3 outcome source is read**.

The receipt must identify at minimum:

- stable expression id and policy version;
- source candidate id / decision receipt;
- exact root;
- exact OCC symbol;
- expiration;
- call/put right;
- canonical strike and millistrike;
- long position;
- quantity = one contract;
- standard multiplier = 100;
- standard, non-adjusted deliverable;
- `decision_at`;
- `available_at`;
- source/rule digests needed to replay the expression selection.

OA-3 does not choose the option. It only measures an already-frozen expression.

V1 excludes:

- same-day expiration;
- adjusted/non-standard deliverables;
- non-100 multipliers;
- short option positions;
- spreads/packages/multi-leg structures;
- expressions whose exact identity cannot be replayed;
- expressions selected after any OA-3 outcome quote was inspected.

An excluded row remains visible in population accounting with its reason. It may not be silently dropped and later replaced by another contract.

## 4. Prospective fence

This document and machine policy do not retroactively authorize outcome audition.

The v1 ruler becomes eligible only after all of the following are true:

1. this exact preregistration has landed on canonical `main`;
2. the separately governed OA expression-selection contract is accepted and active;
3. the implementation records a durable OA-3 activation receipt;
4. the expression itself is first formed after both the expression-policy fence and OA-3 activation boundary.

Pre-fence expressions may be used for code-path diagnostics only. They can never become v1 research outcomes by being observed later.

If the implementation contract or ruler changes after outcomes are inspected, a new version and new forward fence are required.

## 5. Entry clock: actual expression availability, never a backdated trigger

The entry boundary is exactly:

```text
entry_boundary = expression.available_at
```

It is **not**:

- the raw tape print time;
- campaign `formed_at`;
- candidate source time;
- candidate `decision_at` when later than the expression;
- a model's conceptual trigger;
- the first historical quote that would have been attractive before the expression was available.

The eligible entry quote-event window is:

```text
[expression.available_at, expression.available_at + 60 seconds]
```

Select the first valid firm OPRA **ask** for the exact contract inside that closed event-time window.

If no qualifying ask exists in the window, the outcome becomes `unavailable / ENTRY_QUOTE_UNAVAILABLE` after the window is mature. Do not widen the window.

The admitted entry quote's own event timestamp becomes the realized ruler start:

```text
entry_at = entry_quote.event_at
entry_price = entry_quote.ask
```

## 6. Exit clock: fixed H+60 from the admitted entry quote

The target is:

```text
exit_target = entry_quote.event_at + 60 minutes
```

The eligible exit quote-event window is:

```text
[exit_target, exit_target + 60 seconds]
```

Select the first valid firm OPRA **bid** for the exact contract inside that closed event-time window.

If no qualifying bid exists, the outcome becomes `unavailable / EXIT_QUOTE_UNAVAILABLE`.

The horizon is not reset by a later signal, later campaign revision, target hit, stop hit, EOD, a better quote, or any hindsight condition.

## 7. Session and maturity law

Both entry and exit windows must lie inside the same canonical NYSE RTH session.

If `exit_target + 60 seconds` reaches or crosses the scheduled session close, the expression is outside the v1 H+60 domain and receives `excluded / HORIZON_CROSSES_SESSION_CLOSE`.

Premarket, post-close and non-session boundaries are outside v1.

The outcome is not mature until the entire required quote-event window has elapsed. Before that it is `pending`.

Historical quote retrieval may occur later than maturity. That later retrieval does not move the entry or exit event-time windows. Record retrieval/request/response/computed clocks honestly and separately.

This differs deliberately from the benchmark cohort's live-capture requirement that a selected quote become available within 600 seconds. OA-3 is an outcome measurement lane, not a claim that a research system saw or could have acted on the quote within ten minutes.

## 8. Exact quote law

Use the existing licensed ThetaData option-history quote endpoint:

```text
/v3/option/history/quote
interval=tick
```

The source query must bind the exact root, expiration, strike, right, session date, and frozen start/end event-time window.

A quote is eligible only when the relevant side:

- is strictly positive;
- has displayed size >= 1 contract;
- carries a firm condition accepted by the existing frozen OPRA condition vocabulary;
- carries a known exchange code accepted by the existing quote mechanics;
- belongs to the exact expression contract;
- falls inside the exact frozen quote-event window.

Conflicting exact-timestamp quote rows fail closed.

Retain a private receipt for the exact source response bytes and the exact query. Public/committed outcome records may carry hashes, sizes, identities and derived ruler values, but must not publish licensed raw quote rows unless separate rights law explicitly permits it.

## 9. Return arithmetic

For v1:

- quantity = 1 contract;
- multiplier = 100;
- entry = ask;
- exit = bid;
- frozen research fee = USD 0.65 per side.

```text
entry_cost = 100 * entry_ask + 0.65
exit_value_net = 100 * exit_bid - 0.65

net_return_pct =
  100 * (exit_value_net - entry_cost) / entry_cost
```

This is a **quote-ruler estimate**, not an execution or fill claim.

The bid/ask basis already includes spread crossing. V1 does not invent extra slippage, price improvement, account-specific commissions, exchange fees, taxes, or assignment costs. Therefore product copy must call it a frozen research quote ruler, not realized account P&L.

A later cost model requires a new policy version.

## 10. No substitutes

If the exact quote ruler cannot be computed, it stays unavailable.

The following may not substitute:

- midpoint;
- last trade;
- EOD mark;
- underlying return;
- intrinsic value;
- Black-Scholes/theoretical value;
- a neighboring strike or expiration;
- a later "best" print;
- a campaign premium average;
- a Prophet current mark;
- a synthetic reconstructed fill.

No best-strike, best-expiry or best-window search is authorized.

## 11. Status and denominator law

Every eligible expression has exactly one current OA-3 state:

### `pending`

The required entry or exit window has not matured yet.

### `complete`

Both exact quote observations exist and the frozen arithmetic is reproducible.

### `unavailable`

The expression is in the v1 domain, the required window matured, but the exact quote measurement is absent or source retrieval cannot lawfully establish it.

Canonical examples include:

- `ENTRY_QUOTE_UNAVAILABLE`;
- `EXIT_QUOTE_UNAVAILABLE`;
- `SOURCE_UNAVAILABLE`;
- `QUOTE_RESPONSE_INVALID`.

Unavailable expressions remain in the eligible denominator.

### `excluded`

The expression was frozen prospectively but is outside the declared v1 measurement domain, for example:

- `SAME_DAY_EXPIRATION`;
- `NON_STANDARD_DELIVERABLE`;
- `NON_STANDARD_MULTIPLIER`;
- `PACKAGE_NOT_SUPPORTED`;
- `SHORT_OPTION_NOT_SUPPORTED`;
- `HORIZON_CROSSES_SESSION_CLOSE`.

Excluded rows remain in population/accounting reports but are not part of the eligible-return denominator.

### `invalid`

A supposedly eligible record violates immutable identity, clock, receipt, source or correction law. Invalid is a data-integrity state, not a zero return.

No status may be silently deleted from denominators.

## 12. Corrections

Original expression identity and decision clocks are immutable.

If a source correction or contract correction arrives later:

- preserve the original outcome receipt;
- append/version the correction under the existing outcome owner;
- record what source identity changed and when it became available;
- never rewrite the original expression to a more favorable contract;
- never move `expression.available_at` backward;
- never turn an originally unavailable quote into evidence that the system had an earlier actionable fill.

A corrected outcome may be used only under the correction policy of the later evaluation that consumes it.

## 13. Corporate actions, exercise, assignment and expiry

V1 intentionally chooses a domain that avoids unsupported accounting complexity.

An eligible expression must be a standard 100-multiplier, standard-deliverable long option and must not be same-day expiration.

V1 measures only the H+60 quote-ruler window. It does not model:

- early exercise;
- assignment;
- exercise-by-exception;
- physical settlement;
- adjusted deliverables;
- cash-settled index multipliers;
- borrow;
- pin risk.

If the exact contract becomes non-standard or otherwise cannot satisfy the frozen domain before the exit ruler is measured, fail closed under an explicit excluded/invalid reason rather than inventing economics.

A later expiry/assignment or package accounting ruler is a separate version.

## 14. Package accounting is not v1

Package economics cannot be formed by adding leg percentage returns.

A later package ruler must independently freeze:

- complete leg identity;
- orientation (long/short);
- quantities/ratios;
- multipliers/deliverables;
- entry and exit quote rules for every leg;
- capital denominator;
- costs;
- missing-leg law;
- assignment/expiry handling.

Until that exists, OA package outcome is `unavailable`. The single-leg v1 ruler may not be relabeled as package P&L.

## 15. No MFE/MAE claim in v1

V1 freezes terminal H+60 quote return only.

It does not report option MFE or MAE. Those require a separately registered continuous quote-path ruler, path completeness law, halt/crossed-market handling and cost interpretation. The current underlying MFE/MAE fields do not substitute.

## 16. Authority ceiling

Every OA-3 v1 outcome is research-only. It cannot:

- originate or select an expression;
- score or rank candidates;
- create an Options Issue Desk issue;
- size or trade;
- publish a pick;
- train Prophet;
- feed Neural Web;
- claim an executable fill;
- prove a strategy edge by itself.

Statistical acceptance and any product/decision authority remain later governed gates.

## 17. Implementation acceptance tests

Before activation, the implementation must prove at least:

1. Exact expression identity is immutable and selected before outcome access.
2. Entry cannot use any quote with event time before `expression.available_at`.
3. The first valid ask inside the 60-second entry window wins even when a better later ask exists.
4. No entry ask inside the fixed window -> unavailable; the window does not expand.
5. Exit target is exactly 60 minutes after the admitted entry quote, not expression time.
6. The first valid bid inside the 60-second exit window wins even when a better later bid exists.
7. No exit bid inside the fixed window -> unavailable.
8. A same-day-expiry expression is excluded before outcome arithmetic.
9. An H+60 window that crosses the NYSE close is excluded.
10. Premarket/post-close/non-session expressions cannot become complete.
11. Mid, last, EOD, intrinsic, theoretical value, neighboring contract and underlying return cannot fill a missing quote.
12. A conflicting same-timestamp quote response fails closed.
13. Exact raw-response/query receipts bind the derived observations.
14. Delayed historical retrieval does not move either frozen quote-event window.
15. The benchmark cohort's 600-second live availability fence is not imported as an OA-3 outcome criterion.
16. One-contract USD 0.65-per-side arithmetic matches the frozen formula exactly.
17. Missing quote outcomes remain in the eligible denominator.
18. Later corrections append/version and never rewrite the original expression or clock.
19. Package/short/non-standard expressions cannot silently fall through the long-single-leg path.
20. Every authority flag remains false and no output claims an actual fill.

Mutation/falsifier tests should demonstrate that the temporal, contract and substitution fences are load-bearing.

## 18. Implementation boundary

This preregistration does **not** authorize implementation by itself.

Before a source-writing implementation starts:

- OA-1C/candidate and exact-expression selection contracts must be accepted;
- the current episode/campaign outcome integrity and publication lane must be accepted;
- current quote-source rights and source custody must be verified;
- active path collisions must be reconciled;
- the existing outcome owner must return the exact write/test allowlist.

Implementation should reuse the existing outcome identity/publication owner and the generic quote parser/mechanics where lawful. It must not create:

- a second outcome ledger;
- a second options quote store;
- a second scheduler;
- a second candidate identity;
- a competitor-benchmark-derived OA lifecycle.

## 19. Completion boundary

Landing this registration means only that the OA-3 ruler is frozen.

OA-3 becomes product-capable only after a later admitted implementation proves, on a real prospectively frozen exact expression:

```text
candidate/expression receipt
-> exact entry ask or explicit unavailability
-> fixed H+60 maturation
-> exact exit bid or explicit unavailability
-> immutable existing-owner outcome
-> actual current consumer
```

with source, decision, quote-event, retrieval, outcome-availability and publication clocks kept distinct.

A real `unavailable` result is acceptable proof of the negative path. A complete return is not required to manufacture progress.
