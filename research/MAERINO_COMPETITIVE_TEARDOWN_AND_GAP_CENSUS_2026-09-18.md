# Maerino Competitive Teardown and Mastermind Gap Census — 2026-09-18

## Purpose

This is a bounded competitive-intelligence record, not a new program, scheduler, store,
or authority. It preserves what is actually demonstrated by Maerino, contrasts that
with current Mastermind production/source truth, and routes only the residual capability
gaps to existing canonical owners.

Operation: `maerino-competitive-gap-census-20260918-sol-001`.

Mastermind source pin for this census:
- Macro main: `1c4e91ca1d193e60c777377b22dabdc6fbb4c8a1`
- Protected Sol Skillpack: `55473bb43c3ae1908f53ddd4ccfe724643dd6c69`
- Skillpack schema/version: `mastermind.sol_skillpack.v1 / 1.0.1`

## Executive finding

Maerino is a useful benchmark for three narrow product jobs:

1. fast, company-specific post-print earnings flashes;
2. a prototype agentic forensic loop that decides what to investigate next and then
   executes those follow-up filing comparisons; and
3. concise public packaging of third-party/public telemetry, now including AI-model
   usage/adoption data as well as macro releases.

It is not evidence that Mastermind lacks the underlying research, provenance, macro,
SEC, transcript, correction, or developer/model-adoption substrate. In several of
those areas Mastermind is already materially stronger. The residual is mostly
**breadth + composition + distribution**: admit more issuers into the canonical
earnings workspace, converge richer KPI/guidance truth through FIF, adjudicate a
lawful autonomous forensic-follow-up composition boundary, and prove governed public
event distribution through existing owners.

## External Maerino evidence

### Public product surface

Observed public `maerino.com` is a launch/waitlist shell. The shipped React bundle
contains the brand animation, market-like canvas, email form, and `POST /api/waitlist`.
No public research dashboard, screener, company workspace, portfolio engine, signal
engine, or execution surface was present in the inspected bundle.

Freshness recheck on 2026-09-18 followed the production redirect to `https://maerino.com/`
and still received the same `/assets/index-DigExZkl.js` application asset observed in
the earlier teardown. The current bundle contained one `/api/waitlist` reference and
zero string occurrences for `login`, `dashboard`, `portfolio` or `screener`.
This supports the current boundary: the automated public data/social surface is ahead
of the publicly exposed application.

Public build-artifact probing also closed the obvious source-disclosure paths:
the current hashed JS source map, Vite manifest, generic asset manifest,
`manifest.webmanifest`, and raw `/src/main.jsx` / `/src/main.tsx` paths all returned
404. `GET /api/waitlist` returned 405 with `Allow: POST`. No exposed source map or
manifest was found that would justify inferring a richer hidden frontend.

Domain RDAP observed:
- registration: 2025-12-07
- registrar: Cloudflare
- Cloudflare nameservers
- current web hosting resolves to Vercel infrastructure

### Public GitHub lineage

Public GitHub owner `miketravis` has:
- `maerino-policies` — explicitly names Maerino and describes planned authenticated
  app/account behavior and Google Cloud storage;
- `forensicCompany` — Gemini-based forensic filing + earnings-call pipeline;
- `paestelAnalyst` and `paestelanalyst-frontend` — earlier FastAPI/Cloud SQL and
  React/Vercel application experiments.

This is strong ancestry evidence, not proof that any public repository is current
Maerino production source.

### Maerino social/event output

An older MaerinoResearch X status resolves through X oEmbed to the current
`@MaerinoData` account, supporting a single evolving product identity.

Observed equity flash example:
- ADUS Q1 2026: revenue growth, net income, adjusted EBITDA, operating cash flow,
  acquisitions/geographic expansion, and service mix.
- Direct status id observed through X oEmbed: `2051415342879023319`.

Observed macro output includes:
- claims: current/prior/revised values;
- payrolls: headline jobs, precise unemployment, revision aggregate, prime-age EPOP,
  LFPR and wage growth.

