# Navigator W3: responsive evidence view (code-ready; not Paper-applied)

Status: **BUILT_NOT_PROVEN** in its production integration. Synthetic browser and
deterministic cross-language proof are independent of a served, signed-in deployment.

## Contract boundary

Use the already implemented `templates/market_navigator_client.js` as the only
client-side wire admission layer. This view is a detached render callback;
it does not fetch, mount itself, choose identity, originate alerts, save state or
perform any numeric/risk synthesis. The source transport must still bind exact
subject, horizon, knowledge cutoff, permission, entitlement and upstream receipt.
The documented transport shape is `market_navigator.response/v2`, whose
`data` is the closed `market_navigator.context/v1` public projection.
Its `authority` keys are all false; status/thresholds are not trade signals.

W3 tightens the response contract to v2: the Python binder emits a
SHA-256 binding of the exact requested instrument and the JS client checks
it against a WebCrypto SHA-256 of the current requested subject before
admitting content. This is correlation, **not authentication** or an
entitlement receipt. It does not disclose raw internal IDs or grant source
use. The client fails closed without Web Crypto (HTTPS/secure origin is
required); the browser test uses an intercepted localhost origin without
issuing external requests. An old v1 response does not silently pass.

The host can mount inside its existing authenticated page with
`market_navigator_client.js`, `market_navigator_view.js`,
`market_navigator_mount.js` and isolated view CSS. It **must** supply a
current-principal/entitlement scope token and an approved read callback:

```js
const navigatorSurface = MastermindNavigatorMount.createSurface(
  document.getElementById('navigator-region'),
  {getScope: () => existingAuthOwnerCurrentScopeKey()}
);
navigatorSurface.rebind({
  scope_key: existingAuthOwnerCurrentScopeKey(),
  subject: verifiedId, horizon: 'swing', as_of: exactCutoff,
  subjectLabel: trustedPublicLabel, language: 'en', theme: 'dark',
  read: (request, signal) => existingAuthorizedRead(request, signal)
});
// Only upon deliberate signed-in user selection:
// await navigatorSurface.activate();
// On account/entitlement/instrument change, rebind to a NEW exact scope
// before activation; old content is cleared/cancelled synchronously.
// On unmount: navigatorSurface.dispose();
```

The host callbacks above are **interfaces**, not implementations. This module
never chooses a principal, fetches its own data, stores a token or creates an
API endpoint. The new host binding checks scope again before dispatch,
after the read resolves and just before rendering, preventing a prior
account's response from flashing even if the host rebinds late. Rebind
synchronously withdraws the old instrument view. An anonymous denial, unknown
source receipt, unavailable exact capture or missing site permission remains
unavailable; it never triggers synthetic or nearest/current fallback.
A successful activation means the read call returned, not that the data
were valid, the rights admitted or a prediction qualified.

## User experience

The responsive layout keeps the incumbent canonical market verdict visible
only when the owner declares it current. The measurement coverage tile counts
eligible and unavailable observations without turning missingness into zero.
Tracked scenarios render as **unranked** conditional paths, with explicit
current statuses, deterministic bilingual "why this status" explanations
(number of unfulfilled triggers / unverified comparisons / met invalidations),
trigger AND conditions, invalidation OR conditions, support and
counterevidence, rule-availability clock and deadline on expansion.
The short diagnosis is computed only from the validated condition statuses,
without re-evaluating source values, projecting an expected return, or ranking
which condition the investor should trade.
The view does not invent a market price map, analyst narrative, expected return,
probability, saved account state or a default recommended path.

Language (English / Chinese) and light/dark controls are meaningful local
presentation toggles; they do not persist a duplicate account preference.
Expanded source details survive presentation toggles, but a new read or
failure clears the previous subject's content. Keyboard focus is preserved on
controls. Error, denied/unavailable, loading and empty states are explicitly
handled. All dynamic text is assigned via DOM `textContent`, not `innerHTML`.
Accessibility includes real headings, semantic disclosure groups, visible focus
and reduced-motion handling. The module does not inject global styles.

## Actual proof and limits

- Python-owned synthetic **completed-bar cross** (three source-timestamped
  fixture bars and an explicit non-production verifier) ->
  `qualified_observation` binary condition -> existing `compose` +
  `bind_response` -> JS client's `validate` -> DOM renderer -> Node test:
  typed clocks, units, source generation, condition status and all-no-authority
  flags preserved. This proves deterministic end-to-end *math and rendering*
  only, not real source authentication or a profitable signal.
