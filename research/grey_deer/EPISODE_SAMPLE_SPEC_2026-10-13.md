# Episode and negative-control samples (2026-10-13)

Schema: `grey_deer_episode_samples.v1`.
Code: `scripts/research/grey_deer_episode_samples.py`.

This builder freezes the sample later mechanism studies draw from. It does
not score outcomes. The same close series and seed produce the same
`json.dumps(..., sort_keys=True)` bytes. The JSON has dates, counts, ids, a
seed and hashes. It has no closes.

Labels, clusters and episode windows come from the stage-1 functions
`build_labels`, `event_clusters` and `merge_episodes`. That path calls
`cluster_window` and pads with `EPISODE_PRE` (21). This module imports those
functions and does not reimplement them.

## Episodes

`event_episodes(close, h)`:

1. `build_labels` returns one entry per frozen horizon (`5`, `10`, `21`).
   Each entry has `A` (forward maximum loss) and `Y` (true when that loss is
   at least 5%). The last `h` rows are immature and are not events.
2. Event origins are the session indices where `Y == 1`.
3. Origins whose session-index gap is at most `h` form one cluster.
4. A cluster window runs from 21 sessions before its first origin through `h`
   sessions after its last. Clusters whose windows overlap, including a
   shared endpoint, are one episode.
5. The emitted window is that interval clipped to the series, as ISO dates
   `YYYY-MM-DD` and as those same session indices `[lo, hi]`. A negative
   index is not a session, so both fields are clipped. Control length is the
   clipped length.
6. `episode_id` is `h{h}-e{k:03d}` with `k` starting at 0, in time order.
   The episode also records `n_event_origins`, `first_event` and `last_event`.

Every mature `Y == 1` origin on the series is included. The stage-1 warmup
cut (`idx >= 63`) and the comparison-set cut are not applied. A study that
needs those cuts says so in its own preregistration.

## Negative controls

`negative_controls(close, h, episodes, *, seed, per_episode=3, buffer_sessions=63, max_tries=10_000)`
draws up to `per_episode` windows per episode, each the episode's clipped
length.

A start is eligible when the window lies inside the series, the span
`[start - buffer_sessions, end + buffer_sessions]` misses every episode
window, the window holds no `Y == 1` origin at this horizon, and the window
misses every control already accepted in this call. Adjacent sessions do not
overlap, so a pad of 0 may start a control on the session after an episode.
`buffer_sessions` is a non-negative pad.

Month-of-year is the calendar month of the window's first session, not the
year-month. If any eligible start shares the episode's start month, the draw
is uniform among those starts and `month_matched` is true. If none does, the
draw is uniform among the other eligible starts and `month_matched` is false.

One `numpy.random.default_rng(seed)` serves the call. Episodes are filled in
list order, slots in order. Each accepted control is one `integers` draw and
then leaves the pool. An empty pool skips that slot and the later slots of
that episode. Later episodes are still tried. The function returns what it
placed and does not raise when the series runs out of room. Starts are scanned
once, so the search cannot loop forever.

`max_tries` caps proposals on one slot. The eligible set is built first, so a
cap of at least 1 still returns a control whenever one exists and still prefers
a month match whenever one exists. A cap below 1 places nothing.

`build_sample` uses these defaults and records
`shortfall = len(episodes) * per_episode - len(controls)` on that horizon.
Zero means every requested control was placed.

`control_id` is `{episode_id}-c{j:03d}` with `j` from 0 in place order. Each
control also has `episode_id`, `window`, `window_idx`, `month_matched` and
`seed`. Each horizon inside `build_sample` starts a new generator from the
same seed. Horizon 10 does not depend on horizon 5.

## Envelope and hashes

`build_sample(close, *, ticker, horizons=(5, 10, 21), seed=20261013)` returns
`schema`, `ticker`, `seed`, `n_sessions`, `first`, `last`, `input_sha256` and
`horizons`. Horizon keys are `"5"`, `"10"` and `"21"`. Each value has
`episodes`, `controls` and `shortfall`.

`first` and `last` are the ISO dates of the first and last rows. Row order is
session order. The builder does not sort.

`input_sha256` is the hex SHA-256 of one line per session,
`YYYY-MM-DD repr(float(close))`, joined with a newline and no trailing
newline. `repr` is Python's builtin float repr. The digest does not restore
a close.

The freeze hash is the SHA-256 of
`json.dumps(sample, sort_keys=True).encode("utf-8")`. Do not use another JSON
style. Episodes stay in time order and controls stay in draw order. That list
order is part of the hash.

## How T13, T14 and T19 use it

T13 (macro, rates, credit), T14 (leader damage) and T19 (protection) take
episodes and controls from this builder. They do not pick a fresh set inside
the study.

Before any outcome on those hypotheses is computed, the preregistration
records the ticker, `input_sha256`, `first`, `last`, `n_sessions`, the seed
(`20261013` unless the prereg names another), the horizons, the freeze hash
above, and any `episode_id` or `control_id` the prose names.

That recorded sample is the only one the study scores. A new seed, a new
series or a new builder version is a new preregistration, not a check run
after outcomes are known. The study supplies the close series. This module
does not fetch one.

## Limits

Single ticker. One close series. No cross-sectional join.

Do not reuse the panel date-axis episode rule from pullback preregistration
v1.1 decision D9. That rule clusters dates on which any panel name has
`Y = 1`, merges a gap of at most `h` sessions, and builds windows on the
shared date axis. It is a different object from this per-ticker session-index
episode, and it is known to be degenerate at `h = 21`. Keep it out of T13,
T14 and T19 samples.

The optional CLI takes a required CSV path (`date` and `close`, or
`--date-col` / `--close-col`) and a required `--ticker`. It has no default
path. Library functions do not read files and do not use the network.

No hit rate, no forward return after a signal, no skill score and no gate.
Those belong to a study that freezes this sample first.