The macro output is useful but exposes a semantics risk. The 3.76% wage-growth value
is consistent with a not-seasonally-adjusted AHE series while other fields are
seasonally adjusted. The displayed two-month NFP revision of +66K did not reconcile
to the BLS June +11K plus July +44K = +55K revision accounting under the inspected
release. Treat this as a likely vintage/definition/calculation defect unless Maerino
publishes a definition that reconciles it.

### AI / model-usage telemetry — freshness delta

A current indexed Maerino Data post from 2026-08-31 adds a third public content family:
AI-infrastructure / model-usage telemetry. It states that open-weight models exceeded
70% of tokens through Vercel AI Gateway while remaining roughly 10-20% of spend, and
attributes the shift to DeepSeek V4 Flash, MiniMax M3 and GLM 5.3 Flash.

This should not be treated as proof of a proprietary Maerino feed. Vercel itself
publishes an AI Gateway Production Index from real gateway traffic and model/provider
pages, and its July index already reported open-weight models at 29% of tokens in June
on under 4% of spend with DeepSeek at 22.6% of token volume. The observed Maerino job is
therefore best classified as **source discovery + normalization + investable packaging
of platform telemetry**, not demonstrated exclusive data ownership.

This broadens the Maerino output taxonomy from equity + macro into technology/adoption
telemetry and reinforces that its public social feed is functioning as a lightweight
data product/acquisition surface.

## Public prototype architecture evidence

`miketravis/forensicCompany` demonstrates the following prototype loop:

```text
SEC filings + earnings-call audio
        |
        v
longitudinal filing comparison
        |
        v
management-behavior/audio analysis
        |
        v
model proposes next research questions
        |
        v
program selects company/competitor filings
        |
        v
parallel follow-up investigations
        |
        v
consolidated forensic report
```

The prototype used Gemini 2.5 Pro in its public code. That model/vendor choice must not
be projected onto current Maerino production.

The important product idea is not the model. It is the feedback loop:
**finding -> unresolved question -> evidence request -> deeper investigation -> synthesis**.

## Mastermind current capability census

### 1. Macro release intelligence

**Classification: PROVEN_LIVE core; current fast-publication edge degraded.**

Mastermind already has deterministic first-party release parsers, revision/vintage
handling, point-in-time clocks, integrity/quirk metadata, forecast contracts and
preregistered evaluation. This is stronger than the public Maerino macro semantics.

Real-path check on 2026-09-18:
- `/live/release_publications.json` is live and fresh;
- Sep 16 FOMC was `published_unparsed`;
- Sep 17 claims was `verification_delayed`.

Existing owner/carrier: Macro PR #7241. Its current head
`2935e42053d161eee00f156dd2a28ce302641094` contains the same-carrier recovery
repair and CI wiring. Binding CI remained queued at observation time. Preserve as
`BUILT_NOT_PROVEN`; do not duplicate, bypass, or blind-retry.

### 2. Public earnings transcript evidence

**Classification: PROVEN_LIVE.**

Real-path production verification:
- public Earnings Wire reported **5,581** admissible call records;
- current weekly bridge Sep 7-13 reported **50 verified call records / 600 exact facts**;
- individual records expose exact quotation, speaker, categories and receipt-bound
  excerpts;
- the weekly bridge is deterministic and advertises zero model calls.

This means Maerino does **not** have a demonstrated breadth advantage in transcript
evidence.

### 3. Canonical event workspace

**Classification: PROVEN_LIVE for a curated issuer set; PARTIAL as a general issuer plane.**

Current `production_registry()` is exactly:
- AAPL
- DHI
- PHM
- KBH
- TOL

Production real-path reads returned current `event_workspace_public_glance.v1` for
all five and 404 for KR despite KR existing in the broad Earnings Wire.

AAPL current glance showed:
- revenue `$109.4B · +16%`, exact receipt;
- Q4 revenue-growth guidance 9-11%, exact receipt;
- three exact watch claims;
- 7 structured analyst Q&A exchanges;
- consensus unlicensed;
- market reaction not joined.

