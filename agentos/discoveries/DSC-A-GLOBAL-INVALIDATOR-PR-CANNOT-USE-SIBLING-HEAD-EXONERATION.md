---
key: A-GLOBAL-INVALIDATOR-PR-CANNOT-USE-SIBLING-HEAD-EXONERATION
claim: >
  The standing base-side attribution rule — a red is excused when the same check NAME is
  red on >= 2 independent sibling heads — is UNSOUND for any PR that edits a global CI
  invalidator, and it fails in the dangerous direction: it says the red is YOURS. Pack
  membership is not a property of the check name; it is recomputed per head from that
  head's changed-file scope. Measured 2026-09-29 on head `99c64238b7d4` (PR #8008, edits
  `.github/workflows/daily.yml`): the run annotated `ci-pack-scope | full suite: global
  invalidator changed (.github/workflows/daily.yml)` and balanced 238 jobs across 12
  packs, putting `market-os-macro-suite-pages` in pack 11. Sibling `#8205` reported
  `ci-pack-11` SUCCESS at the same base — but its run was scope-inferred and never
  contained that job at all. So a GREEN sibling is not evidence the base is healthy, and
  a lone red sibling (`#8196`) never reaches the required two. The heuristic cannot be
  satisfied even when the base is provably at fault, because the only heads that RUN the
  failing job are the global-invalidator heads themselves. Second measured trap in the
  same incident: the failing test was data-dependent. `tests/test_macro_command_p4_copy.py`
  builds its view from `builder.read_workspace(DATA_ROOT, page)`, so the base's redness is
  a function of LAST NIGHT'S BAKE — `capital_structure` read `STALE_SOURCE`, and the
  test's NEGATIVE control (`empty is None` with the fixture flag OFF) then saw E2 ("No
  reading arrived today") instead of None, so it graded the bake rather than the gate.
  An earlier draft of this record said E2 outranks E4; that is REFUTED and the opposite
  is true — `build_macro_suite_pages.py:1281` checks the withheld gate FIRST and returns
  E4, reaching the E2 path only in its `else` branch, so with the flag ON, E4 fires even
  on a stale base (measured: `no pin, allow=True -> e4`). The confound was only ever in
  the negative control, which is what the pin removes. A local pack reproduction ALSO disagrees with CI on scope:
  `run_ci_pack.py --validate-only` off-CI reports `changed-file set unavailable` and
  balances a different assignment, so a locally computed pack index is not the pack index
  that ran.
falsifier: >
  Read the two heads' scope annotations and job sets, not their check names.
  `gh api repos/mastermindx-market-intelligence/macro/check-runs/<id>/annotations
  --jq '.[]|"\(.annotation_level) | \(.title) | \(.message)"'` on each head's `ci-pack-11`.
  The claim is false if a scope-inferred sibling's pack 11 contains the same job set as a
  global-invalidator head's pack 11, or if `ci-pack-scope` reports `full suite` on a head
  that changed no invalidator. For the data half:
  `python3 -c "import sys;sys.path.insert(0,'.');from tests import test_macro_command_p4_copy as T;print([(e['workspace_id'],(e['snapshot'] or {}).get('availability',{}).get('state')) for e in T._live_entries()])"`
  — false if `capital_structure` reads CURRENT while the test still fails.
so_what: >
  On a PR that edits `.github/workflows/daily.yml` (or any global invalidator), do NOT
  attribute a pack red by comparing check names against siblings — the comparison is
  structurally unavailable and fails closed onto you. Get the failing job BY NAME from the
  check annotations, which name it directly and cost one API call:
  `.[] | select(.annotation_level=="failure")` yields
  `legacy-job-<job>: step '<step>' exited 1`. Then ask reachability instead of similarity:
  import the failing test module and check whether ANY changed module is in `sys.modules`
  (307 modules loaded, none of this PR's — conclusive where a basename grep is not). Note
  `gh api .../jobs/<id>/logs` returns the log but `gh` REFUSES to print it when it contains
  terminal escape sequences; without `--allow-escape-sequences` the redirect reads as an
  empty body and looks exactly like "logs not ready yet". Finally, when the failing
  assertion is data-dependent, pin the fabricated view's availability to CURRENT — the
  house idiom established by #7790 — so the test grades its own gate rather than the
  freshness of last night's bake.
kind: runtime
verified_at: 2026-09-29
verified_by: "gh api repos/mastermindx-market-intelligence/macro/check-runs/109551979869/annotations + actions/jobs/109551979869/logs --allow-escape-sequences + tests/test_macro_command_p4_copy.py::test_credit_funding_e4_needs_the_capture_fixture_flag"
scope:
  - macro
  - .github/ci/legacy-jobs.yml
  - scripts/run_ci_pack.py
  - tests/test_macro_command_p4_copy.py
confidence: verified
---

Companion to `DSC:THE-W2-LEDGER-DISCRIMINATES-A-CAP-KILL-FROM-A-FOREIGN-CANCEL`: that record
says a cancelled nightly leaves the checkpoint unpublished. This one records the downstream
bill — an unpublished `capital_structure` turns a green CI pack red on the next PR that
forces the full suite, so a publication failure is not contained to the dashboard; it
propagates into the merge queue of every shared-workflow change.
