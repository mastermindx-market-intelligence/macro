# SNI identity relationship contract (R1-gated DRAFT)

This document is an R1-gated DRAFT of the Single-Name Intelligence (SNI) identity relationship contract. It mints no ids. Canonical issuer and security identifiers remain owned by Stock Identity / Data OS; this draft only consumes caller-supplied opaque strings and owner-issued receipts. It is not registered, it is not a product surface, and it does not feed a ranker, gate, sizer, signal, escalation, or trade path. Every authority flag in this draft is false (`rank_authority`, `gate_authority`, `size_authority`, `signal_authority`, `escalation_authority`, `trade_authority`). The seat holds this lane until the Chairman's ruling on #6613.

Commission 8659. Module: `research/single_name_intelligence/identity/sni_identity_relations.py`. Tests: `tests/test_sni_identity_relations.py`.

## Purpose

Describe how listing counters of one economic name relate to each other (ADS vs ordinary, dual HKD/RMB counters, aliases) without constructing a canonical issuer id or security id. Unknown identity stays unresolved (null). A relation is a dated, receipt-backed statement about two `CounterRef` endpoints. SNI stores the statement; it does not become an identity authority.

## Owners

Stock Identity and Data OS own issuer ids and security ids. They mint, correct, and expire those ids. SNI consumes the values those owners supply on a receipt (`source_owner`, `receipt_id`, `digest`, validity window). Profile-local keys such as `hkd_9988` are file keys, never identity ids.

This draft does not re-implement Data OS identity, Company Event/Earnings, FIF, Capital Structure, Stock Identity, Options, Research Vault, or qledger/Evaluation. Callers that need an issuer id for an id-dependent operation must pass one; `require_issuer_id(None, op=...)` refuses. Nothing here substitutes a derived id.

## Relation kinds

| Kind | Direction | Endpoints | Ratio |
| --- | --- | --- | --- |
| `ADS_OF` | directed (`a` is the ADS, `b` is the ordinary) | different `venue_mic` | required, `Fraction > 0` |
| `DUAL_COUNTER_OF` | symmetric | same `venue_mic`, different `currency` | forbidden |
| `SAME_ISSUER_GROUP` | symmetric | no venue/currency bind rule in this draft | forbidden |
| `ALIAS_OF` | directed | same `venue_mic`, same `currency` | forbidden |

`record_id` is `sha256` of canonical JSON `{kind, endpoints, ratio, receipt_id, valid_from}`. For symmetric kinds, `endpoints` is `sorted([a.key(), b.key()])`, so `record_id(a,b) == record_id(b,a)`. For directed kinds, `endpoints` keeps `[a.key(), b.key()]` in order.

`CounterRef` equality is the full tuple `(venue_mic, local_code, currency, security_id, security_id_owner)`. An ADS counter and an ordinary counter are never equal. `local_code` is not normalized: `"0700"` is not `"700"`.

## Refusal codes

| Code | A-case | When it fires |
| --- | --- | --- |
| `SELF_RELATION` | A01 | `a == b` (full-tuple equality). Distinct ADS and ordinary counters are two endpoints, never collapsed. |
| `CROSS_BIND_VENUE` | A04 | `ALIAS_OF` with different venues; `ADS_OF` with the same venue; `DUAL_COUNTER_OF` with different venues. |
| `CROSS_BIND_CURRENCY` | A04 | `ALIAS_OF` with different currencies; `DUAL_COUNTER_OF` with the same currency. |
| `PADDING_MISMATCH` | A04 | `ALIAS_OF` where codes differ only by leading zeros, unless `receipt.source_owner == "stock_identity"` (the only path that may equate padded variants; ids stay whatever the receipt carries). |
| `RATIO_REQUIRED` | A01 (ADS shape) | `ADS_OF` missing a `Fraction > 0` ratio. |
| `RATIO_FORBIDDEN` | A01 (ADS shape) | ratio present on a non-`ADS_OF` kind. |
| `RECEIPT_EXPIRED` | A05 | `receipt.expires_at_utc < valid_from_utc`. |
| `BAD_DIGEST` | A05 | receipt digest is not 64 lowercase hex, or JSONL `record_id` does not match the canonical hash. |
| `CONFLICT` | A05 | an active relation of the same kind over the same endpoint set exists with a different ratio or a different receipt digest. |
| `DUPLICATE` | A06 | the same `record_id` is added again (count-once). |
| `ISSUER_ID_REQUIRED` | A03 | `require_issuer_id(None, op=...)`; the message names `op`. Null stays null. |
| `AUTHORITY_FORBIDDEN` | (program law) | a caller sets any authority flag true. |
| `UNKNOWN_RECORD` / `ALREADY_SUPERSEDED` | A05 | supersede target missing or already superseded. |

