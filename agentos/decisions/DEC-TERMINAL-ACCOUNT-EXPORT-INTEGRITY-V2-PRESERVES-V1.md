---
key: TERMINAL-ACCOUNT-EXPORT-INTEGRITY-V2-PRESERVES-V1
question: >-
  How can owned drawings and alert definitions join the Terminal account artifact
  without silently invalidating existing verified four-collection downloads?
answer: >-
  Keep the existing logical account payload schema and legacy builder shape. A payload
  requesting either new collection uses integrity.v2 with six explicit collection
  entries. Legacy payloads retain their exact four-collection integrity.v1 receipt and
  remain verifiable. Drawing revisions come only from stored collection data.revision;
  alerts have no stored revision and report null. Creation timestamps are not versions.
rationale: >-
  The previously downloaded signed-in JSON and CSV already have independently verified
  checksums, collection counts and read windows. Reusing the receipt version with a
  changed collection map would blur compatibility and completeness. An explicit new
  receipt version binds the added collections while preserving existing evidence.
alternatives:
  - option: Change integrity.v1 to six collections for every payload
    why_not: Existing four-collection receipts would stop verifying unchanged.
  - option: Hash the new rows only in the outer payload
    why_not: Their collection states, physical counts and failed/partial distinction would lack matching entries.
  - option: Use created_at as each drawing and alert revision
    why_not: The live tables have no update/version column; creation time does not change when an alert is rearmed or its condition changes.
evidence:
  - Terminal PR875 merged dd65e73234f2a18b3d9e7ceb5c4bce0f286ac7d9, authenticated JSON/CSV thirteen-check acceptance.
  - Terminal PR883 integrity and raw-reader candidate, draft pending final source review/protected CI/production proof.
  - Read-only live catalog 2026-10-09 SHA2568ec4dc7e7ea2fe22640ce665960479b2f905d2ec2ce09eee19c122cad8119729 confirms public.drawings and public.alerts columns.
  - research/terminal_audit20/TAKEOVER_20261009/release-and-repair-proof.json separates source, fixture, independent review, CI, merge and live acceptance.
affects:
  - WS:TERMINAL-REPAIR-AUDIT20-2026-10
confidence: high
reversibility: costly
decided_by: terminal-audit20-01a10f92 under the assigned autonomous Terminal takeover
decided_at: 2026-10-09
---

The upgraded verifier passed all thirteen checks on the actual prior private JSON and
CSV files without publishing their contents. Tests reject receipt downgrades, grafted
new collections, missing or extra receipt entries, and changed geometry/conditions.
A receipt remains an unkeyed checksum rather than identity or complete-account proof.
Reads remain independent collection windows rather than an atomic account snapshot.

Falsifier: an unchanged prior v1 artifact stops verifying, or a v2 artifact can omit,
miscount or alter a requested new collection while still verifying. Either result
requires correcting this implementation before release and revisiting the format.

So what: existing customer downloads retain their evidence, while new persisted
collections receive explicit state/count/digest coverage without a false whole-archive
claim. This decision grants no migration, private-data publication, release bypass,
notification, producer-unit authority or whole-Audit20 acceptance.
