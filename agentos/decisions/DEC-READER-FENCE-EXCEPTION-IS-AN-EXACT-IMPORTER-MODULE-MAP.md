---
key: READER-FENCE-EXCEPTION-IS-AN-EXACT-IMPORTER-MODULE-MAP
question: >
  The CEO-accepted Live Window design composes an optional, disabled-by-default Steward Live Window through
  `integrations.mastermind_window_reader.owner_read_resource.from_existing_business_owner` inside the real
  Steward app factory, but the Reader static fence
  `tests/test_mastermind_window_reader_static_fences.py::test_window_reader_modules_have_only_package_and_test_importers`
  forbade ANY importer outside the package and its tests. How can the accepted design coexist with the fence
  without rewriting what the fence means?
answer: >
  Widen the fence by exactly one auditable, non-general allowance and nothing else:
  `EXTERNAL_IMPORTER_EXCEPTIONS` is an exact importer path -> module-set map carrying precisely
  `integrations/mastermind_steward_app/live_window.py` and
  `tests/test_mastermind_steward_app_live_window.py`, each permitted to import
  `integrations.mastermind_window_reader.owner_read_resource` ONLY — never
  `integrations.mastermind_window_reader.live_window_read`. The fenced module set, the `allowed_roots` tuple
  and the file's other two fences are unchanged.
rationale: >
  The fence exists to keep the Reader a package-and-tests-only surface, and an exact importer->module map
  preserves that purpose while making the exception readable in one place: the set of legal importers is a
  literal dict, so a NEW importer of either Reader module and ANY importer of `live_window_read` still fail.
  The design's own shape decides which module may be excepted — the Steward needs the composition entry
  point (`owner_read_resource`), not the read module (`live_window_read`) — so the exception is narrower than
  the seam it serves. An explicit map also keeps the architecture question visible to the next reader, where
  a package-level re-export or a dynamic import would have hidden it from the instrument entirely.
alternatives:
  - option: Re-export the seam from `integrations/mastermind_window_reader/__init__.py`
    why_not: >
      It evades the fence rather than answering it (the AST fence would see an import of the package, not of
      a fenced module) and it edits the read-only Reader source to serve an external caller. Two defects for
      one convenience.
  - option: Import the seam dynamically (importlib) inside the Steward app
    why_not: >
      A dynamic import is invisible to the AST fence, so the fence would stop being an instrument: the same
      bypass would become available to every future caller with no allowance recorded anywhere.
  - option: Allow the whole Steward package to import Reader modules
    why_not: >
      Over-broad. It grants every present and future Steward module — including ones with no composition
      role — access to the Reader surface, which is a package-wide permission where the design needs two
      files.
  - option: Mint a second seam module for the Steward to import
    why_not: >
      It duplicates the seam the CEO-accepted design already names, creating a second composition entry
      point to keep in step and a new surface for the fence to have to reason about.
evidence:
  - "Mastermind #758, OPEN/DRAFT/HOLD-FOR-SOL at head 55800d57f42f73a6c093e1432da16b78e3d2ab83 (read 2026-09-17 with `gh pr view 758 -R mastermindx-market-intelligence/Mastermind --json state,isDraft,headRefOid,mergeCommit,title`), chain 34f1be5f -> 4021683f -> 55800d57, base e878878c."
  - "At 55800d57, `gh api -H 'Accept: application/vnd.github.raw' repos/.../contents/tests/test_mastermind_window_reader_static_fences.py?ref=55800d57...`: `EXTERNAL_IMPORTER_EXCEPTIONS` at :31-38 maps exactly those two importer paths, each to the single-element frozenset `{integrations.mastermind_window_reader.owner_read_resource}`; the fenced `modules` set at :42-45 still holds BOTH `...live_window_read` and `...owner_read_resource`; `allowed_roots` at :48-51 is unchanged; the exception is applied only after the package/test root check, so it can never re-permit a package-internal file."
  - "Patch sha256 e6faf8d6b505304a…; RED 1 failed with exactly two offenders -> GREEN; mutants M1-M4 killed (child-session receipts)."
  - "Hosted required `test` run 35221207639 SUCCESS; FULL non-author re-review APPROVE, record sha256 bc2d3a054d6b5797… (child-session receipts)."
  - "Sol scope ruling edge 1789644750.659619 authorized exactly this exception shape (child-session receipt)."
affects:
  - WS:EXECUTIVE-CAPACITY-FABRIC
  - tests/test_mastermind_window_reader_static_fences.py
confidence: high
reversibility: easy
decided_by: ceo-sol
decided_at: 2026-09-17
---

## The exception, exactly

```python
EXTERNAL_IMPORTER_EXCEPTIONS: dict[str, frozenset[str]] = {
    "integrations/mastermind_steward_app/live_window.py": frozenset(
        {"integrations.mastermind_window_reader.owner_read_resource"}
    ),
    "tests/test_mastermind_steward_app_live_window.py": frozenset(
        {"integrations.mastermind_window_reader.owner_read_resource"}
    ),
}
```

The check keeps its existing order: a file importing a fenced module is skipped when it lives under
`integrations/mastermind_window_reader` or `tests/mastermind_window_reader`; otherwise the file's own entry
in the map decides, and a module missing from that entry is an offender. Two imports and only two are
therefore newly legal, and both of them are named files rather than a package, a prefix or a wildcard.

## What the fence still refuses

- Any importer of `integrations.mastermind_window_reader.live_window_read` outside the package and its tests
  — the exception map names only `owner_read_resource`, so the read module keeps its original closure.
- Any third file importing either Reader module: a new importer simply has no entry in the map.
- Any package-internal or package-test file: the `allowed_roots` branch runs first and is unchanged.

## Known blindness, carried as awareness rather than repaired

The AST fence is blind to package-form imports (`from integrations.mastermind_window_reader import …`) and
to `importlib`-style dynamic imports. This is PRE-EXISTING, is neither widened nor narrowed by #758, and is
recorded here so a future session does not read the fence as stronger than it is. Repairing it is a separate
piece of work with its own carrier.

## What is NOT claimed

- #758 remains DRAFT/HOLD-FOR-SOL. This decision records the fence exception's shape, not a merge, a
  browser/host binding, or any production behaviour: browser/host binding is a separate gate, and no
  enrollment, grant, #714 activation or production claim is made here.
