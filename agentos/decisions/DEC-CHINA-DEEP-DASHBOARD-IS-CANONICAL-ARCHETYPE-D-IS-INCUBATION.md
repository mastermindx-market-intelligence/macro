---
key: CHINA-DEEP-DASHBOARD-IS-CANONICAL-ARCHETYPE-D-IS-INCUBATION
question: >
  Which China macro dashboard composition is the production default after the
  September 2026 Archetype-D migration?
answer: >
  The pre-#7054 deep China macro dashboard is the canonical published default.
  Archetype-D remains preserved as an incubation concept and evidence set, but it
  is not approved to replace the production composition until it is separately
  matured and explicitly accepted.
rationale: >
  Chairman direction on 2026-09-19 judged the older dashboard materially better
  and more deeply useful. The Archetype-D migration reduced the production page
  too aggressively before the replacement had reached equivalent product depth.
  Restoring the deep composition preserves the richer user job while keeping the
  newer concept available for later development instead of deleting its history.
alternatives:
  - option: Keep Archetype-D as the production default and iterate forward.
    why_not: >
      Rejected by the Chairman for the current production surface: the replacement
      was not mature enough and removed too much useful dashboard depth.
  - option: Delete Archetype-D and its evidence entirely.
    why_not: >
      Unnecessary. The idea remains useful as an incubation reference and can be
      revisited under a future explicit product decision.
evidence:
  - "Chairman live direction, 2026-09-19: restore the old China macro dashboard; the old one is the de facto winner; keep the new one only as an idea because it is not mature enough to be published."
  - "macro PR #7456, merge ef5fb6bd5759218788fa0b29c9d25d59b9bf0343: restored the deep China macro template and repurposed the publication contract to pin the deep composition."
  - "macro PR #7463, merge 01896d6da34d67df45056dd82795be6c8cbf187e: made site-only China rerenders truly offline and committed the restored site/china.html artifact so VPS publication no longer depends on the clogged render lane."
  - "Production proof after #7463: /opt/macro/site/china.html and /opt/macro/site.served/china.html were byte-identical SHA-256 dfbdb24da50683e0275ecd4b9660b8258aed84ddce039f842f4431bf28d449a1; cache-busted https://www.mastermind-x.com/china.html returned HTTP 200 with the same SHA and the deep ROW 4, Market Sentiment, Policy Monitor, Connect Flows and Macro News present while Archetype-D Four Drivers/L1-4 markers were absent."
  - "Headless Chrome DOM proof after merge independently confirmed the deep markers and absence of the Archetype-D production markers."
  - "Chairman live direction, 2026-09-20: preserve the old design as the skeleton and selectively integrate what the newer design does better; a wholesale design wipe is acceptable only when the replacement is substantially better overall, not merely cleaner or newer."
affects:
  - "templates/china.html.j2"
  - "site/china.html"
  - "scripts/build_china.py"
  - "engine/china_news.py"
  - "tests/test_china_archetype_d_s1.py"
  - "mockups/evidence/china-archetype-d/*"
  - "macro PR #7054"
  - "macro PR #7456"
  - "macro PR #7463"
  - "macro PR #7485"
confidence: high
reversibility: easy
decided_by: chairman
decided_at: 2026-09-19
review_by: 2026-10-19
---

## Decision scope

This decision changes the **published China macro dashboard default**, not the
existence of the Archetype-D work. PR #7054 and its evidence remain legitimate
historical/incubation material. They must not be treated as current publication
authority.

The decision does not freeze every detail of the restored dashboard forever.
Normal quality, data, performance, accessibility, and UX improvements may continue
as long as they preserve or improve the current user capability rather than
silently reintroducing the rejected compression.

## Supersession

This record supersedes only the production-default implication of PR #7054
(`china.html -> Archetype-D regime_dashboard migration`). It does **not** erase:

- the implementation history of #7054;
- its design experiments or evidence;
- later China data/engine capabilities that are compatible with the restored
  dashboard;
- shared UI safety repairs that were retained during the restoration.

PR #7456 is the restoration source. PR #7463 is the release-path durability repair.

## Production truth

As of the accepted restoration:

- the deep dashboard is the real served `/china.html` path;
- the index face and multi-row deep racks are present;
- Market Sentiment, Policy Monitor, Connect Flows, Macro News, property, AI brief,
  alerts, and the major click-through dialogs remain first-class production
  capability;
- the Archetype-D six-block L1 compression is not the published default;
- the new concept remains recoverable in Git history/evidence for future iteration.

## Re-entry gate for Archetype-D

A future proposal to make Archetype-D (or a derivative compression) the production
default requires a new explicit product decision. Before that decision, it must
demonstrate at minimum:

1. substantial overall improvement on the user jobs currently served by the deep dashboard, not merely visual simplification or parity;
2. no silent loss of major intelligence surfaces or drill-down workflows;
3. current-data correctness and null/degradation behavior;
4. production-path browser evidence in both supported themes/languages and key
   viewport classes;
5. a migration plan that preserves the old production surface until the replacement
   is accepted.

A clean implementation, screenshots, or green CI alone do not satisfy that gate.

## Selective synthesis rule

The default evolution path is **synthesis, not replacement**. A newer concept may
contribute individual improvements — clearer glance copy, better action framing,
loading/null states, navigation, accessibility, mobile behavior, or other bounded
UX upgrades — while the accepted deep dashboard remains the information-architecture
skeleton.

A wholesale design wipe is a separate product decision. It requires evidence that
the replacement is **substantially better end-to-end** for the actual user job,
including depth, decision usefulness, drill-down workflow, current-data truth,
mobile/desktop behavior, and production proof. "Cleaner", "more modern", fewer
modules, or a successful screenshot review is not sufficient evidence.

When a bounded idea from an incubation design is useful, transplant that capability
into the canonical surface first. Do not use the presence of a promising component
as justification to delete unrelated accepted capability.

## Do not redo

Do not restore the Archetype-D six-block composition to production merely because
#7054 exists, because an old migration test names it, or because the concept is
visually cleaner. Do not delete #7054 or its evidence either. Treat it as an
incubation branch of product thinking unless and until the Chairman explicitly
accepts a matured successor.

Do not rebuild another China publication path. The canonical source remains the
existing template/build/render/VPS path repaired by #7456 and #7463.
