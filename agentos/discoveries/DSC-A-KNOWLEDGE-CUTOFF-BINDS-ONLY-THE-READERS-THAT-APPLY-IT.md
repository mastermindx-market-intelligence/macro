---
key: A-KNOWLEDGE-CUTOFF-BINDS-ONLY-THE-READERS-THAT-APPLY-IT
claim: >-
  The Finance read-model contract compares no date with the document's knowledge_cutoff, so a
  reading dated after the cutoff validates. Only the readers that apply the cutoff themselves
  are bound by it. After #8135, only the valuation anchor did. Every other reader of a dated
  owner row published rows dated after the cutoff: the operating reading, the expectations
  reading, the qualified price reading, the company cells, the source records, the curation
  revisions drawn from theme evidence, and the freshness drawn from them, and a conflict read
  the late readings it was given. The anchor also admitted an observation dated on the cutoff
  by as_of but observed or published after it, because it read as_of first. A cutoff compared
  by calendar date is not the cutoff either: the shared contracts read knowledge_cutoff as an
  instant, so a time written late on the cutoff's date in a zone behind UTC is past it. The
  shared rule that states the cutoff, feature.point_in_time in
  engine/sector_intelligence/contracts.py, belongs to feature_snapshot.v1, not to the Finance
  read model.
falsifier: >-
  `python3 -m pytest tests/test_finance_intelligence_projection.py -q -k "knowledge_cutoff or however_far_ahead"`
  passes (54). Swap in engine/sector_intelligence/finance_projection.py from 2a93791563bb
  (#8135's squash) and 45 must fail, each on an assertion after validate_contract accepted
  the document. The 9 that still pass are the valuation-observation as_of case, the
  world-valid test, the anchor's own cutoff test and the six instant cases whose row is read.
  If the swap passes, the readers already applied the cutoff and this record is wrong.
so_what: >-
  (1) Apply a knowledge cutoff once, at the input boundary, before any reader runs. The
  composer now reads its inputs through _known_at_cutoff, so a reader added later inherits
  the cutoff. A cutoff check inside one reader covers that reader only, and the contract
  will not catch the others.
  (2) Gate only the clocks that say when a row became knowable:
  - observations: as_of, observed_at and published_at;
  - company cells: those three and evidence_date;
  - theme evidence and source records: their source's published_at, observed_at and
    retained_at.
  Never gate the clocks that say when a row holds in the world: a report period,
  effective_at, business validity. A row can be known before the time it describes, such as
  a rate change announced today and effective next month.
  (3) Compare a clock the way the contracts read the published document. The cutoff is an
  instant. A clock is read two ways: as the instant the contracts read from it (a bare date
  is the start of its day in UTC, a time without an offset is UTC), and as the date the
  composer publishes for it (the calendar date it was written in). Either one past the
  cutoff withholds the row, so every date the document publishes is on or before the cutoff.
  The second reading is conservative on purpose: a time written early on the next day in a
  zone ahead of UTC is withheld although its instant is before the cutoff, because the date
  the document would publish for it is not. A clock that names no instant, a time of day or
  an offset that carries it outside the range of a datetime, is read by its date alone, and
  the gate never raises: the composer stays total over malformed owner values.
  (4) Gate every iterable of rows a reader can iterate, not only a list or a tuple. A deque
  passed through the first round of the gate and published a late date.
  (5) The input digest still covers the owner's whole snapshot, so it still identifies which
  snapshot produced the document. A late row changes the digest and nothing else.
  (6) An input receipt that reads READ over an input whose every row the cutoff withheld is
  false. The gate keeps the keyed maps of packets, expectation and market rows, so their
  receipts now read DEGRADED when the cutoff withheld every row the owner supplied.
  (7) A sweep test that moves every clock past the cutoff is not enough. With every source
  record gone, every plane is withheld as unevidenced, so a leak through one input kind
  publishes nothing. A mutant that stopped gating market rows passed the sweep. Only a
  per-row differential caught it. That test adds one late row beside the base and asserts
  the document changes only in its digest. It then puts the same row on the cutoff and
  asserts the document changes, which proves the row is one a reader publishes.
  (8) Enforcing the rule in the Finance read-model contract, or in the shared base's
  evidence grammar (#7870), would refuse a composer regression at validation time. That is
  a contract change and is not made here.
kind: landmine
verified_at: 2026-09-28
verified_by: "tests/test_finance_intelligence_projection.py: ::test_nothing_dated_past_the_knowledge_cutoff_reaches_the_document (6 fixtures), ::test_a_row_dated_past_the_knowledge_cutoff_changes_nothing_but_the_digest (26 row and clock cases), ::test_a_row_known_by_the_cutoff_is_read_however_far_ahead_it_holds, ::test_the_knowledge_cutoff_is_an_instant_no_published_date_passes (7 clocks x 2 ways of writing the cutoff), ::test_rows_in_any_sequence_are_held_to_the_knowledge_cutoff and ::test_an_input_the_knowledge_cutoff_withholds_is_received_as_degraded (5 inputs) and ::test_a_clock_with_no_instant_never_stops_the_composer (4 clocks); tests/test_finance_research_registration.py::test_an_assertion_retained_past_the_knowledge_cutoff_is_not_consumed. With the composer from 2a93791563bb, 45 of the 54 projection tests in the falsifier's selection fail after validate_contract accepts each document, and so does the registration test."
scope:
  - macro
  - engine/sector_intelligence/finance_projection.py
  - tests/test_finance_intelligence_projection.py
  - tests/test_finance_research_registration.py
confidence: verified
---

## How it was found

#8135 made the valuation anchor pass over an observation dated after the knowledge cutoff.
A census then asked every other reader of a dated owner row whether it applied the cutoff.
None did, and the contract accepted every document that published a late date.

An independent review of the first round of the fix found four more holes. Theme evidence
was not gated, although its source carries a retained date and the curation revisions drawn
from it are published. The gate compared calendar dates, so a time late on the cutoff's date
in a zone behind UTC was read. A sequence other than a list or a tuple passed through
ungated. Receipts read READ over an input the gate had emptied. Reading a clock as an instant
then raised on a time of day, or on an offset that carries a time outside the range of a
datetime, until the reader returned no instant for them.

## The fix

- `_known_at_cutoff` removes every owner row that one of its knowledge clocks dates past the
  cutoff, once, before any reader runs. A clock that is absent or does not parse says
  nothing, so how an undated row is read stays each reader's rule.
- The cutoff is the instant the published `knowledge_cutoff` states. `_contract_instant`
  reads it, and every clock, the way `contracts._parse_temporal` does. A clock that names no
  instant gets none, never an error, and its date alone decides.
- The valuation anchor no longer applies its own cutoff. Nothing dated past the cutoff
  reaches it.
- The digest is computed over the owner's inputs, not the gated ones.
- `_withheld_by_cutoff` tells the receipts which keyed inputs the cutoff emptied.

Related: [[DSC:A-SLICE-WIDE-REF-LIST-VOUCHES-FOR-A-VALUE-BORROWED-FROM-ANOTHER-SLICE]] (the
same pattern for slice scope: one rule per input kind, applied where the input enters).
