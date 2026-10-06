# Prophet NVDA Pro Re-Audit — Detection, Rerating, Origination, and Reproducibility

**Date:** 2026-10-06  
**Status:** research / evaluation only; zero score, rank, gate, trading, deployment, or promotion authority  
**Canonical carrier:** draft PR #8495  
**Primary historical source pin:** `mastermindx-market-intelligence/macro@2f2feec4851b45636f63a48ec61e6f0b02b8118a`  
**Protected procedure pin for resumed Pro study:** `mastermindx-market-intelligence/Mastermind@7c12c394b38f52cf6bfc953379535eb2c7a496f2`

## Why this re-audit exists

The first golden-case study established that Prophet noticed NVDA before the subsequent run and that the final Sep-25 configuration was unusually strong across several evidence families. The Pro-mode re-audit stress-tested three things that the first report had not cleanly separated:

1. **Detection success** — did the system identify an important emerging NVDA opportunity before the move?
2. **Executable-entry success** — was there a contemporaneous actionable entry available to an operator before the move?
3. **Plan-origination success** — did the formal Prophet plan system publish a valid plan while that entry was still available?

These are not the same claim.

The re-audit also re-measured the “T2 + news” discovery using absolute returns, SPY-relative returns, sector-relative returns and issuer-deduplicated episodes, and tested whether a broader “rerating” composite generalizes the finding.

---

# 1. Revised executive ruling

## 1.1 Detection: **YES — strongly supported**

The Prophet / Entry Signal stack had NVDA in an actionable state before the major continuation.

The strongest pre-move forensic receipt is not the Sep-26 finalized plan. It is the watchlist sentinel alert first committed on Sep 25 before the US market open:

- alert timestamp: **2026-09-25T09:02:33Z**
- first Git appearance: commit `a374fd966466d342154e5147efec48281f77b501`
- commit time: **2026-09-25T02:20:03-07:00** = 09:20:03 UTC / 05:20:03 ET
- alert: `buy_zone_enter`
- ticker: NVDA
- state: `entry_status=buy_now; gate_tier=T1`

The producer stamps `ts` with `datetime.now(timezone.utc)`, so this timestamp is a real wall-clock generation time, not the marketing layer's date-only synthetic stamp.

The sentinel was reading the committed board, not inventing a separate trading rule.

## 1.2 Executable entry: **YES for the broader Entry Signal stack, with a freshness caveat**

The board state feeding the alert carried:

- board as-of: 2026-09-23
- NVDA price: 228.87
- signal basis: 2026-09-22
- state: FRESH BUY / BUY ZONE
- T1 shallow
- entry status: `buy_now`
- entry z: 72.9
- buy zone: **$223.30–$228.90**
- chase above: **$231.10**
- conviction: 49 / constructive

NVDA opened Sep 25 around **$225.13**, inside that published buy zone and below the no-chase ceiling.

Therefore the system did surface an actionable, non-chasing entry before the subsequent move.

**Caveat:** the board was stale/mixed-vintage. That same staleness correctly prevented the formal plan originator from publishing a new trade plan. So this is evidence of useful early detection and entry intelligence, but also evidence that freshness controls across surfaces were inconsistent.

## 1.3 Formal Prophet plan origination: **LATE**

The new plan `NVDA-BULL-20260917` did not exist before Sep 26.

Git history:

- first add: `74e8f45060e815a2cb7c515ae09f258919ab9da2`
- commit time: 2026-09-26T10:51:05-07:00
- plan `recorded_at`: 2026-09-26
- price basis / entry date: 2026-09-25
- final entry: ~225.10
- final no-chase ceiling: 226.90

By the next regular session, Sep 28, NVDA opened above that final plan's no-chase ceiling and did not trade back below it during the regular session.

Therefore:

> **The Sep-26 finalized plan is excellent detection / historical-plan evidence, but not proof that an operator receiving the plan for the first time could execute its stated entry.**

The earlier Sep-25 watchlist/Entry Signal receipt is the evidence that the system actually exposed a tradable window before the move.

---

# 2. Why formal plan origination lagged

This is now exactly identified.

