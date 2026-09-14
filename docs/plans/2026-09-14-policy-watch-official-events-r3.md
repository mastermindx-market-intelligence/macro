# Policy Watch Official Events R3 — implementation and release plan

## Outcome

Give a Policy Watch reader one compact, source-backed view of recent official policy events that are worth opening now, without asking them to inspect the Europe event parquet files or confusing discovery items with the deterministic policy lifecycle.

The useful end state is:

1. recent, specific, rights-safe official events appear inside the existing **Policy stages** section;
2. publisher date, first-seen/collection time, and source-coverage check time remain visibly separate;
3. delayed, stale, missing, and outage states stay explicit;
4. the existing lifecycle, R1 current-source panel, R2 analysis clock, UK desk, seven-section composition, and 44-call ledger remain intact;
5. no event, score, rank, forecast, sizing instruction, or trade authority is created.

## Existing authority and no-rebuild boundary

This is a read-only consumer of the existing `engine.europe_news_intel` producer and its canonical artifacts:

- `data/europe_news_vector/events.parquet`
- `data/europe_news_vector/coverage.parquet`

The producer already owns source configuration, event identity, point-in-time `first_seen_utc`, publisher timestamps, rights state, coverage state, and the qbus append path. R3 must not create another collector, event database, queue, calendar, identity scheme, correction ledger, scheduler, or publication plane.

The policy lifecycle remains owned by `engine.policy_intent_desk` and `engine.transmission_chains`. A discovery item cannot mint or advance a lifecycle stage.

## User job

Answer four questions quickly:

- What official policy event changed recently?
- Which institution published it?
- When did the institution publish it, and when did Mastermind first collect it?
- Is current source coverage healthy enough to call the feed current?

The source title remains the source title. In Chinese mode it is labelled **原文标题** rather than silently machine-translated.

## Machine job

`engine.policy_watch_current.build_policy_event_feed(root, now)` composes a bounded display view:

- only configured sources with `VERIFIED_PUBLIC_REUSE` rights;
- only exact HTTPS URLs on each source's configured host;
- only `PUBLISHER_STATED` timestamps;
- only specific policy themes: competition/antitrust, financial stability, fiscal, monetary, regulatory, and trade policy;
- only non-future events first known no later than `now` and published within the prior 14 days;
- at most six rows, deterministically ordered;
- at most 5,000 rows and 16 MiB per input artifact;
- no writes, network calls, model calls, or hidden fallback timestamps.

## Clock and null contract

Three clocks remain distinct:

1. `source_date` / `published_at` — what the publisher states;
2. `known_at` — the existing point-in-time first-seen clock;
3. `coverage_checked_at` — when source coverage was last checked.

Coverage older than 36 hours is `stale`, never current. A verified source outage may retain saved dated items, but `fresh` remains false. Missing or unreadable artifacts are `unavailable`. A healthy check with no focused rows is `no_recent_events`, not an outage.

Rights-excluded source rows do not influence health, item selection, or displayed source chips.

## UI contract

The feed is a component inside the existing `#policy` section, not a new L1 section. It renders:

- a compact typed state badge and one non-duplicated explanation;
- source-original event titles;
- bilingual theme, publisher, date, and clock labels;
- direct official-source links;
- per-source coverage chips;
- the sentence: **Discovery only — not a lifecycle stage or market signal.**

Raw machine values such as `trade_policy`, `DELAYED_SOURCE`, and `SOURCE_OUTAGE` may appear only in data attributes or internal receipts, never in visible copy.

## Test-first implementation order

1. RED: no Policy Watch consumer exists for Europe artifacts.
2. GREEN: add the read-only typed composer.
3. RED/GREEN: exact rights, time, URL, source-health, stale/outage, no-coverage, and read-only tests.
4. RED/GREEN: builder and page integration inside the existing policy section.
5. RED/GREEN: remove duplicate healthy copy, localize publishers, and disclose original titles.
6. RED/GREEN: refuse the legacy `Needs refresh` wording in the typed stale state.
7. Render real checked-in inputs, externalize CSS, capture desktop/mobile × EN/ZH × dark/light, and run exact DOM assertions.
8. Run repository gates, current-main integration, independent review, hosted CI, normal merge/publication, and canonical public proof.

## Acceptance

Source-ready acceptance requires:

- full relevant tests green;
- exact real-input render with four admitted events from current fixtures;
- one feed, four event cards, one healthy explanation;
- R2 analysis clock, current panel, UK desk, 44 calls, and seven L1 sections preserved;
- 8/8 browser states with correct localized clocks/publishers, no visible machine tokens, no errors, no failed requests, and no overflow;
- design, runtime-style, visual-evidence, template/site sync, Agent OS, Ruff fatal classes, compile, and diff checks green.

Production acceptance remains separate: exact-head CI, expected-head merge, normal render publication, live/main byte identity, and the same eight-cell browser contract on the canonical public URL.
