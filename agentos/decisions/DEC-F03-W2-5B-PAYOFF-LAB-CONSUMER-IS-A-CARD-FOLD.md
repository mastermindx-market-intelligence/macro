---
key: F03-W2-5B-PAYOFF-LAB-CONSUMER-IS-A-CARD-FOLD
question: >
  Where does the F03-W2-5a index-ETF payoff lab artifact (producer:
  scripts/build_options_payoff_lab.py + engine/options_payoff_lab.py, R2
  published as site/options_payoff_lab/latest.json) belong on the Options
  workspace surface (templates/options.html.j2) at display tier — a NEW
  page under /options, a Tier-1 number on the four index cards' faces, a
  JS-fetched panel, or a fold inside the existing "The four that set the
  tone" panel?
answer: >
  A TIER-2 FOLD ("What a structure pays") inside the existing four index
  cards (SPY/QQQ/IWM only; SPX has no chain in the lab; DIA is not a card
  on this page). The fold carries four plain-named structures (Straddle,
  Upside for downside, Downside hedge, Upside play), their per-share cost,
  breakeven prices, max-loss / max-gain plain words, a wall-bracket track
  with a four-clause verdict, and a one-line footer. The fold is OPT-IN
  via a single "details/summary" container — a click, not a page-load —
  and the card's stance chip (Watch / Protect gains) stays the only stance
  the panel ever speaks. The fold answers "what does it cost, how far must
  it move", never "do this".
rationale: >
  The producer (PR #7759, W2-5a) prices four canonical structures per
  index ETF — that is a CATALOG, not a single headline number, so a Tier-1
  glyph on the card face would discard three of the four. A new page would
  push users to a different URL to read the four cards' companion numbers,
  which is exactly the surface sprawl the Options workspace was chartered
  to compress (out: "ONE PAGE, FOUR MODES"). A JS-fetched panel would
  re-introduce the asset-stamping and fetch-via-script hazards the
  workspace already outlawed (#3372). A fold inside the existing card
  keeps the four-mode invariant, ships numbers + verdict + foot alongside
  the regime/stance already on the card, and degrades honestly to "no
  fold" when the artifact is absent (the SPX card and the whole panel stay
  byte-identical to today).

  Cost is per-share (display). StructureSummary.cost in
  engine/options_payoff.py is per-CONTRACT (the curve computes
  `sum(leg.qty * leg.multiplier * leg.entry_price)`); for index-ETF
  standard contracts the multiplier is 100 (engine/options_payoff_lab.py
  ETF_STANDARD_MULTIPLIER). The page displays PER-SHARE, so the consumer
  divides by 100 — recorded here so the math is auditable. cost_per_unit
  on PayoffCurve is the same value computed the same leg; the canonical
  per-share figure on the page is StructureSummary.cost / 100.0
  (tie-breaker).

  Per-share cost: $15.90 means the structure costs $15.90 per share (one
  option contract controls 100 shares of the underlying, so one share of
  the structure's cost is contract_cost / 100). A CREDIT (negative cost)
  reads "brings in $X.XX a share" — the sign is the user's sign, not the
  engine's. Cost is also shown as a fraction of the index spot (e.g.
  "2.4% of the index") for at-a-glance magnitude.
alternatives:
  - option: A NEW PAGE under /options (e.g. /options/payoff-lab.html)
    why_not: Adds a fifth URL the user must visit to read the four index
      cards' companion figures. The Options workspace's whole design is
      "one page, four modes" (research/options_estate/OEU_MASTERPLAN.md §2);
      pushing the catalog onto a separate URL re-opens the surface sprawl
      this workspace was chartered to compress. A fold carries the same
      numbers and verdict with zero URL change.
  - option: A Tier-1 number on the card FACE (e.g. "±X.X% priced move"
      inside the existing regime line)
    why_not: The producer publishes FOUR structures (atm_straddle, rr25,
      put_spread_95_90, call_spread_105_110) — a single headline number
      collapses the rest. The user has to read them in the existing card
      hierarchy anyway, and forcing a "headline" choice picks an arbitrary
      winner from a closed catalog. Tier-1 placement also strips the wall
      verdict and the per-structure breakevens / max-loss / max-gain, both
      of which are precisely the "what a structure pays" copy the spec
      binds. A fold keeps the closed catalog whole on Tier 2.
  - option: A JS-fetched panel (e.g. a second panel opened on demand
      from a top-bar button, fetching /api/payoff-lab/latest.json)
    why_not: Re-opens the payload-law hazard the workspace already
      outlawed — JS-injected <script> loaders bypass asset stamping
      (#3372), and lazy-fetched payloads break the "baked inline" rule
      the workspace owns (templates/options.html.j2 payload law §6).
      Adds a parallel fetch surface a future reader would have to teach
      itself; the fold reuses the existing committed site file path
      that engine-render already hydrates (R2 → emit →
      site/options_payoff_lab/latest.json), so no second fetch plumbing.
evidence:
  - command: "python3 -c \"import yaml;d=yaml.safe_load(open('.github/workflows/engine-render.yml'));print(max(len(s.get('run','')) for j in d['jobs'].values() for s in j.get('steps',[]) if isinstance(s,dict)))\""
    note: engine-render.yml run-expression max length = 19633 (limit 20,500)
  - command: "python3 -c \"import yaml;yaml.safe_load(open('.github/workflows/engine-render.yml'))\""
    note: engine-render.yml YAML parse OK
  - command: "python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --pack-index 0 --pack-count 12 --validate-only"
    note: Validated 223 legacy jobs (was 222; +1 for options-payoff-lab-consumer)
  - command: "python3 scripts/check_contract_delta.py --base origin/main"
    note: "contract-delta: 0 introduced"
  - command: "python -m pytest tests/test_options_payoff_lab_consumer.py -q"
    note: 8/8 hermetic tests pass (verdict truth table, fold-row count, copy-law, asof note, engine-render.yml pin)
  - command: "python -m pytest tests/test_build_options_command.py tests/test_render_options_workspace_scope.py tests/test_builder_shim_writes.py -q -k \"options\" -p no:cacheprovider"
    note: 153 passed (pre-existing options tests unaffected)
  - file: "engine/options_payoff.py:949-950"
    note: "cost = sum(leg.qty * leg.multiplier * leg.entry_price); cost_per_unit = sum(leg.qty * leg.entry_price)"
  - file: "engine/options_payoff_lab.py:ETF_STANDARD_MULTIPLIER"
    note: 100.0 — the index-ETF standard contract multiplier
  - pr: "#7759"
    note: W2-5a store-host producer (DRAFT, seat-gated) — the consumer's contract source
  - memory: "[[DEC-F03-W2-5-PAYOFF-LAB-CHARTERED-AFTER-C0-FREEZE]] (referenced charter)"
  - memory: "[[WS-MARKET-OS]] (owning workstream)"
  - memo: "research/MARKET_ONTOLOGY_F03_PAYOFF_LAB_CONSUMER_2026-09-23.md §B copy tables + verdict truth table"
affects:
  - WS-MARKET-OS
  - templates/options.html.j2
  - scripts/build_options_command.py
  - tests/test_options_payoff_lab_consumer.py
  - .github/workflows/engine-render.yml
  - .github/ci/legacy-jobs.yml
confidence: high
reversibility: easy
decided_by: session
decided_at: 2026-09-23
review_by: null
---
