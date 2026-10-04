---
key: UIUX-VPS-ONLY-DELIVERY-20260920
question: Which release path should the Chairman-authorized macro UI/UX sweep use?
answer: >
  Use the existing macro VPS serving/update path. Do not request Vercel deployments
  or retries and do not make Vercel preview availability a release requirement for
  this explicitly VPS-only UI/UX program. Preserve all repository CI, source-custody,
  expected-head merge and production-proof gates.
rationale: >
  The current Chairman instruction is "Continue working next one, also do not use
  Vercel." The actual macro production site is already served from the governed VPS
  via /opt/macro/site.served and the locked macro-update entry point. Waiting for an
  unused preview service does not deliver a better frontend. This records the user's
  chosen deployment target; it does not green, rewrite, or suppress Vercel status,
  alter branch protection, or relax any first-party test or security gate.
alternatives:
  - option: Retry or wait for the Vercel preview quota.
    why_not: The Chairman expressly excluded Vercel from this delivery path.
  - option: Bypass repository CI or publish arbitrary branch files straight onto the server.
    why_not: VPS-only is not permission to weaken verification, custody, or the existing deployment owner.
evidence:
  - 'Current live Chairman instruction: Continue working next one, also do not use Vercel.'
  - 'PR #7450 release ruling: issuecomment-5747508199; exact-head CI and current-base integration passed before merge.'
  - 'PR #7450 VPS production acceptance: issuecomment-5747519529; public page SHA-256 36c34b13d4773925a60c71f7c4cb1a1781d04a14d1a1ab6bbe88e8562296e955 matches the released artifact.'
  - 'app/deploy/update.sh: canonical locked macro-update deployment path; installed and repository SHA-256 2c5070a4eff4f985dff631460ac80d101bb79b2d29e379db922509e0564cda29.'
affects:
  - 'site/*.html'
  - 'templates/*.j2'
  - 'app/deploy/update.sh'
confidence: high
reversibility: easy
decided_by: chairman
decided_at: 2026-09-20
---

This is scoped to the current Web Chat macro-dashboard UI/UX sweep. It does not
remove integrations or set policy for unrelated projects. No new publisher,
queue, watcher, credential, or source-of-truth owner is introduced. GitHub remains
the implementation/CI/evidence owner; the existing VPS updater remains publication
owner. The inactive merge-queue-pilot authority context is a separate non-binding
context for main under existing source law; active ci-authority/main stays binding.
