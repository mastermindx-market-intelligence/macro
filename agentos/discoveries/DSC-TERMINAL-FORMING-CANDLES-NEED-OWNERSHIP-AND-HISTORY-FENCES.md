---
key: TERMINAL-FORMING-CANDLES-NEED-OWNERSHIP-AND-HISTORY-FENCES
claim: Complete forming candles require disjoint historical and stream ownership, correction-aware revisions, and an authoritative-history fence; price-only snapshots also require a pane-qualified observation-order boundary.
falsifier: Run `npm test` from hub and `npx vitest run lib/__tests__/liveCandle.test.ts lib/__tests__/formingCandles.test.ts lib/__tests__/liveSplice.test.ts lib/__tests__/candleCalendar.test.ts` from terminal at Terminal #1102; a raced seed, overlapping volume, retained snapshot overwriting accepted history, old correction advancing the quote clock, or countdown outside the canonical bucket disproves the corresponding invariant. Also run the 47 liveCandleSnapshot cases at PR 1108 protected merge 061e7625536d781239cbf687bea64a2e1076202a; an older response repainting a newer same-price observation, an inadmissible overnight tick consuming an older native revision, or snapshot volume treated as complete falsifies the added ordering and coverage invariants.
so_what: Preserve coverage, generation/revision identity, raced-seed invalidation, accepted-history fences, and source-qualified snapshot ordering when changing live charts; derive countdowns from the existing calendar and resamplers before introducing faster transport.
kind: architecture
verified_at: 2026-10-22
verified_by: Terminal PR 1102 reviewed at ca0b9f0f84d2ebbc55506df5ee7e78ba54ad0891 and merged as ab5beab6b0c2362414a1da17745587d490e923e8 with identical git tree; all 16 jobs in CI run 39644751193 succeeded; independent executable contract review at a0ce3290eaeada2d3f57a6e651dc47a85a859b22; final focused 176-test suite and Hub 617-test suite. PR 1108 candidate 845e2b558d42f4c80d0108a93cc51ac3235a9631 passed 119 focused tests, TypeScript, and six responsive browser cases; all seven follow-up files match final CI head 1912800565687e420e5a24e35b526525cb28276a and protected merge 061e7625536d781239cbf687bea64a2e1076202a. All 17 jobs in final CI run 39708563796 passed; the tested and merged trees both equal 4a123ffb346c6c0e54581a3a7a7ee5d1927dde3b.
scope:
  - terminal/hub/lib/formingCandles.js
  - terminal/hub/lib/polygon.js
  - terminal/terminal/lib/formingCandles.ts
  - terminal/terminal/lib/liveCandle.ts
  - terminal/terminal/lib/candleCalendar.ts
  - terminal/terminal/components/ChartPanel.tsx
confidence: verified
---

# Forming candles require ownership and an accepted-history fence

## Finding

A moving last price does not by itself maintain a truthful forming candle. Polling
only the latest second can miss highs, lows, and volume. Late corrections,
reconnects, REST responses arriving after newer stream data, and background history
refreshes can then overwrite accepted OHLCV or count overlapping volume twice.

[Terminal PR 1102](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1102)
implements the first forming-candle slice using the existing roughly one-second
chart polling path and existing native U.S. aggregate entitlement. The chart's
incumbent derivation boundary remains the owner of candle, indicator, table, and
synchronization updates.

## The data contract

The Hub materializes a bounded current-session snapshot from a closed-minute REST
prefix and a disjoint stream suffix. Generation, revision, coverage, and seam
metadata describe what the producer knows. The public quote route projects only
selected chart timeframes with the existing resamplers; raw UTC component arrays
stay inside the Hub-to-route boundary.

Complete snapshots replace exact OHLCV, including corrections that retract an
extreme or reduce volume. Partial snapshots preserve an opaque accepted-history
baseline and do not add overlapping volume as though complete coverage were known.
New producer generations start from the currently accepted bars. Exact duplicate
generation/revision observations are no-ops.

A REST seed changes ownership only if the response is still coherent with the
stream. If a relevant correction arrives during the fetch, the response is
discarded before installation and a bounded retry repairs the seam. Installing the
stale prefix under a partial label would still destroy newer information.

A valid old aggregate must reach repair before the quote-freshness guard. It can
repair an opaque or expired minute without becoming a new last price or advancing
the quote timestamp. Malformed and future windows remain rejected.

