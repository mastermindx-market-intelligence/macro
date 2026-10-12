# SNI twin record contract (R1-gated DRAFT)

This document is an R1-gated DRAFT of the Single-Name Intelligence (SNI) reference-twin record contract. It specifies three clocks, owner-key plus digest admission, correction lineage that never rewrites older generations, then-known views, and hash-chained append-only write acks. It is not a product, not an owner integration, and not a source of minted identity ids. Every authority flag stays false.

The executable contract lives in `contracts/single_name_intelligence/twin_record.v1.schema.json` and `research/single_name_intelligence/twin/sni_twin.py`. This module CONSUMES owner-supplied payload, owner_key, owner_digest and clocks. It does not fork or re-implement Data OS identity, Company Event/Earnings, FIF, Capital Structure, Stock Identity, Options, Research Vault, or qledger/Evaluation.

## Purpose

Hold one immutable generation of a reference twin so Alibaba/Tencent-style product lanes, and later US/Mag-7 generalization, can share a record before any ranker, gate, sizer, signal, escalation or trade path exists. `twin_key` is an opaque caller-supplied string. Unknown identity stays UNRESOLVED / null at the caller; this contract never constructs HK/US issuer or security identifiers from a ticker, name, code or CIK.

## The three clocks

A record carries three clocks, ordered as follows.

1. `clocks.economic_period` — the period or instant the fact is about (`kind` is `"period"` or `"instant"`; `start` is a date; `end` is a date or null). When `end` is present it must be `>= start`.
2. `clocks.owner_known_at_utc` — when the owner system knew the fact (filing time, vendor as-of, owner watermark).
3. `clocks.sni_published_at_utc` — when SNI published this generation of the twin record.

Invariant that orders them: `owner_known_at_utc <= sni_published_at_utc` (A08, refusal `CLOCK_ORDER`). A fact cannot be published by SNI before its owner knew it. Equal timestamps are allowed. The economic period is the fact's own span; a correction keeps that same economic period and publishes a new generation on a later SNI clock.

## Worked example (synthetic earnings fact)

Synthetic `twin_key` `synth.twin.earnings-q`. The economic fact is FY-Q2 of a synthetic issuer, period `2025-04-01` through `2025-06-30`. The owner (Company Event/Earnings analogue) knew the filing at `2025-08-14T12:00:00Z`. SNI published generation 1 at `2025-08-14T16:00:00Z`.

A restatement arrives. Generation 2 is a NEW line: same `twin_key`, same `economic_period` (`2025-04-01`/`2025-06-30`), new owner payload and `owner_digest`, `owner_known_at_utc` at the restatement filing time, `sni_published_at_utc` later still (for example `2025-08-16T09:00:00Z`). `generation` is 2 and `supersedes` is generation 1's `record_id`. Generation 1's JSONL bytes stay unchanged.

## Admission (A15)

`OwnerRegistry` maps `owner_key` to `{"allowed": bool}`. `admit(owner_key, payload, owner_digest)`:

- unknown `owner_key` → `UNKNOWN_OWNER`
- registered but `allowed` is false → `OWNER_NOT_ALLOWED`
- `sha256_text(canonical_json(payload)) != owner_digest` → `DIGEST_MISMATCH`

`canonical_json` is `json.dumps(..., sort_keys=True, separators=(",", ":"))` plus a trailing newline. `owner_digest` is the digest of that text as the OWNER computed it. SNI does not re-derive owner facts.

## Lineage (A16, A05)

Generation 1 has `supersedes` null. A correction is a new record: `generation = prev.generation + 1` and `supersedes = prev.record_id`. `correction.reason` is required (`CORRECTION_REASON_REQUIRED`). Older generations are never rewritten (A16). Two successive corrections yield generation 3; `history` is three lines in file order; `latest` is generation 3 (A05). `verify_chain` reports a generation gap when gen n+1 does not supersede the `record_id` of gen n for that `twin_key`, and reports immutability when a record's bytes differ from the first time that `record_id` appeared.

## Then-known views (A07)

`view_as_of(path, twin_key, as_of_utc)` returns the highest-generation record whose `sni_published_at_utc <= as_of_utc`. Post-cutoff facts cannot enter a then-known view. An as-of before generation 1's publish time returns None. Historical facts known only after a date are never treated as known on that date.

## Write acks and EFFECT_UNKNOWN (A17)

`TwinStore` is an append-only JSONL file. `append` sets `prev_hash` to the last line's `row_hash` (or null), sets `row_hash` to `sha256_text(canonical_json(record without row_hash))`, writes one line, and fsyncs.

Callers write through `write_with_ack`. On success it returns `("ACKED", row_hash)`. If the write raises after the line may have been written (including an injectable `_after_write_hook` that raises), it returns `("EFFECT_UNKNOWN", None)` and does not retry. `reconcile(record_id)` re-reads the same carrier and returns `PRESENT` or `ABSENT`. Blind retry is refused. `verify_chain` reports `hash mismatch` when a line's `row_hash` does not match its bytes, and `prev_hash mismatch` when the chain is broken.

## Refusal code table

| Code | When | A-case |
|---|---|---|
| `UNKNOWN_OWNER` | `owner_key` is not in the registry | A15 |
| `OWNER_NOT_ALLOWED` | registry entry exists and `allowed` is false | A15 |
| `DIGEST_MISMATCH` | owner digest of canonical payload text does not match | A15 |
| `CLOCK_ORDER` | `owner_known_at_utc` is after `sni_published_at_utc` | A08 |
| `PERIOD_ORDER` | `economic_period.end` is present and is before `start` | A08 |
| `CORRECTION_REASON_REQUIRED` | `prev` is given and `correction_reason` is missing | A16 |
| `AUTHORITY_KEY_IN_PAYLOAD` | payload contains any of the six authority flag keys | fence |
| `AUTHORITY_FLAG_TRUE` | a caller sets any of the six authority flags true | fence |

Unestimable work ABSTAINS with a named reason from this table. There is no default 50/50. Residuals and stress statistics, when an owner supplies them in payload, stay DESCRIPTIVE and are never treated as causal news impact.

## What this is not

This is an R1-gated DRAFT pushed to a lane branch. It is not a product rendering, not a live owner integration, and not a commissioned US/Mag-7 surface. It mints no canonical identity ids. It does not feed, and must not be described as feeding, a ranker, gate, sizer, signal, escalation or trade path. `rank_authority`, `gate_authority`, `size_authority`, `signal_authority`, `escalation_authority` and `trade_authority` are const false on every record.
