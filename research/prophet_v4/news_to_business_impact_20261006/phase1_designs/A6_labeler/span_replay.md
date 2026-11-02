# Span replay — the procedure that checks every span before a label is stored

span-replay-v1 (2026-10-12, lane A6_labeler). Implements freeze §7: "the validator checks
every span by replay before a label is stored." Owner basis: `documents.verify_span(span,
segment_text, body_sha256)` re-slices the bytes and raises when the slice does not
reproduce the span's `text_sha256`/locator content (owner module `documents.py`, function
at line 470; module docstring lines 10–22 name the failure mode). The owner states are
`byte_replayed` (UTF-8 byte span we hold, carries `text_sha256`, re-provable offline) and
`address_only` (bytes not held, NO `text_sha256`, explicitly unreplayable). Emitting an
`address_only` span as if it carried a byte receipt is the named defect this procedure
exists to prevent.

## 1. Inputs

Per case: the full source text as sent in the packet (one UTF-8 byte string), the case's
recorded `source_sha256`, and each critical field's span from the `label_return.v1`:
`{text_sha256, segment_index, byte_start, byte_end, excerpt}`.

## 2. Procedure (per span, in order; first failure wins)

1. **Case hash tie (V_SHA_TIE).** `sha256(source_text_bytes)` must equal the recorded
   `source_sha256`, and each span's `text_sha256` must equal it too. (The stored contract
   additionally ties any numeral inside a claimed quote to the excerpt — freeze §3, V_SHA_TIE
   "+ numeral-in-quote"; the numeric fields' values must be derivable from the excerpt.)
2. **Byte-range validity.** `byte_start ≥ 0`, `byte_end ≥ 1`, `byte_end > byte_start`,
   `byte_end ≤ len(source_text_bytes)`, `segment_index ≥ 0`. Slices are 0-indexed,
   end-exclusive over UTF-8 bytes, exactly the owner's locator convention
   (`locator_text_span` required keys `span_start_byte`/`span_end_byte`).
3. **Byte-for-byte reproduction.** `source_text_bytes[byte_start:byte_end]` decoded as UTF-8
   must equal `excerpt` exactly — no normalisation, no whitespace folding, no Unicode
   NFC/NFKC folding, no case folding, no ellipsis. A span that reproduces only after any
   such transform FAILS.
4. **Segment containment.** If the packet supplies a segment table, the span must lie fully
   inside the segment named by `segment_index`.
5. **Instruction scan (G5).** The excerpt is scanned for the injection not-patterns of
   `$defs/text_safe` in the frozen schema (e.g. "ignore previous", "system prompt",
   scheme-style URLs). A hit does not fail the replay — the bytes reproduce — but the field
   is marked `unevidenced` for evidence purposes and the case is recorded as an injection
   finding (`notes.kind: injection_attempt`, plus quarantine handling outside the
   publishable templates, freeze §4.1 D17).
6. **Verdict recorded** per span: `replayed` or a rejection reason (§3).

After ALL spans of a case replay: the storage layer mints the owner `source_span.v1`
payloads (12-key, `receipt_state: byte_replayed` with the 7-key `receipt`,
`evidence_span.claimed_quote = excerpt`) exactly as `documents.py SourceSpan` emits them
(freeze §4.1 D13), then projects per R1/R2 (owner `display_excerpt` nulled when it would
fail `text_safe` or exceed 500 chars). `address_only` stays limited to `table_cell` /
`slide_region` locators and is never upgraded silently to `byte_replayed` (freeze §4.1 F2).
A span whose locator key set is not one of the three closed locators is rejected at the
boundary with `locator_key_not_in_contract` (ruling R4) — never stripped.

## 3. What is rejected, and the reason vocabulary (closed)

| reason | meaning |
|---|---|
| `source_sha_mismatch` | step 1 failed: the text hashed is not the text on the case, or the span names another text |
| `byte_range_invalid` | step 2 failed: negative/inverted/out-of-range offsets |
| `excerpt_mismatch` | step 3 failed: the slice does not reproduce the excerpt byte-for-byte |
| `segment_violation` | step 4 failed: the span crosses the named segment's boundary |
| `injection_pattern_in_excerpt` | step 5 hit: reproduced, but quarantined for instruction content |

## 4. How failures are reported

Per case, one replay report (machine-readable row, kept in the round's accounting):

```
{"case_id": "...", "template": "...", "n_spans_checked": 12, "n_replayed": 12,
 "n_failed": 0, "failures": []}
```

with `failures: [{"field": "<critical field path>", "reason": "<closed reason>",
"detail": "<=240 chars>"}]`.

Rules:
- A failed span makes that field `unevidenced` and the case NOT stored. The case is
  re-labeled as a fresh draft (the failed return is kept verbatim in provenance; it is
  never edited, offset-shifted or auto-repaired).
- Replay failures are counted, never silently dropped (masterplan §11 accounting;
  `n_replays_failed` appears in the agreement report even when zero).
- Replay never consults anything but the case's own source text bytes: no network, no
  re-fetch, no clock (Phase 0 note, freeze §10: replay against bodies awaits the Phase 1
  document fetch through the allowlisted owner).
- A `replayed` verdict is storage-eligibility, not truth: it proves the bytes were cited
  accurately, nothing else (masterplan §3.5).
