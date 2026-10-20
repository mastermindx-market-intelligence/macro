---
workstream: WS:BIOCATALYST-CORE-PRODUCT
session: sol/web-biocatalyst-decision-desk-r1-20261018
model: sol
ended_because: ci_handoff
mission: >
  Continue the Chairman-assigned Catalyst Intelligence program and deliver its
  decision-first BioCatalyst host without competing with the separate native
  R10 and Codex writers. This is a continuing source checkpoint, not product completion.
state_before: >
  Original PR 9611 was Draft/HOLD at 84bd28b6ae2badd444075e83e42b1390362cb068.
  Its reviewed component existed, but the actual host seam was local/unpublished.
  A Studio 502 left canonical capture effects uncertain under checkpoint 6291000963.
changed:
  - path: templates/biocatalyst_decision_desk_host.js
    what: >
      Compose the existing component, MDXAuth events, fixed WMN endpoints and
      existing authenticated loader; bind URL, account and page lifecycle without
      a new authentication, source, persistence or publication owner.
  - path: templates/biocatalyst.html.j2
    what: >
      Make Decision Desk primary; retain trial tools under a secondary disclosure,
      with explicit old trial/filter URLs preserved.
  - path: scripts/build_biocatalyst.py
    what: Emit the paired static Decision Desk assets; public allowlist changes add no API.
  - path: templates/biocatalyst_decision_desk.css
    what: >
      Compose the secondary evidence disclosure with existing tokens. A browser
      regression exposed an undefined focus token; use the existing link token
      instead of an invisible keyboard outline.
  - path: mockups/evidence/biocatalyst-decision-desk-host-r2/manifest.json
    what: >
      Retain canonical anonymous actual-page evidence, separate synthetic host
      verification, exact source hashes and honest admission/entitlement gaps.
verified:
  - claim: The interrupted capture's exact target effects were absent and no live capture remained.
    command: >
      Studio start_process PID 48253: exact staging/inventory/log/manifest existence
      checks and bounded matching-process read; original HEAD and modified source inventory.
    result: >
      Target effects NOT_APPLIED; historical dispatch not asserted. Same carrier
      continued the original targets. Completed captures have explicit exit receipts.
  - claim: The new host integrates with existing source/auth/URL lifecycles.
    command: >
      python3.12 -m pytest -q --tb=short --basetemp=.pytest_cache/host_r2_final_suite_03
      tests/test_biocatalyst_decision_desk.py tests/test_biocatalyst_page.py
      tests/test_biocatalyst_hydration.py tests/test_biocatalyst_d0a_design_contract.py
      tests/test_biocatalyst_d0b_ui.py tests/test_chat_launcher_stub.py
    result: >
      108 passed, one inherited shared-theme relative-asset test failure, 9.61s.
      Wrappers include 89 component and 20 host JS checks; counts overlap.
      Exact failures and later focus/browser refresh are recorded in the evidence.
  - claim: Real page composition works with controlled, explicitly synthetic auth/API seams.
    command: python3.12 tests/verify_biocatalyst_decision_desk_host.py
    result: >
      Before the focus-only repair: 13 behaviors, 16 layout combinations,
      eight CJK-font inspections and zero page errors passed. Final refreshed
      scope and source hashes are in the retained synthetic-host verification.
  - claim: Canonical anonymous capture retains truthful source and state evidence.
    command: >
      python3.12 scripts/capture_page_evidence.py --site-dir .pytest_cache/host_canonical_site
      --routes /biocatalyst.html --viewports desktop,mobile --locales en,zh
      --themes dark,light --max-pages 1 --settle-ms 1400
    result: >
      Same unchanged canonical tool; actual rest/hover/focus captures and PNG
      hashes are in the manifest. Authenticated-access and data-state gaps
      remain explicit. Earlier missing QA account/navigation assets were repaired,
      with superseded receipts preserved rather than relabeled.
unverified:
  - claim: Independent acceptance of this new host delta and exact-head hosted CI.
    what_would_verify: >
      A separately authored source/visual review at the exact published candidate,
      current hosted checks including Node 20, and explicit integration adjudication.
  - claim: Native admitted Company/DataOS and actual entitled deployed source-to-user proof.
    what_would_verify: >
      Existing native owners resolve source and release gates, compose the actual
      qualified inputs, and prove a real correction through shared publisher/server
      state and the authenticated Decision Desk after release authorization.
unresolved:
  - >
    All Draft/HOLD boundaries remain; publishing a review candidate does not
    authorize Ready, automatic merge, merge-to-main, deployment or activation.
  - >
    The inherited test_no_dynamic_child_asset_is_document_relative flags stock.html#
    in unchanged shared theme source. Keep its attribution and current CI verdict.
  - >
    Executive session-target lookup returned backend_unavailable. No independent
    reviewer was launched or fabricated; the old R1 review does not cover host R2.
next_actions:
  - >
    Reconcile exact original candidate/source custody and consume the final
    canonical/controlled browser evidence; publish through the original typed
    operation, never a replacement branch or copied workspace.
  - >
    Obtain exact-head independent source/visual review and hosted CI; repair
    introduced findings on this carrier while preserving native writer boundaries.
  - >
    Consume the separately reviewed native adoption and qualified DataOS result,
    then prove actual entitled source-change/correction behavior and obtain
    explicit release acceptance before activation.
do_not_redo:
  - Do not rebuild accepted R9/R10 or substitute a new publisher, identity allocator, auth client or store.
  - Do not touch the R10 chat's 9662/6712 writer or Codex native-adoption workspace.
  - Do not convert fixture-backed browser checks, local tests or this handoff into native admission.
  - Preserve the existing component and exact fixture bytes except for an evidenced material invalidator.
danger_areas:
  - Original source operation is biocatalyst-decision-desk-r1-20261018; recover its registered SSD worktree.
  - >
    Sparse materialization can prune exact manually restored data fixtures;
    preserve source hashes and restore original Git bytes, never manufacture data.
  - >
    Codex receiver 01a158fd-eaba-7342-8b59-081a483f2fc2 records the remaining native
    DataOS dependency via 9617 and actual production-host/staging denials. Neither
    this file nor fixture consistency overrides those constraints.
prs: [9611, 9662, 6712, 9617]
---

The containing source commit and `mockups/evidence/biocatalyst-decision-desk-host-r2/source-hashes.json`
identify this increment. The original parent is `84bd28b6ae2badd444075e83e42b1390362cb068`.
This checkpoint preserves ongoing project responsibility; `ci_handoff` names the
source review boundary, not an assertion that the overall program ended.

Native coordination was posted on original PR #9662 comment `6291265578`. That
carrier was observed at `902465f702a30abb943b08e792d670827a68650b`, now targeting
main, with independent CI and admission work. No native source was modified here.
