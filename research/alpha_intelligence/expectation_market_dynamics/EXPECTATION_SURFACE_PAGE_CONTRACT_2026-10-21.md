# Expectation Surface page contract — 2026-10-21

This document freezes the data contract for the Expectation Surface page, the
descriptive consensus layer of the Information→Price programme (wave 1). The
page is built by `scripts/build_expectation_surface.py` from the collected
expectation ledger and rendered through
`templates/expectation_surface.html.j2`. It describes how analyst expectation
disclosures changed between collection sessions. It describes only.

## What the page is

A static page (`site/expectation_surface.html`) plus a small static JSON
surface (`site/expectation_surface/summary.json`,
`site/expectation_surface/tickers/index.json`,
`site/expectation_surface/tickers/<T>.json`). Every number on the page is
computed at runtime from `data/revisions/expectation_observations.parquet`,
`data/revisions/expectation_attempts.parquet` and
`data/reference/vendor_aliases.parquet`. Nothing is hardcoded: counts, session
spans, identity figures and movers are recomputed on every build. The stale
figures from the early brief (473,200 rows / 724 unresolved / 777 undated) are
superseded and appear nowhere in the builder or the tests. The identity probe's
issuer-master join is NOT repeated here; identity status is derived only from
the vendor_aliases ledger as specified below.

## Reserved controls

- `financial_influence: false` and `k3e_admissible: false` are present and
  false on `summary.json` and on every `tickers/<T>.json` document, always.
- The page grants no rank, no gate, no position size, no trade, and no capital
  authority. It is not a signal. The words that would suggest otherwise do not
  appear outside the page's "What this is not" list.
- No invented values: every emitted number is derived from the parquet ledgers.
- No LLM-originated numbers anywhere in the builder or its outputs.
- EVAL-1 data is never read by the builder or its tests.
- Render lanes never write under `data/`; the builder writes only under
  `site/`. D57 applies: the site JSON emitted here is a regenerated render
  artifact, never a ledger.
- Identity counts are computed at runtime from `vendor_aliases.parquet`.

## Sessions and clocks (rule a)

A session is a `collection_session_id` in the observations ledger. The session
clock `at` is `min(attempted_at)` per session from
`expectation_attempts.parquet`. If the attempts ledger is missing or unusable,
the clock falls back to `min(system_observed_at)` per session from the
observations and the summary carries the reason
`"attempts_unavailable: session clock from system_observed_at"`. The session
universe is the set of sessions that have observations; attempt-only sessions
(failed collections with no observation rows) neither extend the universe nor
move the latest/prior window. Sessions order by `at`, then by session id.

## Valid points, comparisons, rollovers (rules b, c)

A valid average point is an observations row with
`observation_type == "average"`, non-null `value` and null
`missingness_reason`. Comparisons pair each valid average point with the SAME
key's (`ticker_compat`, `metric`, `horizon_label_raw`) immediately previous
valid point — tickers rotate through the collection in subsets per session, so
a global "previous session" is never used. A pair is counted only when
`period_end` is equal and non-null on both sides; any other adjacent pair is a
rollover: it is excluded from every downstream count and increment
`exclusions.rollover`. A key's first valid point has no pair and is not a
rollover.

## Breadth (rule d)

For each session with at least one comparable pair and each metric: `up` counts
pairs whose latest point is in that session with delta greater than the
tolerance, `down` counts delta below the negated tolerance, `flat` counts
|delta| within the tolerance, where `tol = 1e-9 * max(1, |prior|)`. Rows
`[{session_id, at, metric, up, down, flat}]` order by session `at`, then
metric. A zero prior still produces a breadth direction (delta = latest), even
though the same pair is excluded from movers.

## Movers (rule e)

`latest_session` is the last session by `at`; `prior` for a candidate is that
key's immediately previous valid point under rule c (it is not required to sit
in the globally second-to-last session). For each metric, candidates are keys
whose latest valid point is in the latest session and which have a comparable
prior point. Pairs with `prior == 0` are excluded and counted in
`exclusions.zero_prior`. Rows that rule b filtered out (average-typed
observations with null value or non-null `missingness_reason`) never enter any
comparison; `exclusions.missingness` counts those average-typed rows across
the whole ledger. `pct_change = (latest − prior) / |prior|`, rounded to 6
decimal places. `up` is the top 25 by `pct_change > 0` descending; `down` is
the top 25 by `pct_change < 0` ascending (most negative first); ties break by
ticker then horizon. Each item is
`{ticker, horizon, period_end, prior, latest, pct_change, analysts, prior_at,
latest_at}` where `analysts` is the `covering_analyst_count` value for the
same ticker/metric/horizon/session as the latest point (null when absent) and
`prior_at`/`latest_at` are the session clocks.

## Identity (rule f)

