---
key: THE-PRODUCT-SERVES-ON-TWO-HOSTS-SO-A-525-ON-ONE-IS-NOT-A-PUBLICATION-FAILURE
claim: "The rendered product is served on two public hosts (www.mastermind-x.com and www.mastermindx.ai); an HTTP 525 / origin-TLS failure on one host is a domain/origin incident, not evidence about publication freshness, which is read on the healthy host."
falsifier: "Both hosts answer differently for the same path with the same Last-Modified, or the .com host serves bytes that never match origin/main's site/ after a successful render.yml run."
so_what: "PRODUCTION_PROOF reads (served sha256 == main, served needles) must try the healthy host before declaring the rung blocked; keep the 525 as its own incident routed to its owner (Chairman P0, #6819 comment 5950347675) and never infer .com publication state from .ai."
kind: runtime
verified_at: 2026-10-03
verified_by: "2026-10-03 06-07Z: curl www.mastermindx.ai -> 525 on every path and openssl s_client to the origin returned no certificate, while www.mastermind-x.com/sanctions_map.html, /research_screener.html and /stocks/AAPL.html answered 200 (Sol read 5966648222; CEO A reads for F00C rows MO-DELTA-002 / MO-PAID-059)"
scope:
  - "macro"
  - "WS:MARKET-OS"
confidence: verified
---

The seat spent most of a day stamping served checks "blocked by 525" when the .com host was healthy throughout. Read both hosts once per proof; attribute the failing one to the incident owner.
