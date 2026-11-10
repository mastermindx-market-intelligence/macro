# Build plan: current owners, explicit transitions, useful proof

This plan translates the audited Paper changes into bounded implementation work. **No production task is started by this document.** The assigned implementation session must reconcile its current source, writer, original effects, and applicable release controls before changing code.

The audit pins are recorded in [AUDIT.md](AUDIT.md). Existing programme acceptance and holds remain controlling. The broad Paper audit is not a new runtime programme or a replacement GMI, AI, OS, or Terminal control plane.

## 1. Build priorities

| Order | Bounded outcome | Existing owner / source seam | Why this comes first |
|---|---|---|---|
| B1 | Open the relationship the user actually selected, then return to their research position | Macro GMI builder/model/templates and gmi.js | The current issuer link loses selection and the destination chooses the first relationship. Motion over the wrong record would make the defect more convincing. |
| B2 | Show the context actually used by a particular AI answer | Standalone chat event dispatcher plus incumbent context-receipt contract | Selected context and consumed context currently differ in their source wiring. |
| B3 | Make Terminal replay failures and provenance understandable | Existing Large Trades client and IexDepthReplayView | Typed failures already exist but the view flattens them; users cannot tell whether to sign in, wait, change range, or retry. |
| B4 | Prove the four OS journeys using installed native owners | OS App, project workspace, compose host, Executive/Agent/source owners | Broad capability is already present in source. The next value is exact consumer proof and focused integration repairs. |
| B5 | Implement held Save/Plan capabilities only after their existing prerequisites clear | Incumbent Investigation, thesis, admission, and watch owners | A design or successful local calculation is insufficient proof of an allowed persistent effect. |
| B6 | Continue International through the correct existing design scope | R10 core contracts and the frozen R14 spec/amendments | Prevent another design rewrite or an accidental regression to old reference assumptions. |

B1–B4 are separable implementation candidates; their exact writers and source changes must be checked before parallel work. B5 is a dependent lane. This ordering is a recommendation for the next assigned builder, not authority to reopen held work.

## 2. Feature viability at the audit pins

| Feature | Evidence state | Builder implication |
|---|---|---|
| GMI taxonomy, issuer and relationship presentation | Builder/model/templates and generated output exist | Extend the existing path and its receipt projection. Do not create a second GMI app or data model. |
| GMI exact relationship selection | Source gap confirmed | Bind issuer/relationship/package identity before claiming “open this relationship.” |
| GMI lens state | Current gmi.js supports coverage/chain in the URL hash | Preserve that behavior when extending the route state. |
| GMI search/expanded groups/selection/focus/scroll across pages | Explicit cross-page restoration not found in the inspected path | Implement and prove the return contract; browser history alone is not acceptance. |
| GMI species filters | Buttons are rendered; matching handlers absent in inspected gmi.js | Wire actual filtering or present a non-interactive summary until qualified. |
| AI Go deeper | Existing Paper depth/usage confirmation preserved | Opening and cancellation remain effect-free. Only Start research confirms the request. |
| AI answer context receipts | Existing embedded-client handling; standalone chat integration gap | Share qualification semantics and bind receipts to the owning answer. |
| AI Save with monitoring off | Existing design hold; runtime owner not requalified in this audit | Keep held. No active-save-then-archive workaround. |
| OS create/open/start, send and result flows | Guarded source paths present; installed proof not collected here | Reuse native owners and test exact transitions before declaring the experience available. |
| Options local draft and bounded payoff | D08C documents reuse candidates at its earlier baseline | First confirm current component compatibility, authenticated endpoint and producer policy. |
| Native authored Options Plan save | Current closed manifest has no option_plan field | Incumbent contract/admission work and applicable #804 holds must be resolved before shipping persistence. |
| Watch activation | Separate owner effect | Preview, accepted save, and activation are separate receipts and separate user decisions. |
| International R14 | Frozen design for IM13–IM18 | Use written spec and amendments. Design freeze is not a production verdict. |

## 3. B1 — GMI selected evidence and exact return

### Input, action, result

**Input:** a user is viewing a theme or issuer, with a selected category/lens, search, expanded groups, and a particular documented relationship.

**Action:** open that named relationship or company evidence.

**Result:** the destination resolves the requested identity in the expected source/package context. It displays the right parties, claim, date and limitations, or a specific missing/changed/restricted state. It never silently substitutes model.edges[0].

### Source files to extend