DHI/PHM/KBH/TOL are live event workspaces, but their current public glance is sparse.
The internal workspace is richer than the teaser.

### 4. Deterministic release fact extraction

**Classification: BUILT and production-used on the curated issuer set.**

`engine/earnings_release/figures.py` is generic, model-free, receipt-bound extraction
with a declared concept roster including:
- revenue
- gross profit / gross margin
- operating income
- net income
- basic/diluted EPS
- operating cash flow
- capex
- revenue guidance range

The extraction law refuses values without declared basis, units, period and source.

`engine/company_intelligence/issuer_profiles.py` already provides the correct
issuer-specific seam. It currently contains:
- AAPL profile;
- DHI profile;
- PHM profile;
- KBH profile;
- TOL profile.

The four homebuilder profiles extract sector-specific net-order/cancellation facts
with byte-replayed receipts or typed absence. This is already the architectural answer
to Maerino-style sector KPI selection; it is not yet broad enough.

### 5. Rich KPI/non-GAAP/guidance convergence

**Classification: NOT_BUILT as the canonical broad convergence layer.**

Canonical owner: `WS:FINANCIAL-INTELLIGENCE-FABRIC`, wave **FIF-7**:
"Earnings, non-GAAP, KPI, and guidance convergence."

FIF-7 is `todo` and depends on FIF-3. FIF-3 remains `in_progress`; its accepted
work is golden/fixture/query substrate and production issuer service remains
not built in the current record.

Do not fork FIF-7 inside Earnings Intelligence merely to imitate Maerino.

### 6. Structured Q&A generalization

**Classification: PROVEN_LIVE on AAPL; PARTIAL / not accepted cross-issuer.**

Existing owner: `WS:EARNINGS-EVENT-INTELLIGENCE-COMPILER`.

AAPL E3-B is do-not-redo:
- 7 accepted Q&A exchanges;
- 26 management turns;
- 68 replay spans;
- live Terminal consumer.

E3-C cross-issuer format hardening remains incomplete. The prior R2 implementation
recovered structure on the development corpus but hit a second source-truth falsifier
around management-role identity. Later R3 records attempts closed unmerged. Do not
promote their conclusions as current main law.

### 7. Fundamental / filing forensics

**Classification: PROVEN_LIVE current-quarter source plane; historical/bitemporal
analyst plane PARTIAL/BLOCKED.**

Mastermind already has broad SEC current-quarter ingestion and Filing Forensics product
surfaces. The separate attested historical parity lane is not complete.

This exceeds Maerino's public prototype on provenance and current source governance,
but does not yet make the Maerino agentic follow-up loop automatic.

### 8. Follow-up research execution boundary

**Classification: interactive cited research path exists; autonomous event-triggered
forensic investigation loop is NOT_PROVEN / owner boundary unresolved.**

Current Company Event Intelligence authority already defines the user-facing path:
Company Intelligence / IR Intelligence owns the event workspace, and **Ask Mastermind**
handles cited event and cross-quarter questions through the existing Brain. The
Company Event spine assigns Neural Web / Brain the job of retrieving bounded context
and exact evidence on demand. This is the lawful interactive research surface.

The existing `engine/research_factory/` is **not** a generic document-investigation
queue. Its canonical candidate/state contracts are trial/experimental research:
Oracle/Cortex/alpha/species/external-idea and other preregistered candidate families,
with trial accounting, screening/challenge, human-review and paper/promotion states.
A company-event question such as "compare this accounting choice with two peers" does
not automatically satisfy that contract.

Search of current main found no production path that autonomously does:

`event_workspace.v1 / qa_exchange.v1 -> durable forensic investigation -> bounded
company/peer filing retrieval -> reviewed receipted finding -> event context return`.

Therefore **do not route this gap to Research Factory merely because its name contains
"research."** The composition boundary remains to be adjudicated among existing owners:

- Earnings / Company Event Intelligence: event truth and the originating question;
- Mastermind Brain / Research OS: interactive cited research experience;
- Fundamental Forensics / FIF: filing and financial-fact evidence;
- Executive/agent orchestration only if/when a durable autonomous investigation job
  is explicitly chartered.

