---
key: MARKETDESK-SOURCE-VERIFIER-FAILS-ON-PYCACHE-FROM-A-LOCAL-PYTEST-RUN
claim: >
  Running the `research-vault-source-lineage` suite WITHOUT the hosted job's
  `PYTHONDONTWRITEBYTECODE=1` writes `__pycache__/*.pyc` and `extractor/.pytest_cache/*`
  under `collectors/marketdesk_extractor/`, and `tools/install_runtime.py::verify_source`
  then reports every such file as `unexpected` (`ok: false`, `missing: []`, `mismatched: []`),
  which fails 12 lineage tests (`test_canonical_packet_manifest_is_exact_and_complete`,
  `test_source_verifier_accepts_reviewed_current_release_evolution`, every `test_install_*`
  and `test_rollback_*`) on a head that is 360/360 green under the hosted command.
falsifier: >
  In a clean checkout run `PYTHONPATH=collectors/marketdesk_extractor/extractor/src python -m pytest -q
  tests/test_marketdesk_extractor_lineage.py collectors/marketdesk_extractor/extractor/tests/`
  twice without the env var: a second run that still reports 360 passed, or a failure whose
  `unexpected` list is empty, disproves this.
so_what: >
  Judge a local or lane verification of this packet ONLY under the verbatim hosted environment:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=collectors/marketdesk_extractor/extractor/src python -m pytest
  -p no:cacheprovider ...`. A lineage failure whose verifier output lists `.pyc` or
  `.pytest_cache` paths with `missing=[]` and `mismatched=[]` is a runner artifact, never a
  regression: delete the cache directories under the packet root and re-run before any repair
  packet, review verdict or REQUEST_REPAIR. Same class as
  DSC:PYCACHE-RESIDUE-ABORTS-TERMINAL-DEPLOY-AT-GATE-ZERO (a gitignored `__pycache__` failing a
  byte-exact preflight).
kind: landmine
verified_at: 2026-10-05
verified_by: >
  Research Vault seat 0e657eec on ubuntu1 worktree `~/lanes/wt/mo-ext-fix-8472` at PR #8472 head
  74bc480e1d6a: first run without the env var -> `12 failed, 348 passed`, every failure quoting
  `"unexpected": ["extractor/.pytest_cache/.gitignore", ..., "__pycache__/....pyc"]`; after
  `find collectors/marketdesk_extractor -name __pycache__ -o -name .pytest_cache | xargs rm -rf`
  and the verbatim command with `PYTHONDONTWRITEBYTECODE=1` -> `360 passed in 3.35s`.
  Hosted definition: `.github/ci/legacy-jobs.yml` job `research-vault-source-lineage` (folded
  into `ci-pack-10`) sets `PYTHONDONTWRITEBYTECODE=1` on its pytest step.
scope: [macro, "collectors/marketdesk_extractor/**", "tests/test_marketdesk_extractor_lineage.py"]
confidence: verified
---

## Detail

The verifier is byte-exact over the packet root by design (release lineage #8452 keeps the
immutable `RECOVERY_SHA256SUMS` beside the evolvable `SHA256SUMS`), so anything a tool writes
inside that root - bytecode, pytest's cache, an editor swap file - is a manifest violation.
The hosted job is already correct; the trap is purely local and lane-side, and it produced a
false `REQUEST_REPAIR` candidate in the F4 wave before the environment difference was found.
