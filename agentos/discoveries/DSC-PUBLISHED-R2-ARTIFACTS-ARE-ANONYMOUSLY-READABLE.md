---
key: PUBLISHED-R2-ARTIFACTS-ARE-ANONYMOUSLY-READABLE
claim: >
  Artifacts this repo publishes to R2 are readable ANONYMOUSLY over the public
  r2.dev base `https://pub-f7ffb4441c5f4ad983ca56ec7c651c61.r2.dev/<r2_key>` — no
  credentials, no bearer token, no source-host access, no VPS. The R2 key is exactly
  the prefix the publisher uploads under, so e.g. the options matrix publishes to
  `options_structure/matrix/<ROOT>.json` and is fetchable at
  `<base>/options_structure/matrix/SPY.json`. Cloudflare's WAF 403s python-default
  User-Agents, so a custom UA is required (`curl -A macro-acceptance-probe/1.0`);
  the host also has no LIST endpoint, so keys must be known rather than discovered.
  This matters because the natural assumption is the opposite: the Terminal reaches
  the same data through `/api/hub/matrix/<ROOT>`, an AUTHENTICATED app route, which
  makes the artifact look like it sits behind an operator-held token.
falsifier: >
  `curl -A macro-acceptance-probe/1.0 <base>/options_structure/matrix/SPY.json`
  returning 401/403 rather than 200 would show the bucket's public access was
  revoked. A 404 means that specific key is simply not published (measured
  2026-09-29: MU and ARM 404 because they are not yet enrolled) and is NOT evidence
  the base is closed — check a known-published key before concluding anything.
so_what: >
  A session that needs production evidence of a published artifact must try this
  base BEFORE classifying the lane as EXACT_HUMAN_GATE on a bearer token, or as
  blocked on source-host/VPS access. On 2026-09-29 this converted the last open lane
  of macro #7861 from "blocked, downstream of install" into a completed production
  reproduction: all ten published matrix roots were fetched anonymously and every one
  was an empty heatmap (cells=[], spot=null, `spot unavailable on 2026-09-24`), five
  days stale — and the repaired publisher's real gate, run against those real
  payloads, withheld all ten. That is acceptance-grade evidence obtained with zero
  privilege. Note the boundary: this proves the PUBLISHED artifact only. It says
  nothing about what an authenticated Terminal user is served after app-side
  transforms, so a full served-journey proof can still need the authenticated route.
  Publish only safe summaries of whatever is read — a populated artifact WILL carry
  licensed vendor-derived values even though a null one does not.
kind: runtime
verified_at: 2026-09-29
verified_by: "curl over the public r2.dev base for 12 option roots; macro PR #7861 comment trail; scripts/audit_r2.py:55 and scripts/freshness_sentinel.py:226 carry the same base"
scope:
  - macro
  - scripts/build_options_matrix.py
  - scripts/publish_r2.py
  - acceptance-evidence
confidence: verified
---

The published matrix is R2-only — there is no `site/options_structure/matrix/`, so it
is never served from the static site — and the Terminal reads it through the
authenticated `/api/hub/matrix/<ROOT>` route (`terminal/lib/flowSource.ts:212`, which
maps to the R2 key at `:282`). Both facts point toward "you need a token".

They are both true and the conclusion is still wrong. The same object is public on the
r2.dev base that `scripts/audit_r2.py`, `scripts/freshness_sentinel.py`,
`scripts/hot_tape_radar.py` and `scripts/build_options_signal_episode.py` already use.

Two practical gotchas:

- **Custom User-Agent required.** Cloudflare's WAF 403s python-default agents; both
  `audit_r2.py:53` and `freshness_sentinel.py:220` carry comments saying so.
- **No LIST endpoint.** `publish_r2.py:662` notes it explicitly. You must construct the
  key from the publisher's own prefix constant, not discover it.

Used on 2026-09-29 to close the production-reproduction half of MACRO-05 without any
credential, host or merge — see the handoff
`agentos/handoffs/ADVANCED-DATA-OPTIONS-2026-09-29-matrix-session-alignment.md`.
