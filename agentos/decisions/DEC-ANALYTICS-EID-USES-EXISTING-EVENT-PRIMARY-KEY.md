---
key: ANALYTICS-EID-USES-EXISTING-EVENT-PRIMARY-KEY
question: 'How do new commercial/activation events become idempotent without building a second dedupe
  store, ledger, or event bus?

  '
answer: 'November source correction: retain DB-minted bigint analytics_events.id and place the envelope-v1
  UUID in the separate analytics_events.eid column with UNIQUE identity. The accepted collector insert
  uses on_conflict=eid with ignore-duplicates; it does not send a client UUID as id. Macro#6858 and Terminal#507
  already supplied the correction and migration record. This supersedes the original UUID-id/primary-key/zero-schema-change
  assertions while retaining the no-second-dedupe-store boundary. Preserve existing legacy/null-eid semantics
  and the accepted replay contract; this record introduces no new legacy UUID mapping, DDL, collector
  change or production replay.'
rationale: The September record mistook the existing bigint identity column for a UUID primary key. The
  accepted correction documents PostgREST 22P02 batch failure from that mismatch and uses a separate unique
  UUID eid while the database retains id authority. Source merges and the historical schema receipt correct
  the factual premise; no fresh production schema inspection or proof of every original idempotency behavior
  is claimed. Idempotent acceptance stays within the existing analytics plane, without another ledger.
alternatives:
- option: A separate dedupe/ledger table keyed by event id
  why_not: 'Second store for the same identity — rejected by the no-rebuild census; it can drift from
    the table it guards and doubles the failure surface.

    '
- option: Time-window heuristic dedupe (drop same-looking events within N seconds)
  why_not: 'Heuristics silently drop real repeat acts and silently keep true duplicates outside the window;
    identity must be explicit, not inferred.

    '
- option: Exactly-once delivery guarantees in the client queue
  why_not: 'Exactly-once at the emitter is a fiction over lossy transports; at-least-once with idempotent
    acceptance is the honest contract.

    '
evidence:
- Macro#6858 merged 5e78f26767de167c1b47c6377bced1c8ce45003f; its source description explicitly preserves
  bigint id and uses eid uuid UNIQUE/on_conflict=eid.
- 'Terminal#507 migration record merged 7ca254722fa1aca8e3195c229e1d0701c01946cc. Historical production
  schema/DDL proof is attributed to that carrier and #6835/comment5601315609, not rerun here.'
- 'Original factual finding and permitted bounded correction: https://github.com/mastermindx-market-intelligence/Macro/pull/6835#issuecomment-5592940939'
- 'Full original decision and Chairman attribution are preserved below; current assigned correction: https://github.com/mastermindx-market-intelligence/Macro/pull/6835#issuecomment-6661414324.'
affects:
- WS:COMMERCIAL-ACTIVATION
- app/main.py
- config/growth_events.yml
confidence: high
reversibility: costly
decided_by: sol
decided_at: 2026-11-05
---

# Explicit correction of the historical EID decision

The key is retained solely for reference continuity. It does not endorse the obsolete primary-key assertion in its name. The active November corrective disposition is by the assigned Sol; the complete original Chairman-attributed September record remains below. This incorporates already-accepted source evidence and authorizes no new DDL, collector work or production replay.

## Source qualification — November 5, 2026

Assigned Sol root `macro-backlog-oldest-first-20261105-c3` qualifies this record under protected
Mastermind `5fbcbffe77a06e41bc590fa09d12a7e2baefb4f7`. The source boundary is the ten existing AgentOS records
on original PR #6835; [the current claim](https://github.com/mastermindx-market-intelligence/Macro/pull/6835#issuecomment-6661414324) transfers no application,
runtime, account, report or Watchlist writer.