The Sep-25 Prophet intake did **not** reject NVDA on selection quality.

It admitted NVDA and then failed plan validation because its source board was stale/mixed-vintage.

At the Sep-25 durable checkpoint `4a1882bf510a642674d110c3c5c5dec3111e8ea2`:

- run as-of: 2026-09-25
- `source_asof`: 2026-09-21
- `source_board_asof`: 2026-09-23
- `source_delayed`: true
- `source_mixed_vintage`: true
- admitted candidates: 41
- eligible after duplicate/open-plan skips: 15
- **validation failures: 15**
- originated plans: **0**

NVDA's exact validation failure:

- stale price-basis date;
- mixed-vintage board;
- delayed ranked-price vintage;
- tier-observed date did not match the price-basis date.

Its receipt says:

> cleared every check; plan_not_built

This was not a mysterious ranking failure.

It was a deliberate **clock-provenance safety refusal**.

Later Sep-25 checkpoints still carried `mixed_vintage=true` and originated zero plans. On Sep 26, when the source became clean and current:

- `source_asof`: 2026-09-25
- `source_board_asof`: 2026-09-25
- delayed: false
- mixed vintage: false
- 22 plans originated, including NVDA.

### Important falsified hypothesis

The older August NVDA plan did **not** block re-origination.

The August plan `NVDA-BULL-20260805` had already been closed by the forward ledger:

- close date: 2026-09-21
- outcome: EXPIRED
- ledger as-of: 2026-09-22

So the slot was available.

### Architectural ruling

The formal-plan lag came from **upstream source freshness / mixed-vintage state**, not from:

- C1 rank;
- T tier;
- conviction;
- duplicate plan suppression;
- a plan-count cap.

The clock-provenance validator behaved correctly. The defect is that the earlier alert surface could still present stale board state as an actionable `buy_now` without equally prominent freshness gating.

This must be solved through the existing freshness/data owners — not by weakening plan validation.

---

# 3. The actual causal anatomy of the NVDA win

The golden case is best understood as several linked mechanisms with distinct jobs.

## Layer A — opportunity recognition (“WHY THIS NAME?”)

NVDA was overdetermined across multiple independent evidence families.

Final Sep-25 C1 family contributions:

- F1 Technical Confluence: 71.59
- F2 Momentum / Extension: 68.84
- F4 Catalyst / Event: 93.48
- F5 Flow / Positioning: 69.93
- F8 Attention / Crowding: 98.55

No single family was necessary to keep NVDA near the top.

Leave-one-family-out kept NVDA rank #1 for every individual family removal.

### Important semantic corrections

**F8 news_burst was attention, not bullish sentiment.**

NVDA's exact row:

- n_recent: 6
- sentiment_lean: neutral
- n_pos: 0
- n_neg: 0

Therefore the useful concept is not “bullish news”.

It is closer to **abnormally high information/attention arrival around an already-important name**.

**F4 earnings evidence for NVDA was positive-relative.**

- `sue_z = +1.47` on the final row.
- An earlier Sep-23 board read carried +1.89.

However, the legacy `sue_fresh` boolean in the historical fusion race used truthiness of any nonzero `sue_z`, so the broader historical feature should not be interpreted as “positive earnings surprise” without correction.

Current source contains a corrected versioned earnings observation that requires z > 0, but it explicitly has no live authority by default.

Thus:

- NVDA's own earnings leg is directionally supportive;
- the historical `sue_fresh` cohort is semantically noisier than the label implies.

**F5 smart-money evidence for NVDA was genuinely additive.**

NVDA's chip:

- action: add
- one A/B-grade tracked fund adding
- best fund: Soros Fund Management
- period_end: 2026-06-30

The generic fusion extractor uses `bool(smartmoney_chip)`, but the upstream producer only creates the chip from A/B-grade holders with action `new` or `add`.

So this is not a direction bug.

It is, however, stale 13F evidence, not current flow.

**Options were negative, not explanatory.**

NVDA carried:

- GEX verdict: caution
- deep long gamma
- explicit dealer pin/fade-breakout warning
- call wall around 230

The win therefore did not require all evidence families to agree.

---

## Layer B — ignition / timing (“WHY NOW?”)

