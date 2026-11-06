# Evidence CI failure and archive packaging repair — 18 October 2026

The root owner introduced a publication defect by retaining another repository's source and test snapshots under executable Python filenames in Macro. The correct repair makes their documentary role explicit and preserves the source bytes. It does not change CI rules, add test waivers, suppress import checks or modify the owning Mastermind implementation/tests.

## Exact failed observation

- Evidence PR: https://github.com/mastermindx-market-intelligence/macro/pull/9595
- Head: `f11fa0c66273ca1976f37e2f529fe9ff689ee439`.
- Run: https://github.com/mastermindx-market-intelligence/macro/actions/runs/39113159863 ; attempt 1, completed failure at 09:16:31Z.
- `contract-delta`: six introduced unregistered pytest suites, one `test_deploy_provenance.py` copy in each of `candidate`, `native_run2_candidate`, `pre_native_candidate`, `red_baseline`, `review_red_baseline` and `source`.
- `ci-pack-4 / nyse-calendar-freshness`: the repo-wide first-party import sweep reported 27 import/name findings from retained foreign `source/app` and test copies. That combined suite reported 173 passed / 1 failed. This is not a fresh calendar failure.
- `ci-pack-1 / reference-integrity`: three missing RIG receipt findings in `research/migration_packets/MP-20261018-sector-central-capability-crosswalk.md`, `MP-20261018-sector-central-paper-and-acceptance.md` and `MP-20261018-sector-central.md`. The hosted log reproduced the same three on its CI candidate and base `dfdd93a75da34417deb1ad328c79f0bc795cf458`. None is a changed file in this PR. This is a bounded base-reproduction observation, not a waiver or acceptance of that gate.
- `ci-gate`: failed semantic and contract-delta enforcement. Ten of twelve packs passed. The separate nonbinding merge-queue pilot status does not explain away these real failures.
- Raw failed log retained locally only: 241,956 bytes, SHA256 `4f6c4912033dd26f77b55ef033dcd34356ef502ac49aa8378c019311a8a6477c`. The relevant emitted findings were read by the root owner. No raw operational log is published here.
- At 09:21:38.439890Z, the unchanged-head PR was verified OPEN/draft, without `merge-on-green` or auto-merge, and with no merge commit. No blind rerun occurred.

## Concrete repair and custody

[ARCHIVE_PATH_MAP_2026-10-18.json](ARCHIVE_PATH_MAP_2026-10-18.json) binds the 25 original archive paths to paths with `.txt` appended, recording bytes, SHA256 and the original Git blob. Every archived Python/shell byte is unchanged. This includes unsuccessful baselines, earlier test stages, the accepted narrow helper candidate and its foreign dependency evidence. These files remain readable and recoverable; restoring or executing them requires its own exact-source admission in the appropriate owning environment.

The index updates three direct archive hyperlinks and explains how prior manifests/reviews resolve historical logical names. Earlier manifests and review reports remain unchanged. The 56-file transfer receipt describes its original transfer; the separate four-space presentation correction is still recoverable from its original-text JSON. This new path mapping does not turn the older receipt into a claim about final path names.

No implementation path outside the evidence packet changes. The Mastermind repair PR remains its separate carrier. The complete deployment, source acceptance, model estimation, publication of trading guidance and programme acceptance are not established by this packaging correction.

## Verification state

The packaging operation verified all 25 preimages against Git head `f11fa0c66273ca1976f37e2f529fe9ff689ee439` and all 25 renamed contents against those hashes. Root will record the affected import and suite-discovery checks, normal required CI and exact-file landing separately. Until those gates conclude, this repair is a worktree candidate and the PR remains draft/disarmed.
