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

After this repair, the existing surface producer derives `T` from each root's
fetched-availability / valuation clock (`observed_at`, captured immediately after that
root's network response) to the expiration date's actual US cash-session close.
`cycle_started_at` remains poll-cadence metadata only and is never used to backdate a
later source response. Regular sessions close at 16:00 ET; the existing
`engine.session_digest` owner supplies 13:00 ET early closes. At or after maturity the
contract is omitted rather than given fabricated residual time. The Greek engine's
existing one-minute `MIN_T` remains a numerical IV-solver guard and is not promoted into
source-time truth.

The public replay frame now keeps the clocks/bases distinct: exact root `valuation_at`
(including sub-second precision), later `built_at`, selected trade-event range
(`trade_at_first/last`), provider NBBO range (`quote_at_first/last`, from the actual
ThetaData `quote_timestamp`), and exact pre-session `oi_vintage`. Missing quote time
stays null; a later trade/fetch/build clock never fabricates quote freshness.

## Scope and ownership

No new feed, pricing kernel, expiry calendar, replay plane, freshness policy, signal,
ranking, or trade authority is introduced. `engine.session_digest.session_window_et` and
`lib.nyse_calendar.is_session` remain the clock/calendar owners.
`scripts/live_flow_poller.py` reuses the fetched-root `observed_at` it already records
after each response, and preserves the exact OI source session already returned by
`_load_oi_prev`. `scripts/build_flow_surface.py` uses that same root clock for maturity,
stamp identity and `valuation_at`; a root without a valid current observation is skipped
rather than relabelled with another root's or the wrapper's later clock.

The extractor preserves whole-row source identity. It retains trade time separately from
the provider's `quote_timestamp`, rejects source clocks later than the root observation,
and filters raw bulk-tape rows through the existing cash-session window before choosing
the latest row per contract. Stable whole-row selection is intentional: pandas
`GroupBy.last()` can splice an older non-null quote timestamp onto a newer trade row.
Same-minute replacement overwrites the same replay column and its aligned provenance
rather than forward-filling a later column's clocks.

The current surface universe is US cash-equity/ETF options. This change must not be
silently reused for SPX/VIX or another product whose expiration clock/settlement
contract differs; those products require their own accepted clock metadata before
entering this producer.

## Market-time basis

Cboe's current equity-options extended-hours FAQ states that designated ETF options can
trade to 16:15 ET on expiration day, while OCC closing/settlement marks and underlying
ITM/OTM determination are based on the 16:00 ET underlying close. The main
`engine.live_flow` path already filters trade events to the US cash-session window, but
the surface Greek tap reuses the raw bulk frames and therefore required its own call to
the **same existing session owner** before selecting a contract row. That gate now excludes
post-close raw prints on both normal and 13:00 early-close sessions; it does not create a
second calendar. The modeled maturity horizon and the selected trade-event horizon are
therefore governed by the same cash-session boundary.

Official references:
- Cboe Equity Options Extended Trading Hours FAQ:
  https://www.cboe.com/document/tech-spec/document/technical-specifications/equity-options-extended-trading-hours-faq
- OCC ETF options product characteristics:
  https://www.theocc.com/clearance-and-settlement/clearing/etf-options

## Discriminating evidence

The original fixed-four-hour tests remain discriminating: 10:00 ET 0DTE was four hours
instead of six; 15:59 ET was four hours instead of one minute; a canonical 13:00 early
close was ignored; and the original poller did not provide an observation-time clock to
the extractor. The original-source discrimination log is preserved under
`research/evidence/options-workbench-expiry-clock-20260917/`.

Subsequent adversarial review found and reproduced additional clock-identity defects on
the first candidate:
- `cycle_started_at` could predate a slow root response by many minutes and even keep a
  contract alive after cash close;
- two roots fetched at different times were published under one wrapper clock;
- trade time, provider quote time, root valuation time and build time were conflated or
  dropped;
- pandas `GroupBy.last()` could borrow an older non-null quote clock for the latest
  trade row;
- the raw surface quote tap could select 16:05 / 13:05 extended-hours trades even though
  the accepted cash-session close was 16:00 / 13:00.

Each defect now has a direct red→green regression. The candidate also preserves exact
sub-second root valuation identity, exact OI vintage, honest null quote clocks,
cross-session fail-closed behavior, DST in both EDT/EST, and actual elapsed time across
dates.

Fresh current-candidate verification:
- five owner packs (`test_flow_surface`, `test_live_flow`, `test_session_digest`,
  `test_intraday_greeks`, `test_thetadata`): **624 passed, 1 pre-existing skip,
  zero failures**;
- focused source-clock / row-identity / cash-session regressions: green;
- `python3 -m compileall` on changed producer/poller/tests: exit 0;
- `git diff --check`: clean.

Known warnings in the broad suite are pre-existing FastAPI deprecations and the existing
strict-JSON overflow test's intentional NumPy runtime warning; they are not hidden.

## Non-claims and next gate

This establishes clock correctness for the existing modeled intraday Greek producer;
it does not prove dealer inventory, market freshness, predictive edge, conditional
future price/time surfaces, QuantedOptions parity, or production deployment.

Next: freeze the review-hardened same-carrier head in draft PR #7279, refresh hosted
CI and independent numerical/source review on that exact immutable revision, and only
then use the existing live-flow release owner for a natural RTH proof. The adjacent
gamma-sign PR #7271 and Terminal #608 remain separate carriers with their own release
gates.
