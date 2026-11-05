# US Prophet Committed-Panel Reader Repair

**Goal:** Keep every read-only US rendering/analytics consumer on the committed S&P 1500 price panels instead of silently replacing those panels with a prior GitHub Actions cache.

**Architecture:** Complete daily.engine’s existing Git-authoritative input policy by removing redundant read-only cache steps for the three tracked panels. Exact-key-only restore still allows a same-run retry to overlay an earlier attempt’s cache; the Git checkout already contains the authoritative panel. Only daily.collect may use prefix fallback for these tracked panels, because it then refreshes and commits them. Preserve the gitignored Russell cache, its exact same-run daily handoff, and all existing lifecycle, provenance, scoring and publication authorities.

**Spec:** Current Chairman-directed US Prophet recovery; `.github/workflows/daily.yml` tracked-panel authority comment; `tests/test_daily_collect_commit_path.py` existing overwrite-regression contract.

**Scope:** `.github/workflows/{daily,closing-bell,earlyclose,engine-render,render,weekly,special-sits-backfill}.yml`; extend the already-registered `tests/test_daily_collect_commit_path.py`; date the candidate projection in `templates/dashboard.html.j2` and its existing `tests/test_p0_prophet_candidate_board.py` owner. No new dataset, collector, ranker, calendar, schedule, worker, permission, provider request or gate waiver.

1. Add a regression to the existing commit-path suite that parses actual workflow cache steps, handles both `actions/cache@` and `actions/cache/restore@`, and rejects any cache restore of the three tracked US panels in every non-collector job. Observe real stale reader routes fail.
2. Preserve a positive control that daily.collect still has exactly its three original seed prefixes and that all three files remain Git-tracked. Keep the existing Russell exact-run/untracked control unchanged.
3. Remove only the redundant read-only cache steps for the three tracked panels. Keep every remaining step, condition, credential, collector, schedule and unrelated cache path unchanged.
4. Run the complete existing checkpoint/restore suite, workflow-size/schema contracts, and a mutation control that reintroduces one stale reader key and must fail. Run contract-delta and current-base review before publication.
5. Preserve the finding in the existing Agent OS availability program and submit one bounded PR. All hosted checks, release review, merge, real input-to-alpha-to-board publication and browser proof remain required. Do not cancel or duplicate daily run 35041133038; never bypass the offline ci-linux runner gate.

**Production acceptance:** the served candidate generation derives from the committed, completed-session panel; its actual date/counts/source hashes reconcile to the producer and served board. A current shell date alone is not acceptance. A truly stale committed input remains stale and must never be restamped.

## Consumer truth within the same freshness capability

The candidate heading unconditionally says “screened tonight” even when the artifact is days old. Replace that time-relative promise with its actual `us_standouts.as_of`, with an explicit unavailable date on absent/null/empty source dates. Remove the same relative claim from the adjacent bilingual note and entitlement copy. Preserve candidate/plan separation, count arithmetic, ranking and permissions. Extend the existing registered candidate-board contract suite and prove a stale/undated source cannot borrow freshness from a new shell. A candidate browser capture is not served production proof.