- scripts/build_gmi_explorer.py: generated routes, model loading and paired assets.
- scripts/gmi_explorer/model.py: projection from incumbent taxonomy, coverage, identities, activity and relationship package.
- templates/_gmi_base.html.j2: existing shell, shared nav, theme.js, gmi.js.
- templates/gmi_issuer.html.j2: relationship links and the existing single-primary-theme presentation.
- templates/gmi_relationships.html.j2: selected detail, species controls, package receipt, source clocks and evidence.
- templates/gmi.js: URL/local selection behavior, keyboard/focus and return state.
- templates/gmi.css and required paired site outputs: layout, 44 px controls, theme treatment, reduced motion.

Do not edit the upstream graph, relationship ledger, taxonomy membership or admission rules merely to make a UI example populated. Current product identity resolution and provenance already have owners. The descriptive package is not a ranking, sizing or trading input.

### Identity and return contract

Use the existing from.issuer_id / to.issuer_id and relationship_key, scoped to package_id and package_sha256 from model.edge_package. The pinned package has a unique nonempty relationship_key for each of its 248 edges; cross-version key-generation stability was not examined. Resolve within the actual package and revalidate after refresh. These are current fields, not a new identity scheme. The table below is a behavior contract, not a new payload schema:

| Concern | Required behavior |
|---|---|
| Selected evidence | Resolve the requested issuer and relationship inside the qualified package. A display label, array index or ticker alone is not a universal relationship key. |
| Source identity | Keep the package date, source publication/knowledge/observation/effective clocks and build/read time distinct. Missing clocks remain unknown. |
| Origin position | Capture category, lens, query, expanded groups, page, selected ID, source identity, scroll and a stable opener key. |
| Direct URL | Resolve the requested entity without assuming an origin history entry. Offer a safe local return when none exists. |
| Back / Forward | Restore the visited selection and position while keeping current theme/language preferences and current access observations. Do not replay stale access from a history entry. |
| Missing opener | Restore a valid selection if possible, then focus the results heading instead of a removed DOM node. |
| Changed or removed relationship | Show that the requested item changed or is unavailable; offer the relevant issuer/list. Never open a different relationship as a fallback. |
| Package refresh | Preserve identity only when it still resolves; disclose a new package and invalidate incompatible cached detail. |
| Current access denied | Clear private detail and refuse late responses. An older cached ready state cannot restore access. |
| Failed refresh while access remains valid | Keep a clearly dated last usable answer and provide one retry action. |

The source currently displays one primary admitted/held issuer theme link. Multiple links require a deliberate selection/display contract; do not assume the existing template already handles them.

### Feature process

1. Reproduce the bare-href/first-edge mismatch using two distinct issuers and two distinct relationships in a controlled model fixture.
2. Map the incumbent identifiers and package metadata into the route/link and destination selection.
3. Wire species selection against the same qualified rows. Preserve selected/empty/unknown states and keyboard semantics.
4. Add return-state handling through the existing navigation owner; avoid a new persistent registry or global store.
5. Apply the compact mobile heading, localized topic line and 44 px hit areas from Paper.
6. Add the 200 ms ready-panel transition after correctness is proven. Reduced motion skips directly to the settled state.
7. Generate the paired outputs using the existing feature builder. Do not hand-edit site pages.
8. Exercise the real browser journey and source/access boundary before any production availability claim.

### Proof that matters

- Issuer A opens relationship A; issuer B opens relationship B.
- An unknown or removed relationship cannot fall back to another company's first record.
- Species filters alter the actual eligible list and expose meaningful empty states.
- Back/Forward, direct link and reload preserve valid identity; restore query, group expansion, scroll and focus as specified.
- Theme/language changes survive history without changing data identity.
- Access loss and late callbacks cannot reveal previous-owner evidence.
- Current population and package receipts derive from the model, not the old specimen's counts.
- Dark/light × EN/ZH at 390 px and a 320 px stress view, with no horizontal overflow; keyboard and enlarged-text checks.
- A served, qualified user path with the intended access policy. A screenshot, HTTP 200 or committed HTML file alone does not prove the full journey.

## 4. B2 — AI answer context, research depth and Save boundaries

### Context receipts

The embedded mm_brain.js consumer already qualifies receipts by origin.origin_id matching the sent origin, monotonic revision and request identity. The standalone chat dispatcher needs equivalent integration. Prefer a shared qualified consumer/helper over copied state logic.

