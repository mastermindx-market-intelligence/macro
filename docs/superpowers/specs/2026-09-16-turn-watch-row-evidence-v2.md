# TURN WATCH retry evidence v2 — staged source contract

## Outcome and authority boundary

The user and the B1 consumer need one coherent candidate history across harmless rebuilds. Build duration and unrelated sibling rows must not rewrite an unchanged observation’s evidence identity; genuine changes to the observation or its semantic definition must remain visible and conflicting reuse must remain refused.

This is **PREPARATION_ONLY / BUILT_NOT_PROVEN**, under the existing WS:PROPHET-US-V4-RECOVERY and US availability recovery. The current Chairman directed full recovery and complementary, noncolliding work. This change prepares an explicit operator-selectable input version; it does not authorize production cutover, overwrite an incumbent branch, create another episode/state/identity system, or change any rank/size/entry decision.

Controlling law: `agentos/decisions/DEC-PROPHET-B1-CANONICAL-EPISODE-BINDINGS.md`, especially R5, and the original B1 design. Mastermind procedure was pinned at `e8803ba3d3ee928d150d7dcac1a1e2bad2dc0d48`. The existing immutable event core, generation validation, correction path, and single HEAD publication mechanism remain byte-unchanged.

## Proven cause

The real v1 writer hashes the entire public artifact into the private sidecar. That artifact includes `runtime_seconds`. The intake keys an ordinary observation by session plus row, but uses the whole document hash as the event/anchor receipt. Changing runtime from 10 to 11 with identical rows changes the receipt under the same source key and the real reconciler correctly rejects it. The historical production incident also reproduces with exact inputs; restoring only the originally accepted TURN WATCH file in a nonwriting diagnostic copy clears that source conflict. Neither result authorizes a production rollback.

## Design choice

Keep v1’s interpretation and default output exactly as deployed. Add explicit input schema `prophet.candidate_episode_input.turn_watch/v2` through the same sidecar path, producer, canonical intake, and B1 writer. The full document checksum is still validated and exact file provenance still appears in `source_receipts` and immutable generation receipts. No file evidence is discarded or relabelled as an old receipt.

A v2 row’s semantic receipt hashes the canonical schema, data_session, known_at, selection_era, anchor_era, trigger_registry, and complete row. Runtime, public-display container bytes, and sibling rows are not this observation’s semantic facts. Definitions remain binding: changing selection/anchor/trigger metadata under an already-owned row identity still fails the existing immutable-key guard. The v2 envelope is closed, requires canonical session/close timing, and rejects absent/empty semantic definitions even if a malformed producer recomputes a matching document checksum.

Existing row source-ID construction and B1 episode identity are unchanged. The schema version is an existing component of source identity, not a new identity plane. A transition can occur only on a genuinely new source session; the producer refuses an in-place version switch, an in-place downgrade, or backdating the new version into the existing session timeline. A next-session v2 observation with the same structural anchor attaches to the existing episode without altering its v1 event.

The existing builder exposes `--episode-input-schema v2`; its default remains v1. No workflow or dataset-registry current-value change is made. This is an executable staged protocol, NOT a claim the registry has adopted it or production is fixed. Cutover requires the existing V4/integration authority to accept the protocol and registry transition and verify current, coherent source data before using that explicit option.

## Rejected shortcuts

Ignoring the exception, overwriting historic receipts, changing recorded_at, and putting a changing container hash into every ordinary event ID would respectively discard integrity, rewrite history, fabricate chronology, or multiply otherwise unchanged observations. Re-stamping the periodic Yahoo archive is not a freshness repair. None is permitted. A daily-cadence source repair remains a separate producer responsibility.

## Acceptance

The actual producer/intake/core must preserve the ordinary observation on runtime/sibling changes, preserve exact changed-file lineage, refuse semantic-definition drift and checksum tampering, and retain v1 bytes/identities. Temporary full-generation tests must show zero extra events, unchanged old-generation files, unchanged ledger/projection hashes, and a legitimately new receipt-bearing generation when source-container bytes differ. A nonwriting run against the exact previously accepted production generation must reproduce its hashes with zero appended events.

All new tests run in the existing CI executor under a bounded code-gate job. Independent review and concluded current-head checks remain mandatory. Production acceptance additionally requires actual current Yahoo/TURN WATCH inputs, nonwriting B1 reconciliation, one acknowledged canonical publication, and authorized served candidate/plan plus browser evidence. Fixtures and staged CLI availability are not production proof.
