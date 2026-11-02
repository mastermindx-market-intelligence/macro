# Market Memory pre-session callback assets

The real Google return on 2026-10-14 at approximately 11:30 UTC lost all nine exact source-reference fields after PR #9300 was merged and its seven installed files matched. The browser successfully signed in to the same existing MastermindX Google account. A separate anonymous request to the exact emitted `market_memory_intent.js?v=4f265a66` received HTTP 401. The page and shared theme were HTTP 200 with the expected source hashes.

The intent script runs before the login code becomes a session, so placing it behind registration prevents its own callback restoration. The initial source repair in #9300 remains useful: the real authenticated saved packet, eight historical comparison cases, exact case source inspection, and eight current-context cases passed. The real OAuth journey remains unaccepted until this edge change is installed and verified.

## Change and access boundary

Declare only `market_memory_intent.js`, `market_memory_retained.js`, and `market_memory_retained.css` as public UI assets in the existing `config/site_access.yml` policy and all four corresponding Caddy registration/cache matchers. These committed assets contain UI logic and styling; they contain no retained packets, current values, private identity records, credentials, or outcome data. No public prefix, evidence payload, API dependency, source-rights decision, cookie, session lifetime, or entitlement changes. No raw production Caddy edit or manual restart.

## Validation and release

The new boundary regression failed against current main because all three assets were absent. It passes after the policy change, together with exact policy/edge parity and cache access-boundary tests (3 passed). The registration wall, saved-output route, retained catalog and Caddy upstream-identity checks pass (89 passed). `caddy adapt` and the repository Caddy hub-boundary checker pass. Sparse checkout assets were materialized byte-for-byte from HEAD for the source parity assertion.

Protected CI, normal merge, installed repository and `/etc/caddy/Caddyfile` policy proof, anonymous UI asset reads, and a real Settings-to-Google-to-exact-source return remain release obligations. The full program remains 28 tasks / 49 cases. Brain synthesis authentication, original Fabric operation settlement and independent study admission are separate open lanes.
