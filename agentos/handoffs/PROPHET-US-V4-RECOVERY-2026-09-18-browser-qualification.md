---
workstream: WS:PROPHET-US-V4-RECOVERY
session: claude/prophet-lab-earnings-view-20260917
model: sol
ended_because: blocked
mission: Qualify the published native earnings browser and its integration without
  changing investment or release authority.
state_before: 'PR #7264 at a76d390a92e9c7ad86eb88684831fd8f71d3adf8 had 624 native
  tests but no executed Chromium evidence; two visual guards were held by sparse inputs.'
changed:
- path: mockups/evidence/prophet-earnings-browser-v1
  what: Canonical visual receipt and 32 real Chromium component screenshots; synthetic
    inputs/access, all real gated-access gaps retained.
- path: research/prophet_v4/earnings_view/2026-09-18-browser-qualification.json
  what: 32 functional/visual plus 24 negative-browser cases, 807-test exact-tree integration
    and guard receipts; source semantics unchanged.
prs:
- 7264
verified:
- claim: The committed controller works with the native Lab HTTP producer in real
    Chromium on declared synthetic fixtures.
  command: browser_proof.py and browser_negative_proof.py on the incumbent Studio
    evidence root
  result: 32 component states and 24 negative/lifecycle cases pass; zero page errors
    or external requests.
- claim: Canonical component evidence and runtime-style guards conclude.
  command: python3 scripts/check_ui_visual_evidence.py --diff-file <candidate-ui.diff>;
    python3 scripts/check_runtime_style_injection.py
  result: Both exit 0 after canonical worktree-scoped materialization of mockups and
    site. No sparse guard bypass.
- claim: The candidate composes with pinned main without changing source behavior.
  command: git merge-tree --write-tree --merge-base=c2ac0b8d3196cabfb84d9629b587ee3365509614
    b51d4ebcdf1a73bae3b6b9ef3632495cef107c58 a76d390a92e9c7ad86eb88684831fd8f71d3adf8;
    exact Git archive; native 14-suite pytest command in proof JSON
  result: Tree dd6780bcd1953c903d1c1e3050521be913528eac; 807 passed, zero failures/errors/skips;
    6,904 source files and seven restored inputs unchanged. Initial six missing-export-input
    failures cleared by exact Git-byte restoration, not test changes.
unverified:
- claim: Full generated dashboard and real paid-user production paths work.
  what_would_verify: Actual allowed full-page/browser execution, normal deployment
    and real entitled covered/unavailable/corrected reads.
- claim: Exact-head hosted checks and independent review authorize release.
  what_would_verify: Concluded applicable CI/security, independent reviewer return,
    fresh material-base comparison and explicit expected-head Sol release.
unresolved:
- Full-page harness extension was platform-blocked; the completed tests are component/browser
  proof, never full-product acceptance.
- Existing MastermindX1 request is unconsumed; no new worker or watch was launched.
- Original expectation-revision archive, B-17/identity/rights and separate Evaluation
  OS prerequisites remain unchanged.
next_actions:
- Keep this same PR and branch; consume exact-head CI and the actual independent review,
  without redoing the now-proven component matrix.
- Complete full-dashboard real-account/browser proof when permitted, then the ordinary
  release/deployment path.
- Keep +1y expectation revisions separate from D5 event facts and preserve the 21-session
  preregistration.
do_not_redo:
- Do not restore the old incomplete controller or create another PR/worktree for this
  implementation.
- Do not rebuild B1, D5, source collection, B-17, B3/B4, auth, CI capacity, or the
  completed composition studies.
- 'Do not force unrelated histories: the local repository is shallow; the true merge
  base was independently read from GitHub.'
danger_areas:
- A canonical screenshot manifest does not prove production authentication or independent
  taste approval.
- Integrated source test export is not a deployment and its pinned main is not automatically
  the newest main.
- No ranking, trading authority or predictive performance is granted by source/browser
  tests.
---

# Browser and source-integration qualification

The evidence closes development proof gaps without changing the original strategy, authority, or release barrier. See the exact source hashes and methods in the paired proof record.
