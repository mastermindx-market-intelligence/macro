---
workstream: "WS:MARKET-OS"
session: claude/sol-homepage-research-entry-20260910
model: sol
ended_because: ci_handoff
mission: Deliver a readable homepage research example and preserve the company context when a visitor opens the product.
state_before: The homepage used the original hero and dashboard collage. Mobile repair PR 7026 was a separate delivery.
changed:
  - path: templates/index.html
    what: Bilingual outcome-led hero, dated company example, anchored dossier links and explicit demonstration labels; paired with site/index.html.
  - path: templates/landing.css
    what: Responsive research-example layout and cache updates for every landing-family consumer; paired site stylesheet.
  - path: data/marketing/ad_central/
    what: New planned shadow creative identities through the existing owner; no active experiment or spend.
  - path: tests/test_landing_research_entry.py
    what: Seven acceptance checks, included in the existing navigation test job.
verified:
  - claim: The research-entry implementation exists in the composed source.
    command: git rev-parse HEAD
    result: 1f3806e6170e23655e6e0edfd7f857acc9c0aca3, after source e09fed8f8992b37b82cbd9a410990e7107a75ed0 and mobile repair 10bb93a46e94855ca9338d3bff9c1624284c3213.
  - claim: Combined regression and artifact-parity checks pass.
    command: pytest research-entry, mobile-reflow, navigation, public-chrome, pricing-CTA and Ad Central suites; check_template_site_sync.py
    result: 148 passed; 98 pairs agree. The new research tests initially failed all seven cases before implementation.
  - claim: The local visitor journey preserves the company and section.
    command: check_research_journey.py
    result: Three actual browser clicks reached visible AAPL financials, valuation and why sections; keyboard disclosure passed; no page exceptions. This is not production proof.
unverified:
  - claim: Production acceptance and improved conversion.
    what_would_verify: Independent review, current-base CI, normal approved release, deployed browser journey and reliable cohort measurements. No conversion lift is claimed.
unresolved:
  - The page is locally built, not production-proven. Feature regrouping, commercial consistency and signup simplification remain owed.
  - Existing acquisition-truth PR 6842 and logo PR 6988 remain separately owned.
next_actions:
  - Inspect the final canonical browser matrix and source-bound screenshots, publish this same branch as a draft stacked on PR 7026, then obtain an independent exact-head review.
  - Reconcile existing freshness and logo work without duplicating its implementation or taking another writer's checkout.
  - Continue commercial consistency and the complete visitor-to-product journey after this first useful vertical.
do_not_redo:
  - Do not relabel the historical example as current data, a generated assistant response or a recommendation.
  - Do not modify historical creative identities or activate the shadow experiment as part of a copy release.
  - Do not treat a local screenshot, draft PR or green test as production acceptance.
danger_areas:
  - All seven landing-family HTML consumers must use the final stylesheet hash. Composition required explicit cache-stamp resolution, not an ancestry-only merge.
  - The two demonstration-label changes overlap a small part of PR 6842; its source-derived preview and staleness machinery still belong to that existing carrier.
  - The static evidence server reports a billing endpoint 404 and does not prove a live offer.
---

This record supersedes the earlier uncommitted preimplementation note. The initial tool-side write failure produced no fragment; subsequent bounded source operations built the implementation and passed the stated tests. The broader homepage program remains unfinished.
