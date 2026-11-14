# Lane 1 — Macro sector generation API contract (2026-11-09)

Consumer-facing short contract for the Terminal `/sectors` lane. Source of
truth for behaviour: `app/sector_generation.py`, `app/sector_generation_reader.py`,
`lib/sector_generation_contract.py`, `lib/sector_generation_wire.py`,
`engine/sector_native_view.py` (long-form: `docs/SECTOR_GENERATION_API_CONTRACT.md`).

## Endpoint

`GET /api/sector-generation` — one qualified Macro sector generation, selected
by the private-store selection pointer, never by caller input.

Query: `?audience=preview|entitled` (default `preview`). Any other parameter,
a repeated `audience`, an empty value, or a non-lowercase value is refused
with `400 REQUEST_INVALID` before the reader runs. The caller cannot name a
root, path, generation, or domain through the query.

## Auth (order of evaluation)

1. Site registration wall (cookie → Supabase identity). Missing/unverified →
   `401 AUTHENTICATION_REQUIRED`.
2. Global paywall (staged on/off). Registered-but-free while the wall is on →
   `401 AUTHENTICATION_REQUIRED`.
3. `audience=entitled` additionally requires the `site_full` entitlement →
   `403 ENTITLEMENT_REQUIRED`.
4. Wall infrastructure failure → `503 SERVICE_UNAVAILABLE` (fail closed).

Both audiences are always gated; `preview` is not free access. Local
development equivalent (documented, same as the test suite): a fixed cookie
identity behind the real regwall/paywall code paths.

## Response (success)

`200`, `Cache-Control: private, no-store`, `Content-Type: application/json`,
schema `sector_generation.read/v1`:

```json
{
  "schema": "sector_generation.read/v1",
  "audience": "preview",
  "source_session": "2026-11-06",
  "published_at": "2026-11-10T04:00:46.923865+00:00",
  "qualification": "accepted",
  "projection": {
    "data": {
      "schema": "sector_native_view.v1", "audience": "preview",
      "core": {"sectors": ["…11 sector rows…"]},
      "history": {"meta": "…", "sectors": "…"},
      "brief": {"as_of": "…", "status": "available", "headline": {"en": "…", "zh": "…"}, "leadership": "…"},
      "action_board": "…"
    },
    "receipt": {
      "schema": "sector_native_view.receipt.v1", "source": "macro.sector",
      "generation_id": "…", "source_session": "…", "published_at": "…",
      "qualification": "…", "input_version": "sector-inputs-v1",
      "baseline_session": null, "content_sha256": "…"
    }
  }
}
```

(`preview` truncates non-core sections; `entitled` carries the full core +
history + brief + action_board. Sector ids are the owner's wire ids, e.g.
`xlf`; `content_sha256` differs per audience because the payload differs.)

## Refusals (all bodies `{schema: "sector_generation.error/v1", code: …}`, no private metadata)

| HTTP | code | when |
|-----|------|------|
| 400 | `REQUEST_INVALID` | unknown/duplicate/invalid query field |
| 401 | `AUTHENTICATION_REQUIRED` | no/invalid identity, or free caller while paywall on |
| 403 | `ENTITLEMENT_REQUIRED` | `audience=entitled` without entitlement |
| 404 | `RESOURCE_NOT_AVAILABLE` | path not in the server-owned gate set |
| 503 | `SERVICE_UNAVAILABLE` | wall infrastructure failure, reader not installed, malformed storage binding |
| 503 | `SECTOR_GENERATION_UNAVAILABLE` | no qualified selected generation, corrupt/missing member, replaced pointer, calendar uncertainty |
| 413 | `SECTOR_GENERATION_TOO_LARGE` | encoded projection exceeds the bound |

## Bounds

- Encoded response ceiling: `4 * 1024 * 1024` bytes (`MAX_ENCODED_BYTES`);
  one byte over → `413 SECTOR_GENERATION_TOO_LARGE`.
- Values must be finite JSON (no NaN/Infinity constants anywhere in a member).
- Reader is called exactly once per allowed request; denied requests never
  resolve a snapshot; reads create no directories and never write.

## Field separation (frozen)

`source_session` (producer session), `published_at` (publisher clock),
`qualification` (accepted/degraded/stale — computed, never inferred from
recency), `input_version`, `baseline_session` (retained older Brief baseline
or null) and `content_sha256` are separate fields; none implies another.
Dated-context scope `configured_theme_example_with_market_global_risk` is
optional and capability-local; its failure never erases a qualified core
generation.

## Qualification receipt (local, real bytes — 2026-11-09)

Real chain over this repo's committed producer artifacts (session 2026-11-06),
published through the real private-store publisher into an isolated local
store, read through the real app + gates (local auth equivalent):

- generation_id `lane1-qualification-20261106`, source_session `2026-11-06`,
  published_at `2026-11-10T04:00:46.923865+00:00`, qualification `accepted`
- entitled `content_sha256` `dbc45ea071afe753935419fd3585aefea8d68a7f3081038a6fab87970b3778b0`
  (preview `aa99495c4404e442d8d6286aa0e45e9baeee8b3a97ed21b6241ffde2e366f2ca`)
- core: 11 sector rows — `xlre xlb xlu xli xlc xly xle xlp xlf xlk xlv`;
  history (meta + sectors) and brief present
- unauthenticated call → `401 AUTHENTICATION_REQUIRED` through the real gates

One disclosed input repair: the committed `site/factordata/factors.json`
carries 1,949 non-finite factor scores; the strict member decoder refuses
`NaN` literals (fail closed). For this local receipt the ported real producer
(`scripts/build_sector_action_board.py`) was run with those scores read as
`null`. Nightly production publication needs the factors producer to stop
emitting non-finite literals (or the same null repair) — tracked as a residual,
not fixed by this lane.
