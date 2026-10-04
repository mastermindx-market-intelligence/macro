# Cross-Session Source Timing Census Specification — Freeze 0

Date: 2026-09-25
State: SOURCE_DENOMINATOR_FREEZE / RESEARCH_ONLY / OUTCOME_BLIND
Operation family: geopolitical-relief-event-study-20260924-sol-001
Carrier: Macro PR #8012 / sol/geopolitical-relief-event-study-20260924
Parent: research/CROSS_SESSION_NARRATIVE_HANDOFF_PREREG_2026-09-25.md

## 1. Fixed research window

Primary census window:

- start: 2026-06-14T00:00:00Z
- end: 2026-09-24T23:59:59Z

The window is frozen before the timing-frequency count is computed.

Rationale:
- it covers the already-studied June-through-September U.S.-Iran/Hormuz narrative cycle;
- it includes relief, implementation, breakdown, escalation and rumor/denial phases;
- it ends before this preregistration/census work on September 25.

No earlier/later event may be added to the primary timing statistic after its direction or
market response is inspected. A later expanded era requires a new version.

## 2. Primary dissemination family

Primary timing denominator = Newsquawk live headline records with a recoverable exact
publication timestamp inside the fixed window.

Why this family:
- exact market-feed publication clocks are usually exposed;
- the same dissemination family can carry official quotes, Reuters relays, local-media
  relays, escalation, relief, implementation and denial;
- it avoids mixing article-page timestamps with live-feed ticks.

The original claim origin remains a separate field. Newsquawk dissemination does not turn
a secondary report into an official claim.

## 3. Topic admission

A cluster enters the primary source census when its headline is materially about at least
one of:

- U.S.-Iran military conflict / ceasefire / negotiations;
- Strait of Hormuz closure, reopening, navigation, blockade, mine, vessel attack, escort,
  toll, revenue, or transit terms;
- sanctions/blockade relief directly tied to the conflict;
- official or mediator implementation of an agreement affecting the above.

Generic Iran domestic politics, unrelated nuclear commentary, historical retrospectives,
or market-only recaps without a new geopolitical fact are excluded.

## 4. Direction labels

Assign from source text only:

- relief
- escalation
- denial_or_breakdown
- implementation_relief
- implementation_escalation
- mixed_conflict
- neutral_process

Do not use subsequent oil/equity returns to label direction.

## 5. Materiality rule

A headline is material when a reasonable market participant could update one of:
- conflict intensity;
- probability/timing of ceasefire or agreement;
- Hormuz physical accessibility;
- blockade/sanctions constraints;
- shipping/vessel safety;
- implementation timing;
- military strike probability.

Pure repetition with no new information is clustered rather than counted again.

## 6. Event clustering

Cluster materially identical claims within six hours.

Keep a later item separate only if it changes:
- agreement/negotiation stage;
- physical implementation;
- named-party confirmation;
- operational terms;
- conflict intensity;
- contradiction/denial status.

Article count, repost count and quote count are never independent observations.

## 7. Retrieval protocol

To reduce search-engine/index bias, retrieval is partitioned before inspection.

For each calendar month in the fixed window, search the primary source family using:
- Iran
- Hormuz
- ceasefire
- deal / agreement
- talks / negotiations
- blockade
- shipping / vessel
- strike / attack
- mine
- reopen / open / close / closure

Search results are de-duplicated by canonical Newsquawk headline URL and then clustered by
material information.

A candidate found through one keyword is retained even if it would not have been found by
the others.

Coverage fields:
- search_partition;
- canonical_url;
- exact published timestamp;
- retrieval query/family;
- source-origin class;
- whether the canonical page was directly recoverable.

If the retrieval mechanism cannot establish that all relevant Newsquawk headlines were
enumerated, census_coverage must be labeled **retrieval_incomplete** and no frequency test
may be described as exhaustive.

## 8. Timing statistic eligibility

Primary timing-frequency analysis requires:
- exact Newsquawk publication timestamp;
- source-side direction label;
- independent event-cluster identity;
- no unresolved timestamp conflict.

Price data are not required.

Regional market-open labels are added only from admitted calendar owners. Missing HK/JP
calendar authority remains unknown rather than inferred from weekday/hour.

A secondary exploratory sensitivity may use fixed local session hours, but it must be
labeled advisory and may not replace the calendar-clean primary analysis.

## 9. Anti-motive law

The timing test estimates a distribution of publication clocks.

It does NOT estimate:
- intent to manipulate;
- intent to target Asian investors;
- whether officials delayed a statement for market effect;
- whether a newsroom coordinated with policymakers.

Any observed after-Asia-close concentration must be compared with source geography,
Washington/New York work hours, negotiation chronology, and negative/escalatory headline
timing before causal interpretations are discussed.

## 10. Outcome firewall

During source census construction:
- do not fetch event-window returns;
- do not select events because a price reaction is known;
- do not remove a source-clean event because its later market response is inconvenient;
- existing previously inspected pilot/training events retain their known status but do not
  influence admission of new source rows.

## 11. Completion test

Freeze 0 is complete only when:
1. monthly retrieval partitions have been executed;
2. every retained canonical URL is de-duplicated;
3. six-hour information clusters are assigned;
4. coverage status is declared;
5. direction/taxonomy labels are frozen;
6. no timing-frequency statistic has yet been used to change the corpus.

Only then may the after-Asia-close frequency analysis run.