The critical action state changed sharply while the stock itself moved very little.

The earlier audit measured:

- provisional T3 -> confirmed T2
- extended -> partial
- act level 0 -> 3
- entry z ~-32 -> +64
- conviction low -> constructive
- cycle blocked -> open

The name-level opportunity substrate did not change nearly as much as the timing trigger.

This supports a two-factor causal interpretation:

> **importance/opportunity was already present; timing unlocked action.**

T2 itself is not the whole cause because T3 is already an admitted tier.

The load-bearing plan-admission changes were the conviction and entry-status transitions.

---

## Layer C — action geometry (“CAN I ENTER WITHOUT CHASING?”)

The system separated “interesting” from “enterable” using:

- buy zone;
- chase ceiling;
- stop/invalidation;
- partial vs full entry state.

This is essential and should remain separate from ignition probability.

The best future product state is still:

> **Important emerging ignition candidate — entry not open yet.**

A candidate should be allowed to score extremely high on emergence/ignition without weakening Entry Availability.

---

# 4. Re-measurement of the T2 + news result

The earlier headline “90.9% win rate” was too loose.

The exact historical v3 H=5 T2+news cohort is:

- 11 board rows
- 7 unique issuers
- 8/11 positive **absolute** five-session returns
- 10/11 positive **excess vs SPY**
- 9/11 positive **sector-relative excess**
- mean SPY excess: +3.58%

Deduplicating to first observation per issuer:

- 7 issuers
- 4/7 positive absolute returns
- 6/7 positive SPY excess
- 5/7 positive sector excess
- mean SPY excess: +3.82%

So the correct statement is:

> **T2+news showed unusually strong short-horizon relative performance in a tiny discovery sample. It did not produce a 90.9% profitable-trade rate.**

### H=10 weakens materially

At 10 sessions:

- 10 rows / 6 issuers
- 5/10 positive absolute returns
- 5/10 positive SPY excess
- mean excess +0.84%

Removing INTC:

- 9 rows
- 4/9 positive excess
- mean excess **-1.28%**

The ten-session mean is therefore heavily dependent on one large INTC outcome.

This reinforces the interpretation that the finding, if real, is an **ignition / immediate follow-through** pattern, not yet a persistence signal.

---

# 5. Does “rerating” generalize beyond ticker news?

The Chairman correctly proposed that many winners rerate because of:

- earnings/guidance;
- analyst revisions;
- peer read-through;
- sector pricing/supply-demand;
- theme rotation;
- ownership/flow;
- other information arrivals.

We tested the simplest available proxies in the existing v3 board ledger.

For H=5 T2 rows:

### T2 + news

- n=11
- SPY-excess positive: 90.9%
- mean SPY excess: +3.58%
- first per issuer: 6/7 positive excess

### T2 + historical `sue_fresh`

- n=13
- positive excess: 30.8%
- mean excess: -1.01%
- first per issuer: 2/6 positive excess
- mean first-issuer excess: -2.05%

### T2 + smart-money-add

- n=51
- positive excess: 43.1%
- mean excess: -0.35%
- first per issuer: 9/20 positive excess

### T2 + ANY of news / SUE / smart-money

- n=62
- positive excess: 40.3%
- mean excess: -0.44%

This simple OR does **not** discover a useful general rerating mechanism.

### T2 + TWO OR MORE independent evidence legs

The more interesting result:

- n=12 rows
- 5 unique issuers
- positive SPY excess: 10/12 = 83.3%
- positive absolute return: 9/12 = 75%
- mean SPY excess: +2.69%
- first observation per issuer: 5/5 positive SPY excess
- 4/5 positive absolute returns
- mean first-issuer SPY excess: +3.66%

The five first-issuer cases are:

- TSLA: news + smart-money
- ADM: SUE + smart-money
- PRIM: news + smart-money
- INTC: news + smart-money
- ISRG: SUE + smart-money

This is a very small, discovered-after-the-fact sample and **cannot be promoted**.

But it changes the research hypothesis:

> The stable object may be **fresh technical ignition × convergence of multiple independent evidence families**, not “T2 + news.”

