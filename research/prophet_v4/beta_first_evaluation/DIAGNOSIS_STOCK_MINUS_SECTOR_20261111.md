# What is Prophet's stock-minus-sector deficit? — diagnosis on the 64-session live record

Research only: paper returns, no trade sizing, no recommendation to buy or sell anything. Everything below is
exploratory and at most **protocol level L0 (descriptive)**. Nothing here is a tuned rule, and nothing here is evidence
that a changed selection *would have* worked.

Report written 2026-11-11 13:25Z (real UTC). Plan pre-declared in `PLAN.md` (file mtime 13:14Z; its text says 13:16Z,
an estimate I wrote before saving) before any cut was computed; the first cut ran at ~13:17Z.

## The answer in four sentences

1. The deficit is real in this window and is not an artefact of one date, one sector, costs, or the undated conversions:
   the average clean plan trailed its own sector fund by **−3.0 % at 21 sessions and −5.4 % at 42 sessions**, and in
   1,000 "no-selection" draws (random same-sector, same-date index members) not one draw was that bad.
2. Roughly **half of it is not stock-picking skill at all**: about **−0.6 pp (21 s) / −2.1 pp (42 s)** is what *any*
   average member of the sector did against the cap-weighted sector fund in this window (the "random pick" baseline),
   and about **−1.1 / −1.3 pp** more is explained by *what kind* of stock was picked — higher beta/volatility and, more
   importantly, names that were **short-term bouncing but medium-term laggards** in their sector.
3. The remaining **−1.3 / −2.0 pp** is unexplained negative selection; its intervals exclude zero before correction but
   **do not survive the multiplicity correction (Holm p 0.09 / 0.22)**, and about a quarter to a third of the raw gap
   comes from ~30 picks that are **not S&P 1500 members at all** (quantum, space, crypto-mining, nuclear speculative names),
   which lost 10–19 % against their sector funds.
4. Two of the brief's suspected explanations look wrong on this record: the picks were **not** "leaders near highs" that
   reverted (they were *below* their sector's median on 63-session strength, and in this window strength *persisted*),
   and the deficit is **not** in plans that never reached their entry zone (it is in plans that *filled*; buying at the
   fill instead of at publication recovers only ~0.5 pp at 21 sessions and nothing at 42). How sure: sure about the size
   of the gap and the "random pick" baseline; moderately sure the picks' profile (short-term extended, medium-term weak,
   off-index speculative) is where it comes from; **cannot tell** whether any of this generalises beyond one mild,
   megacap-led decline with 14–22 publication dates.

## Reproduction (step 1) — passed

My own code (`code/load.py`, `code/common.py`, `code/repro.py`) from the pinned git objects reproduces the table to
6 decimals with identical counts and identical CIs to the two prior derivations:

| H | n | dates | stock − SPY | sector ETF − SPY | stock − sector ETF |
|---|---|---|---|---|---|
| 10 | 609 | 28 | +0.426434 [−1.04, +1.74] | +0.747945 | −0.321512 [−1.26, +0.53] |
| 21 | 414 | 22 | −3.024059 [−5.15, −0.86] | +0.012266 | −3.036325 [−4.21, −1.84] |
| 42 | 242 | 14 | −6.597762 [−9.80, −3.24] | −1.172618 | −5.425144 [−8.23, −2.47] |
| 63 | 0 | 0 | unmatured | | |

Inputs: data pin `b5a5c846f8b5…`, read via `git cat-file` from the Macro worktree object store (worktree untouched);
protocol header @ `07f1c9cd8c`, sha256 `3be32166…2ada` verified; all price series truncated at 2026-11-06; input
manifest sha256 `7b347b27…8cee`. Population: 732 clean (no-backfill) era plans published in the window.

## How the gap was taken apart

For each plan date and horizon, the comparison set is every point-in-time S&P 1500 member (membership file) in the same
sector on the same signal date with a price file, ≥253 closes, raw price ≥ $5, and a matured outcome, that was **not**
published that day (~1,400 names/date). Then:

- **Random-pick baseline (PB)** — the average same-sector member's stock − sector ETF. This is "no selection".
- **Characteristic tilt** — a cross-sectional regression per date (in the unpicked universe) of stock − sector ETF on
  publication-time characteristics; tilt = predicted value of the picks minus predicted value of their sector peers.
  Exposure set (a): 126-session beta to SPY, 63-session volatility, log median dollar volume (size proxy; the pin has no
  market cap), index tier (S&P 500/400/600). Momentum set (f): 63- and 126-session return, distance from 252-session high.
