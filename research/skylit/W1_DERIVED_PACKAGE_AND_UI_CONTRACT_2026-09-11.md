# W1 derived package and Money & Breadth consumer contract

Recorded: 2026-09-11 UTC. Accountable seat: ceo-sol.
Operation: `us-sector-participation-w1-20260910-sol-001`.
Applies to Macro PR7060 after Sol review `5174640493` / Slack repair `1789096018.269229`.
Procedure at freeze: Mastermind `797cfd0b1001d9dfe6fe9030af80ecdab0e1220d`, Skillpack 1.0.1 / bootstrap 1.

## 1. Ruling

Use **one validated, atomically replaced derived JSON package** as W1's data artifact and one lazy static-site projection of the same package. This is an output of the existing US breadth owner, not a second price store, service, API, history database, identity plane or publication authority.

Recommended owning paths:

- canonical derived artifact: `data/breadth/sector_participation_20.json`;
- public product projection: `site/sectordata/sector_participation_20.json`;
- existing-page consumer asset: `templates/sector_participation_20.js` plus narrowly scoped styles/markup in the existing template or a namespaced partial;
- existing lazy owner: add the asset to the `money` view in `templates/si_workspace.js`;
- existing builder: validate/copy the package and attach only its pointer/status metadata after the grader boundary.

A single package is preferred to independent summary/detail files because it makes calendar cells and dated constituent evidence inseparable by generation. If the worker finds an already-owned equivalent one-package path, it may use that exact existing seam and document it; it may not create a new generic catalog or multi-generation store.

## 2. Required package semantics

The package is columnar and bounded. Exact field spelling may be refined during implementation, but every meaning below must be present and validated before the builder calls it available.

```json
{
  "schema": "sector_participation_20.v1",
  "generation_id": "sha256-of-canonical-derived-content",
  "method": {
    "window_sessions": 20,
    "comparison": "close_strictly_above_sma_including_session",
    "minimum_eligible": 5,
    "minimum_coverage": 0.9,
    "history_semantics": "selected_reference_universe_reconstruction"
  },
  "reference": {
    "universe": "sp500_reference",
    "roster_id": "content identity of ordered symbol/name/sector membership",
    "observed_at": null,
    "expected_members": 503
  },
  "source": {
    "contract": "licensed_stock_daily_aggregates",
    "basis": "split_adjusted",
    "requested_start": "YYYY-MM-DD",
    "requested_end": "YYYY-MM-DD",
    "latest_expected_session": "YYYY-MM-DD",
    "acquired_at": "UTC timestamp",
    "response_set_id": "content identity of accepted per-name response receipts",
    "requested_names": 503,
    "accepted_names": 0,
    "unavailable_names": 0
  },
  "computed_at": "UTC timestamp",
  "sessions": ["YYYY-MM-DD"],
  "sectors": {},
  "members": [],
  "state_legend": {}
}
```

`reference.observed_at` remains null or explicitly unavailable until the existing membership owner supplies a real observation clock. A file modification time or current build time must not fill it.

`generation_id` changes when accepted prices, roster identity, method, session range or derived values change. `computed_at` and site publication time are not allowed to masquerade as a new economic observation. The builder's small pointer must state the same `generation_id`; the client refuses a fetched package whose ID differs.

Do not expose provider credentials or raw response bodies. Preserve response/request identity through a bounded content receipt such as `response_set_id`; raw vendor request IDs need not be public.

## 3. Sector and member representation

Use the complete validated reference roster to establish expected membership. A missing price column remains an expected member and an exclusion. A sector with zero accepted price names remains present.

Each sector carries its stable GICS label and arrays aligned one-for-one with `sessions`:

```json
{
  "Information Technology": {
    "expected": 73,
    "above": [null],
    "eligible": [null],
    "pct": [null],
    "excluded": {
      "unavailable_source": [null],
      "missing_window": [null],
      "invalid_value": [null],
      "insufficient_history": [null]
    }
  }
}
```

`expected` is roster membership, not covered columns. `above` and `eligible` are integer counts. `pct` is null when the denominator is zero, fewer than five names are eligible, or coverage is below 90%; otherwise it equals `100 * above / eligible`. A valid zero numerator is `0.0`, never null.

