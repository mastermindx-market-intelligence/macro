---
key: TERMINAL-TACTICAL-BOUNDED-MINUTE-SEAM
claim: >
  At Macro main 79e3c06dc2eb874c197cf19f43ce90ee95ab9963, the committed Massive capability manifest records
  entitled stock minute aggregates, second aggregates, recent/historical trades and recent quotes plus an entitled
  real-time stock WebSocket, while engine/entry_radar/vendor_minutes.py is the existing bounded one-ticker/one-session
  minute reader and persists only derived completed-session 4H buckets rather than a general raw-minute archive.
falsifier: >
  Read data/massive/capability_manifest.json and engine/entry_radar/vendor_minutes.py at the pinned Macro revision.
  A non-entitled verdict for aggs_minute/aggs_second/trades/quotes, or a raw-minute durable cache/store in
  VendorMinuteReader, refutes the corresponding dated claim. A newer capability manifest is new evidence and must be
  reconciled rather than rewriting this receipt.
so_what: >
  Keep R1-B's primary causal clock at five minutes. If a later study needs to resolve same-bar target/adverse ordering
  or another enumerated ambiguous episode, extend/qualify the existing Radar minute-reader path under the current data
  owner instead of creating another minute warehouse. Current entitlement evidence does not by itself establish
  historical knowledge-time, corrections, live freshness or a reusable long-horizon one-minute research archive.
kind: architecture
verified_at: '2026-09-17'
verified_by: >
  Macro main 79e3c06dc2eb874c197cf19f43ce90ee95ab9963; capability_manifest read showed HTTP 200/nonempty
  aggs_minute, aggs_second, trades_recent, trades_2015, trades_2005, quotes_recent and entitled ws_stocks_realtime;
  vendor_minutes.py SHA256 ac1b77715a07ff04c983c5956225135d97531ba8ff2c440c97c6f400c7e93ea8.
scope:
- WS:TERMINAL-TACTICAL-INTELLIGENCE
- WS:LIVE-ENTRY-RADAR
- engine/entry_radar/vendor_minutes.py
- data/massive/capability_manifest.json
confidence: verified
---

This discovery is a source/capability boundary, not permission to call the provider, backfill a new plane, or publish raw data. The existing C3 cache is specifically a derived 4H bucket cache; it is not a substitute for point-in-time raw-minute research receipts.
