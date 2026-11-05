# Leadership Rotation — Study T13R (power under prereg V2 §4: G1 retained + G2 positive control)

**Headline (P0):** **H2 `NOT_EXECUTABLE`, H3 `NOT_EXECUTABLE` (V2 §4.3); H1 `NOT_EXECUTABLE` for information.** No hypothesis reaches the 0.50 pass rate in any eligible G2 slot. The eligible slots are δ ≤ 4.0 % with N ≤ 40: cells 100, 101, 103, 104, 106 and 107. All six were measured at M = 100 for both groups. The best eligible slot for H2 is cell 107 (δ 4.0 %, N 40) `defensive_sector/H2` at 1/100 (0.010, Wilson 95 % [0.002, 0.054]). H3 is 0/100 in every eligible slot for both groups. H1 passes 0 of 4,200 (sim, group) evaluations at δ > 0. Across all 147 δ > 0 rows (21 cells × 7 rows; G1 δ ∈ {0.25, 0.50, 1.00} pts, G2 δ ∈ {1, 2, 4, 8} %, N ∈ {20, 40, 80}), the largest pass rate is 2/100, which cannot be told apart from the δ = 0 size level in T12R. The planted drift does reach the H2 statistic: its mean point rises from about −0.1 pts at δ ≤ 1 to +0.20 pts at δ = 4 %, N 80 (note 2). That is still well under the +0.50 margin, and H3 does not move in the registered direction at all. Under V2 §4.3 this is a RESULT at the registered margins and never a reason to lower them. Partition executed: **P0 (synthetic) only**. Development harness — no verdict authority over markets.

This record is the prereg V2 §4 / §8 item 12 power record for the repaired protocol (V2 §2 Option A H1 null, V2 §3 size rule). It does **not** edit or supersede the T13 record (`research/LEADERSHIP_ROTATION_STUDY_T13_2026-10-14.md`), which stays the record of the V1-era G1 result (H2 0/726 at δ = 0, 0/12 at δ = 1.00 — sized but power unidentifiable). Its size companion is T12R (`research/LEADERSHIP_ROTATION_STUDY_T12R_2026-10-14.md`).

## Protocol under test

- Prereg V1 blob `9d1313e0fc0c5c9720dc1aeb16c9ebf273d70abe`, V2 blob `1fcd151cfc4cdeb321789feb50d3fbb127cce056`, V2.1 blob `8f48509b65c70f7f3786402cba9b21940a907e83` (V1/V2 unedited). Arms A0–B7/C3, margins, α = 0.025, Holm m = 6 unchanged; margins are not tuned to either generator (V2 §4.3).
- **G1 power rows (V2 §4.1):** G1 exactly as V1 §8 at δ ∈ {0.25, 0.50, 1.00} pts per 20 sessions, on the slice that matches G2 — σ 0.70 pts, ρ 0.5, N ∈ {20, 40, 80} (cells 6, 7, 8, 12, 13, 14, 18, 19, 20). The rest of the 72-cell G1 catalog (σ 1.00 / 1.40 pts, ρ 0.8) was not re-run for power in this wave (disclosed scope; their δ = 0 size rows are in T12R where V2 §3 requires them).
- **G2 positive control (V2 §4.2):** G1 with the planted drift extended to δ ∈ {1.0, 2.0, 4.0, 8.0} % per 20 sessions, onsets Poisson 2/year, regime length 40–120 sessions, σ 0.70 %, ρ 0.5, N ∈ {20, 40, 80} — cells 100–111. G2 makes no realism claim. Cell 100 has G1 cell 18's parameters with independent seeds (cell id enters the seed).
- **Powered-in-principle rule (V2 §4.3):** H2 (resp. H3) is `POWERED_IN_PRINCIPLE` iff its pass rate reaches ≥ 0.50 at some δ ≤ 4.0 % in some G2 cell with N ≤ 40 (M ≥ 100); otherwise `NOT_EXECUTABLE` at the registered margins for P2/P3 — a RESULT, never a reason to lower a margin. H1 is printed with the same arithmetic **for information** (the §4.3 rule is written for H2/H3).
- M ≥ 100 paths per (δ, cell); seeds `SeedSequence([20261014, cell_id, k])`, k ∈ [0, 100).

## §8 item 12 — power curves (pass rate × δ × cell, Wilson 95 %)

| cell | σ (pts) | δ (pts) | ρ | N | sims ok/unreached | defensive_sector/H1 | defensive_sector/H2 | defensive_sector/H3 | broadening_proxy/H1 | broadening_proxy/H2 | broadening_proxy/H3 | family_any |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 6 | 0.70 | 0.25 | 0.500 | 20 | 100/0 | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 1/100 (0.010) | 0/100 (0.000) | 1/100 (0.010) |
| 7 | 0.70 | 0.25 | 0.500 | 40 | 100/0 | 0/100 (0.000) | 0/100 (0.000) | 1/100 (0.010) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 1/100 (0.010) |
| 8 | 0.70 | 0.25 | 0.500 | 80 | 100/0 | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) |
| 12 | 0.70 | 0.50 | 0.500 | 20 | 100/0 | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) |
| 13 | 0.70 | 0.50 | 0.500 | 40 | 100/0 | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 1/100 (0.010) | 1/100 (0.010) |
| 14 | 0.70 | 0.50 | 0.500 | 80 | 100/0 | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) |
| 18 | 0.70 | 1.00 | 0.500 | 20 | 100/0 | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) |
| 19 | 0.70 | 1.00 | 0.500 | 40 | 100/0 | 0/100 (0.000) | 0/100 (0.000) | 1/100 (0.010) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 1/100 (0.010) |
| 20 | 0.70 | 1.00 | 0.500 | 80 | 100/0 | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 1/100 (0.010) | 1/100 (0.010) |
| 100 | 0.70 | 1.00 | 0.500 | 20 | 100/0 | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) |
| 101 | 0.70 | 1.00 | 0.500 | 40 | 100/0 | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) |
| 102 | 0.70 | 1.00 | 0.500 | 80 | 100/0 | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 1/100 (0.010) | 1/100 (0.010) |
| 103 | 0.70 | 2.00 | 0.500 | 20 | 100/0 | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) |
| 104 | 0.70 | 2.00 | 0.500 | 40 | 100/0 | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) |
| 105 | 0.70 | 2.00 | 0.500 | 80 | 100/0 | 0/100 (0.000) | 0/100 (0.000) | 2/100 (0.020) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 2/100 (0.020) |
| 106 | 0.70 | 4.00 | 0.500 | 20 | 100/0 | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) |
| 107 | 0.70 | 4.00 | 0.500 | 40 | 100/0 | 0/100 (0.000) | 1/100 (0.010) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 1/100 (0.010) |
| 108 | 0.70 | 4.00 | 0.500 | 80 | 100/0 | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) |
| 109 | 0.70 | 8.00 | 0.500 | 20 | 100/0 | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) |
| 110 | 0.70 | 8.00 | 0.500 | 40 | 100/0 | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) |
| 111 | 0.70 | 8.00 | 0.500 | 80 | 100/0 | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) | 0/100 (0.000) |

## §8 item 12 — G2 curve and V2 §4.3 disposition per hypothesis

| generator | cell | δ (pts) | N | row | passes/M | point | Wilson 95 % |
|---|---|---|---|---|---|---|---|
| G1 | 6 | 0.25 | 20 | broadening_proxy/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 6 | 0.25 | 20 | broadening_proxy/H2 | 1/100 | 0.010 | [0.002, 0.054] |
| G1 | 6 | 0.25 | 20 | broadening_proxy/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 6 | 0.25 | 20 | defensive_sector/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 6 | 0.25 | 20 | defensive_sector/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 6 | 0.25 | 20 | defensive_sector/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 6 | 0.25 | 20 | family_any | 1/100 | 0.010 | [0.002, 0.054] |
| G1 | 12 | 0.50 | 20 | broadening_proxy/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 12 | 0.50 | 20 | broadening_proxy/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 12 | 0.50 | 20 | broadening_proxy/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 12 | 0.50 | 20 | defensive_sector/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 12 | 0.50 | 20 | defensive_sector/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 12 | 0.50 | 20 | defensive_sector/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 12 | 0.50 | 20 | family_any | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 18 | 1.00 | 20 | broadening_proxy/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 18 | 1.00 | 20 | broadening_proxy/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 18 | 1.00 | 20 | broadening_proxy/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 18 | 1.00 | 20 | defensive_sector/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 18 | 1.00 | 20 | defensive_sector/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 18 | 1.00 | 20 | defensive_sector/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 18 | 1.00 | 20 | family_any | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 7 | 0.25 | 40 | broadening_proxy/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 7 | 0.25 | 40 | broadening_proxy/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 7 | 0.25 | 40 | broadening_proxy/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 7 | 0.25 | 40 | defensive_sector/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 7 | 0.25 | 40 | defensive_sector/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 7 | 0.25 | 40 | defensive_sector/H3 | 1/100 | 0.010 | [0.002, 0.054] |
| G1 | 7 | 0.25 | 40 | family_any | 1/100 | 0.010 | [0.002, 0.054] |
| G1 | 13 | 0.50 | 40 | broadening_proxy/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 13 | 0.50 | 40 | broadening_proxy/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 13 | 0.50 | 40 | broadening_proxy/H3 | 1/100 | 0.010 | [0.002, 0.054] |
| G1 | 13 | 0.50 | 40 | defensive_sector/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 13 | 0.50 | 40 | defensive_sector/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 13 | 0.50 | 40 | defensive_sector/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 13 | 0.50 | 40 | family_any | 1/100 | 0.010 | [0.002, 0.054] |
| G1 | 19 | 1.00 | 40 | broadening_proxy/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 19 | 1.00 | 40 | broadening_proxy/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 19 | 1.00 | 40 | broadening_proxy/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 19 | 1.00 | 40 | defensive_sector/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 19 | 1.00 | 40 | defensive_sector/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 19 | 1.00 | 40 | defensive_sector/H3 | 1/100 | 0.010 | [0.002, 0.054] |
| G1 | 19 | 1.00 | 40 | family_any | 1/100 | 0.010 | [0.002, 0.054] |
| G1 | 8 | 0.25 | 80 | broadening_proxy/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 8 | 0.25 | 80 | broadening_proxy/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 8 | 0.25 | 80 | broadening_proxy/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 8 | 0.25 | 80 | defensive_sector/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 8 | 0.25 | 80 | defensive_sector/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 8 | 0.25 | 80 | defensive_sector/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 8 | 0.25 | 80 | family_any | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 14 | 0.50 | 80 | broadening_proxy/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 14 | 0.50 | 80 | broadening_proxy/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 14 | 0.50 | 80 | broadening_proxy/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 14 | 0.50 | 80 | defensive_sector/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 14 | 0.50 | 80 | defensive_sector/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 14 | 0.50 | 80 | defensive_sector/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 14 | 0.50 | 80 | family_any | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 20 | 1.00 | 80 | broadening_proxy/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 20 | 1.00 | 80 | broadening_proxy/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 20 | 1.00 | 80 | broadening_proxy/H3 | 1/100 | 0.010 | [0.002, 0.054] |
| G1 | 20 | 1.00 | 80 | defensive_sector/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 20 | 1.00 | 80 | defensive_sector/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 20 | 1.00 | 80 | defensive_sector/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G1 | 20 | 1.00 | 80 | family_any | 1/100 | 0.010 | [0.002, 0.054] |
| G2 | 100 | 1.00 | 20 | broadening_proxy/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 100 | 1.00 | 20 | broadening_proxy/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 100 | 1.00 | 20 | broadening_proxy/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 100 | 1.00 | 20 | defensive_sector/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 100 | 1.00 | 20 | defensive_sector/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 100 | 1.00 | 20 | defensive_sector/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 100 | 1.00 | 20 | family_any | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 103 | 2.00 | 20 | broadening_proxy/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 103 | 2.00 | 20 | broadening_proxy/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 103 | 2.00 | 20 | broadening_proxy/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 103 | 2.00 | 20 | defensive_sector/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 103 | 2.00 | 20 | defensive_sector/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 103 | 2.00 | 20 | defensive_sector/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 103 | 2.00 | 20 | family_any | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 106 | 4.00 | 20 | broadening_proxy/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 106 | 4.00 | 20 | broadening_proxy/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 106 | 4.00 | 20 | broadening_proxy/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 106 | 4.00 | 20 | defensive_sector/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 106 | 4.00 | 20 | defensive_sector/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 106 | 4.00 | 20 | defensive_sector/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 106 | 4.00 | 20 | family_any | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 109 | 8.00 | 20 | broadening_proxy/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 109 | 8.00 | 20 | broadening_proxy/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 109 | 8.00 | 20 | broadening_proxy/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 109 | 8.00 | 20 | defensive_sector/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 109 | 8.00 | 20 | defensive_sector/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 109 | 8.00 | 20 | defensive_sector/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 109 | 8.00 | 20 | family_any | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 101 | 1.00 | 40 | broadening_proxy/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 101 | 1.00 | 40 | broadening_proxy/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 101 | 1.00 | 40 | broadening_proxy/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 101 | 1.00 | 40 | defensive_sector/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 101 | 1.00 | 40 | defensive_sector/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 101 | 1.00 | 40 | defensive_sector/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 101 | 1.00 | 40 | family_any | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 104 | 2.00 | 40 | broadening_proxy/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 104 | 2.00 | 40 | broadening_proxy/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 104 | 2.00 | 40 | broadening_proxy/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 104 | 2.00 | 40 | defensive_sector/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 104 | 2.00 | 40 | defensive_sector/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 104 | 2.00 | 40 | defensive_sector/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 104 | 2.00 | 40 | family_any | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 107 | 4.00 | 40 | broadening_proxy/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 107 | 4.00 | 40 | broadening_proxy/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 107 | 4.00 | 40 | broadening_proxy/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 107 | 4.00 | 40 | defensive_sector/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 107 | 4.00 | 40 | defensive_sector/H2 | 1/100 | 0.010 | [0.002, 0.054] |
| G2 | 107 | 4.00 | 40 | defensive_sector/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 107 | 4.00 | 40 | family_any | 1/100 | 0.010 | [0.002, 0.054] |
| G2 | 110 | 8.00 | 40 | broadening_proxy/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 110 | 8.00 | 40 | broadening_proxy/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 110 | 8.00 | 40 | broadening_proxy/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 110 | 8.00 | 40 | defensive_sector/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 110 | 8.00 | 40 | defensive_sector/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 110 | 8.00 | 40 | defensive_sector/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 110 | 8.00 | 40 | family_any | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 102 | 1.00 | 80 | broadening_proxy/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 102 | 1.00 | 80 | broadening_proxy/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 102 | 1.00 | 80 | broadening_proxy/H3 | 1/100 | 0.010 | [0.002, 0.054] |
| G2 | 102 | 1.00 | 80 | defensive_sector/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 102 | 1.00 | 80 | defensive_sector/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 102 | 1.00 | 80 | defensive_sector/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 102 | 1.00 | 80 | family_any | 1/100 | 0.010 | [0.002, 0.054] |
| G2 | 105 | 2.00 | 80 | broadening_proxy/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 105 | 2.00 | 80 | broadening_proxy/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 105 | 2.00 | 80 | broadening_proxy/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 105 | 2.00 | 80 | defensive_sector/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 105 | 2.00 | 80 | defensive_sector/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 105 | 2.00 | 80 | defensive_sector/H3 | 2/100 | 0.020 | [0.006, 0.070] |
| G2 | 105 | 2.00 | 80 | family_any | 2/100 | 0.020 | [0.006, 0.070] |
| G2 | 108 | 4.00 | 80 | broadening_proxy/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 108 | 4.00 | 80 | broadening_proxy/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 108 | 4.00 | 80 | broadening_proxy/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 108 | 4.00 | 80 | defensive_sector/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 108 | 4.00 | 80 | defensive_sector/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 108 | 4.00 | 80 | defensive_sector/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 108 | 4.00 | 80 | family_any | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 111 | 8.00 | 80 | broadening_proxy/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 111 | 8.00 | 80 | broadening_proxy/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 111 | 8.00 | 80 | broadening_proxy/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 111 | 8.00 | 80 | defensive_sector/H1 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 111 | 8.00 | 80 | defensive_sector/H2 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 111 | 8.00 | 80 | defensive_sector/H3 | 0/100 | 0.000 | [0.000, 0.037] |
| G2 | 111 | 8.00 | 80 | family_any | 0/100 | 0.000 | [0.000, 0.037] |
- H1: NOT_EXECUTABLE (defensive_sector NOT_EXECUTABLE; broadening_proxy NOT_EXECUTABLE) — H1: same arithmetic as V2 §4.3, reported for information; the §4.3 rule is written for H2/H3
- H2: NOT_EXECUTABLE (defensive_sector NOT_EXECUTABLE; broadening_proxy NOT_EXECUTABLE)
- H3: NOT_EXECUTABLE (defensive_sector NOT_EXECUTABLE; broadening_proxy NOT_EXECUTABLE)
Disposition rule: prereg V2 §4.3 — POWERED_IN_PRINCIPLE iff the pass rate reaches ≥ 0.50 at some δ ≤ 4.0 % in some G2 cell with N ≤ 40 and M ≥ min_m; NOT_EXECUTABLE only when every eligible slot is measured and none reaches it; NOT_EVALUATED otherwise, naming the unmeasured slots. Margins are the practical-significance bar and are never lowered to make a generator pass.

