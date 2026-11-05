---
key: FIF-T1-ENVELOPE-PIN
question: >
  When the FIF query kernel binds lineage receipts to the current eligible
  ledger (T1), should it re-derive only the 18-field positive-evidence
  payload, or also pin the receipt ENVELOPE (rule identity, availability,
  source-known clock)?
answer: >
  Pin the envelope at admission AND at per-query revalidation:
  `evidence_rule_id == CONFIRMATION_RULE_ID`;
  `evidence_rule_version == CONFIRMATION_RULE_VERSION` type-strict
  (`type(...) is not int` — a boolean `True` is not a version 1);
  `system_available_at >= max(CONFIRMATION_RULE_AVAILABLE_AT,
  _system_available_floor(parent_group, child_group))` computed over the
  FULL per-accession groups the mint path groups by (never a cutoff-filtered
  subset); and `source_known_at == max(accepted_at)` of the two canonical
  duplicate representatives. Violations return the typed refusal codes
  `receipt_rule_mismatch` / `receipt_system_availability_backdated` (a
  source-known violation classifies as `evidence_does_not_match_source`);
  admission fail-closes the whole provider bundle.
rationale: >
  A receipt hash proves only internal self-consistency — a forged payload
  with a correctly recomputed digest over genuine evidence still passes a
  payload-only check. The envelope decides under WHICH POLICIES a receipt is
  visible: a backdated `system_available_at` (below the mint floor) or a
  foreign rule id/version makes a receipt visible under policies where the
  honest mint is not, flipping `not_evaluable` lineage answers into values
  (the T1b adversarial finding F02). Re-deriving the floor from
  cutoff-filtered groups at revalidation would be a silent weakening: the
  filtered floor can only be weaker than the one the receipt was minted
  under, so both gates must call the same check with the mint's own full
  groups. Refusal reasons are engine-level diagnostics, never response
  bodies.
alternatives:
  - option: payload-only binding (re-derive the 18 evidence fields only)
    why_not: >
      Lets a backdated or foreign-rule receipt pass — the envelope around a
      valid digest governs policy visibility, so payload-only binding leaves
      the exact seam F02 exploited (admission never read top-level
      system_available_at; re-prove only tested it against
      policy.recorded_at).
  - option: cutoff-filtered accession groups at revalidation
    why_not: >
      A later cutoff can move the computed floor below the one the receipt
      was lawfully minted under, admitting receipts the honest mint could
      not serve under that policy; only the full groups reproduce the mint.
evidence:
  - "engine/fundamental_forensics/lineage_evidence.py:131-132 (branch claude/fif-t1-evidence-binding-20261012, head d4dcaba967d6) — REFUSAL_RECEIPT_RULE_MISMATCH / REFUSAL_RECEIPT_SYSTEM_AVAILABILITY_BACKDATED constants"
  - "engine/fundamental_forensics/lineage_evidence.py:542-584 — receipt_envelope_refusal(): id/version type-strict check, availability floor over parent/child groups, source_known_at == max(accepted_at) of canonical duplicate representatives"
  - "engine/fundamental_forensics/query.py:5095 — admission calls receipt_envelope_refusal(receipt, parent_group, child_group) with full groups ('never a cutoff-filtered subset'); LineageEvidenceError fail-closes the provider bundle"
  - "engine/fundamental_forensics/query.py:5288 — revalidation calls receipt_envelope_refusal with self._accession_group(...) full groups, explicitly NOT the _visible_accession_group cutoff-filtered subsets"
  - "tests/test_fundamental_forensics_cross_filing_lineage.py:723-731 — _T1_VALID_CASE_PINS: four governed policy cases (response sha256 + query_hash) pinned on base 5267c66846e7; test at :880 (A02) proves valid cases stay byte-identical; parametrized version/type mutation at :1040 ([2, True]) proves the type-strict refusal"
affects:
  - WS:FINANCIAL-INTELLIGENCE-FABRIC
  - engine/fundamental_forensics/lineage_evidence.py
  - engine/fundamental_forensics/query.py
  - tests/test_fundamental_forensics_cross_filing_lineage.py
confidence: high
reversibility: easy
decided_by: coo-fable (FIF e2e seat; branch claude/fif-t1-evidence-binding-20261012, commits f1323eb13f44 / d4dcaba967d6)
decided_at: 2026-10-12
---

# FIF T1/T1b — the receipt envelope is pinned, not just the payload

T1 bound every lineage receipt's 18 positive-evidence fields to what the one
canonical builder reconstructs from the CURRENT eligible ledger, at admission
and at revalidation. T1b closed the remaining seam this decision records: the
ENVELOPE around the payload (rule id/version, system availability floor,
source-known clock) is now pinned by the same function
(`receipt_envelope_refusal`) at both gates, always over the mint's full
per-accession groups.

Two properties a future session must not regress:

1. **Type-strict version equality** — `True` (bool) is not `1` (int); a
   payload that smuggles a truthy version fails `receipt_rule_mismatch`.
2. **Full groups at revalidation** — passing policy cutoffs only proves the
   receipt is not NEWER than the policy; the envelope pin additionally proves
   it is not OLDER than the lawful mint floor. Substituting the
   cutoff-filtered `_visible_accession_group` subsets for the full
   `_accession_group` groups reopens F02.

The four governed policy cases keep byte-identical responses (pinned in
`_T1_VALID_CASE_PINS`, captured on base `5267c66846e7` before the repair);
T2's seal manifest (`t1_compatibility_seal_manifest_v1.json`) is the
independent pre-T1 capture that makes any drift red.
