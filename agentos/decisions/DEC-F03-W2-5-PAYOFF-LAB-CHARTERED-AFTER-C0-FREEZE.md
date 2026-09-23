---
key: F03-W2-5-PAYOFF-LAB-CHARTERED-AFTER-C0-FREEZE
question: >
  After the C0-FREEZE (Phase-0 / Phase-1A scope) closed the canonical
  workspace surfaces and gated the F0-F2 wave behind a display-tier
  charter, is the F03 W2-5 (index-ETF payoff lab) program authorized to
  build, and if so under which scope + ownership?
answer: >
  Yes — the F03 W2-5 program is CHARTERED under the F0-F2 wave. The
  W2-5a store-host producer (engine/options_payoff_lab.py +
  scripts/build_options_payoff_lab.py; R2 published as
  site/options_payoff_lab/latest.json) and the W2-5b consumer (the
  four-card fold on templates/options.html.j2) both belong to the F03
  workstream, owned by WS-MARKET-OS. The producer ships to R2 and
  commits the artifact via engine-render.yml's --emit leg; the consumer
  reads the committed artifact via a SEPARATE loader and never computes
  a new price, threshold, or ranking. The charter is display-tier only;
  gauntlet promotion remains the F0-F2 path's binding authority.
rationale: >
  The C0-FREEZE closed the Phase-0/1A scope and froze the canonical
  workspace surfaces; F0-F2 is the F-series wave that follows, and
  F03 is the "options" sub-stream of that wave. The payoff lab artifact
  is a DERIVED display from already-published gex/chain surfaces — it
  reads existing JSON files and does not introduce a new data plane.
  Chartering it under F03 is consistent with the F0-F2 scope rule
  ("display tier only until gauntleted") and with the WS-MARKET-OS
  ownership (the same workstream that owns the Options workspace and
  the gex/skim/skew artifacts the lab reads).
alternatives:
  - option: "Defer the program to the F3+ wave (after Phase 2 gauntleted the Options surface)"
    why_not: "F0-F2 explicitly charters derived display surfaces from already-published data; deferral would mean F03 owns nothing on the workspace until 2027 H1."
  - option: "Charter the consumer-only half (W2-5b) and leave the producer (W2-5a) under ad-hoc build"
    why_not: "The consumer's contract IS the producer's SCHEMA mastermind.options_payoff_lab/v1; splitting them orphans the contract on the producer side."
evidence:
  - file: "agentos/workstreams/WS-MARKET-OS.md"
    note: owning workstream; F03 sub-stream under F0-F2
  - file: "research/MASTERMIND_SUPERINTELLIGENCE_MASTERPLAN.md"
    note: F-series wave charter; F0-F2 = display tier only
  - file: "engine/options_payoff_lab.py SCHEMA 'mastermind.options_payoff_lab/v1'"
    note: the producer's contract the consumer reads
  - pr: "#7759"
    note: W2-5a store-host producer (DRAFT, seat-gated)
  - pr: "#7763"
    note: W2-5b consumer (DRAFT, seat-gated) — this PR
  - memo: "research/MARKET_ONTOLOGY_F03_PAYOFF_LAB_CONSUMER_2026-09-23.md"
    note: consumer's data path + liveness recipe
affects:
  - WS-MARKET-OS
  - engine/options_payoff_lab.py
  - scripts/build_options_payoff_lab.py
  - scripts/build_options_command.py
  - templates/options.html.j2
  - .github/workflows/engine-render.yml
confidence: high
reversibility: easy
decided_by: session
decided_at: 2026-09-23
review_by: 2026-12-31
---