## H1 intersection–union components (δ > 0)

| cell | group | cond_a_true/n_ok | cond_b_true/n_ok | median delay_reduction | median burden_cut_b |
|---|---|---|---|---|---|
| 6 | defensive_sector | 73/100 | 100/100 | 5.000 | 0.488 |
| 6 | broadening_proxy | 79/100 | 100/100 | 5.000 | 0.483 |
| 7 | defensive_sector | 74/100 | 100/100 | 5.000 | 0.491 |
| 7 | broadening_proxy | 63/100 | 100/100 | 5.000 | 0.503 |
| 8 | defensive_sector | 76/100 | 100/100 | 5.000 | 0.486 |
| 8 | broadening_proxy | 69/100 | 100/100 | 5.000 | 0.486 |
| 12 | defensive_sector | 77/100 | 100/100 | 5.000 | 0.465 |
| 12 | broadening_proxy | 77/100 | 100/100 | 5.000 | 0.464 |
| 13 | defensive_sector | 71/100 | 100/100 | 5.000 | 0.475 |
| 13 | broadening_proxy | 74/100 | 100/100 | 5.000 | 0.471 |
| 14 | defensive_sector | 64/100 | 100/100 | 5.000 | 0.472 |
| 14 | broadening_proxy | 78/100 | 100/100 | 5.000 | 0.460 |
| 18 | defensive_sector | 78/100 | 100/100 | 5.000 | 0.430 |
| 18 | broadening_proxy | 65/100 | 100/100 | 5.000 | 0.442 |
| 19 | defensive_sector | 79/100 | 100/100 | 5.000 | 0.432 |
| 19 | broadening_proxy | 65/100 | 100/100 | 5.000 | 0.438 |
| 20 | defensive_sector | 64/100 | 100/100 | 5.000 | 0.439 |
| 20 | broadening_proxy | 64/100 | 100/100 | 5.000 | 0.439 |
| 100 | defensive_sector | 69/100 | 100/100 | 5.000 | 0.448 |
| 100 | broadening_proxy | 76/100 | 100/100 | 5.000 | 0.448 |
| 101 | defensive_sector | 63/100 | 100/100 | 5.000 | 0.437 |
| 101 | broadening_proxy | 70/100 | 100/100 | 5.000 | 0.451 |
| 102 | defensive_sector | 72/100 | 100/100 | 5.000 | 0.437 |
| 102 | broadening_proxy | 66/100 | 100/100 | 5.000 | 0.440 |
| 103 | defensive_sector | 74/100 | 96/100 | 5.000 | 0.377 |
| 103 | broadening_proxy | 75/100 | 92/100 | 5.000 | 0.396 |
| 104 | defensive_sector | 62/100 | 99/100 | 5.000 | 0.375 |
| 104 | broadening_proxy | 71/100 | 99/100 | 5.000 | 0.391 |
| 105 | defensive_sector | 62/100 | 100/100 | 5.000 | 0.376 |
| 105 | broadening_proxy | 74/100 | 100/100 | 5.000 | 0.380 |
| 106 | defensive_sector | 75/100 | 97/100 | 5.000 | 0.354 |
| 106 | broadening_proxy | 73/100 | 88/100 | 5.000 | 0.375 |
| 107 | defensive_sector | 78/100 | 96/100 | 5.000 | 0.350 |
| 107 | broadening_proxy | 72/100 | 99/100 | 5.000 | 0.365 |
| 108 | defensive_sector | 72/100 | 100/100 | 5.000 | 0.348 |
| 108 | broadening_proxy | 68/100 | 100/100 | 5.000 | 0.354 |
| 109 | defensive_sector | 82/100 | 98/100 | 5.000 | 0.423 |
| 109 | broadening_proxy | 72/100 | 100/100 | 5.000 | 0.447 |
| 110 | defensive_sector | 80/100 | 100/100 | 5.000 | 0.428 |
| 110 | broadening_proxy | 82/100 | 100/100 | 5.000 | 0.434 |
| 111 | defensive_sector | 76/100 | 100/100 | 5.000 | 0.434 |
| 111 | broadening_proxy | 74/100 | 100/100 | 5.000 | 0.439 |

## §8 item 10 — Option A null for every H1 result (V2 §2)

Derivation as in T12R §8 item 10 (σ̂ / ρ̂ from the read's formation window, matched to G1's own parameters on the 0.0005 / 0.05 grid; N = realised H1 honest-N; seed 20261014 + crc32("P0|<group>"), spawn key (j,), K = 1000; null quantile `numpy.quantile(finite, 0.975)`). Aggregate over the OK sims of each (cell, group):

| cell | group | sims | K | null status | seed key / crc32 | median σ̂ (gen → bank) | median ρ̂ (gen → bank) | median N (range) | T_a q0.975 median (range) | T_b q0.975 median (range) | median p_a / p_b / p_H1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 6 | broadening_proxy | 100 | 1000 | OK: 100 | P0\|broadening_proxy / 3923611080 | 0.0070 → 0.0070 | 0.498 → 0.50 | 20 (20–26) | 5.00 (5.00–5.00) | 0.607 (0.600–0.610) | 0.714 / 0.637 / 0.781 |
| 6 | defensive_sector | 100 | 1000 | OK: 100 | P0\|defensive_sector / 1109301814 | 0.0070 → 0.0070 | 0.500 → 0.50 | 23 (20–39) | 5.00 (5.00–5.00) | 0.598 (0.580–0.607) | 0.713 / 0.606 / 0.821 |
| 7 | broadening_proxy | 100 | 1000 | OK: 100 | P0\|broadening_proxy / 3923611080 | 0.0070 → 0.0070 | 0.500 → 0.50 | 40 (40–47) | 5.00 (5.00–5.00) | 0.579 (0.575–0.579) | 0.718 / 0.523 / 0.859 |
| 7 | defensive_sector | 100 | 1000 | OK: 100 | P0\|defensive_sector / 1109301814 | 0.0070 → 0.0070 | 0.501 → 0.50 | 45 (40–58) | 5.00 (5.00–5.00) | 0.573 (0.564–0.577) | 0.680 / 0.605 / 0.713 |
| 8 | broadening_proxy | 100 | 1000 | OK: 100 | P0\|broadening_proxy / 3923611080 | 0.0070 → 0.0070 | 0.500 → 0.50 | 80 (80–81) | 5.00 (5.00–5.00) | 0.557 (0.557–0.557) | 0.695 / 0.760 / 0.901 |
| 8 | defensive_sector | 100 | 1000 | OK: 100 | P0\|defensive_sector / 1109301814 | 0.0070 → 0.0070 | 0.500 → 0.50 | 95 (80–117) | 5.00 (5.00–5.00) | 0.552 (0.549–0.560) | 0.670 / 0.754 / 0.862 |
| 12 | broadening_proxy | 100 | 1000 | OK: 100 | P0\|broadening_proxy / 3923611080 | 0.0070 → 0.0070 | 0.499 → 0.50 | 20 (20–24) | 5.00 (5.00–5.00) | 0.607 (0.600–0.607) | 0.714 / 0.768 / 0.846 |
| 12 | defensive_sector | 100 | 1000 | OK: 100 | P0\|defensive_sector / 1109301814 | 0.0070 → 0.0070 | 0.502 → 0.50 | 22 (20–35) | 5.00 (5.00–5.00) | 0.602 (0.583–0.607) | 0.713 / 0.753 / 0.843 |
| 13 | broadening_proxy | 100 | 1000 | OK: 100 | P0\|broadening_proxy / 3923611080 | 0.0070 → 0.0070 | 0.500 → 0.50 | 40 (40–45) | 5.00 (5.00–5.00) | 0.579 (0.575–0.579) | 0.718 / 0.785 / 0.892 |
| 13 | defensive_sector | 100 | 1000 | OK: 100 | P0\|defensive_sector / 1109301814 | 0.0070 → 0.0070 | 0.500 → 0.50 | 46 (40–65) | 5.00 (5.00–5.00) | 0.572 (0.562–0.577) | 0.679 / 0.758 / 0.921 |
| 14 | broadening_proxy | 100 | 1000 | OK: 100 | P0\|broadening_proxy / 3923611080 | 0.0070 → 0.0070 | 0.501 → 0.50 | 80 (80–82) | 5.00 (5.00–5.00) | 0.557 (0.557–0.557) | 0.695 / 0.943 / 0.979 |
| 14 | defensive_sector | 100 | 1000 | OK: 100 | P0\|defensive_sector / 1109301814 | 0.0070 → 0.0070 | 0.500 → 0.50 | 93 (80–116) | 5.00 (5.00–5.00) | 0.552 (0.549–0.560) | 0.670 / 0.884 / 0.983 |
| 18 | broadening_proxy | 100 | 1000 | OK: 100 | P0\|broadening_proxy / 3923611080 | 0.0070 → 0.0070 | 0.498 → 0.50 | 20 (20–26) | 5.00 (5.00–5.00) | 0.607 (0.600–0.610) | 0.714 / 0.867 / 0.943 |
| 18 | defensive_sector | 100 | 1000 | OK: 100 | P0\|defensive_sector / 1109301814 | 0.0070 → 0.0070 | 0.501 → 0.50 | 22 (20–34) | 5.00 (5.00–5.00) | 0.602 (0.582–0.607) | 0.713 / 0.899 / 0.942 |
| 19 | broadening_proxy | 100 | 1000 | OK: 100 | P0\|broadening_proxy / 3923611080 | 0.0070 → 0.0070 | 0.500 → 0.50 | 40 (40–47) | 5.00 (5.00–5.00) | 0.579 (0.575–0.579) | 0.718 / 0.945 / 0.984 |
| 19 | defensive_sector | 100 | 1000 | OK: 100 | P0\|defensive_sector / 1109301814 | 0.0070 → 0.0070 | 0.500 → 0.50 | 46 (40–68) | 5.00 (5.00–5.00) | 0.572 (0.560–0.577) | 0.677 / 0.956 / 0.978 |
| 20 | broadening_proxy | 100 | 1000 | OK: 100 | P0\|broadening_proxy / 3923611080 | 0.0070 → 0.0070 | 0.501 → 0.50 | 80 (80–88) | 5.00 (5.00–5.00) | 0.557 (0.557–0.559) | 0.695 / 0.988 / 0.996 |
| 20 | defensive_sector | 100 | 1000 | OK: 100 | P0\|defensive_sector / 1109301814 | 0.0070 → 0.0070 | 0.501 → 0.50 | 93 (80–112) | 5.00 (5.00–5.00) | 0.553 (0.549–0.560) | 0.672 / 0.991 / 0.999 |
| 100 | broadening_proxy | 100 | 1000 | OK: 100 | P0\|broadening_proxy / 3923611080 | 0.0070 → 0.0070 | 0.504 → 0.50 | 20 (20–25) | 5.00 (5.00–5.00) | 0.607 (0.600–0.610) | 0.714 / 0.833 / 0.934 |
| 100 | defensive_sector | 100 | 1000 | OK: 100 | P0\|defensive_sector / 1109301814 | 0.0070 → 0.0070 | 0.501 → 0.50 | 23 (20–31) | 5.00 (5.00–5.00) | 0.597 (0.586–0.607) | 0.713 / 0.843 / 0.945 |
| 101 | broadening_proxy | 100 | 1000 | OK: 100 | P0\|broadening_proxy / 3923611080 | 0.0070 → 0.0070 | 0.502 → 0.50 | 40 (40–47) | 5.00 (5.00–5.00) | 0.579 (0.575–0.579) | 0.718 / 0.898 / 0.976 |
| 101 | defensive_sector | 100 | 1000 | OK: 100 | P0\|defensive_sector / 1109301814 | 0.0070 → 0.0070 | 0.500 → 0.50 | 44 (40–60) | 5.00 (5.00–5.00) | 0.573 (0.564–0.577) | 0.684 / 0.952 / 0.983 |
| 102 | broadening_proxy | 100 | 1000 | OK: 100 | P0\|broadening_proxy / 3923611080 | 0.0070 → 0.0070 | 0.500 → 0.50 | 80 (80–92) | 5.00 (5.00–5.00) | 0.557 (0.554–0.560) | 0.695 / 0.988 / 0.996 |
| 102 | defensive_sector | 100 | 1000 | OK: 100 | P0\|defensive_sector / 1109301814 | 0.0070 → 0.0070 | 0.501 → 0.50 | 92 (80–118) | 5.00 (5.00–5.00) | 0.553 (0.549–0.560) | 0.671 / 0.993 / 0.998 |
| 103 | broadening_proxy | 100 | 1000 | OK: 100 | P0\|broadening_proxy / 3923611080 | 0.0070 → 0.0070 | 0.500 → 0.50 | 20 (20–24) | 5.00 (5.00–5.00) | 0.607 (0.600–0.610) | 0.714 / 0.967 / 0.969 |
| 103 | defensive_sector | 100 | 1000 | OK: 100 | P0\|defensive_sector / 1109301814 | 0.0070 → 0.0070 | 0.503 → 0.50 | 22 (20–33) | 5.00 (5.00–5.00) | 0.602 (0.582–0.611) | 0.713 / 0.984 / 0.986 |
| 104 | broadening_proxy | 100 | 1000 | OK: 100 | P0\|broadening_proxy / 3923611080 | 0.0070 → 0.0070 | 0.503 → 0.50 | 40 (40–45) | 5.00 (5.00–5.00) | 0.579 (0.575–0.579) | 0.718 / 0.998 / 0.999 |
| 104 | defensive_sector | 100 | 1000 | OK: 100 | P0\|defensive_sector / 1109301814 | 0.0070 → 0.0070 | 0.503 → 0.50 | 46 (40–62) | 5.00 (5.00–5.00) | 0.572 (0.563–0.577) | 0.682 / 1.000 / 1.000 |
| 105 | broadening_proxy | 100 | 1000 | OK: 100 | P0\|broadening_proxy / 3923611080 | 0.0070 → 0.0070 | 0.502 → 0.50 | 80 (80–89) | 5.00 (5.00–5.00) | 0.557 (0.556–0.560) | 0.695 / 1.000 / 1.000 |
| 105 | defensive_sector | 100 | 1000 | OK: 100 | P0\|defensive_sector / 1109301814 | 0.0070 → 0.0070 | 0.503 → 0.50 | 92 (80–125) | 5.00 (5.00–5.00) | 0.552 (0.549–0.560) | 0.678 / 1.000 / 1.000 |
| 106 | broadening_proxy | 100 | 1000 | OK: 100 | P0\|broadening_proxy / 3923611080 | 0.0071 → 0.0070 | 0.511 → 0.50 | 20 (20–26) | 5.00 (5.00–5.00) | 0.607 (0.600–0.610) | 0.714 / 0.982 / 0.983 |
| 106 | defensive_sector | 100 | 1000 | OK: 100 | P0\|defensive_sector / 1109301814 | 0.0071 → 0.0070 | 0.510 → 0.50 | 22 (20–32) | 5.00 (5.00–5.00) | 0.602 (0.585–0.607) | 0.713 / 0.995 / 0.995 |
| 107 | broadening_proxy | 100 | 1000 | OK: 100 | P0\|broadening_proxy / 3923611080 | 0.0071 → 0.0070 | 0.509 → 0.50 | 40 (40–51) | 5.00 (5.00–5.00) | 0.579 (0.569–0.582) | 0.718 / 1.000 / 1.000 |
| 107 | defensive_sector | 100 | 1000 | OK: 100 | P0\|defensive_sector / 1109301814 | 0.0071 → 0.0070 | 0.509 → 0.50 | 45 (40–64) | 5.00 (5.00–5.00) | 0.573 (0.564–0.577) | 0.675 / 1.000 / 1.000 |
| 108 | broadening_proxy | 100 | 1000 | OK: 100 | P0\|broadening_proxy / 3923611080 | 0.0071 → 0.0070 | 0.509 → 0.50 | 80 (80–87) | 5.00 (5.00–5.00) | 0.557 (0.557–0.560) | 0.695 / 1.000 / 1.000 |
| 108 | defensive_sector | 100 | 1000 | OK: 100 | P0\|defensive_sector / 1109301814 | 0.0071 → 0.0070 | 0.509 → 0.50 | 91 (80–120) | 5.00 (5.00–5.00) | 0.553 (0.549–0.560) | 0.671 / 1.000 / 1.000 |
| 109 | broadening_proxy | 100 | 1000 | OK: 100 | P0\|broadening_proxy / 3923611080 | 0.0073 → 0.0075 | 0.546 → 0.55 | 20 (20–25) | 5.00 (5.00–5.00) | 0.614 (0.600–0.620) | 0.716 / 0.855 / 0.943 |
| 109 | defensive_sector | 100 | 1000 | OK: 100 | P0\|defensive_sector / 1109301814 | 0.0073 → 0.0075 | 0.543 → 0.55 | 21 (20–28) | 5.00 (5.00–5.00) | 0.606 (0.590–0.611) | 0.717 / 0.920 / 0.946 |
| 110 | broadening_proxy | 100 | 1000 | OK: 100 | P0\|broadening_proxy / 3923611080 | 0.0073 → 0.0075 | 0.546 → 0.55 | 40 (40–48) | 5.00 (5.00–5.00) | 0.589 (0.577–0.589) | 0.677 / 0.957 / 0.974 |
| 110 | defensive_sector | 100 | 1000 | OK: 100 | P0\|defensive_sector / 1109301814 | 0.0073 → 0.0075 | 0.548 → 0.55 | 45 (40–62) | 5.00 (5.00–5.00) | 0.580 (0.563–0.586) | 0.680 / 0.972 / 0.984 |
| 111 | broadening_proxy | 100 | 1000 | OK: 100 | P0\|broadening_proxy / 3923611080 | 0.0073 → 0.0075 | 0.547 → 0.55 | 80 (80–91) | 5.00 (5.00–5.00) | 0.565 (0.557–0.565) | 0.689 / 0.990 / 0.996 |
| 111 | defensive_sector | 100 | 1000 | OK: 100 | P0\|defensive_sector / 1109301814 | 0.0073 → 0.0075 | 0.549 → 0.55 | 88 (80–121) | 5.00 (5.00–5.00) | 0.562 (0.552–0.564) | 0.675 / 0.997 / 0.998 |

