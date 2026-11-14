# RD note 2026-11-14: the 2-session trailing-bin drop (SI fact on grey_dot.py:170–196, via the Prophet lead)
- events_v1 already covers this case. FULL_GUARD recomputes the dot from closes truncated at every G3 known_ts, which is what a live run would see. An event is kept only if the dot fires on that same known_ts. FULL_GUARD.md records 4,500 G3 drops attributed to the changed 2B availability leg (95.7% of all drops), plus 203 others.
- The retained 35,465 G3 events are therefore those a live run would print on their own date.
- Open, description only: a dot the live run prints one session later (at t+1) appears as an event only if the full-history mask also fires at t+1. Those delayed versions may therefore be missing. This is a calendar-parity selection, so it is not expected to relate to outcomes, but that has not been measured. The W1 brief carries this caveat.

## Addendum 2026-11-14, SI count. Synthetic only, seeds 11 and 12, not checked on real names
- Cut range: the full history has 55 dots (seed 11) and 61 (seed 12). The cut-date differences are 6 and 7, about 1 dot in 10 (~0.25% of days).
- At t+1, on 2,599 cuts per seed, day t matches the full-history value in every case (0 failures). The one dot per seed that existed only in the short history drops out by t+1.
- SI's reading: a live run prints about 1 dot in 10 one session late. From t+1 it agrees with the full-history replay.
- For W1: FULL_GUARD keeps a dot only if it is present when closes are truncated at known_ts, so the late-printed dots fall into its excluded set. A share of about 10% is the same order as our observed FULL_GUARD drop (4,500 of 39,965, 11.3%). This is suggestive only: the excluded set has not been broken down by cause.
- W1 caveat wording: "Retained dots are those visible on their own close. About 1 in 10 dots (synthetic estimate) first print a session late in live use and are excluded here. Results describe same-session-visible dots."
