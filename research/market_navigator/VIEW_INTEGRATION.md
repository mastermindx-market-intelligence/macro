# Navigator W3: responsive evidence view (code-ready; not Paper-applied)

Status: **BUILT_NOT_PROVEN** in its production integration. Synthetic browser and
deterministic cross-language proof are independent of a served, signed-in deployment.

## Contract boundary

Use the already implemented `templates/market_navigator_client.js` as the only
client-side wire admission layer. This view is a detached render callback;
it does not fetch, mount itself, choose identity, originate alerts, save state or
perform any numeric/risk synthesis. The source transport must still bind exact
subject, horizon, knowledge cutoff, permission, entitlement and upstream receipt.
The documented transport shape is `market_navigator.response/v1`, whose
`data` is the closed `market_navigator.context/v1` public projection.
Its `authority` keys are all false; status/thresholds are not trade signals.

The host can compose (after loading the two JS files and view CSS, inside its
existing authenticated scope):

```js
const view = window.MastermindNavigatorView.createView(
  document.getElementById('navigator-region'),
  {language: 'en', theme: 'dark', subjectLabel: 'SPY · NYSE Arca'}
);
const client = window.MastermindNavigatorClient.createController({
  read: (request, signal) => existingAuthorizedRead(request, signal),
  render: view.render
});
// Only on an actual user selection with verified rights and source availability:
// await client.load({subject: verifiedId, horizon: 'swing', as_of: exactCutoff});
// On auth / entitlement / account / instrument scope changes, clear before changing scope:
client.clear();
// On owner-unmount:
client.dispose();
view.dispose();
```

`existingAuthorizedRead` above is intentionally **not** implemented. The actual
application must supply the admitted existing owner read. An anonymous 401,
unsupported subject or absent original capture must render an unavailable
state, not trigger synthetic or nearest/current fallback. No direct
`view.render` of unvalidated model output is a supported source path.

## User experience

The responsive layout keeps the incumbent canonical market verdict visible
only when the owner declares it current. The measurement coverage tile counts
eligible and unavailable observations without turning missingness into zero.
Tracked scenarios render as **unranked** conditional paths, with explicit
current statuses, trigger AND conditions, invalidation OR conditions, support
and counterevidence, rule-availability clock and deadline on expansion.
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

- Python-owned synthetic `compose` + `bind_response` -> real JS client's
  `validate` -> DOM renderer -> Node test harness: source, units, clocks and
  all-no-authority flags preserved.
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
