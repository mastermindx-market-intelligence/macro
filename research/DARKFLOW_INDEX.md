# Dark Flow: independent DIX-style market composition

Commission: Chris, 2026-10-17. Implementation owner: Macro. Tier: display/context.
This document describes the implemented construction and acceptance contract; it
is not a predictive qualification, source-license grant, or production receipt.

## User outcome and placement

The user can inspect an independently calculated market-wide short-marked share,
distinguish constituent-ratio changes from changes in trading concentration, see
which sectors and names differ, and compare the observation with independently
dated volatility context. A recovery or deterioration is investigated rather than
inferred from an unexplained gauge.

A compact, lazy-loaded card sits immediately after Macro's Market State overview.
It expands in place and links to the existing `darkpool.html#dark-flow` desk. The
full desk reuses the identical component. This belongs with market internals and
risk interpretation, not inside the causal Transmission classifier. Existing
Risk Radar authority and the existing off-exchange-participation gauge remain
unchanged. No new risk score, alert owner, scheduler, collector or model call.

## Source census and reuse

- `collectors/finra_short_volume.py`: existing daily FINRA CNMS short-sale files.
- `scripts/backfill_finra_short_volume.py`: existing deep history writer; adds an
  explicit historical S&P 500 coverage-repair mode. It still cannot write the
  sealed collector panel and retains its 25 MB ceiling.
- `data/finra_short_volume/panel.parquet` plus `panel_deep.parquet`: same precedence
  as the existing Dark Pool Desk; the current collector wins overlapping rows.
- `collectors/massive_stock_day.py`: existing raw daily prices and R2 ownership.
  The new build reads the existing restored mirror and never substitutes adjusted
  Yahoo prices. No new price feed or credential route is introduced.
- `data/breadth/sp1500_pit_membership.parquet` and the existing observed-membership
  ledger: historical intervals followed by actual observed membership. Current
  survivors are not projected backward across the whole series.
- `engine/vol_velocity.py` / `site/basketdata/vol_weather.json`: existing volatility
  owner; the client consumes its VIX level, five-session velocity, term slope and
  VVIX/VIX chips without recomputing, fusing or changing their authority.
- Existing Dark Pool ledger namespace: first-observed index input snapshots use
  the same nightly-only advancement gate, not a new lifecycle or signal registry.

`engine/darkpool_episode_duration.py` stays research-only and unwired. The
PSS-AF1 family, manifest, original ledger and frozen panel prefix are not changed.
The earlier failed standalone accumulation/distribution construction described in
`DARKPOOL_DESK_AUDIT_AND_UPGRADE_2026-08-05.md` is not revived under a new name.

## Calculation contract

For eligible member i on session t, define S as FINRA ShortVolume, V as FINRA
TotalVolume, and P as the same-session unadjusted closing price:

```
ratio_i = S_i / V_i
market_ratio = 100 * sum(P_i * S_i) / sum(P_i * V_i)
weight_i = P_i * V_i / sum(P * V)
```

This is traded-dollar weighting, not market-cap weighting and not an equal-weight
average. Closing price is an explicit notional proxy; it is not a per-print VWAP.
FINRA ShortVolume includes ShortExemptVolume: never add exempt volume again.
Fractional volumes stay fractional. The raw denominator is FINRA-reported volume,
not consolidated exchange-plus-off-exchange volume.

Market publication requires at least 400 observed names and 90% member-count
coverage. Sectors require five observations and 80%. Coverage is explicitly a
COUNT measure, not a claim about missing-dollar coverage; a missing large trader
can still affect the aggregate materially. Missing-source counts, source hashes,
reference membership dates and sample weights are exposed. This is an independently
constructed proxy, not exact SqueezeMetrics parity.

Zero short-marked volume is a valid zero. Missing, non-finite, negative, excessive
short volume, impossible exempt volume, non-positive prices and ambiguous duplicate
rows do not become zeros. Only explicit common-share aliases are normalized;
case-sensitive preferred-share symbols are not silently uppercased.