That is consistent with NVDA itself, whose case was overdetermined across attention, catalyst, positioning and technical state.

### Crucial caveat

This should not become an additive “number of catalysts” score.

The future study must distinguish:

- independent evidence;
- duplicated evidence;
- stale ownership evidence;
- directionally correct vs semantically ambiguous earnings evidence;
- event species;
- regime;
- entry availability.

---

# 6. July is not a clean negative replication

The previous cross-era comparison should be downgraded from “failed replication” to **not-yet-comparable**.

Repository chronology shows July was still a substrate-build era:

- Jul 7: stock flow-to-price / 13F + short-flow
- Jul 10: expanded smart-money roster/backfill
- Jul 10: Ownership Intelligence Desk
- Jul 10: narrative-flare engine
- Jul 30: Intelligence Desk V2
- Aug 2: US `us_prophet_v1` priority engine
- Aug 9: Anticipation architecture
- Aug 15: canonical C1 `us_prophet_v3`

July `confluence` therefore differs on:

- data-plane maturity;
- feature coverage;
- feature semantics;
- candidate population;
- entry architecture;
- rank architecture.

It was also a materially different semiconductor / growth regime.

A July-v3 comparison is only meaningful after conditioning on both:

1. **what evidence was actually measurable at the time**, and
2. **market/sector regime**.

---

# 7. Leadership Persistence: what the Fable null did and did not kill

The Trend Persistence C1 result is a legitimate null for its registered construction.

It does **not** falsify Prophet's need for a durability head.

It tested:

- eleven GICS sectors;
- 20/60-session horizons;
- rank-linear construction;
- as-of-now, non-era-correct labels;
- survivor-tilted labelled universe;
- group RS / participation / leader retention / coherence features;
- incremental contribution after member trailing-return/volatility controls.

Its own result explicitly leaves:

- GICS industry groups;
- industries;
- baskets;
- dynamic themes

untested.

More importantly, it did not condition on a **fresh ignition / rerating event**.

Prophet's durability question is different:

> Given that a stock has just undergone a credible rerating and ignition, what is the probability that leadership survives for 21–63 sessions rather than stalls or mean-reverts?

That is better framed as:

- episode-conditioned survival;
- duration/hazard to loss of leadership;
- group/theme persistence;
- revision/catalyst persistence;
- RS depth;
- dip recovery;
- breadth/participation;
- leader-retention after the event cut.

Do not rerun Fable's failed sector model under another name.

---

# 8. Revised Prophet architecture

The golden case now supports a stronger decomposition:

## Head 1 — Emergence / Research Attention

Question:

> Is this becoming an unusually important opportunity that deserves operator attention?

Optimize for recall.

Can be high even when entry is closed.

Inputs may include:

- abnormal information arrival;
- revision acceleration;
- cross-family evidence convergence;
- theme/industry changes;
- emerging RS;
- attention;
- ownership/flow context.

## Head 2 — Rerating / Ignition

Question:

> Is new information being accepted by the tape now?

Optimize short-horizon follow-through.

Candidate interactions:

- technical confirmation × attention arrival;
- technical confirmation × catalyst/revision;
- technical confirmation × independent multi-family convergence;
- group rerating × stock RS;
- event type × technical state;
- regime × event type × confirmation.

Do not hard-code `T2 && news_burst`.

## Head 3 — Leadership Persistence / Durability

Question:

> Is this ignition likely to become a durable 21–63-session leader?

Optimize duration and leader retention.

This head must be distinct from the failed unconditional sector persistence construction.

## Head 4 — Entry Availability

Question:

> Is entry open now, for this strategy, at this price?

Keep deterministic.

It owns:

- freshness;
- chase/extension;
- buy-zone geometry;
- blackout;
- invalidation;
- quote/session validity.

It must be able to say:

> “High-importance emerging winner. Entry unavailable — wait.”

## Head 5 — Plan / Execution Publication

Question:

> Can the system publish a formally valid plan from current, provenance-clean inputs?

This final layer is separate from Entry Availability.

The NVDA case proved why: the Entry Signal surface found a viable window, but formal plan origination correctly refused mixed-vintage data.