- **Residual** = gap − PB − tilt: what is left that the profile cannot explain.

| Piece (share of the gap) | 21 sessions | 42 sessions |
|---|---|---|
| **Gap (stock − own sector ETF)** | **−3.04** [−4.21, −1.84] | **−5.43** [−8.23, −2.47] |
| Random same-sector member (PB) | −0.62 [−1.18, −0.03] (20 %) | −2.14 [−2.74, −1.43] (39 %) |
| Exposure tilt (beta, vol, size, tier) | −0.75 [−1.18, −0.31] (25 %) | −0.39 [−1.03, +0.24] (7 %) |
| Momentum/extension-from-high tilt | −0.37 [−0.65, −0.11] (12 %) | −1.03 [−1.41, −0.64] (19 %) |
| Joint tilt (both sets together) | −1.08 [−1.59, −0.56] (35 %) | −1.32 [−2.12, −0.53] (24 %) |
| **Residual selection** | **−1.34** [−2.31, −0.39] (44 %) | **−1.96** [−3.67, −0.05] (36 %) |

(Percent-point units; intervals are 95 % date-cluster bootstrap, B = 10,000, seed 20261110; equal weight per plan.
Shares of the joint decomposition add to 100 %; the single-set tilts are not additive with each other.)

## Pre-declared family and Holm correction (22 tests)

| Test | Expl. | H21 estimate [95 %] | raw p | Holm | H42 estimate [95 %] | raw p | Holm |
|---|---|---|---|---|---|---|---|
| T1 exposure tilt | a | −0.75 [−1.18, −0.31] | .001 | **.011** | −0.39 [−1.03, +0.24] | .255 | .766 |
| T2 momentum tilt | f | −0.37 [−0.65, −0.11] | .008 | .097 | −1.03 [−1.41, −0.64] | <.001 | **<.001** |
| T3 residual selection | d | −1.34 [−2.31, −0.39] | .006 | .087 | −1.96 [−3.67, −0.05] | .034 | .224 |
| T4 matched-band peers (beta × mom63 terciles) | d | −1.41 [−2.45, −0.45] | .007 | .092 | −2.14 [−4.01, −0.20] | .029 | .224 |
| T5 pick − random same-sector member | d | −2.41 [−3.56, −1.27] | <.001 | **<.001** | −3.28 [−5.62, −0.72] | .008 | .097 |
| T6 slope on entry-zone depth (pp per 1 pt) | b | +0.97 [+0.61, +1.39] | <.001 | **.002** | +2.24 [+1.89, +2.84] | <.001 | **<.001** |
| T7 after − before SPY window high (Oct 6) | c | +2.56 [−2.74, +5.61] | .188 | .753 | not estimable (no matured 42-s plan after Oct 6) | — | — |
| T8 stratum heterogeneity (perm.) | e | — | .312 | .766 | — | .028 | .224 |
| T9 setup-family heterogeneity (perm.) | e | — | .847 | .847 | — | .015 | .155 |
| T10 sector heterogeneity (perm.) | e | — | <.001 | **.008** | — | .068 | .340 |
| T11 slope on 63-s return (pp per pp) | f | +0.06 [+0.01, +0.11] | .023 | .210 | +0.215 [+0.09, +0.32] | .001 | **.008** |

21 tests were estimable (T7-H42 structurally not); Holm over those 21. p-values are two-sided centred-bootstrap
(T1–T7, T11) or within-date label permutations, 2,000 (T8–T10). With 14–22 date clusters even "raw p < .01" is fragile:
nearby publication dates share most of their forward path, so the effective number of independent observations is
smaller than the cluster count.

---

## (a) Exposure, not selection — **PARTLY SUPPORTED (about 40–45 % of the gap, mostly size, little beta)**