Research Factory becomes relevant only if a returned investigation yields a separate
falsifiable investable hypothesis that legitimately fits its candidate/trial contract.
No second research queue, hypothesis store, grader or scheduler is permitted.

### 9. Cross-company economic read-through

**Classification: NOT_BUILT at issuer-mechanism hypothesis grain.**

Existing owner: `WS:ALPHA-INTELLIGENCE-INTEGRATION` K3-D.

Current source explicitly records `earnings_readthrough_hypothesis/v1` as the lawful
join and not built. K3-D must consume existing relationship/theme/market graph owners,
use exact identities, and abstain where a relationship path is unavailable.

This is separate from same-company forensic follow-up. Do not assign both jobs to one
new Maerino-parity component.

### 10. Public event distribution / X

**Classification: BUILT_NOT_WIRED for the native earnings-call derivative; broader
canonical event-to-X automation NOT_PROVEN.**

Current main `engine/marketing/earnings_call_lane.py` states plainly that its
deterministic Chronicle earnings-call derivative is **"NOT WIRED TO ANYTHING TODAY"**:
no engine/script/app/workflow calls `enqueue_event` or `run_ledger`; only tests do.
The module itself already reuses the canonical Marketing outbox, routing, story lock,
copy validation, preflight/dedupe, card publishing and value gate, and it explicitly
refuses unlabeled correction duplicates.

This matters competitively because Maerino demonstrably uses public social event
distribution as a product/acquisition surface. Mastermind has the safer projection
machinery but not a proven live CEI -> X path.

Do **not** answer this by creating another scheduler or publisher. Existing X Growth /
Marketing owns distribution. Any future activation must reuse the current outbox,
approval/value/copy gates, correction semantics and persona/cadence controls, and must
prove a natural real event reaches the intended channel without historical flood.

### 11. AI / developer adoption telemetry

**Classification: PROVEN_LIVE adjacent Mastermind family; exact Vercel-Gateway usage
source not found in current source.**

Mastermind already operates a public Alternative Data desk with:
- Hugging Face model-download velocity / WoW adoption;
- GitHub developer-adoption momentum;
- issuer-level joins that combine app demand, developer activity, model downloads,
  patents and other contextual evidence;
- an accountable outcome scorecard rather than assuming the telemetry is predictive.

Real-path check on 2026-09-18 showed the live Alternative Data page publishing an
"AI model adoption" table (Hugging Face downloads + WoW) and a "Developer adoption"
table (GitHub stars + WoW), with the source legend explicitly naming Hugging Face and
GitHub. Current source also contains the Hugging Face collector and
`hf_model_momentum` family, while the Signal Lab research estate has already examined
NPM, PyPI and Hugging Face adoption families.

No current Vercel AI Gateway model-share collector was found. That is a **source-specific
coverage delta**, not evidence that Mastermind needs another telemetry plane. If a
future source census shows incremental economic information, rights and stable clocks,
route it through the existing Alternative Data / Signal Lab ownership one source at a
time. Do not create a Maerino AI-usage parity program.

## Disagreement / boundary ledger

| Claim | Evidence | Ruling |
|---|---|---|
| "Mastermind only does AAPL earnings" | AAPL Q&A is the flagship, but production registry also includes four homebuilders and public Wire has 5,581 calls | False / too broad |
| "Maerino is broader on transcripts" | Mastermind production Wire breadth and weekly receipts | Not demonstrated |
| "Mastermind lacks sector-specific KPIs" | `IssuerProfile` + four homebuilder extractors | False architecturally; breadth remains limited |
| "Mastermind already has broad KPI convergence" | FIF-7 is todo | False |
| "Research Factory solves Maerino follow-up already" | Factory candidate schema is alpha/trial-oriented, while Company Intelligence already routes cited questions to Brain | False; autonomous forensic composition remains unproven |
| "Current macro publication is healthy" | latest FOMC/claims degraded on public feed | False at current edge; #7241 owns repair |
| "Economic read-through is ready" | K3-D current state says not built | False |
| "Mastermind already auto-publishes CEI earnings intelligence to X" | `engine/marketing/earnings_call_lane.py` says no runtime caller exists | False; guarded projection is built but unwired |
| "Maerino has a unique AI-adoption telemetry plane Mastermind lacks" | Maerino packages Vercel AI Gateway usage; Mastermind live Alt Data already publishes Hugging Face model downloads + GitHub adoption | Not demonstrated; exact source coverage differs |

