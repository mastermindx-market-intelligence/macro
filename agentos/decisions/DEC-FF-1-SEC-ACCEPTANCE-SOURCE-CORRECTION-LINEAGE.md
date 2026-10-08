---
key: FF-1-SEC-ACCEPTANCE-SOURCE-CORRECTION-LINEAGE
question: >
  When a current SEC Submissions object restates an accession's
  acceptance_datetime to a different UTC instant than the prior bound object
  recorded, may FF-1 admit the restatement, and on what evidence?
answer: >
  Yes, but only as a recorded correction and only when every discriminator holds.
  Exact text equality remains first and
  DEC:FF-1-ACCEPTANCE-DATETIME-COMPARES-BY-INSTANT remains second; the correction
  path runs only after both refuse. Admission requires the same accession, exactly
  one prior and one current row, every non-time filing fact exactly equal, both
  source objects re-read from the store, ungzipped, rehashed to their recorded
  sha256 and re-parsed to exactly the recorded rows, exactly one lawful
  URL-bound `recent` Submissions component producing each side, the prior object
  strictly older than the admitting one, identical fractional spelling, and a tz
  database mapping in which the prior text read as a naive America/New_York wall
  time lands on the current UTC instant exactly at that date's legal offset
  (-4h EDT or -5h EST). Nonexistent and ambiguous DST wall times are refused.
  Any failure retains historical_submissions_conflict. The merged row carries the
  corrected current value; the prior value survives only inside the correction
  entry.
rationale: >
  The ROST defect is not the ANGO case. Accession 0000745732-26-000031 carried
  2026-06-02T16:37:27.000Z and now carries 2026-06-02T20:37:27.000Z with every
  other filing fact identical. Those are two different instants, so the
  representational-equivalence rule correctly refuses them, and the duplicate
  guard fail-closes. Reading the prior text as EDGAR local wall time on a date the
  tz database says is EDT yields exactly the current UTC instant, which identifies
  a genuine source restatement rather than a disagreement. Admitting it silently
  would assert the two values were always the same instant; refusing it forever
  would leave sec_accepted_at four hours early and strand the issuer. Recording it
  as bound evidence preserves both truths: the correction is applied, and what
  changed stays auditable against the exact objects that produced it.
  The offset is looked up from the tz database and then the mapping is verified,
  never inferred from the observed difference, so a three- or six-hour shift, a
  seven-hour Pacific guess, or a four-hour shift on an EST date cannot be
  laundered into a correction.
alternatives:
  - option: Widen _filing_fact_values_are_compatible with a timezone branch
    why_not: >
      That comparator sees only two values. It cannot check source chronology,
      object binding, component uniqueness or row uniqueness, so widening it would
      make FF-1 a fuzzy time normalizer that accepts any four-hour difference.
  - option: Retain the first-bound prior text, as the fractional rule does
    why_not: >
      The fractional rule retains first text because both spellings name one
      instant. Here the prior value is a different, wrong instant; retaining it
      would leave sec_accepted_at four hours early.
  - option: Normalize every acceptance_datetime to a canonical UTC form on read
    why_not: >
      It rewrites immutable source evidence, destroys the first-bound SEC text and
      silently repairs disagreements that are not corrections.
  - option: Keep failing closed until a human adjudicates each occurrence
    why_not: >
      The ANGO precedent shows a single unadjudicated acceptance conflict halts a
      bounded recovery at cursor zero. A typed, fully discriminated, recorded path
      is auditable where a per-case ruling does not scale.
evidence:
  - "engine/fundamental_forensics/broad_sec_store.py:_derive_filing_corrections is the sole derivation site; _merge_filing_rows performs a pure allowlist lookup."
  - "Base-source RED: _assert_no_duplicate_filing_conflicts raises historical_submissions_conflict, 'accession 0000745732-26-000031 conflicts on acceptance_datetime'."
  - "tests/test_fundamental_forensics_broad_sec.py::test_rost_acceptance_timezone_source_correction_is_admitted"
  - "tests/test_fundamental_forensics_broad_sec.py::test_acceptance_correction_time_matrix_fails_closed (12 hostile time cases)"
  - "tests/test_fundamental_forensics_broad_sec.py::test_correction_ledger_rejects_reorder_duplication_and_edited_rule"
  - "tests/test_fundamental_forensics_broad_sec.py::test_filing_corrections_change_identity_but_preserve_historical_manifests"
  - "tests/test_fundamental_forensics_broad_sec.py::test_acceptance_correction_refuses_when_a_third_source_asserts_the_accession (independent review finding)"
affects:
  - WS:FUNDAMENTAL-FORENSICS
  - engine/fundamental_forensics/broad_sec_store.py
  - contracts/fundamental_forensics_broad_sec_issuer_manifest.schema.json
  - contracts/fundamental_forensics_broad_sec_run.schema.json
  - tests/test_fundamental_forensics_broad_sec.py