## Time, revisions and historical limits

FINRA's existing source clock becomes due at 18:30 New York time on exchange
sessions. The current expected session remains explicit even when its prices are
missing. A last-complete fallback has its own date, ratios, sectors, attribution,
SPY comparison and constituent observations; today's empty sectors cannot be shown
under yesterday's headline. The next due timestamp uses the existing NYSE calendar.
The client detects publication overdue without an interval poller.

Data is parsed and hashed from the SAME byte snapshot. A concurrent file replacement
cannot cause the receipt to attest a different vintage from the parsed input.
Separate compact-summary/history files carry an identical content generation;
a mixed-generation fetch retains the dated summary and refuses the mismatched
history, with an explicit retry control.

History is labeled `reconstructed_source_vintage`, not original publication-time
availability. Current sector classifications are disclosed and never presented as
historical sector membership. The known June 14-July 10, 2026 membership-accrual gap
and restatement uncertainty remain limitations, not erased observations. Active
membership is a carried observed state with a five-market-session freshness ceiling.

No record can become a live first observation using a replay clock. The optional
nightly append records `known_at`, source hashes and the actual current covered
session, keeps the first record on correction, and refuses a corrupt existing log.
No forward outcome is computed by this writer. Historical backfills never get
inserted into the live observation ledger as if they had been known earlier.

## Trajectory and attribution

The card exposes exact-calendar one-, three- and five-session changes, a complete
five-session average, and a prior-only 252-session percentile (minimum 60 prior
covered observations). Missing sessions remain chart gaps.

Three-session velocity = (R_t - R_t-3) / 3, in percentage points per session.
Three-session acceleration = (R_t - 2 R_t-3 + R_t-6) / 9, in percentage points per
session squared. The required four/seven-session windows must be covered. Positive
acceleration during a negative velocity means the ratio is falling more slowly,
not that stock prices have bottomed.

For common members, midpoint attribution is exact:

```
ratio_effect_i = 100 * (w_t + w_0)/2 * (ratio_t - ratio_0)
weight_effect_i = 100 * (ratio_t + ratio_0)/2 * (w_t - w_0)
```

Entry/exit and coverage changes have a separate contribution. The components sum
to the aggregate change; zero-sum rearrangements are not labeled capital inflows.
The explanation names the largest arithmetic component. Constituent breadth counts
rising SHORT-MARKED RATIOS among common names; it is never labeled price breadth.

## Interpretation and scientific authority

The observable ratio does not identify the end investor, aggressor direction, net
inventory, short interest or institutional buying/selling. A market maker can sell
short to satisfy a customer purchase; execution mix and hedging can change ratios
without the directional narrative suggested by a social post.

Useful user sequence: check freshness and coverage; examine the ratio trajectory;
separate ratio effects from weight/coverage effects; inspect sector and ticker
participation; compare with price recovery, breadth, credit and volatility using
each source's actual date. This can expose an internally uneven rebound without
calling every low reading an institutional sell signal.

No 40/45/50 level is installed as a bullish/bearish trigger. The aggregate, VIX,
VVIX and term structure are not averaged into a second Fear & Greed score. There
is no validated pivot probability, expected return, alert escalation, sizing or
trade authority. Computational tests do not establish forecasting power. Any
future qualification must use the existing research owner, declared hypotheses,
point-in-time observation timestamps, matched benchmarks, costs and held-out/forward
evidence; it must not reopen the forbidden standalone construction or alter the
frozen PSS-AF1 study. Simply reproducing a vendor's historical association is not
independent qualification.

## Paper design and implementation evidence

Paper file `01M2WGNCX9475G79JRKJTCM08P`, page `p-1W-1`:
https://app.paper.design/file/01M2WGNCX9475G79JRKJTCM08P/p-1W-1

