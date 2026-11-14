# Cohort-first implied-volatility input census

**Outcome-blind input diagnostic. No entry, rotation or trading-performance claim.**

Source `6bbc4b0fc694c847077661ff5bf4c19ea41e4e81`; window 2013-01-02 through 2019-12-31.
The native VIX and implied VVIX stores are read through a date-filtered Arrow reader.
No post-2019 row is decoded, no return outcome is read, and no raw vendor series is published.

The measurement is MA20 direction over five equity sessions, with a one-session delay.
It preserves level, level relative to its average, native trailing rank and retreat from
an earlier peak separately. It does not combine these into a new risk score.

Of 1,762 equity sessions, 1,737
have both qualified MA trajectories and 1,510 have both
full 252-session ranks. Opposite MA directions occur on 401
sessions. These counts establish non-identical input behavior, not incremental predictive value.

| Pair of implied-volatility MA directions | Sessions |
|---|---:|
| BOTH_FALLING | 743 |
| BOTH_RISING | 593 |
| UNAVAILABLE | 25 |
| VIX_FALLING_VVIX_RISING | 222 |
| VIX_RISING_VVIX_FALLING | 179 |

## Interpretation and next proof

A rising VVIX trend is not equivalent to high VVIX, a high VVIX/VIX ratio, or realized
variability of VIX changes. Test its incremental contribution through the existing
Fable event archive and registered outcome contract, alongside market-date and cohort
controls. Preserve the native holdout release and every rejected/unknown entry.

The prior-session lag is `PRIOR_SESSION_LABEL_PROXY_NOT_ORIGINAL_RECEIPT`. Original publication and data-vintage
proof remain owed. Missing sessions are never forward-filled. This census does not
choose a gate, estimate a win probability or authorize a change in exposure.
