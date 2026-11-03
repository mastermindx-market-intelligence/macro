# F01 — Shared shell product and UX specification

**Version: F01/1.0.0-candidate.1. Status: PARTIAL; RIG draft; not accepted for implementation.**

Source carrier: [Macro #10645](https://github.com/mastermindx-market-intelligence/macro/pull/10645). Sole source/canvas owner for this slice: the current F01 receiver, GitHub principal mastermidx4. F02 remains with mastermindx-2 on [#10630](https://github.com/mastermindx-market-intelligence/macro/pull/10630). The [joint candidate](JOINT_SHELL_SYSTEM_CONTRACT.md), [source contracts](SOURCE_AND_DATA_CONTRACT.md), [retention ledger](FEATURE_RETENTION_LEDGER.md), [acceptance cases](ACCEPTANCE_TESTS.md) and [evidence record](EVIDENCE_AND_REVIEW.md) are one bounded package under the supplied programme, not a new programme or runtime owner.

## 1. Product outcome and scope

An investor should be able to identify where they are, find a company or existing tool, inspect evidence without sacrificing the main analytical object, move into the focused chart workspace, and return to the intended research context. This is the shell's primary job. It must not imply that a navigation action saves work, that a successful page load establishes fresh data, or that a market label changes an instrument's identity.

The candidate improves global hierarchy, local-navigation slots, destination naming, usable content width and recovery. It retains all admitted destinations, local product features, historical periods, source/data definitions, actual access decisions and saved-object owners. It does not redesign Macro analytics, Company views, Options semantics, public content, internal operations or the focused chart itself. Specimen values are illustrative and are explicitly labeled. A four-period example is a visible window, not a restriction on history.

The design is successful when a user can complete the following jobs without losing identity or interpreting unavailable information as a valid observation:

1. Start at Today, identify a relevant market destination, and open a company using its actual symbol/listing.
2. Find a similarly named tool through All tools and distinguish its exact destination.
3. Change a local analytical view, inspect a particular field or row, close evidence and continue at the same selection.
4. Open the current company's chart, investigate there, then use the named return to the captured source URL.
5. Recover from expired access, unavailable content or an uncertain save through the actual owning workflow.

These are acceptance journeys, not measured usability results. The current live/source findings and their limitations are in the evidence record.

## 2. Direction decision

**Recommend A: persistent labeled navigation on desktop, one navigation drawer on narrow screens, explicit compact mode.** A reuses the retained p-23-0 shell structure and familiar six-workspace vocabulary. It leaves the primary task on a stable horizontal alignment and provides a predictable location for All tools, AI and account access.

**Alternative B: a horizontal six-workspace masthead.** The editable B board contains the same Macro content as A, making the hierarchy comparison concrete. It frees the left edge but puts navigation, company search, utilities and localization into the same horizontal band. The expected competition at narrower widths and with longer labels is a design inference; no comparative user study has been conducted. B is a retained comparison, not an accepted replacement.

**H: compact navigation is a user choice.** It retains named accessible controls and tooltips, including market shortcuts and account entry. It must never be forced merely because an inspector opened. Its discoverability cost makes it unsuitable as the default. Tooltip labels must work on keyboard focus as well as hover; the mobile drawer remains fully labeled.

Recommendation is not acceptance. Independent product/regression and visual/taste qualification, F02 concurrence and QA01 integration review remain separate gates.

## 3. Global hierarchy and exact destinations

| Layer | User question | Candidate rule | Existing authority |
| --- | --- | --- | --- |
| Global workspace navigation | What kind of work am I doing? | Today, Discover, Analysis, Monitor, Research, Portfolio retain their destinations. | sharedShellNavigation, AppNav, MobileNav |
| Current product and location | Which tool is open? | Show a concise product title/location. A specialist route must not falsely activate Today merely because it has no mapping. | Existing route projection; F01/F03 presentation mapping |
| Market destination | Which market am I entering? | Preserve US, China, Hong Kong, Canada and International as real links. A market chooser navigates to those links. | Existing SHARED_SHELL_MARKETS and domain owners |
| Entity context | Which issuer/listing am I studying? | Show symbol, issuer and exchange/currency when provided by the domain; never infer a cross-listing from language or label. | Existing company/listing source |
| Local product navigation | Which view of this product? | Keep the domain's exact views, URL grammar and historical state. | D07, D08 and other domain owners |
| Local controls | Which observations and comparison? | Filters, period, sort, density and selected row stay with the domain. | Existing domain state |
| Evidence | Why should I trust this value? | One contextual inspector; precise identity, period, unit, source and limitation. | Domain data + F02 evidence anatomy |

Only a real destination receives current-page semantics. Within the primary job navigation, one known job may be current; an unmapped specialist route may have none. Its actual product remains named in the location/title and, where present, the exact shortcut. Do not infer current Today from a fallback. Market context is visually distinct and must not create a second competing global current-page indication. F03 and the existing exporter must qualify the exact presentation mapping before implementation; this file grants no route admission.

The six routes remain /today, /discover, /analysis, /monitor, /research and /portfolio. Market homes remain /us_stocks.html, /china.html, /hk.html, /canada.html and /intl.html. The root and focused Terminal retain their own contracts. The source contract and directory-retention audit bind the full inspected projection; these examples are not an exhaustive route registry.

## 4. Search and All tools

Keep company search and destination search separate while making the handoff visible. The global search label says “Search companies”; All tools opens the existing destination directory. Slash invokes company search and Command/Control+K invokes All tools outside editable controls. A parent-window listener does not establish shortcut support while focus is inside a cross-origin legacy document; that path remains a verification case.

All tools retains existing categories, normalized query matching, canonical-path search, result counts, explicit Show more and no speculative URL generation. Category and query remain available when the mounted dialog is reopened. At 320px, search, category and result identity stack vertically. The category control may compact into a labeled selector; all existing categories remain reachable. Every result presents a short name, product/market context and a quiet canonical destination when necessary to disambiguate.

In particular, /options, /options.html, /options_screener.html and /options/futures remain distinct. No title-based deduplication is permitted. Long specialist names wrap. The directory is a projection of admitted routes, not an admission authority or a new registry. Proposed names and aliases are reviewed through F03 and the current exporter.

Company selection uses the existing SymbolPicker and transport owner. Keep ticker/name/exchange disambiguation and current preference semantics. “Show all markets” must be described according to its actual persisted preference behavior; it is not a temporary F01-only query filter. Loading, no matches, unavailable source and retained results are separate states. F01 introduces no alternate company-search endpoint or duplicate active-symbol store.

## 5. Local navigation and retained product depth

Local tabs or links appear below product identity, not inside global navigation. Use actual link semantics when the route changes; use tabs only for an actual tabbed panel. Keep a stable selected indication, named panel and keyboard behavior. On phone, retain every view through a contained horizontal strip or an explicit “More views” control with the selected view named. Do not silently omit views to fit a screenshot.

Company retains Company/Theses/Investigations grammar and the observed Overview, Intelligence, Financials, Earnings, Market, Ownership and Lab sections. Financials retains Statements, Statistics, Revenue, Dividends and Compare, plus statement type, annual/quarterly, earlier/later periods and transcript access. Saved research and Your theses remain reachable. D07 decides their exact composition; F01 supplies the space and consistent shell behavior.

Options retains the source-owned Command, Flow, Exposure, Structure, Volatility, Statistics and Prophet hierarchy. The default /options journey is Flow → Options Tape. D08 and its slices own subviews, filters, exports, replay, temporal identity and data semantics. The F01 tape specimen tests width and evidence access; it is not a replacement Options product.

Macro keeps the D02-owned analytical sections and the D02/D03 shared-template separation. Illustrative navigation in the Macro comparison denotes the local-navigation slot, not newly admitted tabs or URLs. No local feature, model, source clock or historical record is removed by the shell candidate.

## 6. Inspectors, sidepanes and overlay coordination

An evidence trigger names its subject: “Evidence — Revenue, FY2024” or “Inspect print, 15:58:12”. Opening another object replaces the inspector's content and preserves the main view's filters, sorting, selected period and scroll. No nested inspector stack is introduced. Domain-owned deep links may identify an object; F01 does not invent an inspector query parameter.

The docked inspector is nonmodal and 320px wide, with a 24px gap. It is eligible only when at least 640px of useful primary content remains, or a larger minimum required by the actual domain object. Keyboard focus enters the requested evidence context intentionally, but Tab remains in normal page order. Closing restores the invoking control or a stable logical fallback in the selected row.

When docking fails the width rule, use a modal sidepane up to 400px wide with an appropriate viewport inset; on phone it becomes a full-width evidence screen. The background becomes inert, body scroll is locked without a layout jump, focus stays within the dialog, and the close action remains reachable above the virtual keyboard and safe-area insets. Escape first closes a child menu; otherwise it closes the active modal. The application must not trap focus in a docked panel.

Global navigation, All tools, company search, account dialogs and a modal inspector coordinate so only one top-level modal owns focus and scroll lock. Moving from drawer to directory replaces the drawer, not stacks it. Closing a transient view retains domain selection; it never declares an in-flight write cancelled. Actual D23 save/readback semantics govern pending and uncertain mutations.

## 7. Deep links, history and return context

All links retain existing admitted identities and the real parser. Ordinary query order, repeated keys, empty values, meaningful encodings and hash survive the existing transport boundary; only the two bridge transport keys are removed. Browser URL resolution can normalize relative syntax, so the promise concerns the resolved canonical contract, not every lexical spelling of an input href.

Current-chart entry captures the actual current URL. A URL-selected valid Analysis symbol takes precedence over a stale shared cursor. An explicit invalid identity cannot silently open the previous company. Generic “Open Terminal” is a separate affordance and must not pretend to be current-company entry unless it uses the same owner-qualified context.

Named return and browser Back are different actions. The existing named return may hard-navigate to the captured URL. Exact URL return, bounded legacy history restoration and complete native selection/scroll/focus restoration are three separate promises. The last is not yet proven by the inspected source or browser session. Preserve existing owners and implement/qualify any gap there; do not create another general return-state database.

Copy/share respects the same route and access boundaries. It never includes authentication material, cached private payloads or a client-generated access grant. Direct loading, refresh, new tab, browser Back/Forward, named return and malformed-link recovery all require explicit acceptance cases.

## 8. Responsive, locale and presentation behavior

The joint candidate supplies exact dimensions and content widths. There is one main page scroll owner; a table or chart that genuinely needs two dimensions owns a contained scroll region. Navigation and inspectors must not create accidental document-wide horizontal scrolling. A 12-column tape remains a complete table with local overflow and a complete-row evidence path; it must not collapse into prose that loses columns.

EN/ZH changes chrome and supported labels through the existing locale owner. It does not change region, listing, price sign convention, currency, units, source time or authored research. Public long-form articles retain their actual English-body/bilingual-chrome contract; no /zh/ URL family is introduced. Chinese labels wrap naturally using an available CJK fallback, without letter-spacing tricks or unreadable truncation.

Light/dark/auto uses the existing preference owners. Shell presentation toggles and explicit account-saved Settings have different persistence effects; the UI must not claim “saved to your account” without that owner's confirmation. The incumbent focused Terminal dark presentation remains an explicit exception pending D06-qualified change. Locale alone must not invert financial color meaning. The Chinese US-market specimen retains the same sign semantics as the English US-market specimen.

F02 owns semantic color, typography, density, icon and motion roles. Existing Paper tokens are reused where valid; proposed light roles are explicit candidate values, not silently installed tokens. Cross-repository token names are mapped by meaning, not spelling. In particular, --sp-8 has different incumbent values in different sources. All container edges are neutral; selected state uses fill and text weight. Color reinforces sign/status words and never carries the only meaning. Accessible focus outlines remain distinct from decorative colored borders.

## 9. Accessibility and quality requirements

Target WCAG 2.2 AA for the delivered implementation. Normal text must meet 4.5:1 contrast, large text 3:1, and required control/focus information its applicable non-text contrast. These are future implementation gates, not a certification of the current site. The house target for important touch controls is 44px and phone rows at least 48px; it is deliberately distinct from WCAG's 24px target-size minimum and exceptions. [W3C target size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)

At 320 CSS px and 400% zoom, the application shell reflows; only intrinsically two-dimensional content uses local overflow. Sticky chrome must not obscure keyboard focus. A skip link reaches the main content; regions, headings, tab relationships and dialog labels are semantic. Route changes move focus deliberately to the destination heading after content readiness, while same-view filters retain the relevant control. [W3C reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html), [focus not obscured](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html)

Modal focus enters the dialog, cycles within it, closes with Escape where appropriate and returns to the invoking or logical next control. Docked evidence is not modal. Announce loading/results/errors through concise status regions without reading the entire changing table. Reduced motion disables nonessential transitions; no data update should animate the whole page. Verify forced colors, text enlargement, long labels, CJK glyphs, screen-reader naming and keyboard completion. [W3C modal dialog pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/)

## 10. Implementation guidance and gates

Implement later through AppShell/AppNav/MobileNav, the scoped shared-shell stylesheet, existing search/directory, presentation owner, legacy host and domain slots. Do not add a second shell, route registry, auth store, active-symbol store, preference pump, save endpoint or Brain. Keep focused Terminal, public acquisition and internal operations as separate compositions using qualified shared primitives.

Before implementation, reconcile overlapping Terminal #1188/#1191/#1228/#1236 and merged #1226 at their then-current heads. Do not copy their changes into F01 or treat their branch state as permission. Protect lazy loading/no-prefetch and the existing catalogue-defer work: the new UI must not eagerly serialize or fetch the whole 13k-route corpus on every page. Measure navigation/search readiness and asset/DOM deltas against the actual prior build; this design exercise claims no performance improvement.

Recommended implementation sequence after qualification: (1) owner-agreed presentation mapping and exact-return invariants; (2) scoped shell geometry and retained navigation; (3) inspector coordination and focus; (4) three domain integrations at measured widths; (5) locale/theme and failure cases; (6) source-head-bound browser/keyboard/regression evidence. Each step retains its existing owner. Rollback restores presentation independently of data schemas, writes and route admission.

Implementation entry requires frozen F01/F02 references, reconciled Paper effects, actual F02 concurrence, independent product/regression and visual/taste qualification, QA01 integration disposition and retained-feature coverage. This assignment performs design/research only. It authorizes no production implementation, merge, Ready transition, enqueue, relabel or deployment.
