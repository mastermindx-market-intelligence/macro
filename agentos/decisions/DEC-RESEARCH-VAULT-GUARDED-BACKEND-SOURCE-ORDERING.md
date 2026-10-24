---
key: RESEARCH-VAULT-GUARDED-BACKEND-SOURCE-ORDERING
question: >
  Must the F11 common-generation coverage prerequisite also block protected delivery
  of guarded dedicated-reader backend libraries required to construct the MCP runtime?
answer: >
  No. Amend F12-Q-L4-2 (f) only for the guarded dedicated-reader backend composition.
  Those libraries and their deterministic tests may follow normal protected source
  delivery before common-generation coverage reaches 95 percent. Ordinary Brain F11
  wiring and activation remain held until the existing >=95% common-generation proof.
rationale: >
  Protected Mastermind 2a2216 imports read_runtime and qualified_reader, but protected
  Macro aee0f40a lacks both. The current completion principal explicitly authorized
  this source-ordering amendment under Chris's full-program autonomy instruction.
  Shipping guarded libraries resolves a real constructor dependency without asserting
  coverage, selecting an image, changing ordinary Brain reads or admitting a writer.
alternatives:
  - option: Publish the complete retained F11 branch before coverage
    why_not: It changes ordinary Brain reads and the private comparison feature; those remain held.
  - option: Remove verifier imports or copy only the two missing modules
    why_not: That bypasses the intended contract or misses catalog and read-service dependencies.
evidence:
  - "Explicit Meta-CEO ruling in root 01a13301-995f-7631-8cee-d675d7de5671 to child 01a152a1-1215-7d33-8da3-d1cf1eefba0b on 2026-10-19."
  - "Mastermind 2a2216e58839cb0efce923742f000de076c4b69e integrations/research_read_mcp/port_adapter.py:398,415."
  - "Retained full F11 8f5ad6dc6dbee0b288646b676a38c20e227d17bc; original carrier #9177 head2962036f."
  - "Constructor closure: runtime-composition/producer-release-resolution-20261019/f11-integration/held-f11-constructor-smoke.json under the existing programme evidence root."
affects:
  - "WS:RESEARCH-VAULT-AI-FABRIC"
  - engine/research_vault/read_runtime.py
  - engine/research_vault/qualified_reader.py
confidence: high
reversibility: easy
decided_by: "Meta-CEO programme principal 01a13301-995f-7631-8cee-d675d7de5671 under current Chairman commission"
decided_at: 2026-10-19
---

This is a narrow amendment of the technical source ordering in F12-Q-L4-2 (f),
not a release or runtime admission receipt. The full desired F11 implementation is
preserved on `claude/rv-f11-prepared-01a13301` at `8f5ad6dc` for later integration.
Ordinary Brain wiring, comparison and public-route changes are deliberately deferred.

All selected-reader preparation/delivery guards, expected producer identity, writer
policy and custody, original uncertain operations/no-replay, auth/MFA/permission,
quote limits and consumer acceptance remain unchanged. Source, protected merge,
installation, selection, observed reads and product acceptance are separate facts.
The native archive also needs the exact tracked `scripts/__init__.py` and
`scripts/check_research_vault_source_freshness.py`; archive construction and installation
remain with the existing release owner.
