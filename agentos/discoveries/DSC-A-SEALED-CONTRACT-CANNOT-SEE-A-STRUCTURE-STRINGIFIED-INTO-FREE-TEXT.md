---
key: A-SEALED-CONTRACT-CANNOT-SEE-A-STRUCTURE-STRINGIFIED-INTO-FREE-TEXT
claim: >-
  A contract that seals every object (additionalProperties false) still cannot refuse an
  owner structure that the composer has already turned into a string. The Finance read
  model types 91 property sites (77 scalar, 14 arrays of strings) only as a non-empty
  string. So `str()` of an owner mapping validates, and so does `list()` of one, which
  yields its key names. Measured on the round-1 head of PR #8121 (6c78279feacb), which had
  already closed the metric KEY leak. A plant that deleted, emptied or replaced each owner
  value in turn found 29 leaking mutations at 10 composer sites, each in a document the
  contract accepted. Two of the sites are the operating and valuation primary_metric names:
  an owner metric mapping with no name fell back to `str()` of the whole mapping, with the
  private keys inside it. The other eight are input_receipts generation, snapshot_identity
  curation_revision_set, exposure-cell evidence_refs, the macro mechanism, a constraint's
  economic_effect, and material-change change_id, operating_implication and conflict_ids
  (`list()` of a mapping publishes its key names). The round-1 key plant could not
  see any of these. It only added keys, so no fallback ran, and the planted keys rode
  inside one string value. Two of the sites sit behind owner
  fields that every committed fixture leaves empty (sector_dossier, theme_evidence), and two
  behind owner keys no committed fixture carries (a source record's constraints, a material
  change's conflict_ids). No plant reached any of the four.
falsifier: >-
  `python3 -m pytest tests/test_finance_intelligence_projection.py -q -k "owner_value or stringified or owner_fences_plant or composer_reads"`
  passes. The positive control replaces `_owner_text` with
  `lambda v: None if v is None else str(v)`, and then the nameless-metric mutations must
  report LEAKED. Swap in engine/sector_intelligence/finance_projection.py from 6c78279feacb
  with inert `_owner_text`/`_owner_refs` shims: the value fence must then report 29 LEAKED.
  If it reports none, this was not the leak path. The site count comes from walking the
  schema for properties equal to `{"type": "string", "minLength": 1}`, alone or in a oneOf
  with null, and for arrays of such items.
so_what: >-
  (1) A sealed contract is a complete KEY check. It is no check at all on content that the
  composer launders into a string. Publish owner text only through a scalar gate
  (`_owner_text`: str, int, float or date, otherwise absent). Publish owner reference lists
  only from a real list (`_owner_refs`). Never use `str()`, an f-string, `join` or `list()`
  on an owner value. (2) A plant that only ADDS keys never runs a fallback. The fence has
  to delete, empty and replace each owner value in turn. A fixture field that is empty is a
  field no plant reaches, so assert that every owner field was planted; and a key no fixture
  carries is a key no plant reaches, so pin every key the composer reads against the keys the
  fixtures carry, naming each exception with its reason. (3) Plant a
  structure that carries no authority word. The composer's emit guard refuses a structure
  holding a peer rank wherever it lands. That hides whether the contract, or the composer's
  own projection, would have held it: 164 of the first 170 refusals were that guard.
  And recognize the plant however a path reshapes it. The oracle searches the document for
  the planted key and the planted value, case-folded. A search for the literal key alone
  called an upper-cased rendering, or one publishing only the mapping's values, clean
  (found by the round-2 review; hashed, encoded or truncated renderings stay beyond it).
  (4) The composer is not total over malformed owner input. A structure given as a
  source_family, as a slice_id, as a market price_basis or as a metric name raises TypeError or
  AttributeError. That failure is closed for a leak, but it is open for the page: one
  malformed owner field takes down the whole projection instead of rendering its missing
  state in words.
kind: landmine
verified_at: 2026-09-28
verified_by: "tests/test_finance_intelligence_projection.py::test_an_owner_value_crosses_into_free_text_only_as_a_scalar (847 mutations over six fixtures: 657 clean, 183 sealed by the contract, 7 refused, 0 leaked with the fix; 29 LEAKED with 6c78279feacb swapped in), ::test_the_owner_value_fence_fires_on_a_stringified_owner_metric[str,upper,values] (LEAKED with the seam rendering a structure as is, upper-cased or as its values; upper and values read clean under a literal-key oracle) and ::test_every_owner_key_the_composer_reads_is_planted"
scope:
  - macro
  - engine/sector_intelligence/finance_projection.py
  - tests/test_finance_intelligence_projection.py
  - contracts/sector_intelligence/finance_intelligence_read_model.v1.schema.json
confidence: verified
---

Found by an independent Opus review of PR #8121's round 1, not by the round-1 fence. The
reviewer read `_build_primary_metric` and saw that the fallback for a missing metric name
ran `str()` on the owner's whole metric mapping. The class was then closed rather than the
one line: every `str()` that publishes owner text now goes through `_owner_text`, every
owner reference list through `_owner_refs`, and the fence mutates values as well as keys.

The remaining `str()` calls in the module either map into a closed set (direction,
freshness, lag, state) or stay internal (an as-of comparison, a popped raw freshness state,
the identity-key union). A new `str()` on an owner value should be read as a leak until
shown otherwise.

Related: [[DSC-A-LEAK-TEST-OVER-A-CLEAN-FIXTURE-CANNOT-FAIL-PLANT-THE-OWNER-KEYS]], the
round-1 record. It covers the same composer and the key half of the same boundary.
