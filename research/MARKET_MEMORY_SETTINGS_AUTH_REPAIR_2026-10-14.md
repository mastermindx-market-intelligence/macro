# Preserve exact Market Memory evidence through sign-in and compressed responses

The real Google OAuth return on 2026-10-14 lost all nine exact Market Memory source keys. The retained catalog was pending; global Settings opened the onboarding sheet without running the retained panel's intent capture. An older same-tab ordinary SPY capsule survived and was restored instead.

The shared onboarding entry now freezes the current Market Memory intent before either opening an existing sheet or loading it. Ambiguous references clear stale intent and cannot initiate authentication with that old capsule. The existing intent module still owns validation, same-origin targets and callback restoration. No provider, account, entitlement or permission configuration changes.

## Evidence

Five new tests fail against released source and pass with the repair. The complete auth-return suite passes22tests, and the affected page/asset suite passes32tests. Cases cover both sheet states, loader error/timeout and duplicate reference refusal. These are deterministic synthetic tests. Both Hong Kong and Canada shared-chrome browser fixture matrices were re-executed with actual emitted theme bytes, across dark/light, EN/ZH and mobile/desktop; their generated receipts are committed separately from the historical baseline.

The original failure screenshot and provider observation are retained under the program evidence root at integration/U1_REAL_OAUTH_LOST_REFERENCE.*. Original admin browser authentication was restored after the failed Google check. The local repair is not a successful real provider return: protected source delivery, installed hash verification and another real browser round trip are still required. Read-slot observability is a separate carrier, PR9298. The later live catalog and saved requests returned200; that does not establish a lasting latency resolution.

## Encoded saved-response validator

A subsequent actual authenticated request returned catalog200 in2.38seconds and saved200 in969milliseconds, but the UI rejected saved_etag. Native Chrome Network search confirmed Content-Encoding:gzip and the exact packet digest followed by -gzip in the ETag. The edge's gzip/zstd representation tag is now accepted only when its full digest and encoding suffix match the actual Content-Encoding. Original generation, query, capture, source and packet checks remain unchanged. Wrong hashes, weak tags, missing or different encodings, compound encodings and arbitrary suffixes fail closed. The baseline fails2new encoding cases; the repaired normalization suite passes32tests, and the actual frontend fetch-to-commit path passes both encodings. These are local repairs pending real installed-browser verification.

## Current-main integration

The combined repair incorporates N3 citation release a828d89c through main9ab95cb6. Both browser matrices were regenerated after the actual emitted theme changed. Current-source page/assets pass32tests; combined first-frame, data and closure tests pass136 with4skipped. P0B input closure passes and Agent OS reports0errors. Historical baseline evidence is unchanged.
