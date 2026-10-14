# Preserve the exact Market Memory source through global sign-in

The real Google OAuth return on 2026-10-14 lost all nine exact Market Memory source keys. The retained catalog was pending; global Settings opened the onboarding sheet without running the retained panel's intent capture. An older same-tab ordinary SPY capsule survived and was restored instead.

The shared onboarding entry now freezes the current Market Memory intent before either opening an existing sheet or loading it. Ambiguous references clear stale intent and cannot initiate authentication with that old capsule. The existing intent module still owns validation, same-origin targets and callback restoration. No provider, account, entitlement or permission configuration changes.

## Evidence

Five new tests fail against released source and pass with the repair. The complete auth-return suite passes22tests, and the affected page/asset suite passes32tests. Cases cover both sheet states, loader error/timeout and duplicate reference refusal. These are deterministic synthetic tests. Both Hong Kong and Canada shared-chrome browser fixture matrices were re-executed with actual emitted theme bytes, across dark/light, EN/ZH and mobile/desktop; their generated receipts are committed separately from the historical baseline.

The original failure screenshot and provider observation are retained under the program evidence root at integration/U1_REAL_OAUTH_LOST_REFERENCE.*. Original admin browser authentication was restored after the failed Google check. The local repair is not a successful real provider return: protected source delivery, installed hash verification and another real browser round trip are still required. Catalog BUSY is a separate unresolved runtime issue under its own bounded diagnostic carrier.
