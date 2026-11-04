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
