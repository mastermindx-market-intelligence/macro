# Independent pre-seal vintage interface challenge

Two bounded counterexamples were executed against draft `contract.py` SHA-256 `ad90cf372a95ae7ca05691681d95ea9a18e784a1379066e19e15fa05b0ef6b7d`. The exact challenged bytes are retained as `challenged_contract.py`; no producer file was edited. This is an early challenge, not the final acceptance review of the vintage repair.

## Confirmed findings

| Finding | Executed input and result | Required resolution |
|---|---|---|
| V-R1: a blob-wide availability clock checks only the selected row | One synthetic source blob declares availability on September 16 but contains finalized daily rows for September 16 and October 12. The September 16 mark passes source resolution and grading on September 16. Selecting October 12 correctly refuses, so this is a missing whole-blob consistency check. | Check the declared availability against the calendar close of every finalized row in this codec. A blob cannot be available before part of its asserted finalized content exists. |
| V-R2: equal-time correction accepted under a later-time contract | A separately hashed correction changes price from 100 to 99, references the authentic original and has exactly the same recording timestamp. Append succeeds with both records. | Require a strictly later correction recording timestamp, or explicitly change the contract. The producer accepted the stricter rule. |

The producer acknowledged both findings and will add discriminating controls before sealing a final candidate. Publication exactly at the entry anchor is intentionally admitted by the existing producer fixture; the design language should say “at or before” rather than imply strict precedence.

## Reproduction and limits

Run `python probe.py` in this directory. It compiles only the retained draft, reconstructs the explicit synthetic inputs, verifies the selected-future-row negative control, and writes deterministic `EVIDENCE.json`. The evidence includes the entire source fixture, calendar, original and correction records, returned mark, expected resolution and exact draft hash.

These results do not establish a natural production occurrence, market execution, real provider availability or exchange-calendar truth. They challenge the internal consistency of an explicitly synthetic research codec and append contract. The original laboratories and independent reviews remain unchanged.
