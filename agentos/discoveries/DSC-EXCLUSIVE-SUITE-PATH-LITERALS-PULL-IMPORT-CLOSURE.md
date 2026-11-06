---
key: EXCLUSIVE-SUITE-PATH-LITERALS-PULL-IMPORT-CLOSURE
claim: >
  A SOURCE-MODULE path written as a plain string literal inside a test suite owned by a
  `scope: exclusive` job pulls that module's entire transitive import closure into the job's
  inferred scope, because `curated_exclusive_closure_findings` takes the closure of
  `inferred_as_if_not_exclusive(manifest)[job].paths` and inference resolves path literals,
  not only `import` statements. Suite-path literals (`tests/...`) are harmless - test files
  are not closure members - so the failure looks arbitrary until the literal kind is noticed.
  Measured 2026-09-29 on PR #7426: four source literals in one `owned_sources` set in
  `tests/test_ci_pack.py` produced 33 uncovered paths on `ci-control-plane-contracts`, the
  whole `engine/company_intelligence/**` + `earnings_narrative/**` + `earnings_release/**` +
  `fundamental_forensics/**` + `press/**` subgraph. The regression is invisible from either
  side alone: `ci-control-plane-contracts` joined the PR code gate 2026-09-25 and that head is
  from 09-18, so payload-at-its-own-base = 0, base alone = 0, payload-on-current-main = 33.
falsifier: >
  Revert the single suite file and recompute
  `scripts.run_ci_pack.curated_exclusive_closure_findings(Path(".github/ci/legacy-jobs.yml"))`;
  then, separately, delete ONLY the source-module literals and recompute. If either still
  reports the findings, the literals are not the cause. Both returned 0 while the fully
  restored tree returned 33.
so_what: >
  Do not reflexively apply the test's own remedy text ("Widen the job's `paths:`"). Measured:
  widening `ci-control-plane-contracts` by the 33 makes BOTH the closure test and the packing
  probe pass, while adding that ~1400 weight-second job to every PR touching any of the 33
  files (1947->3347, +72%; 2248->3648, +62%). The probes cannot see it - they sit on
  `templates/index.html`, `scripts/build_free_content.py` and `engine/prophet/plan_book.py`,
  none in the subgraph - so the widening passes CI while doing exactly what that job's own
  comment forbids. Relocate the literal into a suite owned by the job that already declares
  those sources instead: measured clean, zero selection cost. Also: bisect this class
  SUBTRACTIVELY from the complete payload. An additive bisect returned 0 at every step here
  because the causing file was never re-added, flatly contradicting the A/B result.
kind: landmine
verified_at: 2026-09-29
verified_by: "scripts/run_ci_pack.py:1709 curated_exclusive_closure_findings; tests/test_ci_pack.py:4626; PR 7426 comment 5896690771"
scope:
  - macro
  - ".github/ci/legacy-jobs.yml"
  - "tests/test_ci_pack.py"
  - "scripts/run_ci_pack.py"
confidence: verified
---

Isolation table measured on the K4-G integration tree (payload merged into main pinned at
`1df73c1ac9289a21e192aeb50088a4f9119aee82`; base side re-checked clean at `877754f2053c`):

| tree state | uncovered paths |
|---|---|
| payload fully applied | 33 |
| `tests/test_ci_pack.py` alone reverted to base | 0 |
| only the four `owned_sources` literals removed | 0 |
| four literals relocated to a `prophet-lab`-owned suite | 0 |
| restored | 33 |

Two wrong turns worth not repeating. The records/docs files in the payload were suspected first
and are innocent (removing all seven leaves 33). The manifest edit was suspected second and is
innocent (`.github/ci/legacy-jobs.yml` at base still yields 33) - its only change sits under
`prophet-lab`, a different job from the one that reds.
