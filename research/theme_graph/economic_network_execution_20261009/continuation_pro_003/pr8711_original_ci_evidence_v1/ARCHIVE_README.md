# PR8711 original-candidate failed/pending evidence archive

**Frozen original candidate; failed contract gate; incomplete overall CI proof.**

Observation bound: 2026-10-09 12:14:53.330798 UTC. Candidate: `9df735bbeaa8d0f4d4967296270bfb2246a5212f`. Run: `37925499382`, attempt `1`.

This archive preserves all **13/13 actually available artifacts**, comprising the plan, changed paths and packs 1–11, with original ZIPs and exact JSON members. Complete-run expectation was **15** artifacts; pack 0 and final semantic aggregate were missing. The available fragments contain **97/98 selected jobs and 300/316 planned proof steps**. All 300 observed steps passed. The missing 16 belong to `ci-control-plane-contracts`. The owner command actually logged **275 passed in 8.73s**. Contract-delta actually failed with **2 introduced, 0 inherited** findings. The workflow itself was still in progress with null conclusion.

## Transfer files

| File | Bytes | SHA-256 |
|---|---:|---|
| `PR8711_ORIGINAL_CANDIDATE_FAILED_PENDING_EVIDENCE.tar.gz` | 1858043 | `e8f6e688d6805daea04a827dd02ffe1eb6add5d57a7385ee02fac0fa99209db8` |
| `ARCHIVE_MANIFEST.json` | 16593 | `0fc883c4ecc4338c3f6132129f21e6dd88631267218ccb13cae93d01a4f39c86` |
| `ARCHIVE_VERIFICATION.json` | 2151 | `04355823aeb3e5146d97572cac7e55a477a2c032fc69a4a81b6327712da1dc60` |

Keep this README with those three files. The archive contains **57 regular files**, totaling **5,216,732 uncompressed file bytes**, under `pr8711_ci_release_evidence_v1/`. The external manifest explicitly enumerates every archive name, length and SHA-256. Archive metadata, gzip time/name and entry order are normalized. There are no links, duplicate names or traversal entries. Credentials, signed download URLs, raw log bodies, caches and unrelated work are excluded. The retained whole-log hashes were computed during actual in-memory GETs; only bounded sanitized excerpts remain.

Entry points inside the archive: `OBSERVATION_REPORT.md`, `FOCUSED_OBSERVATION.json`, `AVAILABLE_ARTIFACT_VERIFICATION.json`, `ARTIFACT_INVENTORY.json`, and `ARCHIVE_REPRESENTATION_ASSESSMENT.md`. `PACKAGING_NOTES.md` documents explicit context-copy paths and preparation adjustments. `native_read_scripts.json` contains exact GET scripts and all six reconciled native PIDs.

Extraction was checked against every manifest entry. The unchanged preserved-data verifier then ran successfully from that extracted layout, with a fresh output filename. All 2,672 assertions passed, and its result equals the original apart from `created_at_utc`. The extra replay output is separately accounted for in `ARCHIVE_VERIFICATION.json`; it was not added to or used to change this frozen archive. Every original and extracted preserved file remained byte-identical after replay.

With Python 3 and PyYAML, a reviewer can run from the extracted evidence directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python -B verify_available_artifacts.py --snapshot native_snapshot_003.json --output FRESH_REPLAY.json
```

Use a new output name. This reads preserved observations without repository imports, application tests, Git, native operations or network. It cannot turn the missing pack/final aggregate into a pass and does not certify any repaired candidate. Root owns the subsequent material correction, new-head CI and release adjudication.