| | 21 s | 42 s |
|---|---|---|
| Mean beta of picks / of their sector ETFs | 0.94 / 0.70 | 0.90 / 0.65 |
| SPY's mean forward move over the same windows | −0.87 % | −0.20 % |
| Gap after subtracting (beta_pick − beta_ETF) × SPY move | −2.58 [−3.68, −1.51] | −5.37 [−8.19, −2.36] |
| Random-member baseline (size/equal-weight drag) | −0.62 | −2.14 |
| Exposure tilt (beta, vol, size, tier) | −0.75 (Holm .011) | −0.39 (n.s.) |

Plain words: the picks *are* higher-beta than their sector funds, but SPY barely moved over the specific 21/42-session
windows these plans cover, so market beta explains only ~0.5 pp at 21 sessions and ~nothing at 42. What matters more is
that the yardstick is a **cap-weighted** fund: in this window the *average* member of a sector trailed its sector fund
by 0.6 pp (21 s) and 2.1 pp (42 s). Any stock picker drawing evenly from the membership would have shown that much
"deficit" with no skill at all. Higher volatility and higher beta *within* the cross-section added a further −0.75 pp at
21 s (the one exposure result that survives Holm). Exposure is real and part of the answer, but it does not make the
gap disappear: the beta-adjusted gap is still −2.6 / −5.4.

Within-sector the picks sat at the median on beta, volatility and dollar volume (in-sector percentiles 0.51 / 0.51 /
0.49); their higher average beta comes from which sectors and from the off-index names, not from tilting within sectors.

## (b) Entry timing — **NOT SUPPORTED as framed; but a related publication-time marker is SUPPORTED**

| Entry state (outcome-contaminated, descriptive) | 21 s gap (n) | 42 s gap (n) |
|---|---|---|
| filled (price reached the zone) | −3.80 [−5.06, −2.48] (330) | −6.00 [−9.12, −2.75] (209) |
| converted (no conversion date) | −1.10 [−3.38, +1.82] (59) | −2.26 [−7.48, +3.40] (27) |
| live (never reached zone) | +6.98 [−2.40, +20.3] (10) | — |
| expired (never reached zone) | −0.64 [−5.78, +6.04] (15) | +0.35 (6) |
| **Same filled plans, measured from the fill date instead of publication** | **−3.23** (313) vs −3.72 | **−5.93** (197) vs −5.96 |

The deficit is **not** concentrated in plans that never entered — those are few and, if anything, did better. It sits
in the plans that *did* fill (which is partly mechanical: a stock falls into a pullback zone by falling). Buying at the
fill rather than at publication would have recovered only ~0.5 pp at 21 sessions and nothing at 42, so "the study buys
too early" is not the explanation.

However, the **depth of the recommended entry zone** at publication (how far below the publication price the plan put
its entry band; median −1.8 %, quartiles −3.3 / −1.0) strongly predicts the outcome when bought at publication: each 1
point deeper zone ≈ −1.0 pp at 21 s and −2.2 pp at 42 s (both survive Holm). Zone depth correlates −0.69 with how far
the stock sat above its own 20-session average at publication (added after seeing results, below). So the product's
own "wait" signal is telling you the stock is short-term extended — and extended picks did badly *whether or not* you
waited for the zone. Caveat: plan fields come from the latest snapshot, not as-issued; the `entry_zone` block carries
its own price-basis date and appears frozen at issue, but I cannot prove it.

## (c) A few dates — **NOT SUPPORTED that it is a handful of dates; CANNOT TELL whether it is one regime**

| | 21 s | 42 s |
|---|---|---|
| Dates with a negative mean | 20 of 22 | 12 of 14 |
| Leave-one-date-out range of the gap | −3.36 … −2.81 | −6.02 … −4.71 |
| Share carried by the worst 3 dates | 33 % (Aug 14, Oct 5, Aug 13) | 62 % (Aug 14, Aug 13, Aug 18) |
| After vs before SPY's window high (Oct 6), T7 | +2.56 [−2.74, +5.61], only 3 dates after | not estimable |

No single date carries it, and it is negative almost everywhere. But the 42-session result is concentrated in the
mid-August cohort and *all* matured 42-session plans were published Aug 11 – Sep 8 — one stretch of one mild,
megacap-led decline. Whether the October top changed anything cannot be told: only three 21-session publication dates
fall after it, and none at 42.

## (d) Real negative selection — **CANNOT TELL ON THIS RECORD (leans negative; does not survive Holm)**

