# Treasury daily history for internal portfolio calculation

`GET http://127.0.0.1:8000/api/internal/treasury-history` reads the existing
`data/fred/DGS3MO.parquet` input. It accepts required `start`, `end`, and
`expected_through` ISO dates, with a maximum 3,660-calendar-day window. It
accepts no holdings, account identifiers, source path, ticker, or upstream URL.
It performs no collection, interpolation, cache write, or fallback.

The transport reuses `app.prophet_lab._hub_prophet_authorized`: only an actual
loopback socket peer with **no** `X-MM-Peer` header passes. The deployed public
Caddy `/api/*` proxy overwrites that header with the public peer, so every
edge request is denied, including an authenticated one or an empty/spoofed
header. The existing `require_site_full_user` also verifies the caller's
Bearer credential and site-full entitlement before reading native input.
The existing service must remain bound to `127.0.0.1:8000`; a source-IP check
alone behind Caddy is insufficient. Responses, refusals and errors are private,
no-store, and noindex.

The response schema is `treasury.daily_history.v1`. Each point is
`{date: "YYYY-MM-DD", value: <finite annual percent>}`. Source identity is
**DGS3MO via FRED**, alias `us3m`, investment basis, units `percent_per_annum`.
This is a Treasury nominal constant-maturity yield, not a bill discount yield
or an OHLC price. Negative finite yields are retained. Missing, empty, invalid,
unreadable, oversized and uncovered inputs have explicit unavailable reasons;
no value is invented. Duplicate/invalid dates, wrong columns, nulls and
nonfinite values fail closed. Coverage counts actual observations and requested
calendar days, never inferred exchange sessions.

The source tail and requested-window tail are separate. A requested-window
tail before `expected_through` returns `status: stale` and dated observations.
`read_at` is the actual local read-attempt clock; release, knowledge and vintage
clocks remain null. This is an observation-date view, not a vintage or causal
availability assertion. The exact bytes read receive a SHA256 fingerprint.

FRED identifies DGS3MO as Public Domain: Citation Requested. Its terms expressly
allow attributed internal commercial use and reports to clients, while raw
third-party redistribution has separate restrictions. This same-organization
input read supports Terminal's existing server-side derived metrics. It does
not activate a browser/raw-history export. Attribution remains Board of
Governors of the Federal Reserve System (US), H.15, via FRED:
https://fred.stlouisfed.org/series/DGS3MO and https://fred.stlouisfed.org/legal/.

The original Board H.15 release describes the identical economic series and
the Board disclaimer permits attributed copying/distribution. This contract
does **not** relabel FRED-retained bytes as original-Board acquisition. The
original historical DDP read was denied; no original-source adapter, guessed
download URL, or alternate acquisition is activated by this change.

## Terminal binding

The incumbent Terminal risk-history owner should request this exact same-box
route using an existing verified site-full Bearer credential. A configurable
backend must be verified as the intended loopback origin before forwarding any
credential. Do not send holdings or portfolio costs. Do not call it through the
public origin or forward browser cookies to another origin.

Validate schema, source identity, units, basis, status, dates and finite values.
Map `points` into the existing compiler's dated annual-percent input and retain
source/status metadata. Request seven calendar days before the first required
return date to preserve its existing backward-only, at-most-seven-day alignment.
Keep `annualPercentToDaily` and its existing 252-day conversion in Terminal;
never substitute a scalar/current yield, forward observation or zero. Preserve
staleness and coverage failures. Missing/unreadable RF must retain beta when
prices suffice and leave Sharpe/Sortino null. This source change does not bind
the consumer, resolve price-origin access, or prove the authenticated journey.
