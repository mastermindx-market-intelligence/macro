# PR8711 corrected-candidate CI evidence archive

**Complete observed CI evidence for candidate `42174563149254d2399e23e101baafd8b06f9b1e`; no merge authorization.**

The frozen observation completed at **2026-10-09T13:22:08.722425+00:00**. Run **37932039980**, attempt **1**, concluded **success**. Actual tested synthetic commit: `04b70807e6b0a7d48091997eb405f9cc53ade9ad`; ordered parents: `40ebaebdbcd57eedaa627623f1cfd1860ff3ee3a` then the exact candidate head. Git tree: `0c5bd664aec83fe9a9d456b2f35e1e870fc0b3e8`.

The archive contains all **15 original artifact ZIPs and 15 exact JSON members**: the plan, changed paths, all **12** raw pack fragments and final semantic aggregate. The independent verifier accounts for **98/98 selected jobs** and **316/316 proof steps**, all passed. It recomputes the 98 job execution and 316 step specification source digests and reconstructs the exact complete all-pass aggregate. That aggregate’s logical SHA-256 is `33eefd16f3c4b548f18e3a442c66415c684089bce99f3ec464bc05a91464dc73`. The final gate’s complete JSON stdout and summary also match it exactly.

Actual new owner result: **275 passed in 9.25s**. Actual new contract gate: **0 introduced, 0 inherited**, using the actual tested base. Whole raw owner, contract-delta and final gate logs are preserved unchanged, with lengths, hashes and line references. The separate source verifier proves **53/53 accepted engine/lib byte pins**, **1,483,905 bytes**, from three complete tree responses and 52 unique blob responses at the actual tested tree. This is byte compatibility, not a new functional code review.

## Transfer files

| File | Bytes | SHA-256 |
|---|---:|---|
| `PR8711_CORRECTED_CANDIDATE_CI_EVIDENCE.tar.gz` | 3809105 | `9723b71acf3d44f6918ddb8c1d319e49bcc760c048106ec3277d09c94a7a7805` |
| `ARCHIVE_MANIFEST.json` | 27011 | `48561925c0d7d08cd829db8407380ee83f5fb5060447970c5bedcd3a1331143b` |
| `ARCHIVE_VERIFICATION.json` | 4276 | `d47db7b19161660cda56688d225549b97d3241b6e7e5565ca75988b029bdd887` |

Keep this README with those three files. The archive has **90 regular files**, totaling **10,470,166 uncompressed file bytes**, under `pr8711_corrected_ci_release_evidence_v1/`. The external manifest explicitly enumerates every relative name, length and SHA-256. The outer archive has normalized time, ownership, modes and ordering. A second in-memory encoding was byte-identical. The original GitHub ZIPs retain their own exact original bytes and metadata. There are no links, duplicate names, traversal entries, caches, credentials or retained signed artifact redirect URLs.

Entry points: `OBSERVATION_REPORT.md`, `CI_EVIDENCE_VERIFICATION.json`, `FOCUSED_OBSERVATION.json`, `ARTIFACT_INVENTORY.json`, `SOURCE_PIN_VERIFICATION.json`, `READ_TIMELINE.json`, `PACKAGING_NOTES.md`, and `native_read_scripts.json`. Exact read scripts and all **nine** reconciled native PIDs are preserved. Historical partial observations and their exact verifier versions remain unchanged. The original failed/pending candidate packet is already committed separately and is referenced without rewriting it or attributing its results to this candidate.

Every manifest entry was safely extracted and verified. Both unchanged preserved-data verifiers then executed from the extracted layout, each using a fresh output filename. The 53-pin result and the complete CI result both matched their original preserved reports exactly apart from `created_at_utc`. All **2,295 CI assertions** passed again. The two additional replay outputs are separately accounted for in `ARCHIVE_VERIFICATION.json` and do not alter the frozen archive. Original and extracted preserved files remained byte-identical; original input mtimes also remained unchanged.

From the extracted evidence directory, with Python 3 and PyYAML:

```sh
PYTHONDONTWRITEBYTECODE=1 python -B verify_tested_code_pins.py --output FRESH_SOURCE_PIN_VERIFICATION.json
PYTHONDONTWRITEBYTECODE=1 python -B verify_corrected_artifacts.py --snapshot artifact_read_005_and_snapshot_006.json --output FRESH_CI_EVIDENCE_VERIFICATION.json
```

Use new output names. These commands read preserved evidence; they do not contact GitHub, operate on a native device, mutate Git, import repository applications or run application tests.

The exact-head check census retains `ci-authority/codex/merge-queue-pilot` as failure and `ci-authority/main` as success. This packet neither waives nor rules on the policy binding of those checks. Root owns current protected procedure, live freshness/holds, accepted-source verification, merge and the native C01 witness. There is no rights, custody, historical, factual, Graph1, production or predictive promotion.
