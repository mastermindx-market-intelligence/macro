# Vercel migration: dormant live-data origin candidate

**Workstream:** WS:MARKET-OS · **Operation:** `vercel-backend-origin-20261104-web`
**Base:** Macro `f07bcc766145921b9dabe24e20a79650c0e85f92`; proposed source-only addition, not deployed.
**Vercel frontend source:** Terminal PR #1284. Source status: CANDIDATE, not serving/accepted.

## Purpose

Existing `app.mastermind-x.com` and `beta.mastermind-x.com` use Caddy on :3000 and :3001 with a dedicated `terminal_public_data` snippet reading live, independently updated files from `/opt/terminal/terminal/public/data`. The reviewed Vercel frontend introduces a strict `/data/:path*` before-files rewrite so immutable Git snapshots cannot impersonate current market data. The independent hostname `data.mastermind-x.com` must exist **before** the application hostnames move, otherwise both browser-facing domains would route data back to themselves after cutover.

`vercel_data_origin_candidate.caddy` adds a read-only **separate host only** and reuses the existing `terminal_public_data` snippet. Non-data paths receive 404. It is deliberately **not imported in `Caddyfile`**, and no DNS, TLS, EdgeOne, service, deployment, or billing changes accompany this candidate. This prevents collision with open Macro #10670 and #10678, both modifying `app/deploy/Caddyfile`.

## Adoption and acceptance

1. On the **original Caddyfile source owner**, reconcile open #10670 and #10678 and their exact latest source blobs. Serially admit the candidate host block to the one protected/live source; do not overwrite, force/rebase, or bypass either active PR.
2. Confirm EdgeOne/DNS ownership, origin hostname routing, HTTPS certificate behavior (current beta uses EdgeOne public TLS and Caddy internal TLS) and no circular upstream, and provision `data.mastermind-x.com` through its actual authorized provider control. DNS creation is a provider effect, not source review.
3. Run `caddy adapt` using the complete live-compatible Caddyfile, then install only with the accepted guarded deployment procedure and verify the served exact source/source identity. No direct edits to the live box.
4. Real-path check `https://data.mastermind-x.com/data/manifest.json` and one newly published `/data/<symbol>.json` return consistent fresh publisher identity, expected content type and cache freshness; compare to original app domain at the same observation epoch. Confirm `/api/...`, `/terminal`, `/admin`, and `/` are 404 on the data host. Verify no account cookies/private payloads on public data.
5. Only after origin proof, configure `MMX_MARKET_DATA_ORIGIN=https://data.mastermind-x.com` on an eligible commercial Vercel project with a distinct application host. Test Vercel rewrite precedence and the public response through the new frontend; perform authenticated end-to-end beta and Terminal separately.
6. Retain the old frontend and independent publishing service throughout, with verified Caddy/EdgeOne/DNS rollback.

**Not part of this source change:** general Terminal `/api/*` migration, upstream API origin creation, credential copying, account/CORS/cookie changes, Vercel billing, global Caddyfile mutation, producer replacement, DNS change or cutover. Terminal `/api/shared-shell/status` must stay build-consistent with its serving frontend; a blanket API proxy to the old app is unsafe.

## Qualification

```bash
python3 -m unittest -v tests/test_vercel_data_origin_candidate.py
```

M2 Caddy 2.11.4 `adapt` succeeded on original source Caddyfile with this candidate appended; `data.mastermind-x.com` matched one host route containing the original read-only file_server and a 404 catch-all; no reverse proxy in candidate. The 3 unit/adapter tests passed after fixing test expectations (comment text and numeric 404 representation). This is **source-qualification only**. Production release and consumer acceptance remain unproven.

**Collision gate:** Macro PR #10670 and #10678 currently edit the very Caddyfile this block ultimately needs. Preserve their writers and release paths. This dormant file can be reviewed independently, but any promotion into Caddyfile is a separate serial action against accepted current source.

## Companion API origins — deliberately dormant, not accepted for public service

The Next frontend cannot run its 109 incumbent API route handlers on Vercel unchanged: authenticated requests, localhost quote hub, mutable data, streaming and runtime secrets still belong to the VPS. The frontend's new source-scoped API routing contract therefore delegates the existing API families to an independently addressed **corresponding original VPS service**; this retains user-facing same-origin `/api/` request URLs while leaving backend execution on its current source.

The **separate** `vercel_api_origins_candidate.caddy` registers:
- `terminal-origin.mastermind-x.com` — `/api/*` only, forwarding to current `127.0.0.1:3000`, preserving the original app Host and forwarded Host.
- `beta-origin.mastermind-x.com` — `/api/*` only, forwarding to existing beta `127.0.0.1:3001`, preserving the original beta Host and forwarded Host.
- All other paths 404 and response cache `private, no-store`; no broad static data, HTML UI, admin shell, quote hub direct access, or new credentials.

**Admission is NOT established by Caddy adaptation.** Before installing either API alias, a security and actual response contract review must verify: session cookie scope and SameSite behavior, CSRF/Origin checks on mutating endpoints, trusted forwarded headers, rate-limiter client identity through Vercel/EdgeOne, entitlement enforcement, POST/PATCH/DELETE body handling, CORS, preview branch identity, backend version skew, error/timeout mapping, no user-specific edge caching, and correct API request headers. Test `/api/shared-shell/status` on the new Vercel frontend as local and build-matched, not rewritten to the old beta/Terminal backend. Test direct origin host negative paths, guest/authenticated access and disallowed cross-origin requests. Do not expose new public API aliases until those exact negative and positive tests are recorded.

The candidate API Caddy block is **not imported or installed**; its hostnames do not have verified DNS/TLS. The existing Caddyfile remains untouched in both source changes. The current PRs #10670 and #10678 independently edit live Caddyfile and retain serial ownership; do not merge conflicting source without their adopted head, release admission and production proof.

Local Caddy v2.11.4 source-adaptation of the composite incumbent Caddyfile plus the two dormant candidates passed. Both dedicated API hosts matched exactly one `/api/*` proxy to the correct legacy ports, a non-API 404, no `/data/*`, and private no-store response rules. The two extra API-source tests plus three data-origin tests passed (5 total). This is **not** proof of safe real sessions, production access or ability to switch public domains.
