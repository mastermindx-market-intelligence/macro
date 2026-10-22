# Superseded build-copy archive

This archive consolidates six historical, post-freeze generated build copies from immutable head `ba4466fc170f2f4f3cdfdb131ca6b51508703934`. It preserves every original byte while reducing the pull request's individually enumerated files below the trusted CI authority controller's 3,000-file ceiling.

The original authority rejection is retained as evidence. The authority controller, its limit, complete inventory requirements, permissions and other gates are unchanged.

## Contents and retrieval

`ARCHIVE_MANIFEST.json` maps all 259 original repository-relative paths to their Git blobs, byte lengths, modes and SHA-256 values. The archive contains those same relative paths, so historical build receipts remain accurate records of where each build ran. Those original files also remain directly accessible at immutable Git commit `ba4466fc170f2f4f3cdfdb131ca6b51508703934`.

The six roots are:

| Original build directory | Files |
|---|---:|
| `research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/proposed_shelltools20261022_repair` | 43 |
| `research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/transport_query_repair_20261022/main_composition_6a4_20261022/proposed_main6a420261022_repair` | 43 |
| `research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/transport_query_repair_20261022/main_composition_90df_20261022/proposed_main90df20261022_repair` | 43 |
| `research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/transport_query_repair_20261022/proposed_shellquery20261022_repair` | 44 |
| `research/reference_integrity/intl-country-intelligence-20261020/proposed_composition20261022_repair` | 43 |
| `research/reference_integrity/intl-country-intelligence-20261020/proposed_main25020261022_repair` | 43 |

Archive SHA-256: `df8e74b13511259675f355ccb05aa86fb0b371ddf98fe656e768cf27cf842c02`.
Compressed bytes: 5,271,275. Original bytes: 28,918,589. Every member is a regular file with mode 0644.

To inspect an older build, verify the archive hash, list its members, and extract into a new empty directory. The archive's repository-relative hierarchy recreates the original paths beneath that directory. Compare extracted files against the manifest before using them as evidence. Do not overwrite a current source workspace.

Example, from this directory:

```sh
shasum -a 256 superseded_build_copies.tar.gz
tar -tzf superseded_build_copies.tar.gz
mkdir /tmp/intl-historical-builds-review
tar -xzf superseded_build_copies.tar.gz -C /tmp/intl-historical-builds-review
```

## Preserved ordinary paths

The consolidation does not move the frozen `proposed_dock4_repair` artifact, canonical RIG documents, baseline or later screenshots, raw observations, logs, failed-run receipts, original input snapshot/archive, fresh `proposed_scenariopop20261022_repair`, or v13 proof. Product source, tests, configuration, workflows and authority-controller code are unchanged.

The owner observed a complete byte/mode round trip after compression. Independent review compared every manifest path, blob and size against immutable GitHub content and reviewed the preparation procedure. The independent reviewer did not claim to have read the compressed archive itself; the direct execution receipt supplies that observation.

This is an evidence-storage correction. It does not establish authority clearance, hosted CI success, protected-main adoption, production acquisition or served acceptance.
