---
key: SOVEREIGN-AUCTION-CALENDAR-TRANSPORT-GAP
claim: >
  At Macro 8a35d8b62494a84b2448182aaa561edea83fe54f and Mastermind
  c7e47c859eb2925c5626931fd511800773ba09ac, event_calendar.json has no
  Git delivery: site/feeds is ignored, daily builds after its output commit,
  the Macro updater has no feeds hydration and Mastermind's R2 leg mirrors stockdata only.
falsifier: >
  Show a tracked event_calendar.json, an effective feeds hydration step in the cited
  updater/refresh revisions, or a different actual selected consumer transport at those pins.
so_what: >
  A successful isolated consumer fixture cannot establish publication readiness. Use the
  same existing calendar artifact, admit that one file to Git and build it before the
  existing output commit; verify identical bytes and separately verify deployed entitled reads.
kind: architecture
verified_at: 2026-10-08
verified_by: >
  research/sovereign_auction_pressure/publication_audit/SOURCE_MANIFEST.json,
  TRANSPORT_SOURCE_RECEIPT.json and PUBLICATION_AND_ENTITLEMENT_AUDIT.md;
  git ls-tree at Macro 8a35d8b and inspected exact updater/refresh source.
scope:
  - WS:RATES-INFLATION-COMMAND
  - macro/site/feeds/event_calendar.json
  - macro/.github/workflows/daily.yml
  - Mastermind/data_layer/macro_refresh.py
confidence: verified
---

The same audit establishes that Macro's existing default-deny asset route applies
registration and staged `site_full` entitlement to this path. An anonymous 401 at
2026-10-08 23:18:35 UTC proves the registration refusal only; it cannot prove a file
exists behind that gate or that an entitled caller receives it.

The held source bridge changes no Caddy, deployment updater, refresh service, paywall
switch or Terminal tier rule. A local byte-copy test models delivery, not deployment.
