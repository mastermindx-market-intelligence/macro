---
key: HERMES-UPSTREAM-CONTRIBUTION-AUTHORIZED
question: >
  The executive_worker_policy in Mastermind's authority_map.yml denies workers
  PUSH_BRANCH and CROSS_REPO_PUBLISH, yet the org holds a verified fix for an
  upstream bug in NousResearch/hermes-agent (a persistence-failure explainer
  that blames disk-full / another-Hermes-process for owner_unavailable errors,
  a mechanism that does not exist in the gateway-owner architecture, since
  worker processes never write the SQLite state DB directly). May the org fork
  the upstream repo and open a pull request carrying this fix, and under what
  boundary?
answer: >
  Yes — decided 2026-11-10 by the Meta-CEO seat on kanban card t_7a209280
  (escalated by the chief-of-staff from t_f012c021 because the worker policy
  denies exactly these capabilities). A one-time scoped grant to the
  engineering seat: (1) create the fork
  mastermindx-market-intelligence/hermes-agent; (2) branch off upstream commit
  ba4ddf9945a213ede9dda016602a86591ed634f9; (3) apply the exact verified
  patch (sha256
  2ac227865355ba5440b7e6be5d1f21cd44eac304f4f4c28b61938fd8ef3a603f, 323
  lines, 20 files); (4) open exactly one pull request against
  NousResearch/hermes-agent main. Boundaries retained: no push exercised
  against upstream beyond the PR itself; no merge, release, or tag actions
  upstream or in the fork beyond the fix branch; the shared checkout at
  ~/.hermes/hermes-agent is never mutated (work happens in a fresh clone of
  the fork); the grant is exhausted once the PR is open; the local
  post-update re-apply hook (card t_44891beb) remains the interim durable
  home until the fix lands in a release actually installed on the estate.
rationale: >
  The bug is upstream's, not ours: the false explainer already cost two kanban
  cards and roughly a day of lsof/disk forensics, and it recurs on every
  update-fence stall, so a local-only terminal home guarantees repeated
  misdiagnosis. The patch is verified (87 i18n + explainer regression tests
  passed; 63 passed / 14 skipped classifier-adjacent) and hygiene-clean (all
  20 touched files are upstream project paths; no secrets, local paths, or
  company-internal identifiers appear in the diff). Authority rests on
  DEC-META-CEO-ORG-AUTHORITY (2026-11-07, chairman-level authority over the
  company's hosts and repos): a fork inside the org is squarely inside that
  grant, and opening a public, closable, reviewable PR to an open-source
  dependency the company runs is a reversible and transparent act, not an A7
  irreversible act, so it does not require separate Chairman sign-off — though
  this record gives the Chairman full visibility and overrule rights.
alternatives:
  - option: Local patch with post-update re-apply hook as terminal home.
    why_not: >
      Keeps a verified upstream fix out of upstream; the hook must survive
      every future update and the false explainer keeps sending operators
      down forensic dead ends. Retained only as the interim home
      (t_44891beb).
  - option: Won't-fix (revert the local change).
    why_not: >
      Rejected at t_f012c021: the fix is live and verified, and the
      misdiagnosis recurs on every update-fence stall.
  - option: Escalate the external-publish half to the Chairman before acting.
    why_not: >
      The org-authority grant plus the reversible/transparent nature of a PR
      puts this within Meta-CEO authority; the Chairman retains overrule
      rights through this record and the board.
evidence:
  - "Kanban escalation chain t_a037330b (fix + verification) -> t_f012c021 (decision + independent re-verification) -> t_7a209280 (this grant), 2026-11-10."
  - "Patch sha256 2ac227865355ba5440b7e6be5d1f21cd44eac304f4f4c28b61938fd8ef3a603f, 323 lines, 20 files (agent/turn_explainers.py, hermes_state_errors.py, tests/agent/test_turn_completion_explainer.py, 17 locale files) — re-hashed 2026-11-10; hygiene scan found no secrets, absolute local paths, or internal identifiers."
  - "Verification at t_a037330b: 87 i18n + explainer regression tests passed; 63 passed / 14 skipped classifier-adjacent."
  - "authority_map.yml executive_worker_policy denied_capabilities includes PUSH_BRANCH and CROSS_REPO_PUBLISH (re-read 2026-11-10)."
  - "gh token active with admin:org, repo, workflow scopes; repos/mastermindx-market-intelligence/hermes-agent returned 404 (no fork existed); NousResearch/hermes-agent default_branch main, fork false, org permissions push false — fork + PR is the only publish path."
  - "DEC-META-CEO-ORG-AUTHORITY (merged): chairman-level authority over company hosts/repos, with charter supremacy and A7 retained."
affects:
  - "external:NousResearch/hermes-agent (one PR)"
  - "org:mastermindx-market-intelligence/hermes-agent (fork to create)"
  - "mastermind:config/authority_map.yml (scoped exception recorded here, file unchanged)"
confidence: high
reversibility: easy
decided_by: meta-ceo-uncensored
decided_at: 2026-11-10
review_by: 2026-11-17
---

# One-time grant: fork + upstream PR for the owner_unavailable explainer fix

The estate runs NousResearch/hermes-agent as its agent harness. When the
gateway owner process is unavailable, the turn-completion explainer tells the
operator the failure may be disk-full or another Hermes process holding the
database — but worker processes never open the SQLite state DB directly in
this architecture; they RPC to the single gateway owner that owns it. The
stale explainer sends operators down lsof/disk forensics dead ends on every
update-fence stall.

The fix (t_a037330b, verified) corrects the explainer mechanism across two
source files, one regression test, and seventeen locale files. This record
authorizes its terminal durable home: fork + one upstream PR. The interim
local re-apply hook (t_44891beb) stands until the fix lands in a release
actually installed here.
