# D08C receiving decision: B → C exact-contract entry

**One bounded non-merge continuation.** Observed November 3, 2026, 8:30pm America/Chicago (02:30Z November 4). D08C remains Draft on #10687. This source-only addendum qualifies the receiving boundary raised by D08B; it changes no product, Paper target, route, shared interface version, account state or release gate.

## Decision

**C accepts D08B's boundary qualification as a source/design constraint.** The admissible existing local-draft path starts with a separately resolved, actual `doi` or `hot` source row and its original unfiltered source list. A B exposure node, cohort member or chain coordinate is origin evidence; it is not itself a `ShortlistPin`.

**No arbitrary exposure/chain adapter is admitted by this change.** C's exact shape checks do not authenticate a provider, prove that a supplied row belonged to a supplied list, or prove the list is complete. A caller must not manufacture a one-row list, recast a B row as `doi`/`hot`, or treat successful validation as source qualification. The new executable evidence demonstrates these limits directly.

This resolves the C-side ambiguity in D08B's §5 question. It does not establish a mounted B→C UI path or release the held Plan/Investigation integration. D08 retains shared navigation/interface admission; C retains draft/payoff semantics; the existing source and access owners retain provenance/entitlement; D23 and original #804 retain persistence/watch gates.

## Exact inputs consumed