Universe U = distinct `ticker_compat` in the observations. `resolved` = tickers
in U with at least one aliases row where `vendor == "store"`,
`vendor_symbol == ticker` and non-null `security_id`. `unresolved = |U| −
resolved`. `undated_aliases` = resolved tickers with no aliases row (any
vendor, same `vendor_symbol`) carrying a non-null `valid_from`. Per-ticker
`identity_status` is `resolved` (resolved and dated), `undated` (resolved but
undated) or `unresolved`. When the aliases ledger is missing or unusable every
ticker is `unknown` and a reason names it. `identity.state` is always the
literal `COMPLETE_DEGRADED` — degraded identity is the standing condition of
this surface, not an error state.

## Census (rule g)

`census.observations` = row count of the observations ledger;
`securities` = |U|; `metrics` and `horizons` = sorted distinct values;
`sessions` = distinct observed sessions; `span` = {first, last} session clock;
`analysts_median` = median over keys of the `covering_analyst_count` value at
each key's latest session carrying one (null when none).

## JSON contract (rule h — summary.json)

```json
{
  "schema": "expectation_surface.page.v1",
  "rendered_at": "<ISO-8601 UTC, Z suffix>",
  "financial_influence": false,
  "k3e_admissible": false,
  "state": "LIVE" | "OFFLINE",
  "reasons": ["…"],
  "source": {
    "observations_path": "data/revisions/expectation_observations.parquet",
    "observations_blob_sha1": "<git blob id>",
    "source_revision": "<git rev-parse HEAD or null>",
    "latest_session": {"id": "…", "at": "…"},
    "prior_session": {"id": "…", "at": "…"}
  },
  "identity": {"state": "COMPLETE_DEGRADED", "resolved": 0, "unresolved": 0,
               "undated_aliases": 0},
  "census": {"observations": 0, "securities": 0, "metrics": [], "horizons": [],
             "sessions": 0, "span": {"first": null, "last": null},
             "analysts_median": null},
  "breadth": [{"session_id": "…", "at": "…", "metric": "…", "up": 0, "down": 0,
               "flat": 0}],
  "movers": {"EPS": {"up": [], "down": []}, "revenue": {"up": [], "down": []}},
  "exclusions": {"rollover": 0, "missingness": 0, "zero_prior": 0}
}
```

`observations_blob_sha1` is the git blob object id of the observations parquet,
computed in-process (sha1 of `b"blob <len>\0" + bytes`). `source_revision` is
`git rev-parse HEAD` via subprocess with a 5 s timeout, else null plus a
reason. Additive keys relative to the earlier frozen contract:
`exclusions`, `observations_blob_sha1`, and `period_end` on series points.
Every key shown above is emitted on every build; nothing frozen was removed.

## JSON contract (rule i — tickers)

`tickers/index.json` is a list of
`{ticker, sessions, latest_at, identity_status}` sorted by ticker. `sessions`
counts the distinct observed sessions carrying that ticker; `latest_at` is the
clock of its latest one. The index is complete (it lists every ticker in U);
the per-ticker FILES are gated: `tickers/<T>.json` is written only when the
ticker matches `^[A-Z0-9.\-]{1,15}$`; skipped tickers produce the reason
`"ticker_skipped_unsafe_filename: <n> tickers"` (count only, no names). Each
ticker file is:

```json
{
  "ticker": "…",
  "identity_status": "resolved" | "undated" | "unresolved" | "unknown",
  "financial_influence": false,
  "k3e_admissible": false,
  "series": {
    "EPS":  {"0q": [], "+1q": [], "0y": [], "+1y": []},
    "revenue": {"…": []}
  }
}
```

Series carries both metric keys always; horizon keys appear only where the
ticker has data. Points order by session clock; each point is
`{at, period_end, average, median, high, low, analysts}` with values from the
same session/key and null when that observation_type is absent from the
session.

## Numbers (rule j)

Floats round to 6 decimal places; NaN becomes null; timestamps are ISO-8601
UTC ending in `Z`. Every JSON document is written with
`json.dumps(…, ensure_ascii=False, sort_keys=False, allow_nan=False)`.

## Honest state (rule k — OFFLINE)

If the observations parquet is missing or unreadable, `state` is `OFFLINE`,
`reasons[]` names the cause, census fields are zeros/nulls, `breadth` is `[]`,
`movers` carries the frozen EPS/revenue shape with empty lists, the index is
`[]` and no ticker files are written. The HTML page still renders and shows an
offline band (`role="status"`) listing the reasons. The builder never raises
outside `main()`'s guard and never writes under `data/`.

## Registration and budget

`scripts/build_site.py` registers the builder with one additive try/except
block placed directly after the `_render_finance` block; a failure logs a
warning and skips the page without breaking the main build. The full real
run over the current ledger must finish in under 60 s wall.