---

# 9. The new most important engineering/research lesson from NVDA

The system's biggest missed opportunity was **not necessarily prediction quality**.

The sequence was:

1. NVDA was becoming important.
2. Entry intelligence saw an actionable state.
3. The watchlist emitted a premarket buy-zone alert.
4. The formal plan system refused to originate because the source plane was stale/mixed.
5. The clean board arrived after the market had already advanced.
6. A formal plan was published the next day.

That means improving Prophet requires work on **both**:

- better intelligence / interaction modeling;
- lower-latency, provenance-clean data availability and consistent freshness semantics across surfaces.

A world-class predictor connected to stale source planes still misses entries.

This should become an explicit acceptance requirement:

> **Lead-time gained by intelligence must not be consumed by stale-data or publication lag.**

---

# 10. Revised reproducibility assessment

## Mechanical detection path: HIGH

If equivalent PIT inputs recur, the deterministic stack will reproduce the same state transitions.

## “NVDA-like multi-family case matters”: MODERATE-HIGH

The case is overdetermined and not dependent on one family.

The broader principle — independent evidence convergence plus timing unlock — is plausible and supported enough to pursue.

## Exact T2+news rule: LOW-MODERATE

Very small discovery sample, stronger only at H=5, and historical semantics/era drift are material.

Do not expect the raw 90.9% relative-hit statistic to persist.

## T2 + 2 independent evidence families: PROMISING DISCOVERY, LOW CONFIRMATORY CONFIDENCE

The 10/12 H5 result is interesting but contains only 5 unique issuers.

It is a hypothesis seed, not a shipping rule.

## Durable leadership prediction: UNPROVEN

NVDA itself continued, but the historical interaction evidence does not yet establish 21–63-session persistence.

## Ability to materially improve winner recall: MODERATE-HIGH architectural confidence

The key is not to widen Entry Availability.

It is to add a broad research-attention/emergence state upstream, so high-value blocked names remain visible.

---

# 11. Required next study

The next Pro/Astra phase should no longer ask:

> “Does T2 + news work?”

It should ask:

> **When independent information/evidence arrives around an already-interesting name, which configurations lead to a genuine rerating, which ignite immediately, and which persist into durable leadership?**

Required unit: PIT candidate episode.

Required clocks:

- first emergence;
- first independent evidence arrival;
- technical anticipation;
- technical ignition;
- first research-attention promotion;
- first Entry Availability open;
- formal plan publication;
- first valid execution window;
- leadership-loss / persistence endpoint.

Required outcome separation:

- absolute return;
- excess vs SPY;
- sector-relative excess;
- MFE / MAE / MDD;
- top-decile winner capture;
- actual entry availability;
- plan executability.

Required evidence provenance:

- earnings / guidance;
- analyst revisions;
- peer/customer/supplier;
- sector pricing/capacity/inventory;
- theme/industry breadth;
- attention/news;
- smart money / ownership;
- options/flow confirmer;
- technical-only rerating;
- multi-source convergence.

---

# 12. Promotion and build ruling

## Build / accrue now at zero authority

- episode-level emergence and rerating receipts;
- independent evidence-family count / provenance;
- explicit event species;
- research-attention state separate from entry;
- lead-time milestones;
- current-session freshness across every surface;
- formal plan-publication lag telemetry;
- prospective interaction hypotheses.

## Do not promote now

- T2+news;
- T2+2 evidence legs;
- SUE;
- news burst;
- smart money;
- a fitted C3/C4 model.

The registered fold law still has zero usable fitted folds.

## Must repair independently

- stale/mixed-vintage upstream source plane;
- freshness consistency between alert and plan surfaces;
- management replay / historical first-cross timestamps from the previous audit.

---

---

# 13. New interaction census — T2 × independent-evidence convergence

The broader rerating OR is not the mechanism. The interaction becomes materially more interesting only when **fresh T2 technical acceptance** and **multiple independent evidence legs** coincide.

For this exploratory read, the three presently measurable evidence legs were:

- `news_burst` — attention / information arrival, direction-neutral;
- `sue_fresh` — legacy earnings-evidence proxy, with the semantic caveat documented above;
- `smartmoney_add` — A/B-grade `new` / `add` ownership evidence, stale by 13F cadence.

