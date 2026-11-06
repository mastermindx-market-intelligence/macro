---
key: NEWS-COCKPIT-ACKNOWLEDGEMENT-IS-NOT-CHANGE
claim: A successful acknowledgement of an already stored News source revision is not newly changed reporting, including after validator eviction or press-state loss.
falsifier: Run the replay and failed-publication recovery regressions in tests/test_research_news_intake.py; a replay that increments last_changed_item_count or advances accepted_revision_at disproves the corrected invariant.
so_what: Use the incumbent owner receipt's changed_item_count for change displays and keep accepted_item_count for idempotent acknowledgements; never infer new reporting from the daemon validator cache alone.
kind: landmine
verified_at: 2026-10-20
verified_by: "Macro PR #9612; pytest tests/test_research_news_intake.py tests/test_marketing_intelligence_desk.py; docs/evidence/news-cockpit-20261020-recovery/verification.json"
scope:
  - macro
  - engine/marketing/intelligence_desk.py
  - scripts/marketing_fastlane_daemon.py
confidence: verified
---

# Acknowledgement and changed reporting are different facts

The bounded validator map can forget a source identity that remains in the incumbent
IntelligenceStore. The former receipt counted its successful no-op replay as a changed
item. Recovery reproduced this after validator eviction and full press-state loss.
The correction retains current/superseded acknowledgement semantics and source clocks,
while counting unique actual stored changes in the existing transaction. Publication
still precedes external acknowledgement; a successful retry of a failed export does not
become a new source revision.

The root is `news-cockpit-rebuild-20261018-astra-01`, original Macro PR #9612. Current
implementation/evidence and the ordered release frontier remain in
`docs/NEWS_DESK_RELEASE.md` and that same PR. This discovery grants no execution,
source-writer, merge, entitlement, trade or deployment authority.

The semantic registry has no separate News cockpit workstream. Do not alias this
mission to `WS:PROPHET-NEWS-IMPACT`, which is a different programme.
