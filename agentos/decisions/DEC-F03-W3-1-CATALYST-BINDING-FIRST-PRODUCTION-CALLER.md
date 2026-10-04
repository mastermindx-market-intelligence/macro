---
key: F03-W3-1-CATALYST-BINDING-FIRST-PRODUCTION-CALLER
question: >
  Where should the first production call to bind_events live, so a nightly
  can measure how often live-flow events bind to a catalyst?
answer: >
  A nightly builder, scripts/build_options_catalyst_links.py, is the first
  production caller. It binds the session's events to one earnings candidate
  per root and to FOMC dates on the shared calendar, and it writes a
  context-only histogram under site/options_catalyst_links/. The options page
  is a later packet. Every authority flag stays false.
rationale: >
  engine/options_catalyst_link.py already reduces identity, then expiry, then
  catalyst, and it had no production caller. The episode step already reads
  the date-keyed events stage, so this builder reuses that read instead of
  opening a second client. Earnings staleness follows fields_from_assessment:
  stale false is fresh only when an age is present. FOMC dates come from one
  new pure accessor on the existing calendar. The artifact carries the
  binding-state histogram and not a rank, a size, or a trade. The page that
  would display the links waits until the seat has read three nightlies.
alternatives:
  - option: Bind at render time inside build_options_command
    why_not: >
      That couples an R2 read into the render budget. The histogram would
      be recomputed on every page build instead of once per session.
  - option: A store-host producer
    why_not: >
      No chain frame is needed. The inputs are the events stage, the earnings
      assessment, and the FOMC calendar. A store host would add a machine
      this packet does not use.
  - option: Defer macro catalysts
    why_not: >
      FOMC is the dominant ETF catalyst, and adding it costs one pure
      accessor over the calendar the engine already imports.
evidence:
  - "engine/options_catalyst_link.py bind_events is the only binder. Before
    this packet its only importer was tests/test_options_catalyst_link.py."
  - "scripts/build_options_catalyst_links.py calls fetch_event_stage and
    bind_events. It does not construct an R2 client."
  - "engine/event_calendar.py fomc_decision_dates reads _FOMC and returns
    the dates inside the window, sorted."
  - "python3 -m pytest tests/test_build_options_catalyst_links.py
    tests/test_options_catalyst_link.py
    tests/test_options_catalyst_links_nightly_shape.py -q → 58 passed in 1.85s."
  - "A Friday earnings row is age 1 on Saturday and on Labor Day. The stamp
    is Friday. A Thursday event is excluded and the FOMC date wins."
  - "The nightly site commit still stages site/ with the existing git add.
    .github/workflows/daily.yml comment says git add site/ covers, and
    scripts/ci/daily_engine_commit_outputs.sh runs git add data/ site/ reports/."
affects:
  - "scripts/build_options_catalyst_links.py"
  - "engine/event_calendar.py"
  - ".github/workflows/daily.yml"
  - ".github/ci/legacy-jobs.yml"
  - "tests/test_build_options_catalyst_links.py"
  - "tests/test_options_catalyst_links_nightly_shape.py"
confidence: high
reversibility: easy
decided_by: "META-CEO A seat, packet A-F03-W3-1a, 2026-09-23"
decided_at: 2026-09-23
---

Delete the `options_catalyst_links` step and the `options-catalyst-links`
job to reverse this packet. The binder module was already on main and stays.
The seat reads the histogram. This record does not charter the page.