Implementation:
[Hub owner](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ca0b9f0f84d2ebbc55506df5ee7e78ba54ad0891/hub/lib/formingCandles.js),
[adapter](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ca0b9f0f84d2ebbc55506df5ee7e78ba54ad0891/hub/lib/polygon.js),
[projection](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ca0b9f0f84d2ebbc55506df5ee7e78ba54ad0891/terminal/lib/formingCandles.ts).

## Accepted history is a new boundary

Whenever authoritative history is accepted, the reducer records the retained
snapshot's generation, revision, and timestamp. That already-known snapshot cannot
overwrite the new history on the next quote poll. A newer measured price can still
advance the close while carrying the retained snapshot; it cannot replace the
refreshed open, extrema, or volume.

This fence applies to initial intraday history, daily splicing, and accepted 24H
background observations, including observations whose arrays compare equal.
Without the equal-observation case, a refresh can silently fail to establish the
boundary even though it authoritatively confirmed the bars.

The independent executable review preserved H120 / C103 / V45 through a raced
seed, then joined a coherent retry. A seven-minute-old correction repaired its
minute without advancing the live quote. A retained-snapshot/history reproduction
advanced C110 to C111 while preserving H120 / L95 / V2000; repeating it was a no-op.
The extracted daily splice passed the corresponding fence check.

Implementation:
[reducer](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ca0b9f0f84d2ebbc55506df5ee7e78ba54ad0891/terminal/lib/liveCandle.ts),
[ChartPanel](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ca0b9f0f84d2ebbc55506df5ee7e78ba54ad0891/terminal/components/ChartPanel.tsx).
Related: DSC:TERMINAL-LIVE-BAR-MOVED-ONLY-THE-CANDLE and
DEC:TERMINAL-ONE-LIVE-BAR-DERIVATION-BOUNDARY.

## Price-only observations need their own ordering boundary

The PR 1102 production observation paired a changing `polygon-snapshot-rt` last
price with a separate delayed extended quote. The reducer required an explicit
LIVE extended value in pre/post sessions, so it ignored the otherwise usable
snapshot print and the candle stayed at its loaded history.

[Terminal PR 1108](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1108)
admits that fallback only when the exact source is `polygon-snapshot-rt`, the
measured basis is `REALTIME`, price is finite and positive, and an explicit
`asOfMs` identifies the print. The observation may be at most 120 seconds old or
five seconds in the future. Its actual print time must fall in the canonical
pre/post phase of an explicitly enabled U.S. ETH/24H minute or hour pane. A
response-level `marketSession` label is insufficient. Existing admissible LIVE
extended quotes retain precedence.

A price-only observation preserves accepted open and volume, expands observed
extrema, and updates close. A newly observed bucket has zero known volume; no
missing buckets are fabricated. Both the bar and mutation report partial
coverage. A newer same-price response advances the observation floor even when
there is no chart mutation, so a later-arriving older response cannot repaint it.

An explicit extended tick may bypass the native handoff floor only after passing
the selected pane's history, phase, bucket, and tail checks. In the verified
counterexample, an overnight BOATS tick was inadmissible to an ETH-only pane but
previously let an older native revision overwrite a newer pre/post observation.
The repaired admission order rejects the older handoff before consuming its
revision, while preserving genuinely admissible extended-tick precedence.

The 47 snapshot regressions and six responsive browser cases exercise these
boundaries. The browser cases inspect the actual rendered price-series tail and
synchronization lookup, preserved preceding bar, one minute rollover, and
countdown `00:50 → 00:40 → 00:58`. These are deterministic fixture observations,
separate from a future live-market proof of the deployed follow-up.

## The countdown belongs to the plotted candle

Countdowns must follow the same session and resampling rules as the candle they
describe. A display epoch is not necessarily a true UTC instant. Daylight-saving
changes, shortened U.S. sessions, HK segment anchors, CN close clipping, and the
published 2D/3D anchor must remain consistent with historical construction.

The shared calendar uses the incumbent session and resampling owners. A weekly or
monthly candle's last observed member is a plotted label, not independent evidence
of the period's final eligible session. Sparse non-U.S. observations do not
establish an exact future close. Where authoritative calendar coverage is missing,
an exact countdown is absent; U.S. holidays and guessed weekdays are not borrowed.

The independent calendar review accepted the implementation with bounded
qualifications. That acceptance is code-review evidence, separate from the
executed 37 calendar tests and the production observations.

