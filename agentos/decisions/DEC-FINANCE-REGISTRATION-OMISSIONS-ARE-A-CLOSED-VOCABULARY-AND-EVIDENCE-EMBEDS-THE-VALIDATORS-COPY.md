---
key: FINANCE-REGISTRATION-OMISSIONS-ARE-A-CLOSED-VOCABULARY-AND-EVIDENCE-EMBEDS-THE-VALIDATORS-COPY
question: >-
  The Finance T10 registration adapter
  (engine/sector_intelligence/finance_research_registration.py, PR #8006) turns an owner's
  research bundle into a Finance evidence envelope. Two things from the owner reach that
  envelope: the names of the inputs the owner says it omitted, and the curation assertion
  the adapter selects as evidence. What may cross into the envelope, and in what form?
answer: >-
  (1) Owner omissions are a CLOSED vocabulary. The set of admitted names, _OMISSION_NAMES, is
  exactly the owner inputs and owner-bundle fields the adapter already declares
  (_OWNER_INPUT_FIELDS | _OWNER_BUNDLE_UNMAPPED_FIELDS). A declared name reaches the envelope
  as owner_omission:<name>. Any other non-blank string collapses to the single marker
  owner_omission:unrecognized, and a blank string reads owner_omission:unnamed. The adapter
  collapses an unknown omission and never refuses on one, because the omissions source raises
  nothing. A shape filter (a slug regex bounding characters and length) is not enough: owner
  text written in lowercase snake_case passes any shape test.
  (2) The evidence envelope embeds the copy that the shell's validate_assertion RETURNS,
  never the raw bundle entry. The shell's validator returns a deep-copied dict (#7870,
  engine/theme_graph/curation_assertion.py). A ValueError from the validator, which includes
  the shell's CurationAssertionError, reads as the not_available refusal. A validator that
  returns a non-mapping is a broken shell: it raises TypeError, and a KeyError propagates as
  itself. Neither is read as not_available.
rationale: >-
  The envelope is a public-facing projection. Anything owner-authored that crosses it
  verbatim can carry private research. The seat's privacy probe seeded the omission
  "client_acme_short_5mm_block", and it reached the envelope through the round-3 slug filter.
  A closed vocabulary is the only filter whose admitted set is known in advance. Embedding the
  validator's copy means the envelope holds only fields the shared owner's contract admits:
  the assertion object is open, and the raw entry can carry anything. Letting a broken
  validator fail as itself keeps a shell defect from being reported as an ordinary "not
  available", which would hide the break from every consumer.
alternatives:
  - option: bound omission names by shape (slug regex, length cap)
    why_not: shape is not content; the round-3 re-review (M1) showed owner text in snake_case passing verbatim
  - option: refuse the whole registration on an unknown omission
    why_not: the omissions source raises nothing and an unknown name is not a defect of the evidence; collapse keeps the registration and still says something was omitted
  - option: embed the raw bundle entry, or name the shell's private error type
    why_not: the raw entry is an open object; naming CurationAssertionError would couple Finance to the shell's private class, when catching its ValueError base is enough
evidence:
  - "PR #8006 round-3b head 92e2df941d10: suites 126 passed, 1 xfailed; seat red-proof 13/13 RED on revert; positive control on #7870's tree 90 passed, 1 xfailed"
  - "tests/test_finance_research_registration.py: test_an_owner_omission_reaches_the_envelope_only_as_a_declared_name (markers [event_workspaces, financial_packets, unnamed, unrecognized]; _OMISSION_NAMES equals the declared field sets)"
  - "tests/test_finance_research_registration.py: the privacy test seeds client_acme_short_5mm_block and asserts client_acme is absent from both the compose and evidence blobs"
  - "tests/test_finance_research_registration.py: test_evidence_lets_a_broken_validator_fail_as_itself[_raises_keyerror-KeyError, _returns_none-TypeError]"
affects:
  - WS:GMI-FINANCE-INTELLIGENCE
  - engine/sector_intelligence/finance_research_registration.py
  - tests/test_finance_research_registration.py
confidence: high
reversibility: easy
decided_by: "seat 938d17d6 (Finance Intelligence CEO seat, operation gmi-finance-fable-ceo-e2e-20260924-chairman-001)"
decided_at: 2026-09-27
---