| | 21 s | 42 s |
|---|---|---|
| Pick − random same-sector member (T5) | −2.41 [−3.56, −1.27], Holm <.001 | −3.28 [−5.62, −0.72], Holm .097 |
| Pick − same-sector peers in the same beta × 63-s-return tercile cell (T4) | −1.41 [−2.45, −0.45], Holm .092 | −2.14 [−4.01, −0.20], Holm .224 |
| Residual after the full characteristic model (T3) | −1.34 [−2.31, −0.39], Holm .087 | −1.96 [−3.67, −0.05], Holm .224 |
| Residual, S&P 1500 member picks only (added after) | −1.07 [−2.03, −0.21] | −1.09 [−2.36, +0.20] |
| Placebo: 1,000 random same-sector same-date draws | mean −0.63, 95 % range [−1.65, +0.36]; real −3.04 below all | mean −2.16, [−3.80, −0.49]; real −5.43 below all |

Plain words: picks clearly did worse than a random member of their sector on the same date (that survives correction
at 21 s). Once you compare them only with peers of similar beta and recent return, the shortfall halves to about
−1.1 to −2.1 pp; that remainder is negative on every version, but with 14–22 date clusters and 21 tests it does not
clear Holm. And about half of the remainder at 42 s disappears if the off-index names are dropped. So "Prophet picks
the wrong members even after exposure matching" is plausible, not established. The placebo range shows what no
selection looks like here: about −0.6 pp at 21 s and −2.2 pp at 42 s *for free*. (The placebo holds dates and sectors
fixed, so it shows sampling noise in member choice only, not uncertainty about the window.)

## (e) Composition — **NOT SUPPORTED for stratum or family; sector differences SUPPORTED at 21 s but no sector carries it; off-index names (added after) carry a quarter to a third**

| Group | 21 s gap (n) | 42 s gap (n) |
|---|---|---|
| patience | −2.79 [−4.28, −1.24] (283) | −6.08 [−9.52, −2.21] (145) |
| confirmation | −3.12 [−4.89, −1.31] (113) | −3.19 [−5.22, −0.98] (87) |
| early_turn_starter | −6.47 [−15.9, +1.0] (18) | −15.37 [−27.8, −4.4] (10) |
| washout / reset_band | −3.00 (265) | −7.96 [−11.7, −3.7] (136) |
| washout / accumulate | −1.78 (44) | −2.79 (30) |
| pullback / accumulate | −3.98 (67) | −2.83 (55) |
| pullback / reset_band | −2.99 (37) | +1.06 (20) |
| Worst sectors | XLK −7.9 (59), XLI −6.1 (62), XLE −5.4 (20), XLB −4.5 (28) | XLE −16.2 (17), XLB −13.2 (17), XLI −8.0 (32) |
| Leave-one-sector-out range of the gap | −3.51 … −2.23 | −5.85 … −4.61 |
| Not an S&P 1500 member at signal date (added after) | −10.46 [−16.7, −4.5] (31) | −19.39 [−24.4, −5.7] (24) |
| S&P 500 / 400 / 600 members | −1.17 / −3.80 / −2.61 | −3.23 / −3.11 / −4.97 |

All three admission strata are negative; early-turn-starter is the worst but has 10–18 plans and contributes ≈ −0.6 pp
at 42 s. Stratum and family heterogeneity do not survive Holm. Sectors do differ at 21 s (Holm .008: technology,
industrials, energy, materials worst), but dropping any one sector leaves the gap between −2.2 and −3.5, so no sector
carries it. The single most concentrated piece found — **added after seeing results, so less weight** — is the 46
clean plans on stocks that are **not** in the point-in-time S&P 1500 (ALM, ASTS, BKSY, CRCL, GLXY, IONQ, IREN, LUNR,
NNE, OKLO, PL, QBTS, QUBT, RKLB, USAR, WULF, …; also foreign ADRs like ASML, AZN, NVO): 7–10 % of matured plans,
contributing −0.78 pp (26 %) of the 21-session gap and −1.92 pp (35 %) of the 42-session gap. Excluding them the gap is
−2.44 [−3.62, −1.30] and −3.89 [−5.86, −2.01]. Their "sector fund" comparison is weak (these names are not in the
fund), which is itself a reason they should not be graded as sector-relative picks.

## (f) Mean reversion of selected strength — **NOT SUPPORTED; the opposite is what the record shows**

