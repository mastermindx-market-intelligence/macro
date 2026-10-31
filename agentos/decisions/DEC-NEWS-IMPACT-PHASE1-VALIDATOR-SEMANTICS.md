---
key: NEWS-IMPACT-PHASE1-VALIDATOR-SEMANTICS
question: >
  The frozen v1 contract is a JSON Schema, and a 33-fixture hostile corpus showed that
  sixteen hostile payloads pass a schema-only validator. Which extra rules does the Phase 1
  validator in engine/news_impact/validate.py enforce on top of the schema, how far does
  the forbidden vocabulary reach (ruling R5), and what stays out of the validator?
answer: >
  The validator adds a fixed list of semantic rules, S1-S13, and reports each one with an
  existing closed reason code. It never mints a new code and never changes the contract bytes.
  S1: a NaN or infinite float is rejected.
  S2: span start greater than span end is rejected.
  S3: a receipt span that ends past its segment length is rejected.
  S4: a fact that supersedes itself is rejected (supersedes_required).
  S5: an observation timestamp earlier than the source availability timestamp is rejected.
  S6: a date or date-time string must be a real calendar value.
  S7: data:, vbscript: and blob: schemes count as injection.
  S8: a role marker split across two text fields of one object counts as injection.
  S9/S10: the R5 vocabulary rules.
  S11: an amount range with low greater than high is rejected.
  S12: an event cannot name its own issuer as the counterparty.
  S13: a fiscal period cannot end before it starts.
  Ruling R5 sets how far the forbidden vocabulary reaches. It applies to key names, to
  identifier-form tokens inside string values, and to provenance ids that name a model
  origin: ids containing llm, gpt or synthetic, or llm together with generated. It does not
  apply to plain words inside a verbatim source quote.
  A fabricated quote is defeated by span replay (V_SPAN_REPLAY, Phase 2), not by a word
  list: the validator checks shape, and span replay checks provenance.
rationale: >
  The contract stays byte-frozen (sha256 prefix 3edc7139), so every gap the hostile corpus
  found is closed in code with an existing reason code. Each S rule is either physics (a
  source cannot be observed before it exists, a span cannot end before it starts, a range
  cannot invert) or a restatement of a masterplan sentence; no ordering is invented.
  Applying the word list to verbatim quotes would reject true filings that merely use the
  words "confidence" or "probability". The C1 lane relabelled fixture 011 from reject to
  accept on that ground. A fabricated quote looks identical in shape to a real one, so only
  replaying the bytes against the owner receipt can tell them apart.
alternatives:
  - option: Amend the contract to v2 with the S rules expressed as schema keywords.
    why_not: >
      Most S rules compare two fields (start/end, low/high, observed/available, issuer/
      counterparty), which JSON Schema cannot express without non-standard keywords; and a v2
      would invalidate the Phase 0 freeze gate for no gain in what is rejected.
  - option: Apply the forbidden vocabulary to every string, including verbatim quotes.
    why_not: >
      It rejects genuine filings whose own text uses the words, and still admits a fabricated
      quote that avoids them; it is a false sense of provenance.
  - option: Add new reason codes per semantic rule.
    why_not: >
      REASON_CODES is a closed enum consumed by the hostile manifest and downstream
      receipts; the five existing codes already name every failure class the rules detect.
evidence:
  - "Hostile corpus tests/fixtures/news_impact/hostile/ (33 fixtures, C1_hostile lane): 16 schema-only gaps listed in its manifest; fixture 011 relabelled accept under R5."
  - "Contract contracts/news_impact/news_impact_event.v1.schema.json sha256 prefix 3edc7139, unchanged by this decision."
  - "DEC:NEWS-IMPACT-PHASE0-FREEZE rulings R1-R4 (excerpt projection, version minimum, closed locators) are inherited unchanged."
  - "Span replay design: research/prophet_v4/news_to_business_impact_20261006/phase1_designs/A6_labeler/span_replay.md."
affects:
  - "engine/news_impact/validate.py"
  - "tests/test_news_impact_validate.py"
  - "tests/test_news_impact_hostile.py"
  - "tests/fixtures/news_impact/hostile/*"
confidence: high
reversibility: easy
decided_by: fable-meta-ceo-seat-0e739467 under the Chairman delegation of 2026-10-10
decided_at: 2026-10-13
---

## Do not redo

Do not widen the forbidden vocabulary to verbatim quotes. Do not add reason codes for the
S rules. Do not move an S rule into the schema without a versioned v2 contract and its own
decision. A new ordering rule needs a physics argument or a masterplan sentence.