| Input | Exact source |
| --- | --- |
| Protected law | Mastermind `910803421beca53ca25145392725ab2d84c7a8e9`; current protected `master` refresh matched the prior compatible pin; `mastermind.sol_skillpack.v1`, skillpack1.0.1 / bootstrap1 |
| Frozen shared contract | [D08-OPTIONS/1.0.0](https://github.com/mastermindx-market-intelligence/macro/blob/d0516e1bad9cb5982d43d20c4167d0355cb70e2c/research/design_candidates/production_design_20261102/d08/SLICE_INTERFACES.json) |
| B return / question | [#10649 comment6620312718](https://github.com/mastermindx-market-intelligence/macro/pull/10649#issuecomment-6620312718); B Draft#10686 `a3356474cebbdd88e6448e05ffc3d2e44faa5ca6` |
| B source contract | [SOURCE_BUILD_CONTRACT §5](https://github.com/mastermindx-market-intelligence/macro/blob/a3356474cebbdd88e6448e05ffc3d2e44faa5ca6/research/design_candidates/production_design_20261102/d08b/SOURCE_BUILD_CONTRACT.md), blob `abc4a489227b464b8772df65158c6cbabbc15716` |
| Original C review packet | [#10687](https://github.com/mastermindx-market-intelligence/macro/pull/10687), `291f21aa8e9d757466412549a8d6537d889ab4d8`; all original 53 files remain byte-identical |
| Exercised consumer | Terminal `2ded360882b9c721e690907ff363b553781fb920`; exact shortlist/draft blobs listed below |
| Current protected consumer refresh | Terminal `d1b8b171f0ad5788e427a0bab96fb8fb3d180b85`; both exercised blobs are unchanged, verified by fresh reads |

The vendored `upstream/` files are byte-identical test inputs from the owned Terminal repository, not new product modules. `optionsContractShortlist.ts` is blob `8d42da79f3e5bbda9ea236df93845824feb4900d`; `optionsPlanDraft.ts` is blob `1b02689501cd26226b61e7a5d3fa8f5868552f7b`. The harness verifies these Git blob hashes before executing them.

## Receiving rules and useful recovery

| Incoming state | C disposition | Researcher-facing next step / preservation |
| --- | --- | --- |
| Aggregate-only node or cohort | `aggregate_only`; do not synthesize a leg | Keep node, lens, vintage and return context. Offer actual contract investigation where the existing host supports it |
| Exact B coordinate without an actual supported source row/full-list context | `missing_evidence`; no cast into `doi`/`hot` | Explain “Choose a contract from its source list.” Navigate through an existing admitted Screener destination/selection, without invented Plan query keys |
| Actual accepted `doi`/`hot` row, complete original-list context, unique valid identity | Existing `buildPin` then `createOptionsPlanDraft` may produce a local research draft | Preserve copied row, source family/hot view, session/raw as-of, schema, stale marker and exact contract terms. Leave side, quantity and entry null until authored |
| Missing optional terms | Preserve explicit nulls; draft retention can still succeed | “Terms not supplied.” Do not infer 100 shares, settlement, exercise style, deliverable or payoff eligibility |
| Malformed supplied terms or ambiguous full-list identity | Preserve exact helper refusal; shared design category `ambiguous_terms` where applicable | Keep B investigation and actual source evidence. No arbitrary first-match selection |
| Same identity/family/session through another hot view | Existing pin, not another contract | Keep source-list provenance; focus existing selection. A view change is not a refresh |
| Same contract observed in DOI and Hot | Observation comparison can retain both pins; Plan rejects duplicate contract identity | Ask for an explicit observation choice for the leg; retain the other as separately labelled evidence where the existing host supports it |
| Fifth selection | Existing `full` refusal | Preserve the four existing pins; let the user remove one explicitly |
| Distinct exact roots | Existing draft `mixed_root` refusal | Do not normalize adjusted roots or silently change one leg. D08 owns any later shared refusal-vocabulary amendment |
| Mixed expiry, stale evidence or unknown terms in an otherwise valid draft | Preserve research; calculation remains separately qualified | Explain the actual payoff restriction when calculation is requested; never delete the research to make a curve possible |
| Access/context changes while resolving | Existing source/host owner decides visibility and stale-response rejection | Hide protected former-owner data, retain only lawful origin context and disclose a named fallback if the original target is no longer reachable |

The frozen exchange's `unsupported_payoff` is a calculation boundary, not permission to discard a valid draft. The shared interface is logical design vocabulary; this addendum introduces no runtime result enum, wire field or endpoint.

## Required caller custody

1. Obtain the selected row, family, source envelope and full original unfiltered list from the **same existing source reader generation**. Keep exact source namespace/root and access ownership. A B coordinate alone is insufficient evidence of that origin.
2. Preserve the original full-list content for ambiguity checking. Do not substitute the displayed/filtered page or manufacture `[selectedRow]` as a supposed full list. Treat the captured list as immutable; the helper's list cache is not a source-version authority.
3. Check actual supported source family at the receiving boundary, then use the existing helpers. A TypeScript union is not a runtime provenance check. Run the draft validator as well; `buildPin` alone is insufficient.
4. Preserve the returned pin's exact fields. A root suffix, supplied term or source session is part of identity/basis; source-list context is retained provenance, not a replacement deduplication key.
5. Keep B's node/cohort/return object separate from the closed pin/draft payload. Do not insert an `originNode` or arbitrary provenance field into `options_plan_draft.v1`. Use the incumbent host's validated transient return context and, when separately admitted, its existing selected-evidence mechanism. If an evidence reference is not admitted there, report the gap rather than inventing a field or store.
6. Before an explicit transition, show whether the actual selected contract is independently sourced or has a qualified exact association with the B evidence. Matching display labels alone do not prove that association. Neither B's measurement nor a later source row rewrites the original observation.
7. Keep local draft creation, payoff qualification, native admission, Save/readback and watch activation separate. These pure functions perform none of the latter effects.

No new trust service, signed payload, identity registry, fetcher, cache or persistence plane is required by this decision. These are caller obligations on existing owners. Their actual UI/source binding is a future implementation gate.

## Executed proof

Run from this directory with the recorded runtime:

```bash
node verify_boundary.mjs
```

Recorded environment: **Node 24.22.1**. Result: **20 behavior checks passed; four trust limits reproduced; zero failed checks**. [RESULT.json](RESULT.json) records each named case. The harness runs the real pinned pure modules. It uses Node's type erasure and resolves one exact local import extension in temporary generated files; both original TypeScript inputs remain unchanged. No package installation, network request, browser, account, Save, alert, database or product edit is involved.

The behavior cases exercise actual accepted-row entry, aggregate refusal, full-list ambiguity, exact roots/terms, clocks, hot-view deduplication, duplicate observations versus duplicate legs, four-pin capacity, null authored assumptions, same-root requirements, mixed-expiry retention, closed-payload checks and detached evidence.

### Four limits deliberately reproduced

| Case | Actual result | Integration implication |
| --- | --- | --- |
| L01 | A full duplicate-containing list refuses the pin; a filtered singleton can pass | The caller must carry the full original list, not the filtered display |
| L02 | `buildPin` can accept a row absent from the supplied list | The existing source owner must establish row membership; shape validation does not |
| L03 | `buildPin` can carry a runtime family outside its TypeScript union; draft validation rejects it | Do not call `buildPin` the complete admission gate |
| L04 | A fabricated source-labelled row can pass both pin and draft shape validation | Successful parsing is not provider authenticity; arbitrary B→C casts remain prohibited |

`REPRODUCED` is evidence of a limit, not a successful security guard. The run does not prove the mounted B→C path, provider authenticity, qualified calculation, save/reopen or watch. The original 47 future product scenarios remain NOT_RUN; the original 238-check arithmetic proof remains a separate evidence class.

## Quick acceptance/integration census

| Carrier/gate | Observed state and next owner |
| --- | --- |
| D08 #10649 | Open Draft at `e89f527e3267b1d1dd27ac7507e9a25983c0c903`. Source-only approval5748205136 is bound to older `a4281091`; it does not approve the current native/reference set. D08 owns slice consumption and contextual admission |
| D08C #10687 | At census, open Draft at `291f21a…`; no formal review/comment return. This addendum advances only the C receiving question, preserving the original 53-file review input |
| Hosted authority check | D08C run [41757297246](https://github.com/mastermindx-market-intelligence/macro/actions/runs/41757297246) on `291f21a…` reports `unsupported_base_ref` for the stacked D08 branch. D08's latest observed run41599134897 is also failed. No retarget, rerun, queue or CI bypass is performed |
| F01 #10645 | Head `abfecf1efc452383fe720cb3ea2016ad8d7088e0` unchanged; policy concurrence received, final foundation/runtime/native qualification remains open |
| F02 #10630 | Advanced to `32ea8d5b132ff8f65e9c66ed3224d4e0f6f0c68f`. [Non-author source review5762038797](https://github.com/mastermindx-market-intelligence/macro/pull/10630#pullrequestreview-5762038797) is COMMENTED, with parent-ledger integration correction required and PR-wide approval withheld. Original effect/full-set and formal acceptance gates remain separate |
| Original Terminal #804 | Head `27df56d997df0ae94a17b6b8e2d14867431bb394` unchanged, Draft/HOLD. Original hold5989604142, T03k/effect/exact-0030 and authenticated acceptance constraints remain with its receiver |
| Served product | Prior access-verification failure remains the last D08C browser observation; no fresh normal-data, entitlement or save/watch proof is claimed |

F02's shared `SESSION_RETURNS.md` risk belongs to the existing F02/programme owners. This addendum changes no shared ledger and imports no F02 tree. Foundation progress does not justify redoing the accepted D08C compositions.

## Scope, disposition and exact successor

**Completed delta:** the C receiver has answered B's source-family/adapter question, with executable behavior and trust-limit evidence against the actual consumer. The current protected consumer refresh confirms both exercised blobs are still unchanged. This is a concrete source/design qualification, not a shipped entry feature or formal reviewer approval.

Direct execution rationale: `PRINCIPAL_JUDGMENT / LOWER_TOTAL_OVERHEAD` for the bounded receiving decision and two-module characterization. A native read-only advisor supplied the independent gate census and was closed ACCEPTED/STOP. No Fabric, model, mode, account or worker admission was changed; no background execution is claimed.

**Next owner action:** D08 can consume this C decision together with B §5, record the existing-source resolution path, and keep a generic B-row adapter unavailable until separately specified and admitted through its incumbent source/C build scope. An eventual builder must prove actual source membership/full-list custody and the preserved node/lens/vintage return in the admitted host. D23/#804 and formal foundation/QA01 gates remain intact.

The original 53-file packet, all 11 Paper boards and all original effects are untouched. Only this additive source/proof directory is published. No merge, Ready, un-draft, enqueue, held-PR relabel, uncertain-operation replay or deployment occurred. The user requested one next non-merge step; this return ends at that bounded completion.
