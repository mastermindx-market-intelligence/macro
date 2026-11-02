---
key: FIF-X2-SAVED-VIEW-BINDS-EXPORT-CONTRACT
question: >
  How do FIF saved research views (X2-s) store the analyst's query, where do
  they live, and what happens when the query contract they were saved against
  changes?
answer: >
  A saved view's `request` binds to X0's frozen financial query request
  contract and stores the contract version it was saved against. On load, a
  version mismatch REFUSES with the plain "saved view unavailable" state and
  never repairs or migrates silently. Storage for wave 1 is a device-local
  briefcase key plus a URL permalink (permalink exact on any device; the saved
  LIST is per-device). Cross-device storage (Terminal investigations manifest
  v2) is the named in-scope follow-up X2-b after X2-s lands, with a lossless
  1:1 migration pinned by a test. Notifications (X2-n) are a separate half that
  ships dormant: FIF_SAVED_RESEARCH_ENABLE and ALERT_DRAIN_ENABLE stay OFF
  until an operator gate after V1.
rationale: >
  A saved view promises to reproduce exact filters, policies and cutoffs. A
  silent repair across a contract change would show the analyst a different
  answer under the old name — worse than no answer. Binding to X0's contract
  (rather than a private saved-view schema) means one request vocabulary for
  API, export and saved research.
alternatives:
  - option: Store the raw UI state and re-derive the request on load.
    why_not: A UI refactor would silently change what a saved view means.
  - option: Auto-migrate old saved views to the new contract.
    why_not: Migration is a repair; it can change filters/cutoffs without the analyst seeing it.
  - option: Cross-device storage first.
    why_not: Needs Terminal-side manifest work; device-local + permalink delivers exact reload/back/direct-link now, and X2-b is commissioned, not deferred.
evidence:
  - "Seat rulings R0-R5 frozen 2026-10-12 ~14:3xZ (X2 frozen spec §10), Meta-CEO seat 96dc937a."
  - "X0 #8996 (squash 2ec6b98ad929) and P2 #9011 (squash 3c2ba6fc0aa9) MERGED — the X2-s writer gate (P2 AND X0 landed) is satisfied."
  - "TASK_GRAPH X2: requires_all [P2, X0]; 'restore exact filters/policies/cutoffs; no duplicate scheduler'."
affects:
  - WS:FINANCIAL-INTELLIGENCE-FABRIC
  - engine/fundamental_forensics/query_exports.py
  - templates/watchstore.js
confidence: high
reversibility: costly
decided_by: "seat 96dc937a (FIF Meta-CEO, Chairman commission 2026-10-11)"
decided_at: 2026-10-12
---

# Saved views bind to the export request contract and refuse on mismatch

R2 (notifications subscription) is recorded here only as context. It uses a
designated "Filing Forensics" watchlist created lazily on an explicit user watch
action, and it requires zero Terminal repo edits. The producer reuses the
existing service-client env names; a new secret or env name is a STOP.