Desktop artboard `63EB-1` (1440 x 900, dark), mobile artboard `645Y-1` (390 x 844,
light). Both target screenshots were inspected; reading-component JSX was read
from `64OW-1`. The reference uses dated actual source observations rather than
invented current readings. Source implementation shares tokens, hierarchy,
neutral-blue ratio charts and explicit freshness treatment. The iOS status bar
belongs only to the Paper reference, not the web application.

`templates/_darkflow_panel.html.j2`, `darkflow.css` and `darkflow.js` are one shared
component. English/Chinese, light/dark, keyboard chart inspection, sector/range
selection, constituent lookup, dated source errors and generation-mismatch retry
are part of its acceptance contract. Compact mode fetches neither history nor
volatility until expanded. No chart library, external script or background poller.

`tests/darkflow_browser.py` uses the real component with source-backed inputs,
then separately exercises typed synthetic faults. Its screenshots are component
proof, not production or authenticated-navigation proof. Production source and
browser receipts must be attached to the delivery separately.

## Build, failure and repair

```
python -m scripts.build_darkflow_index
python -m scripts.build_darkflow_index --record-observation  # existing nightly only
python -m scripts.backfill_finra_short_volume --universe sp500 --start YYYY-MM-DD --end YYYY-MM-DD
python -m pytest tests/test_darkflow_index.py tests/test_darkflow_publish.py -q
python tests/darkflow_browser.py --source /absolute/site --output /outside/repo/browser
```

The daily engine invokes the producer after its existing raw-price restore.
Render-only lanes consume committed JSON; they do not advance a data ledger.
The existing Macro render scope also rebuilds the full desk with
`scripts.build_darkpool_desk --render-only`, which passes the existing context
producer its `write=False` mode. The producer and full template are exercised by
a hermetic test that verifies no context or forward ledger is created. This closes
a delivery gap: the prior narrow Macro render did not rebuild the Dark Pool Desk.
The existing freshness sentinel reads `observed_asof`, not the expected session
on a newly built incomplete publication. A source failure returns non-zero and preserves the previous publication; missing
current prices can publish a truthful partial/latest-complete view. Never heal it
by forward-filling prices or falsifying the session. Two-file publication errors
are detected by generation mismatch. No automatic replay of an ambiguous append.

## Data rights and primary references

The implementation does not ingest or rehost SqueezeMetrics' published series,
code, graphics or proprietary data. It uses Mastermind's existing FINRA and raw-price
sources, publishes derived ratios, and exposes no raw price-feed download or
credentials. Public CDN availability is not a blanket commercial redistribution
license; existing provider agreements remain applicable. This implementation does
not grant a new right to redistribute source datasets or their full history.

- FINRA short-sale data and definitions: https://www.finra.org/finra-data/browse-catalog/short-sale-volume-data
- FINRA interpretation notice (May 10, 2019): https://www.finra.org/rules-guidance/notices/information-notice-051019
- SqueezeMetrics original DIX explanation: https://squeezemetrics.com/monitor/docs

## Verified data-acquisition milestone (not a deployment receipt)

The bounded historical S&P coverage repair completed, adding to the deep store,
not the sealed panel. Recorded SHA256 witnesses:

```
sealed panel before = after:
de628779340b774440ab8e7b205e1b65081823de4951688cb58f18ee24dd4371
deep store before:
12cc30a28547c30d7effd0991c6dab773b419f36b2fc4cc2133069fc444d5d9f
deep store after:
c87c3c509703f8aec711363ca7fa81b8e9b2fdcaeb97612dd53634d3d77ca9bc
```

416 FINRA file requests, 96 sessions already covered, 552 historical/observed names,
6,669,373-byte final deep store. Scope was October 1, 2024-October 15, 2026.
At the source-backed design build, FINRA extended through October 16 but restored
raw prices through October 15. The October 15 result was 41.5133%, covering 499/503
names; its five-session -6.85712806 pp decomposed into -7.03640803 ratio effect,
+0.28317386 weight effect and -0.10389389 coverage/membership effect. These are
specific dated arithmetic observations, not current market calls.
