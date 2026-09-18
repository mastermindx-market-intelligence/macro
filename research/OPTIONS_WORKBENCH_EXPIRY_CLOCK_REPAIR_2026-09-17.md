# Options Workbench R0 — Intraday Expiry Clock Repair

Date: 2026-09-17
Operation: `options-workbench-r0-expiry-clock-20260917-sol-001`
Parent: Terminal #603 Options Workbench recovery
Base: Macro `c3d4b81acee75081138c9e40aba8d7589aa341e3`
Skillpack: Mastermind `320f586126b7c82c843ef17612f12d40d20a42e0`
State: BUILT_NOT_PROVEN until review, CI, release, and production proof.

## User/machine capability

Before this repair, every same-day contract entering the intraday Gamma/Vanna/Charm
surface was assigned exactly four hours of remaining life regardless of whether the
snapshot was at 10:00 ET or 15:59 ET. The heat field therefore used a false decay
clock precisely where 0DTE Greeks are most time-sensitive.

After this repair, the existing surface producer derives `T` from the poller's
canonical `cycle_started_at` to the expiration date's actual US cash-session close.
Regular sessions close at 16:00 ET; the existing `engine.session_digest` owner supplies
13:00 ET early closes. At or after maturity the contract is omitted rather than given
fabricated residual time. The Greek engine's existing one-minute `MIN_T` remains a
numerical IV-solver guard and is not promoted into source-time truth.

## Scope and ownership

No new feed, pricing kernel, expiry calendar, replay plane, signal, ranking, or trade
authority is introduced. `engine.session_digest.session_window_et` and
`lib.nyse_calendar.is_session` remain the clock/calendar owners.
`scripts/build_flow_surface.py` now requires `observed_at` for contract extraction.
`scripts/live_flow_poller.py` passes the already-canonical `cycle_started_at`.
The producer rejects a session date paired with an observation clock from another ET
session, preventing historical/diagnostic state from wearing today's time-to-expiry.

The current surface universe is US cash-equity/ETF options. This change must not be
silently reused for SPX/VIX or another product whose expiration clock/settlement
contract differs; those products require their own accepted clock metadata before
entering this producer.

## Market-time basis

Cboe's current equity-options extended-hours FAQ states that designated ETF options can
trade to 16:15 ET on expiration day, while OCC closing/settlement marks and underlying
ITM/OTM determination are based on the 16:00 ET underlying close. The current
`live_flow` producer already filters its tape to the US cash-session window, so this
surface's modeled observation horizon ends with that same cash-session close rather
than inventing a 16:15 post-cash tape it does not ingest.

Official references:
- Cboe Equity Options Extended Trading Hours FAQ:
  https://www.cboe.com/document/tech-spec/document/technical-specifications/equity-options-extended-trading-hours-faq
- OCC ETF options product characteristics:
  https://www.theocc.com/clearance-and-settlement/clearing/etf-options

## Discriminating evidence

New tests fail on the original producer for four independent reasons: 10:00 ET 0DTE
is incorrectly four hours instead of six; 15:59 ET is incorrectly four hours instead
of one minute; a canonical 13:00 early close is ignored; and `run_cycle` does not pass
its canonical cycle clock into the extractor. The original-source discrimination log
is preserved under `research/evidence/options-workbench-expiry-clock-20260917/`.
The candidate additionally rejects non-session expiration dates and cross-session
clock/session mismatches. DST is exercised in both July (EDT) and January (EST), and
next-day maturity measures actual elapsed calendar hours rather than integer date delta.

Fresh candidate verification after restoring from the original-source discrimination:
- focused surface/Greek/poller set: 74 passed;
- broad surface + intraday Greeks + live-flow + session-digest set: 509 passed,
  one pre-existing skip, zero failures;
- `tests/test_live_flow.py` alone: 284 passed after materializing the tracked `app/`
  and `ops/` trees omitted by the sparse worktree;
- `python3 -m compileall` on changed producer/poller/tests: exit 0;
- `git diff --check`: clean.

Known warnings in the broad suite are pre-existing FastAPI deprecations and the existing
strict-JSON overflow test's intentional NumPy runtime warning; they are not hidden.

## Non-claims and next gate

This establishes clock correctness for the existing modeled intraday Greek producer;
it does not prove dealer inventory, market freshness, predictive edge, conditional
future price/time surfaces, QuantedOptions parity, or production deployment.

Next: preserve the exact candidate in a draft PR, run current-head CI, obtain independent
numerical/source review, and only then use the existing live-flow release owner for a
natural RTH proof. The adjacent gamma-sign PR #7271 and Terminal #608 remain separate
carriers with their own release gates.
