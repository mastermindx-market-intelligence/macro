# Q12 — PREREG amendment 1 (finisher, after the independent audit)

Amends: PREREG.md sha256 `b6bfe4b12e07056dd229b8d181a220b0bc6f1403e71e7b071683d6f57fa200b3`,
frozen in FREEZE.log (sha256 `b53eb3d2cb2eb30163dded78055f56431e5c113b7342fa424e4c7216b1c26a0f`).
PREREG.md itself is unchanged.

Timing, stated plainly: this amendment was written after the finisher re-ran evaluate.py
(RUNS.log entry `2026-10-09T10:38:33Z`). That run, like every run before it, read **no H2
outcome**. Eligibility rule E found 0 stores, so `comparison_H2_run` is false and the stop
rule applied. The run's only results are the schema census, synthetic baseline controls
and the descriptive D1 diagnostic. Neither change below can move the verdict toward KEEP
or REJECT.

## A1 — §1 estimand: the D band is intersected at one common D

PREREG §1 writes `I_k(t)` "widened over [D_lo, D_hi]" and `F_hat_g(t)` as the intersection
of the I_k. Read literally (widen each pair over the band, then intersect), that is only an
OUTER bound of the intended set. The pairs can overlap while no single discount factor
makes them all hold. Counterexample: band (0.9, 1.0), strikes 82 and 83.5, puts bid/ask
1.0/1.5, calls 19.5/20.0. Widened-then-intersected gives [101.5, 103.11], but at every
single D the strike-83.5 lower bound exceeds the strike-82 upper bound.

Amended definition:

    F_hat_g(t) = union over D in [D_lo, D_hi] of  intersection_k [K_k + x_lo_k/D, K_k + x_hi_k/D]

Here x_lo = C_bid − P_ask and x_hi = C_ask − P_bid. If the set is empty the group is
`incompatible` (reason `no_common_discount_factor_in_band`). For a point band (D_lo = D_hi)
the two readings are identical. The amended set is always contained in the widened one,
so it is never wider. It is the set the §5 H2 comparison would score.

## A2 — §4 rule E census: an advisory alias pass in addition to the exact-name sets

evaluate.py's exact-name column sets could miss renamed quote columns. The census now also
tokenizes every parquet column name and json/jsonl/csv head key. A store becomes an alias
candidate when it carries a bid-level token, an ask-level token and a strike token.
Size, share, side, flow, count, spread, basis-point and basket tokens disqualify a column,
because those columns are statistics, not quote levels. An alias candidate forces exit 4
(amendment before any outcome is read), the same as an exact-name match. The pass can only
make the stop rule stricter, never looser.

Result of the finisher run: 0 alias candidates and 0 exact-name eligible stores, across
25,246 parquet schemas and 39,175 text heads (results/census.json, results/summary.json).
