# Exact institutional holding research

The existing Filing Forensics desk provides **Read a reported holding**, opened directly at `fundamental_forensics.html#reported-holding`. Choose the retained March/June Custos example (or edit its exact filing selection), then click **Read reported holding**. The first-party client obtains the existing browser session through `MDXAuth.client()` and sends it only in the Authorization header; no token is exported, stored or placed in a URL. This disclosure is independent of the separate financial-statement dataset state.

The paid API performs a bounded read of one owner-verified reported holding:

`POST /api/forensics/v1/institutional/reported-holding`

Use the existing Supabase bearer session and `site_full` entitlement. This adds no auth, account, claim, database or catalog writer. The public Ownership Intelligence Desk and its aggregate-only publication contract are unchanged.

```json
{
  "filer_cik": "0001904423",
  "report_period": "2026-06-30",
  "accession": "0001904423-26-000004",
  "infotable_sk": "4611686018427387905",
  "decision_cutoff": "2026-08-27T09:22:23.700168Z",
  "generation_id": "i13fgen_9ae95a9de85cc0ed426b09cd7db443210c8cdc5d9178aaad5859c3f8a57527cd"
}
```

The row key is canonical decimal **text**, preserving native int64 identity through browser clients. The owner receives its exact Python integer. Omit `generation_id` to use the native current pointer; a historical comparison should pin the original generation. Pinned reads expose `pointer.state=not_read`, `current_generation_id=null` and `superseded=null`; they make no claim about the current pointer. A current generation published after the decision cutoff remains unavailable.

The consumer calls `project_reported_holding` through the existing dedicated institutional store. It verifies the content-addressed generation manifest, full filing lineage/receipt membership, the selected accession holding bucket, reporting relationships and raw receipt using owner operations. The context uses `institutional_13f.reported_holding_accession_context.v1` and explicitly identifies `accession_bucket` verification; it never claims the other 63 holding buckets were read or verified. The default full-generation `project_reported_holding` behavior is unchanged. It then composes verified **reporting-entity** semantics. CUSIP remains reported identity; economic vehicle/class/complex and strategy remain unresolved. No caller-supplied owner payload, verifier registry, ticker inference, canonical alias publication, recipe or positive K2C/K3E activation is accepted. Original source/observation clocks remain distinct.

`AVAILABLE_UNQUALIFIED` contains delayed reported context. `UNAVAILABLE` and `REFUSED` retain the owner's typed reasons and are never rendered as zero ownership. Every response is private/no-store, varies on Authorization and forbids indexing. Auth/entitlement denial precedes request-body and owner reads. Backend/configuration failures return a generic private 503 without storage keys or credentials. JSON bodies are limited to 4096 bytes and responses to 64 KiB; duplicate/extra fields and imprecise numeric row keys are rejected.

Interactive reads admit one owner operation per process, at most 64 MiB aggregate source bytes and 16 source-object reads. The selected owner scope verifies five artifacts (full filings, one holding bucket, manager relationships, source receipts and coverage), bounds each selected artifact to 100,000 declared rows, and bounds decoded Parquet row-group bytes to 128 MiB before decoding. Global catalog counts do not falsely exclude an otherwise small selected scope. The 30 second budget is cooperative between operations; it does not cancel an in-flight owner network read. The slot stays occupied until that read returns. Selections exceeding these bounds are unavailable on this interactive lane and require a separately bounded owner operation; they are not partially exposed or counted as absent.

Production uses only the pre-existing `INSTITUTIONAL_13F_R2_ENDPOINT`, `INSTITUTIONAL_13F_R2_ACCESS_KEY_ID`, `INSTITUTIONAL_13F_R2_SECRET_ACCESS_KEY`, and `INSTITUTIONAL_13F_R2_BUCKET` namespace. Missing provisioning is unavailable. There is no generic R2, public bucket or filesystem fallback. This source change does not provision credentials or change their scope. API installation and authenticated real-user execution must be verified separately from source/CI; local tests exercise the actual auth dependency wrapper and native catalog projection with an in-test owner store.

The client shows delayed reported context and unresolved semantics, with original clocks and source receipts in a details disclosure. Selecting another filing, editing inputs or changing authentication clears the previous private result and cancels its request. Anonymous/denied/absent/refused/unavailable states never become zero ownership. Local browser/Node fixtures are engineering proof only; the final real entitled product invocation and installed source must be qualified separately.
