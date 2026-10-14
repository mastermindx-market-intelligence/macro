---
key: DATAOS-D00-A1-VENUE-CLOCK-UNITS-SCOPE
question: >
  After the wave-2 independent review (R02) found that the action projection decides "has the ex-date
  passed" on the UTC date, that price rows carry no declared currency, and that the measured consumer-A
  population (venues incl. XASE; vendor-adjusted mixed-source bars) differs from the D00.D6 row written
  before measurement — how does D00 change, and what stays frozen?
answer: >
  One amendment, D00.A1 (research/data_os_completion/2026-10-13/D00_A1_AMENDMENT.md). A1.1: the as_at day
  is the listing venue's local calendar date, from a CLOSED VENUE_TZ map beside KNOWN_MICS; an unmapped MIC
  is a typed VENUE_CLOCK_UNKNOWN refusal, never a UTC default; evidence clocks stay UTC. A1.2: the request's
  field_units.currency is the listing currency resolved from a CLOSED venue→currency map; cash views require
  policy and every cash event to match it (typed CURRENCY_MISMATCH); an optional row currency column must
  match; no FX ever. A1.3: consumer-A venues are [XNYS, XNAS, XASE, ARCX]; the v1 Terminal witness is a
  vendor-adjusted series labelled TRADJ served as an explicitly labelled, non-executable proxy; the
  data-origin readout must print basis, per-ticker src, generation and "vendor-adjusted — not a printed
  price"; a house SADJ Terminal series is not claimed in v1 and is recorded as coverage. Everything else in
  D00 is unchanged.
rationale: >
  R02 m3 is a real off-by-one: a US as_at between 20:00 ET and midnight ET applies the next day's split
  (price_views.py L519-522 on the P04 head). The venue is already the identity authority (KNOWN_MICS is a
  closed list), so the clock belongs beside it and inherits the same "extend in a diff, never default" law.
  R02 m6: D00.01 already demands field_units on every request; binding the price rows to that declared
  currency closes the gap without a new column or any FX. R00 G2/G4: the row was measured after D00.D6 was
  written; the honest label is TRADJ (a label may never claim less adjustment than a constituent may carry)
  and the readout is exactly the surface whose job is to say so; XASE is a measured venue and a known MIC.
  Ruling these as one amendment keeps D00 frozen and falsifiable instead of letting the consumer lanes
  "fix" them silently (R02's explicit danger).
alternatives:
  - option: Keep the UTC date for as_at (packet O2-P02 letter) and document the 4-hour window.
    why_not: >
      The SADJ definition in D00.D3 is "the share basis at as_at"; a view that divides by a split the tape
      has not yet applied mis-states the share basis for every US request in that window.
  - option: Pass an explicit exchange-local date instead of a datetime as_at.
    why_not: >
      Breaks the single as_at instant that RECONSTRUCT and the evidence clocks already share (D00.D1);
      two notions of "now" per request is the conflation D00 was written to prevent.
  - option: Require the Terminal to serve house SADJ from RAW bars so consumer A matches D00.D3 SADJ.
    why_not: >
      The Terminal ingest keeps no RAW tape for mixed-src tickers; producing one is a new collector path,
      which the programme forbids. The honest witness is the labelled proxy plus a readout that says so.
  - option: Leave XASE out and report XASE rows as a coverage gap.
    why_not: >
      XASE is a measured venue in the producer's own MIC map and already a KNOWN_MIC; excluding it hides
      population rather than declaring it.
evidence:
  - "R02 (Opus read-only review, 2026-10-13T16:13Z) findings m3, m6, m8; seat execution of M1/M2/M3 via scratchpad verify_r02.sh (M1 split_factor=4, M2 holding_return=1/50, M3 default-path CONFIRMED)."
  - "lib/dataos/price_views.py @ bfba67e0eeac (P04 head) L519 `as_at_day = as_at.astimezone(timezone.utc).date()`, L522 `if not (t < event.ex_date <= as_at_day)`."
  - "lib/dataos/identity.py @ origin/main L111-128: KNOWN_MICS is a closed set {BATS, XNYS, XNAS, XASE, ARCX, XSHG, XSHE, XBSE, XHKG, XTSE, XTSX}."
  - "R00 matrix @ ccef37925b5a L80 (G2) and L82 (G4); config/dataset_registry.yml @ ccef37925b5a L1613-1641 (terminal.bars.daily.ohlc_json: basis tradj, venues [XNYS, XNAS, XASE, ARCX], PROPOSED)."
  - "D00_SEMANTIC_DECISIONS.md @ origin/main L51-75 (D3), L109-131 (D6), L132-140 (D00.01)."
affects:
  - "WS:DATA-OS-COMPLETION"
  - "lib/dataos/price_views.py"
  - "lib/dataos/identity.py"
  - "config/dataset_registry.yml"
  - "terminal:ingest/build_universe.py"
  - "terminal:terminal/components/ChartFrameBar.tsx"
confidence: high
reversibility: costly
decided_by: coo-fable
decided_at: 2026-10-13
---

# D00.A1 — venue clock, declared units, consumer-A scope

See `research/data_os_completion/2026-10-13/D00_A1_AMENDMENT.md` for the full text and falsifiers.
Implementation is a consumer-wave lane (P06) under the consumer-wave orchestrator: `VENUE_TZ` /
`VENUE_CURRENCY` beside `KNOWN_MICS`, `VENUE_CLOCK_UNKNOWN` and `CURRENCY_MISMATCH` refusals, fail-on-old
tests for the 2026-06-10T02:00Z falsifier; U01/U02 carry the readout obligation. Until P06 lands, the
UTC-date rule on main is a recorded limitation, not a licence for a consumer lane to patch it locally.
