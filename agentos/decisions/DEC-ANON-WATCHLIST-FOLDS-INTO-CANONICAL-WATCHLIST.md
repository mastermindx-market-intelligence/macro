---
key: ANON-WATCHLIST-FOLDS-INTO-CANONICAL-WATCHLIST
question: 'Where does anonymous personal state (the pre-account local Watchlist) go after signup?

  '
answer: 'The anonymous local Watchlist folds idempotently into the existing canonical watchlists/watchlist_symbols
  plane after verified account creation. Fold is a set union; canonical server membership is the delete
  authority; no folded event or "saved" UI state may precede the canonical readback acknowledgement. The
  fold never creates a second cloud store and never writes Portfolio exposure.

  '
rationale: Historical policy rationale recorded on 2026-09-04, retained as dated reasoning. Its then-current
  wizard, owner census, product and dependency observations are not freshly re-attested in November. The
  local list is pre-account intent, and canonical account Watchlist truth already exists with a settled
  separate-truth ruling (DEC:MARKET-OS-WATCHLIST-PORTFOLIO-SEPARATE-TRUTH-UNIFIED-EXPERIENCE lineage).
  Preserving the visitor's list through signup is the entire promise of "Save My Market"; losing it or
  parking it in a parallel store would either break the promise or mint a second truth plane. Portfolio
  is ownership, Watchlist is attention — folding attention into portfolio_positions would corrupt risk
  calculations.
alternatives:
- option: Keep the anonymous list in localStorage after signup, merged only at read time
  why_not: 'Read-time merge makes membership device-local and unqueryable; retention and activation measurement
    need canonical membership, and cross-device return would silently show different lists.

    '
- option: Create a dedicated "saved insights" cloud table for folded anonymous state
  why_not: 'Explicitly rejected by the no-rebuild census — a second saved-state store parallel to Watchlists
    is a second truth plane requiring perpetual reconciliation.

    '
- option: Discard the anonymous list at signup
  why_not: 'Destroys the personal act that motivated registration; the journey''s conversion mechanism
    is preservation of personally meaningful state.

    '
evidence:
- 'Historical September supporting evidence, not current verification or a fresh publication claim: research/commercial_activation/PROJECT_SOL_RETURN_V1_COMMERCIAL_ACTIVATION_20260903.md
  §5.3 (fold conflict/partial-failure state law), §8 (no-rebuild boundary)'
- 'Historical September supporting evidence, not current verification or a fresh publication claim: agentos/decisions/DEC-MARKET-OS-WATCHLIST-PORTFOLIO-SEPARATE-TRUTH-UNIFIED-EXPERIENCE.md
  (separate-truth ruling this composes with)'
- 'Historical September supporting evidence, not current verification or a fresh publication claim: supabase/migrations/0004_analytics.sql
  and existing watchlists/watchlist_symbols schema (canonical plane already live)'
- 'November source qualification: https://github.com/mastermindx-market-intelligence/Macro/pull/6835#issuecomment-6661414324;
  original bundle custody and limits: https://github.com/mastermindx-market-intelligence/Macro/pull/6835#issuecomment-5601315609.
  This records repair has not retrieved its payload.'
- 'Current source outcomes: Macro#6838/#6858 merged; Terminal#444/#446/#435/#507 merged; Terminal#445
  closed/unmerged. Source release does not prove the original production journey.'
affects:
- WS:COMMERCIAL-ACTIVATION
- WS:MARKET-OS
confidence: high
reversibility: costly
decided_by: chairman
decided_at: 2026-09-04
---

# Retained commercial policy

The original Chairman policy, decision date, alternatives and authority boundaries remain. November annotations qualify its supporting historical observations; they do not redesign signup, Watchlist, billing or measurement. The third-symbol prompt, where applicable, remains a preregistered product hypothesis rather than a measured success.

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

## Complete original September record — dated evidence

The complete original below is 2,742 UTF-8 bytes, Git blob `c27f82dbfe6c7e678f314bb583efe79dd55ee36f`, including its final newline. Its historical attribution, erroneous factual assertions, then-current source/CI/runtime statements and execution directions are preserved for provenance. They are not active instructions or fresh verification; the qualified frontmatter and November disposition above control this record.

``````text
---
key: ANON-WATCHLIST-FOLDS-INTO-CANONICAL-WATCHLIST
question: >
  Where does anonymous personal state (the pre-account local Watchlist) go after signup?
answer: >
  The anonymous local Watchlist folds idempotently into the existing canonical
  watchlists/watchlist_symbols plane after verified account creation. Fold is a set
  union; canonical server membership is the delete authority; no folded event or "saved"
  UI state may precede the canonical readback acknowledgement. The fold never creates a
  second cloud store and never writes Portfolio exposure.
rationale: >
  The local list is pre-account intent, and canonical account Watchlist truth already
  exists with a settled separate-truth ruling
  (DEC:MARKET-OS-WATCHLIST-PORTFOLIO-SEPARATE-TRUTH-UNIFIED-EXPERIENCE lineage).
  Preserving the visitor's list through signup is the entire promise of "Save My
  Market"; losing it or parking it in a parallel store would either break the promise or
  mint a second truth plane. Portfolio is ownership, Watchlist is attention — folding
  attention into portfolio_positions would corrupt risk calculations.
alternatives:
  - option: Keep the anonymous list in localStorage after signup, merged only at read time
    why_not: >
      Read-time merge makes membership device-local and unqueryable; retention and
      activation measurement need canonical membership, and cross-device return would
      silently show different lists.
  - option: Create a dedicated "saved insights" cloud table for folded anonymous state
    why_not: >
      Explicitly rejected by the no-rebuild census — a second saved-state store parallel
      to Watchlists is a second truth plane requiring perpetual reconciliation.
  - option: Discard the anonymous list at signup
    why_not: >
      Destroys the personal act that motivated registration; the journey's conversion
      mechanism is preservation of personally meaningful state.
evidence:
  - research/commercial_activation/PROJECT_SOL_RETURN_V1_COMMERCIAL_ACTIVATION_20260903.md §5.3 (fold conflict/partial-failure state law), §8 (no-rebuild boundary)
  - agentos/decisions/DEC-MARKET-OS-WATCHLIST-PORTFOLIO-SEPARATE-TRUTH-UNIFIED-EXPERIENCE.md (separate-truth ruling this composes with)
  - supabase/migrations/0004_analytics.sql and existing watchlists/watchlist_symbols schema (canonical plane already live)
affects:
  - "WS:COMMERCIAL-ACTIVATION"
  - "WS:MARKET-OS"
confidence: high
reversibility: costly
decided_by: chairman
decided_at: 2026-09-04
---

Ratified by direct Chairman grant to session claude/mmx-commercial-activation-03fe73 on
2026-09-04. Fold implementation is CA1B scope; CA1A only measures the anonymous side
(storage=local events) and must not implement any fold.
``````
