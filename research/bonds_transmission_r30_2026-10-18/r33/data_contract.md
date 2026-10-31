# R33 source publication and display contract

## Producer

**Data path:** `data/macro_context/decision_workspaces.json`

**Protected site mirror:** `site/macro-context-data/decision_workspaces.json` — the same serialization, byte for byte; added 19 October for the existing Bonds consumer.

**Schema:** `macro_context.decision_publication.v1`

**Producer:** the existing `scripts/build_macro_context.py` main function.

The existing `data/macro_context/latest.json` remains exactly five keys: `asof`, `macro_context_id`, `n_transitions_14d`, `headline_en`, `headline_zh`.

| Member | Meaning |
| --- | --- |
| `display_only: true` | Descriptive projection only |
| `claim_scope: projection_only` | No observation, event or saved-evidence admission |
| `probability_policy: withheld` | No empirical continuation probability |
| `hub` | Same five-key summary from the selected view model |
| `decision_workspaces` | Existing workspace projection, normalized to finite JSON |
| `publication` | Input fingerprints, component clocks, field origins and declared content identity |

## Identity and clocks

Input fingerprints hash normalized loaded values plus invalid-value diagnostics. Transition identity covers the last 60 parsed rows in loader order. The source files are not reread during fingerprinting.

`content_sha256` covers the normalized publication excluding itself and `built_at`. It includes the validation date. The declared algorithm is `sha256_python_sorted_compact_utf8_json`. The identity is suitable for content comparison only. It is neither authentication nor a resolvable retained-evidence identifier.

`built_at` is a UTC construction timestamp. `validation_date` is the date against which component dates were assessed. Components use explicit known/future/malformed/missing statuses and retain the reported raw value.

Six clock definitions are preserved: snapshot, oldest reported snapshot component, rates/credit, cross-asset funding, regime and FX/dollar. Each is a component date. It does not establish the observation time, availability time, vendor quote freshness or a universal market-close cutoff.

Related regime-series dates retain their upstream stale/cadence fields. A cadence-cleared monthly/quarterly input is still dated. A related vintage cannot become the field-observation clock of a broad HY spread or Treasury quote.

## Field lineage

The companion supplies 22 scalar Bonds display-field mappings. The [field manifest](source-field-manifest.json) records the actual selected file/path, display unit and component clock.

The producer mirrors the existing Python `primary or fallback` selection exactly, including empty-primary behavior. A selected fallback does not borrow the primary snapshot's receipt. Attempted paths remain inspectable.

`observation_asof`, `available_at` and `underlying_source_family` are null because the selected projection does not supply qualified field-level observations. An imported caller cannot fill these fields and thereby gain rule or evidence authority.

Nonfinite numbers are normalized to null with diagnostics. In the consumer, numbers must be finite numeric JSON values; numeric strings and booleans are not coerced. Explicit zero remains zero.

## Financial meaning

| Displayed context | Permitted reading | Still required for the richer claim |
| --- | --- | --- |
| Broad HY OAS | Dated index spread level | Complete matched 12-peer daily spread changes |
| 10Y–3M curve slope | That specific curve pair in percentage points | Separate 2Y–10Y observations for the design specimen |
| Calm funding proxy | Descriptive dated funding state | Exact instrument scope and qualified current funding receipt |
| Credit-canary flag | Owner-provided flag | Issuer default evidence and matched peer breadth |
| Duration lean | Macro context | An admitted position, sizing or trade recommendation |
| Real yield and term premium | Their individual estimates | A matched and complete yield decomposition |
| Stock–bond correlation | An upstream number with unspecified method/horizon | Evidence of causal transmission or lead/lag |
| Selected label changes | A limited selected transition view | Complete event history, event success or continuation result |

The consumer therefore exposes `evaluate=false`, `forecast=false`, `retain=false`, `monitor=false`. Event results, continuation probability and independent confirmation counts remain absent.

## Preserved offline captured example

The bundled publication was built locally on **18 October 2026 at 11:00:08 UTC** from Macro inputs pinned to `b912fd97827cca925a7123aa2012e9765077f3f7`. It is not a deployed-feed capture.

The captured rates/credit component is dated 16 October; the funding component is dated 17 October. The readable overview contains broad HY OAS 3.16%, 10Y real yield 2.88% and the owner's calm funding label. Those dated context values do not populate the surrounding synthetic scenario inputs.

Captured content digest: `d568576803a0fa032846f419fd433a9391e01c13e60e6dc4c75a8ff6017a1455`.

The inspector count 22/22 refers only to supplied display fields. It does not mean complete decision evidence. The existing hub's transition count and this locally rebuilt capture can differ because their validation dates differ.

## Current existing-Bonds integration publication

The separate [integration build receipt](verification/integration/build-receipt.json) binds six actual owner inputs at `80f270c44bcdf11f5e71dacc05b11a0875a01d7f`. The existing Macro generator assessed them on **2026-10-19** and built the site/data companion bytes at **2026-10-19T11:33:48Z**. The declared content digest is `bc376400bbed713cb8a85e2f528fd1fc066b7e388e6f3f07ffc7d494abf481d1`; the exact mirrored file SHA-256 is `53581d326fb985bd3abe1534625e42cab4517768803d6e792452c8ef10ccc98a`. Component dates remain 16/17 October, with the oldest reported snapshot component dated 14 October. These clocks have different meanings and none supplies the missing observation/availability timestamps.

This candidate is retained for evidence only. The mounted consumer fetches the protected site publication and has no fallback to either retained example. The older offline reference above and its 65+26 journeys remain unchanged.

## Failure behavior

- Missing/wrong schema, authority marker or selected-origin mapping: reject the publication.
- Invalid scalar type: preserve the raw diagnostic and show the field as unavailable.
- Missing/malformed/future date: preserve the explicit limitation; do not make an event admissible.
- File over 1.5 MB or malformed JSON: keep sourced values unavailable.
- Pending import: clear the previous displayed source values.
- Restore while a read is pending: invalidate the older request generation.
- Imported HTML: render as escaped text.
- Imported extra capability claims: ignore them; never admit them.
- Repeated views of one field: do not increase an independent evidence count.

The original research case, edits, selected rule and evaluator state remain unchanged across all source-inspection actions.
