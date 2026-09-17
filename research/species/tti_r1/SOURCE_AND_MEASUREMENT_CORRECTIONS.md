# TTI input and measurement corrections

Status: source-grounded design, not an installed producer repair.

## Existing fields are lost before the current chart store
Massive Custom Bars exposes optional per-bar `vw` and `n` and fractional `v`; its endpoint-specific timestamps are UTC milliseconds marking bar start, with split adjustment controlled by `adjusted`. Terminal's current six-value historical projection keeps OHLCV, casts volume to int, and discards `vw`/`n`. D0 preserving fractional values at read time cannot restore information already truncated upstream.

A bar-derived HLC3*volume average must be called a bar-VWAP proxy, not exact trade VWAP. Massive's extended-hours documentation further warns that volume eligibility and price eligibility differ for some sale conditions. Thus even the usual low/high bound for the volume-weighted underlying trade sample must not be assumed from sparse OHLC bars alone.

Required producer follow-on, under the existing data owner: preserve available `vw`, `n`, fractional volume, UTC window start/end, adjustment declaration, request/capture identity and correction/availability evidence inside the accepted source contract. Do not create a second independent warehouse, replay store or live feed. Current six-value chart compatibility must survive a versioned additive source contract. Its specific authoring paths and installed writer must be reconciled before modifying the producer.

Primary external contracts checked 2026-09-17:
https://www.massive.com/docs/rest/stocks/aggregates/custom-bars
https://massive.com/knowledge-base/article/does-massive-offer-pre-market-and-after-hours-data

## Historical uncertainty must not freeze useful research
Corrected-history experiments can falsify constructions and identify follow-on questions, provided they are not represented as faithful historical live execution. Missing historical availability is not a reason to stop all feature engineering. Prospective capture must preserve real availability from inception; a new fetch or mtime cannot backdate it. Do not claim an inferred vendor delay repairs undocumented historical revisions.

The after-hours/premarket interval is not continuous 24-hour coverage. Do not forward-fill the 20:00–04:00 period and call it observable overnight demand. Early-close post-market schedules need their own qualified source; the regular-session calendar alone does not establish them.

## Eligibility can leak even when the formula is causal
Whole-file hashes and global invalid-row counts are provenance/inventory, not predictors. A future corrupt OHLC value in otherwise parseable data must not remove an earlier candidate or alter its eligibility. Validate observation content at the decision prefix; keep whole-file diagnostics separate. Outcome-window availability may censor a result, but must not erase the pre-outcome firing denominator. Missing data and failed processing must never masquerade as no signal.

## Measurement-interface mismatch
`engine/species_registry.py` currently admits rotational/positional horizon classes. `engine/rule_replay.py` has frozen daily horizon/reference conventions. Do not smuggle a 60-minute/3-session rule through those interfaces by relabeling units. A bounded research recipe can use existing TrialLedger accounting without changing daily semantics; eventual generic intraday admission needs an explicit versioned amendment in the existing scientific owner, not a second registry or replay engine.

## Current-history repair review
Terminal #595 remains the existing refresh carrier. Source review at ba7c48cf58b2a04deb5b566655e8e61721caca3b identified two failure-reporting paths: exhausted `_get` failures become empty/unchanged, and a failed later page can return/publish an accumulated prefix. Review 5242058779 requests a bounded repair and actual offline transport-path discriminators. No repair, refresh, merge or deployment was performed by this R1 work. A proposed reproduction was platform-blocked; no runtime reproduction is claimed.

## R1 effect boundary and later recovery
The original trial-grid registration/commit request and subsequent implementation-write request were platform-blocked before a process/result was returned. Same-carrier inspection proved zero effect at that point, so no alternate-carrier resubmission occurred. A later material tool/mode recovery allowed this **same R1 carrier** to proceed lawfully: prereg/config remained frozen, the existing TrialLedger received exactly 84 study rows at `0109877f57009973cbebe9f72e43bd23e35a5183`, and implementation/results followed. `REGISTRATION_RECEIPT.json`, `TTI_R1A_REPORT.md` and `STATUS.md` are the current receipts. The old refusal remains historical evidence, not the current capability state.