Bind the receipt to the request and answer that actually used it. A compact “Context used” disclosure can explain what was included, excluded, unavailable or stale. Keep citations separate: choosing a context item does not make it evidence cited by the answer.

Late or foreign receipts may be retained as historical information only when the existing contract supports that. They must not replace current selection, rewrite a newer answer, or claim that the user just changed their inputs.

### Depth confirmation

“Go deeper…” opens the existing 67–68 depth/usage view. The review should show the actual eligible depth/profile and material usage implications returned by the current owner. The final Start research action is the effect boundary. Do not infer available models or quota from static Paper options.

States to qualify: ready, usage unavailable, depth unavailable, request started, denied, cancelled before transmission, and uncertain after transmission. An unknown outcome retains the original request reference; it does not create an automatic second run.

### Saving and monitoring

The existing Paper hold on Save with monitoring off remains until its incumbent path can create the intended state and return a structured receipt. An implementation must not briefly create an active monitor and then archive it to simulate an inactive save.

For a qualified save, bind account owner, record ID, revision and accepted operation receipt; then read back the saved revision. A separate monitor review and confirmation owns activation. Cancelling research or Save must not silently activate monitoring.

### Required proof

- Matching and foreign origins, stale and duplicate revisions, delayed receipts and switched conversations.
- A historical answer displayed while the current context has changed.
- A genuinely absent historical receipt rendered as unavailable, not reconstructed from today's selection.
- Opening/selecting/cancelling depth causes zero research requests; Start creates one accepted operation.
- Account change clears previous-account data and rejects late responses.
- If Save remains held, the UI accurately says so and offers safe draft/reading behavior.

## 5. B3 — Terminal replay recovery and clocks

The current client has more information than the replay view. Repair the view at the existing client boundary.

| Client state | Useful UI behavior |
|---|---|
| Loading | Keep range and controls stable; identify the pending read. |
| Ready with samples | Show observed data with the correct source/serving metadata and retained gaps. |
| Valid empty result | Explain that no observations were returned for the selection; offer another range. Do not draw a zero series. |
| Signed out | Use the existing sign-in path and preserve safe return context. |
| Denied | Hide restricted detail and explain the available access action. Do not repeatedly refetch. |
| Rate limited | Honor an actual retry interval when supplied; do not invent a countdown. |
| Invalid response | Explain that the data could not be read; retain a diagnostic reference for the owner. |
| Unavailable / error | Give a range-specific or retry action according to the actual reason. Keep a prior usable artifact only when current access still permits it. |

servedAtNs is a serving timestamp. It is not the market observation time or proof of when information became knowable. A nullable artifact hash does not justify a “verified” badge.

When refresh changes the artifact, either restore by an established observation identity or move to a clearly disclosed latest sample. Never silently retain an array index across a different artifact. Add previous/next observed-sample controls and a clear latest/reset action if the current view lacks them. Preserve ordering and missing intervals; interpolation and automatic playback require separate product justification.

Use shared semantic theme roles rather than hardcoded chart colors. Respect reduced motion without hiding historical gaps or implying real-time movement.

Proof: each typed failure produces the right action; changing account invalidates late responses; refreshing to a different artifact preserves or explicitly resets identity; source and serving clocks remain distinct; both themes and keyboard control remain legible.

## 6. B4 — Mastermind OS: prove existing transitions

Paper UX18 is a build sequence, not a replacement service specification. Keep the existing five primary destinations and project tabs. navigationPaths in App.tsx contains icon paths; do not mistake it for a URL router.

| Journey | Existing-owner rule | Required proof |
|---|---|---|
| Create → Open → Start | Creation returns the canonical project. Open refreshes the exact record. Start is a separate operation using a current eligible preview. | Lost create/open responses do not create another project; ineligible launch remains a usable project; actual model/profile/repo/base/mode comes from the current owner. |
| Read → Draft → Send | Read exact owner/reference/revision. Add an excerpt to the existing unaddressed draft; native Send remains the effect. | “Added to draft · Not sent”; undo only the unchanged insertion in the same qualified draft; mounted composer/transcript survives disclosure. |
| Run → Result → Follow-up | Bind exact work_ref/root and the result's qualified reader reference. | No recent-root substitution; completion, delivery and acceptance remain distinct; follow-up has a new accepted run and valid parent witness. |
| Return → Access → Recover | Reuse the current route, auth and operation owners. | Sign-out/owner change clears private data; unknown operation reconciles its original target/carrier; stale, withheld and unavailable remain different states. |

