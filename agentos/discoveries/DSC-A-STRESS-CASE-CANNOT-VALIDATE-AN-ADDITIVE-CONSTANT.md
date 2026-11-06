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
  Historical targets: common/agent_dialogue_consultation_contract.py and integrations/slack_agent_dialogue/slack_web_api.py; use the table and parser conditions recorded in https://github.com/mastermindx-market-intelligence/Mastermind/pull/600#issuecomment-5828084895.
so_what: >
  A green instrument that asserts the charge is `>=` a MINIMAL entry is a lower bound the
  implementation clears trivially, so it cannot catch a short constant either - both the worker's
  measurement and the reviewer's instrument probed the extreme that hides the defect. Any additive
  constant in a budget needs its own discriminator at the small-variable end, and a spec that names
  that constant must name the shape it is measured from, not a byte count.
kind: landmine
verified_at: 2026-09-25
verified_by: >
  Historical author-recorded verification dated 2026-09-25; supporting receipt: https://github.com/mastermindx-market-intelligence/Mastermind/pull/600#issuecomment-5828084895.
  The B3 receipt records the 217-versus-448 capacity table: at 100-byte frames 157 versus 101 entries, and at 20-byte frames 255 versus 134. The supporting parser-grounding correction is also recorded at https://github.com/mastermindx-market-intelligence/Mastermind/pull/600#issuecomment-5827970534. This was source-only evidence with zero production callers.
scope:
  - "Mastermind historical IAC-P1 B3 donor evidence (2026-09-25)"
  - "common/agent_dialogue_consultation_contract.py"
  - "integrations/slack_agent_dialogue/slack_web_api.py"
confidence: verified
---

## Historical provenance — 2026-09-25

The measurements, confidence and verification date above describe the original September 25 observation. The November 6 record repair validates document structure and preserves source references; it does not rerun the historical experiment or establish current runtime behavior. The supporting [original receipt](https://github.com/mastermindx-market-intelligence/Mastermind/pull/600#issuecomment-5828084895) records the historical evidence.

The [later canonical lineage ruling](https://github.com/mastermindx-market-intelligence/Mastermind/pull/600#issuecomment-5841164702) designated claude/iac1-p1-packet-carriage-20260925 as **DONOR_TEST_EVIDENCE / DO_NOT_PUBLISH_AS_P1**, with [Mastermind #986](https://github.com/mastermindx-market-intelligence/Mastermind/pull/986) the canonical P1 carrier. Its held C-D child remained STOP / DO_NOT_PUBLISH. These knowledge records grant no transplantation, installation, live-packet or replay authority; all original refused or uncertain effects retain their original target and reconciliation boundary.