| | 21 s | 42 s |
|---|---|---|
| Picks' median in-sector percentile, 63-s return / distance from 252-s high | 0.39 / 0.43 | same |
| Universe: per-date slope of stock − sector on 63-s return (share of dates negative) | +0.010 (50 %) | +0.084 (0 % — positive on all 14 dates) |
| Universe: slope on distance from 252-s high (share negative) | +0.028 (27 %) | +0.121 (0 %) |
| Among picks: pp of gap per pp of 63-s return (T11) | +0.06 (Holm .21) | +0.215 (Holm .008) |
| Momentum tilt (T2) | −0.37 (Holm .097) | −1.03 (Holm <.001) |

The premise is wrong for this record. Prophet did **not** pick leaders near their highs: the picks were below the
median of their own sector on 63-session strength and further than average from their 52-week high (this fits the
plan families — 72 % of clean plans are "washout" setups). And in this window medium-term strength *persisted* rather
than reverted: at 42 sessions, on every one of the 14 dates, sector members with stronger trailing returns beat
weaker ones. Picks lost partly *because* they were relative laggards (−1.0 pp at 42 s, survives Holm), and among the
picks the stronger ones did better.

## Added after seeing results (less weight)

1. **Short-term extension.** Picks sat at the **75th percentile** of their sector on distance above their own
   20-session average (and the 77th on 10-session return), i.e. they were *bouncing* at publication. In the whole
   universe, short-term extension reversed at 21 sessions (negative slope on 86 % of dates), but not at 42. Among picks,
   each 1 pp further above the 20-session average ≈ −0.45 pp at 21 s and −0.80 pp at 42 s. Picks in the top half of
   in-sector extension trailed bottom-half picks by −3.5 pp [−5.3, −1.4] (21 s) and −5.5 pp [−9.1, −0.6] (42 s);
   ~70–76 % of picks were in the top half. With zone depth and extension in one regression, zone depth keeps most of its
   slope at 42 s, so the plan's own zone field carries information beyond simple extension.
2. **Off-index names** (above, under (e)).
3. Model caveat: in T1–T3 the off-index picks were scored with S&P 500 tier dummies (they have no tier). Re-running the
   decomposition on member picks only: 21 s gap −2.44 = PB −0.61 + exposure −0.41 + momentum −0.29 + residual −1.07;
   42 s gap −3.89 = PB −2.04 + exposure +0.04 + momentum −0.75 + residual −1.09.

Overall reading: the picks were **medium-term laggards caught on a short-term bounce**, with a slice of **off-index
speculative names**, graded against **cap-weighted** sector funds in a window where the cap-weighted leaders kept leading.

## Robustness of the headline gap

| Check | 21 s | 42 s |
|---|---|---|
| Headline (equal per plan) | −3.04 [−4.21, −1.84] | −5.43 [−8.23, −2.47] |
| Equal per publication date | −3.39 [−4.53, −2.21] | −4.85 [−7.46, −2.27] |
| Net of round-trip costs (10 bp/side stock, 3 bp/side ETF) | −3.17 [−4.34, −1.97] | −5.55 [−8.35, −2.61] |
| Excluding converted plans (no conversion date; 59 / 27) | −3.36 [−4.72, −1.97] | −5.82 [−8.98, −2.55] |
| Leave-one-date-out range | −3.36 … −2.81 | −6.02 … −4.71 |
| Leave-one-sector-out range | −3.51 … −2.23 | −5.85 … −4.61 |
| No-selection placebo (1,000 draws), 95 % range | −1.65 … +0.36 (mean −0.63) | −3.80 … −0.49 (mean −2.16) |

The gap is robust to every check required. Its size relative to the placebo is the clearest single fact in this report.

## Limits (restated, binding)

- 64 sessions, one mild megacap-led decline (SPY −4.6 %); 22 (21 s) and 14 (42 s) publication-date clusters, adjacent
  dates sharing most of their forward path; no matured clean 63-session plan. Everything is L0 descriptive.
- 68 clean positions (76 clean published plans) are "converted" with no conversion date; shown excluded above.
- Two held positions (LFUS, SBH) have no later closes. The event study uses the grader's own-calendar ruler (as in
  the reproduced table), so these names are measured on their available bars, which spans the gap in their files;
  at most two plans, immaterial to any mean here, but not a clean measurement.