ProjectWorkspace consumes qualified slots. It must not independently create, read, send, pause, or persist. Compose host should mount the existing Executive provider when actually available; absence of an obsolete Launch manifest is not proof that current project execution is unavailable.

Passive conversation history is bounded managed-turn context, not a full provider transcript or Send authority. A source excerpt and a result reader have different qualified references; do not collapse them into a generic source string.

For Today's review card, use the actual artifact title and revision. “Review recipients” opens the current access/review owner and must not itself publish. The visible recipients, revision, confirmation and readback must agree before claiming a sharing change.

Acceptance is an installed authorized-user journey with exact receipts, not only source tests or a mock UI capture. Preserve current operating and resource gates; do not start a real execution merely to make a screenshot.

## 7. B5 — Options Plan and other held persistence

D08C's component inventory is a starting point for compatibility review, not fresh evidence that every component is routed or admitted at the current head.

### Viable local authoring

Reuse the existing shortlist, local draft/editor and qualified expiry calculation pipeline when their current contracts match. Preserve one-to-four-leg limits and actual input qualifications. A displayed source mark is not automatically an authored entry assumption. Once inputs change, old numerical results must not masquerade as the new calculation.

Incomplete, unavailable or unqualified responses suppress numerical results. Keep source observation time, retrieval time, EOD data and live quotes distinct. A hypothetical plan does not place an order or create a holding.

### Native Save remains dependent

The current Investigation manifest's closed v1/v2 shape has no option_plan. Do not serialize a Plan into scenario_capture or an unrelated extension field. The incumbent schema/admission work and applicable #804 release conditions must permit the exact object first.

Then use the existing revision operation and operation reader. “Saved” requires the matching owner, record, revision and accepted receipt/readback. A timeout, lost response or auth failure after transmission keeps the original pending operation for reconciliation; no automatic new Save. Account changes clear visible data and reject late callbacks without erasing the previous account's unresolved operation.

Watch preview and activation are separate. A calculation or accepted Save must not arm a watch.

### Release proof

- Closed-shape negative tests and actual admitted Plan contract, when approved.
- Exact owner/record/revision conservation through Save and reopen.
- Lost-response recovery on the original operation, with no duplicate record.
- Account switch, stale revision, denied access and unavailable admission.
- Separately confirmed watch activation with its own receipt.
- Actual production path proof after the original release holds are satisfied.

## 8. B6 — International and consolidation

Use R10 for core research pages 01–04B and page 80 contracts. Use the R14 written specification and freeze amendments for Global Surveillance IM13–IM18. Do not merge the two scopes by version number or redraw frozen artwork without a material invalidator.

The freeze decision explicitly makes written specifications and production tokens authoritative over screenshot discrepancies. Its evidence obligations remain: the actual theme/language/viewport matrix and focus captures on the real build, not a green file-existence gate alone.

Keep China in Intelligence Hub R4 and Returns in Terminal / Returns Calendar. Preserve R12/R13 and older relocated studies as references until their own disposition is established.

Do not write to the oversized MASTERMIND PAGES file. Its copy requires content parity, consumer-reference and current-writer checks before any replacement claim. The empty Jolly vase file is a cleanup candidate; QA/canary files may still support live adapter acceptance and must not be bulk-archived.

## 9. Motion reference: how to use it

Open evidence-motion-reference.html locally. It has no external assets or data requests. Its controls demonstrate dark/light, EN/ZH, reduced motion and simulated ready/read-failed/access-changed states.

Run the supplied focused source check:

```bash
node research/design_candidates/paper_audit_20261108/verify-motion-reference.cjs
```

The nine passing checks cover the reference's state transitions. They are not a browser engine, accessibility-tree audit, real access decision, or product integration test. Port the behavior into the existing owners and governed stylesheets; do not copy the reference's self-contained fixture architecture into production.

Use Signal Ink for settled display illustrations where appropriate and the existing interactive chart stack for real chart interaction. Motion should reveal a meaningful change, never manufacture freshness, confidence or magnitude.

## 10. Required implementation return

Each future implementation return should state:

1. The exact input, action and visible result changed.
2. Owning source paths, source head and qualified data/operation identities.
3. The relevant focused checks and real consumer proof.
4. What remains unavailable, held or untested.
5. Existing release/production gates and whether they were actually met.

The next assigned receiver owns recovery on the existing carrier. Historical author names are provenance, not a requirement to revive an old conversation. Preserve every live writer, explicit denial and unknown effect. No document here transfers those effects or starts background work.