`insider_cluster` was excluded from the convergence count because the serving path is stale/dead and it is not a clean current signal.

## 13.1 H=5 tier × evidence-count map

Within the `us_prophet_v3` buy lane:

### T1

- zero evidence legs: n=242, 40.1% SPY-positive, mean excess -0.87%;
- one leg: n=43, 37.2%, mean -2.39%;
- two legs: n=5, 40.0%, mean -1.18%.

There is no positive convergence pattern here.

### T2

- zero legs: n=265, 37.4% SPY-positive, mean -0.60%;
- one leg: n=50, 30.0%, mean -1.19%;
- **two legs: n=11, 81.8%, mean +2.60%;**
- three legs: n=1, positive, +3.62%;
- **two-or-more: n=12, 83.3%, mean +2.69%.**

### T3

The available cells are tiny and poor; no positive convergence claim is supported.

## 13.2 Issuer-deduplicated T2 result

Using the **first T2 observation per ticker**:

- T2 + zero legs: n=89, 42.7% SPY-positive, mean +0.06%;
- T2 + one leg: n=17, 29.4%, mean -1.74%;
- **T2 + two legs: n=5, 5/5 positive vs SPY, 5/5 positive vs sector, 4/5 positive absolute, mean SPY excess +3.66%.**

The five issuers were:

- TSLA — news + smart-money;
- ADM — SUE + smart-money;
- PRIM — news + smart-money;
- INTC — news + smart-money;
- ISRG — SUE + smart-money.

This should **not** be read as a 100% expected hit rate. It is five discovered issuers.

## 13.3 Convergence without T2 does not reproduce the result

The specificity matters.

First-ticker observations with two evidence legs across **all tiers** were only:

- n=11;
- 63.6% SPY-positive;
- mean SPY excess approximately flat.

First-ticker T1 + two legs was:

- n=2;
- 0/2 SPY-positive;
- mean SPY excess -2.54%.

Thus the current evidence does **not** support “more evidence is always better.”

The plausible object is the interaction:

> **independent evidence convergence × a specific fresh T2 acceptance state**

not an additive catalyst count.

## 13.4 Same-date controls

On every one of the seven dates where a T2 + two-or-more-leg row existed, that subgroup had higher mean five-session SPY excess than same-date T2 rows with fewer than two legs.

Mean date-level excess advantage: about **+4.19 percentage points**.

Observed date-level differences:

- Aug-21: +5.12 pp;
- Sep-03: +2.66 pp;
- Sep-04: +3.62 pp;
- Sep-08: +3.73 pp;
- Sep-09: +4.55 pp;
- Sep-10: +4.85 pp;
- Sep-14: +4.77 pp.

Exploratory Fisher tests:

- repeated nightly rows: OR ~8.82, one-sided p ~0.00146;
- first-T2-per-ticker: 5/5 vs 56/138 control successes, one-sided p ~0.0128.

These are **post-selection discovery statistics**. The interaction was not preregistered before the outcomes were inspected. They establish research priority, not score or trade authority.

## 13.5 Mechanistic interpretation of T2

T2 is not a generic green technical badge.

Its construction requires:

1. a 3D StochRSI turn has already crossed recently;
2. the 2D RSI-MACD then freshly crosses;
3. the longer-timescale state remains constructive;
4. RSI is below the buy ceiling;
5. the setup is not topped / bear-crossed;
6. the cross remains inside a short freshness window.

That is naturally interpretable as a **second-timescale price acceptance event**:

> the initial turn exists first, then a slower momentum layer confirms that the move is being accepted rather than immediately rejected.

The current best zero-authority hypothesis is therefore:

> **new independent evidence converges around the name, and price subsequently confirms that rerating on a second timescale.**

That is substantially more specific than “T2 + news.”

---

# 14. Persistence should be conditioned on ignition, not treated as one day-zero scalar

A first-T2 episode study provides a useful architectural clue.

Among first-T2 episodes with both H=5 and H=10 grades:

