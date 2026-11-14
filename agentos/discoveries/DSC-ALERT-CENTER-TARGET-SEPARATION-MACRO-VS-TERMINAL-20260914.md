---
key: ALERT-CENTER-TARGET-SEPARATION-MACRO-VS-TERMINAL-20260914
claim: >
  Chris clarified that the requested redesign target is Macro's shared public
  https://www.mastermind-x.com/alerts.html page, not Terminal's authenticated /alerts workspace.
  The existing Terminal-oriented Figma work on wvVt4GTPGMqnaPprVnbloU remains useful and must be
  preserved, but it is no longer the active design target. Macro alerts.html requires a fresh
  product/experience architecture rooted in the current Alert Triage owner before new Figma work.
falsifier: >
  A later explicit Chairman instruction can change the target. Otherwise re-read Macro main's
  templates/alerts.html.j2 and engine/alert_triage.py plus the current live alerts.html route; do
  not infer the target from the older mixed shared/personal Figma prototype or PR title.
so_what: >
  Stop extending the Terminal prototype for this commission. Preserve it as a reusable Terminal
  alert-center asset. Recover Macro alerts.html current behavior, identify the user job and
  capability boundary, present design approaches for Chairman selection, and only then create the
  new Macro mockup. Reuse #7022's source-grounded explorer/evidence ideas where they fit, but do not
  inherit its visual design or treat its Draft candidate as current main.
kind: architecture
verified_at: 2026-09-14
verified_by: >
  Current Chairman correction in the live session; protected Skillpack 1.0.1 at Mastermind
  2aa28559a857461fd674fae52d2904116b854891; Macro main
  e0e3fda2fa2a44d8d64c3f0a52b9d56c1de3653b source reads; current live-page HTML and bounded
  desktop/mobile headless renders on the authorized admin Mini. No Figma writes were made after
  this target correction.
scope:
  - macro
  - alerts.html
  - terminal-alert-center-retained
confidence: verified
---

## What is now separated

### Active target: Macro Alert Center

Route family `RF.us.alerts` is `https://www.mastermind-x.com/alerts.html`, a top-level,
anonymous-accessible Macro page. Current main is built by the existing canonical chain:

`engine/alert_triage.py::build_triage` -> `scripts/build_site.py::build_alerts_page` ->
`templates/alerts.html.j2` -> `site/alerts.html`, with machine projections under the existing alert
publication plane. The triage layer remains the sole assembler. No second reader, score, event store,
identity system, queue or alert publication path is authorized by this redesign.

The active product job is shared market-change triage and investigation: tell a user what materially
changed across the market, what deserves attention now, why it matters, what evidence/limitations
support it, and where to investigate next. It is not the user's private notification inbox or alert
configuration workspace.

### Preserved asset: Terminal Alert Center prototype

The Figma connected-journey page `33:222` in file `wvVt4GTPGMqnaPprVnbloU` remains a useful design
for Terminal-style private monitoring, notification settings, email return, read/archive state and
personal history. Keep it. Do not delete, repurpose, relabel or overwrite it to make the Macro target
look complete. The second Figma file `EQlAQXIOdRdO63nMX2RK3u` remains a reference.

Private holdings/watchlist/thesis relevance, explicit monitor definitions, quiet hours, notification
preferences and per-user delivery remain under their existing F08/Terminal/account owners. Macro can
later offer a clear contextual handoff such as “Monitor this,” but that must enter the existing
private workflow rather than turning shared `alerts.html` into another authenticated alert system.

## Current Macro product archaeology

At Macro main `e0e3fda2fa2a44d8d64c3f0a52b9d56c1de3653b`, the live page already has valuable substrate:

- typed coverage states that distinguish available, clean-zero, no-coverage and unavailable;
- three-clock handling and a New York board day;
- a ranked 30-day board with source, severity, tier, lifecycle, recurrence, validation and exact
  evidence deep-links;
- current backdrop (regime, cross-asset context, risk/catalyst data);
- browser search/filtering, since-last-visit local state and shareable filter hashes;
- storyline buckets and graceful partial-evidence behavior.

Those are capabilities to preserve. The current presentation is the defect, not a reason to rebuild
its source authorities.

### Live-page evidence sampled 2026-09-14

A bounded current render returned 60 cards. Their composition was:

- 55/60 `minor`; 57/60 `watch`; only 3/60 `act`;
- 55/60 carry the same priority value `48`; the other values in the rendered board were 52, 76, 78
  and 82;
- 43/60 were re-fired;
- sources: altdata 24, themes 22, rotation 8, macro 3, commodity 2, vector 1;
- clusters: rotation 30, single-name 24, regime 3, stress 2, other 1;
- the generated HTML contains 181 help-tip nodes for a 60-card board.

Thus 90% of the board is rotation + single-name material and 91.7% has the same visible priority.
A large red/yellow score treatment therefore consumes attention without meaningfully discriminating
most rows.

The live desktop first viewport is dominated by the pressure hero, five storyline buckets, four-cell
backdrop and filters before the ranked feed. A bounded 390x900 render showed no actual ranked alert
card before the fold; it showed the hero and the start of the storyline buckets instead. This is a
user-job failure even when the underlying facts are correct.

The five current “story” cards are taxonomy clusters produced by `_storylines`; they are not a durable
cross-domain situation identity or independent confirmation. Do not make the redesign more confident
than the underlying grouping.

## Existing candidate that may be reused selectively

Macro Draft PR #7022 (`claude/alert-center-v2-astra-20260908`, exact recorded candidate
`c83a5771b54e6e487cdb2d06be45ccbf480e560d`) is a BUILT_NOT_PROVEN / Draft source-grounded
investigation candidate. It introduces an uncapped explorer, evidence inspector, observed firing
history and same-source exact-subject groupings while retaining the legacy Alert Triage authorities.
Its visual implementation is not accepted and it is far behind current main. Use it as archaeology
for useful producer/consumer capabilities, not as the new design brief and not as authority to merge.

## Current product/design diagnosis

The page is trying to be four products at once:

1. an overall market-pressure dashboard;
2. a cluster/story summary;
3. a methodology/validation explainer;
4. the actual alert investigation feed.

The actual user job is fourth, supported by the first three as context. Current hierarchy reverses
that relationship. It also prints mechanics repeatedly at glance level: priority numbers, severity,
recurrence, validation disclaimers, help tips and action labels compete with the actual change.
This conflicts with the current User-First Design Doctrine: primary dashboards must communicate the
signal, meaning and next action in seconds, with mechanics demoted behind interaction.

## No-design-yet boundary

No Macro Figma page, visual system or implementation is frozen by this discovery. The current live
page should not be recreated 1:1 merely to preserve its hierarchy. The next decision is the product
architecture: choose how much of the first screen belongs to meaningful changes, broader market
context, grouped developments and the all-alert explorer. Only after Chris accepts that direction
should Sol create the new Macro visual specification.

## Exact next action

Sol presents 2–3 Macro experience approaches grounded in this archaeology, with a recommended
architecture and explicit user journey. The recommended path should preserve `alert_triage` and
existing evidence/correction/time owners, keep personal monitoring in Terminal, and leave richer
cross-domain Situation Intelligence as an additive capability rather than a visual fiction. On
Chairman acceptance, write the Macro-specific design freeze and then start a clean Figma page/file
for the shared Macro Alert Center without modifying the preserved Terminal prototype.
