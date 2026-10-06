# Leadership Persistence RPH-0 — Findings and Product Ruling

**Operation:** `leadership-persistence-rph0-20260910-sol-001`
**Program:** `sector-rotation-intelligence`
**Input:** `data/signal_archive/baskets.parquet`
**Input SHA-256:** `b2f45d79e3e506a2a1aec21a117046859d8677acc2da46865579ad52c7fecc21`
**Measured archive:** 2026-06-18 through 2026-09-09
**Authority:** descriptive research context only; no rank, gate, size, entry, exit, trade, Prophet, Oracle or portfolio authority

## Executive result

The archive supports a useful but multidimensional conclusion: the **whole published ordering retains
memory much longer than membership in the strict top quartile**, while the published scores of current
leaders have recently tended to compress relative to laggards. Those are three different facts and
must not be collapsed into one rotation-speed or market-regime label.

RPH-0 also found a preregistration defect before any temporal-shape verdict was promoted. The frozen
20-session recent window cannot mature two of the three long-horizon cells at the eight-pair evidence
floor. The shape result is therefore `INSUFFICIENT_HISTORY` with the stronger structural state
`STRUCTURALLY_UNESTIMABLE`, not a measured continuation/reversal/multiscale verdict.

## Evidence receipt and coverage

- 41 valid archive snapshots were recovered across 57 expected NYSE sessions: coverage `0.7193`.
- 16 expected sessions are missing inside the observed date range.
- Per-snapshot theme count ranges from 25 to 49, with median 46.
- The exact one-session transition study has 30 eligible endpoint pairs, 2 ineligible pairs and 9
  target-missing pairs.
- Missing sessions are never forward-filled. They right-censor leader-residency episodes and reduce
  eligible endpoint counts instead of being treated as continuous observations.

Coverage is sufficient for several aggregate measurements but not for a general historical claim.
The archive represents what the existing thematic system published, not reconstructed point-in-time
raw membership, stock returns or an independently validated economic regime.

## Finding 1 — whole-ranking memory is persistent

Recent mean rank Spearman correlation remains high across every measured horizon:

| Horizon | Recent rank rho | 90% moving-block interval | Eligible recent anchors |
|---:|---:|---:|---:|
| 1 session | 0.873 | [0.837, 0.906] | 14 |
| 2 sessions | 0.805 | [0.696, 0.874] | 12 |
| 3 sessions | 0.802 | [0.732, 0.862] | 12 |
| 5 sessions | 0.661 | [0.501, 0.807] | 11 |
| 7 sessions | 0.655 | [0.516, 0.785] | 10 |

The all-window rank curve passes the frozen half-life admissibility rule at **14.15 sessions**; the
prior window measures **13.63 sessions**. The recent curve remains above its half target through the
last measured horizon and therefore returns the honest null `NO_HALF_CROSSING` rather than forcing a
scalar.

This is state memory, not expected return. A theme can remain high in the ordering while its score,
breadth, internal leadership or entry availability weakens.

## Finding 2 — strict leader membership turns faster than the whole ordering

Recent top-quartile survival declines from 0.775 at one session to approximately 0.62 at five to seven
sessions:

| Horizon | Recent top-Q survival | 90% moving-block interval |
|---:|---:|---:|
| 1 session | 0.775 | [0.720, 0.819] |
| 2 sessions | 0.712 | [0.647, 0.763] |
| 3 sessions | 0.686 | [0.615, 0.750] |
| 5 sessions | 0.629 | [0.510, 0.727] |
| 7 sessions | 0.623 | [0.500, 0.746] |

The top-quartile episode ledger contains 202 observed/censored episode rows. Kaplan-Meier uses 92
episodes with observed starts, including 44 observed exits and 48 right-censored endings; 110
left-censored episodes are excluded. Its measured median top-Q residency is **3 sessions**.

The difference between a roughly 14-session whole-ranking half-life and a 3-session strict-leader
median is not a contradiction. It shows why one scalar is inadequate: themes frequently move around
the leadership boundary while the broad cross-sectional ordering remains recognizable.

## Finding 3 — one-session movement is usually adjacent, not instantaneous pole reversal

The measured one-session transition probabilities are:

| From / To | Q1 | Q2 | Q3 | Q4 |
|---|---:|---:|---:|---:|
| Q1 | 0.760 | 0.210 | 0.030 | 0.000 |
| Q2 | 0.232 | 0.527 | 0.226 | 0.015 |
| Q3 | 0.029 | 0.224 | 0.538 | 0.209 |
| Q4 | 0.000 | 0.012 | 0.220 | 0.768 |

