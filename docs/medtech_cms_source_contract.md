# CMS coverage-source qualification for the MedTech continuation

Status: **research qualification only**. CMS coverage is still unsupported by the current R14 runtime. This work advances the original FDA/CMS/SEC research scope without changing the FDA release candidate or enabling a new watch type.

## Sources and captured identity

The official [Coverage API documentation](https://api.coverage.cms.gov/docs/) links the [Swagger interface](https://api.coverage.cms.gov/docs/swagger/index.html). The interface exposes the actual [OpenAPI document](https://api.coverage.cms.gov/docs/v1/coverage-api.json).

On 2026-10-20 at 17:13:43 UTC, that document returned HTTP 200, OpenAPI 3.0.3, API version **1.6**, 284,894 bytes, SHA-256 `f785d57459573b5e54d01369cd04db74e14b62896a34b7b9462b5539d344fac9`. The separately published [release notes](https://api.coverage.cms.gov/docs/release_notes) last listed version 1.5; do not infer the current machine contract solely from that notes page.

The accompanying [bounded evidence receipt](evidence/medtech-cms-source-qualification-20261020.json) records exact request URLs, times, HTTP and API-envelope status, body digests, operation parameters, duplicate rows and a bounded projection of the observed records. It omits staff contacts and clinical narrative HTML. The original response-byte digests are distinct from the projected evidence-file digest.

## Qualified entry points

All sample calls below succeeded without an API key or license token. That observation applies to these national endpoints, not every endpoint in the API. Some local coding endpoints have a separate license workflow; none was invoked or accepted here.

| Operation | Required/observed parameters | Purpose |
| --- | --- | --- |
| `GET /v1/reports/national-coverage-ncacal/` | Optional `document_type`, `status`; unfiltered call qualified | Enumerate NCA/CAL native identities and report versions |
| `GET /v1/data/nca/` | `ncaid` | Current native NCA identity, status, title and last-updated date |
| `GET /v1/data/nca/tracking-sheet` | `ncaid` | Actual process milestones and separately labeled process targets |
| `GET /v1/data/nca/related-ncd` | `ncaid` | CMS-reported links to exact NCD identities/versions |
| `GET /v1/data/ncd/` | `ncdid`, optional `ncdver`; explicit version 2 qualified | Versioned NCD text metadata, effective and implementation dates |

The schema also advertises NCA history, proposed-decision memo, final-decision memo, and annual national reports. They were inspected as contracts but not exercised in this bounded sample.

A successful transport status is insufficient: inspect `meta.status.id`, `meta.notes`, `data`, and `meta.next_token`. All exercised responses had HTTP 200 and `meta.status.id = 200`. The report's next token was empty. Its operation does not advertise a general cursor/page-size interface, so production pagination behavior is not yet qualified.

Returned resource URLs such as `/data/nca?ncaid=322` omit the API's `/v1` prefix. Resolve through the known allowlisted resource/parameter mapping. Do not blindly follow arbitrary response URLs or forward credentials.

## Observed duplicate identity problem

The unfiltered report returned **298 rows**, comprising 261 NCA rows and 37 CAL rows, but only **295 distinct (document_type, document_id) identities**. Three (type, ID, version) keys appeared twice:

| Native key | Report titles for the same key |
| --- | --- |
| NCA 322, version 4, CAG-00471N | “Leadless CRT - Wireless Stimulation Endocardially (WiSE)” and “Wireless Stimulation Endocardially for Cardiac Resynchronization Therapy System (WiSE CRT)” |
| NCA 143, version 50, CAG-00274N | “Mobility Assistive Equipment” and “Wheelchairs” |
| NCA 297, version 17, CAG-00438R | “Transcatheter Edge-to-Edge Repair (TEER) for Mitral Valve Regurgitation” and “Transcatheter Mitral Valve Repair (TMVR)” |

These are observed same-key title discrepancies. They do not establish two distinct analyses or two new developments. A collector must preserve the source rows and evidence, reconcile stable native identity and title provenance, and refuse silent last-row-wins behavior. Whether every such pair is a deliberate alias remains unqualified.

The bounded receipt retains the native `last_updated_sort` field for each duplicate row. This source sorting value has no qualified timezone or public-knowledge meaning here; it must not become a publication timestamp. The owner reproduced all nine retained response digests/lengths, the complete report counts and all 54 projected native sample fields. The independent factual review assessed the schema and date semantics; its projection-key correction is incorporated.

The sampled detail/tracking response for NCA 322 uses the first title. Neither NCA detail nor tracking response echoes the report's `document_version`. Therefore an atomic version-pinned report/detail join is not yet proven. Capture independent payload hashes and clocks; qualify source-race handling before publication.

## Dates have different meanings

The official [WiSE tracking sheet](https://www.cms.gov/medicare-coverage-database/view/ncacal-tracking-sheet.aspx?ncaid=322) and sampled API returned:

| Field | NCA 322: WiSE | NCA 324: TAVR for aortic regurgitation |
| --- | --- | --- |
| CMS status | Open | Open |
| Formal request | 2026-06-03 | 2026-09-10 |
| Initial public comment period | 2026-06-03 through 2026-07-03 | 2026-09-10 through 2026-10-10 |
| Proposed decision memo due | 2026-12-03 | 2027-03-10 |
| Expected completion | 2027-03-03 | 2027-06-08 |
| Actual proposed memo date | Empty source field | Empty source field |
| Actual final memo date | Empty source field | Empty source field |

These expected/due dates describe the CMS process. They are neither approval predictions nor coverage-effective dates. “Open” remains the source status even after the initial comment window; elapsed calendar time does not authorize a new outcome label.

NCA 322's related-NCD call returned an empty array with an explicit zero-results note. That proves only that the endpoint reported no related link in this observation. It does not prove absence of Medicare coverage.

NCA 324's related-NCD response linked **NCD 355, version 2, section 20.32**, “Transcatheter Aortic Valve Replacement (TAVR).” Fetching that explicit version returned:

- Effective date: **2019-06-21**.
- Implementation date: **2020-06-12**.
- Effective end date: the literal **N/A**.
- Publication: 100-3; transmittal 217, with [the official transmittal URL](https://www.cms.gov/files/document/r217ncd.pdf).

The older linked NCD is not a 2026 approval of the new analysis. Keep NCA identity, related NCD/version and their respective dates distinct. Preserve empty strings, N/A and unknowns in raw evidence; normalized absent dates must never become today. Day-only source dates also do not supply a publication timestamp or timezone.

## Proposed next implementation boundary

Use the existing private-evidence/public-projection architecture, after separate source and product acceptance:

1. Add a bounded CMS acquisition adapter that records exact response bytes, request URLs and source clocks; validates API-envelope status, schema, duplicate keys and joins; and preserves the preceding publication on incomplete or inconsistent acquisition.
2. Keep typed CMS native identities separate from FDA submissions. Add explicit capability flags and date semantics. A source's “Open” or “Closed” is not an FDA decision or a clinical recommendation. Company/issuer linkage remains with the existing identity owner.
3. Preserve append-only observations, stable subject identity and baseline-aware changes. An alias, recapture or historical backfill must not manufacture a new coverage development.
4. Qualify source-race/version mismatches, duplicate title rows, empty links, missing/invalid dates, HTTP-200 API errors, partial responses, bounds and no-results behavior with captured and adversarial fixtures.
5. Only then design the corresponding bilingual R14 coverage views and supported watch triggers, with the Paper contract and honest unknown/unsupported states. No prospective FDA dates or calendar predictions are introduced by this CMS work.

CMS coverage evidence is factual policy context. It does not by itself qualify payment economics, adoption, revenue, issuer materiality, equity value or a recommendation. Any later promotion into an issuer-specific case requires the incumbent owners to bind the exact device, applicant, submission, indication, territory, issuer/security and retained economic rights, with separately qualified coverage, commercial and materiality evidence. Capture timestamps establish observation; day-only source dates do not establish when a fact was publicly knowable for a historical case.

### Outstanding source qualifications

- General pagination, rate-budget/retry policy, NCA version-consistent joins, arbitrary historical versions, conditional-request semantics, notification delivery, local coverage/coding license endpoints and issuer/product matching remain unqualified. SEC expansion remains a separate source contract.
- Retention and commercial-display rights for the proposed national payload and field set, including any embedded third-party content, have not been qualified by these access tests. Successful unauthenticated requests establish observed access, not blanket permission for every retention or display use. Resolve the proposed field set through the existing source owner before production CMS acquisition or publication. This dossier does not assert that the observed national metadata is prohibited.
- The official [API FAQ](https://api.coverage.cms.gov/docs/) distinguishes keyless access from endpoints requiring a license-agreement token. The [CMS AMA license page](https://www.cms.gov/license/ama) describes restrictions on embedded CPT material. Neither that token flow nor a license acceptance was exercised here. Do not treat successful national-endpoint reads as acceptance of, or exemption from, any separate third-party-content terms.

## Continuity with the existing research proposals

The older [MedTech Catalyst R1 research proposal, Macro #8182](https://github.com/mastermindx-market-intelligence/macro/pull/8182), was observed open, non-draft and unmerged at `8935a09813dc5fb9b34b2206e3b067a0d62e29d1`. Its [current research contract](https://github.com/mastermindx-market-intelligence/macro/blob/8935a09813dc5fb9b34b2206e3b067a0d62e29d1/research/medtech/MEDTECH_CATALYST_R1_RESEARCH_AND_DECISIONS_2026-09-29.md) separates regulatory, identity/rights, commercial, materiality and public-knowledge clocks. Its formal-review condition and no-auto-merge boundary remain with that proposal's owner.

The [Wave 1 commissioning proposal, Macro #8079](https://github.com/mastermindx-market-intelligence/macro/pull/8079), was observed open, draft and unmerged at `72c966f92fbb5bba468c83780ccf6f127145ac06`, with `DRAFT / HOLD-FOR-SOL` and no merge-on-green. Its [source document](https://github.com/mastermindx-market-intelligence/macro/blob/72c966f92fbb5bba468c83780ccf6f127145ac06/agentos/decisions/DEC-CATALYST-WAVE1-WEB-FIRST-FOUR-LANE-COMMISSION.md) remains a proposal until repository acceptance and permits independently ready source-family increments.

This CMS source-discovery increment does not adopt, supersede or complete either proposal. It introduces no R1-derived hold on the separately reviewed factual FDA watchdesk, and it does not qualify an investment cohort or investment-case model. The older proposals' historical checks are not current R14 release evidence.

## Evidence scope

The live reads occurred between 17:13 and 17:19 UTC on 2026-10-20. They changed no source service, production database, watch, account setting or current release head. No public comment was submitted and no license agreement was accepted. This is a reproducible contract-discovery record with exact source digests, not a claim that CMS has shipped in R14.