## Per-arm metrics (V2 §3.4)

| cell | σ | δ | ρ | N | group | A0 raw burden | A0 burden | A1 burden | A1 median delay | A1 detection | A2 median delay | sims |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 6 | 0.007 | 0.003 | 0.500 | 20 | defensive_sector | 11.057 | 5.062 | 2.612 | 18.000 | 0.939 | 22.000 | 100 |
| 6 | 0.007 | 0.003 | 0.500 | 20 | broadening_proxy | 11.049 | 5.063 | 2.609 | 18.000 | 0.957 | 22.000 | 100 |
| 7 | 0.007 | 0.003 | 0.500 | 40 | defensive_sector | 11.053 | 5.134 | 2.611 | 18.000 | 0.949 | 22.000 | 100 |
| 7 | 0.007 | 0.003 | 0.500 | 40 | broadening_proxy | 11.037 | 5.145 | 2.567 | 18.000 | 0.941 | 22.000 | 100 |
| 8 | 0.007 | 0.003 | 0.500 | 80 | defensive_sector | 11.042 | 5.095 | 2.624 | 18.000 | 0.944 | 22.000 | 100 |
| 8 | 0.007 | 0.003 | 0.500 | 80 | broadening_proxy | 11.047 | 5.089 | 2.625 | 18.000 | 0.936 | 22.000 | 100 |
| 12 | 0.007 | 0.005 | 0.500 | 20 | defensive_sector | 11.100 | 5.076 | 2.656 | 18.000 | 0.945 | 22.000 | 100 |
| 12 | 0.007 | 0.005 | 0.500 | 20 | broadening_proxy | 11.053 | 4.948 | 2.648 | 18.000 | 0.943 | 22.000 | 100 |
| 13 | 0.007 | 0.005 | 0.500 | 40 | defensive_sector | 11.067 | 5.071 | 2.670 | 18.000 | 0.947 | 22.000 | 100 |
| 13 | 0.007 | 0.005 | 0.500 | 40 | broadening_proxy | 11.034 | 5.066 | 2.654 | 18.000 | 0.940 | 22.000 | 100 |
| 14 | 0.007 | 0.005 | 0.500 | 80 | defensive_sector | 11.050 | 5.067 | 2.672 | 18.000 | 0.942 | 22.000 | 100 |
| 14 | 0.007 | 0.005 | 0.500 | 80 | broadening_proxy | 11.050 | 5.017 | 2.717 | 18.000 | 0.938 | 22.000 | 100 |
| 18 | 0.007 | 0.010 | 0.500 | 20 | defensive_sector | 11.094 | 4.854 | 2.790 | 17.500 | 0.935 | 22.000 | 100 |
| 18 | 0.007 | 0.010 | 0.500 | 20 | broadening_proxy | 11.056 | 4.866 | 2.705 | 17.000 | 0.958 | 22.000 | 100 |
| 19 | 0.007 | 0.010 | 0.500 | 40 | defensive_sector | 11.082 | 4.906 | 2.769 | 18.000 | 0.937 | 22.000 | 100 |
| 19 | 0.007 | 0.010 | 0.500 | 40 | broadening_proxy | 11.054 | 4.918 | 2.732 | 18.000 | 0.945 | 22.000 | 100 |
| 20 | 0.007 | 0.010 | 0.500 | 80 | defensive_sector | 11.066 | 4.891 | 2.767 | 18.000 | 0.941 | 22.000 | 100 |
| 20 | 0.007 | 0.010 | 0.500 | 80 | broadening_proxy | 11.060 | 4.873 | 2.723 | 18.000 | 0.941 | 22.000 | 100 |
| 100 | 0.007 | 0.010 | 0.500 | 20 | defensive_sector | 11.080 | 4.881 | 2.727 | 17.000 | 0.944 | 22.000 | 100 |
| 100 | 0.007 | 0.010 | 0.500 | 20 | broadening_proxy | 11.064 | 4.933 | 2.750 | 18.000 | 0.957 | 22.000 | 100 |
| 101 | 0.007 | 0.010 | 0.500 | 40 | defensive_sector | 11.080 | 4.885 | 2.751 | 18.000 | 0.939 | 22.000 | 100 |
| 101 | 0.007 | 0.010 | 0.500 | 40 | broadening_proxy | 11.049 | 4.909 | 2.725 | 18.000 | 0.941 | 22.000 | 100 |
| 102 | 0.007 | 0.010 | 0.500 | 80 | defensive_sector | 11.078 | 4.915 | 2.764 | 18.000 | 0.944 | 22.000 | 100 |
| 102 | 0.007 | 0.010 | 0.500 | 80 | broadening_proxy | 11.058 | 4.904 | 2.721 | 18.000 | 0.937 | 22.000 | 100 |
| 103 | 0.007 | 0.020 | 0.500 | 20 | defensive_sector | 11.137 | 4.600 | 2.857 | 17.000 | 0.943 | 22.000 | 100 |
| 103 | 0.007 | 0.020 | 0.500 | 20 | broadening_proxy | 11.090 | 4.650 | 2.812 | 17.000 | 0.954 | 22.000 | 100 |
| 104 | 0.007 | 0.020 | 0.500 | 40 | defensive_sector | 11.132 | 4.573 | 2.884 | 18.000 | 0.946 | 22.000 | 100 |
| 104 | 0.007 | 0.020 | 0.500 | 40 | broadening_proxy | 11.117 | 4.618 | 2.831 | 18.000 | 0.952 | 22.000 | 100 |
| 105 | 0.007 | 0.020 | 0.500 | 80 | defensive_sector | 11.135 | 4.627 | 2.901 | 18.000 | 0.952 | 22.000 | 100 |
| 105 | 0.007 | 0.020 | 0.500 | 80 | broadening_proxy | 11.119 | 4.625 | 2.864 | 17.000 | 0.950 | 22.000 | 100 |
| 106 | 0.007 | 0.040 | 0.500 | 20 | defensive_sector | 11.249 | 4.124 | 2.635 | 17.000 | 0.964 | 22.000 | 100 |
| 106 | 0.007 | 0.040 | 0.500 | 20 | broadening_proxy | 11.215 | 4.196 | 2.675 | 17.000 | 0.961 | 22.000 | 100 |
| 107 | 0.007 | 0.040 | 0.500 | 40 | defensive_sector | 11.270 | 4.154 | 2.713 | 17.000 | 0.955 | 22.000 | 100 |
| 107 | 0.007 | 0.040 | 0.500 | 40 | broadening_proxy | 11.244 | 4.223 | 2.691 | 17.000 | 0.960 | 22.000 | 100 |
| 108 | 0.007 | 0.040 | 0.500 | 80 | defensive_sector | 11.272 | 4.153 | 2.704 | 17.000 | 0.957 | 22.000 | 100 |
| 108 | 0.007 | 0.040 | 0.500 | 80 | broadening_proxy | 11.265 | 4.167 | 2.679 | 17.000 | 0.954 | 22.000 | 100 |
| 109 | 0.007 | 0.080 | 0.500 | 20 | defensive_sector | 11.383 | 3.565 | 2.021 | 16.000 | 0.966 | 21.000 | 100 |
| 109 | 0.007 | 0.080 | 0.500 | 20 | broadening_proxy | 11.345 | 3.511 | 1.926 | 17.000 | 0.964 | 21.000 | 100 |
| 110 | 0.007 | 0.080 | 0.500 | 40 | defensive_sector | 11.377 | 3.516 | 2.001 | 16.000 | 0.962 | 21.000 | 100 |
| 110 | 0.007 | 0.080 | 0.500 | 40 | broadening_proxy | 11.358 | 3.547 | 2.000 | 16.000 | 0.965 | 21.000 | 100 |
| 111 | 0.007 | 0.080 | 0.500 | 80 | defensive_sector | 11.402 | 3.486 | 1.976 | 16.000 | 0.965 | 21.000 | 100 |
| 111 | 0.007 | 0.080 | 0.500 | 80 | broadening_proxy | 11.359 | 3.550 | 1.995 | 16.000 | 0.957 | 21.000 | 100 |
Medians over OK sims. "A0 raw" = A0 fires before the 5-quiet-session suppression, through the same window filter, merge and classifier as A0 ("suppressed"); burden = REPEATED + LATE + FALSE_START per measured pair-year.

