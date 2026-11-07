# P12.T30.S2 — missing Terminal data routing correction

Original root-reviewed runtime/source packet: `0ab32c77`. The source-release continuation keeps that runtime blob exact. Current test placement and natural CI integration are described in `CI-INTEGRATION.md`.

Local source candidate only, based on observed protected Macro `2e17ae66adca54dcecb9cbe9c669f32d8593ff41`. Root commissioned changed-serving independent review before any release. No push, PR, CI, HTTP application request, listener, host/config write, reload, provider or browser effect occurred. `caddy adapt` parsed source without validation/provisioning/loading. Previous native error presentation input `498532c3` remains frozen and disjoint.

## Actual failure and source binding

Consumed the retained T30 RCA before implementation:
`/Volumes/Mastermind/evidence/shared-shell-auth03-t30-20261103/missing-data-source-rca.json`.

The original GET89153 and HEAD86295 each ran once. Missing `/data/shared-shell-acceptance-missing-f0eebcad.json` returned 404, zero bytes, no JSON type and public cache policy. Compatibility independently bound the installed persisted Caddyfile/autosave to Macro `c6229faa`; its SHA256 `125a8aa0d82aa1b7a28a6f5b9f44082b3a9832f4de03696c322ace365b178c52` is also the exact Caddyfile on this newer protected base. The installed Terminal f0ee resource route was correctly bound but never reached: the shared Caddy `/data/*` static handler runs first. No canary was repeated here and no edge-cache cause is asserted.

Admit Routes' new source turn failed before execution from model capacity. Root transferred this source-only integration. Existing Terminal/auth/resource source and original host carrier remain untouched. New task is **P12.T30.S2**, a child of T30. During registration an already-existing S1 id was mistakenly started; its prior root-reviewed state was restored with an explicit history note, and no S1 source or verdict changed.

## Smallest serving change

Only `(terminal_public_data)` changes. The same shared read-only owner still serves app and beta from `/opt/terminal/terminal/public`.

1. Preserve existing path/root and manifest/rest public cache headers.
2. Place the file server first in an explicit ordered `route`, with `pass_thru`.
3. Only its not-found continuation reaches data-local GET/HEAD headers: `Cache-Control: no-store`, `Content-Type: application/json`.
4. HEAD responds 404 without a body; GET responds 404 with the same `{ "error": "not_found" }` contract as Terminal's existing missing-data route.
5. Other missing-file methods end in the original native 404 error path. Existing-file methods, permission/I/O errors, redirect/conditional/range handling remain owned by the unchanged file server. No HTML/auth/Next proxy fallback or global error handler is added.

The official [file_server reference](https://caddyserver.com/docs/caddyfile/directives/file_server) specifies that `pass_thru` continues only on not found and needs an ordered route. The inspected [Caddy v2.11.4 file-server source](https://raw.githubusercontent.com/caddyserver/caddy/v2.11.4/modules/caddyhttp/fileserver/staticfiles.go) keeps permission/invalid/I/O failures separate from that continuation and enforces existing-file GET/HEAD methods before serving. Its not-found class also includes hidden files and directories without an index; those GET/HEAD cases receive the same bounded JSON404. Existing directory/file canonical redirects remain native. This is reference/source qualification, not an executed FileServer test.

## Proof at its actual layer

Installed **local** adapter: Caddy v2.11.4; exact binary digest is in `source-adapt-proof.json`. Its version is not asserted to be the installed host's version.

- Final tests against the exact baseline: **4 fail / 1 pass**. They discriminate absent ordered continuation, missing JSON/cache override and missing empty-HEAD fallback.
- Exact candidate: **5 pass** using the real installed adapter on the full Caddyfile via stdin; no service is started. Tests inspect ordered data subroutes, method matchers, bodies/statuses, original root/cache policies and absence of HTML/auth proxy fallback.
- Adjacent controls: **45 pass** across `test_macro_caddy_overlay.py`, `test_control_room_caddy.py` and `test_caddy_hub_boundary_am_edition.py`.
- Source outside this snippet is byte-identical. The entire adapted configuration outside the new data continuation is equal after **alpha-renaming generated group identifiers while preserving all equivalence classes**. Raw equality initially exposed Caddy's generated group-number shifts; no groups were dropped to make the comparison pass.
- `caddy adapt` succeeds; its existing formatting warning remains visible. No whole-file reformat or unrelated source change was made. `git diff --check` passes.

Run the focused checks with an installed Caddy:

```sh
CADDY_BIN=caddy python3 -m pytest tests/test_control_room_caddy.py -q
```

The suite skips explicitly when no Caddy adapter is installed. Baseline reconstruction may point `MM_CADDY_SOURCE` to the retained exact baseline file; it performs parsing only. No behavioral HTTP model is used or reported as real traffic.

`source-adapt-proof.json` binds source, adapter and retained artifacts. `data-subroutes.json` is the actual full-config adapter output restricted to the two affected routes. Full before/after adapter graphs, source preimage, patch and negatives remain at:

`/Volumes/Mastermind/evidence/shared-shell-caddy-missing-data-p12t30s2-20261103`.

## Review and remaining serving obligations

Changed risk is the shared data-only not-found continuation and its header overwrite timing, on **both** app and beta. Successful file responses must terminate before fallback; errors other than not found must remain native. The tests and primary-source inspection support this composition, but no actual FileServer/HTTP runtime was exercised in this phase.

Root's independent serving review, ordinary protected source release, any specifically authorized host deployment/reload, and same-carrier served GET/HEAD/cache/existing-file controls remain separate. Neither the original failed canaries nor this adapter output proves an installed repair. Preserve original 1188/Person1/browser, SQL/unknown-effect, account/provider and production holds. No alternate host or source carrier was used to obtain a held effect.
