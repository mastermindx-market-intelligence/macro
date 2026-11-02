---
key: D2-WAITS-ON-A-BUILT-V1-1-NOT-ONLY-ON-THE-BASE-MERGE
claim: >
  "D2 is held until #7870's shared foundation lands on `main`" understates the gate. The five
  functions Healthcare T03 names as its consumption surface
  (`validate_assertion(payload, *, allow_unstamped=False)`, `curation_revision(payload)`,
  `encode_assertion(payload)`, `decode_assertion(value)`, `source_ref_for(payload)`) all EXIST
  on #7870's head with signatures matching the plan exactly, and all are ABSENT from `main` —
  so the merge gate is real and correctly stated. But T03 is specified as a *version-aware*
  consumption ("explicit `schema` selects the branch", v1/v1.1 discriminator), and the v1.1
  half of that discriminator does not exist as code or as a schema file anywhere on the base
  carrier. `contracts/theme_graph/` holds ten `*.v1.schema.json` files and no v1.1 file;
  `curation_assertion.py` pins a single frozen `SCHEMA_ID = "theme_graph.curation_assertion.v1"`
  with no version branch, and `reference_for_assertion` RAISES `k1_owner_schema_drift` unless
  the owner row advertises exactly `[SCHEMA_ID]` — i.e. the module actively refuses a
  two-version owner today. v1.1 exists only as
  `research/theme_graph/CURATION_ASSERTION_V1_1_PROPOSAL_2026-09-24.md`, whose own state line
  reads `V1_1: PROPOSED_NOT_BUILT` and which says of itself "**Not** live data admission, not a
  schema enrollment, not code." So `theme_graph.curation_assertion.v1.1` is a NOT-YET-MINTED
  identifier, not a defect in the base: D2/T03 becomes buildable on the base merge ONLY if it
  is scoped to v1-only consumption, and its v1.1 branch waits on the base owner building v1.1.
falsifier: >
  Run, on the base carrier's head:
  `git ls-tree -r --name-only refs/hc/pr7870 -- contracts/theme_graph/` and
  `grep -n 'SCHEMA_ID' engine/theme_graph/curation_assertion.py`. If a
  `curation_assertion.v1.1.schema.json` appears, or `SCHEMA_ID` becomes a `SCHEMA_IDS` tuple
  with a `_validator_for(schema)` dispatch, or the proposal's state line stops reading
  `V1_1: PROPOSED_NOT_BUILT`, then v1.1 is built and this constraint is discharged — T03 may
  consume both branches. Equally, if the plan's T03 text is amended to name only v1, the
  version-aware half of the gate disappears and only the merge gate remains.
so_what: >
  Without this, a D2 lane reads the plan's "explicit `schema` selects the branch" plus a
  remembered "D2 unblocks when #7870 merges", finds no v1.1 to dispatch on, and INVENTS the
  v1.1 shape so the call it was told to write can exist — the exact failure family as
  `DSC:A-SYNTHETIC-FIXTURES-NEVER-REACHED-THE-BRANCH-THE-LIVE-FEED-TAKES`, and the one the
  plan's own C0 gate forbids in the words "No adapter is synthesized from this checklist."
  Minting it would also breach the standing Chairman/Astra directive that #7870 owns the shared
  base and sector verticals mint NO shell/evidence/rights vocabularies. Two consequences for
  sequencing: (1) the C0 gate is TEN supplied facts on the existing PR/Agent OS record, of
  which "explicit v1/v1.1 discriminator and supported payload" is one — a bare merge satisfies
  neither it nor the other nine automatically, so re-evaluate the checklist at merge rather
  than treating merge as the gate; (2) the lawful Healthcare move when v1.1 is still
  `PROPOSED_NOT_BUILT` is to scope T03 to v1-only and record the deferral, never to build the
  missing half and never to ask the base owner to reorder their program for this vertical.
kind: constraint
verified_at: 2026-09-27
verified_by: >
  direct observation against base carrier head `a0d7b054ff23` (fetched as `refs/hc/pr7870`)
  and `origin/main` at `386c98edda2c`. Symbol resolution: for each of the five names,
  `git grep -l "def <name>" origin/main -- '*.py'` returned 0 files and
  `git grep -l "def <name>" refs/hc/pr7870 -- '*.py'` returned 1, all
  `engine/theme_graph/curation_assertion.py`; signatures read at that blob's lines 121, 280,
  305, 322, 345 match the plan's `Consumes/produces` text verbatim including the
  keyword-only `allow_unstamped: bool = False`. Version surface:
  `git ls-tree -r --name-only refs/hc/pr7870 -- contracts/theme_graph/` = ten `*.v1.schema.json`
  files, no v1.1; `SCHEMA_ID = "theme_graph.curation_assertion.v1"` at line 46 with the owner
  equality check at line 539 (`if owner.get("native_schemas") != [SCHEMA_ID]`); the only v1.1
  artifact on the ref is the proposal document, state line
  `MISSION_COMPLETE: FALSE · SEMICONDUCTOR_B: NOT_BUILT · C1: DEFERRED · V1_1: PROPOSED_NOT_BUILT`.
  Gate text read from the R13 plan blob `23cd3788620c5ad26abb878dddbc29911b2fab6f`
  (C0 at line 72, T03 `Consumes/produces` at line 175).
scope:
  - mastermindx-market-intelligence/macro
  - engine/theme_graph/curation_assertion.py
  - contracts/theme_graph/
confidence: verified
---

Recorded by the Healthcare seat as a D2 **preflight**, before any D2 write, so the scoping
decision is made from the tree rather than from the wave order. It changes nothing in the base
and asks nothing of the base owner, who has already published `V1_1: PROPOSED_NOT_BUILT`.
