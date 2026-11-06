---
key: OPTIONS-CONTEXT-AUDIT-PREREG-V2
title: Options Context Audit preregistration v2
objective: >
  Replace the frozen v1 Options Context Audit with a new preregistration whose
  future NYSE boundary can represent the live owner corpus. The ~25,000-row /
  48 MiB figures previously reviewed are already exceeded by the live corpus
  (29,509 episode rows; outcomes_h60 50,889,496 B; charter capacity refresh
  2026-10-11), so v2 sizes its bound from live measurement with stated headroom.
  Keep the v1 4,096 refusal and the production-records MAX_SOURCE_ROWS=25_000
  refusal honest until that successor exists. Do not window, evict, or truncate
  episode owners.
status: active
program: options-intelligence
repos: [macro]
owner: coo-fable
class: adjudication
blast_radius: reversible
ambiguity: scoped
owns_paths:
  - engine/options_market_memory_context.py
  - engine/options_market_memory_receipt_store.py
  - scripts/audit_options_market_memory_context.py
  - app/deploy/macro-market-memory-options-context-audit.service
  - app/deploy/macro-market-memory-options-context-audit.timer
waves:
  - id: V2-PREREG-CHARTER
    title: Charter the successor preregistration; do not implement it here
    status: done
    pr: [7711]
    next_action: >
      None for the charter: PR #7711 (MERGED 2026-10-11 as d1b93722ec41) ships
      research/options_estate/OPTIONS_CONTEXT_AUDIT_PREREG_V2_CHARTER_2026-09-22.md
      including the capacity refresh at current main. The successor
      implementation child is still separately keyed and still gated on Sol
      accepting the preregistration.
next_action: >
  Sol acceptance of the preregistration charter (PR #7711, d1b93722ec41) is the
  implementation gate. The v2 bound must be sized from the live measurement in the
  charter's capacity refresh (29,509 episode rows / outcomes_h60 50,889,496 B on
  2026-10-11, growing ~2,200-5,600 rows per session) with stated headroom, not to
  the historical ~25k / 48 MiB figures. Until an accepted v2 exists, the production-
  records capture stays fail-closed at MAX_SOURCE_ROWS=25_000
  (DEC:PRODUCTION-RECORDS-ROW-BOUND-STAYS-FAIL-CLOSED-UNTIL-PREREG-V2). Implementation
  requires a separately keyed later child. Do not widen `_MAX_REFERENCES`, edit v1 in
  place, or recouple this owner into trusted-context publication.
decisions:
  - "DEC:W2C-V1-CONTEXT-OWNER-DECOUPLED-FROM-OPTIONS-AUDIT"
  - "DEC:PRODUCTION-RECORDS-ROW-BOUND-STAYS-FAIL-CLOSED-UNTIL-PREREG-V2"
discoveries:
  - "DSC:OPTIONS-CONTEXT-AUDIT-V1-TIMEOUT-PRECEDES-4096-REFUSAL"
do_not_redo:
  - Do not implement preregistration v2 inside a W2C timer-recovery PR.
  - Do not raise TimeoutStartSec or CPUQuota as a substitute for v2.
  - Do not widen `_MAX_REFERENCES` or the pinned receipt-store reference ceiling.
  - Do not window, evict, rotate, or truncate episode owners (DNR:KILL-OPTIONS-CONTEXT-AUDIT-OWNER-EVICTION).
  - Do not swallow the audit exception or mark the audit healthy.
  - Do not create a shadow validator with a larger cap.
landmines:
  - The v1 engine is byte-pinned by sparse_selector_preregistration_receipt_v1.json.
  - Production construction is O(N) over the complete owner corpus and currently dies on TimeoutStartSec=180 / CPUQuota=50% before the deterministic 4,096 refusal.
  - Trusted Market Memory context is a different owner. Recoupling this audit into macro-market-memory-context.service re-breaks W2C v1 timer arming.
artifacts:
  - research/options_estate/OPTIONS_CONTEXT_AUDIT_LEDGER_BOUND_ADJUDICATION_2026-08-13.md
  - research/options_estate/sparse_selector_preregistration_receipt_v1.json
  - research/options_estate/OPTIONS_CONTEXT_AUDIT_PREREG_V2_CHARTER_2026-09-22.md
---

Lawful repair is a new preregistration v2, not a timeout or ceiling patch on v1.
