# US leadership incident: clock correction and integration boundary

## Scope and status

The Chairman's September 21 report concerns the entire path from concentrated
leadership to sector portrayal, stock discovery, entry decisions and outcomes.
This is a bounded source-integrity repair within that mandate, **not a declaration
that Prophet or the live dashboard is fixed**. Existing Prophet US / GMI / entry /
evaluation owners remain authoritative; no new program, score or publication plane
is created. Capability: **BUILT_NOT_PROVEN** pending exact-head review, CI and
production evidence. No trading recommendation or portfolio action was executed.

Protected procedure: `Mastermind@6f321cb42166e4224e5107ac3312a6f7cd01fffa`, verified
protected master, Skillpack 1.0.1/bootstrap 1. Same-pin INDEX, COLD_START,
ACTIVE_EXECUTION, WEB_CEO_DELEGATION and CLOSEOUT were consumed. Implementation
base: `macro@2b62f49603e731daf68877516d3f6f748497b160`. Material compatibility was
checked through `64799e9ecc0c9e56cdf5118fb06417fe8cd426cd`: no changes in the pulse
owner, its existing tests, signal archive owner or NYSE calendar. Direct execution
reason: PRINCIPAL_JUDGMENT / LOWER_TOTAL_OVERHEAD for this shared source seam.

## Reproduced defect, not a market opinion

At the implementation base, `site/basketdata/baskets.json` carries September 18
Theme Intelligence, while `data/signal_archive/baskets.parquet` ends September 17
and lacks September 15. The pulse reader previously selected comparison dates by
position from the archive tail, not from the current observation. Consequently:

- Its purported one-day semiconductor rank improvement of +10 used September 16,
  not September 17. The correct one-session comparison is -1 (rank 5 to rank 6).
- Missing archive sessions distorted longer windows. The correct September 18
  US five-/twenty-session endpoints are September 11 / August 20.
- Future archive rows could change the pulse attached to an older theme snapshot.
- Duplicate dates could manufacture apparent history; a pre-existing test fixture
  actually repeated one date six times and called it six sessions.
- An absent observation date was replaced by the wall-clock build date.
- Reader, enrichment and JSON writer duplicated this logic independently.

These are defects even when a correction does not improve a favored stock/theme's
reported velocity. Correct September 18 evidence is not September 21 intraday
evidence. A nightly ranking alone cannot establish the current-session CPU leader.

## Implemented canonical path

`engine/sector_pulse.py` now routes `build_pulse`,
`merge_pulse_into_theme_intel` and `write_pulse` through one internal projection.
The source observation date is mandatory and never manufactured. The archive is
ordered and deduplicated under its existing keep-FIRST rule; later observations
cannot leak into earlier theme reads. US comparisons use the existing
`lib.nyse_calendar.session_n_back` owner, preserving empty slots for unavailable
sessions rather than widening a one-/five-day window. Non-US regions retain their
own dated-observation convention rather than borrowing US exchange holidays.

The additive `history` object exposes the basis, actual comparison dates and
expected comparison dates. Missing evidence is null, not zero. The existing
schema, field names, heat thresholds, rank/score/label/recommendation fields and
consumer entry permissions remain unchanged. A failed/undated publication leaves
the prior dated file intact rather than stamping old evidence as current.

The original fixture was corrected to six distinct trading dates without removing
or weakening any assertion. No live data, generated site page, ledger, strategy
weight, entry gate, authorization path, deployment configuration was modified. The existing CI job and trigger
allowlist were extended to run both the previously unlisted pulse unit suite
and the new observation-clock suite; no existing check was removed or relaxed.

## Verification

`real_source_proof.json` binds all three immutable input blobs and the candidate
engine by SHA-256. Its reproducer invokes both old and new implementations on the
same real source data, with calibration enrichment omitted identically.

```sh
python3 research/sector_pulse/observation_clock_20260921/prove_observation_clock.py \
  --source-ref 2b62f49603e731daf68877516d3f6f748497b160 \
  --output /tmp/sector-pulse-observation-proof.json
```

All 49 themes preserve their canonical identity, rank, score, label and
recommendation. Representative date-corrected results:

| Theme | Rank | Previous reported 1d | Correct 1d | Correct 5d |
|---|---:|---:|---:|---:|
| AI Semiconductors | 6 | +10 | -1 | +14 |
| Cybersecurity | 4 | -3 | -3 | +25 |
| Memory, HBM & Storage | 5 | +19 | +12 | +8 |
| Magnificent Seven | 2 | 0 | 0 | +3 |

There is no claim of logged-at point-in-time replay, forward-return improvement,
live September 21 coverage or independent external review in this result.

