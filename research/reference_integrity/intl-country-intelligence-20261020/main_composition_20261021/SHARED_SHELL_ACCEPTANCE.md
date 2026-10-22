# Shared Shell acceptance boundary — principal source review

Reviewer: `/root/international_recovery_advisor`; accepted by the integration owner on 2026-10-22 UTC. No runtime execution or implementation was performed for this review.

## Supported path and precise risk

The accepted Terminal merge `e45bde2cac07ac3b29285ff70c40d68900fad62c` admits `/intl.html` as directory ID `macro:intl` in `terminal/lib/sharedShellRoutes.generated.json` (blob `efac783c589ef522d5d1301a748c4f8591a6c149`). AppShell mounts SharedShellRuntime under its enabled flag; that runtime mounts LegacyPageHost. The host blob `0295d2c9e8afa642ff441e9eeed2c3e1a995765e` remains identical at later inspected Terminal source `187bf9582b3deba2de49b597e29ccce6356333d3`.

The composed International builder writes through `lib/pages.py` and `lib/shared_shell.py`, injecting the bridge. Qualification requires the frame transport parameters, allowed parent origin, trusted INIT and admitted document/runtime metadata. Source wiring does not establish current served qualification.

Parent document/hash/Back-Forward navigation mounts a fresh child generation. The country controller's initial followHash opens the appropriate country or legacy ancestors. Child country rail links use data-imc-country and reveal their target before wrapped history navigation, so URL projection does not remove that explicit reveal. LOCATION_ACCEPTED is an acknowledgement of the latest child-initiated NAVIGATE, matched to the child's already-current canonical URL; it is not an arbitrary parent hash command.

The concrete source-level risk is the existing Data & tools link. `templates/intl_country_cockpit.html.j2` authors `href="#intl-analysis-tools"`; the active bridge projects it to an absolute parent-origin URL. The country click handler in `templates/intl_country_cockpit.js` matches only the literal fragment href. Generic bridge scrolling does not open details. On a matching ACK the bridge emits `mmx:shell-location`, but the country controller subscribes only to native hashchange. The workspace-entry subscriber handles targets within `#intl-legacy-research`, which excludes the outer tools disclosure. Therefore the outer disclosure may stay closed after the real projected toolbar link is accepted. This is a source inference, not a reproduced browser failure.

## Required focused proof

Use the actual supported parent host with the exact composed document and assets, binding parent source/build, route-registry digest, HTML/asset hashes and observed enabled runtime. Check a parent non-default country deep link; parent country-to-nested-legacy navigation and Back/Forward; child country selection with one parent history transition and retained child generation; and the real projected Data & tools and nested legacy links, including repeated-click behavior. Manually dispatched events or fabricated ACKs do not establish the actual product path. A local source-pinned parent can qualify integration behavior but not public beta DNS/TLS/auth/served acceptance.

The frozen 411 assertions and independent product/visual approval remain valid at their original scope. The new 155 standalone checks do not qualify this enabled Shared Shell path.

## Controlling source references

- https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/e45bde2cac07ac3b29285ff70c40d68900fad62c/terminal/components/chrome/shared-shell/LegacyPageHost.tsx
- https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/e45bde2cac07ac3b29285ff70c40d68900fad62c/terminal/lib/sharedShellRoutes.generated.json
- https://github.com/mastermindx-market-intelligence/macro/blob/2fed30a5a14f6bdd5e69d42c5bfcbac5814b3915/templates/shared_shell_bridge.js
- https://github.com/mastermindx-market-intelligence/macro/blob/2fed30a5a14f6bdd5e69d42c5bfcbac5814b3915/research/market_os/evidence/shared-shell-continuation-20261019/macro-608-df3-proof-config.json

Disposition: ACCEPTED / STOP. No further task or watcher armed.
