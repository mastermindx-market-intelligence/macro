# Private breadth and basket-member generation

Mission: [always-on Macro migration](https://github.com/mastermindx-market-intelligence/macro/issues/10779)  
Implementation carrier: [PR10780](https://github.com/mastermindx-market-intelligence/macro/pull/10780)  
Source base: `519b2ae0060c40db6ae01b928157ca304ff4d7c8`  
State: parent source implementation qualified; runtime remains inactive.

## Purpose and ownership

Sector calculations need the broad constituent archive and thematic membership in addition to the exact fourteen-symbol Yahoo cycle cohort. This contract puts those inputs into one immutable private generation using the existing live orchestrator's publication, selection, locking and verified-byte reader.

It adds no scheduler, provider owner, authentication system, data cache, selection pointer implementation, or replication service. The input bundle is not a public API payload. The existing Sector output generation and authorized API remain the product boundary.

The fixed domain is `sector-breadth-members`. Its receipt schema is `sector_breadth_members.v1`.

## Fixed nineteen members

| Logical member | Count | Meaning |
| --- | ---: | --- |
| `groups/<group>/<field>.parquet` | 12 | Exact groups breadth, smallcap_breadth, midcap_breadth; fields close, high, low, volume. Full admitted archives, including retained/departed columns. |
| `groups/<group>/constituents.json` | 3 | Captured repaired symbol/name/sector rows, preserving constituent order. |
| `baskets/membership.json` | 1 | Complete captured membership, including dated additions/removals and descriptive metadata. |
| `baskets/extras_close.parquet` | 1 | Full supplemental close archive. |
| `references/close.parquet` | 1 | Explicit qualified optional basket reference closes; an empty primitive parquet is still present. |
| `acquisition.json` | 1 | Source capture identities, effective policies, observed acquisition and resolver evidence, Yahoo dependency, prior identity, and explicit optional-reference absences. |

The generic manifest remains the authoritative artifact hash/length inventory. The domain input identity binds the receipt digest, exact Yahoo content ID, source session, preparation time and producer source revision. There is no second manifest or separately persisted merged price matrix. These identities bind the captured repaired values; they do not prove the raw pre-repair constituent response or historical custody of an external source document.

## Primitive wide-panel codec

The panel format contains a timezone-free `session: timestamp[ns]` and sorted primitive float64 symbol columns. It accepts no pandas/serialized Arrow schema, extensions, nested values, ambiguous fields or arbitrary metadata. JSON decoding rejects duplicate keys, nonfinite literals and exponent-overflow values such as 1e400.

Present prices must be positive and finite; present volume may be zero and must be finite/nonnegative. Missing cells remain missing. Dates must be unique, increasing, midnight US session dates and no later than the declared source session.

Engineering bounds are separate from economic history policy:

- Existing capture bounds: 50,000 rows, 5,000 columns and 5,000,000 cells per panel.
- Existing publication bounds: 64 MiB encoded per member and 512 MiB for the generation.
- Wide codec: at most 8 MiB footer, 32 row groups and 64 MiB declared/materialized decode per panel.
- At most 256 MiB of prospective panel values across the bundle, checked from metadata before materializing the panels.
- JSON members at most 8 MiB.
- Prospective union rows, columns and cells are bounded before merging or reference concatenation. The membership projection is bounded before resolver allocation.

These are refusal boundaries. The adapter does not truncate archives or delete departed names to make an input fit. The narrow Yahoo codec retains its existing tighter bounds.

## Admission and composition

All three breadth acquisitions must have the same completed source session as the captured Yahoo generation. The final publisher callback re-evaluates the completed US target at actual admission time; crossing the next target boundary refuses the candidate and preserves the prior selection.

Breadth acceptance is recomputed against the captured constituent populations. The existing post-repair floors remain 400 large cap, 450 small cap and 350 mid cap; at least ceil(active × 0.8) members must be newly qualified at the target in all four fields. Retained, departed and unresolved columns cannot count as current acquisition. The receipt records actual MA/NHNL history policy, ticker fixes, exclusions, effective retry/batch/basis settings and per-member canonical/vendor identities. Yahoo's 1,000-session policy is not applied to breadth.

The shared panel merger now has a value-only entry point. The legacy filesystem wrapper delegates to the same calculation. Runtime composition:

1. Uses the established breadth → smallcap_breadth → midcap_breadth order.
2. Chooses each column by its last actual observation, with that order breaking ties.
3. Preserves the existing longest-donor history stitch and its five-overlap/1e-6 agreement requirement.
4. Aligns the merged primary to the exact captured Yahoo SPY close observation.
5. Determines primary acquisition qualification from the selected column's actual source group.
6. Resolves thematic extras on that frozen calendar through the existing resolver.
7. Recomputes extras population, required historical observations, selected-source evidence, and complete/partial/unavailable status.

The supplied acquisition's resolved panel must exactly equal an independent replay from the serialized inputs. It is not stored as another price authority. Extras may be partial; the existing per-basket population owner still determines whether each basket can be emitted.

The explicit BasketInputs path receives the untrimmed broad panel, original captured SPY, separate extras, labels and references. The basket core retains its own common-observation receipt. Label priority remains constituent group/row priority, independent of the freshest price tier. An optional source_basis field carries the actual explicit basis into the resolver; legacy default receipts remain unchanged. Adjustment vintage remains unrecorded.

## Optional basket references

Reference requirements come from captured membership rather than the six-item legacy seed list. References already in the captured fourteen-symbol Yahoo generation must use that exact capture; the optional panel cannot override them.

Each other requested reference is explicitly available or absent. Available reference evidence states its actual source, capture clock and established adjusted basis. Its close series must contain at least 62 actual observations and an actual target close. The existing basket correlation still requires more than 60 joined return observations.

Absent references have a closed reason such as not_captured, not_current or acquisition_failed. There is no store fallback, fabricated second basis, implicit seed refresh or forced 1,000-session minimum. The runtime BasketInputs option requires all legs of a configured blend and propagates a missing leg return on each included date; a missing leg withholds that reference while preserving the basket calculation. The incumbent historical forward-fill policy remains unchanged. The legacy default blend behavior is unchanged.

The source audit at the base found 30 configured basket reference symbols: twelve overlap the Yahoo fourteen, five additional names have an ordinary Yahoo universe origin, and thirteen do not. This maps acquisition configuration; it is not a claim that all stored reference files are missing or stale. IBIT and SIL specifically can be left frozen by the legacy create-if-absent proxy seed path. Additional-reference acquisition and writer transfer remain separate deployment obligations.

## Recovery of pinned dependencies

Yahoo and breadth are separate coherent input generations. If Yahoo advances and breadth acquisition fails, the old breadth generation remains valid as a prior against its original Yahoo dependency.

The existing publisher now exposes a read-only retained-generation facade:

`read_retained_generation(generations_root, domain, generation_id, content_id, members)`

It validates the exact identity and bounded member names, constructs the exact retained directory, and calls the incumbent retained-byte verifier once. It never reads current.json, scans for alternatives, selects a generation, creates locks/directories or repairs state. Symlink ancestors, malformed identity, absent members, corrupt bytes and a mismatched content ID refuse.

A breadth read captures its own selected snapshot once. When no explicit Yahoo capture is supplied, it resolves the exact retained Yahoo dependency named in those verified receipt bytes, then uses the shared Yahoo semantic decoder. This recovery permits older input generations as priors; new publication still requires the current completed target.

The breadth receipt binds the original Yahoo publication time explicitly, because the generic content ID does not include that clock. Recovery never substitutes the current selection or recovery time. A changed retained publication time therefore fails dependency validation even if the generic content hash is unchanged.

## Publication adapter and effects

Both input domains now share one private ephemeral staging helper in the existing Orchestrator. Each typed adapter validates and detaches its member bytes and identity before staging. Staged files are private and fsynced; publication still uses the same final bundle validator, original expected-current-content-ID fence and original result semantics.

A rejected candidate leaves selection unchanged. An uncertain publication is returned as uncertain; neither adapter retries or refreshes the fence. A source-to-source selection race is not permission to republish against a newer fence.

## Qualification

The initial controlled-source run passed 27 focused tests. A subsequent combined contract/Yahoo recovery run passed 126 tests with six pre-existing pytest temporary-directory cleanup warnings. These counts overlap; they are not additive.

Final receipts are recorded below. Tests use controlled incumbent acquisitions and the actual temporary publisher/reader/calculator. They do not establish provider availability, production activation, runtime ownership transfer, CI registration, or authenticated beta acceptance.

## Remaining delivery work

- Wire acquisition sequencing and explicit bootstrap capture to the existing snapshot lane.
- Acquire and transfer the remaining reference inputs through the incumbent Yahoo owner.
- Supply actual auxiliary calibrations, ledgers, market context and holdings; do not relabel their older vintages.
- Complete the data-only basket handoff, canonical board and final five-member Sector composition.
- Complete source-updater crash recovery/first-install fencing, drain legacy writers and prevent downgrade.
- Resolve the existing CI capability-owner gate, complete protected release, mount the existing authorized API, bind the Terminal consumer and prove authenticated beta source-to-screen refresh.
- Continue the remaining dashboard family migration waves under the pinned master plan.

## Final source proof — 2026-11-06T08:58:40.323039+00:00

| Run | Passed | Log SHA256 |
| --- | ---: | --- |
| final_contract | 49 | `0260cceeed8c924349c27bf8e72ffc4103c73ac7d8ee6f6cc06735094b429cf2` |
| affected_consumers | 76 | `3201d2d38d86247d47980cf6c2e74ad9e863ac7d04fe4f3b44446a1f4076c2ac` |
| expanded | 254 | `13ce4ba84955bda0581cfbc454bffc0606ff0e6a33e4b3c1a535be28ddf1a664` |
| generic_publisher | 68 | `b0561e1ea34094af5bc46db03d03630e0747fe48f498a903c6170036b02a497f` |

All listed commands exited 0; counts overlap. The generic publisher selection ran with 88 tests deselected. Each run reported six pre-existing pytest temporary-directory cleanup warnings. Final `git diff --check` exited 0. The last contract run includes dependency-content recomputation using the incumbent publisher hash function; the separate consumer run includes complete-leg and nonfinite-decoder counterexamples.

Independent legacy compatibility uses `tests/fixtures/base_closes_merge_519b.py`, extracted literally from the base source whose SHA256 is `4d0388506ac93f5dddac6dc50545cb4029b567ea4986e49df202d346f370634e`. Fixture SHA256: `9a0558f02defca3b8be28c26dfae9bab28b5389bdbf27e28eac232fd7b29e8f1`. The full-candle, source ownership, release and beta acceptance obligations remain open.
