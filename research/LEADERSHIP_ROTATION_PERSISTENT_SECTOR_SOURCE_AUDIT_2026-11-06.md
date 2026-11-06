# Persistent Sector Leadership — native evidence and consumer admission audit

Date: 2026-11-06. Scope: PSL-2 source qualification and PSL-3/4 consumer seams.
This is a source audit and dated native-shape proof, not scientific or production acceptance.

## Ruling

The first measured dossier is implemented and callable at Macro commit
`378e289b180b90ed2902a7689e960932a8a26fe6` through
`measured_group_read(..., include_sector_dossiers=True)`. It remains explicitly optional.
All existing default producer/parser bytes and core exports are preserved.

A retained native Sector Cycles artifact composes successfully for **all eleven sectors**.
Its session is **2026-10-22**, so it supplies no proof of current freshness. The actual retained
Risk Envelope is dated **2026-10-23** and declares `DEGRADED` coverage with off-session
sources. Joining these into one same-generation sector/risk explanation would be wrong.
The first slice therefore keeps risk unavailable and historical knowledge unqualified.

No sector fundamental adapter is admitted by this audit. Native basket/theme/issuer readers
exist, but their identities, knowledge clocks and purpose rights must survive composition.
The next implementation should call the existing owner-qualified reader at the authenticated
consumer boundary, then bind its exact admitted subject to an accepted sector/cohort mapping.
Copying a raw fact dictionary into the dossier would bypass that contract.

## Pins and evidence

- Protected Mastermind law and Mastermind code inspection:
  `fa46c271b23902555c5f3c83592edc2cf77069c6`.
