# Overlap check — reconstruction vs `data/breadth/sector_breadth.parquet`

Historical Reconstruction Protocol §4.6: where the recorded and the reconstructed
series overlap, compare once and write down the difference. No tuning was done
to make them agree.

- Run: 2026-11-12, engine `engine/group_breadth_history.py` at commit `09296e430719`.
- Inputs (origin/main `4869c78575b9`): `data/breadth/_closes_cache.parquet`
  (416 sessions, 2025-03-18..2026-11-10, 519 tickers) and
  `data/breadth/constituents.parquet` (503 current members, current GICS labels).
- Basis: `reconstructed_current_membership` (the same basis `compute_sectors` uses).

| Metric | Shared sessions | Sectors | Max abs difference (pct points) |
|---|---|---|---|
| `pct_above_50` | 367 | 11 | 0.0 |
| `pct_above_200` | 217 | 11 | 0.0 |

Every sector matches exactly on every shared session. This is expected: both use
`rolling(w, min_periods=w)` on the same closes and the same members. It confirms
the new code path reproduces the shipped series. It does **not** measure
survivorship error, because both sides use today's members.

## Second check — the published history (Tiingo closes) vs the same file

Shared span 2025-12-31..2026-10-09, 195 sessions, share above the 200-session
average. Mean absolute difference by sector 0.27 to 3.30 points on today's basis
and 0.27 to 4.87 on the dated basis; per-sector table and the causes in
`BUILD_REPORT.md` §Overlap check. The engine is the same; the difference is the
price store and, on the dated basis, membership changes. On the price store:
- 18 of today's members are absent from the Tiingo capture;
- the collector's own cache mixes dividend-adjusted vintages (#11124), so the
  collector's series is the one that is off.

The earlier wording, "small adjusted-price differences", was untested and is
corrected in `BUILD_REPORT.md` §Overlap check.
