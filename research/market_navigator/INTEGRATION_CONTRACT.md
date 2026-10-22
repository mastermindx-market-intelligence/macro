# Navigator production integration contract

This document fixes the next integration boundary. It grants no source, runtime,
publication, personal-state or trading authority. Current implementation is a pure
read-only foundation; do not mark it live because this contract exists.

## 1. Do not flatten unlike clocks

A concrete integration hazard was verified in `engine/neuralweb/market_memory.py`:
its canonical context preserves both `measurement_end` and `observed_at`, with the
operational rule `available_at <= observed_at <= as_known_at`. Here `observed_at`
represents the system's capture/observation of the source, not necessarily the market
measurement time.

The initial Navigator Receipt instead names its **market measurement** clock
`observed_at` and then requires `observed_at <= received_at <= available_at`.
These are different naming conventions. They must NOT be joined by field name.

| Semantic event | Incumbent Market Memory field | Navigator boundary requirement |
|---|---|---|
| Measurement period ends | source `measurement_end` | Preserve as market measurement end |
| Source becomes knowable | source `available_at` + declared availability rule | Preserve source availability, never replace with a later data date |
| System captures source | source `observed_at` | Preserve capture clock and receipt identity |
| Derived feature observed | feature `observed_at`, source dependencies | Preserve derived-feature availability under the owner rule |
| Decision information cutoff | `clocks.as_known_at` / `knowledge_cutoff` | Exact caller-bound decision cutoff |
| Observation validity expires | source quality/owner availability policy | Consumer capability-specific policy; do not invent a vendor expiry |

Before implementing a Market Memory-to-Navigator adapter, choose one of two explicit
routes: (a) consume the validated canonical context as a retained reference without
flattening its clocks, or (b) define and test a semantic translation with all necessary
clocks supplied by the actual source owner. A missing clock stays missing. Do not
manufacture equality between receipt and availability merely to satisfy a type.
The preferred route is (a) until a lossless translation is proven necessary.

`validate_as_known_at_context` checks the complete canonical packet, registry versions,
identity/calendar receipts, feature/source lineage, quality, cutoff and context ID.
It is not a substitute for the trusted reader/materializer's retained external integrity
anchor. Call it on the actual existing reader output, not on a hand-authored imitation.
Do not import historical outcome labels into the decision context.

## 2. Production adapter capability gate

The current SPY adapter accepts only SPY:ARCX and the US market-state schema. This is
a canary scope, not a new instrument master. Its production wiring must supply:

1. An authenticated existing-owner read of the exact source artifact/generation.
2. The corresponding owner-issued availability receipt and its existing verification
   path, bound to the actual bytes or source revision, subject and cutoff.
3. Calendar evidence for the expected daily session and completion of any newer session.
4. Source/data rights appropriate to this consumer, audience and display purpose.
5. Consumer freshness policy appropriate to the requested horizon and source cadence.

The verifier is dependency injection at application composition time, never a function,
flag or arbitrary endpoint supplied by an HTTP client. A lambda returning true in a
unit test is a fixture, not production authentication. A digest comparison proves byte
identity, not source authenticity. `production_binding_proven` remains false until a
separately recorded real-path proof exists; do not turn that field into a new authority.

The calendar's 17:00 ET expected-daily-data floor is a settle-buffer convention. A
16:01 ET completed close may legitimately be newer than that floor. The adapter must
require explicit bar-completion evidence, not pretend the session is still trading,
and must not invent that evidence from a wall-clock comparison alone.

## 3. Response contract

The structured consumer packet remains:

```
subject / horizon / as_of
canonical_market: existing verdict or explicit unavailable reason
observations: qualified value, unit, family, quality and original clock/reference
scenarios: own subject, definition availability/version, trigger, invalidation,
           deadline, support, counterevidence, status
coincident_conditions: ambiguity indication, not preferred-path ranking
readiness: research_only in this foundation
probabilities: absent/null until independently accepted evidence exists
authority: every initial signal/rank/size/trade/auto-exit/alert capability false
context_digest: deterministic identity, not an authorization token
```

The closed public projection removes internal source paths, raw source text and subject
identifiers not intended for that view. The application route still owns authentication,
subscription/data entitlement, personalized scope and safe public source labels. No
public endpoint is created by this foundation.

A response declares one coherent input generation. If a newer quote arrives while an
option book remains old, either preserve the named joint snapshot or mark the affected
scenario unresolved; do not silently combine them as one current dealer picture.
The public projection retains qualified observation clocks and typed trigger/
invalidation/counterevidence detail, without exposing private source references.
Future availability metadata is not presented as past knowledge. Lists are detached
so a client projection cannot mutate the original context.

No source condition can infer a hold/cross from a single price. Those conditions require
completed-bar sequences from the incumbent owner and their own explicit semantics.

## 4. Frontend and design seam

The production UI consumes the typed response and trusted public labels, never raw
repository content. It uses existing shared navigation, theme, authentication and
instrument context. Do not ship the research preview as a new top-level product page.

The preview is an interaction/visual study. Production must replace its sample values,
illustrative labels and disabled controls with real supported capabilities, or preserve
an explicit unavailability state. No fabricated price history is drawn. When source
qualification fails, the UI must not retain the old current-looking hero while only
changing a small footnote.

The request key is `(subject, horizon, cutoff policy, source generation, entitlement)`.
Ignore a late response for a previous subject/horizon. Clear or relabel dependent
content atomically. Templates work without an LLM. No chat-model output may change
status/authority, invent numeric confidence or control tool effects.

## 5. Save, restore, compare and watch

The Capital Structure saved-scenario implementation is domain-specific; do not write a
market-path object into that schema without an accepted owner change. Locate the
actual shared user-state owner, then define a compatible typed extension only there.

A save must retain the exact original subject/horizon/cutoff, scenario definition,
source-generation references and content identity. A later restore produces a separate
current comparison; it never rewrites the original target or deadline. Cross-user
identity and entitlement are server-enforced. Cache keys include user scope where needed.

A watch is an explicit user operation through the incumbent alert owner. No background
subscription, notifier, poller or outbox is created by loading a page or reading a
scenario. A stale/unqualified condition cannot escalate. Actual delivery needs a real
receipt; UI intent and queued transport are not delivery.

## 6. Ordered integration tests and proof

1. Existing owner fixture validates through its real schema; translation retains clocks,
   identity, quality, nulls and source references exactly.
2. Real read with deliberately missing receipt returns unavailable; no inferred current
   value or changed source state. Record exact target and generation.
3. Authorized current source with valid receipt reaches the compositor. Read-only
   browser shows the same canonical posture and its actual horizon/age.
4. Late/revised/stale/partial input changes produce the specified explicit states.
5. Delayed response and changed-symbol tests prove no cross-generation overwrite.
6. Signed-in save/restore proves actual backend persistence and cross-user isolation.
7. Native Paper node/export and implementation evidence match the full theme/language/
   viewport and failure-state matrix. Browser screenshot is not a Paper export.
8. Production deployment identity and real-path evidence are recorded separately from
   local tests, CI and merge. Only then claim the corresponding capability delivered.

## 7. Current exact release identity

Foundation PR: macro #10055. Initial published candidate:
`5c9b747049d40ea1486889cd1ab4ae97c452aff5` (upstream main integrated).
Current PR head/checks must be read from GitHub; this identifier is immutable historical
provenance, not a claim that no later source change exists.

No source adapter was promoted to production. No native Paper edit, account save,
notification, paid feed, raw corpus ingestion or trade occurred in this foundation.