The original PR's claim that frozen artifacts were committed under
`research/commercial_activation/` is retracted. The actual dated recovery source is
[receipt 5601315609](https://github.com/mastermindx-market-intelligence/Macro/pull/6835#issuecomment-5601315609): archive
`MMX_COMMERCIAL_ACTIVATION_SOL_BUNDLE_20260903.zip`, 32,868 bytes,
SHA-256 `642a1f27a33d30a7dc9cb076f7e1f8ec0880a5be3b349307fa4500f76628d27e`,
in authenticated Linear MAS-6 attachment `fcdbe167-85d4-4331-9857-b405ca2b0f49`.
That receipt records original-member hashes and authenticated custody, discloses the
unauthenticated 401, and does not claim a complete stored-object hash recomputation.
This qualification reads that published receipt, not the archive or attachment; it
publishes no replacement research payload and claims no fresh attachment availability.

Original policy references to that bundle are historical locators, not claims that this
carrier published those paths. Original source/history/caller/collision, archive-content,
Flow Velocity and production-script refusals remain fenced. No alternate carrier, retained
copy or reconstruction is used to repeat them. Current source merges and dated synthetic
proof remain distinct from the original production canary and full commercial journey.

## Source outcomes and retained proof gaps

| Component | Observed or retained evidence | Meaning for the current continuation |
|---|---|---|
| Macro #6815 | Merged `0007d955278c0456507bb4854eb85ddb41e2874e` | Preserve the existing flow-observation source; no rebuild |
| CA1A #6838 | Merged `d3294b0b974a4b592f68c43c9ab0ba4ad7e5bfe6` | Event-spine source already implemented |
| Collector correction #6858 | Merged `5e78f26767de167c1b47c6377bced1c8ce45003f` | Preserve DB-minted bigint `id`, separate UUID `eid`, `on_conflict=eid` |
| Terminal migration record #507 | Merged `7ca254722fa1aca8e3195c229e1d0701c01946cc` | Historical schema/DDL evidence; no new production read or DDL here |
| Terminal #444, #446 and #435 | Merged `b4fc51d38e966c1b2ee23bfb5a374def8dc35391`, `21e0d51d2c674f7c29360516c38bc859ce86047f`, `ce0d994202b18513b3135b07fa61d2bbfcfdf445` | Retain accepted entitlement/billing composition; no renewed old release train |
| Terminal #445 | Closed/unmerged; receipt 5592940939 identifies its behavior as absorbed into #446 | Do not reopen or commission a duplicate E-4 repair |
| Earlier ordered-report candidate | [5607238737](https://github.com/mastermindx-market-intelligence/Macro/pull/6838#issuecomment-5607238737): finite static review accepted/STOP; historical 69-test author evidence | Reviewed inert proposal; no source adoption or new execution inferred |
| Producer V1 and R2 | [5609711602](https://github.com/mastermindx-market-intelligence/Macro/pull/6838#issuecomment-5609711602): V1 withdrawn; R2 narrow attribution PASS, overall journey HOLD | Preserve the accepted finite review and distinct unresolved rebind/persistence finding |
| Native Chrome evidence | [5610769472](https://github.com/mastermindx-market-intelligence/Macro/pull/6838#issuecomment-5610769472): real DOM/storage/timers, synthetic page, boot suppressed | Store-API evidence, not production UI, deployed-byte or full-journey acceptance |
| Existing ordered-report PR #7258 | OPEN/Draft at `9872bbe611a3a2ce532f03e28ab15735371f38ef` on November 5 | Separate opt-in candidate; its source/adoption/check gates remain with its owner |

The September report, attribution and pending-save/list-rebind findings remain durable
evidence. This record does not re-attest today's deployed product as broken or repaired;
current adoption and real-path proof remain unverified in this source operation. The older
accepted report review does not approve the distinct #7258 implementation automatically.

The original section 16 proof still requires an accepted running build, genuine public
read, three controlled distinct Watchlist adds, exact same-visitor anonymous events, one
replay without a second row, a real report reaching save, analytics-failure noninterference,
client cleanup and retained evidence. Schema readback, source merges and synthetic browser
tests do not supply that acceptance. Recover any existing admissible accepted receipt through
its incumbent owner before proposing another canary; no refused action is retried here.

## Complete original September record — dated evidence

The complete original below is 2,809 UTF-8 bytes, Git blob `3d8b844e5e6b7334f337565e7c62433f1ea944f8`, including its final newline. Its historical attribution, erroneous factual assertions, then-current source/CI/runtime statements and execution directions are preserved for provenance. They are not active instructions or fresh verification; the qualified frontmatter and November disposition above control this record.

``````text
---
key: ANALYTICS-EID-USES-EXISTING-EVENT-PRIMARY-KEY
question: >
  How do new commercial/activation events become idempotent without building a second
  dedupe store, ledger, or event bus?
answer: >
  Every newly implemented registry event carries a required client- or
  authority-derived UUID `eid`, and the collector maps it onto the existing
  analytics_events.id UUID primary key. Retries reuse the same eid; a duplicate primary
  key is ignored (conflict-safe insert) rather than failing the product act; the same
  eid with a different payload is a conflict diagnostic and never overwrites the
  original row. Server-authority events use a deterministic UUID derived from the
  authority event identity plus logical event name. Legacy event wires keep receiving
  server-generated UUIDs until migrated. Malformed or non-UUID ids on new events are
  rejected.
rationale: >
  The existing table already has the needed uniqueness identity in its primary key; a
  parallel dedupe ledger would duplicate state, add a second write path, and still
  require reconciliation against the table. Idempotent delivery is the precondition for
  honest funnel counts (replay on flaky networks must be one row) and for at-least-once
  producers. Using the row id keeps replay semantics queryable with zero schema change.
alternatives:
  - option: A separate dedupe/ledger table keyed by event id
    why_not: >
      Second store for the same identity — rejected by the no-rebuild census; it can
      drift from the table it guards and doubles the failure surface.
  - option: Time-window heuristic dedupe (drop same-looking events within N seconds)
    why_not: >
      Heuristics silently drop real repeat acts and silently keep true duplicates
      outside the window; identity must be explicit, not inferred.
  - option: Exactly-once delivery guarantees in the client queue
    why_not: >
      Exactly-once at the emitter is a fiction over lossy transports; at-least-once with
      idempotent acceptance is the honest contract.
evidence:
  - supabase/migrations/0004_analytics.sql (analytics_events.id UUID primary key already exists)
  - research/commercial_activation/PROJECT_SOL_RETURN_V1_COMMERCIAL_ACTIVATION_20260903.md §6.2-§6.3 (envelope and idempotency contract)
  - research/commercial_activation/CLAUDE_ORCHESTRATOR_HANDOFF_V1_CA1A_EVENT_SPINE_20260903.md §10-§11 (collector mapping and replay behavior)
affects:
  - "WS:COMMERCIAL-ACTIVATION"
  - app/main.py
  - config/growth_events.yml
confidence: high
reversibility: costly
decided_by: chairman
decided_at: 2026-09-04
---

Ratified by direct Chairman grant to session claude/mmx-commercial-activation-03fe73 on
2026-09-04. CA1A implements this for the four early-funnel wires; no other event gains
an eid requirement until its own wave.
``````