confidence: high
reversibility: easy
decided_by: claude-opus-5
decided_at: 2026-09-20
---

## Identity

`filing_corrections` is an optional manifest field. `issuer_source_identity`
includes it **only when it is non-empty**, and then only as the list of
`correction_id` values. Adding the key unconditionally — even as an empty list —
would change the identity of every historical manifest and break their
verification, so the conditional is load-bearing, not a style choice. A
correction therefore yields a new issuer-source identity and a new manifest id
while the previous manifest stays reachable and every prior raw object stays
byte-identical.

Each `correction_id` is the SHA-256 of its own entry with `correction_id`
removed. The containing manifest's id is absent from the entry by construction,
so the ledger cannot cycle through the identity it participates in. The ledger is
written in canonical (accession, field, correction_id) order and de-duplicated;
a reordered, duplicated, or edited entry fails closed at read because any mutated
field changes the entry's own content address. A legacy manifest — one without
component-set identity — may never carry a ledger.

## Telemetry

`coverage.submissions_fetched` was a false aggregate in `run_broad_sec_poll`:
initialised to zero, emitted in the receipt, never incremented, while
`_run_recovery_poll` incremented its own. It is now incremented once immediately
after `fetch_submissions` returns and binds bytes, before any parse or
recomposition can fail; a pre-byte transport failure raises inside the fetcher
and never counts. The run contract's shared `submissions_fetched` bound was
raised from 64 to `MAX_UNIVERSE_ISSUERS` (4000) — it was only ever within 64
because the incremental lane never incremented it, so repairing the counter
without the bound would have made real runs violate their own receipt schema.

## Boundary

This is a source-comparison and telemetry decision only. It declares nothing
about production. Merging it leaves FF-1 `BUILT_NOT_PROVEN / PRODUCTION_INERT`:
no R2 mutation, no scheduled workflow, no FF-1R recovery dispatch, no
latest-pointer movement, no live canary. The frozen recovery plan
`e252f0a85c193323be128b6de2762c522a0ab86b74d8a2ed15a1f3014695e5a4`,
cursor/completed `0`, backlog `2,571` and the null last-successful recovery
receipt are all preserved. The ANGO adjudication in
`DEC:FF-1-ACCEPTANCE-DATETIME-COMPARES-BY-INSTANT` is unchanged and still runs
first. Previous-quarter reconciliation remains SPEC_ONLY / NOT_BUILT and FF-2
remains FORBIDDEN / NOT_STARTED. A separate accepted proof wave owns copied exact
production ROST bytes, an isolated frozen replay, and only then any lawful real
schedule.

## Independent review outcome

An independent adversarial pass over provenance laundering, identity cycles,
identity instability, historical breakage and fail-open found one substantive
defect, which this decision incorporates.

**The allowlist is keyed by value, and is consumed over row groups the
adjudicator never reads.** A correction is derived from exactly two bound
`recent` Submissions objects, but `_merge_filing_rows` and
`_assert_no_duplicate_filing_conflicts` also receive historical shard rows and
withheld rows. A historical shard asserting the stale instant would have been
silently overwritten — never rehashed, never chronology-checked, its sha256
absent from the correction entry — leaving the manifest contradicting a bound
component with no record that it disagreed. That is the laundering this rule
exists to prevent. `_derive_filing_corrections` now takes `other_rows` and
refuses outright when any third source asserts the same accession. Neutering the
guard turns
`test_acceptance_correction_refuses_when_a_third_source_asserts_the_accession`
red, so it is load-bearing rather than decorative. The same guard removes an
order sensitivity the reviewer measured: previously
`prior+current+historical` raised while `prior+historical+current` succeeded.

Two lesser items were also taken: `_rebound_source_rows` caught only `OSError`,
so a truncated gzip raised `EOFError` past the refusal path (fail-closed, but as
an untyped exception); it now refuses. And the current-side component-uniqueness
check is redundant, because `current_component` is constructed from the same
literal it is then checked against — the reviewer could not turn this into an
exploit, and the check retains real force on the prior side, where components
come from a stored manifest that may hold zero or several `recent` entries. It
is kept as a cheap invariant restatement.

Identity cycle, identity instability across hash seeds, and historical manifest
breakage each returned no finding.

## Unresolved gate for the production wave

The correction ledger is append-only and never pruned. A canonical entry is
roughly 1.1 KB, so the schema's `maxItems: 64` and the 128 KiB immutable-manifest
envelope bound an issuer at a few dozen lifetime corrections, after which writes
fail closed with no pruning path. That bound is acceptable for a source wave that
mutates nothing, and a repeatedly-restated issuer is itself a signal worth
stopping on, but the production proof wave must decide whether corrections are
ever compacted and, if so, how a compaction preserves lineage.
