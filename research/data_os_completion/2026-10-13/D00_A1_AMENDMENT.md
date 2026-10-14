# D00.A1 — Venue clock, declared units, consumer-A scope

Amendment to `D00_SEMANTIC_DECISIONS.md` (#9133), ruled by the Fable Meta-CEO seat on 2026-10-13 after the
wave-2 independent review (R02 findings m3, m6, m8 / R00 gaps G2, G4). D00 stays frozen; this file is the only
place its meaning changes. Three clarifications; no rights widened; no new store, registry, collector, queue,
scheduler, publisher or evaluator; no historical book is repriced.

## A1.1 — The as_at day is the listing venue's calendar day (amends D00.D3, SADJ and event admission)

An action takes effect on its `ex_date`, a session date on the listing venue's calendar. Whether it has taken
effect at `as_at` is decided on the **venue-local calendar date of `as_at`**, never the UTC date:

```
as_at_day = as_at.astimezone(VENUE_TZ[listing.mic]).date()
event is effective at as_at  ⇔  event.ex_date <= as_at_day
```

`VENUE_TZ` is a CLOSED map beside `KNOWN_MICS` in `lib/dataos/identity.py` (same human-once-in-a-diff law):
BATS / XNYS / XNAS / XASE / ARCX → `America/New_York`; XTSE / XTSX → `America/Toronto`; XHKG → `Asia/Hong_Kong`;
XSHG / XSHE / XBSE → `Asia/Shanghai`. A naive `as_at` stays refused (unchanged). A MIC with no venue clock is a
typed refusal `VENUE_CLOCK_UNKNOWN` — never a silent fallback to UTC. The `evidence_mode` clocks (`known_at`,
`ingested_at`, `published_at`) remain UTC instants; this amendment touches only the ex-date comparison.

Falsifier: a US listing with a 2:1 forward split ex 2026-06-10 and `as_at = 2026-06-10T02:00Z` (22:00 ET on
06-09) must give `S(t; v) = 1` for every `t < 2026-06-10` — the tape has not split yet. The UTC rule gives 2.

## A1.2 — Price rows carry declared units; cash and policy must match them (amends D00.D3 currency sentence; binds D00.01 `field_units`)

Price rows carry no currency column by contract. The request's `field_units.currency` **is** the listing
currency and is resolved from the venue by a second CLOSED map beside `VENUE_TZ`: BATS / XNYS / XNAS / XASE /
ARCX → `USD`; XTSE / XTSX → `CAD`; XHKG → `HKD`; XSHG / XSHE / XBSE → `CNY`. Every view that computes with cash
(house `TOTAL_RETURN`) requires `policy.currency == field_units.currency` and every cash event's currency equal
to it, else typed `CURRENCY_MISMATCH`; an optional `currency` column on rows, when present, must equal it row by
row. RAW and SADJ views carry the declared currency through to the view label. No FX is ever applied (unchanged).
Share basis and volume convention in `field_units` are unchanged (D00.D3 V03).

## A1.3 — Consumer A scope: venues and basis (amends D00.D6 row A; closes R00 G2 and G4)

- **Venues:** `[XNYS, XNAS, XASE, ARCX]`. XASE (NYSE American) is measured in the Terminal producer's MIC map
  and is already a `KNOWN_MIC`; D00.D6 named three venues before the population was measured.
- **Basis:** the v1 Terminal daily-OHLC positive witness is a **vendor-adjusted series labelled `TRADJ`**
  (R00 ruling: one row label never claims less adjustment than any constituent may carry; per-ticker `src` is
  deep / polygon / yahoo). It is served for chart continuity as an explicitly labelled proxy under D00.D3 —
  never executable, never compared against a printed price, never a brokerage ledger.
- **Readout obligation (binds U01/U02):** the data-origin readout states, in plain words, `basis = tradj`,
  the per-ticker `src`, the generation / as-of it was built from, and "vendor-adjusted — not a printed price".
  Where `src` is unknown the readout prints *unknown* (nulls printed, never hidden).
- **Not claimed in v1:** a house SADJ Terminal series. The Terminal ingest retains no RAW tape for the
  mixed-`src` tickers, and producing one is a producer change outside this programme (no new collector).
  Recorded as coverage, not hidden.
- Unchanged: the consumer-A registry row stays `PROPOSED` until the Terminal producer is in-repo evidence
  (R00.01); consumers B and C are untouched.

## What would reopen this amendment

- A Terminal producer that retains RAW bars reopens A1.3's SADJ exclusion.
- A consumer carrying a venue outside the closed maps extends them in a diff (the KNOWN_MICS law) — it never
  defaults.
- A listing whose trading currency differs from its venue currency (dual-currency counters) reopens A1.2 with a
  per-listing override; none is enrolled in v1.

## Implementation

Package P06 under the consumer-wave orchestrator: `VENUE_TZ` / `VENUE_CURRENCY` beside `KNOWN_MICS`
(`lib/dataos/identity.py`, additive), `VENUE_CLOCK_UNKNOWN` and `CURRENCY_MISMATCH` refusals in
`lib/dataos/price_views.py`, a fail-on-old test for the 2026-06-10T02:00Z falsifier, and the U01/U02 readout
obligation. Decision record: `DEC:DATAOS-D00-A1-VENUE-CLOCK-UNITS-SCOPE`.
