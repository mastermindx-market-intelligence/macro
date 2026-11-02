# PBOC liquidity composition read (2026-10-13)

Display and context only. `engine/china_pboc_liquidity.py` (`china_pboc_liquidity.v1`) turns a caller-supplied window of open-market days into a typed current liquidity state. No collector, template, or page calls it. Wiring it to a bulletin source needs a separate owner-approved packet.

The function is pure. The same inputs produce the same `to_dict()`. It does not read a store, a file, or the network, and it does not rescale amounts. Callers pass injection, maturity, and the medium-term net already in one unit.

## Why a missing day stays missing

Two kinds of empty day exist, and they mean different things.

- A valid zero is a day the bulletin was observed. Injection `0` or `0.0`, maturity present (including zero), and operation count `0` are real observations. A stretch of those days is a quiet stretch.
- A missing day is a day where injection, maturity, or the operation count was not observed (`None`). That day is left out of the sums and left out of the quiet-stretch test. The reason list gains `partial_window`.

Treating "no row" as "the central bank added nothing, so it is draining" collapses those two facts. A quiet stretch is called ample only when the money-market rate agrees with the policy rate. A blank day never fills in as a zero to make that test pass.

## States

| State | Plain reading | When |
| --- | --- | --- |
| `insufficient_data` | Not enough fresh observations to read liquidity | Stale window, fewer than 3 observed days, or a quiet stretch with no rate spread |
| `zero_op_ample` | Quiet: no operations, money is ample | Every observed day is a valid zero, and the spread is at or under the band (default 15 bp) |
| `zero_op_tight` | Quiet: no operations, money is tight | Every observed day is a valid zero, and the spread is above the band |
| `rollover` | Roughly balanced: new money matches what is coming due | Operations occurred, and the net is inside the balance band, including the edge |
| `net_support` | Net support: more money is added than comes due | Net is above the balance band |
| `net_drain` | Net drain: more money comes due than is added | Net is below the balance band |

English and Chinese display strings live on `LABELS`. They do not use internal abbreviations.

## Rules

`classify_liquidity(inputs, *, window_days=5, tight_spread_bp=15.0, rollover_abs_cny_bn=5.0, rollover_rel=0.10, stale_after_days=4)`:

1. A day dated after `asof` raises `FutureDatedInput`. Two rows on the same date raise `ValueError`. Negative injection, maturity, or operation count raises `ValueError`. Operation count `0` together with a positive injection raises `ValueError` (the bulletin contradicts itself).
2. The read keeps the last `window_days` rows by date. A non-positive count keeps nothing.
3. Stale means the newest kept day is more than `stale_after_days` calendar days before `asof`. No rows is stale. Stale forces `insufficient_data`, with reason `stale`.
4. A day is observed only when injection, maturity, and operation count are all present. Fewer than 3 observed days forces `insufficient_data`, with reason `fewer_than_3_observed`.
5. Gross injection and gross maturity are the sums over observed days (0 when none). Net is gross injection minus gross maturity, plus the medium-term net when that figure was supplied. When it was not, the net is the open-market net only and the reason is `mlf_unknown`.
6. Spread, in basis points, is `(FR007 percent − 7-day policy rate percent) × 100` when both rates are present. Otherwise the spread is unknown (`spread_unknown`).
7. Quiet stretch: every observed day has operation count 0 and injection 0. Money coming due on those days stays in the net figure and does not flip the state to a drain. Unknown spread → `insufficient_data` (`zero_op_spread_unknown`). Spread at or under the band → `zero_op_ample`. Spread above the band → `zero_op_tight`.
8. Otherwise the balance band is the larger of `rollover_abs_cny_bn` and `rollover_rel × gross maturity`. Net inside the band, including exact equality, is `rollover`. Above is `net_support`. Below is `net_drain`.
9. Any kept day that is missing adds `partial_window`. Three or more observed zero days can still read as a quiet stretch.

Reason order is fixed: `stale`, `fewer_than_3_observed`, `partial_window`, `mlf_unknown`, `spread_unknown`, `zero_op_spread_unknown`. Amounts are still filled in when the state is `insufficient_data`, so a caller can see the partial arithmetic beside the refusal to name a direction.

## Source census

Read for this note: `collectors/china_pboc.py` and `engine/china_pboc_stance.py`. Neither module is an input to the classifier.

What those modules have today:

- `collectors/china_pboc.py` stores three series: monthly FX reserves and gold (`fx_reserves`), daily interbank repo fixings `FR001`, `FR007`, and `FR014` (`repo_rates`), and the daily USD/CNY reference (`cny_fix`).
- `engine/china_pboc_stance.py` reads LPR 1Y and 5Y, the reserve-requirement ratio, `FR007` against its own trailing average, SHIBOR overnight and 3-month, FX reserves, gold, and USD/CNY. It produces an easing / on-hold / tightening stance. It does not read `FR001` or `FR014`.

What this read needs, against that pair:

| Input | In those two modules |
| --- | --- |
| Daily injection, maturity, operation count | No |
| Medium-term lending net | No |
| `FR007` | Yes, `repo_rates` column `FR007` |
| 7-day policy rate | No |

The collector says, in one line: "The current MLF / 7-day OMO administered RATE is not exposed cleanly by any keyless source (PBoC HTML only)". The stance path therefore uses LPR, the reserve ratio, and `FR007`. That is a corridor read. It is not this composition read.

Also in the repo, and not used here: `collectors/china_omo.py` keeps bulletin rows (operation date, tenor, a rate when the bulletin states one, an amount, a maturity date, and a column for medium-term tenders). It does not emit the daily injection / maturity / operation-count triple, and it does not emit a medium-term net. A search of that file found no announced-zero path. Its coverage counter treats an unstated rate as a null, which is the same idea as this read: an unstated figure must not be stored as zero. The amounts on that tape are the bulletin's own 亿元 figures. This classifier does not convert units. A wiring packet has to say how those rows become injection, maturity, operation count, a valid announced zero, and the medium-term net.

`python3 -c "import akshare"` on this host raises `ModuleNotFoundError`. No installed akshare tree was searched, and no akshare function was called.

## Not wired

This read is display and context only. It is not imported by a page, a template, or another engine. No score, rank, or risk gate uses it. Connecting it to `FR007`, a 7-day policy rate, and a bulletin window is a later packet with its own owner approval. Until that packet exists, callers pass literal inputs and receive a typed state.