- Macro source baseline: `26946d4f7b921a0940eef016c9d81fcf1adbeeda`.
- Terminal reader inspection: `3095319891bb557ba41f6c6fb5ec99a8aeaac0fc`.
- Implementation:
  [Macro 378e289b](https://github.com/mastermindx-market-intelligence/macro/commit/378e289b180b90ed2902a7689e960932a8a26fe6).
- Dated native read receipt:
  [LEADERSHIP_ROTATION_PERSISTENT_SECTOR_NATIVE_READ_2026-11-06.json](LEADERSHIP_ROTATION_PERSISTENT_SECTOR_NATIVE_READ_2026-11-06.json).
- Master plan:
  [LEADERSHIP_ROTATION_PERSISTENT_SECTOR_MASTERPLAN_2026-11-06.md](LEADERSHIP_ROTATION_PERSISTENT_SECTOR_MASTERPLAN_2026-11-06.md).

The audit inspected source contracts and retained artifacts, not every possible mapping in the
repository. “Not admitted here” does not mean no compatible mapping can exist anywhere.

## Source qualification matrix

| Native owner / object | Identity and clock actually present | Safe reuse | Unresolved admission obligation |
|---|---|---|---|
| `sector_cycles` / `rs_history.v1` | Eleven ETF ticker identities; source session; explicit SPY benchmark, total-return basis, 21/63 horizons; reconstructed history | Exact dated relative-wealth measurements; separate cross-sector positive counts | Native immutable generation, original availability and correction/retraction selection; current freshness; constituents/weights; requested 5/20 horizons |
| `group_earnings.compute_group_earnings` | Output keyed by `basket_id`; `as_of` from the sessions grid; `generated_at` is build time; live basket members use added/removed dates | Existing basket earnings context under its own identity, coverage and authority | An admitted sector relationship and overlap-aware cohort; original availability for historical cuts; source-specific claim/correction references |
| `theme_revisions.compute_theme_revisions` | Configured theme identity/tickers; aggregate `asof` is the maximum date in the current revisions cache; forward ledger is keyed theme/asof | Existing display-only theme revision context; keep its own member coverage | A sector/theme mapping and matching vintage; member-level availability; do not promote maximum cache date or rebuild timestamp into historical knowledge |
| `theme_graph.store` | Append-only bitemporal node/edge/evidence tables; latest edge belief selected by owner `read_edges(latest_belief=True)` | Existing semantic spine and its owner-selected view | A current view alone is not the requested historical knowledge cut; no raw parquet shortcut, new store or duplicate identity authority |
| `theme_graph.theme_state_owner_readers` | Re-reads native PIT membership, identity and rights; receipts bind captured read hashes; membership date-only, identity generated_at, rights registry revision | Existing consistency qualification and state/use readers | Receipt consistency is not authentication/rights grant; same-day knowledge may remain unproven; no automatic sector mapping or eligibility receipt |
| `theme_graph.economic_context` / issuer reader | Native DisclosureAuthority and read-only store supplied by entitled host; owner controls source selection, identity, rights, clocks and revisions | Existing owner-qualified current issuer fact view; first species is planned product integration | Not a shipment, contract, cash-flow share or forecast; no caller-supplied raw fact or plausible edge-ID bypass; bind admitted issuer fact to exact sector context |
| `risk_envelope` | Bundle ID over semantic source payload; market, revision, source_session, observed_at, produced_at, native coverage/freshness and individual source clocks | Existing market-global state and contradictory/degraded source information | Produced/observed time is not blanket original availability; keep market-global scope, exact source session, correction/revision and per-source freshness |
| `neuralweb.rotation_risk_context` | Existing compact/settled/live qualification with caller observation clock and entitlement; live preference verifies exact settled anchor | Reuse this risk consumer seam when composing later context | No fresh build may refresh old risk input; current/live preference is distinct from historical-as-known selection; no new risk verdict or policy |

### Immutable source references

- [Sector Cycles](https://github.com/mastermindx-market-intelligence/macro/blob/26946d4f7b921a0940eef016c9d81fcf1adbeeda/engine/sector_cycles.py)
- [Group earnings](https://github.com/mastermindx-market-intelligence/macro/blob/26946d4f7b921a0940eef016c9d81fcf1adbeeda/engine/group_earnings.py)
- [Theme revisions](https://github.com/mastermindx-market-intelligence/macro/blob/26946d4f7b921a0940eef016c9d81fcf1adbeeda/engine/theme_revisions.py)
- [Theme Graph store](https://github.com/mastermindx-market-intelligence/macro/blob/26946d4f7b921a0940eef016c9d81fcf1adbeeda/engine/theme_graph/store.py)
- [ThemeState owner readers](https://github.com/mastermindx-market-intelligence/macro/blob/26946d4f7b921a0940eef016c9d81fcf1adbeeda/engine/theme_graph/theme_state_owner_readers.py)
- [ThemeState use reader](https://github.com/mastermindx-market-intelligence/macro/blob/26946d4f7b921a0940eef016c9d81fcf1adbeeda/engine/theme_graph/theme_state_use_reader.py)
- [Economic context](https://github.com/mastermindx-market-intelligence/macro/blob/26946d4f7b921a0940eef016c9d81fcf1adbeeda/engine/theme_graph/economic_context.py)
- [Issuer economic context](https://github.com/mastermindx-market-intelligence/macro/blob/26946d4f7b921a0940eef016c9d81fcf1adbeeda/engine/theme_graph/issuer_economic_context.py)
- [Risk Envelope](https://github.com/mastermindx-market-intelligence/macro/blob/26946d4f7b921a0940eef016c9d81fcf1adbeeda/engine/risk_envelope.py)
- [Risk/rotation read context](https://github.com/mastermindx-market-intelligence/macro/blob/26946d4f7b921a0940eef016c9d81fcf1adbeeda/engine/neuralweb/rotation_risk_context.py)

## Native-shape proof

Read-only input was the retained M2 macro-main `site/sectordata/sector_cycles.json`,
1,909,102 bytes, SHA-256
`46a7b95a11446f12028a90cb071955710d516accd68f49db5ad99bab111194fa`.
The operation loaded that file once and called only the pure measured reader, first with
the default and then with the dossier opt-in. It invoked no producer, collector, ledger or
publisher. Original Studio process 12800 returned the proof retained in the JSON receipt.

Results:

- 11 of 11 group identities and both native windows qualified; no duplicate/outside/malformed rows.
- `measurement_status=available` while `status=partial`: complete measurement coverage does
  not claim a complete explanation, qualified risk or persistence forecast.
- Serialized dossier: 4,788 UTF-8 bytes for this input.
- Removing the optional addendum yields exactly the original default projection.
- Native artifact bytes remained unchanged.
- Freshness remains `unverified`; original availability is null; historical admissibility is false.
- Every ranking/gating/sizing/trading/escalation permission remains false.
- This is source-shape/read-path evidence on a retained dated artifact. It is not a deployed
  API/browser receipt or an observation of today's market.

For comparison, the retained canonical settled risk artifact
`site/riskdata/risk_envelope.json` has bundle `51ae9c5eed283a36`, source session
2026-10-23, produced/observed time 2026-10-24T01:04:03Z and data state DEGRADED.
Its freshness declares off-session leadership and rotation sources. Those facts explain why
risk is not silently joined to the 2026-10-22 sector example; they are not current risk advice.

## Consumer implementation contracts

### Macro

`engine/sector_central.py::_measured_read` is the existing owner call and `compute`
already publishes `measured_read`. The new flag must be intentionally activated there,
using the generation owner's supplied inputs. #10780 owns that path and the native generation
contract. Reconcile its current head and changed contract before editing; do not duplicate
its scheduler/publication work. The legacy default remains unchanged meanwhile.

### Terminal

`terminal/lib/sectorIntelligence.ts::sectorMeasuredRead` currently narrows the producer
object. The additive typed dossier parser in [Terminal #1332](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1332)
now preserves all eleven identities, exact horizons, status/null reasons and source metadata.
Unknown schema or malformed addendum yields an invalid dossier result while leaving the
accepted legacy measured panel intact. Head `260002504a80e2ce297cec2a82b2f5c73290816c`
passed 80 focused tests, route type generation, full TypeScript checking and lint.

The existing `terminal/app/api/sector-intelligence/route.ts` gateway already forwards
the sector payload. No new URL, auth fallback, independent fetch or endpoint is needed.
Any detail/source-inspector rendering follows accepted design and actual writer custody.
This slice adds only separate parser/tests/fixtures. #1232's shared parser, #1244's gateway
and #1249's Workspace/cycle UI remain unchanged; #1249's recorded design hold is preserved.
A source parser and passing local owner-envelope fixture do not prove a signed-in HTTP/UI path.

### Portfolio intelligence

`brain/portfolio_intelligence.py::sector_rotation(limit=6)` currently projects legacy
sector/basket rows. Whole-cohort dossier coverage cannot be hidden inside that top-N slice.
The explicit `projection="sector_dossiers"` now returns a separate bounded all-eleven
projection through that same reader and `brain/autonomous_mcp.py::get_sector_rotation` in
[Mastermind #2157](https://github.com/mastermindx-market-intelligence/Mastermind/pull/2157),
head `21775669516630a183817f1ef334be0ff7d4aba2`. The existing artifact reader and
`brain/bot_mcp.py::_json` serializer remain the path. Default ranking, limits, `_rotation_row`,
`market_packet` and the remainder of the portfolio module are byte-identical to the protected
base. No new ranking/sizing, tool namespace or fallback truth source is introduced.

## Transport qualification and exact source exclusions

The [retained transport receipt](LEADERSHIP_ROTATION_PERSISTENT_SECTOR_TRANSPORT_PROBE_2026-11-06.json)
records both the rejected raw approach and the qualified alternative.

| Case | Actual decoded result | Ruling |
|---|---|---|
| Raw dossier alone, representative partly available fixture | 4,808 characters; 11 sectors | Does not qualify larger/unavailable responses |
| Raw dossier appended to six legacy sectors and six baskets | 11,353 input characters → 6,490 output; only 3 sectors, declared expected_n still 11 | Inadmissible |
| Raw unavailable dossier alone | 8,304 input → 7,791 output; only 10 sectors | Inadmissible |
| Selected compact partly available fixture | 4,323 UTF-8 bytes; 11 sectors; no truncation | Locally qualified |
| Selected compact unavailable fixture | 4,943 UTF-8 bytes; 11 sectors; no truncation | Locally qualified |
| Selected compact retained 2026-10-22 native source | 4,298 UTF-8 bytes; all 11 measured, dossier partial, exact values/shared qualifications | Local native-shape parity; not a natural publication or production endpoint |

The selected packet retains shared native qualifications and encodes exact row reasons through
a reason table. Its 7,200-UTF-8-byte ceiling is below both the current character budget and the
separate held strict-byte transport proposal. Invalid, unsupported or oversized input yields all
eleven **expected** identities with null values and `cohort_status=expected_not_admitted`.
It never labels a truncated subset complete. The actual handler/serializer suite has 65 new
contract cases; the combined incumbent MCP/common-stock boundary suite has 123 passes and one
live-vendor skip. No model turn, live portfolio, server, publication or deployment was invoked.

Bounded current custody checks examined relevant named candidates, not every one of the 192
open Mastermind PRs. #548's refused legacy ID/freshness/view/pagination/correction repair remains
excluded, along with its tests/plan. #495 and #790 retain generic serializer/own-book work;
#673 retains receipt-only snapshot capture; #1357/#1831 retain research-snapshot and SDK-retry
effects; #901 retains the reverse Portfolio→Macro publication seam. #900 aliases the existing
decorated handler, so the selector is shared read capability; its Advisor composition is unchanged.
No child provided a formal GitHub approval. Parent self-review and bounded C3 source judgments
do not substitute for any actually enforced native release requirement.

## Gates for the next explanation slice

1. Select one exact native subject/cohort mapping and source cut through its incumbent owner.
2. Retain issuer/security/theme/sector identity, membership vintage, benchmark and overlap.
3. Invoke the existing authenticated owner reader; preserve rights and source/effective/knowledge clocks.
4. Use real source references and native correction/supersession selection. Absent evidence stays absent.
5. Express a supported mechanism alongside alternative causes, contradictions, falsifiers and the next
   observable check. A price move alone supplies no causal explanation.
6. Keep global risk scope and its native coverage/conflicts. Mismatched dated generations do not join.
7. Prove the same content at each consumer and retain at least one unavailable/contradictory case.
8. Keep forecasts/weights null and the separate LR-W6 scientific embargo unchanged.

No new LLM narrator, registry, state store, polling loop, risk composer or authority plane is
needed to pass these gates. This audit advances the implementation contract; it does not
declare the mechanism, history or consumer milestones complete.
