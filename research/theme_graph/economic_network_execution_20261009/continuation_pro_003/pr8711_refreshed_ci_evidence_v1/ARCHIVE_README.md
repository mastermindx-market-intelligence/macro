# PR8711 refreshed-candidate CI evidence archive

**Complete observed CI evidence for candidate `693ee939c8a28920ef9de7bc32a9f47a7ba76b82`; canonical release adjudication remains with the principal.**

The frozen observation completed at **2026-10-09T14:16:52.263323+00:00**. Run **37938576895**, attempt **1**, concluded **success**. Actual tested synthetic commit: `7d5fd7428fa91567db755117657f856e1347c5f9`; ordered parents: `3bb1ee47939d9caa1db10a4e764365d3a2ee5b77` then the exact candidate head. Distinct Git tree: `67c6a12f7b91e45b63614819a732753fa4a7599a`.

The archive contains all **15 original artifact ZIPs and 15 exact JSON members**: the plan, changed paths, all **12** raw pack fragments and final semantic aggregate. The independent verifier accounts for **98/98 selected jobs** and **316/316 proof steps**, all passed. It recomputes the 98 job execution and 316 step specification source digests and reconstructs the complete all-pass aggregate. Its logical SHA-256 is `e9deb074013733053d9552c8ab4f710f44e1cd940e2b30eb1be40fa0c838e913`. The complete final gate JSON stdout, summary and notices match it exactly.

The actual current relationship owner is **pack 6**, with **275 passed in 10.76s**. The actual new contract gate reports **0 introduced, 0 inherited**, against the actual tested base. Whole raw owner, contract-delta and final gate logs are preserved unchanged with lengths, hashes and line references. The separate source proof verifies **53/53 accepted engine/lib byte pins**, **1,483,905 bytes**, from fresh native GET captures of three complete trees and 52 unique blobs at the tested tree. That establishes byte compatibility; functional code review retains its existing owner.

The retained old/new full manifests and plans establish exactly one changed job/step specification and **51 changed job-to-pack assignments**, including the owner moving from pack 11 to pack 6. All selected/excluded inventories and 98 execution-context digests remain unchanged. The complete source comparison and its unchanged replay are included. Prior successful and failed/pending packets remain separate and unchanged; their execution outcomes do not supply current-head proof.

## Transfer files

| File | Bytes | SHA-256 |
|---|---:|---|
| `PR8711_REFRESHED_CANDIDATE_CI_EVIDENCE.tar.gz` | 4171717 | `9c6baa4681447f390cb176ebbe18ae39b6362daee64884799a0fec9bf42b00ce` |
| `ARCHIVE_MANIFEST.json` | 29242 | `6b44652c3390957569f5190e31c9a89e3d49b49206ee35043f93631cde520bc5` |
| `ARCHIVE_VERIFICATION.json` | 5551 | `87f79ddc656aacded38238d1cf0b72ccc609c411f36541309e41a078a0053dd0` |

Keep this README with those three files. The archive has **98 regular files**, totaling **11,768,732 uncompressed file bytes**, under `pr8711_refreshed_ci_release_evidence_v1/`. The external manifest enumerates every relative archive name, length and SHA-256. Outer metadata, ownership, times, modes and entry order are normalized. A second in-memory encoding was byte-identical. Every original GitHub ZIP retains its exact original bytes and internal metadata. There are no links, duplicate names, traversal entries, caches or retained credentials/signed artifact redirect URLs. A bounded common-pattern scan of the three whole logs is retained without modifying them.

Entry points: `OBSERVATION_REPORT.md`, `CI_EVIDENCE_VERIFICATION.json`, `FOCUSED_OBSERVATION.json`, `ARTIFACT_INVENTORY.json`, `SOURCE_PIN_VERIFICATION.json`, `SOURCE_REFRESH_ASSESSMENT.json`, `READ_TIMELINE.json`, `PACKAGING_NOTES.md`, and `native_read_scripts.json`. Exact read scripts and all **7** reconciled native PIDs are preserved. Historical partial observations and the refused initial preparation assertion remain unchanged. The archive helper's own origin, source diff and generation changes are in `ARCHIVE_BUILDER_DERIVATION.json` and `ARCHIVE_BUILDER_REVISION.diff`.

Every manifest entry was safely extracted and verified. All **three unchanged preserved-data verifiers** then executed from the extracted layout with fresh output filenames. The source comparison was byte-identical. The 53-pin and complete CI reports matched their preserved reports exactly apart from `created_at_utc`; all **2,302 CI assertions** passed again. The three additional replay outputs are accounted for separately in `ARCHIVE_VERIFICATION.json` and are not part of the frozen archive. Original and extracted preserved files remained byte-identical; original input mtimes also remained unchanged.

From the extracted evidence directory, with Python 3 and PyYAML:

```sh
PYTHONDONTWRITEBYTECODE=1 python -B assess_source_refresh.py --output FRESH_SOURCE_REFRESH_ASSESSMENT.json
PYTHONDONTWRITEBYTECODE=1 python -B verify_tested_code_pins.py --output FRESH_SOURCE_PIN_VERIFICATION.json
PYTHONDONTWRITEBYTECODE=1 python -B verify_refreshed_artifacts.py --snapshot artifact_read_005_and_snapshot_005.json --output FRESH_CI_EVIDENCE_VERIFICATION.json
```

Use new output names. These commands read preserved evidence without contacting GitHub, operating on native devices, mutating Git, importing repository applications or running application tests. Earlier partial snapshots describe their own available inventories; final replay uses the selected final snapshot and all retained captures.

The exact-head census explicitly retains `ci-authority/codex/merge-queue-pilot` as failure and `ci-authority/main` as success. This packet does not waive a check or rule on its current policy binding. Root retains current protected procedure, live freshness/holds, accepted-source verification, expected-head merge and the native C01 witness. No rights, custody, history, factual, Graph1, production or predictive promotion is made.
