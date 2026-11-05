# Retained Brain context receipts

Brain already persists user and assistant turns in `brain_threads` and
`brain_messages`. Its in-process run buffer expires after thirty minutes and is
lost on API restart. Before this change, the compiler receipt was only returned
on the response/SSE wire, so durable history lost the exact request's context
resolution even when it retained the answer.

The six native, instant and deep assistant-write sites in `brain_gateway.py`
now add `meta.retained_context` to the same existing assistant row. This field
contains a `brain.retained_context.v1` record and the exact server-generated
`ai_context_receipt.v1`. The original system-event metadata is preserved.
The existing message timestamp supplies the storage clock. No table, background
writer, request, provider call, retry mechanism or schema migration is added.

Each request retains its own receipt, including its request identity, effective
context, precedence, exclusions and limitations. Equal context revisions do not
deduplicate different requests. The compiler, its v1 security semantics, pin
owner and response protocol are unchanged. Saved inquiry subjects do not enter
this path or become pins.

The copied receipt is capped at 65,536 UTF-8 bytes. A malformed, unserializable or
oversized receipt records `status: unavailable` with a bounded reason and leaves
the answer eligible for normal best-effort persistence. No receipt is truncated
and reported as complete. The status `retained` describes metadata included in
the row; the existing store's best-effort behavior is not a new durable-write ACK.

## Scope and access

This is the G6 context-retention foundation, not a complete research artifact.
`scope: context_resolution_only` and `used_inputs_status: not_recorded` are
explicit. Offered/resolved context does not prove which evidence the model used.
No raw request context, source document bytes, provider reasoning, new permission
claim, or hidden provider provenance is copied by this change.

Existing thread/history readers continue selecting their existing fields and do
not expose metadata. No artifact read, export or share route is introduced.
The full G6 reader must bind an exact Investigation revision, record owner
vintages and actual used/excluded inputs, report model/input limitations, and
recheck current source/derived rights before exposing any result. It must open
old lawful outputs without generation and compare input manifests before prose.
Those integration and live-acceptance obligations remain open.

## Validation and release

Tests compare the exact response/SSE receipt with the stored assistant metadata
on native, instant and deep paths, including provider-free native answers.
They cover request separation, copy isolation, malformed/cyclic metadata and
UTF-8 size refusal. The existing compiler, gateway, thread, run, instant-lane
and exact-source suites protect the incumbent behavior. The test file runs in
the existing `unrun-brain-gateway` CI owner.

Review and production acceptance remain separate. The runtime change is wholly
in `brain_gateway.py`, already covered by the Macro API restart selector.
Rollback removes the additive write wrapper and leaves prior message metadata
and all retained user history intact; it requires no destructive data repair.
