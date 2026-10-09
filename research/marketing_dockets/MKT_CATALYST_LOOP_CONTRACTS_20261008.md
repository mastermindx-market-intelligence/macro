# Catalyst Loop — frozen integration v1 (Session 00)

**Operation** `MMX-ACQ-CATALYST-INT-20261008` · **status** `DRAFT/HOLD` · **authority** current direct Chairman delivery; not permission to deploy, merge, send, or contact a partner.

## Source pins and custody

- Protected Mastermind `master`: `732cf7be88e7159b4995a8885fbd381cd1484e3e` (INDEX schema `mastermind.sol_skillpack.v1`, version `1.0.1`, bootstrap major `1`). Loaded COLD_START, ACTIVE_EXECUTION, SESSION_RELIABILITY, WEB_CEO_DELEGATION, COMMISSION_WAVE, WORKER_AVENUE_ROUTING and the two universal dialogue/routing source laws from **that** commit.
- Macro `main` at branch cut: `4fd2d0e2b2fb0eeb5d98222e01c4a8b36d9e9396`.
- Commission source: `research/marketing_dockets/MKT_CATALYST_LOOP_CHATGPT_WEB_FANOUT_20261008.md` at `49a72c605ad910b4116e6b942d00a72ff6c210eb`, Sections 0–4 and 11.
- GitHub owns implementation evidence; incumbent producer, authentication, consent, mailer, UTM and publication owners are unchanged. All Session 00 files/commits stay on `sol/mmx-acq-catalyst-int-20261008`, never in a sibling branch.
- Public `app/ticker_news.py` is **not** a free source: it requires authenticated site-full entitlement and a separate rights receipt. Do not fetch or rehost its body, scores, or text in this scan. `engine/marketing/earnings_feed.py` best-effort Finviz/free-poll items likewise lack a verified public-display rights receipt; ingestion alone does not authorize publication.
- `engine/marketing/attribution.py` already owns nightly-first-touch ledger joins (`utm_content=post_id`; opaque `user_ref`); `engine/marketing/links.py::canonical_link` owns UTM formatting. `app/mailer.py` owns ledger-first sending, suppression and uncertain SMTP outcomes; `app/unsubscribe.py` owns public HMAC unsubscribe. `email_prefs.marketing_opt_out=false` is **not** affirmative Catalyst consent.

## FROZEN public producer → scan contract (01 → 00, 03, 04)

**Authoritative read:** `engine.marketing.catalyst_scan.scan_tickers(tickers: list[str], *, event_id: str | None = None, now_utc: datetime | None = None) -> dict`. This is a **read-only** service, not a second event database. Missing/not-admitted source returns a typed `temporarily_unavailable` response, never demo text in production. No arbitrary feed URL, filename, requester identity or rights override argument.

**JSON envelope** `schema="catalyst.scan/v1"`, `schema_version=1`, `as_of_utc` (ISO-8601 UTC), `requested_tickers` (1–10 uppercase, deduped, order kept), `results` (one per requested ticker), `event_id` (stable source-backed ID or null), `generation` (monotonic event revision or null), `coverage_note` and `publication_state` (`PUBLIC_QUALIFIED|PARTIAL|UNAVAILABLE`). All fields are machine-readable; extra internal/PII fields are stripped at the **00 public serialization boundary**.

Each result: `ticker`, `status` in `SUPPORTED|NOT_COVERED|TEMPORARILY_UNAVAILABLE|RIGHTS_BLOCKED`, optional `relationship` in `DIRECT|EVIDENCED_INDIRECT|UNKNOWN`, optional `relationship_evidence_ids`, `headline`, `headline_evidence_ids` (nonempty IDs of public source receipts supporting every material headline), `what_changed` (array of `{text,evidence_ids}`), `scenarios` (array of `{case,trigger,evidence_ids}`, case BULL|BASE|BEAR), `invalidators` (array of `{text,evidence_ids}`), `sources` (array of `{source_id,url,title,published_at_utc,display_rights,rights_receipt_id}`), `as_of_utc`, `dossier_path` (same-origin allowlisted `/stocks/<TICKER>/` or null), `correction_state` (`CURRENT|CORRECTED|RETRACTED`) and `coverage_note`. For unsupported, blocked, stale or retracted results, all material claim arrays MUST be empty, and never include private body or numerical scores. Session 00 replaces all producer `coverage_note` text with fixed, public-safe status phrases; even a rights-blocked note is not blindly copied. The current scan/result `as_of_utc` must be UTC and within seven days at serialization (older becomes unavailable); independently dated source publication can be older, provided the qualified scan has a current as-of.

