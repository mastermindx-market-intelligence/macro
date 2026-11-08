# Policy effective-date proof — 2026-11-08

## Scope and source

Parent assignment: [News Intelligence end-to-end completion, Macro #10244](https://github.com/mastermindx-market-intelligence/macro/pull/10244#issuecomment-6718847852).

Product and proof base: `8251e41bcb67cfd045b67501c47cf27fe06b1af2`.
Protected law pin: Mastermind `1981aea5122943ce59d7ebe9706ddf5a658b377d`.

This corrects the accepted V4 P1 defect in the existing Federal Register collector and policy calendar. The collector now requests and stores `effective_on`. The calendar selects the earliest valid future-or-today effective date from its existing `final_rule` population, independently of comment deadlines. The existing rationale chip includes the effective date and preserves both labels when deadlines fall on the same day.

## Discriminating evidence

With a fixed reference date of **2026-11-02**, the synthetic final rule's source values are:

| Fact | Source date | Calendar interval |
|---|---|---|
| Comment deadline | 2026-11-20 | 18 days |
| Rule effective date | 2026-12-15 | 43 days |

The regression exercises the actual mocked HTTP request, collector `fetch()`, Parquet write/read, calendar and chip. It proves both source fields survive, retain separate meanings and produce the two labels. It is synthetic offline evidence, not a live Federal Register response or authenticated production proof.

- **22 new regression cases fail against the original product source.**
- **All 64 tests** in `tests/test_federal_register.py` and `tests/test_policy_calendar.py` pass on the candidate (**1.71s**, local Python 3.12).
- V4 `p1_stage_states()` ran twice with both writer lanes unset. The identical output is **PROVEN**, with effective date `2026-12-15`, `proxy=False`, and visible countdown **43d**.
- The P1 predicate now also requires the displayed countdown to match the effective date. Its expected file changes only P1 and the V4 tally to **1 PROVEN / 3 PARTIAL / 1 ABSENT / 0 HUMAN_GATE**. The remaining V4 properties were not replayed locally; the existing hosted V91 job owns their full replay.
- The two existing unit modules previously belonged to the unrun backlog. The existing `news-v91-vertical-proofs` job now names both in its path scope and pytest command, and only their two grandfather-list entries are removed. No second test workflow is introduced.
- The incumbent CI weight calculation changes this logical job from **4 to 8**. No global packing ceiling is relaxed.

Two existing tests needed explicit isolation when enrolled: the ledger assertion enables the nightly lane only after redirecting its data directory; the cascade-stage test redirects its data directory and clears writer lanes.

## Review and limits

The active principal self-reviewed the product diff. A distinct native reasoning child reviewed the same local source, tests and P1 change and found no blocking correctness defect. That child did not run tests, mutate source, or submit a GitHub approval.

Historical tape rows remain first-write-wins. A newly fetched duplicate does not backfill an old missing effective date or rewrite `_first_seen`, `significant`, title or an existing effective date. Missing, malformed, wrong-type, compact, week-form and timestamp values remain unknown. The new date does not promote a proposal or interim-final row into `final_rule`.

Stage taxonomy, weights, latency, inflow, comment-only upcoming events and the nightly ledger gate are unchanged. This is a factual date correction; it changes no predictive score or trading authority.

Generated production artifacts require the normal collector/build path to refresh. No release, production output refresh, live effective-date coverage, authenticated consumer proof or complete V4 journey is claimed by this receipt.