- Eight actual Chromium combinations: 1440/390px × EN/ZH × dark/light;
  evidence disclosure, focus return, language/theme toggling and disclosure
  state preservation, no viewport overflow, no page errors, no observed
  network/storage access, and withdrawal on unavailable status.
- The separate preexisting 10-case response race/cancellation matrix remains
  authoritative for superseded responses. Do not infer production authentication,
  data rights, Paper design acceptance or analyst predictive skill.

The native Paper file is still edit-held. Paper Desktop was connected but its
approved write catalog was incompatible and its active canvas was oversize.
These sources are not claimed to be Paper-extracted JSX.

## Conditional confirmation semantics

W3 can now consume a binary source-qualified completed-bar condition from
`engine.market_navigator_price_confirmation.qualified_observation`. One
means the specifically defined event occurred at this cutoff; zero means
the defined event did not occur. Neither number is a probability. The
historical/source rules and original scenario remain attached to the existing
compositor, not a JS heuristic or an options order. Any missing, expired,
future or unauthorized evidence causes an unresolved condition instead of
a fabricated numeric zero. See `PRICE_CONFIRMATION.md`.

## Existing-owner delivery gates

1. Qualify incumbent original/current Market Memory projections through the
   actual principal/rights policy. Do not bypass the legacy guard to read
   opaque internal snapshot objects.
2. Mount this view in an existing authenticated Macro/Terminal region with
   the app's real language/theme/account controls and source admission.
3. Create a separate safe native Paper target once an authorized write
   schema is available; inspect native artboards and reconcile genuine
   design-system details and JSX without using the old file.
4. Verify failure/refresh and cross-account isolation in signed-in browser.
   For saved hypotheses, use a separately admitted extension of the actual
   user-state owner, not `lib/user_prefs` scalar settings, Capital Structure
   scenarios or the read-only Market Memory saved-output wrapper.
5. Only request live alert delivery through the incumbent explicit user-alert
   owner after its actual contract is accepted. No trade authority in W3.


The view accepts an optional, display-only subjectLabel (for example SPY / NYSE Arca).
It is not a source-receipt or entitlement claim: create the view with the
authenticated host's exact requested instrument; the incumbent Python response
binder and request-bound JS client separately enforce actual subject matching.
On instrument change the host must first dispose the old controller and
view, then create a new paired controller/view with the newly verified
request. The label is immutable for that pair, so the host cannot relabel
an older packet without withdrawing it. The presentation layer cannot
authenticate this label on its own. No user-supplied label becomes market evidence.


## Evidence-family overview (2026-10-22)
The read-only view groups already admitted observations into the existing
seven source families: price, volatility, positioning, breadth, macro,
liquidity, and events. A family with observed source rows displays a
current/total count and expands to show only the validated values and
available-at clocks. Missing, stale and not-yet-available observations
remain explicitly unavailable, without a numerical value or private source
reference. Families for which the owner supplied no observations are
combined into one small accessible disclosure, preserving the distinction
between no source rows and a source row with unavailable evidence.

The fixed taxonomy is not a weighting, confidence, confluence score,
bull/bear vote, probability or ranking. Expanded states survive a theme
or language toggle, but not an instrument/account rebind. Desktop/mobile,
EN/ZH, dark/light browser fixtures use entirely synthetic source records.


## Evidence quality and missing-observation explanation (2026-10-22)

The view now labels each current observation explicitly as **observed**
or **estimated**, using the owner-approved quality field that was already
validated by the request-bound v2 client. An available estimated gamma,
volatility or cross-asset reading is therefore never presented to readers as
a direct measurement of executed dealer orders. The estimated label also
follows current scenario condition detail and current support/counterevidence.
Unavailable, stale, user-claim and synthetic observations do not obtain a
numerical current-value badge, and no new market quality rule is invented.

When an unresolved, invalidated or waiting path contains exactly one
distinct failed/unknown observation key, its concise bilingual explanation
names that existing key (for example breadth), instead of only a count.
Multiple distinct keys remain a count: the UI cannot manufacture a
ranked "most important" condition. Full original conditions and clocks
remain expandable. Nothing here makes an estimate into a trading signal,
probability, dealer flow observation or backtested rule.
