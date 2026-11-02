# FIF C0 — incremental discovery: shared SEC request pacer + filing observation state

- Lane: `fif-c0-incremental-discovery-20261012`, WS:FINANCIAL-INTELLIGENCE-FABRIC, program `fundamental-forensics`.
- Base: `dbd2f871beee153358998b5722a6eab0668b1558` (head of open D3 PR #8951, stacked).
- Scope: A20 (one shared SEC request budget) + A21 (filing observation state, no re-render freshness).

## A20 — one incumbent pacer (before/after)

**Before (3 pacer owners per process).** Each forensics SEC collector paced itself
with its own `_last_request_at` and interval floor 0.1s:

| Collector | Pacer (before) | After |
|---|---|---|
| `SecForensicsCollector` | `_pace` at `collectors/edgar_forensics.py:248-251` (pre-edit) | delegates to shared `SecRequestPacer` |
| `SecCompanyFactsCollector` | `_pace` at `collectors/fundamental_forensics_companyfacts.py:475-480` (pre-edit) | delegates to shared `SecRequestPacer` |
| `SecFilingArchiveCollector` | `_pace` at `collectors/sec_document_spine.py:837-840` (pre-edit) | delegates to shared `SecRequestPacer` |

`live_fetchers` built the first two with a shared UA but NOT a pacer
(`engine/fundamental_forensics/broad_sec_store.py:4136-4158` pre-edit), and
`acquire_bounded_filings` built submissions + archive collectors each with its
own interval (`collectors/fundamental_forensics_acquisition.py:641-652` pre-edit).

**After (1 pacer owner per process).** `SecRequestPacer`
(`collectors/edgar_forensics.py:226`) is the ONLY pacer class — module docstring
names it the incumbent forensics SEC request pacer. A `threading.Lock` guards
read-compute-sleep-mark; first `acquire()` never sleeps; interval floored
`max(0.1, float(x))`; `sleeper`/`monotonic` default to late-bound module
lookups so existing `monkeypatch.setattr("collectors.edgar_forensics.time.sleep", ...)`
tests keep working. Wiring:

- each collector takes `pacer: SecRequestPacer | None = None` and builds a
  private one from its own `min_interval_seconds` (+ injected clocks where the
  constructor accepts them) when None — byte-for-byte legacy behaviour
  (`edgar_forensics.py:295,305,314`; `fundamental_forensics_companyfacts.py:448,478,490`;
  `sec_document_spine.py:822,841,853`);
- `acquire_bounded_filings` takes `pacer=None`, builds ONE, passes it to BOTH
  factories (`fundamental_forensics_acquisition.py:548,645,655,662`);
- `live_fetchers` takes `pacer=None`, builds ONE, hands it to BOTH collectors
  (`broad_sec_store.py:4142,4152,4158,4164`).

**Stays out (byte-identical, by design):** `collectors/edgar.py` (fundamentals-frames
`time.sleep(0.12)` pacer, daily.yml lane), `collectors/sec_capital_structure_companyfacts.py`,
`scripts/seed_fundamental_forensics_attested_history.py` (attested-history path),
`scripts/research/*`. Cross-process/cross-host pacing is unchanged: the workflow
concurrency group `filing-forensics-sec` remains the only cross-process mutex; no
lockfile, no lease, no token bucket, no second scheduler/queue/budget owner was added.

## A21 — filing observation state (`engine/fundamental_forensics/filing_observation_state.py`)

Pure leaf module: no I/O, no clock read (every time is an explicit aware-UTC
ISO-8601 argument), no `collectors/`/`scripts/` import; imports only
`FRESHNESS_BUDGET_SECONDS` from `engine.fundamental_forensics.health` (:36-37).
States: `new_filing, new_content, checked_no_change, index_quiet, source_outage,
absent_at_source, budget_exhausted, check_failed, not_applicable`.
`SUCCESSFUL_CHECK_STATES = {new_filing, new_content, checked_no_change,
absent_at_source}` — the source answered authoritatively; `index_quiet` is
excluded because an index-diff skip is NOT a byte-level check.

### Wave-2 mapping (`OBSERVATION_OUTCOMES`, `fundamental_forensics_acquisition.py:67`)

| Wave-2 outcome | State | Basis |
|---|---|---|
| `unchanged` | `checked_no_change` | content key matched a stored manifest (:397-422) |
| `new_filing` | `new_filing` | no stored manifest for (cik, accession) |
| `new_content` | `new_content` | stored manifests exist, content key is new |
| `missing` + `missing_cause=http_404` | `absent_at_source` | explicit SEC 404 |
| `missing` + `byte_budget` | `budget_exhausted` | bounded-ingest budget |
| `missing` + `transient_exhausted` | `source_outage` | retry exhaustion |
| `missing` without cause | error `missing_cause_required` | fail closed |

### FF-1 mapping (`REASON_CODES`, `broad_sec_store.py:125-152`; outcome rows :2657, :3510, :3769-3788)

| FF-1 outcome / reason | State | Basis |
|---|---|---|
| `observed_no_relevant_change` | `index_quiet` | CIK not in index-diff work set; no Submissions fetch (:3510-3517) |
| `observed` + `submissions_unchanged=True` | `checked_no_change` | SHA match, prior manifest reused (:3769-3782) |
| `observed` + new accessions | `new_filing` | new accession in fetched Submissions |
| `observed` + `submissions_unchanged=False`, no new accessions | `new_content` | fresh manifest forced: bytes/corrections/removals changed (:3790+) |
| `observed` with neither | error `observation_evidence_required` | fail closed |
| `failed` + `sec_429_exhausted` / `sec_5xx_exhausted` / `sec_timeout_exhausted` / `edgar_index_unavailable` | `source_outage` | SEC did not answer usably |
| `failed` + `response_too_large` | `budget_exhausted` | bounded-ingest cap (`classify_fetch_error`, broad_sec_store.py:559) |
| `failed` + `edgar_index_too_large` | `budget_exhausted` | master.zip caps (:893,917,933) |
| `failed` + `queue_overflow` | `budget_exhausted` | every raise names a budget/cap: "Company Facts byte budget exhausted" (:2925,2929), affected-issuer/run caps (:3243,3250) — deviation from the packet's default bucket, justified from source |
| `failed` + `historical_submissions_budget_exhausted` | `budget_exhausted` | named by the spec |
| `failed` + any other code (18: integrity/binding/store/recovery/universe/index-validity) | `check_failed` | our side cannot attest, not the source's |

Every one of the 25 `REASON_CODES` members is assigned exactly once; the test
suite imports `REASON_CODES` from the source module and pins the mapping total,
so vocabulary drift fails closed.

### Records, publication, freshness

- `record_id = ffobs_ + sha256(canonical JSON [schema, cik-10-digit, accession|None])[:32]`
  — no clock, run id or render id enters it.
- `observe()`: `last_successful_check_at` advances only on `SUCCESSFUL_CHECK_STATES`;
  outage/budget/quiet/failed/not_applicable carry it forward; `checked_at <
  prior.last_checked_at` → `clock_regression`; equal time + equal state → record
  equal to prior (duplicate idempotent); equal time + different state →
  `conflicting_duplicate`; `prior.record_id` mismatch → `record_mismatch`.
- `mark_published()`: kind ∈ {disclosure_bundle, source_snapshot, issuer_manifest};
  requires a successful check (`publish_without_successful_check`); older stamp →
  `publication_regression`; identical republish → equal record.
- `freshness()`: `never_checked` / `stale` / `current` vs `FRESHNESS_BUDGET_SECONDS`;
  `as_of` earlier than the successful check → `clock_order_violation`.

## Freshness F1/F2 (`scripts/build_fundamental_forensics.py`)

- **F1 landed.** `_write_public_summary` (:880) now reuses the prior file's
  `generated_at` verbatim when the prior file carries the same schema and an
  IDENTICAL `public_summary_projection` (`_reusable_public_summary_stamp`, :856-877).
  A rewrite of unchanged counts is byte-identical; the `datetime.now` fallback
  remains only for no-prior-file / changed-counts. Existing page tests
  (no-`generated_at` calls) stay green unchanged.
- **F2 NOT landed — blocked by a forbidden file.** Replacing `_source_generated_at`'s
  wall-clock fallback (:536-549) with `None` requires `compose_state`'s
  downstream to tolerate an absent source clock. It does not:
  `render()` → `_write_state_atomic` (build script :848) validates the blob through
  `decode_state_blob`, which REQUIRES a non-empty string `generated_at`
  (`engine/fundamental_forensics/private_state.py:74-75` — byte-identical/FORBIDDEN
  for this lane). A `None` clock would crash every build whose panels carry no
  `as_of`, i.e. F2's stated precondition ("compose_state already handles an absent
  source clock") is false at the transport envelope. Per the packet's own rule,
  F2 is reverted entirely, F1 kept, no second file touched.

## Follow-on (NOT this lane)

Wiring `observe()`/`mark_published()` into the Wave-2 observation log and FF-1
observation rows is a later commission — this lane changes no receipt/log/manifest
schema string and no `OBSERVATION_OUTCOMES`/`REASON_CODES` value. A follow-up
that wants F2 must first relax `private_state.decode_state_blob`'s clock
requirement (or stamp a sentinel) in its own lane with its own incumbent-suite run.