- Sector labels are current, not as-issued; the membership file has no recorded change after June 2; 35 members lack
  price files; plan snapshots are latest, not as-issued (zone depth, stratum, family read from them).
- No market-capitalisation field in the pin: size is proxied by median dollar volume and index tier.
- The comparison universe is S&P 1500 members only; off-index picks have no proper peer set.
- Point-in-time correctness of characteristics is by construction (closes through the bar before publication), but the
  price files are the latest Yahoo snapshot with its adjustments, not as-of-issue files.
- The decomposition is linear, pooled across sectors per date; tilt + residual is an accounting split, not causal.

## What to test next (at most three; pre-registrable; ordered by how much of the gap they could plausibly close)

Detectability uses the date-cluster standard error measured here, 80 % power, two-sided α = 0.05; "dates" are
publication dates with a matured outcome (this record produced ~28 in 64 sessions, i.e. roughly one every two nights),
and every horizon adds its own maturity lag. Effects are shown at the observed size and at half (the honest planning
number — observed effects on a selected post-hoc cut are usually inflated). Shares of the gap overlap; do not add them.

**H-1. Short-term extension at publication.**
Variable: close at the signal bar / mean of the last 20 closes − 1, ranked within same-sector, same-date S&P 1500
members (or equivalently the plan's own entry-zone depth). Comparison: picks in the top half vs bottom half of that rank.
Yardstick: own sector SPDR, gross, publication close to +21 sessions (secondary +42). Refuted if top-half − bottom-half
≥ 0 (point estimate) with ≥ 40 new publication dates. Observed −3.5 pp (SE ≈ 1.0); detectable with ~15 new dates at the
observed size, ~57 at half (≈ 30 / 115 nights plus 21 sessions). Plausible share of the gap: up to roughly half, much
less if it is a one-window reversal effect (the universe shows reversal at 21 s but not at 42 s).

**H-2. Medium-term relative strength within sector.**
Variable: 63-session total return minus own sector ETF's, ranked within same-sector, same-date members. Comparison:
picks below vs above the sector median. Yardstick: own sector SPDR, +42 sessions (secondary +21). Refuted if
below-median − above-median ≥ 0 with ≥ 40 new dates. Observed −5.0 pp at 42 s (SE ≈ 2.4), −1.4 pp at 21 s (n.s.);
needs ~26 new dates at the observed size, ~104 at half (≈ 50 / 210 nights plus 42 sessions). This directly tests
whether Prophet's washout/laggard preference costs it the sector-relative return. Plausible share: about a fifth of
the 42-session gap via the tilt, more if the within-pick gradient holds.

**H-3. Off-index (non-S&P 1500) names.**
Variable: point-in-time S&P 1500 membership on the signal date (yes/no). Comparison: non-member picks vs member picks.
Yardstick: own sector SPDR, +21 sessions (secondary +42; also report stock − SPY, since these names have no real sector
yardstick). Refuted if non-member − member ≥ 0 with ≥ 30 new non-member picks. Observed −8.0 pp at 21 s (SE ≈ 3.4) and
−15.5 pp at 42 s; ~31 new dates at observed size, ~121 at half — limited by how few such picks there are (~7–10 %).
Plausible share: replacing them with average member picks would close ~0.6 pp (20 %) at 21 s and ~1.5 pp (28 %) at 42 s.

None of these is a recommendation to change selection; each is a falsifiable statement for a sealed forward record.
The size/equal-weight drag (−0.6 / −2.1 pp) is a **yardstick** fact, not a selection hypothesis: the evaluation
should report a same-sector equal-weight member benchmark beside the cap-weighted ETF so that this part of the gap is
not attributed to member choice.

## What I could not determine

- Whether any of this is more than one window's behaviour: one regime, no matured 63-session clean plan, too few
  post-October-top dates to tell whether the top changed anything (T7).
- Whether the residual −1 to −2 pp after matching is genuine negative selection (does not survive Holm).
- Whether waiting for the zone helps on plans that never filled (no counterfactual entry exists for them).
- As-issued sector labels, as-issued plan fields, membership changes after June 2, and market capitalisation.

## Files

The working files named in this report (`PLAN.md`, `code/`, `out/`, including the per-plan table) are scratch files on the analysis host and are not committed.
