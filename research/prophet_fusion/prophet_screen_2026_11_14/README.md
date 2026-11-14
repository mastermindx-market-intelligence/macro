# Prophet screenshot study: recovered source and actual context integration

Status: **original source recovered; metadata consumer executed; no new outcome test**.
Continuation of Macro #11241 recovery comment
[6874456598](https://github.com/mastermindx-market-intelligence/macro/pull/11241#issuecomment-6874456598)
and team return
[6874394466](https://github.com/mastermindx-market-intelligence/macro/issues/11014#issuecomment-6874394466).
Protected procedure for this continuation: Mastermind
576d70957cd5c02f65e04785111665f2bd6153a1.

## Owner and source

The source belongs to the Prophet programme on Ubuntu2, not Sector Intelligence.
The original archive is
/home/ubuntu2/tmp/rotation-core/v4/catalogue/trough/.
The native detector checkout is ext/macro_main_e999086d at
e999086d3fb1d627ff4eda4a2206c59884389b37.
Its engine/stock_identity/replay/grey_dot.py SHA256 is
0419d7c0a5624ea134d48e650ba97139ad2b231953f51612c59a76b5bd27611a.

source_manifest.json binds the exact original files and 15 original method/report
documents. Its SHA256 is
6215ac12fa47ab594f424295365e72c6e71865d5c7a6bd9986df23b6f9aada6c.
The source/ snapshots preserve original bytes. They are historical evidence, not
new instructions, registrations or replacements for the programme's current source.

| Original artifact | Original population / purpose | SHA256 |
| --- | --- | --- |
| events_v1/EVENTS_G3.parquet | 35,465 retained G3 events, 2013–2023; only SCREEN metadata is projected here | bad2ff33eeacfc073960fbfcdded814ccc566d7772740d0fe119707b510727f3 |
| events_v1/FULL_GUARD_RESULTS.parquet | Same-date prefix checks, including rejected candidates | 4abb5a80e3d832655b9fef19d65e4c4c050f6ade87c5c0a2f7a9755fd94513a5 |
| dot_gate_1/ANALYTIC_EVENTS.parquet | 21,773 original primary SCREEN events | 96d8464a7b43be23f2b26ec05e7e17c2e8f8aab24324a6356b7d2407f325d3c4 |
| events_v1/EVENT_GATE_COLS.parquet | Original leave-one-out feature seam; not decoded by this adapter | 3af7a492e40244f90796fe6fce0527ac2647cd1951aa71834dfe7715e208b4db |
| events_v1/SCREEN_T1_T2_DESCRIPTION.parquet | Original lead/lag description; no outcome columns decoded here | fbbe8af4e30de14a59de9b99a84ea5ec6bc8a9d2c179ba7bbd180946e334ba25 |

## Exact screenshot match and label contract

The source DOT-GATE-1 report has ANY = **14,441** and A4 = **7,332**.
They partition **21,773 unique events**. A1–A3 can overlap; ANY is their union.
A4 means all three are false only where the native gates are defined.
The adapter retains **23,065 SCREEN events** and leaves the other **1,292**
unclassified. Original primary-analysis membership is not prospective eligibility.

The other screenshot matches events_v1/T1_COMPARISON.md: G3 T1 has 22,313 dots,
11,455 matched, median lead 9 sessions, and mean captured pre-T1 move 0.046872.
Its separately defined extra-false-call share is 0.445256; it is not the unmatched
fraction. These are readbacks of the original report, not a repeated study.

PLAN_TROUGH_v1.md defines the native primary label real63 at 1.0 ATR_c:
the trailing ten-close trough must not be undercut by more than 1.0 ATR_c over the
next 63 sessions. ATR_c is the 14-session mean absolute close change, not true
range. real21 and the 0.5/2.0 multipliers are ancillary/descriptive. The original
leader ruling purges SCREEN events whose 63-session label would cross
2020-01-02. No label is recomputed or joined by this integration.

The G3 table is the locked Terminal twin: a 3D StochRSI K/D cross, D below 20 within
eight bars, and a strictly rising 2D RSI-MACD histogram. Same-stock/grid dots
within five sessions are folded into the first. Amber washout context is a feature,
not a population filter. This does not equate native developing-bar Terminal
observations with completed replay, Macro G0, or a replacement live detector.

## What the known-time proof establishes

- Native date is the declared known date; bar_label is a separate display label.
- Every exported event matches its original event ID, ticker and date in a true
  FULL_GUARD_RESULTS row. Source digests are checked before and after projection.
- The original guard re-ran retained dots on prices truncated to that date.
  This establishes same-date prefix visibility, not an original first-seen receipt.
- The trailing two-session bin caveat remains: delayed live dots can be missing.
  The source's roughly one-in-ten estimate is synthetic, not a measured census error.
- Original coverage grades remain explicit. “Usable” is the source's designation
  for 2018–19 in this window; 2013–17 is survivor-biased.
- The historical source predates W1's split-calendar and issuer-seam quarantine.
  The new join does not repair or silently certify those original events.

No research ID is converted into a newly derived EntryEvent ID, appended to a
native observation store, or given fabricated first-observation/finality evidence.

## Registration recovered, not recreated

original_registration.jsonl preserves 15 exact original registry lines, with
line numbers, IDs, times and source-at-read digest in registration_receipt.json.
The canonical registry remains /home/ubuntu2/tmp/rotation-core/v4/trials.jsonl.

The records include the plan approval, DOT-GATE-1 addendum, run-notes/brief approvals,
the G1a mixed-cluster ruling, the original completion and leader acceptance, and the
three missing LSI gate rows. The source snapshots retain the underlying documents.

The counting family has four comparisons, Bonferroni .10/4. Under governing G1a,
event flags remain fixed while whole basket-day outcome blocks are permuted among
equal-size clusters. The mechanical fallback to same ISO-week × exact cluster size
was fixed before the reported p-values when within-day immobility exceeded 25%.
There are 20,000 two-sided draws and a whole-month 2,000-draw bootstrap.
The original immobility limitation remains; the intervals are not simultaneous.

A2/A3 use per-basket SCREEN80 cuts fitted over the full development window,
applied to leave-one-out measurements. They are retrospective development fits.
Gate-undefined is not A4. DOT-GATE-1 and the stock-feature BH family cannot count
the same gate evidence twice. Basket gates have no released HOLD claim here.

The original verdict is preserved: **no measurable benefit at this power**.
Original ANY centered real63 contrast is −0.0861704 percentage points, with
95% interval −1.548704 to +1.390052 points, counting p .8269087, and MDE 2.799220
points. The original weakest-relative-strength comparator and fwd63 guard did not
establish the required joint result. These are historical report facts, not new
inference from this join or an interchangeable restatement of an at21 screenshot.

## Actual consumer proof

scripts/prophet_fusion_screen_source.py extracts only explicit metadata projections
from EVENTS_G3, FULL_GUARD_RESULTS and ANALYTIC_EVENTS. Arrow applies the SCREEN
date predicate before conversion to pandas. No outcome column is decoded.
This does not claim Arrow performs zero physical decoding of excluded metadata
inside a Parquet row group.

The code-pinned manifest, caller-pinned export receipt, extractor hash, schema
allowlist, physical export row count, source digests, identity-set digest and
primary partition all qualify the input. A substituted receipt or extra
out-of-window export row cannot silently narrow the population.

The consumer reuses read_inputs and implied_volatility_trajectory at native data
pin 6bbc4b0fc694c847077661ff5bf4c19ea41e4e81. It joins on the declared date to
context already lagged one expected NYSE session. It never applies a second lag,
uses an as-of fill, or makes “common session” mean only dates with both feeds present.

| Population | Total retained | Joined date proxy | Incomplete context |
| --- | ---: | ---: | ---: |
| All original SCREEN events | 23,065 | 22,860 | 205 |
| Original primary analytic subset | 21,773 | 21,573 | 200 |
| Outside original primary analysis | 1,292 | 1,287 | 5 |

All original IDs survive, with set SHA256
c57c4c9681f167a46b6381c9d6adc973a6391ee070a42b809be2c7e7c78881c1.
context_report.json includes native grade breakdowns and direction counts; these
are coverage/composition diagnostics, not predictive results. metadata_receipt.json
and consumer_receipt.json bind the actual run. Only aggregate evidence and receipts
are committed; metadata exports remain disposable consumer inputs.

Qualification: **91 focused tests passed**, including altered-source/receipt refusal,
guard identity/date disagreement, overlapping or undefined primary classes,
unexpected outcome columns, extra out-of-SCREEN rows, source changes during reads,
same-day/double lag, missing observations, retained invalid/unknown dates, and the
actual synthetic Parquet-to-report path. The real source consumer separately
completed successfully. The existing prophet-lab CODE job owns these tests.

## Reproduction and next boundary

Run the extractor against the original source using its existing Python environment
and an exact copy of this script/manifest. It refuses an existing export directory
or any output inside the source archive. Then transfer only metadata.parquet and
receipt.json and supply the independently recorded receipt SHA256 to report mode.
The actual extraction/consumer paths and hashes are in consumer_receipt.json.

Example consumer shape:

    python3 scripts/prophet_fusion_screen_source.py report \
      --metadata /path/to/verified/metadata-directory \
      --manifest research/prophet_fusion/prophet_screen_2026_11_14/source_manifest.json \
      --receipt-sha256 <recorded-receipt-sha256> \
      --out /tmp/prophet-screen-context-report

The existing W1 brief is preserved separately with its own digest in
registration_receipt.json. It fixes m=44 and explicitly excludes day-constant
VIX-related columns from that within-day screen. The accompanying context-test
proposal is unexecuted and cannot alter W1, append to its ledger, or consume a
holdout. The next predictive comparison must use the incumbent programme's
registration, split/identity qualification, family budget and execution authority.

#11242 remains on its original armed carrier. No sibling branch, accepted pilot,
stock-price store, holdout, live gate, rank, size, order or original trial is changed.
