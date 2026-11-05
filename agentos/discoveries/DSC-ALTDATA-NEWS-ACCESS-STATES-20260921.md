---
key: ALTDATA-NEWS-ACCESS-STATES-20260921
claim: >
  On alt_data.html at macro main 1dc11fb3eb326393c803bc2eff408db89bb91bc1,
  three anonymous HTTP 401 news reads rendered a claim that the news surface
  was not built and would appear after the next daily build.
falsifier: >
  Read the public route anonymously and inspect the three unchanged news requests
  and #sid-news. A sign-in state rather than the not-built promise on that source
  disproves the observation. before.json and before.png retain the observed result.
so_what: >
  Preserve access, transport and successful-empty states separately in the existing
  news widget. A fallback market feed does not prove there is no related news when
  per-name data failed. Keep native retry focused while busy with aria-disabled
  plus the existing in-flight guard; native disabled was proven to blur the button.
kind: landmine
verified_at: 2026-09-21
verified_by: 'python3 -m pytest tests/test_altdata_price_truth.py -q'
scope:
  - 'mastermindx-market-intelligence/macro'
  - 'templates/alt_data.html.j2'
  - 'site/alt_data.html'
  - 'tests/test_altdata_price_truth.py'
confidence: verified
---

The bounded candidate does not widen access, change source data, rank names, or add
polling/automatic retries. Its local fixture results are not authenticated production
proof. Existing News PR #7591 remains a separate held writer; this discovery does not
transfer its source custody. The broader Web Chat UIUX programme remains incomplete.
