# D04 — Verified implementation delivery and packet reconstruction

**The bounded Confluence implementation is committed and published in held [draft #10705](https://github.com/mastermindx-market-intelligence/macro/pull/10705), at `126bb13421d7052527ce034a900c89cd1a7fb9e6`.** This is the current evidence index on the existing D04 domain carrier, [draft #7727](https://github.com/mastermindx-market-intelligence/macro/pull/7727).

Read the [complete implementation/design report](https://github.com/mastermindx-market-intelligence/macro/blob/8057a2bd6a3ad43e3bf64e3f1a6a96c64cc019cf/research/design_candidates/production_design_20261102/d04/implementation_20261104/evidence_bundle/IMPLEMENTATION_REPORT.md). The Chairman's “Resume design and implementation” instruction commissioned the source work. Merge, Ready/un-draft, enqueue, held relabels, unauthorized Paper writes and production deployment remain held.

## What is complete

The researcher sees the full eligible population separately from the top three displayed, equal-weight recent/test and older/training evidence, visible sample counts and accurate EN/ZH methodology. Missing source and optional evidence stay unknown. Protected identities hydrate only after the complete response matches the public source generation and row contract. Auth-owner changes, late responses, session expiry, retry focus and native company Back were exercised.

| Verified item | Result and boundary |
| --- | --- |
| Focused unit/miner suite | 138 passed; zero failures/errors. |
| Finite local browser suite | 39 passed; real renderer/theme/handlers with controlled auth/HTTP fixtures. |
| Canonical source captures | 24 native captures in #10705: eight theme/locale/viewport cells at rest, focus and hover. |
| Additional packet captures | 23 original PNGs, preserved as base64 records and reconstructed byte for byte. |
| Packet integrity | 30 checks pass; 69 file digests plus the manifest account for all 70 packet files. |
| Programme retention | Ten canonical route families, 113 capabilities, 24 aliases and 49 baskets retained; zero removals. |
| Acceptance boundary | All 75 full-programme product cases remain unpromoted; 25 inherited reference conditions retain their recorded dispositions. |

## Exact evidence representation

The current carrier stores **14 committed UTF-8 bundle parts containing all 50 prepared artifact changes**: 27 original text files and 23 original PNGs. Every part was read back at its immutable commit and matched its local UTF-8 bytes exactly. The [manifest](https://github.com/mastermindx-market-intelligence/macro/blob/ad7620f29bab7be1fe9442a2a6eb5202907d108d/research/design_candidates/production_design_20261102/d04/implementation_20261104/evidence_bundle/manifest.json) records each part's bytes, SHA256, Git blob SHA, commit and parent.

Apply those changes to the exact 34-file D04 baseline at `23bd2c0b7400548485e39c119954977b8a9f3472` to recover the complete 70-file current packet. Reconstruction and the packet's 30 checks passed. The current plain files outside this bundle retain the historical baseline except for this delivery index; run current packet verification in the reconstructed directory.

The original prepared native tree, `150adb0b196a002c34a6edebec2b223c56dd146f`, was **not committed**. GitHub's Git commit endpoint returned definitive HTTP 422 “Tree SHA does not exist” twice, despite successful original-tree readback and an unchanged original branch. That operation was stopped. The supported Contents API then persisted the same artifact bytes to the same authorized branch. There was no alternate credential, new carrier, force update or unknown ref effect. Native placement of the 50 prepared files remains unmaterialized; encoded persistence is complete.

## Reconstruct and verify

Use an existing authorized checkout containing the baseline commit and this bundle directory. Export the baseline into a new empty directory:

```sh
mkdir /tmp/d04-baseline-20261104
git archive 23bd2c0b7400548485e39c119954977b8a9f3472:research/design_candidates/production_design_20261102/d04 | tar -x -C /tmp/d04-baseline-20261104
python3 research/design_candidates/production_design_20261102/d04/implementation_20261104/evidence_bundle/materialize.py --base /tmp/d04-baseline-20261104 --output /tmp/d04-restored-20261104
python3 /tmp/d04-restored-20261104/verify_spec.py
```

The [materializer](https://github.com/mastermindx-market-intelligence/macro/blob/7187e9ae4079ed7438af9a77b613a792b0d57550/research/design_candidates/production_design_20261102/d04/implementation_20261104/evidence_bundle/materialize.py) uses Python's standard library. It checks the pinned baseline, every part, every original file and the final file set before writing. It refuses an existing output directory. The packet verifier also uses Pillow to read actual image dimensions. Neither operation executes product mutations or publishes code.

| Complete deliverable | Path in the restored packet |
| --- | --- |
| Current overview and evidence | `README.md`, `implementation_20261104/README.md` |
| Product and interaction contract | `PRODUCT_AND_UX.md` |
| 113-capability retention ledger | `CAPABILITY_LEDGER.md`, `capabilities.json` |
| Ten-route/backend/data contract | `ROUTES_AND_DATA.md` |
| Aliases, basket IDs and return compatibility | `COMPATIBILITY.md`, `compatibility.json` |
| Build guidance and 75-case acceptance plan | `BUILD_AND_ACCEPTANCE.md`, `acceptance_cases.json` |
| Scoped actual test coverage | `implementation_20261104/coverage.json` |
| Paper identity and continuity | `PAPER_REVIEW_AND_GATES.md`, `REVIEW_CONTINUITY.md`, `review_continuity.json` |
| Original source/website/Paper evidence | `SOURCE_INDEX.md`, `evidence/` |
| Actual implementation proof | `implementation_20261104/evidence/`, `quality_gates.json`, `publication_receipt.json` |

The [24 canonical product captures](https://github.com/mastermindx-market-intelligence/macro/tree/126bb13421d7052527ce034a900c89cd1a7fb9e6/mockups/evidence/d04-confluence-evidence-20261104) remain directly viewable native files in the implementation carrier.

## Remaining boundaries

F01/F02 final joint foundations and exact Paper admission remain prerequisites for final composition. Broader heatmap exact-state return, D23 fixed/live saved-view integration and full ten-route acceptance remain in the complete contract. The bounded source implementation does not claim live production entitlement/revocation proof, cross-origin state restoration, Safari/iOS, actual 400% zoom or a complete assistive-technology audit. Existing shared Brain overlap on phone remains disclosed.

At the source observation on 2026-11-04T05:28:37Z, main authority, fence-pack, contract-delta and ci-plan passed; ten CI packs were running and two queued. The inactive merge-queue-pilot authority context reported `inactive_base_context`. No all-CI-green or release claim follows from local proof.

**Classification: PROVEN_OUTCOME for the bounded source implementation and byte-verified durable evidence.** Final programme acceptance and release remain separate.
