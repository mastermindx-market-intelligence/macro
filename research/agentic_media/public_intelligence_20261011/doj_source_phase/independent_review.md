**PASS** for the bounded DOJ source-route review of the current uncommitted worktree diff against `35e06edabd3236ddf295cfe5a95e7be40b0b09fb`. The checked-out Git `HEAD` remains that base; the review target is the dirty, isolated follow-on workspace state.

Reviewed application-byte hashes:

| Path | SHA-256 |
|---|---|
| `engine/press/official_feed_candidate.py` | `af349f5784bdd0c6484617803e0e221d8fd1d865ceedbe8c9334867b5dcc9e1e` |
| `scripts/stage_official_feed_press.py` | `8c3b19d7186e15efc3eb6205ffed24b322b5ae1215801bf394f3a1c98425990a` |
| `tests/test_press_official_feed_candidate.py` | `b3747edcb794fd2d4fd79cd8a9abbd87682e5bf4f90109be4ddb179c41a22763` |
| `tests/test_press_official_staging.py` | `323019e6048030fc66e8c809e5bdef04e5458dd8ee5c4c00aa93d8da6ba7a0fa` |

Verified retained source evidence hashes:

| Retained DOJ input | SHA-256 |
|---|---|
| `rss.xml` | `7e3c848cf4b38d9dcde99a8d7ecba4413bb937df06c4cc453e80a3625cd2c6a7` |
| `release.html` | `ad08e9652445dfb628b5b220d21878477eb10efb8605aa04ab0ad326347f3847` |
| `policy.html` | `dd99df630bfd52d5ba46a8e258198ed20d32518eb042d5163d15c37127982770` |
| `cvs_candidate.json` | `86643a8d2173552713afa2f9c7b2f3e6a8cafb8671a1142cd76ccfdba30f0549` |
| `retrieval.json` | `cb0c789a08282f59e419e0cd44651c11272a989c1e443253ca1d6725e9d86084` |

The new [official-feed candidate planner](/Volumes/Mastermind%202/agent-workspaces/claude/14851c4656838a3b/mmx-press-validator-followon-20261014-c1dc27962b7d07c4/engine/press/official_feed_candidate.py:49) correctly constrains the DOJ route:

- It accepts only the specific DOJ RSS origin, HTTPS host, and canonical `/opa/pr/<slug>` release path.
- It binds the selected feed item URL to exactly one RSS item, matches the RSS publisher time to the qualification and to the retained release’s `<time datetime>`, and enforces the retained release’s own canonical URL.
- It hash-binds both release and reuse-policy bytes and requires the policy document’s canonical identity and the specific public-domain / third-party-material qualifications before accepting the source.
- It requires a literal source qualifier from the retained release. Where the release contains the relevant disposition, it specifically requires a qualifier that states both “allegations only” and “no determination of liability.”
- The plan adds that qualifier both as a third-party fact and in the retained full raw document. My local fixture-based prompt probe confirmed that the exact qualifier reaches the writer’s untrusted evidence fence. It does not enter the trusted system prompt as a mutable instruction.

The real CVS evidence preserves the material limitation:

> “The claims resolved by the settlement are allegations only and there has been no determination of liability.”

This is included in the plan’s facts and raw document, while the route’s reviewed monetary claim remains limited to the qualified `$315 million` allegation-resolution statement.

The source remains planning-only. The returned plan has `allow_stage=False`, `allow_emit=False`, and `publication_approved=False`. It carries only third-party facts. When forwarded through [stage_official_feed_candidate](/Volumes/Mastermind%202/agent-workspaces/claude/14851c4656838a3b/mmx-press-validator-followon-20261014-c1dc27962b7d07c4/scripts/stage_official_feed_press.py:214), the existing first-party context check refuses it before a checkpoint or writer/provider invocation. This preserves the prior acceptance boundary rather than converting a real public release into a spendable generation request.

I exercised the focused DOJ/refusal safety tests and an independent local fixture probe. The probe confirmed:

```text
plan is private, all-third-party; literal allegation qualifier reaches writer evidence fence
```

The focused test selection completed successfully, including DOJ retained-document rejection paths, third-party-only preflight refusal, and existing official private-emit guard paths. I also ran the file-path import-pin test; it passed, so the staging entrypoint remains resistant to an earlier ambient `engine`/`scripts` package path.

I found no concrete rights/provenance, canonical identity, clock-binding, replay, or publication-safety regression in the reviewed path. `git diff --check` is clean.

Limits remain material:

- The qualification artifact is caller-supplied and hash-bound for the invocation; this is a retained-evidence contract, not an independently signed authorization system.
- The allegation qualifier is preserved in prompt-visible source facts, but this bounded review does not establish semantic-completeness enforcement of every generated sentence. The present candidate cannot reach a writer because it has no qualifying first-party context, and any future official private staging remains blocked from emission by the existing `official_feed:`/private-rail guard.
- This review does not constitute generation, staging, publication, CI, protected merge, deployment, or authenticated live proof.

No source edits, provider calls, CI/GitHub calls, staging/publication actions, cleanup, PR actions, or worker creation were performed.