Member rows use compact arrays aligned to `sessions` so one year of 503 names remains a bounded static payload:

```json
{
  "symbol": "AAPL",
  "name": "Apple Inc.",
  "sector": "Information Technology",
  "href": "stocks/AAPL.html",
  "states": "HHHBAA...",
  "distance_bps": [null, null, null, -125, 84]
}
```

Required state vocabulary:

- `A`: eligible and strictly above its 20-session average;
- `B`: eligible and equal to or below its average;
- `H`: fewer than 20 consecutive valid expected sessions exist;
- `M`: a required expected session is missing;
- `I`: a supplied observation is invalid or identity/basis qualification failed;
- `U`: the source request for the member was unavailable/refused.

A state code may be changed only if the implementation preserves these distinctions. `distance_bps` is a derived explanatory field, not authority; it is null for excluded states. The UI may filter members by the supplied state for a selected session, but it must not recompute the sector metric from prices or silently repair summary/detail disagreement.

Duplicate price columns, duplicate roster symbols, conflicting sector assignments, wrong-case vendor identities and unresolvable class-share notation are invalid inputs. Apply the existing Massive identity law: comparison is case-exact, with only the accepted dot-to-hyphen class-share normalization. Do not reuse the Yahoo-only alias map as a Massive identity authority.

## 4. Source response and time qualification

The official stock custom-bars contract supplies `ticker`, `adjusted`, `status`, `queryCount`, `resultsCount`, `request_id`, `results` and optional `next_url`. Validate the envelope before accepting values:

- response is a mapping with success status;
- returned ticker matches the requested provider identity under the existing case-exact/class-share rule;
- `adjusted` is exactly true;
- `resultsCount` matches the accepted returned result count;
- unexpected `next_url` is a bounded truncation refusal, not permission for an unbounded pagination loop;
- every result timestamp maps to one unique expected session inside the requested range;
- every close is finite, positive and non-Boolean;
- conflicting duplicate sessions are refused;
- non-session and out-of-range rows are refused or explicitly excluded before derivation.

Daily-bar timestamps identify the start of an Eastern Time aggregate window. Convert according to that contract and test the provider's midnight-ET shape; do not validate only synthetic 20:00-UTC rows.

A complete response may legitimately omit a session when no qualifying trade/bar exists. Preserve that hole for the member and let only affected rolling windows become unavailable. Distinguish a sparse but complete envelope from transport truncation (`next_url`, count mismatch, malformed status). New listings and halted names therefore do not poison all otherwise valid history.

The requested range must contain the display history plus the 19 earlier expected sessions needed for its first calculation. `requested_end` and `latest_expected_session` come from the existing NYSE calendar and invocation contract, never from the latest row returned by the provider.

## 5. Acquisition and failure isolation

One per-ticker request can be finite while the 503-name operation is unbounded. The US-owner invocation must declare all of:

- maximum roster/request count;
- bounded worker concurrency using existing HTTP/config primitives;
- per-request timeout/retry values passed to the existing `Adapter.http_get` owner;
- one overall elapsed-time budget;
- fail-fast behavior for authentication/entitlement refusal or systemic host failure;
- minimum package qualification required before atomic publication.

Do not introduce another retry queue, session store, scheduler or credential owner. Cancellation/timeout is not proof an in-flight request had no effect, but these GETs have no remote mutation; partial local results must never replace the prior complete derived artifact.

The existing 50/200 breadth output is the protected primary collector result. A W1 refusal, timeout, low coverage or malformed response must leave those old outputs publishable and unchanged. W1 may retain a prior valid package only with its original source/generation clocks so the page labels it stale; first-run failure produces an unavailable state.

Publication uses same-directory temporary bytes plus atomic replace after full schema validation and finite JSON serialization with `allow_nan=false`. Do not route this package through the generic `store.upsert(... combine_first ...)`: newly unavailable cells must not be filled from an older generation, and adapter-wide `overwrite_overlap` would alter existing breadth outputs.

## 6. Existing-page consumer

Place one new section in the existing Money & Breadth view after the current Under-the-hood breadth cards and before the existing sector-flow/heatmap organs. Keep `#money`, `#si-money`, `#internals-section` and `#scc-leadership` behavior unchanged.