- 134 episodes total;
- 55 were SPY-positive at H=5;
- **35/55 = 63.6% of those H5 responders remained SPY-positive at H=10**;
- among 79 H5 non-responders, only **9** became H10 SPY-positive.

So the observed path is asymmetric:

- early successful ignition often continues;
- failed early ignition rarely repairs itself by day 10.

This suggests the leadership-persistence system should likely be a **conditional update after ignition**, not one monolithic 60-day forecast made at the original signal cut.

A future product can maintain two separate probabilities:

1. **ex-ante durability prior** at detection / ignition;
2. **post-ignition survival update** as 1–5 sessions of acceptance, breadth, revisions and dip behavior arrive.

That is compatible with the Chairman's desired state:

> “This is an unusually important emerging ignition candidate. Entry is not open yet.”

and later:

> “Ignition has now been accepted; persistence probability is rising/falling.”

## 14.1 Exploratory persistence correlates among H5 responders

These are descriptive only and too small for promotion.

Among the 55 H5-positive first-T2 episodes:

- persistent-to-H10 group had higher mean C1 score (~31.1 vs ~26.5);
- residual alpha was less negative (~-0.22 vs ~-0.40);
- evidence-count mean was higher (~0.29 vs ~0.15);
- `confluence_k` was higher (~0.34 vs ~0.10);
- `TURN SIGNALED` states persisted 7/9 to H10;
- smart-money-positive H5 responders persisted 7/8, versus ~60% without it.

These are small and confounded. The smart-money read is also stale by 13F cadence.

The useful conclusion is architectural, not parametric:

> **persistence should consume the path after ignition and update with new evidence, rather than trying to squeeze durability out of the same entry score.**

---

# 15. Updated research priority

The strongest research target after the Pro re-audit is now:

## H-IGNITION-CONVERGENCE

> A fresh T2 acceptance event has materially higher short-horizon follow-through when at least two **independent, point-in-time-valid rerating evidence families** are concurrently active.

This is a **prospective research hypothesis**, not a production rule.

The legacy historical legs used to discover it are not yet suitable as the final serving definition:

- `news_burst` needs explicit information-arrival semantics and provenance;
- earnings evidence must use directionally correct positive-relative semantics;
- ownership evidence must expose knowable date / staleness;
- future analyst / peer / sector rerating species must be registered, not silently added after outcomes.

The next study should freeze the hypothesis before reading future outcomes and accrue episode-level observations through the existing Conditional Fusion evaluation owner.


---

# 16. NVDA had an earlier “important but not enterable” state

The full v3 board ledger contains an earlier NVDA sequence that is directly relevant to the proposed Emergence / Research-Attention head.

NVDA appeared on the **watch** lane on:

- 2026-09-08;
- 2026-09-09;
- 2026-09-10.

Across all three dates:

- lane: `watch`;
- state: `HOLD`;
- entry status: `await_confluence`;
- act level: 1;
- no T1/T2/T3 cascade tier on the graded row;
- `news_burst = true`;
- `smartmoney_add = true`;
- independent-evidence count = 2.

Its C1 score remained material:

- Sep-08: 58;
- Sep-09: 62;
- Sep-10: 51.

This is almost exactly the product state the Chairman requested:

> **“This is an unusually important emerging ignition candidate. Entry is not open yet.”**

## 16.1 This early state was not an immediate five-day alpha rule

The Sep-08 to Sep-10 watch observations did not all immediately outperform:

- Sep-08 H5 excess vs SPY: -3.17%;
- Sep-09: -0.18%;
- Sep-10: +0.64%.

At H10 they improved modestly:

- Sep-08: +0.22% excess;
- Sep-09: +1.36%;
- Sep-10: +2.22%.

This is important.

The Emergence head should **not** be optimized as another five-day buy predictor.

Its job is:

1. preserve an important unresolved candidate;
2. explain why it matters;
3. keep following the evidence;
4. wait for a separate ignition / Entry Availability transition.

## 16.2 Generic watch-lane convergence is not enough

Across the v3 H5 watch lane:

- two-or-more legacy evidence legs: n=44;
- only 27.3% positive excess vs SPY;
- mean excess -1.59%.