Implementation:
[calendar](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/ca0b9f0f84d2ebbc55506df5ee7e78ba54ad0891/terminal/lib/candleCalendar.ts).

## Publication and activation are separate contracts

The initial PR 1102 production inspection on 2026-10-21 found that the live Hub
intentionally uses the delayed AM socket while its separate real-time REST
snapshot leg has an 8000 ms TTL. That TTL does not guarantee an eight-second
price-change or refresh cadence. The Next process does not inherit the
Hub's environment file, so the historical seconds band remains disabled. This split
is recorded in WS:STOCK-DOSSIER-LIVE-QUOTE and its 2026-08-28 handoff.

The plan of record, `research/MASSIVE_ADVANCED_INTEGRATION_MASTERPLAN_BY_FABLE.md`
section 3.1b, reserves the real-time vendor socket for the TP-1 ingest owner and pins
Hub to delayed until it consumes the shared producer. Enabling a second live socket
is not a routine feature flag change. This slice preserves that boundary; complete
native forming snapshots are implemented and deterministically proved, but their
production activation cannot be inferred from this deployment.

The new quote projection must also preserve the existing access contract. It now
authenticates before every cache read when authentication is required, fails closed
on verification errors, and checks the Next seconds-band capability before serving
either fresh or cached second-resolution projections. A disabled mixed selection
receives an atomic empty response naming the disabled timeframes; it is not silently
reshaped into a partially fulfilled request. Minute/hour and ordinary quotes retain
their existing public behavior with the seconds switch off.

Six regressions reproduced the pre-repair access gaps. The final 21 quote-route
tests cover cold and warm requests, both response shapes, mixed selections,
capability changes, auth changes, error and thrown-auth paths, and preserved public
minute/ordinary behavior.


The inspected TP-1 revision does not provide a ready adapter input. At Macro
PR 8660 head `6cc0858fa93fa3200268390c9588bcc67358eb23`, its
[README](https://github.com/mastermindx-market-intelligence/macro/blob/6cc0858fa93fa3200268390c9588bcc67358eb23/engine/tick_plane/README.md)
explicitly describes pure source components with no deployed publication. Its
minute projection requires an already-matured minute and produces pressure-context
counts, notional, and native-share denominators, not unfinished OHLCV. The
[activation record](https://github.com/mastermindx-market-intelligence/macro/blob/6cc0858fa93fa3200268390c9588bcc67358eb23/ops/TP1_EQUITY_SOURCE_ACTIVATION.md)
also records the missing admitted runtime/publication. A fresh PR-state read on
2026-10-22 found PR 8660 still open and draft at that same immutable head.
Those dated source records and the fresh PR-state read are not a census of the
current socket holder. A future candle integration must
resolve current source custody and provide an admitted forming-OHLCV publication;
it cannot reinterpret mature pressure-context minutes as candle bars.

## Verification boundary

The PR 1102 source passed 617 Hub tests, the final focused 176-test Terminal suite,
the final 23 evidence/publication checks, production build, and post-build
TypeScript. Responsive candle/indicator/table checks passed 15 cases with zero
retries; Visual Intelligence passed 30 English/Chinese cases. Thirty-five required
screenshots were genuinely recaptured, with prior historical qualifications kept.

PR 1102 was deployed successfully and independently identified at
2026-10-21T22:00:21Z. Seven installed source hashes, canonical HEAD, deployment
marker, and public page/chunk IDs matched its protected squash. Its subsequent
API observation found changing measured prices and no native forming snapshots;
its UI observation exposed the pre/post consumer defect repaired by PR 1108.

The follow-up's 119 local tests, TypeScript check, six browser cases, and all 17
jobs in final CI run 39708563796 establish the tested behavior. PR 1108 merged
as `061e7625536d781239cbf687bea64a2e1076202a`; its tree exactly matches the
CI-tested head. The release owner exited 0 at 2026-10-22T03:02:08Z, followed
by independent installed/public identity, compiled-asset hash, API-contract, and
fresh-browser delivery checks. The API observation contained 38 HTTP 200 responses
from the closed overnight path, all carrying a delayed snapshot and no native
forming payload. The 1m ETH chart rendered its completed historical bar without
console errors. This is delivery and closed-session evidence; positive pre/post
price movement and rollover remain unverified. None establishes native complete
OHLCV publication or tick-complete coverage. Exact receipts and observed values
are recorded in the associated handoff.
