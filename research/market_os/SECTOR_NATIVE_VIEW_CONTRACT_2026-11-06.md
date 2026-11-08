# Native Sector view: qualified projection boundary

Date: 2026-11-06
Mission: https://github.com/mastermindx-market-intelligence/macro/issues/10779
Convergence: https://github.com/mastermindx-market-intelligence/macro/pull/10780
Governing Mastermind source: 49c2e1d93e5e080b1671c98087a845e5beb09dd5

## Delivered scope

`engine/sector_native_view.py` projects the existing Macro Brief and action-board
owner outputs into one bounded native representation. It does not collect,
calculate a new signal, authorize a request, validate a private filesystem
generation, grade calls, save user watches, publish, or select a generation.

The paid projection commission
`macro-always-on-20261106-c3-native-projection-01` returned terminal rc75,
root verified, with `host_temperature_at_or_above_limit` admission refusal.
The complete result digest is
`46fc4d42f30816b7fb3eb3740f9048a870150503be6b81c962ecaa326dc2765a`.
There was no replay or alternate host dispatch. The assigned parent performed
this bounded source work under the permitted direct-work recovery rule.

## One tier algorithm

The Sector builder's existing `split_actnow` now uses the shared import-light
`lib/sector_action_preview.py`. The builder retains its existing names and
return contract. Both the legacy split and native visible-row projection use
`partition_actnow`; there is no copied native tier budget.

The six original lane destinations and wrapping flags are unchanged. Hold uses
the shared stand-aside preview allowance first; avoid gets the remainder.
Ungated/invalid input or no withheld rows still returns `(None, [])` from the
legacy helper. The native view independently constructs only its permitted rows;
it never includes the full original board alongside gating metadata.

The module was initially placed under engine. The existing import-light guard
correctly rejected a top-level engine import in the legacy builder. Moving the
pure shared helper into lib preserved that guard without weakening its assertion.

## Explicit inputs and public receipt

`project_sector_view(inputs, receipt, audience=..., preview_rows=3)` receives:

- Parsed central and cycle documents whose source sessions must agree.
- Parsed baskets, handoff and source-bound action-board documents.
- A trusted `SectorViewReceipt`: accepted generation identity, source session,
  publication time, qualification, input version and optional explicit older
  baseline session.
- A trusted audience choice, preview or entitled. This argument is not
  authorization; the API must still apply each represented canonical resource's
  existing policy. A preview representation does not change the current access
  classification of /sectordata or /basketdata.

Required core source dates must equal the receipt source session. Baskets,
theme-intelligence, handoff and action-board dates must equal the same baseline.
An older baseline is allowed only when the caller explicitly declares it; the
Brief reports `declared_older_baseline`, preserves its actual date, and does not
adopt the newer sector date. Such a baseline must not support a combined
current-session conclusion. Future, mixed, missing or malformed required dates
fail closed with a safe reason code.

The caller must verify exact artifact bytes, basket/action-board hash association,
semantic requirements and selected-generation membership before projection.
Parsed dictionaries and these date checks alone do not prove that binding.

## Preserved intelligence and disclosure

Leadership state, stance, strength order, trailing leader and factor-season
copy come from the existing owner fields. The renderer does not rank groups,
recompute recommendations, infer an entry signal, or change trade authority.

The comparison uses precisely the existing Brief formula over 21 aligned positive
observations (20 sessions):

`((group_t / group_start) / (benchmark_t / benchmark_start) - 1) * 100`

The focused suite executes the shipped JavaScript owner
`templates/_sector_central_brief.js.j2::buildSectorBriefSeries` on the same
fixture and compares every point. Missing/misaligned/nonpositive/nonfinite
comparison closes produce unavailable comparison state, never a fabricated zero.

The subject remains an equal-weight sector basket or theme basket; the sector
ETF is not substituted. Original construction/history disclosure is carried
forward. The chart contract does not declare a uniform price/TR basis, so the
projection explicitly says `not_declared_by_chart` rather than inventing one.
For example, the deployed basket artifact described monthly rebalancing and
back-projected current-roster history; that is not a naturally observed track
record.

## Isolation and transport boundary

Only allowlisted fields reach the native view. Hidden rows, unknown board
collections, private input hashes, source manifests and nested metadata inside
scalar fields are excluded or rejected. Preview counts follow the existing
approved lane counts. Unsafe cross-origin/script/traversal links are omitted.

The content hash covers only the authorized data representation. Changing a
withheld row while preserving visible content/counts does not change the preview
content hash. Generation identity can still change when a new generation is
selected. Source session, publication time and browser/BFF observation time remain
distinct; polling never upgrades qualification.

The returned JSON is finite, detached from mutable input objects, deterministic
for the same explicit inputs, and limited to 4 MiB including its receipt. The API
must apply the same transport budget to any larger aggregate envelope and enforce
private/no-store, cookie-varying responses. No personal watch state is bundled;
the existing Supabase watchlist owner remains responsible.

## Verification

Parent qualification after the final source changes:

`python3 -m pytest tests/test_sector_native_view.py tests/test_sector_central_gate.py -q`

**52 passed**. This includes executed legacy-JavaScript formula parity, shared
preview budget, hidden-row negative controls, input immutability, source-date
mismatch refusals, older-baseline disclosure, source-clock preservation, oversized
and nonfinite failure, safe links, nested metadata rejection, and no implicit
file/current-clock reads. Existing import-light and tier-contract tests passed.

The new suite has a named step in the incumbent tier-gate CI job. Hosted CI,
the real selected-generation adapter, API policy integration, native Terminal UI,
deployment and authenticated browser acceptance remain separate requirements.
This document does not claim any of them has completed.
