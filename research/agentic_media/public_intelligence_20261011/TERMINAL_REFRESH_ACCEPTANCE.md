# Terminal sign-in integration acceptance

Operation: `mmx-public-intelligence-delivery-20261011-local-ceo-001`.

PR956 now carries `2fd1b1a9abd197bced0366d2489613e3d6c832fa`. The prior
`a6559d38aaf69d6a2da212a01d7515b4840e43cd` CI38182377131 was cancelled on
refresh, not accepted as a completed run. Merge4292b29d903320347f97a40f583296c7843ee36a
integrated protected master857a5076fda7984df0c169635b2a399c046c0a9d, including
existing PR927 watchlist annotation sync. The subsequent2fd commit reconciled
that migration's existing ledger. Root preserved both; no migration ran here.
Current hosted proof is CI38185449454, still pending at this checkpoint.

The new shell delta was qualified against the sign-in repair on the integrated
source. Command from terminal/: `npm test -- lib/__tests__/onboardingSigninCompletion.test.tsx
lib/__tests__/passwordRecovery.test.tsx lib/__tests__/onboardingStash.test.ts
lib/__tests__/onboardingPrefsOutbox.test.ts lib/__tests__/onboardingSheetPrefsPending.test.ts
lib/__tests__/watchlistOwner.test.ts lib/__tests__/watchlistAnnotationSync.test.ts
lib/__tests__/watchlistAnnotations.test.ts && npx tsc --noEmit`.
Result:104tests,8files passed in4.43s; typecheck exited0.

Command: `TERMINAL_E2E_PORT=3186 npm run test:e2e:responsive --
e2e/onboarding-signin-completion.spec.ts e2e/password-recovery.spec.ts --workers=2
--output=../test-results/mmx-signin-2fd`.
Result:18passed in1.7m. Existing local SDK/form/router fixtures were used; no real
account or new follow was written. Outputs remain in the named local test folder.
The previous committed image set was not overwritten or restamped.

Bounded independent review used the existing installed M2 Fabric adapter:
`mmx-press-terminal956-refresh-review-20261011-001`, classreview/C2_COMPLEX_BOUNDED,
root andparent01a12a2a-d7e1-77b1-9262-ab593179dd13, remote cwd~.
The incumbent router admitted MiniMax onubuntu2, returnedrc0 and5438retained bytes,
and reported remote transport cleanup. Root consumed that exact retained result
and accepted with`accept <same-id> --by reviewer` after source/test review.
The usage receipt was missing, so no usage or cost claim is made.

The review PASS is limited to the supplied shell delta and exact onboarding
source excerpts. It does not prove the annotation-sync internals, its bundle
exclusion or database migration state. Existing identity/annotation tests and the
new integrated browser pass provide the named local evidence. Protected landing,
merged-source installation and pristine saved-credential browser behavior remain
separate, unproven release obligations.