## §8 item 13 — C2 direction strata (V2 §6)

Prereg V2 §6 direction stratification (CHAL GATES #2); NOT the sealed Trend-Persistence-era study also called 'C2', which stays closed. Points only, no p-values; SOURCE_LIMITED where the stratum's clustered n < 5.
| cell | row | stratum | sims | status counts | median n | median point(s) |
|---|---|---|---|---|---|---|
| 6 | defensive_sector/H1 | both_up | 100 | COMPUTED: 75, SOURCE_LIMITED: 25 | 6.000 | 6.000 / 0.773 |
| 6 | defensive_sector/H1 | both_down | 100 | COMPUTED: 100 | 12.000 | 5.000 / 0.188 |
| 6 | defensive_sector/H1 | mixed | 100 | COMPUTED: 92, SOURCE_LIMITED: 8 | 8.000 | 5.000 / 0.148 |
| 6 | defensive_sector/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 6 | defensive_sector/H2 | both_up | 100 | COMPUTED: 94, SOURCE_LIMITED: 6 | 8.000 | -0.006 |
| 6 | defensive_sector/H2 | both_down | 100 | COMPUTED: 100 | 13.000 | -0.002 |
| 6 | defensive_sector/H2 | mixed | 100 | COMPUTED: 99, SOURCE_LIMITED: 1 | 10.000 | -0.005 |
| 6 | defensive_sector/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 6 | defensive_sector/H3 | both_up | 100 | COMPUTED: 94, SOURCE_LIMITED: 6 | 8.000 | -0.002 |
| 6 | defensive_sector/H3 | both_down | 100 | COMPUTED: 100 | 13.000 | 0.001 |
| 6 | defensive_sector/H3 | mixed | 100 | COMPUTED: 99, SOURCE_LIMITED: 1 | 10.000 | -0.001 |
| 6 | defensive_sector/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 6 | broadening_proxy/H1 | both_up | 100 | COMPUTED: 61, SOURCE_LIMITED: 39 | 5.000 | 5.000 / 0.782 |
| 6 | broadening_proxy/H1 | both_down | 100 | COMPUTED: 99, SOURCE_LIMITED: 1 | 10.000 | 5.000 / 0.234 |
| 6 | broadening_proxy/H1 | mixed | 100 | COMPUTED: 85, SOURCE_LIMITED: 15 | 6.000 | 5.000 / 0.116 |
| 6 | broadening_proxy/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 6 | broadening_proxy/H2 | both_up | 100 | COMPUTED: 78, SOURCE_LIMITED: 22 | 6.000 | -0.000 |
| 6 | broadening_proxy/H2 | both_down | 100 | COMPUTED: 100 | 11.000 | -0.002 |
| 6 | broadening_proxy/H2 | mixed | 100 | COMPUTED: 96, SOURCE_LIMITED: 4 | 9.000 | -0.003 |
| 6 | broadening_proxy/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 6 | broadening_proxy/H3 | both_up | 100 | COMPUTED: 78, SOURCE_LIMITED: 22 | 6.000 | -0.001 |
| 6 | broadening_proxy/H3 | both_down | 100 | COMPUTED: 100 | 11.000 | -0.000 |
| 6 | broadening_proxy/H3 | mixed | 100 | COMPUTED: 96, SOURCE_LIMITED: 4 | 9.000 | -0.003 |
| 6 | broadening_proxy/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 7 | defensive_sector/H1 | both_up | 100 | COMPUTED: 98, SOURCE_LIMITED: 2 | 11.000 | 5.000 / 0.784 |
| 7 | defensive_sector/H1 | both_down | 100 | COMPUTED: 100 | 22.000 | 5.000 / 0.193 |
| 7 | defensive_sector/H1 | mixed | 100 | COMPUTED: 100 | 16.000 | 4.000 / 0.140 |
| 7 | defensive_sector/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 7 | defensive_sector/H2 | both_up | 100 | COMPUTED: 100 | 14.000 | -0.002 |
| 7 | defensive_sector/H2 | both_down | 100 | COMPUTED: 100 | 25.000 | -0.002 |
| 7 | defensive_sector/H2 | mixed | 100 | COMPUTED: 100 | 21.000 | -0.000 |
| 7 | defensive_sector/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 7 | defensive_sector/H3 | both_up | 100 | COMPUTED: 100 | 14.000 | -0.000 |
| 7 | defensive_sector/H3 | both_down | 100 | COMPUTED: 100 | 25.000 | 0.001 |
| 7 | defensive_sector/H3 | mixed | 100 | COMPUTED: 100 | 21.000 | -0.001 |
| 7 | defensive_sector/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 7 | broadening_proxy/H1 | both_up | 100 | COMPUTED: 97, SOURCE_LIMITED: 3 | 10.000 | 5.000 / 0.781 |
| 7 | broadening_proxy/H1 | both_down | 100 | COMPUTED: 100 | 19.000 | 5.000 / 0.213 |
| 7 | broadening_proxy/H1 | mixed | 100 | COMPUTED: 100 | 13.000 | 4.000 / 0.144 |
| 7 | broadening_proxy/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 7 | broadening_proxy/H2 | both_up | 100 | COMPUTED: 99, SOURCE_LIMITED: 1 | 12.000 | -0.002 |
| 7 | broadening_proxy/H2 | both_down | 100 | COMPUTED: 100 | 22.000 | -0.002 |
| 7 | broadening_proxy/H2 | mixed | 100 | COMPUTED: 100 | 17.000 | -0.003 |
| 7 | broadening_proxy/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 7 | broadening_proxy/H3 | both_up | 100 | COMPUTED: 99, SOURCE_LIMITED: 1 | 12.000 | 0.000 |
| 7 | broadening_proxy/H3 | both_down | 100 | COMPUTED: 100 | 22.000 | 0.001 |
| 7 | broadening_proxy/H3 | mixed | 100 | COMPUTED: 100 | 17.000 | 0.000 |
| 7 | broadening_proxy/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 8 | defensive_sector/H1 | both_up | 100 | COMPUTED: 100 | 23.000 | 6.000 / 0.777 |
| 8 | defensive_sector/H1 | both_down | 100 | COMPUTED: 100 | 45.500 | 5.000 / 0.204 |
| 8 | defensive_sector/H1 | mixed | 100 | COMPUTED: 100 | 33.000 | 4.000 / 0.120 |
| 8 | defensive_sector/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 8 | defensive_sector/H2 | both_up | 100 | COMPUTED: 100 | 29.000 | -0.002 |
| 8 | defensive_sector/H2 | both_down | 100 | COMPUTED: 100 | 51.000 | -0.001 |
| 8 | defensive_sector/H2 | mixed | 100 | COMPUTED: 100 | 41.000 | -0.002 |
| 8 | defensive_sector/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 8 | defensive_sector/H3 | both_up | 100 | COMPUTED: 100 | 29.000 | -0.000 |
| 8 | defensive_sector/H3 | both_down | 100 | COMPUTED: 100 | 51.000 | -0.001 |
| 8 | defensive_sector/H3 | mixed | 100 | COMPUTED: 100 | 41.000 | 0.001 |
| 8 | defensive_sector/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 8 | broadening_proxy/H1 | both_up | 100 | COMPUTED: 100 | 18.000 | 5.000 / 0.779 |
| 8 | broadening_proxy/H1 | both_down | 100 | COMPUTED: 100 | 38.500 | 5.000 / 0.201 |
| 8 | broadening_proxy/H1 | mixed | 100 | COMPUTED: 100 | 26.000 | 4.000 / 0.132 |
| 8 | broadening_proxy/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 8 | broadening_proxy/H2 | both_up | 100 | COMPUTED: 100 | 24.000 | -0.002 |
| 8 | broadening_proxy/H2 | both_down | 100 | COMPUTED: 100 | 45.000 | -0.001 |
| 8 | broadening_proxy/H2 | mixed | 100 | COMPUTED: 100 | 34.000 | -0.004 |
| 8 | broadening_proxy/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 8 | broadening_proxy/H3 | both_up | 100 | COMPUTED: 100 | 24.000 | -0.001 |
| 8 | broadening_proxy/H3 | both_down | 100 | COMPUTED: 100 | 45.000 | -0.001 |
| 8 | broadening_proxy/H3 | mixed | 100 | COMPUTED: 100 | 34.000 | 0.001 |
| 8 | broadening_proxy/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 12 | defensive_sector/H1 | both_up | 100 | COMPUTED: 69, SOURCE_LIMITED: 31 | 6.000 | 5.000 / 0.765 |
| 12 | defensive_sector/H1 | both_down | 100 | COMPUTED: 100 | 11.000 | 5.000 / 0.199 |
| 12 | defensive_sector/H1 | mixed | 100 | COMPUTED: 98, SOURCE_LIMITED: 2 | 8.000 | 4.500 / 0.089 |
| 12 | defensive_sector/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 12 | defensive_sector/H2 | both_up | 100 | COMPUTED: 93, SOURCE_LIMITED: 7 | 8.000 | -0.002 |
| 12 | defensive_sector/H2 | both_down | 100 | COMPUTED: 100 | 12.500 | -0.002 |
| 12 | defensive_sector/H2 | mixed | 100 | COMPUTED: 100 | 10.000 | -0.007 |
| 12 | defensive_sector/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 12 | defensive_sector/H3 | both_up | 100 | COMPUTED: 93, SOURCE_LIMITED: 7 | 8.000 | 0.001 |
| 12 | defensive_sector/H3 | both_down | 100 | COMPUTED: 100 | 12.500 | 0.001 |
| 12 | defensive_sector/H3 | mixed | 100 | COMPUTED: 100 | 10.000 | -0.001 |
| 12 | defensive_sector/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 12 | broadening_proxy/H1 | both_up | 100 | COMPUTED: 50, SOURCE_LIMITED: 50 | 4.500 | 5.000 / 0.766 |
| 12 | broadening_proxy/H1 | both_down | 100 | COMPUTED: 99, SOURCE_LIMITED: 1 | 10.000 | 5.000 / 0.153 |
| 12 | broadening_proxy/H1 | mixed | 100 | COMPUTED: 86, SOURCE_LIMITED: 14 | 6.000 | 5.000 / 0.105 |
| 12 | broadening_proxy/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 12 | broadening_proxy/H2 | both_up | 100 | COMPUTED: 74, SOURCE_LIMITED: 26 | 6.000 | -0.002 |
| 12 | broadening_proxy/H2 | both_down | 100 | COMPUTED: 100 | 11.000 | -0.002 |
| 12 | broadening_proxy/H2 | mixed | 100 | COMPUTED: 95, SOURCE_LIMITED: 5 | 8.500 | -0.004 |
| 12 | broadening_proxy/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 12 | broadening_proxy/H3 | both_up | 100 | COMPUTED: 74, SOURCE_LIMITED: 26 | 6.000 | 0.003 |
| 12 | broadening_proxy/H3 | both_down | 100 | COMPUTED: 100 | 11.000 | -0.000 |
| 12 | broadening_proxy/H3 | mixed | 100 | COMPUTED: 95, SOURCE_LIMITED: 5 | 8.500 | 0.001 |
| 12 | broadening_proxy/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 13 | defensive_sector/H1 | both_up | 100 | COMPUTED: 100 | 12.000 | 5.000 / 0.768 |
| 13 | defensive_sector/H1 | both_down | 100 | COMPUTED: 100 | 22.000 | 5.000 / 0.185 |
| 13 | defensive_sector/H1 | mixed | 100 | COMPUTED: 100 | 16.000 | 4.000 / 0.107 |
| 13 | defensive_sector/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 13 | defensive_sector/H2 | both_up | 100 | COMPUTED: 100 | 15.500 | -0.002 |
| 13 | defensive_sector/H2 | both_down | 100 | COMPUTED: 100 | 25.000 | -0.002 |
| 13 | defensive_sector/H2 | mixed | 100 | COMPUTED: 100 | 20.500 | -0.004 |
| 13 | defensive_sector/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 13 | defensive_sector/H3 | both_up | 100 | COMPUTED: 100 | 15.500 | 0.000 |
| 13 | defensive_sector/H3 | both_down | 100 | COMPUTED: 100 | 25.000 | -0.000 |
| 13 | defensive_sector/H3 | mixed | 100 | COMPUTED: 100 | 20.500 | -0.000 |
| 13 | defensive_sector/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 13 | broadening_proxy/H1 | both_up | 100 | COMPUTED: 99, SOURCE_LIMITED: 1 | 9.500 | 5.000 / 0.772 |
| 13 | broadening_proxy/H1 | both_down | 100 | COMPUTED: 100 | 19.000 | 5.000 / 0.194 |
| 13 | broadening_proxy/H1 | mixed | 100 | COMPUTED: 100 | 13.000 | 4.000 / 0.081 |
| 13 | broadening_proxy/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 13 | broadening_proxy/H2 | both_up | 100 | COMPUTED: 100 | 13.000 | -0.002 |
| 13 | broadening_proxy/H2 | both_down | 100 | COMPUTED: 100 | 22.000 | -0.001 |
| 13 | broadening_proxy/H2 | mixed | 100 | COMPUTED: 100 | 17.000 | -0.004 |
| 13 | broadening_proxy/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 13 | broadening_proxy/H3 | both_up | 100 | COMPUTED: 100 | 13.000 | -0.001 |
| 13 | broadening_proxy/H3 | both_down | 100 | COMPUTED: 100 | 22.000 | -0.000 |
| 13 | broadening_proxy/H3 | mixed | 100 | COMPUTED: 100 | 17.000 | -0.001 |
| 13 | broadening_proxy/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 14 | defensive_sector/H1 | both_up | 100 | COMPUTED: 100 | 24.000 | 5.000 / 0.767 |
| 14 | defensive_sector/H1 | both_down | 100 | COMPUTED: 100 | 46.000 | 5.000 / 0.186 |
| 14 | defensive_sector/H1 | mixed | 100 | COMPUTED: 100 | 32.000 | 4.000 / 0.101 |
| 14 | defensive_sector/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 14 | defensive_sector/H2 | both_up | 100 | COMPUTED: 100 | 31.000 | -0.002 |
| 14 | defensive_sector/H2 | both_down | 100 | COMPUTED: 100 | 51.000 | -0.001 |
| 14 | defensive_sector/H2 | mixed | 100 | COMPUTED: 100 | 41.000 | -0.003 |
| 14 | defensive_sector/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 14 | defensive_sector/H3 | both_up | 100 | COMPUTED: 100 | 31.000 | -0.001 |
| 14 | defensive_sector/H3 | both_down | 100 | COMPUTED: 100 | 51.000 | 0.000 |
| 14 | defensive_sector/H3 | mixed | 100 | COMPUTED: 100 | 41.000 | -0.002 |
| 14 | defensive_sector/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 14 | broadening_proxy/H1 | both_up | 100 | COMPUTED: 100 | 18.000 | 5.000 / 0.768 |
| 14 | broadening_proxy/H1 | both_down | 100 | COMPUTED: 100 | 38.000 | 5.000 / 0.175 |
| 14 | broadening_proxy/H1 | mixed | 100 | COMPUTED: 100 | 26.000 | 4.000 / 0.064 |
| 14 | broadening_proxy/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 14 | broadening_proxy/H2 | both_up | 100 | COMPUTED: 100 | 25.000 | -0.001 |
| 14 | broadening_proxy/H2 | both_down | 100 | COMPUTED: 100 | 44.500 | -0.002 |
| 14 | broadening_proxy/H2 | mixed | 100 | COMPUTED: 100 | 34.000 | -0.002 |
| 14 | broadening_proxy/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 14 | broadening_proxy/H3 | both_up | 100 | COMPUTED: 100 | 25.000 | 0.001 |
| 14 | broadening_proxy/H3 | both_down | 100 | COMPUTED: 100 | 44.500 | -0.000 |
| 14 | broadening_proxy/H3 | mixed | 100 | COMPUTED: 100 | 34.000 | -0.001 |
| 14 | broadening_proxy/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 18 | defensive_sector/H1 | both_up | 100 | COMPUTED: 74, SOURCE_LIMITED: 26 | 6.000 | 5.000 / 0.746 |
| 18 | defensive_sector/H1 | both_down | 100 | COMPUTED: 99, SOURCE_LIMITED: 1 | 10.000 | 5.000 / 0.170 |
| 18 | defensive_sector/H1 | mixed | 100 | COMPUTED: 92, SOURCE_LIMITED: 8 | 8.000 | 4.000 / -0.059 |
| 18 | defensive_sector/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 18 | defensive_sector/H2 | both_up | 100 | COMPUTED: 92, SOURCE_LIMITED: 8 | 8.000 | -0.002 |
| 18 | defensive_sector/H2 | both_down | 100 | COMPUTED: 100 | 13.000 | -0.003 |
| 18 | defensive_sector/H2 | mixed | 100 | COMPUTED: 100 | 10.000 | -0.004 |
| 18 | defensive_sector/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 18 | defensive_sector/H3 | both_up | 100 | COMPUTED: 92, SOURCE_LIMITED: 8 | 8.000 | 0.001 |
| 18 | defensive_sector/H3 | both_down | 100 | COMPUTED: 100 | 13.000 | -0.001 |
| 18 | defensive_sector/H3 | mixed | 100 | COMPUTED: 100 | 10.000 | -0.001 |
| 18 | defensive_sector/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 18 | broadening_proxy/H1 | both_up | 100 | COMPUTED: 54, SOURCE_LIMITED: 46 | 5.000 | 5.000 / 0.750 |
| 18 | broadening_proxy/H1 | both_down | 100 | COMPUTED: 99, SOURCE_LIMITED: 1 | 9.000 | 5.000 / 0.156 |
| 18 | broadening_proxy/H1 | mixed | 100 | COMPUTED: 89, SOURCE_LIMITED: 11 | 8.000 | 4.000 / 0.038 |
| 18 | broadening_proxy/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 18 | broadening_proxy/H2 | both_up | 100 | COMPUTED: 74, SOURCE_LIMITED: 26 | 7.000 | -0.003 |
| 18 | broadening_proxy/H2 | both_down | 100 | COMPUTED: 100 | 11.000 | -0.003 |
| 18 | broadening_proxy/H2 | mixed | 100 | COMPUTED: 100 | 9.000 | -0.005 |
| 18 | broadening_proxy/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 18 | broadening_proxy/H3 | both_up | 100 | COMPUTED: 74, SOURCE_LIMITED: 26 | 7.000 | -0.001 |
| 18 | broadening_proxy/H3 | both_down | 100 | COMPUTED: 100 | 11.000 | 0.000 |
| 18 | broadening_proxy/H3 | mixed | 100 | COMPUTED: 100 | 9.000 | -0.001 |
| 18 | broadening_proxy/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 19 | defensive_sector/H1 | both_up | 100 | COMPUTED: 99, SOURCE_LIMITED: 1 | 11.500 | 5.000 / 0.744 |
| 19 | defensive_sector/H1 | both_down | 100 | COMPUTED: 100 | 22.000 | 5.000 / 0.156 |
| 19 | defensive_sector/H1 | mixed | 100 | COMPUTED: 100 | 16.000 | 4.000 / 0.006 |
| 19 | defensive_sector/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 19 | defensive_sector/H2 | both_up | 100 | COMPUTED: 100 | 15.000 | 0.000 |
| 19 | defensive_sector/H2 | both_down | 100 | COMPUTED: 100 | 25.000 | -0.001 |
| 19 | defensive_sector/H2 | mixed | 100 | COMPUTED: 100 | 21.000 | -0.003 |
| 19 | defensive_sector/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 19 | defensive_sector/H3 | both_up | 100 | COMPUTED: 100 | 15.000 | 0.001 |
| 19 | defensive_sector/H3 | both_down | 100 | COMPUTED: 100 | 25.000 | 0.001 |
| 19 | defensive_sector/H3 | mixed | 100 | COMPUTED: 100 | 21.000 | -0.000 |
| 19 | defensive_sector/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 19 | broadening_proxy/H1 | both_up | 100 | COMPUTED: 99, SOURCE_LIMITED: 1 | 10.000 | 5.000 / 0.754 |
| 19 | broadening_proxy/H1 | both_down | 100 | COMPUTED: 100 | 19.000 | 5.000 / 0.166 |
| 19 | broadening_proxy/H1 | mixed | 100 | COMPUTED: 100 | 13.000 | 4.000 / 0.000 |
| 19 | broadening_proxy/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 19 | broadening_proxy/H2 | both_up | 100 | COMPUTED: 100 | 13.000 | -0.003 |
| 19 | broadening_proxy/H2 | both_down | 100 | COMPUTED: 100 | 23.000 | -0.003 |
| 19 | broadening_proxy/H2 | mixed | 100 | COMPUTED: 100 | 17.500 | -0.004 |
| 19 | broadening_proxy/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 19 | broadening_proxy/H3 | both_up | 100 | COMPUTED: 100 | 13.000 | -0.001 |
| 19 | broadening_proxy/H3 | both_down | 100 | COMPUTED: 100 | 23.000 | 0.000 |
| 19 | broadening_proxy/H3 | mixed | 100 | COMPUTED: 100 | 17.500 | -0.000 |
| 19 | broadening_proxy/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 20 | defensive_sector/H1 | both_up | 100 | COMPUTED: 100 | 24.000 | 5.500 / 0.744 |
| 20 | defensive_sector/H1 | both_down | 100 | COMPUTED: 100 | 44.500 | 5.000 / 0.161 |
| 20 | defensive_sector/H1 | mixed | 100 | COMPUTED: 100 | 33.000 | 4.000 / -0.007 |
| 20 | defensive_sector/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 20 | defensive_sector/H2 | both_up | 100 | COMPUTED: 100 | 32.500 | 0.001 |
| 20 | defensive_sector/H2 | both_down | 100 | COMPUTED: 100 | 49.000 | -0.001 |
| 20 | defensive_sector/H2 | mixed | 100 | COMPUTED: 100 | 42.000 | -0.001 |
| 20 | defensive_sector/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 20 | defensive_sector/H3 | both_up | 100 | COMPUTED: 100 | 32.500 | 0.001 |
| 20 | defensive_sector/H3 | both_down | 100 | COMPUTED: 100 | 49.000 | -0.000 |
| 20 | defensive_sector/H3 | mixed | 100 | COMPUTED: 100 | 42.000 | 0.000 |
| 20 | defensive_sector/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 20 | broadening_proxy/H1 | both_up | 100 | COMPUTED: 100 | 20.000 | 5.000 / 0.745 |
| 20 | broadening_proxy/H1 | both_down | 100 | COMPUTED: 100 | 36.500 | 5.000 / 0.142 |
| 20 | broadening_proxy/H1 | mixed | 100 | COMPUTED: 100 | 26.000 | 4.000 / -0.016 |
| 20 | broadening_proxy/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 20 | broadening_proxy/H2 | both_up | 100 | COMPUTED: 100 | 26.000 | -0.002 |
| 20 | broadening_proxy/H2 | both_down | 100 | COMPUTED: 100 | 44.000 | -0.001 |
| 20 | broadening_proxy/H2 | mixed | 100 | COMPUTED: 100 | 35.000 | -0.002 |
| 20 | broadening_proxy/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 20 | broadening_proxy/H3 | both_up | 100 | COMPUTED: 100 | 26.000 | 0.000 |
| 20 | broadening_proxy/H3 | both_down | 100 | COMPUTED: 100 | 44.000 | 0.001 |
| 20 | broadening_proxy/H3 | mixed | 100 | COMPUTED: 100 | 35.000 | 0.001 |
| 20 | broadening_proxy/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 100 | defensive_sector/H1 | both_up | 100 | COMPUTED: 67, SOURCE_LIMITED: 33 | 6.000 | 5.000 / 0.769 |
| 100 | defensive_sector/H1 | both_down | 100 | COMPUTED: 100 | 11.000 | 5.000 / 0.128 |
| 100 | defensive_sector/H1 | mixed | 100 | COMPUTED: 96, SOURCE_LIMITED: 4 | 9.000 | 5.000 / 0.029 |
| 100 | defensive_sector/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 100 | defensive_sector/H2 | both_up | 100 | COMPUTED: 97, SOURCE_LIMITED: 3 | 7.500 | -0.003 |
| 100 | defensive_sector/H2 | both_down | 100 | COMPUTED: 100 | 12.500 | -0.002 |
| 100 | defensive_sector/H2 | mixed | 100 | COMPUTED: 100 | 11.000 | -0.003 |
| 100 | defensive_sector/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 100 | defensive_sector/H3 | both_up | 100 | COMPUTED: 97, SOURCE_LIMITED: 3 | 7.500 | 0.001 |
| 100 | defensive_sector/H3 | both_down | 100 | COMPUTED: 100 | 12.500 | -0.000 |
| 100 | defensive_sector/H3 | mixed | 100 | COMPUTED: 100 | 11.000 | 0.001 |
| 100 | defensive_sector/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 100 | broadening_proxy/H1 | both_up | 100 | COMPUTED: 68, SOURCE_LIMITED: 32 | 5.000 | 5.000 / 0.750 |
| 100 | broadening_proxy/H1 | both_down | 100 | COMPUTED: 97, SOURCE_LIMITED: 3 | 9.000 | 5.000 / 0.164 |
| 100 | broadening_proxy/H1 | mixed | 100 | COMPUTED: 88, SOURCE_LIMITED: 12 | 7.000 | 5.000 / -0.032 |
| 100 | broadening_proxy/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 100 | broadening_proxy/H2 | both_up | 100 | COMPUTED: 91, SOURCE_LIMITED: 9 | 7.000 | -0.002 |
| 100 | broadening_proxy/H2 | both_down | 100 | COMPUTED: 100 | 11.000 | -0.003 |
| 100 | broadening_proxy/H2 | mixed | 100 | COMPUTED: 99, SOURCE_LIMITED: 1 | 9.000 | -0.005 |
| 100 | broadening_proxy/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 100 | broadening_proxy/H3 | both_up | 100 | COMPUTED: 91, SOURCE_LIMITED: 9 | 7.000 | 0.001 |
| 100 | broadening_proxy/H3 | both_down | 100 | COMPUTED: 100 | 11.000 | -0.001 |
| 100 | broadening_proxy/H3 | mixed | 100 | COMPUTED: 99, SOURCE_LIMITED: 1 | 9.000 | -0.000 |
| 100 | broadening_proxy/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 101 | defensive_sector/H1 | both_up | 100 | COMPUTED: 99, SOURCE_LIMITED: 1 | 11.000 | 6.000 / 0.742 |
| 101 | defensive_sector/H1 | both_down | 100 | COMPUTED: 100 | 21.000 | 5.000 / 0.151 |
| 101 | defensive_sector/H1 | mixed | 100 | COMPUTED: 100 | 17.000 | 4.000 / 0.028 |
| 101 | defensive_sector/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 101 | defensive_sector/H2 | both_up | 100 | COMPUTED: 100 | 15.000 | -0.002 |
| 101 | defensive_sector/H2 | both_down | 100 | COMPUTED: 100 | 25.000 | -0.001 |
| 101 | defensive_sector/H2 | mixed | 100 | COMPUTED: 100 | 21.000 | -0.003 |
| 101 | defensive_sector/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 101 | defensive_sector/H3 | both_up | 100 | COMPUTED: 100 | 15.000 | -0.000 |
| 101 | defensive_sector/H3 | both_down | 100 | COMPUTED: 100 | 25.000 | -0.000 |
| 101 | defensive_sector/H3 | mixed | 100 | COMPUTED: 100 | 21.000 | 0.001 |
| 101 | defensive_sector/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 101 | broadening_proxy/H1 | both_up | 100 | COMPUTED: 97, SOURCE_LIMITED: 3 | 10.000 | 6.000 / 0.758 |
| 101 | broadening_proxy/H1 | both_down | 100 | COMPUTED: 100 | 19.000 | 5.000 / 0.135 |
| 101 | broadening_proxy/H1 | mixed | 100 | COMPUTED: 100 | 13.000 | 4.000 / 0.010 |
| 101 | broadening_proxy/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 101 | broadening_proxy/H2 | both_up | 100 | COMPUTED: 100 | 13.000 | -0.001 |
| 101 | broadening_proxy/H2 | both_down | 100 | COMPUTED: 100 | 22.000 | -0.003 |
| 101 | broadening_proxy/H2 | mixed | 100 | COMPUTED: 100 | 17.000 | -0.004 |
| 101 | broadening_proxy/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 101 | broadening_proxy/H3 | both_up | 100 | COMPUTED: 100 | 13.000 | 0.000 |
| 101 | broadening_proxy/H3 | both_down | 100 | COMPUTED: 100 | 22.000 | -0.001 |
| 101 | broadening_proxy/H3 | mixed | 100 | COMPUTED: 100 | 17.000 | 0.000 |
| 101 | broadening_proxy/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 102 | defensive_sector/H1 | both_up | 100 | COMPUTED: 100 | 24.000 | 6.000 / 0.742 |
| 102 | defensive_sector/H1 | both_down | 100 | COMPUTED: 100 | 44.000 | 5.000 / 0.144 |
| 102 | defensive_sector/H1 | mixed | 100 | COMPUTED: 100 | 31.000 | 4.000 / 0.023 |
| 102 | defensive_sector/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 102 | defensive_sector/H2 | both_up | 100 | COMPUTED: 100 | 31.000 | -0.000 |
| 102 | defensive_sector/H2 | both_down | 100 | COMPUTED: 100 | 50.000 | -0.000 |
| 102 | defensive_sector/H2 | mixed | 100 | COMPUTED: 100 | 42.000 | -0.001 |
| 102 | defensive_sector/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 102 | defensive_sector/H3 | both_up | 100 | COMPUTED: 100 | 31.000 | 0.000 |
| 102 | defensive_sector/H3 | both_down | 100 | COMPUTED: 100 | 50.000 | 0.000 |
| 102 | defensive_sector/H3 | mixed | 100 | COMPUTED: 100 | 42.000 | 0.000 |
| 102 | defensive_sector/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 102 | broadening_proxy/H1 | both_up | 100 | COMPUTED: 100 | 20.000 | 5.500 / 0.755 |
| 102 | broadening_proxy/H1 | both_down | 100 | COMPUTED: 100 | 37.000 | 5.000 / 0.172 |
| 102 | broadening_proxy/H1 | mixed | 100 | COMPUTED: 100 | 27.000 | 4.000 / -0.005 |
| 102 | broadening_proxy/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 102 | broadening_proxy/H2 | both_up | 100 | COMPUTED: 100 | 26.000 | -0.001 |
| 102 | broadening_proxy/H2 | both_down | 100 | COMPUTED: 100 | 45.000 | -0.001 |
| 102 | broadening_proxy/H2 | mixed | 100 | COMPUTED: 100 | 33.000 | -0.001 |
| 102 | broadening_proxy/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 102 | broadening_proxy/H3 | both_up | 100 | COMPUTED: 100 | 26.000 | -0.000 |
| 102 | broadening_proxy/H3 | both_down | 100 | COMPUTED: 100 | 45.000 | 0.000 |
| 102 | broadening_proxy/H3 | mixed | 100 | COMPUTED: 100 | 33.000 | -0.000 |
| 102 | broadening_proxy/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 103 | defensive_sector/H1 | both_up | 100 | COMPUTED: 83, SOURCE_LIMITED: 17 | 6.500 | 5.000 / 0.697 |
| 103 | defensive_sector/H1 | both_down | 100 | COMPUTED: 99, SOURCE_LIMITED: 1 | 10.000 | 5.000 / 0.103 |
| 103 | defensive_sector/H1 | mixed | 100 | COMPUTED: 93, SOURCE_LIMITED: 7 | 8.500 | 4.000 / -0.122 |
| 103 | defensive_sector/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 103 | defensive_sector/H2 | both_up | 100 | COMPUTED: 95, SOURCE_LIMITED: 5 | 8.000 | -0.001 |
| 103 | defensive_sector/H2 | both_down | 100 | COMPUTED: 100 | 13.000 | -0.002 |
| 103 | defensive_sector/H2 | mixed | 100 | COMPUTED: 99, SOURCE_LIMITED: 1 | 11.000 | -0.002 |
| 103 | defensive_sector/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 103 | defensive_sector/H3 | both_up | 100 | COMPUTED: 95, SOURCE_LIMITED: 5 | 8.000 | 0.002 |
| 103 | defensive_sector/H3 | both_down | 100 | COMPUTED: 100 | 13.000 | -0.001 |
| 103 | defensive_sector/H3 | mixed | 100 | COMPUTED: 99, SOURCE_LIMITED: 1 | 11.000 | 0.001 |
| 103 | defensive_sector/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 103 | broadening_proxy/H1 | both_up | 100 | COMPUTED: 62, SOURCE_LIMITED: 38 | 5.000 | 5.000 / 0.704 |
| 103 | broadening_proxy/H1 | both_down | 100 | COMPUTED: 100 | 9.000 | 5.000 / 0.120 |
| 103 | broadening_proxy/H1 | mixed | 100 | COMPUTED: 88, SOURCE_LIMITED: 12 | 7.000 | 4.000 / -0.134 |
| 103 | broadening_proxy/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 103 | broadening_proxy/H2 | both_up | 100 | COMPUTED: 87, SOURCE_LIMITED: 13 | 7.000 | -0.002 |
| 103 | broadening_proxy/H2 | both_down | 100 | COMPUTED: 99, SOURCE_LIMITED: 1 | 11.000 | -0.003 |
| 103 | broadening_proxy/H2 | mixed | 100 | COMPUTED: 97, SOURCE_LIMITED: 3 | 9.000 | -0.003 |
| 103 | broadening_proxy/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 103 | broadening_proxy/H3 | both_up | 100 | COMPUTED: 87, SOURCE_LIMITED: 13 | 7.000 | 0.000 |
| 103 | broadening_proxy/H3 | both_down | 100 | COMPUTED: 99, SOURCE_LIMITED: 1 | 11.000 | 0.001 |
| 103 | broadening_proxy/H3 | mixed | 100 | COMPUTED: 97, SOURCE_LIMITED: 3 | 9.000 | -0.001 |
| 103 | broadening_proxy/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 104 | defensive_sector/H1 | both_up | 100 | COMPUTED: 100 | 13.000 | 5.000 / 0.699 |
| 104 | defensive_sector/H1 | both_down | 100 | COMPUTED: 100 | 21.500 | 5.000 / 0.112 |
| 104 | defensive_sector/H1 | mixed | 100 | COMPUTED: 100 | 16.000 | 4.000 / -0.147 |
| 104 | defensive_sector/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 104 | defensive_sector/H2 | both_up | 100 | COMPUTED: 100 | 16.000 | -0.001 |
| 104 | defensive_sector/H2 | both_down | 100 | COMPUTED: 100 | 25.000 | -0.002 |
| 104 | defensive_sector/H2 | mixed | 100 | COMPUTED: 100 | 22.000 | -0.001 |
| 104 | defensive_sector/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 104 | defensive_sector/H3 | both_up | 100 | COMPUTED: 100 | 16.000 | 0.001 |
| 104 | defensive_sector/H3 | both_down | 100 | COMPUTED: 100 | 25.000 | -0.001 |
| 104 | defensive_sector/H3 | mixed | 100 | COMPUTED: 100 | 22.000 | -0.001 |
| 104 | defensive_sector/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 104 | broadening_proxy/H1 | both_up | 100 | COMPUTED: 98, SOURCE_LIMITED: 2 | 11.000 | 5.000 / 0.703 |
| 104 | broadening_proxy/H1 | both_down | 100 | COMPUTED: 100 | 18.000 | 5.000 / 0.111 |
| 104 | broadening_proxy/H1 | mixed | 100 | COMPUTED: 100 | 14.000 | 4.000 / -0.127 |
| 104 | broadening_proxy/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 104 | broadening_proxy/H2 | both_up | 100 | COMPUTED: 100 | 14.000 | -0.001 |
| 104 | broadening_proxy/H2 | both_down | 100 | COMPUTED: 100 | 22.000 | -0.002 |
| 104 | broadening_proxy/H2 | mixed | 100 | COMPUTED: 100 | 17.000 | -0.002 |
| 104 | broadening_proxy/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 104 | broadening_proxy/H3 | both_up | 100 | COMPUTED: 100 | 14.000 | 0.002 |
| 104 | broadening_proxy/H3 | both_down | 100 | COMPUTED: 100 | 22.000 | -0.001 |
| 104 | broadening_proxy/H3 | mixed | 100 | COMPUTED: 100 | 17.000 | -0.000 |
| 104 | broadening_proxy/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 105 | defensive_sector/H1 | both_up | 100 | COMPUTED: 100 | 26.000 | 5.000 / 0.702 |
| 105 | defensive_sector/H1 | both_down | 100 | COMPUTED: 100 | 44.000 | 5.000 / 0.096 |
| 105 | defensive_sector/H1 | mixed | 100 | COMPUTED: 100 | 34.000 | 4.000 / -0.136 |
| 105 | defensive_sector/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 105 | defensive_sector/H2 | both_up | 100 | COMPUTED: 100 | 34.000 | 0.000 |
| 105 | defensive_sector/H2 | both_down | 100 | COMPUTED: 100 | 49.000 | -0.000 |
| 105 | defensive_sector/H2 | mixed | 100 | COMPUTED: 100 | 43.000 | -0.002 |
| 105 | defensive_sector/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 105 | defensive_sector/H3 | both_up | 100 | COMPUTED: 100 | 34.000 | 0.002 |
| 105 | defensive_sector/H3 | both_down | 100 | COMPUTED: 100 | 49.000 | -0.001 |
| 105 | defensive_sector/H3 | mixed | 100 | COMPUTED: 100 | 43.000 | -0.001 |
| 105 | defensive_sector/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 105 | broadening_proxy/H1 | both_up | 100 | COMPUTED: 100 | 22.000 | 5.000 / 0.696 |
| 105 | broadening_proxy/H1 | both_down | 100 | COMPUTED: 100 | 35.500 | 5.000 / 0.101 |
| 105 | broadening_proxy/H1 | mixed | 100 | COMPUTED: 100 | 27.000 | 4.000 / -0.116 |
| 105 | broadening_proxy/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 105 | broadening_proxy/H2 | both_up | 100 | COMPUTED: 100 | 27.000 | 0.000 |
| 105 | broadening_proxy/H2 | both_down | 100 | COMPUTED: 100 | 43.000 | -0.001 |
| 105 | broadening_proxy/H2 | mixed | 100 | COMPUTED: 100 | 35.000 | -0.001 |
| 105 | broadening_proxy/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 105 | broadening_proxy/H3 | both_up | 100 | COMPUTED: 100 | 27.000 | 0.002 |
| 105 | broadening_proxy/H3 | both_down | 100 | COMPUTED: 100 | 43.000 | -0.000 |
| 105 | broadening_proxy/H3 | mixed | 100 | COMPUTED: 100 | 35.000 | -0.001 |
| 105 | broadening_proxy/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 106 | defensive_sector/H1 | both_up | 100 | COMPUTED: 87, SOURCE_LIMITED: 13 | 7.000 | 5.000 / 0.658 |
| 106 | defensive_sector/H1 | both_down | 100 | COMPUTED: 100 | 11.000 | 5.000 / 0.099 |
| 106 | defensive_sector/H1 | mixed | 100 | COMPUTED: 97, SOURCE_LIMITED: 3 | 9.000 | 4.000 / -0.128 |
| 106 | defensive_sector/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 106 | defensive_sector/H2 | both_up | 100 | COMPUTED: 98, SOURCE_LIMITED: 2 | 9.000 | 0.004 |
| 106 | defensive_sector/H2 | both_down | 100 | COMPUTED: 100 | 12.000 | -0.003 |
| 106 | defensive_sector/H2 | mixed | 100 | COMPUTED: 100 | 11.000 | -0.004 |
| 106 | defensive_sector/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 106 | defensive_sector/H3 | both_up | 100 | COMPUTED: 98, SOURCE_LIMITED: 2 | 9.000 | 0.005 |
| 106 | defensive_sector/H3 | both_down | 100 | COMPUTED: 100 | 12.000 | 0.001 |
| 106 | defensive_sector/H3 | mixed | 100 | COMPUTED: 100 | 11.000 | -0.003 |
| 106 | defensive_sector/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 106 | broadening_proxy/H1 | both_up | 100 | COMPUTED: 79, SOURCE_LIMITED: 21 | 6.000 | 5.000 / 0.658 |
| 106 | broadening_proxy/H1 | both_down | 100 | COMPUTED: 99, SOURCE_LIMITED: 1 | 9.000 | 5.000 / 0.135 |
| 106 | broadening_proxy/H1 | mixed | 100 | COMPUTED: 93, SOURCE_LIMITED: 7 | 7.000 | 5.000 / -0.143 |
| 106 | broadening_proxy/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 106 | broadening_proxy/H2 | both_up | 100 | COMPUTED: 89, SOURCE_LIMITED: 11 | 7.000 | 0.002 |
| 106 | broadening_proxy/H2 | both_down | 100 | COMPUTED: 98, SOURCE_LIMITED: 2 | 11.000 | -0.001 |
| 106 | broadening_proxy/H2 | mixed | 100 | COMPUTED: 99, SOURCE_LIMITED: 1 | 9.000 | -0.005 |
| 106 | broadening_proxy/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 106 | broadening_proxy/H3 | both_up | 100 | COMPUTED: 89, SOURCE_LIMITED: 11 | 7.000 | 0.004 |
| 106 | broadening_proxy/H3 | both_down | 100 | COMPUTED: 98, SOURCE_LIMITED: 2 | 11.000 | 0.000 |
| 106 | broadening_proxy/H3 | mixed | 100 | COMPUTED: 99, SOURCE_LIMITED: 1 | 9.000 | -0.004 |
| 106 | broadening_proxy/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 107 | defensive_sector/H1 | both_up | 100 | COMPUTED: 100 | 14.000 | 5.500 / 0.645 |
| 107 | defensive_sector/H1 | both_down | 100 | COMPUTED: 100 | 20.000 | 5.000 / 0.118 |
| 107 | defensive_sector/H1 | mixed | 100 | COMPUTED: 100 | 18.000 | 4.000 / -0.168 |
| 107 | defensive_sector/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 107 | defensive_sector/H2 | both_up | 100 | COMPUTED: 100 | 18.000 | 0.005 |
| 107 | defensive_sector/H2 | both_down | 100 | COMPUTED: 100 | 23.000 | -0.002 |
| 107 | defensive_sector/H2 | mixed | 100 | COMPUTED: 100 | 22.000 | -0.002 |
| 107 | defensive_sector/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 107 | defensive_sector/H3 | both_up | 100 | COMPUTED: 100 | 18.000 | 0.004 |
| 107 | defensive_sector/H3 | both_down | 100 | COMPUTED: 100 | 23.000 | -0.002 |
| 107 | defensive_sector/H3 | mixed | 100 | COMPUTED: 100 | 22.000 | -0.002 |
| 107 | defensive_sector/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 107 | broadening_proxy/H1 | both_up | 100 | COMPUTED: 99, SOURCE_LIMITED: 1 | 12.000 | 5.000 / 0.656 |
| 107 | broadening_proxy/H1 | both_down | 100 | COMPUTED: 100 | 19.000 | 5.000 / 0.126 |
| 107 | broadening_proxy/H1 | mixed | 100 | COMPUTED: 100 | 14.000 | 4.000 / -0.103 |
| 107 | broadening_proxy/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 107 | broadening_proxy/H2 | both_up | 100 | COMPUTED: 100 | 14.000 | 0.003 |
| 107 | broadening_proxy/H2 | both_down | 100 | COMPUTED: 100 | 21.000 | 0.000 |
| 107 | broadening_proxy/H2 | mixed | 100 | COMPUTED: 100 | 18.000 | -0.003 |
| 107 | broadening_proxy/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 107 | broadening_proxy/H3 | both_up | 100 | COMPUTED: 100 | 14.000 | 0.004 |
| 107 | broadening_proxy/H3 | both_down | 100 | COMPUTED: 100 | 21.000 | 0.000 |
| 107 | broadening_proxy/H3 | mixed | 100 | COMPUTED: 100 | 18.000 | -0.003 |
| 107 | broadening_proxy/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 108 | defensive_sector/H1 | both_up | 100 | COMPUTED: 100 | 29.000 | 5.000 / 0.644 |
| 108 | defensive_sector/H1 | both_down | 100 | COMPUTED: 100 | 42.000 | 5.000 / 0.112 |
| 108 | defensive_sector/H1 | mixed | 100 | COMPUTED: 100 | 35.000 | 4.000 / -0.177 |
| 108 | defensive_sector/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 108 | defensive_sector/H2 | both_up | 100 | COMPUTED: 100 | 35.000 | 0.006 |
| 108 | defensive_sector/H2 | both_down | 100 | COMPUTED: 100 | 46.000 | -0.000 |
| 108 | defensive_sector/H2 | mixed | 100 | COMPUTED: 100 | 43.000 | -0.001 |
| 108 | defensive_sector/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 108 | defensive_sector/H3 | both_up | 100 | COMPUTED: 100 | 35.000 | 0.005 |
| 108 | defensive_sector/H3 | both_down | 100 | COMPUTED: 100 | 46.000 | -0.001 |
| 108 | defensive_sector/H3 | mixed | 100 | COMPUTED: 100 | 43.000 | -0.002 |
| 108 | defensive_sector/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 108 | broadening_proxy/H1 | both_up | 100 | COMPUTED: 100 | 23.500 | 6.000 / 0.649 |
| 108 | broadening_proxy/H1 | both_down | 100 | COMPUTED: 100 | 35.000 | 5.000 / 0.112 |
| 108 | broadening_proxy/H1 | mixed | 100 | COMPUTED: 100 | 29.000 | 4.000 / -0.095 |
| 108 | broadening_proxy/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 108 | broadening_proxy/H2 | both_up | 100 | COMPUTED: 100 | 29.000 | 0.006 |
| 108 | broadening_proxy/H2 | both_down | 100 | COMPUTED: 100 | 41.000 | -0.000 |
| 108 | broadening_proxy/H2 | mixed | 100 | COMPUTED: 100 | 35.500 | -0.003 |
| 108 | broadening_proxy/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 108 | broadening_proxy/H3 | both_up | 100 | COMPUTED: 100 | 29.000 | 0.006 |
| 108 | broadening_proxy/H3 | both_down | 100 | COMPUTED: 100 | 41.000 | -0.001 |
| 108 | broadening_proxy/H3 | mixed | 100 | COMPUTED: 100 | 35.500 | -0.003 |
| 108 | broadening_proxy/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 109 | defensive_sector/H1 | both_up | 100 | COMPUTED: 87, SOURCE_LIMITED: 13 | 8.000 | 5.000 / 0.685 |
| 109 | defensive_sector/H1 | both_down | 100 | COMPUTED: 98, SOURCE_LIMITED: 2 | 9.000 | 5.000 / 0.177 |
| 109 | defensive_sector/H1 | mixed | 100 | COMPUTED: 95, SOURCE_LIMITED: 5 | 8.000 | 4.000 / 0.104 |
| 109 | defensive_sector/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 109 | defensive_sector/H2 | both_up | 100 | COMPUTED: 94, SOURCE_LIMITED: 6 | 9.000 | 0.011 |
| 109 | defensive_sector/H2 | both_down | 100 | COMPUTED: 100 | 12.000 | -0.003 |
| 109 | defensive_sector/H2 | mixed | 100 | COMPUTED: 100 | 11.000 | -0.014 |
| 109 | defensive_sector/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 109 | defensive_sector/H3 | both_up | 100 | COMPUTED: 94, SOURCE_LIMITED: 6 | 9.000 | 0.012 |
| 109 | defensive_sector/H3 | both_down | 100 | COMPUTED: 100 | 12.000 | -0.007 |
| 109 | defensive_sector/H3 | mixed | 100 | COMPUTED: 100 | 11.000 | -0.011 |
| 109 | defensive_sector/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 109 | broadening_proxy/H1 | both_up | 100 | COMPUTED: 78, SOURCE_LIMITED: 22 | 6.000 | 5.000 / 0.692 |
| 109 | broadening_proxy/H1 | both_down | 100 | COMPUTED: 99, SOURCE_LIMITED: 1 | 8.000 | 5.000 / 0.208 |
| 109 | broadening_proxy/H1 | mixed | 100 | COMPUTED: 95, SOURCE_LIMITED: 5 | 8.000 | 5.000 / 0.125 |
| 109 | broadening_proxy/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 109 | broadening_proxy/H2 | both_up | 100 | COMPUTED: 95, SOURCE_LIMITED: 5 | 7.500 | 0.011 |
| 109 | broadening_proxy/H2 | both_down | 100 | COMPUTED: 99, SOURCE_LIMITED: 1 | 10.000 | -0.002 |
| 109 | broadening_proxy/H2 | mixed | 100 | COMPUTED: 98, SOURCE_LIMITED: 2 | 9.000 | -0.014 |
| 109 | broadening_proxy/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 109 | broadening_proxy/H3 | both_up | 100 | COMPUTED: 95, SOURCE_LIMITED: 5 | 7.500 | 0.011 |
| 109 | broadening_proxy/H3 | both_down | 100 | COMPUTED: 99, SOURCE_LIMITED: 1 | 10.000 | -0.003 |
| 109 | broadening_proxy/H3 | mixed | 100 | COMPUTED: 98, SOURCE_LIMITED: 2 | 9.000 | -0.014 |
| 109 | broadening_proxy/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 110 | defensive_sector/H1 | both_up | 100 | COMPUTED: 100 | 14.000 | 6.000 / 0.686 |
| 110 | defensive_sector/H1 | both_down | 100 | COMPUTED: 100 | 20.000 | 5.000 / 0.196 |
| 110 | defensive_sector/H1 | mixed | 100 | COMPUTED: 100 | 17.000 | 4.000 / 0.116 |
| 110 | defensive_sector/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 110 | defensive_sector/H2 | both_up | 100 | COMPUTED: 100 | 18.000 | 0.012 |
| 110 | defensive_sector/H2 | both_down | 100 | COMPUTED: 100 | 24.000 | 0.000 |
| 110 | defensive_sector/H2 | mixed | 100 | COMPUTED: 100 | 21.000 | -0.013 |
| 110 | defensive_sector/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 110 | defensive_sector/H3 | both_up | 100 | COMPUTED: 100 | 18.000 | 0.012 |
| 110 | defensive_sector/H3 | both_down | 100 | COMPUTED: 100 | 24.000 | -0.003 |
| 110 | defensive_sector/H3 | mixed | 100 | COMPUTED: 100 | 21.000 | -0.015 |
| 110 | defensive_sector/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 110 | broadening_proxy/H1 | both_up | 100 | COMPUTED: 99, SOURCE_LIMITED: 1 | 13.000 | 5.000 / 0.692 |
| 110 | broadening_proxy/H1 | both_down | 100 | COMPUTED: 100 | 17.000 | 5.000 / 0.210 |
| 110 | broadening_proxy/H1 | mixed | 100 | COMPUTED: 100 | 15.000 | 4.000 / 0.114 |
| 110 | broadening_proxy/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 110 | broadening_proxy/H2 | both_up | 100 | COMPUTED: 100 | 15.000 | 0.014 |
| 110 | broadening_proxy/H2 | both_down | 100 | COMPUTED: 100 | 21.000 | -0.003 |
| 110 | broadening_proxy/H2 | mixed | 100 | COMPUTED: 100 | 18.000 | -0.011 |
| 110 | broadening_proxy/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 110 | broadening_proxy/H3 | both_up | 100 | COMPUTED: 100 | 15.000 | 0.011 |
| 110 | broadening_proxy/H3 | both_down | 100 | COMPUTED: 100 | 21.000 | -0.003 |
| 110 | broadening_proxy/H3 | mixed | 100 | COMPUTED: 100 | 18.000 | -0.016 |
| 110 | broadening_proxy/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 111 | defensive_sector/H1 | both_up | 100 | COMPUTED: 100 | 29.000 | 6.000 / 0.683 |
| 111 | defensive_sector/H1 | both_down | 100 | COMPUTED: 100 | 39.000 | 5.000 / 0.199 |
| 111 | defensive_sector/H1 | mixed | 100 | COMPUTED: 100 | 36.000 | 4.000 / 0.091 |
| 111 | defensive_sector/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 111 | defensive_sector/H2 | both_up | 100 | COMPUTED: 100 | 36.000 | 0.014 |
| 111 | defensive_sector/H2 | both_down | 100 | COMPUTED: 100 | 45.000 | 0.000 |
| 111 | defensive_sector/H2 | mixed | 100 | COMPUTED: 100 | 43.000 | -0.010 |
| 111 | defensive_sector/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 111 | defensive_sector/H3 | both_up | 100 | COMPUTED: 100 | 36.000 | 0.012 |
| 111 | defensive_sector/H3 | both_down | 100 | COMPUTED: 100 | 45.000 | -0.006 |
| 111 | defensive_sector/H3 | mixed | 100 | COMPUTED: 100 | 43.000 | -0.013 |
| 111 | defensive_sector/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 111 | broadening_proxy/H1 | both_up | 100 | COMPUTED: 100 | 26.000 | 6.000 / 0.694 |
| 111 | broadening_proxy/H1 | both_down | 100 | COMPUTED: 100 | 33.500 | 5.000 / 0.197 |
| 111 | broadening_proxy/H1 | mixed | 100 | COMPUTED: 100 | 29.000 | 4.000 / 0.105 |
| 111 | broadening_proxy/H1 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — / — |
| 111 | broadening_proxy/H2 | both_up | 100 | COMPUTED: 100 | 31.000 | 0.015 |
| 111 | broadening_proxy/H2 | both_down | 100 | COMPUTED: 100 | 41.000 | -0.000 |
| 111 | broadening_proxy/H2 | mixed | 100 | COMPUTED: 100 | 37.000 | -0.011 |
| 111 | broadening_proxy/H2 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |
| 111 | broadening_proxy/H3 | both_up | 100 | COMPUTED: 100 | 31.000 | 0.010 |
| 111 | broadening_proxy/H3 | both_down | 100 | COMPUTED: 100 | 41.000 | -0.005 |
| 111 | broadening_proxy/H3 | mixed | 100 | COMPUTED: 100 | 37.000 | -0.015 |
| 111 | broadening_proxy/H3 | unmeasured | 100 | UNMEASURED: 100 | 0.000 | — |

## Interpretation notes (T13R)

1. **How to read the power tables.** Table 2 gives pass counts per cell × row. Table 2b gives the same counts with a Wilson 95 % interval per row, followed by the V2 §4.3 disposition lines. M = 100 per (δ, cell): 4 processes × 25 sims at k ∈ [0, 100), pooled exactly as launched. The eligible slots are G2 cells 100, 101, 103, 104, 106 and 107 (δ ≤ 4.0 %, N ≤ 40). Every one is measured (M = 100 ≥ `min_m` = 100) for both groups, so the disposition is `NOT_EXECUTABLE` and not `NOT_EVALUATED`. **Units:** G1 "pts" and G2 "%" are the same scale, 0.01 in log-return units, and σ = 0.007 in both. Two display quirks, which are rounding only (the records hold exact values): the Table 2/2b header says "δ (pts)" for G2 rows as well, and Table 5 prints δ to three decimals (0.003 for 0.0025). **Replication check:** cell 100 has G1 cell 18's parameters with independent seeds. Both are 0/100 in every row, and their mean H2 points (−0.180 and −0.149 pts, note 2) agree within noise.
2. **The drift reaches the statistics; the margins and the p-value are what bind.** The table below is a diagnostic, not a registered output. It is computed from the same 2,100 records, with both groups pooled (n = 200 per cell), and is descriptive only.

   | cell | gen | δ /20 sessions | N | (sim, group) n | mean H2 point (pts) | sd | median H2 raw p | mean H3 point (pts) | median H3 raw p | mean A1 detection | mean A1 median delay (sessions) |
   |---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
   | 6 | G1 | 0.25 pts | 20 | 200 | -0.176 | 0.497 | 0.714 | +0.010 | 0.498 | 0.936 | 17.6 |
   | 7 | G1 | 0.25 pts | 40 | 200 | -0.098 | 0.380 | 0.677 | +0.035 | 0.470 | 0.941 | 17.6 |
   | 8 | G1 | 0.25 pts | 80 | 200 | -0.110 | 0.279 | 0.701 | -0.015 | 0.524 | 0.940 | 17.7 |
   | 12 | G1 | 0.50 pts | 20 | 200 | -0.186 | 0.539 | 0.663 | +0.029 | 0.469 | 0.937 | 17.5 |
   | 13 | G1 | 0.50 pts | 40 | 200 | -0.101 | 0.378 | 0.653 | -0.016 | 0.520 | 0.940 | 17.6 |
   | 14 | G1 | 0.50 pts | 80 | 200 | -0.087 | 0.279 | 0.665 | -0.031 | 0.532 | 0.938 | 17.6 |
   | 18 | G1 | 1.00 pts | 20 | 200 | -0.149 | 0.503 | 0.679 | -0.026 | 0.496 | 0.939 | 17.3 |
   | 19 | G1 | 1.00 pts | 40 | 200 | -0.098 | 0.410 | 0.667 | +0.011 | 0.467 | 0.941 | 17.5 |
   | 20 | G1 | 1.00 pts | 80 | 200 | -0.037 | 0.268 | 0.596 | +0.034 | 0.425 | 0.941 | 17.6 |
   | 100 | G2 | 1.00 % | 20 | 200 | -0.180 | 0.546 | 0.671 | +0.070 | 0.475 | 0.939 | 17.4 |
   | 101 | G2 | 1.00 % | 40 | 200 | -0.111 | 0.360 | 0.665 | +0.003 | 0.494 | 0.939 | 17.5 |
   | 102 | G2 | 1.00 % | 80 | 200 | -0.024 | 0.277 | 0.582 | +0.040 | 0.444 | 0.940 | 17.6 |
   | 103 | G2 | 2.00 % | 20 | 200 | -0.078 | 0.577 | 0.604 | +0.001 | 0.482 | 0.938 | 17.2 |
   | 104 | G2 | 2.00 % | 40 | 200 | -0.040 | 0.379 | 0.599 | +0.018 | 0.484 | 0.946 | 17.5 |
   | 105 | G2 | 2.00 % | 80 | 200 | -0.002 | 0.268 | 0.563 | +0.015 | 0.496 | 0.947 | 17.4 |
   | 106 | G2 | 4.00 % | 20 | 200 | +0.074 | 0.620 | 0.518 | +0.054 | 0.475 | 0.954 | 17.0 |
   | 107 | G2 | 4.00 % | 40 | 200 | +0.142 | 0.400 | 0.438 | +0.029 | 0.474 | 0.954 | 17.2 |
   | 108 | G2 | 4.00 % | 80 | 200 | +0.202 | 0.295 | 0.321 | +0.011 | 0.482 | 0.953 | 17.3 |
   | 109 | G2 | 8.00 % | 20 | 200 | +0.061 | 0.777 | 0.559 | -0.337 | 0.646 | 0.954 | 16.4 |
   | 110 | G2 | 8.00 % | 40 | 200 | +0.046 | 0.526 | 0.501 | -0.357 | 0.708 | 0.961 | 16.5 |
   | 111 | G2 | 8.00 % | 80 | 200 | +0.119 | 0.396 | 0.419 | -0.410 | 0.826 | 0.960 | 16.5 |

   As δ grows, A1 detection rises (about 0.94 → 0.96) and A1's median confirmation delay falls (about 17.5 → 16.5 sessions). At fixed N, the mean H2 point rises from about −0.1 pts at δ ≤ 1 to +0.14 / +0.20 pts at δ = 4 % (N 40 / 80) and grows no further at δ = 8 % (+0.05 / +0.12). The G2 generator is therefore not inert. The registered H2 statistic responds to a planted rotation, but even at its best the mean point is about 40 % of the +0.50 margin. The H2 p-value half also fails: median raw p is ≥ 0.32 before Holm. H3's mean point stays near zero through δ = 4 % and turns **negative** at δ = 8 % (−0.34 to −0.41 pts; median raw p 0.65–0.83), so H3 does not detect the planted rotation in its registered direction. This diagnostic explains the `NOT_EXECUTABLE` dispositions. It does not change them, and it was not used to choose anything.
3. **H1 (for information) cannot pass by construction.** This holds for the same reason given in T12R note 3. T_a is the A2 median confirmation delay minus the A1 median delay, which equals `iut.delay_reduction`. Under V1 ruling R5, A2 ≡ A1 + 5 sessions, so T_a ≈ 5 on observed and null paths alike. The Option A null's T_a 0.975-quantile is 5.0 in all 4,200 (sim, group) evaluations, so p_a is never below α, at any δ. H1's zero power is structural, not a sample-size effect. It is reported, not repaired, because arms A0–B7/C3 are frozen. Measured p_a by observed T_a:

   | cell | (cell, group) rows | observed T_a (value: count) | null T_a q975 (value: count) | median p_a | H1 PASS (margin AND p_H1 < α) | of which T_a ≥ 6 |
   |---|---|---|---|---|---|---|
   | 6 | 200 | 0.0: 1, 2.0: 2, 3.0: 6, 4.0: 39, 5.0: 147, 6.0: 5 | 5.0: 200 | 0.714 | 0 | 0 |
   | 7 | 200 | 3.0: 3, 4.0: 60, 5.0: 135, 6.0: 1, 7.0: 1 | 5.0: 200 | 0.718 | 0 | 0 |
   | 8 | 200 | 3.0: 2, 4.0: 53, 5.0: 145 | 5.0: 200 | 0.695 | 0 | 0 |
   | 12 | 200 | 1.0: 1, 3.0: 6, 4.0: 38, 5.0: 151, 6.0: 4 | 5.0: 200 | 0.714 | 0 | 0 |
   | 13 | 200 | 3.0: 3, 4.0: 52, 5.0: 145 | 5.0: 200 | 0.718 | 0 | 0 |
   | 14 | 200 | 4.0: 58, 5.0: 142 | 5.0: 200 | 0.695 | 0 | 0 |
   | 18 | 200 | 3.0: 7, 4.0: 50, 5.0: 140, 6.0: 3 | 5.0: 200 | 0.714 | 0 | 0 |
   | 19 | 200 | 3.0: 3, 4.0: 53, 5.0: 142, 6.0: 2 | 5.0: 200 | 0.718 | 0 | 0 |
   | 20 | 200 | 3.0: 1, 4.0: 71, 5.0: 128 | 5.0: 200 | 0.695 | 0 | 0 |
   | 100 | 200 | 2.0: 1, 3.0: 7, 4.0: 47, 5.0: 138, 6.0: 7 | 5.0: 200 | 0.714 | 0 | 0 |
   | 101 | 200 | 3.0: 2, 4.0: 65, 5.0: 132, 6.0: 1 | 5.0: 200 | 0.718 | 0 | 0 |
   | 102 | 200 | 4.0: 62, 5.0: 138 | 5.0: 200 | 0.695 | 0 | 0 |
   | 103 | 200 | 3.0: 9, 4.0: 42, 5.0: 145, 6.0: 3, 8.0: 1 | 5.0: 200 | 0.714 | 0 | 0 |
   | 104 | 200 | 2.0: 1, 3.0: 1, 4.0: 65, 5.0: 132, 6.0: 1 | 5.0: 200 | 0.718 | 0 | 0 |
   | 105 | 200 | 3.0: 1, 4.0: 63, 5.0: 136 | 5.0: 200 | 0.695 | 0 | 0 |
   | 106 | 200 | 3.0: 4, 4.0: 48, 5.0: 145, 6.0: 3 | 5.0: 200 | 0.714 | 0 | 0 |
   | 107 | 200 | 3.0: 3, 4.0: 47, 5.0: 150 | 5.0: 200 | 0.718 | 0 | 0 |
   | 108 | 200 | 4.0: 60, 5.0: 140 | 5.0: 200 | 0.695 | 0 | 0 |
   | 109 | 200 | 2.0: 2, 3.0: 5, 4.0: 39, 5.0: 151, 6.0: 2, 7.0: 1 | 5.0: 200 | 0.717 | 0 | 0 |
   | 110 | 200 | 3.0: 2, 4.0: 36, 5.0: 162 | 5.0: 200 | 0.680 | 0 | 0 |
   | 111 | 200 | 4.0: 50, 5.0: 149, 6.0: 1 | 5.0: 200 | 0.677 | 0 | 0 |
   
   All cells: 4200 (sim, group) rows; H1 PASS in 0; of those, observed T_a ≥ 6 in 0.
4. **Table 3 is margin-only.** Its `cond_a` / `cond_b` columns count only whether each intersection–union component met its registered margin. The p-value half of each component is in the §8 item 10 aggregate and in note 3. `cond_a` met its margin in 3,028 of 4,200 evaluations (62–82 per 100 by row), and `cond_b` in 4,164 of 4,200. H1 still passed 0 times, because p_a never falls below α.
5. **Scope: G1 slice only.** The G1 power rows are the σ 0.70 pts, ρ 0.5 slice that matches G2 (cells 6, 7, 8, 12, 13, 14, 18, 19, 20). The rest of the 72-cell G1 catalog (σ 1.00 / 1.40 pts, ρ 0.8) was not re-run for power in this wave. This is disclosed scope, not a selection: those cells' δ = 0 size rows are in T12R wherever V2 §3 requires them.
6. **The null bank is shared within each group.** For a given (σ, ρ, N), H1's Option A null for every (sim, group) comes from one bank per group, seeded 20261014 + crc32("P0|<group>"). Power is therefore estimated conditional on that one bank draw, as in T12R note 7. Because the T_a quantile is exactly 5.0 in every bank, H1's zero is not an artifact of the bank.
7. **`NOT_EXECUTABLE` is a RESULT, not a reason to lower anything.** Per V2 §4.3, margins are the practical-significance bar and are not tuned to the generator, and α and the arms are unchanged. V2 triggers a V3 only through the V2 §2 size falsifier, which did not fire (T12R). The consequence for the program, stated plainly: at the registered margins, H1 is powerless by construction and H2/H3 are `NOT_EXECUTABLE` for P2/P3. Changing a statistic or an arm to restore power would be a new preregistration act for the program owner, not a harness repair. This record makes no such change.
8. **Process disclosure.** The power run was executed once, at a pre-set M = 100 with pre-set seeds, and pooled exactly as launched. Partial progress was looked at while the runs were in flight. That included a preview of the dispositions over the 20 completed cells before cell 111 (δ 8 %, N 80) finished, a cell that cannot affect the disposition because it is not eligible. Nothing was changed, re-run or selected as a result. Cell 111's first sims took about 200–260 s each because they built new null-bank shards for unseen N values. That cost is runtime only; the cache key covers the full payload, so it cannot change any value.
9. **What this record licenses.** It is §8 item 12 (the power curve and dispositions) for the repaired protocol, plus §8 items 10 and 13 at δ > 0. It is not a P1, P2 or P3 read. R-H1-4's size half is T12R's job. Nothing here is a promotion claim.

## Input identities

| file | sha256 | lines | cells | k | status | head | start (UTC) | end (UTC) | secs | rc |
|---|---|---:|---|---|---|---|---|---|---:|---:|
| `power_k0.jsonl` | `04d9e113998bcf5b9fc2e65ee007eb72e83c348fb6a822f0074da68c6e738a6f` | 525 | 6,7,8,12,13,14,18,19,20,100,101,102,103,104,105,106,107,108,109,110,111 | 0–24 | OK:525 | `b85c8979e8ef` | 2026-10-14T20:07:44Z | 2026-10-14T21:37:51Z | 5407 | 0 |
| `power_k25.jsonl` | `4eff19c761a0a82777ac4b24a721ea4740bf80c530c9283206711283e842483f` | 525 | 6,7,8,12,13,14,18,19,20,100,101,102,103,104,105,106,107,108,109,110,111 | 25–49 | OK:525 | `b85c8979e8ef` | 2026-10-14T20:08:44Z | 2026-10-14T21:30:12Z | 4888 | 0 |
| `power_k50.jsonl` | `030f39dd3a163bdee3caf96a446df1f65e92e0281dfd750fc8d60c7e00f629f6` | 525 | 6,7,8,12,13,14,18,19,20,100,101,102,103,104,105,106,107,108,109,110,111 | 50–74 | OK:525 | `b85c8979e8ef` | 2026-10-14T20:08:44Z | 2026-10-14T21:32:10Z | 5006 | 0 |
| `power_k75.jsonl` | `5d656a0de80cb859437268d502b64cec94144d987f28e963db9afa1118fb4e56` | 525 | 6,7,8,12,13,14,18,19,20,100,101,102,103,104,105,106,107,108,109,110,111 | 75–99 | OK:525 | `b85c8979e8ef` | 2026-10-14T20:09:44Z | 2026-10-14T21:37:12Z | 5248 | 0 |

harness_id values across records: `0461f9c294ce4749f3cc98e2799b0e9765f179583334022caa2d26d4640920d7` ×2100

- Code head for every record: `b85c8979e8efce1ec2e5200dc686361fd45614a2` (branch `claude/lr-harness-repair-2026-10-14`), the same head as T12R. `harness_id` (sha256 over the HARNESS_MODULES blobs) is identical in all 2,100 records and equals T12R's.
- Command per process (from the scratch `run_one.sh`): `python3 scripts/leadership_rotation_p0.py grid --cells 6,7,8,12,13,14,18,19,20,100,101,102,103,104,105,106,107,108,109,110,111 --sims-null 25 --sims-alt 25 --k-start <0|25|50|75> --workers 1 --null-k 1000 --out <file>`. Run under nohup on host m2studio (24 CPUs; python 3.14.7, numpy 2.5.2, pandas 3.0.5). Four processes ran in parallel, within the ≤ 4 cap.
- Power and disposition outputs: `python3 scripts/leadership_rotation_p0.py power --in <4 files> --min-m 100 --out power.json` (rule `V2_SEC4_POWERED_IN_PRINCIPLE`, threshold 0.50, max δ 0.04, max N 40, min M 100), and `python3 scripts/leadership_rotation_p0.py summary --in <4 files> --min-m 100 --json … --md …` for Tables 2–6. Both exited with rc = 0.
- Null bank: the same `LR_NULL_BANK_DIR` shard cache as T12R, shared under fcntl locks. Each shard is keyed by the sha256 of its full payload, including `code_fingerprint()` of the null module, so a reused shard is an identical computation under identical code.
- Test-path seeds: `SeedSequence([20261014, cell_id, k])` for k ∈ [0, 100). The cell id enters the seed, so cell 100 is independent of cell 18. Null seeds: 20261014 + crc32("P0|defensive_sector") = 20261014 + 1109301814, and 20261014 + crc32("P0|broadening_proxy") = 20261014 + 3923611080.
- Pooling: `power` and `summary` de-duplicate on (cell_id, k) and raise on a conflicting duplicate. 2,100 records were kept: 21 cells × 100, with 0 duplicates, 0 partial and 0 non-OK records.

## Look count

P1 looks: 0 (look ledger absent). P2 looks: 0. P3 looks: 0. P0 runs for this record: 4 processes (POWER0–POWER3), each covering cells 6, 7, 8, 12, 13, 14, 18, 19, 20 and 100–111 × 25 sims, with k ranges [0, 25), [25, 50), [50, 75) and [75, 100). All ran at head `b85c8979`, all exited with rc = 0, and their wall times were 5,407 s, 4,888 s, 5,006 s and 5,248 s (2026-10-14 20:07:44Z → 21:37:51Z). Each was launched once, with no reruns. Together with T12R's four SIZE runs, that is 8 P0 processes for the repaired protocol.

## Verdict

**H2 `NOT_EXECUTABLE` and H3 `NOT_EXECUTABLE` at the registered margins (P0, development harness); H1 `NOT_EXECUTABLE` for information.** Under V2 §4.3, no hypothesis reaches a pass rate ≥ 0.50 at δ ≤ 4.0 % in any G2 cell with N ≤ 40. Every eligible slot was measured at M = 100, and the curve stays at size level (≤ 2/100) all the way to δ = 8 %, N = 80. This is a RESULT, reported as V2 requires. No margin, α or arm was changed, and V2 triggers no V3 from power; the size falsifier, V2's only V3 trigger, did not fire (T12R). For the program owner: as registered, a P2 or P3 read cannot pass H2 or H3 except at roughly the size rate, and H1 cannot pass at all (note 3). Whether to proceed to P1/P2/P3 under these dispositions, or to re-register the statistics, is an owner decision outside this record. This record authorises no read.