The `money` view lazy-loads the namespaced W1 asset only after the view is visible, using the existing `LAZY`/`vUrl` mechanism. It fetches only the builder-approved `sectordata/sector_participation_20.json` path. No polling loop or new route.

Use a native accessible table/grid:

- sector names are row headers;
- sessions are column headers;
- each selectable cell is a keyboard/touch button with an aria-label containing sector, date, participation or unavailable reason, and counts;
- hue is not the only carrier; percentage/text/state remains available;
- 3M/6M/1Y controls are view windows over the same package, never alternate calculations or network acquisitions;
- mobile may horizontally scroll the calendar but must keep sector/date context legible.

Selection opens an in-view detail panel for the same `generation_id`, sector and session. It shows above/eligible/expected, all exclusion counts, method, source session, latest expected session, roster semantics and computation/publication clocks. Constituent rows distinguish A/B/H/M/I/U, may sort/filter by supplied state/distance, and link through the existing `stocks/<symbol>.html` destination only when that page exists under the accepted resolver.

Preserve selection without taking over the workspace hash. Use namespaced query keys with `#money` or another already-approved bounded browser-state mechanism; clearing removes only W1 keys. Browser Back to Sector Central must restore the selected sector/session/window. Do not create another route, identity store or global localStorage preference.

English and Chinese must carry equivalent units, counts, timestamps and warnings. Reuse existing tokens and scoped component styles; no global bare selector or copied Skylit visual asset/branding.

## 7. Builder projection and coherent states

The builder runs after the existing grader step. It validates the canonical package, atomically writes/copies the site projection, and then attaches a small pointer to the public Sector Central payload:

```json
{
  "status": "ready|stale|missing|invalid|withheld",
  "generation_id": "...",
  "url": "sectordata/sector_participation_20.json",
  "source_session": "YYYY-MM-DD",
  "latest_expected_session": "YYYY-MM-DD",
  "published_at": "UTC timestamp"
}
```

Only `ready` or explicitly `stale` can carry a URL. The fetched package must match the pointer generation. `published_at` is page publication time and cannot refresh `source_session`.

The package contains no existing Act-Now/premium-board rows. Per the current Sector Central access contract, Money is an ungated context view; W1 must not silently expand or weaken the only existing premium wall. Anonymous and entitled users receive the same W1 context unless a newer accepted access ruling changes that scope.

Required visible states remain: loading, ready, valid 0%, insufficient sample, insufficient coverage, stale source, missing input, malformed/conflicting input and unavailable historical detail. A W1 error cannot remove or block the pre-existing Money & Breadth organs.

## 8. Discriminating proof additions

In addition to A01-A26 and the existing Sol review, require:

1. Provider sample timestamp at midnight ET maps to the correct session; an arbitrary out-of-session timestamp is refused.
2. `resultsCount != len(results)` and any unexpected `next_url` refuse the response.
3. A complete sparse envelope preserves missing sessions rather than refusing all history.
4. Membership symbol `BRK-B` accepts only the explicitly normalized case-exact provider identity `BRK.B`; mixed/lowercase variants are not folded into it.
5. A W1 auth refusal on the first bounded request stops new W1 scheduling and old 50/200 frames still return/publish.
6. Overall acquisition-budget expiry leaves the prior W1 generation untouched and old breadth unaffected.
7. A simulated process failure before atomic replace leaves the previous package byte-identical.
8. The builder refuses a package with summary/detail count disagreement or wrong generation ID.
9. The browser refuses a detail package whose generation differs from its pointer.
10. Initial load does not fetch W1 outside Money; first Money activation fetches once; return/resize does not duplicate the fetch.
11. Selecting a historical cell shows the same date's member states even when current data differs.
12. Back/clear/query-state behavior preserves the workspace hash and only W1's namespaced state.
13. Full 503-name x covered-session package remains within the stated payload/render budget without dropping members.

## 9. What this freeze does not authorize or prove

This record does not prove PR7060 repaired, create a worker START, permit another receiver, run the live provider, change credentials, mark Ready, merge, deploy, or accept W1. It does not create a historical membership store or prediction model.

The same Claude8 writer must first consume the existing Sol repair on the exact carrier, establish its current worktree/source checkpoint, then implement and return the repaired immutable PR head. Sol re-runs adversarial review before independent review and real-input/browser/publication proof.
