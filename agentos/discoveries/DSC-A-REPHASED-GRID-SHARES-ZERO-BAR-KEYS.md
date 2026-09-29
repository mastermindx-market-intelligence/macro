---
key: A-REPHASED-GRID-SHARES-ZERO-BAR-KEYS
claim: >
  Two multi-session bar grids over the same feed that differ in phase or in which session keys
  the bar share ZERO bar keys, not "most" keys. Measured on the served 6,963-session NVDA
  document: the canonical grid yields 2,322 keys, the previous feed-start floor(i/3) grid yields
  2,321, and the intersection is empty. Therefore ONE date read off the live chart decides
  which rule produced it — there is no date both rules could have emitted.
falsifier: >
  Run, against the served document, the intersection of the two key sets:
  `python3 -c "import json;b=[r[0] for r in json.load(open('terminal/public/data/NVDA.json'))['bars']];
  new={b[i] for i in range(len(b)) if i==0 or (i-1)%3==0};old={b[min(i+2,len(b)-1)] for i in
  range(0,len(b),3)};print(len(new),len(old),len(new&old))"` — a non-empty intersection refutes the
  claim for that symbol, and any acceptance argument resting on a single crosshair read must then be
  discarded for a full-set comparison. See terminal/lib/sessionBars.ts:120 (`sessionBarOpens`) for
  the rule being compared, and #772 for the measurement. The claim is also refuted for a symbol
  whose feed starts exactly on a grid boundary AND whose bars are keyed identically by both rules:
  there the two coincide and no single read is discriminating.
so_what: >
  Live acceptance of a bar-grid repair does not need a bulk export, a licensed capture or a
  privileged endpoint. Hover the chart, read the time-axis crosshair label, and check set
  membership. This converted an acceptance step that looked like it required production data
  extraction into five browser reads, and it is how the same class of repair should be accepted
  in future rather than by re-counting fixtures.
  Corollary for whoever reads this next: the reason the original defect survived in production is
  the same arithmetic. Because the grids share no keys, EVERY marker was on the wrong candle, yet
  nearest-bar snapping with a ~10-day tolerance put each one on a plausible neighbour. Total
  disagreement and plausible output are not in tension.
kind: architecture
verified_at: 2026-09-29
verified_by: >
  mastermind-terminal PR #772 (d284493688ba); key-set intersection computed over the served
  terminal/public/data/NVDA.json bars array; five time-axis crosshair reads on the served
  generation; signal placement bar_index - canonical_bar(ts) == {0: 317}.
scope:
  - mastermind-terminal terminal/lib/sessionBars.ts
  - mastermind-terminal terminal/components/ChartPanel.tsx
  - mastermind-terminal 2D/3D session-derived timeframes
  - "generation d284493688ba1d200c93e0b5b075edf1f3da041c served at app.mastermind-x.com"
confidence: verified
---

## How the live read is taken

⚠️ Read the key from the **canvas time-axis crosshair label** — hovering the chart highlights the
hovered bar's date on the time axis. Do **not** try to read it from the legend: `.status-ohlc`
always shows the LAST bar, never the hovered one, so a hover sweep returns an identical string at
every x position and looks like a dead crosshair. A session that mistakes this for a broken
crosshair will conclude the chart is unreadable and reach for a data export it does not need.

Five reads taken on the served generation, each belonging to the canonical grid and to no grid the
previous rule could produce: `22 Jan '99` (the forced row-0 partial), `23 Mar '26`, `14 Sep '26`,
`22 Sep '26`, `25 Sep '26` (final bar).

## Two independent confirmations from the same reads

- **Identity vs availability.** The final bar's key is `2026-09-25` while the document's last
  session is `2026-09-28`. The bar is named by the session it OPENED on, not the one that closed
  it — visible without any instrumentation, and matching the prediction recorded before the read.
- **The aggregation is the canonical bucket.** The legend's `O`/`H`/`L` for the final bar match the
  canonical final bucket exactly and mismatch the previous rule's bucket on both `O` and `L`.
  `C` tracks the live quote rather than the stored close — watch it tick while `O`/`H`/`L` hold
  constant, and do not treat that as a mismatch.

## Signal placement measured the same way

Engine `indicator.as_of` equals the chart's last bar key. Across 317 signals spanning 27 years,
`bar_index - canonical_bar(ts)` and `bar_index - canonical_bar(known_ts)` are both `{0: 317}` —
exact, with zero look-ahead.

⚠️ The first attempt at this measurement asked whether a signal's `ts` was itself a bar key and got
198/317 (~63%), which reads as a partial failure and is a wrong question. Signals are daily-resolution
events ASSIGNED to a 3D bar via `bar_index` (the engine's own `honest_read` says "confluence on
daily—3D"); they are not 3D-bar-keyed events. Splitting the 63% by era gave a uniform 56–67%, which
ruled out a phase offset — a real phase error would have given ~0% — and that is what exposed the
question as wrong rather than the code.

Related: DEC-BAR-PHASE-IS-PUBLISHED-BY-THE-PRODUCER,
DSC-ACCEPTANCE-PROBE-CAN-FIRE-ON-THE-NEGATIVE-CASE.
