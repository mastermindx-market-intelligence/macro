# Macro opportunity-desk repair — September 21, 2026

Operation: `macro-hottest-desk-velocity-20260921-astra-001`.
Consumer carrier: macro #7520, `claude/us-sector-heating-order-r1`.
Received head: `053236460df537f04dc0f569ce445117955ee664`.
Reconciled main: `2b62f49603e731daf68877516d3f6f748497b160`.
Skillpack pin: Mastermind `6f321cb42166e4224e5107ac3312a6f7cd01fffa`.
Producer dependency: #7650, reviewed candidate
`ad4a8c32a79e1e919021fa9efce9beea33fc2c7c`.

## Why the old card was misleading

The live Macro card observed September 21 named Cybersecurity and said
“Running hot right now”, without its source date. The template selected the
first row of the heating strip, ordered by absolute rank and already capped
at four entries. That was not a full-population velocity or opportunity query.
The original #7520 fix separated heating from merely-hot incumbents, but did
not remove the first-row dependency or premature candidate truncation.

A second defect is owned by shared producer repair #7650. The observation is
September 18, but the archive ends September 17 and lacks September 15.
Counting archive rows used September 16 for “1d” and September 9 for “5d”.
The real session endpoints are September 17 and September 11. The early
+10 semiconductor latest-session claim is withdrawn.

Correctly dated observations, independently reproduced:

| Desk | Overall rank | Existing rating | Five-session rank rise | Latest-session rank rise |
|---|---:|---|---:|---:|
| Cybersecurity | 4 | Hold | +25 | -3 |
| Memory, HBM & Storage | 5 | Accumulate | +8 | +12 |
| AI Semiconductors | 6 | Accumulate | +14 | -1 |

Cybersecurity has the larger rank rebound overall; semiconductors is the
largest five-session climber among heating desks already rated Enter or
Accumulate. These closed-session observations do not establish September 21
intraday CPU leadership. Price/rank momentum does not establish fund inflows.

## Consumer behavior

`lib/sector_desk_view.py::opportunity_desk` consumes the full heating population
before the strip cap. Eligibility follows the existing Enter or Accumulate
rating. Largest positive five-session rank improvement determines the research
destination; latest-session change breaks a tie only when every co-leader has
that observation and the producer proves its date. Unresolved ties do not
manufacture a sole winner. Names, absolute rank and array order are not
selection privileges.

The consumer requires the #7650 contract: `history.basis=nyse_sessions` and
matching expected/observed comparison dates, checked against the existing
NYSE calendar. Old producers, missing history and wrong comparison dates
produce neutral Sector Central navigation, not relabeled row-offset data.
One dated session of publication lag is allowed; two missing completed
sessions suppress the opportunity claim. Invalid, future and non-session
source dates are neutral; weekends and holidays do not create false staleness.

The existing strip remains capped at four rows in producer order. Cooling,
the fixed software/hardware rotation lane, canonical scores, ranks, ratings,
sizing and trading gates are not changed by this consumer. Inputs are not
mutated. Routes use existing validated basket identifiers.

## Presentation

The existing card geometry, material, font, icon and interaction styles remain.
The card becomes **Opportunity watch · Accumulate rating**, with the full name,
“Up 14 places over 5 sessions · Sep 18”, and a direct “Explore this desk” link
to `basket/ai_semiconductors.html`. This is an existing desk rating, not a new
buy instruction. English and Chinese have parity. Missing, stale and tied
readings have neutral states. The source date remains visible. No whole-link
LENS handler is attached: browser testing proved it hijacks the first mobile
tap. The measured window and existing rating explain the card without requiring
a tooltip. No new CSS, scoring system or deployment hook is added.

## Ownership and verification

The local clock experiment was withdrawn when #7650's incumbent producer work
was discovered. #7520 has no competing `engine/sector_pulse.py` patch or
producer-test rewrite. Coordination receipts preserve the shared projection
and archive keep-FIRST law. This consumer is safe to render before #7650:
it does not advertise a winner without the producer's date proof.

Five consumer/regression suites passed **142 tests** after dependency
separation: new card tests, market-score authority, pulse wiring, dashboard
render and Risk dialog. The final card-only suite passed **55 tests**, including malformed-rating and
mobile-link guards. The canonical browser driver captured **8/8 states**, and
all eight first-click/tap navigation checks passed. Reviewed card crops and
provenance are committed under `research/sector_desk/opportunity_20260921/`.
The new card suite is explicitly wired into the existing CI guard and path
triggers. No test or dependency guard was disabled.

The integration probe loads the exact #7650 candidate with real committed
inputs, invokes the actual consumer adapter, and renders the new partial in
the committed full-page shell. This is candidate evidence, not a full data
rebuild or a production deployment. The canonical browser driver and separate
first-click/tap checks cover light/dark, English/Chinese and desktop/mobile.
Evidence root on Studio:
`/Users/chriswong/lanes/macro-hottest-desk-evidence-20260921-astra-001/`.

A broad local build was stopped and its tracked generated outputs restored.
No data/ledger or generated page output from that build is included in #7520.
Concluded exact-head CI, both accepted source changes, the normal renderer and
live verification are required before claiming this is deployed.

## Remaining product boundary

CPU-specific opportunities and capital flows need their own current,
coverage-qualified sources. Do not infer those from a basket rank change or
make every semiconductor subtheme inherit one basket's rating. Existing
subtheme/Prophet lanes retain that broader work; this repair neither consumes
their unaccepted outputs nor promotes a new investment policy.