- Unmodified pulse/consumer baseline: 79 passed.
- Initial new discriminators against old code: 16 failed, 8 passed.
- Final pulse/consumer/observation-clock tests: 118 passed, including 39 new cases.
- Python 3.14 with NYSE/calendar and actual dashboard-owner tests: **154 passed**.
- Python 3.12 pulse/consumer/clock/calendar suites: **138 passed**. The broader
  Python 3.12 dashboard suite could not collect because that interpreter lacks
  `plotly`; no dependency or test was disabled. The same dashboard-owner tests
  passed under Python 3.14. Full configured CI is still owed.

Stored `verification.txt` records the exact successful commands and outputs.

## Other source-proven failure mechanisms, not silently promoted here

**Relative strength is not absolute price extension.** The US path in
`engine/theme_scoring.py` excludes US from its `ext_abs` calculation and falls back
to `rs_pctile` in `_extended` / `_reco`. The same synthetic dominant, above-trend
input at relative-strength percentile .95 gives HOLD under the US legacy gate;
adding an own-price extension of .5 gives ACCUMULATE under the existing absolute
extension path. The reproducer records this discriminator. It is not a measured
US price, a validated threshold change or permission to promote that policy.
A versioned same-cohort comparison must separate leadership from genuine gap,
volatility and own-trend extension while preserving drawdown protections.

**Discovery is being capped before final scoring.** Existing candidate-visibility
carrier #7572 at `44ee80f30878d5709a24afb9f21866644ac22960` documents 66 eligible
September 18 names, 52 main-list and 14 off-list. AMD was T1-eligible at pre-cap
position 26 and excluded by `sector_cap_overflow`, without a final Prophet score.
That carrier already implements searchable visibility and conversion tracing;
do not rebuild it. Scoring all eligible names changes percentile denominators,
so any full-cohort-before-cap challenger must be versioned and evaluated before
replacing current scoring. Portfolio concentration limits belong after discovery,
not as unreported erasure of evidence.

**The live US ranker has no usable theme-structure family.**
`engine/us_prophet_fusion.py` marks F3_THEME_STRUCTURE absent from the candidate
frame. Broad sector identity does not substitute for CPU, GPU, memory, networking,
semiconductor equipment or AI build-out evidence. Consume canonical point-in-time
memberships and existing GMI/F04 evidence; do not create a duplicate theme state,
an AI narrative bonus or count the same price momentum twice.

**The UI confuses clocks and decisions.** `scripts/build_site.py`'s sector heat
view and the dashboard hottest-desk card consume closed-session pulse data.
The existing `engine/neuralweb/market_packet.py` leaders path correctly uses the
intraday basket pulse instead of nightly heat for today's moves. Keep the existing
owner and its data rights; do not bolt on a parallel live-leader service. A missing
clean-entry flag also does not establish that price is literally overextended.
The differing buy counts in the supplied screenshots require same-universe,
same-session reconciliation before declaring them an arithmetic defect.

## Integration order and acceptance, using existing carriers

1. **Current-session leadership / freshness:** coordinate this source correction
   with hottest-desk #7520, publication #7211 and existing selective-risk carriers.
   Preserve their actual write custody. Show current tape, prior-close trend and
   quote/source times explicitly; do not make a stale nightly winner sound live.
   The exact wrong +10 semiconductor comparison was reported to #7520 in comment
   `5768028874`; it must not become a frozen acceptance fixture.
2. **Risk scope and entry reasons:** broad fragility is not proof that all sectors
   lack opportunity. Show market risk, theme participation/leadership and specific
   entry state separately. Distinguish leading/entry-open, leading/wait-for-trigger,
   leading/price-extended, nonleader and unavailable. No text says 'breadth lines up'
   when the supporting breadth leg is actually weak. Flow claims require actual
   flow evidence; price/volume acceleration must not be mislabeled fund inflows.
3. **Prophet discovery and rank input:** converge #7572, #7604, early-subtheme #7455,
   entry #7508 and independent acceptance #7453. Measure candidate loss at universe,
   membership, evidence, screen, pre-cap, scoring, entry and presentation stages.
   Every exclusion needs a dated, readable reason. Off-cohort unscored is not zero.
4. **Behavioral promotion:** compare the frozen incumbent with a versioned
   alternative on the same point-in-time universe and decision times. Assess
   discovery latency, recall of eligible emerging leaders, false-breakout rate,
   excessive-chase incidence, adverse excursion, turnover and net-of-cost outcomes.
   Include concentrated rallies and reversals outside semiconductors. Today's
   winning names are diagnostics, not a training whitelist or retrospective proof.

Release acceptance requires exact-head tests/review and authorized deployed
producer-to-consumer/browser evidence, including missing/stale/closed-session
states. The live market-risk score, stock ranks and allocation rules are not
changed by this patch. **MISSION_COMPLETE: false.**
