---
key: A-STRESS-CASE-CANNOT-VALIDATE-AN-ADDITIVE-CONSTANT
claim: >
  When a cost model has the form `constant + k * variable`, proving it correct at the regime where
  the VARIABLE dominates says nothing about the CONSTANT, because the constant's relative error is
  maximised where the variable is smallest - and that is usually the ordinary case, not the stress
  case. Measured 2026-09-25 on Mastermind IAC-P1 B3: `reply_entry_page_bytes` charges a replies page
  `REPLY_ENTRY_ENVELOPE_BYTES (217) + 2 * escaped_frame_bytes` against a 64 KiB page ceiling. The
  worker proved its worst case correct - escaped frame 9,674 B, charge 19,565, admitted capacity 3,
  page 58,695 B <= 65,536 - and that proof is sound. But the envelope constant is short: the
  incumbent reply parser (`_parse_message`) REQUIRES `subtype` and `team == workspace_id` on a
  changed entry, so the minimal accepted envelope is 226 B and 448 B once the optional
  `team`/`thread_ts`/`edited` fields appear. At the proven worst case, correcting 217 -> 448 leaves
  capacity at 3, UNCHANGED - the error is invisible there. At small frames it is not: escaped 100 B
  gives capacity 157 charged vs 101 real (56 entries of overcommit), and escaped 20 B gives 255 vs
  134 (121 entries).
falsifier: >
  Hold the page ceiling and stored-copy count fixed and tabulate admitted capacity for the charged
  constant against the real one across the frame-size range, not at one point. If the two columns
  agree at the stress case and diverge at small frames, the stress case was never a validation of
  the constant. To confirm which term is doing the work, re-run the tabulation with the constant set
  to zero: the large-frame capacities must be unchanged.
so_what: >
  A green instrument that asserts the charge is `>=` a MINIMAL entry is a lower bound the
  implementation clears trivially, so it cannot catch a short constant either - both the worker's
  measurement and the reviewer's instrument probed the extreme that hides the defect. Any additive
  constant in a budget needs its own discriminator at the small-variable end, and a spec that names
  that constant must name the shape it is measured from, not a byte count.