Simple refinements such as near-high, C1 score >=50 or nonnegative alpha did not rescue the cohort.

Therefore:

> **Do not turn “watch + multiple evidence legs” into a promotion rule.**

NVDA's earlier watch state is a useful example of **research persistence**, not evidence that every such state predicts near-term returns.

A future Emergence head needs a different objective from the Ignition head: recall of important future opportunities, lead time, and successful later conversion — not H5 return from the first watch stamp.

---

# 17. Sep-25 did not receive a new fundamental catalyst; it received price acceptance

A direct Sep-24 vs frozen Sep-25 comparison shows the “why this name?” evidence was already present before the action switch.

## Sep-24

- SUE z: +1.47;
- revision z: +2.16;
- news burst: 6, neutral sentiment;
- smart-money chip: unchanged `add`;
- selection-axis z: ~1.121;
- potential fuel: ~0.077;
- potential edge: ~1.224;
- entry-axis z: **-0.32**;
- cycle blocked: true;
- potential trigger: **0.075**;
- potential score: **4 / low**;
- entry status: `extended`.

## Sep-25

- SUE z: +1.47;
- revision z: +2.23;
- news burst: the same 6 neutral items;
- smart-money chip: unchanged;
- selection-axis z: ~1.116;
- potential fuel: ~0.074;
- potential edge: ~1.223;
- entry-axis z: **+0.907**;
- cycle blocked: false;
- potential trigger: **0.92**;
- potential score: **51 / constructive**;
- entry status: `partial`.

Thus almost all the decisive change occurred in **timing / acceptance**, not the rerating substrate.

The best causal description of the Sep-25 recommendation is:

> **an already-supported rerating thesis received a fresh multi-timescale price-acceptance confirmation.**

This is stronger and more precise than saying “news caused Prophet to buy NVDA.”

## 17.1 SUE freshness clock caveat is stronger than previously stated

`sue_fresh_days` must not be interpreted as the true age of an earnings release.

The producer documents that the EDGAR EPS panel lacks the real filing date and uses a synthetic:

> `period_end + 60 days`

as `asof_date`.

Therefore NVDA's `sue_fresh_days = 1` on Sep-25 does **not** prove that earnings arrived one day earlier.

This matters for the rerating ontology:

- SUE magnitude can remain contextual evidence;
- the current freshness field is not a lawful event-arrival clock for ignition timing;
- prospective rerating studies need a real filing / known-at timestamp before earnings evidence can count as a timed information-arrival event.

## 17.2 Analyst revisions are more plausible rerating context — but were already strong before T2

The analyst revision leg is built from current revision breadth and 30-day estimate change, cross-sectionally normalized.

NVDA carried:

- revision z ~+2.16 on Sep-24;
- revision z ~+2.23 on Sep-25.

That is strong rerating context, but it barely changed across the action transition.

So revisions help explain **why NVDA was important**, not what mechanically flipped the Sep-25 recommendation.

---

# 18. Product consequence: persistence has two different meanings

The study now distinguishes:

### Research persistence

Keep an unresolved, high-importance candidate alive across days/weeks even when:

- Entry Availability is closed;
- H5 return is initially weak;
- the technical acceptance event has not fired.

NVDA Sep-08→Sep-25 is the golden example.

This is a **candidate-memory / attention priority problem**, not a directional trade signal.

### Leadership persistence

After ignition has occurred, update the probability that relative leadership will survive.

This is the post-ignition survival problem described in §14.

These should not be one model.


# Final ruling

NVDA remains a valuable golden case, but its real lesson is more subtle than “Prophet picked a winner.”

It demonstrated that Mastermind already has pieces of a high-quality architecture:

> **multi-family opportunity recognition  
> → timing/ignition transition  
> → Entry Availability  
> → bounded geometry**

It also exposed the next missing links:

> **typed rerating intelligence  
> + explicit emergence/research-attention state  
> + durability modeling  
> + provenance-clean low-latency source delivery  
> + formal publication that does not consume the intelligence lead time**

The golden case should therefore be used to improve both the **intelligence engine** and the **delivery/freshness path**.

No live Prophet behavior is changed by this re-audit.