A02 is a positive path: dual-counter relations build with `security_id=None` and the serialized record contains no constructed identity prefix.

## Supersession and expiry

The registry is append-only. `add` validates and stores a row. `supersede(old_record_id, new_rel, reason=...)` keeps the old row, sets `superseded_by` to the new `record_id`, and appends the new row. The old `Relation` payload is never rewritten.

`active(as_of_utc)` returns relations that are not superseded, whose `valid_from_utc <= as_of`, whose `valid_to_utc` has not passed (`valid_to_utc <= as_of` is passed), and whose receipt has not expired (`expires_at_utc <= as_of` is expired). `history(endpoint_key)` returns every stored relation touching that counter key, including superseded and expired rows.

`to_jsonl` / `from_jsonl` round-trip the registry. JSONL order is sorted by `record_id`, so two input orders of the same relations serialize identically (A06).

## Worked examples of shape

These examples use the counters named in the Alibaba and Tencent coverage profiles as EXAMPLES OF SHAPE. No identifier here is canonical. Fixtures in tests are synthetic; `security_id` is left null.

1. **ADS_OF, directed.** NYSE counter `BABA` (`venue_mic=XNYS`, `local_code=BABA`, `currency=USD`) is `ADS_OF` HKEX ordinary `9988` (`venue_mic=XHKG`, `local_code=09988`, `currency=HKD`) with ratio `1/8` (one ADS per eight ordinary shares), valid from a receipt issued by Stock Identity. The two `CounterRef` values are unequal. The ratio is a receipt-backed descriptive fact, not a Data OS field this module invents.

2. **DUAL_COUNTER_OF, symmetric.** HKEX `9988` HKD (`local_code=09988`, `currency=HKD`) and HKEX `89988` RMB (`local_code=89988`, `currency=CNH`) are dual counters of one economic security on the same venue with different currencies. `record_id` is the same either endpoint order. Both `security_id` values may be null; the relation still records.

3. **DUAL_COUNTER_OF, symmetric.** HKEX `700` HKD (`local_code=00700`, `currency=HKD`) and HKEX `80700` RMB (`local_code=80700`, `currency=CNH`) are the Tencent-shape dual pair. The Tencent issuer id on the Data OS issuer axis is unresolved in the coverage profile; this draft leaves it unresolved. `require_issuer_id(None, op="group_issuers")` refuses rather than guessing an id.

4. **ALIAS_OF padding.** `"0700"` and `"700"` on the same venue and currency differ only by leading zeros. Without a `stock_identity` receipt the bind is `PADDING_MISMATCH`. With such a receipt the alias may be stored; the module still does not rewrite either `local_code` or invent a security id.

## What this draft is not

This draft is not registered research. It is R1-gated: pushed to a lane branch, no pull request from this lane. It is not a product surface. It does not mint, look up, or correct canonical ids. It does not pool dual counters as extra issuers. It does not treat a residual, a basis, or a dual-counter quote as news impact or as a default 50/50. It does not feed rank, gate, size, signal, escalation, or trade. The Chairman's ruling on #6613 decides whether a later registered contract replaces this draft.
