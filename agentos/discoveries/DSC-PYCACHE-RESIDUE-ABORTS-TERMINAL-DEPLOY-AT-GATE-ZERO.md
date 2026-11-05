---
key: PYCACHE-RESIDUE-ABORTS-TERMINAL-DEPLOY-AT-GATE-ZERO
claim: >
  A single `__pycache__` directory under the Terminal deploy owner's canonical
  preflight bundle killed the release at its FIRST gate, before fetch, reset, build
  or any source write, and the owner provably could not clear it. `select_preflight_artifacts`
  in ops/terminal-build.sh raised `ValueError: preflight runtime must not contain
  __pycache__` and returned 66; `__pycache__/` is gitignored, and BOTH canonical recovery
  paths in that same script run `git clean -qfd` WITHOUT `-x`, which keeps ignored paths.
  Only an out-of-band `rm -rf` cleared it. Measured on 146.190.142.17: three releases died
  this way in five days -- deploy-sol-ci-scroll-hotfix-20260924T1451Z,
  deploy-paper-research-20260925-8bc5f946 and deploy-static-boundary-repair-20260928T0025Z
  -- each rescued by a manual re-run 1-14 minutes later that selected the SAME canonical
  bundle (runtime_sha256=accd6734be898f9d0393be5772853e6d7bf19aa659a7c47be7116b2bd284b7a7).
  There was never a fallback bundle: `select_preflight_artifacts 0 "$AUTHORING_OPS_DIR"
  "$SRC/ops"` has exactly two candidates and /opt/terminal holds none of the three required
  artifacts, so .gitsrc/ops is the only bundle that has ever been selected.
falsifier: >
  A deploy log on the host containing the `preflight runtime must not contain __pycache__`
  traceback followed by ANY further `[build]` line, which would show the release continuing
  past the gate; or a successful release whose `preflight bundle selected:` line carries a
  runtime_sha256 other than accd6734..., which would show a second bundle path exists.
  Check with `grep -A2 'must not contain __pycache__' /opt/terminal/deploy-*.log` and
  `grep -h 'preflight bundle selected' /opt/terminal/deploy-*.log | sort -u`. Note that
  `ls /opt/terminal/terminal_audit` succeeding would also falsify the "only one candidate"
  half, because it would make AUTHORING_OPS_DIR a real candidate.
so_what: >
  Never reason about this failure as a degraded-but-working deploy. It is a hard stop with
  a healthy bundle present, and the retry that "fixed" it was a human deleting a directory,
  not the script recovering. Two consequences for future work. First, when adding any
  artifact-custody gate to a deploy owner, check whether the owner's own cleanup can reach
  the thing it refuses -- `git clean -fd` cannot touch gitignored paths, so a gate keyed on
  derived state is self-blocking by construction. Second, when a defect report says a later
  release "fell back" to another path, verify the claim against the release's own
  `preflight bundle selected:` line before repeating it; the fallback story was asserted on
  this defect for days and was false in both halves.
kind: landmine
verified_at: 2026-09-29
verified_by: >
  Deploy logs on root@146.190.142.17. `grep -l 'must not contain __pycache__' /opt/terminal/*.log`
  returns exactly the three logs named above; each is two lines long and ends at the FATAL.
  `ls -ld /opt/terminal/terminal_release_preflight.py /opt/terminal/terminal_source_audit.production.json
  /opt/terminal/terminal_audit` -> all three No such file or directory, so candidate 1 cannot
  match. Candidate ordering at ops/terminal-build.sh:1034; the refusal at ops/terminal-build.sh:91-258;
  `git clean -qfd` (no -x) in both recovery paths. Fixed in mastermindx-market-intelligence/mastermind-terminal#771,
  merged 541330e4c90593f0ec60918347330d3194c2c5ab, deployed 2026-09-29 19:03:07 UTC.
scope:
  - mastermind-terminal
  - ops/terminal-build.sh
  - any deploy-owner artifact-custody gate
confidence: verified
---

## Why this was invisible

The residue is gitignored, so it never appears in `git status`, never appears in a PR diff,
and survives every `git clean -fd` the owner runs. It is created by any root Python import
under the canonical `ops/` — a hand-run of the preflight script, a debugging session, a cron
that imports the package — and nothing in the deploy chain writes it deliberately. So the
population of hosts that can hit this is "any host where someone once ran Python in the
wrong directory", and the deploy that dies is the one *after* that, with no causal link
visible in either change set.

## The fix, and why half of it is non-obvious

Tolerating the residue alone is a root code-execution regression, and this is the part worth
carrying forward to any similar gate. `-B` and `PYTHONDONTWRITEBYTECODE` stop bytecode
**writes**. CPython still **reads** a source-adjacent `.pyc` in preference to the `.py`
beside it. So a gate that stops hashing `__pycache__` while still importing from that tree
lets an unhashed cache entry execute in place of the hashed source the release receipt
attests to.

The control for **reads** is `-X pycache_prefix=<dir>`, which redirects
`importlib.util.cache_from_source` for both lookup and write. It is a command-line option,
so unlike `PYTHONPYCACHEPREFIX` it survives the `-E` that the same invocation uses to drop
the ambient `PYTHON*` namespace. `SourcelessFileLoader` and `ExtensionFileLoader` never
consult `cache_from_source`, which is why loose `.pyc` and `.so` files beside the sources
must still be refused outright — `pycache_prefix` cannot neutralise them.

The negative control that proves this, from `tests/test_terminal_build_admission.py`:

| variant | result |
|---|---|
| refuse residue (pre-fix) | RED — `ValueError: preflight runtime must not contain __pycache__`, rc 66 |
| tolerate residue, no redirect | RED — `ValueError: bad marshal data (unknown type code)` — **the poisoned `.pyc` executed** |
| tolerate + redirect | GREEN |

Do not ship the first half without the second.

## What contains the residue is custody, not hashing

`PREFLIGHT_RUNTIME_SHA256` is **observational** — it is logged, never compared against a
pinned value, and never carried in the receipt. The control that stops arbitrary bytes
executing is `trusted_stat`: every directory on the path is proven owned by the expected
principal and not group/other writable. The fix therefore keeps `trusted_stat` running on
`__pycache__` itself and prunes it only from the descent, which is why a world-writable
`__pycache__` still returns 66 after the fix. Anyone reasoning about this gate as though
the digest were the security boundary will draw the wrong conclusion about what may be
safely tolerated.
