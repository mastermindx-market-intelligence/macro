# Mastermind AI China Freshness Repair — Design

## Incident

On 2026-09-13 Mastermind AI described 2026-09-09 as China's latest/last trading day even though mainland sessions completed on 2026-09-10 and 2026-09-11.

Production evidence shows two coupled defects:

1. `collectors.china_universe.ChinaUniverseAdapter.fetch()` aborted before price refresh when Sina membership lookup failed, even though committed `data/china_search/members.parquet` was a usable last-known-good universe. The Asia collector deliberately continued after one source failed, so downstream builders published mixed vintages.
2. `engine.neuralweb.market_packet._render_regional()` printed the China basket component's `as_of` as the regional board's “own session.” A component vintage is not an exchange-session fact, so the model turned `basket as_of=2026-09-09` into the false claim that 2026-09-09 was the last trading day.

## Outcome

Mastermind AI must distinguish four clocks:

- latest completed mainland exchange session;
- latest regional state date;
- latest basket/price-input date;
- sessions of lag between the component and the exchange clock.

A transient membership-source outage must not stop price refresh when a valid last-known-good universe exists. If the required broad China close store nevertheless remains behind the latest completed mainland session, the Asia collector must fail before the workflow commits or builds mixed-vintage China artifacts.

## Architecture

Extend existing canonical planes only:

- Reuse `data/china_search/members.parquet` as the last-known-good Sina universe; do not create another membership store.
- Reuse `lib.cn_calendar.expected_last_session` and `sessions_between`; do not create another calendar.
- Extend `scripts/check_tushare_freshness.py`, the existing China freshness module, with a binding health check for `data/china_search/closes.parquet`; do not create another freshness checker.
- Have `scripts.collect --group asia` evaluate that required-store postcondition only after every adapter and post-collect task has run. A stale/absent core store returns exit 3, so the existing workflow stops before its commit/build steps without any workflow-authority edit.
- Extend the existing Live Market State Packet with explicit exchange/state/component clocks and remove the ambiguous generic regional `as_of` alias.
- Add one epistemic gateway rule: a component `as_of` never establishes the market's last trading day.

## Behavior

### Cached-universe recovery

If live Sina membership succeeds, behavior is unchanged.

If live Sina membership fails and `members.parquet` contains a sufficiently wide, well-shaped prior universe, the collector:

- emits a line-start GitHub warning;
- reconstructs the live membership shape from the prior table;
- continues the normal CSI-extra/config-extra union and Yahoo close refresh;
- rewrites the enriched full members table, avoiding a reduced-cache ratchet;
- preserves live price freshness while disclosing membership degradation.

The cache must carry valid A-share tickers, `name_zh`, numeric `mktcap_yi`, and at least 75% of the configured universe width. If no usable cache exists, the collector still fails. It never invents membership.

### Required Asia postcondition

`scripts.check_tushare_freshness.check_china_search_core()` compares the newest index date in `data/china_search/closes.parquet` with the latest completed mainland session from `lib.cn_calendar`.

- current store: return 0;
- store ahead of the completed-session clock: warn and return 0 (newer cannot mean a missing completed session);
- absent, unreadable, or one-plus completed sessions behind: emit a line-start error and return 3.

`scripts.collect.main()` runs this postcondition only for `--group asia`, after all collection/status/tail work. Other groups retain their historical exit contract. The existing `--skip-quality` flag is the explicit maintenance escape hatch: it emits a loud BYPASS annotation and is not production proof. A deliberately partial Asia `--only` run that excludes `china_universe` is likewise exempt because it cannot repair that plane. The production workflow uses neither escape. The existing Tushare flow-store tripwire remains advisory.

### Chatbot provenance

For the incident shape—China state through 2026-09-11 and basket inputs through 2026-09-09—the packet renders:

`latest completed session 2026-09-11; state through 2026-09-11; basket inputs through 2026-09-09, 2 sessions behind`

It must never render `CN (2026-09-09)` as though that component date were a session stamp. Missing artifacts remain explicit gaps. If the calendar is unavailable, the packet still labels state and component dates and says `exchange session unavailable`; it never falls back to a bare date. If China content has no valid state or component date, the packet says `content vintage unknown` beside the exchange clock. HK/Canada component dates are also labeled as component inputs, without changing their source data or authority.

## Non-goals

- No new signal, rank, score, sizing, gate, or trading authority.
- No change to historical factor methodology.
- No fabrication of missing September 10/11 cross-sectional values.
- No duplicate calendar, retry plane, membership store, workflow step, or freshness control plane.
