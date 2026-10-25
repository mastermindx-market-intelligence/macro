---
key: MASTERMIND-VENDOR-MACRO-SRC-SYMLINK-SHADOWS-THE-REPO-SCRIPTS-PACKAGE
claim: >
  In a Mastermind agent worktree, creating the conventional `vendor/macro_src` symlink to the Macro
  checkout makes `tests/conftest.py:46-47` run `sys.path.insert(0, <vendor/macro_src>)`, and the
  Macro repository ships its own REGULAR package `scripts/__init__.py` with no `ohf/` subpackage.
  Because Macro then occupies `sys.path[0]` it wins outright over the Mastermind repo's own
  `scripts/__init__.py`, so `control_plane/executive_runtime.py:95`
  (`from scripts.ohf.redaction import redact_evidence, redact_evidence_text`) raises
  `ModuleNotFoundError: No module named 'scripts.ohf'` and EVERY test module that transitively
  imports `control_plane` fails at COLLECTION, not at run time. The error names `scripts.ohf`, not
  `scripts`, which is the tell: `scripts` resolved successfully somewhere that lacks `ohf`.
  `vendor/macro_src` is untracked, but `vendor/macro` IS tracked, and a dangling `vendor/macro` is
  the normal, harmless fresh-worktree state because conftest inserts only `macro_src`.
falsifier: >
  Any of these refutes it: `ls vendor/macro_src/scripts/__init__.py` absent while the collection
  error still occurs; `PYTHONPATH=<repo root>` fixing the collection error; the same suites failing
  to collect in a worktree that has no `vendor/macro_src`; or `importlib.util.find_spec("scripts")`
  under pytest resolving to the repo's own `scripts/__init__.py` while the error persists.
so_what: >
  The symptom looks like a missing file or a sparse-checkout problem and is neither, so the three
  obvious repairs all fail and waste a full investigation: `git sparse-checkout disable` does not
  fix it (the file was already materialised), `PYTHONPATH=.` CANNOT fix it because PYTHONPATH lands
  after index 0, and there is no venv `.pth` to blame. A bare interpreter also hides the bug —
  `find_spec("scripts")` from the shell points at the worktree, because only conftest performs the
  shadowing insert. Create `vendor/macro_src` ONLY when the suites under test actually import
  `engine.*` / `lib.*` / `macro`; grep for that first. For `control_plane` / `integrations` /
  `common` suites, remove it and let conftest's documented hermetic `engine.canon` stub apply.
  Never delete `vendor/macro` to "clean up" — it is tracked; restore it with
  `git checkout -- vendor/macro`.
kind: landmine
verified_at: 2026-09-25
verified_by: >
  Fable delivery principal, 2026-09-25 01:30Z-01:45Z, establishing the IAC-P1 pre-change baseline on
  Mastermind protected master `a29161fa`. Measured first-hand in worktree
  `iac1-p1-packet-carriage-20260925`: the 14-suite envelope gate reported `7 errors during
  collection`, and the full traceback terminated at `control_plane/executive_runtime.py:95` with
  `ModuleNotFoundError: No module named 'scripts.ohf'` while `scripts/__init__.py` and
  `scripts/ohf/__init__.py` both existed in the worktree and
  `importlib.util.find_spec("scripts")` from a bare interpreter resolved to the worktree's own
  package. Discriminating comparison against the working reference worktree
  `iac1-company-inbox-ee257c8062cb977e` showed the only difference was the presence of
  `vendor/macro_src`; `ls vendor/macro_src/scripts/__init__.py` confirmed Macro's regular package.
  Removing `vendor/macro_src` took the identical gate from 7 collection errors to `668 passed` in
  63.15s; restoring the tracked `vendor/macro` symlink left it at `668 passed` with a clean tree.
scope:
  - Mastermind
  - agent worktree test harness
  - vendor/macro_src
confidence: verified
---

# The vendor/macro_src symlink shadows the repo's own `scripts` package

`ModuleNotFoundError: No module named 'scripts.ohf'` names `scripts.ohf`, not `scripts` — so `scripts`
resolved somewhere lacking `ohf`. Only conftest performs the shadowing insert, so a bare interpreter
cannot reproduce it, and `PYTHONPATH` can never fix it. Create the symlink only for suites that really
import `engine.*` / `lib.*`; never delete the tracked `vendor/macro`.