The producer packet backing `SUPPORTED` includes `schema="catalyst.public_event/v1"`, stable `event_id`, `event_kind`, `primary_subject`, `event_time_utc`, `first_observed_at_utc`, `as_of_utc`, separately known `publication_time_utc`, qualified `sources`, explicit `relationship_evidence_ids`, `generation`, `correction_state`, `public_safe=true` and explicit `partial_reason`. Unverified/unlicensed, ambiguous, outdated or retracted evidence MUST not enter a SUPPORTED public result. No private qbus feed read can upgrade `display_rights` to ALLOWED.

**Public eligibility invariant:** `SUPPORTED` requires `source.display_rights="ALLOWED"` and nonempty `rights_receipt_id` for every displayed source; every numerical/causal claim **including the headline** refers to at least one displayed source/evidence ID; corrected generations replace eligibility of older generations without rewriting historical-as-known. If not provable return RIGHTS_BLOCKED/UNAVAILABLE (with no body). Unknown indirect links remain UNKNOWN/NOT_COVERED. No model-originated numbers, probabilities, stock ranking, buy/sell call or market-engine scoring.

## FROZEN 00 HTTP interface (00 owns route registration)

- `POST /api/catalyst/scan` JSON `{"tickers":["NVDA","UNLISTED"],"event_id":null}`. No authentication. Exactly 1–10 unique validated tickers (uppercase normalization); return the public envelope above, or HTTP `400` bad input / `503` unavailable. JSON response `Cache-Control: no-store`. No private/paid content, event injection, arbitrary URLs or PII.
- `GET /api/catalyst/scan?tickers=NVDA,UNLISTED` equivalent anonymous JSON read for shareable scan links (tickers/event only; no email/token); `GET /api/catalyst?tickers=NVDA,UNLISTED` is the accessible server-rendered HTML fallback (same first-value service, no signup). This is an **API** link, not a guaranteed published SEO page. Avoid claiming the public HTML shell is live until Caddy, regwall, static build and browser proof exist.
- `POST /api/catalyst/optin` JSON `{"email":"…","event_id":"…","tickers":["NVDA"],"consent":true,"scope":"catalyst_event_updates/v1","attribution":{"utm_source":"…","utm_medium":"…","utm_campaign":"…","utm_content":"…"}}`. Returned `{"status":"VERIFICATION_REQUIRED","public_ref":"opaque"}` ONLY after secure owner accepts a pending request; never `verified` or `sent` on submission. Opt-in may happen only AFTER first scan in UI, not required for GET/POST scan. External UI must POST email (never encode in GET URL). Verify and suppress using existing identity/consent owner.
- Internal lifecycle seam `app.catalyst_optin.request_optin(body: dict) -> dict`; it owns verified-at, exact scope, expiry/replay, revocation, durable consent, opaque join, first-touch capture and anti-abuse. No new public email/verification endpoint is invented by 00. Worker 02 must return its separately secured verification binding before 00 can expose a confirmation route.
- Internal update seam (02-owned) `app.catalyst_optin.deliver_update(event_id: str, generation: int) -> dict` calls incumbent `app.mailer.send(cls="marketing")` with send-time suppression, unique `idem_key`, unsubscribe and real `email_log` receipt. `sent`, `queued`, `failed`, `skipped_no_smtp`, `suppressed` and `EFFECT_UNKNOWN` MUST stay distinct. No public endpoint can trigger delivery.
- 04 contract: `engine.marketing.catalyst_partner_pack.build_partner_pack(packet: dict, partner: dict, *, preview_only: bool = True) -> dict`. Use `marketing.links.canonical_link`, preserve `utm_content` as the existing post ID, require real approved partner descriptor. No inferred endorsement, send or publication.

## Cross-branch acceptance / safety matrix

