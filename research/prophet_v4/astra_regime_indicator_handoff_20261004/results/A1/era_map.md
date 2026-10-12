# Era map — indicator / clock / rank-family commits

Command (this checkout): `git log --date=short --format='%h %ad %s' -- <file>`.

`git rev-parse --is-shallow-repository` → `true`. `git log --all -- engine/canon.py` dies with `error: Could not read 948bccfd511119f6f2eba8936b8ad46373462e3c`. Same blob-missing error on `git log origin/main -- engine/canon.py` beyond the shallow window. Path-filtered log and `git log -S` for `RSI_LEN`, `US_EPOCH`, `derive_3d_ohlcv`, `BOARD_DEFINITION`, `us_prophet_v3` each return **one** commit: the immune squash that **added** the current blobs.

That is a receipt, not a claim that constants never changed before 2026-08-23. Pre-squash history is not readable on this checkout.

## `engine/canon.py`

```
69268b06502c 2026-08-23 chore(immune): update ci_status + immune journals [skip ci]
```

`git log --follow` also shows `9bc2bb716ef6 2026-08-21 whitehouse: alert update 2026-08-21T11:00Z` then the immune add. `git blame -L 417,418 engine/canon.py` attributes `RSI_LEN, FAST_LEN, BASE_LEN, SIG_LEN = 14, 14, 60, 5` and `STOCH_LEN, SMOOTH_K, SMOOTH_D = 14, 3, 3` to `^69268b06502c`.

`git show --stat 69268b06502c -- engine/canon.py`: `engine/canon.py | 522 +++++++++` (file added, 522 lines). Subject is a CI/immune chore; the diff is the whole file. Constants in the added blob: `RSI_LEN=14, FAST_LEN=14, BASE_LEN=60, SIG_LEN=5, STOCH_LEN=14, SMOOTH_K=3, SMOOTH_D=3` (`engine/canon.py:417-418`). `resample_sessions` uses `np.arange(len(s)) // n` (`:391`) — ordinal phase, not the absolute session calendar.

No later commit on this checkout touches those constants.

## `engine/session_anchor.py`

```
69268b06502c 2026-08-23 chore(immune): update ci_status + immune journals [skip ci]
```

`git show --stat`: `engine/session_anchor.py | 202 ++++` (file added). Added blob: `US_EPOCH = date(1950, 1, 3)` (`:69`); `US_FORWARD_DAYS = 400` (`:73`); `bucket(d) = position(d) // n` with `position(d) = R.searchsorted(d, side="left")` (`:17`, `:164-191`). Era named in the module docstring: `abs-session-2026-08-06` (`:3`).

No later commit on this checkout touches the epoch or the bucketing rule.

## `engine/bar_derive.py`

```
69268b06502c 2026-08-23 chore(immune): update ci_status + immune journals [skip ci]
```

`git show --stat`: `engine/bar_derive.py | 398 +++++++` (file added). Added blob: `ANCHOR_ERA = "display-grid-abs-session-2026-08-06"` (`:62`); `_anchored_ohlcv` uses `session_anchor.session_positions(idx, market) // n` (`:268`); `derive_2d_ohlcv` / `derive_3d_ohlcv` (`:289-314`). Docstring records the retired rule: used to bucket with `resample("2B"/"3B")` (`:29-34`).

No later commit on this checkout touches the bucketing rule.

## `engine/mtf_upturn.py`

```
69268b06502c 2026-08-23 chore(immune): update ci_status + immune journals [skip ci]
```

`git show --stat`: `engine/mtf_upturn.py | 1348 +++++++++++++++++++++++` (file added). Added blob: `ANCHOR_ERA = "coiled-mtf-abs-session-2026-08-06"` (`:72`); amendment log `2026-08-06: trend.d3 buckets cut on the ABSOLUTE session calendar (session_anchor.session_positions // 3 ...)` (`:25-28`). 3D leg reuses `signal_quality.signal_frame` (`:45`).

No later commit on this checkout.

## `engine/us_board_rank.py`

```
69268b06502c 2026-08-23 chore(immune): update ci_status + immune journals [skip ci]
```

`git show --stat`: `engine/us_board_rank.py | 2667 ++++++++++++++++++++++++++++++++++++++++++++++` (file added). Added blob rank-family set:

| stamp | line | note in the added blob |
|---|---|---|
| `BOARD_DEFINITION = "us_prophet_v3"` | 100 | live ranker as of 2026-08-15 (`BOARD_DEFINITION_ADOPTED`, line 119) |
| `SHADOW_DEFINITION = "us_prophet_v2_shadow"` | 128 | retired scorer, zero authority |
| `FALLBACK_DEFINITION = "us_prophet_v2_fallback"` | 136 | degradation stamp |
| `SUPERSEDED_ERA_STAMPS`: `us_prophet_v1` | 147 | live 2026-08-02 → 2026-08-10 |
| `SUPERSEDED_ERA_STAMPS`: `us_prophet_v2` | 148 | live 2026-08-10 → 2026-08-15 |

No later commit on this checkout changes the rank-family set.

## Commits whose subject/diff touched a constant / epoch / bucket / rank family

On this checkout, the only readable commit for all five files is:

| commit | date | one line |
|---|---|---|
| `69268b06502c` | 2026-08-23 | chore(immune): update ci_status + immune journals [skip ci] — **adds** canon constants 14/14/60/5 and 14/3/3, US_EPOCH 1950-01-03, US_FORWARD_DAYS 400, absolute `session_positions // n` bars, and rank family `{us_prophet_v1, v2, v3, v2_shadow, v2_fallback}`. |

`git show 69268b06502c -- engine/canon.py | head -200` is the new-file header plus the module docstring through `net_liquidity_bn` (not the RSI constants; those sit at lines 417-418 of the added blob, past the 200-line cap). Constants were confirmed via `git blame` and by reading the working tree.

## Gap

Shallow clone + missing object `948bccfd511119f6f2eba8936b8ad46373462e3c` blocks any era earlier than the 2026-08-23 immune add. In-file comments still *name* prior eras (`abs-session-2026-08-06`, `display-grid-abs-session-2026-08-06`, `sq-abs-session-2026-08-06`, `us_prophet_v1/v2/v3` dates) but those named dates are not independently recoverable as git diffs here.
