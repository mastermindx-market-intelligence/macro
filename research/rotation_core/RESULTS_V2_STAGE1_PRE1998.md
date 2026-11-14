# Rotation Core v2 — stage 1 result (pre-1998, 1928-01-02 → 1997-12-31)

**Verdict: the gate is closed. H1, H2 and H3 are recorded FAILED.** No hypothesis had a positive excess over its exposure-matched mix in both eras (1928–1945 and 1946–1997), under both leg readings, at both base and strict costs. The 2020–2025 window was not opened and stays sealed. Under R17.1 the gate is closed for good for this protocol.

- **Source:** `results_v2_stage1_pre1998_published.json`, published at once because the gate closed (R16 S6).
- **Run:** engine `b3f7ce4548`, release `8cd6410201`, ledger START `15893a170e`, GATE `2200b942d4`, magnitudes sha256 `0c6c207e…ff29`. Selected setting h = 3, b = 25.
- **Window:** previously examined by Pro run B; not clean.
- **What the figures are:** annualised mean daily excess over the hypothesis's own exposure-matched mix. Base costs are 10 bp; strict costs are 20 bp on switches and re-formation, with the mix paying nothing (R18). The 95 % intervals are stationary bootstrap, block 21, B = 10,000, and exist for the full window only; the era figures are point estimates.

## H1 — two-key switch between defence, offence and the equal-weight base

H1 tested whether arming on a breadth drop near the relative line's high, then switching on a break below its 50-day average, beats holding the same average mix.

| Reading / costs | Full window [95 %] | 1928–1945 | 1946–1997 |
|---|---|---|---|
| equal weight, base | −2.60 % [−3.66, −1.57] | −3.55 % | −2.22 % |
| equal weight, strict | −4.05 % [−5.15, −2.99] | −4.81 % | −3.75 % |
| drift, base | −2.46 % [−3.52, −1.43] | −2.91 % | −2.23 % |
| drift, strict | −3.91 % [−5.00, −2.85] | −4.16 % | −3.75 % |

## H3 — 126-day momentum between the offence and defence legs

H3 tested whether holding whichever of the two legs has the higher 126-session return, checked at each month-end, beats holding the same average mix.

| Reading / costs | Full window [95 %] | 1928–1945 | 1946–1997 |
|---|---|---|---|
| equal weight, base | +1.10 % [−0.30, +2.48] | +0.53 % | +1.28 % |
| equal weight, strict | +0.40 % [−1.03, +1.80] | −0.14 % | +0.57 % |
| drift, base | +0.93 % [−0.49, +2.32] | −0.27 % | +1.30 % |
| drift, strict | +0.23 % [−1.22, +1.64] | −0.95 % | +0.59 % |

H3 is positive in all four 1946–1997 cells and negative in three of the four 1928–1945 cells, so it fails the gate. Every full-window interval includes zero.

## H2 — the breadth key in the arming condition (H1 minus its price-only control, paired daily)

| Reading / costs | Full window [95 %] | 1928–1945 | 1946–1997 |
|---|---|---|---|
| equal weight, base | +0.71 % [+0.25, +1.20] | +0.75 % | +0.69 % |
| equal weight, strict | +0.96 % [+0.47, +1.48] | +1.13 % | +0.90 % |
| drift, base | +0.72 % [+0.26, +1.21] | +0.83 % | +0.69 % |
| drift, strict | +0.98 % [+0.49, +1.50] | +1.21 % | +0.90 % |

H2's paired difference is positive in all eight era cells. It is recorded FAILED because the gate closed (amendment f), and this is not a claim. It says only that H1 lost less than the price-only version of the same rule. The price-only control's own excess over its mix is −3.34 % (equal weight, base).

## Integrity counts

| Count | Value |
|---|---|
| Sessions | 1928–1945: 5,363; 1946–1997: 13,294 |
| Offence leg members | min 13, max 16 |
| Deferred executions | 0 |
| Days holding after a last close | 0 |
| Non-finite gate statistics | 0 |
| Dropped industry-days (eligible industries only; no imputation) | 138 |
| Named episodes found | 9 |
| H1 sessions | NEUTRAL 8,368 · DEFEND 4,625 · ATTACK 5,664 |
| Price-only sessions | NEUTRAL 6,993 · DEFEND 6,206 · ATTACK 5,458 |
| H3 sessions | DEFEND 9,817 · ATTACK 8,840 |

Phase A was clean: strict-run inequality violations 0, and executions identical across cost runs. Three counts include warm-up sessions (R31.5): deferred executions, days holding after a last close, and dropped industry-days.