## Residual capability docket — existing owners only

### Gap A — broad canonical issuer admission

Owner: `WS:EARNINGS-EVENT-INTELLIGENCE-COMPILER` / Earnings Intelligence.

Job:
- generalize issuer admission and structured Q&A without source-specific fabrication;
- preserve the five-issuer production registry and AAPL 7/26/68 oracle;
- admit a second issuer only when non-empty source-supported structure reaches a real
  consumer.

This is the immediate earnings breadth dependency.

### Gap B — broad post-print KPI/guidance convergence

Owner: FIF-7, after FIF-3 dependency is lawfully ready.

Job:
- converge GAAP, non-GAAP, issuer/sector KPIs and guidance onto one source-backed fact
  authority;
- reuse `earnings_release` receipts and `IssuerProfile` seam;
- do not create a second metric registry or guessed beat/miss plane.

Maerino is useful pressure to make this user-visible and fast, not justification to
skip FIF dependencies.

### Gap C — fast event synthesis / presentation

Owner: Earnings Intelligence consumer/product layer, consuming A/B truth.

Current Terminal can render all event facts in Results, but the top-level deterministic
presentation is deliberately narrow. A future fast flash should be a **selection and
presentation** over receipted canonical facts, not an LLM-authored truth layer.

Target output:
- headline financials;
- material issuer/sector KPIs;
- guidance deltas where legally available;
- capital-allocation / strategic-event facts when sourced;
- evidence link for every item;
- correction rebuild behavior;
- typed absence instead of guessed completeness.

### Gap D — event-triggered forensic follow-up

**Owner: unresolved composition boundary; do not assign to Research Factory by name.**

Known owner pieces:
- Earnings / Company Event Intelligence owns the receipt-bound event/question context;
- Brain / Mastermind Research OS already owns interactive cited event research;
- Fundamental Forensics/FIF owns filing and financial-fact evidence;
- Research Factory remains reserved for candidates that satisfy its experimental/trial
  contract, not generic document investigations.

Target capability:
```text
receipt-bound event fact / Q&A claim
 -> open question / anomaly
 -> bounded company + peer evidence request
 -> cited filing/event investigation
 -> reviewed receipted finding
 -> event/company context return
```

The next architecture action is **owner/composition adjudication**, not implementation.
It must either reuse an existing durable deep-investigation/job carrier or explicitly
extend the current Research OS/agent execution boundary without creating a second
queue/store/control plane. First capability proof should be one real event, one useful
follow-up question, one bounded peer/company investigation, and one returned receipted
finding visible in the original research context. Infrastructure-only closure is not
accepted.

### Gap E — economic propagation / read-through

Owner: Alpha Intelligence K3-D.

Do not merge with Gap D. K3-D owns cross-company mechanism/read-through hypothesis
semantics and the honesty-preserving graph join.

### Gap F — current macro fast-publication recovery

Owner: existing PR #7241 carrier.

Hold until binding CI and same-carrier release gates complete; then require installed
and production/natural-heartbeat proof.

### Gap G — governed public event distribution

Owner: existing X Growth / Marketing distribution system.

Current source already contains the deterministic `earnings_call_lane`, canonical
outbox reuse, story locks, card/value/copy gates and correction refusal. What is absent
is the live producer/wiring proof.

This is an **operator/product activation decision**, not a greenfield build:
- choose the canonical event/story producer that is allowed to originate the derivative;
- connect only through the existing outbox/publisher authority;
- preserve first-deploy age/event caps so history cannot flood the channel;
- require one natural new event to produce a real channel receipt;
- keep X copy display/context-only and never let publication become trade authority.