| Case | Required behavior |
|---|---|
| Direct rights-qualified event | Anonymously readable, as-of UTC, independently clickable sources, useful evidence before registration |
| Evidenced indirect relationship | Must carry relation evidence IDs and cannot invent an issuer connection |
| Unsupported or unknown ticker | NOT_COVERED, no synthetic score or implied coverage |
| Unqualified rights or private qbus | RIGHTS_BLOCKED without protected text/claims |
| Stale / correction / retraction | UNAVAILABLE or corrected generation, no earlier-as-known overwrite, no stale mail |
| Invalid or 11 tickers | HTTP 400; no downstream producer invocation |
| Unverified or opted-out address | No send, no conversion qualification, no PII in public/UTM/analytics |
| Provider uncertain after DATA | No duplicate resend; classify EFFECT_UNKNOWN, do not call it failed |
| Partner link | Existing canonical UTM, only valid public source and approved real partner, no implied endorsement |

**Collision check at freeze:** #8302 editorial, #7489 outbox/media, #7493 marketing config, #6842 landing/shell build, #7258 activation-report, #8057 intelligence desk, #8186 Events & News, #7949 shared shell are still open at this pin. Their changed-path manifests do not include `app/main.py`, `app/catalyst_integration.py`, or the new integration-only tests/contract; this is NOT a lease for any other shared path. Recheck right before merging.

## Integration proof and hold

00 integrates real sibling heads **only when actual PR/head and explicit return evidence exist**; do not import proposed paths as if they exist. A staged test can inject a synthetic, conspicuously non-live source fixture to prove shape and denial behavior, but must never be relabeled real producer proof. Production still requires individually verified source rights, secure consent store, sender credentials/authority with unsubscribe, registered public page/edge gate, end-to-end hosted browser + email return, security/legal review, independent adversarial review, first operator-approved distribution and admission. **Never auto-deploy, send or merge this HOLD branch.**

## First assembled increment / security controls

Session 00 now provides `app.catalyst_integration.router` and mounts it in `app/main.py` without changing source, consent or outbound mail owners. It is opt-in activated only by separate `CATALYST_PUBLIC_ENABLED=1`; `CATALYST_OPTIN_ENABLED=1` additionally controls email submission. Absent/unimportable worker 01 or 02 adapter is `503`, not an empty success. Only verified adapter receipt `VERIFICATION_REQUIRED` + opaque ID is surfaced to a submitter (HTTP 202), never a claim that an address was verified.

- Server accepts at most 8 KiB JSON for a scan, 4 KiB for opt-in, validates 1–10 tickers before producer use; query-only requests never carry PII.
- Per-process rate protection: each visitor gets up to 30 scan requests/60 seconds or 5 opt-in requests/hour; the separate trusted Caddy peer guard is looser (2,400 scans/60 seconds or 180 opt-ins/hour) and prevents direct-origin forged claimed IPs bypassing the cap. This is defense in depth, **not** proof of fleet-wide/distributed DDoS or mail-abuse resistance. The incumbent edge and secure 02 consent owner remain the ultimate rate/anti-abuse authorities.
- Public serializer strips every unallowlisted upstream field (including private body/score/email), replaces upstream coverage notes with fixed public strings, checks valid source receipts/headline/claim evidence IDs and source URLs, validates event generation/correction and seven-day freshness; no source detail escapes rights-negative cases. These are structural defenses, **not** cryptographic proof of provider licenses: producer 01 must provide independently qualified rights receipts.
- `tests/test_catalyst_integration.py` and portable `tests/fixtures/catalyst_scan_contract_v1.json` are explicitly synthetic security/integration contract fixtures; it must never be reported as a real Earnings event, real email send or live browser proof. The test local run at code/test head `c947ef364115fdcf0e2efb13c111916d6fb1cb3c` was **20 passed** (exact test/bridge/portable fixture bytes matched GitHub blob hashes); outer source/rights, UI 03, owner 02, user-facing consent confirmation and real delivery are still gates.

**Return vocabulary:** `SPEC_ONLY` for documented siblings; `BUILT_NOT_PROVEN` for tested code without hosted/full-path proof; `PROVEN_LIVE` only with current consumer and email/browser receipts.