No Q1-to-Q4 or Q4-to-Q1 transitions occur in the measured exact-session pairs. The dominant one-day
pattern is persistence or movement into an adjacent quartile. This supports a state model that keeps
level and derivative separate rather than interpreting every rank change as a new regime.

## Finding 4 — recent published-score pressure is negative despite rank persistence

Published-score continuation IC is negative at every measured recent horizon:

| Horizon | Recent score-continuation IC | 90% moving-block interval |
|---:|---:|---:|
| 1 session | -0.198 | [-0.373, -0.002] |
| 2 sessions | -0.236 | [-0.337, -0.130] |
| 3 sessions | -0.232 | [-0.354, -0.140] |
| 5 sessions | -0.295 | [-0.385, -0.181] |
| 7 sessions | -0.190 | [-0.320, -0.053] |

Within this archive, higher-ranked themes tended to lose more published score, or gain less, than
lower-ranked themes over the measured short horizons. This is **published-output compression**, not
return reversal, alpha decay or an instruction to sell leaders. It is useful precisely because it can
coexist with high rank persistence.

## Finding 5 — the temporal-shape classifier is structurally unestimable as frozen

With `recent_sessions=20` and `minimum_pair_count=8`, the theoretical maximum matured anchors are:

- horizon 10: 10;
- horizon 15: 5;
- horizon 20: 0.

Only horizon 10 can ever meet the evidence floor, while the classifier requires two measured long
cells. The minimum recent window that can satisfy the rule is 23 sessions, which permits 13 horizon-10
anchors and 8 horizon-15 anchors under perfect coverage.

The correction preserves the original RPH-0 parameters and observed result. It adds an explicit
estimability receipt; it does not post-hoc widen the window. A 23- or 30-session classifier must be a
separately preregistered follow-up and cannot be described as the confirmatory RPH-0 result.

## Latest published snapshot context — descriptive only

The 2026-09-09 archive snapshot ranks the following themes in its first ten rows:

1. crypto;
2. AI software;
3. energy complex;
4. gold miners;
5. silver miners;
6. crypto rails;
7. U.S. energy sector;
8. PGM miners;
9. memory and storage;
10. Mag 7.

The current top-quartile episode ledger is partially left-censored because the archive resumes after
an earlier gap. The listed order is therefore a current published state, not proof of the complete age
of each leadership episode and not a buy list.

## Product and intelligence ruling

A robust rotation read must expose at least five independent dimensions:

1. **leadership level** — current rank/quantile;
2. **leadership memory** — rank persistence across exact session horizons;
3. **boundary residency** — survival and transition behavior for the top group;
4. **score pressure** — whether incumbent leaders are gaining or losing published score;
5. **evidence quality** — archive coverage, eligible anchors and structural estimability.

These dimensions may disagree and disagreement is informative. Sector Central, State of Themes and
future machine context should not average them into one opaque score. A theme can be a persistent
leader under negative score pressure; a damaged theme can show a positive short derivative without
becoming a repaired leader; and a dispersed theme can require member-participation evidence even
when its aggregate rank remains high.

RPH-0 does not modify existing Sector Pulse, Rotation Events, Subsector Turn, ThemeState, Prophet or
portfolio policy. Any future product projection must extend an existing owner surface and preserve
its source clocks, nulls and authority. Prophet use remains blocked until Entry Truth admits a
strategy-specific deterministic consumer.

## Capability state and exact continuation

- Deterministic archive loader, pair surface, half-life, transition, residency and report harness:
  `BUILT_NOT_PROVEN` until exact-head review and applicable CI conclude.
- Real archive result: measured research evidence with the limits above; not production proof.
- Temporal-shape verdict: `STRUCTURALLY_UNESTIMABLE` under frozen RPH-0 geometry.
- Full stock-to-theme point-in-time economic exposure and complete-universe rotation map: not proven
  by this wave.

The next scientific operation should be preregistered before reading its results. It must either:

- define a structurally estimable recent window of at least 23 sessions while retaining the frozen
  evidence floor; or
- reconstruct deeper point-in-time theme/member history through the existing GMI/ThemeState and
  basket owners, then stratify persistence by breadth, dispersion, lifecycle and hierarchy level.

No follow-up may silently reuse RPH-0 as if its long-side classifier had been valid.
