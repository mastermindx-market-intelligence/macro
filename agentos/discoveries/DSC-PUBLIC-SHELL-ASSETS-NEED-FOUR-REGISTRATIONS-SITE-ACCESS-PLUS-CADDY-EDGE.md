---
key: PUBLIC-SHELL-ASSETS-NEED-FOUR-REGISTRATIONS-SITE-ACCESS-PLUS-CADDY-EDGE
claim: >
  Registering a public page shell in `config/site_access.yml` `public.exact` makes only the
  HTML public: its paired `.css`/`.js` still answer `401 x-regwall: deny` at the Caddy edge
  until they are ALSO listed in `app/deploy/Caddyfile` in four places — the two `@reg_asset`
  `not path` exclusion lines (~345, ~471) and the two public-asset `path` lists (~515, ~550).
  `app/regwall.py` PUBLIC_PATHS is HTML-only and does not cover assets. A shell registered in
  the YAML alone therefore ships a blank page in production while every local render, every
  test and the page's own 200 look green.
evidence:
  - T8 shell #7952 merged 2026-09-24T16:11:10Z (4c191a3e) with `/finance_intelligence.{html,css,js}` in `public.exact`; live check the same hour — `curl -sL -D - -o /dev/null https://www.mastermind-x.com/finance_intelligence.js | grep -E '^(HTTP|x-regwall)'` → `HTTP/2 401` + `x-regwall: deny`, `.css` identical, `.html` → 200; `/api/health` `commit` equalled `checkout` (the API was not stale — the edge was the cause).
  - #7956 (6b1483f4, merged 2026-09-24T17:33:28Z) added the three finance entries to Caddyfile lines 345 and 471 and the two asset entries to lines 515 and 550, mirroring biocatalyst which carried all four; after the VPS pull reloaded Caddy the same curl answered `HTTP/2 200` with no `x-regwall` header for both assets at 2026-09-24T17:36:27Z.
falsifier: >
  A future public shell whose `.css`/`.js` serve 200 anonymously with entries in
  `config/site_access.yml` alone (no Caddyfile edit in the same or an earlier PR) refutes the
  claim; so would a Caddyfile refactor that derives the asset exclusions from the YAML.
so_what: >
  A packet that introduces a public page shell must list the four Caddyfile lines under OWNED
  FILES beside `config/site_access.yml`, and the seat's live verification must curl the paired
  assets with `-D -` and grep `x-regwall`, not only the page — a 200 on the HTML proves nothing
  about the shell's ability to render.
kind: landmine
confidence: verified
verified_at: 2026-09-24T17:36:27Z
verified_by: >
  for a in js css html; do curl -sL -D - -o /dev/null "https://www.mastermind-x.com/finance_intelligence.$a" | grep -E '^(HTTP|x-regwall)'; done;
  grep -n finance_intelligence app/deploy/Caddyfile config/site_access.yml app/regwall.py
scope:
  - macro
---

The paywall's `classify_path` (site_access.yml) decides the HTML response; the Caddy edge's
`@reg_asset` matcher intercepts every non-HTML asset that is not explicitly excluded and hands
it to the regwall, which denies anonymous requests regardless of the YAML. Biocatalyst, the
model for the finance shell/payload split, had been registered in all four Caddyfile places by
hand; nothing tests that parity, so the omission was invisible until the live curl.