Do not arm this lane merely to imitate Maerino; activate only when source coverage,
channel custody and current marketing policy gates are satisfied.

## Priority order

No new Maerino program should be created.

1. Preserve and finish the already-active **Earnings E3-C** generalization rather than
   reopening AAPL.
2. Keep **FIF-3 -> FIF-7** dependency honest; when FIF-7 is admissible, use Maerino as
   product pressure for fast broad KPI/guidance coverage.
3. Adjudicate the **event -> autonomous forensic follow-up** composition boundary.
   Reuse Brain/Research OS and FIF evidence where they already own the job; do not
   force document investigations into Research Factory's alpha/trial candidate model
   or create a second queue/store/control plane.
4. Let **K3-D** own later cross-company read-through.
5. Let **#7241** finish the current macro recovery on its existing carrier.
6. Treat CEI -> X as an **existing-lane activation/proof** problem under X Growth /
   Marketing, not a new distribution system; do not arm it from this census.
7. Treat Vercel AI Gateway usage as a **source-expansion candidate** inside existing
   Alternative Data / Signal Lab ownership only if it survives rights, clock,
   incremental-information and consumer-value review; no parity lane is created.

## 10/10 end-state

The leapfrog product is not "Maerino with more fields." It is:

```text
event observed
 -> exact source/vintage/correction identity
 -> deterministic facts + issuer-specific KPIs
 -> structured management Q&A
 -> fast material event digest
 -> governed product/social derivative from the same corrected fact packet
 -> unresolved questions / anomalies
 -> governed autonomous follow-up research
 -> peer and historical evidence
 -> economic read-through hypotheses where relationship evidence exists
 -> market-incorporation context
 -> Neural Web / Terminal / portfolio context
```

Every visible item remains traceable to a receipt or an explicit typed absence.
Research findings remain context until independently validated for any stronger
authority. No summary, sentiment score or competitor-inspired shortcut may directly
rank, size, gate or originate trades.

## Sources / recovery anchors

External:
- https://www.maerino.com/
- https://github.com/miketravis/maerino-policies
- https://github.com/miketravis/forensicCompany
- https://github.com/miketravis/paestelAnalyst
- https://github.com/miketravis/paestelanalyst-frontend
- X status 2051415342879023319 (older MaerinoResearch identity resolves to MaerinoData)
- Vercel AI Gateway Production Index — July 2026
- Vercel AI Gateway model pages for DeepSeek V4 Flash, MiniMax M3 and GLM 5.3 Flash

Mastermind:
- `agentos/workstreams/WS-EARNINGS-EVENT-INTELLIGENCE-COMPILER.md`
- `agentos/workstreams/WS-EARNINGS-INTELLIGENCE-OS.md`
- `agentos/workstreams/WS-FINANCIAL-INTELLIGENCE-FABRIC.md`
- `agentos/workstreams/WS-FUNDAMENTAL-FORENSICS.md`
- `agentos/workstreams/WS-CALCBENCH-FILING-FORENSICS-PARITY.md`
- `agentos/workstreams/WS-ALPHA-INTELLIGENCE-INTEGRATION.md`
- `engine/earnings_release/figures.py`
- `engine/company_intelligence/issuer_profiles.py`
- `engine/company_intelligence/event_workspace_build.py`
- `engine/marketing/earnings_call_lane.py`
- `engine/altdata.py`
- `engine/altdata_models.py`
- `collectors/huggingface.py`
- `templates/alt_data.html.j2`
- `research/earnings_intelligence/E0_E1_E2_CONTRACT_FREEZE.md`
- `research/economic_propagation/D0_THREE_GRAPH_SEPARATION_MAP.md`
- `research/COMPANY_EVENT_INTELLIGENCE_SPINE_AND_PREMIUM_IR_SUITE_BUILD_DOCKET_2026-08-01.md`
- `engine/research_factory/schema.py`
- public production: `/stocks/earnings/`, `/api/event-workspace/{ticker}`,
  `/live/release_publications.json`
