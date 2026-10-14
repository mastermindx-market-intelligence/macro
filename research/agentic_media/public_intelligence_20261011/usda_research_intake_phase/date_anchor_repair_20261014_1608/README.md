# Date rendering correction and rejected parser

The final change tells future Research drafts to retain supplied ISO observation
dates. It changes no facts, dates, numeric receipts, thresholds or validator logic.
The actual USDA draft remains quarantined and byte-identical. No provider was
called to verify this repair; no same-event regeneration is permitted.

Independent Fabric run `mmx-press-date-anchor-review-20261014-001` completed and
was consumed on its original root/parent. Its useful diagnosis is accepted; its
verdict on the proposed parser is **BLOCKERS / NO PASS**. The reviewer used the
submitted diff and nearest available ancestor semantics, not an exact checkout
of the final candidate. Parent reproduction against actual `c3325f190919` confirmed
five remaining failures: month labels hiding quantities, wrong-year resolution,
and false rejection of non-date month/number prose. See `review_reproductions.json`.

The unaccepted parser was withdrawn. Validator and validator-test bytes are
restored exactly to accepted `e7112006a5d69b9fb125ff5e36f2f61a6174dadd`. The rejected
implementation and its tests remain recoverable in that candidate commit and
`rejected_parser.patch.json` (exact patch bytes encoded as JSON). Earlier 457-test and 37-group results describe that
rejected candidate; they are not release approval. The independent reviewer did
not inspect the final three-line writer wording; the parent reviewed that change.

Final checks:

- `python3 -m pytest -q tests/test_press_writer.py tests/test_press_validators.py tests/test_press_run.py tests/test_press_research_triage.py`: **434 passed / 1 existing sparse-site skip**.
- `python3 -B <this-directory>/verify_iso_prompt.py`: Brief, external Brief and
  earnings claim-scope fixture prompts byte-identical; actual USDA selected slot
  and user prompt unchanged; system difference exactly the ISO instruction.
- Four existing portable probes against the current 24-source manifest:
  **12 integrity + 5 DOJ + 9 Research pool + 7 radar = 33 groups**, locally passed.
  Wrong writer hash refused before fixtures; imports precede the hash check.
- Only writer hash changed in the current manifest, to
  `335d1d4755e9dcbe983a0ae99b4e1cc075c339d38ba45360cb88e23757b6002c`.
  Other 23 source hashes and all 3 page hashes are unchanged.

Portable results report local source execution, isolated fixtures and zero real
provider/publication writes. The private installation bundle is syntax-checked
and prepared, **not executed on production**. Original #9209 must land and pass
installed acceptance before the same reviewed follow-on receives its own PR.

The real USDA attempt remains bound to earlier writer `c8027347` and source
`e7112006`; no evidence is retroactively restamped. Three close-paraphrase blocks
and the parent's unrelated-context objection independently keep that draft held.
Publication/cutover remain false; mixed-desk acceptance remains 0/10.
