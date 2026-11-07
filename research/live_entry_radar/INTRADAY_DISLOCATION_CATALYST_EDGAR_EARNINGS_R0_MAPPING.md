# Catalyst Context R0 Mapping Freeze - EDGAR Earnings Item 2.02

**Owner path:** `collectors/edgar_earnings_8k.py` + canonical filing key in `engine/earnings_release/filing_key.py`  
**Consumer:** `engine.entry_radar.catalyst_context`  
**Authority:** research-only context; all Radar authority remains false  
**Frozen before:** adapter implementation or any outcome study

## 1. Purpose

Map one already-observed canonical SEC filing record into an R0 catalyst evidence reference without inventing a second filing identity or a historical processing clock.

This mapping does **not** establish source coverage. A single event adapter can prove presence of one event; it cannot prove absence of all events.

## 2. Accepted source record

The adapter accepts only a mapping with:

- `ticker`
- `cik`
- `accession`
- `form`
- `acceptance_datetime`
- `items`

The canonical filing identity is delegated to `filing_key_from_8k_row`. No ticker/date fuzzy join is permitted.

Accepted forms:

- `8-K`
- `8-K/A`

The `items` field must contain the exact comma-delimited token `2.02`. Substring matches such as `12.02` and `2.020` are refused.

## 3. Clock law

`acceptance_datetime` is the SEC source-availability clock.

The adapter also requires an explicit caller-supplied `owner_observed_at`. That is the system observation/processing clock.

Output clocks are:

- `source_available_at = acceptance_datetime`
- `known_at = owner_observed_at`

Required ordering:

`acceptance_datetime <= owner_observed_at`

A historical parquet row with no per-row observation receipt cannot manufacture `owner_observed_at` from file mtime, report generation time, current `asof`, or SEC acceptance. Such a row is not admissible to a historical as-observed intraday decision through this adapter.

## 4. Frozen disposition mapping

For this safety-context experiment only:

- exact Item 2.02 `8-K` -> `owner_disposition = blocking`
- exact Item 2.02 `8-K/A` -> `owner_disposition = blocking`

This is deliberately conservative and direction-free. It means only:

> an earnings-results filing was known by the tactical decision clock, so the event cannot be treated as an ordinary catalyst-clear mean-reversion case.

It does not say earnings were good/bad, predict continuation/reversal, or confer trading authority.

Event kinds:

- `earnings_results_item_2_02`
- `earnings_results_item_2_02_amendment`

## 5. Identity and evidence reference

Native identity is the canonical filing key:

`{cik:010d}:{canonical_accession}`

Evidence reference is:

`sec-edgar-item202:{native_identity}`

The adapter does not create a new event id.

## 6. Refusals

The adapter refuses:

- non-mapping input;
- missing/unparseable CIK or accession;
- unsupported form;
- missing exact Item 2.02 token;
- missing/unparseable acceptance timestamp;
- `owner_observed_at < acceptance_datetime`;
- missing ticker.

Refusal is not `nonblocking`. The caller must keep the source/event state unavailable or unknown.

## 7. No-coverage rule

This adapter returns only `CatalystEvidence`. It never returns `CatalystSourceRead`.

A healthy `CatalystSourceRead` for an EDGAR source requires a separate owner-specific coverage receipt proving that the relevant source query/stream was complete and observed by the decision clock. The historical static store alone does not prove that.

## 8. Validation

Synthetic acceptance tests must cover canonical identity, exact-token matching, amendment semantics, missing identity, missing clock, clock inversion, and absence of any rank/score/trade output.

## Relevance window (2026-10-03)

A results release drives the context from the moment it is known until the close of the first regular US session that opens at or after the release became available. A release after the close or before the open is relevant through that next session's close. A release during a session is relevant through the following session's close. After that the reference is kept as expired evidence and no longer drives the context state. The window is computed from the Radar reference-session calendar and the release's source-availability clock only.

## Repair 2 — 2026-10-03

- `aftermath_until` is five reference US session closes after `relevant_until`, so a Thursday after-close filing can still read as aftermath on the following Monday when coverage is complete.
- The 900-second module read staleness ceiling applies to any EDGAR coverage read paired with this evidence; it is independent of `fresh_until`.
- Late EDGAR rows are audit flags only and never change decision-time state.
- Each 8-K/A amendment stays its own row and reference.
