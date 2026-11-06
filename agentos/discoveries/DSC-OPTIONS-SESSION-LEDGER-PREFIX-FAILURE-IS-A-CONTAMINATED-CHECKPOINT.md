---
key: OPTIONS-SESSION-LEDGER-PREFIX-FAILURE-IS-A-CONTAMINATED-CHECKPOINT
claim: >
  `CampaignContractError: ledger prefix changed: data/options_signal_episode/outcomes_session.jsonl`
  is a contaminated-CHECKPOINT defect, not a source-integrity defect. The canonical episode
  outcome ledgers on origin/main were never rewritten: across all 11 distinct historical
  versions of outcomes_session.jsonl, all 10 of outcomes_h60.jsonl and all 10 of
  episodes.jsonl, every version is an exact byte-prefix of main's current file (zero
  append-only violations). The campaign checkpoint published by the broad-publisher sweep
  55d267539a7a2e (`data: asia collection 2026-09-03`) instead pins source receipts at row
  counts main's ledgers never passed through - session_outcomes 23,771 when main went
  20,364 -> 27,770, and h60_outcomes 6,525 when main went 5,709 -> 7,122 - so no version of
  the verifier could ever match them. Its episodes receipt (8,872) DOES match main, which is
  why the error surfaces on the outcome ledgers alone and reads like source corruption.
falsifier: >
  Re-run the prefix audit over origin/main: for each of
  data/options_signal_episode/{outcomes_session,outcomes_h60,episodes}.jsonl enumerate every
  distinct blob via `git log --full-history` + `git rev-parse <sha>:<path>`, stream each blob
  accumulating sha256 per line, and compare each version's full digest against the current
  file's digest at that same row count. The claim is disproved if ANY historical version is
  not a byte-prefix of the current file, or if row counts 23,771 (session) or 6,525 (h60)
  appear among the counts main actually published, or if
  `data/options_signal_campaign/checkpoint.json` at 0b467285660b already carried the
  23,771/6,525 receipts rather than 20,364/5,709.
so_what: >
  Never respond to this error by reissuing historical receipts, regenerating old hashes,
  rewriting or compacting the session/h60 ledgers, discarding outcomes, or lowering horizons -
  the source bytes are provably pristine and are the thing worth protecting. Equally, do not
  block the bounded 48-MiB session-outcome parts durability carrier on it: the failure
  pre-exists that change, is independent of it, and is reproducible with plain sha256
  arithmetic over committed bytes with no engine code involved. The lawful repair is
  owner-bound quarantine/reconciliation of the campaign checkpoint plus the contaminated
  campaign-outcome suffix (24,578 -> 28,423) written against that foreign generation, by the
  incumbent campaign owner. A broad `data/` publisher that can sweep a narrow owner's
  checkpoint while leaving that owner's own sources behind can mint a receipt describing a
  generation that never existed on main; that exclusion is what #7193/#7263 defend.
kind: landmine
verified_at: 2026-09-29
verified_by: >
  Full-history prefix audit at origin/main 1df73c1ac9289a21e192aeb50088a4f9119aee82 with
  data/ opted into a sparse worktree and all five participating files verified
  byte-identical to their origin/main blobs; campaign checkpoint receipts read at
  0b467285660b (ocp_8c9d7db10cc6984e90e3a7c6: 20,364 / 5,709 / 6,902) and at
  55d267539a7a (ocp_e3255025e9e8d98b72c3e9ec: 23,771 / 6,525 / 8,872); blob identity across
  23fa320434f5, 3d0dda34c720, 55d267539a7a, 38ad6084d519, 685d1143251d, da3c6b907cc1 read
  with `git rev-parse <commit>:<path>` (tree-only, no content fetch).
scope:
  - macro
  - options-intelligence
  - options-alpha
  - "data/options_signal_episode/*"
  - "data/options_signal_campaign/*"
  - "engine/options_signal_campaign.py"
confidence: verified
---

Measured receipts.

`data/options_signal_campaign/checkpoint.json` at main pins these source prefixes:

| source | recorded records | recorded prefix_sha256 | main's actual prefix at that count | row counts main ever published |
|---|---|---|---|---|
| episodes.jsonl | 8,872 | `577173f2…` | `577173f2…` MATCH | …, 6,902, **8,872**, 9,641 |
| outcomes_session.jsonl | 23,771 | `6b95148d…` | `ed8be51f…` MISMATCH | …, 20,364, **27,770**, 27,775, 30,327 |
| outcomes_h60.jsonl | 6,525 | `129b56d4…` | `73eaf4b6…` MISMATCH | …, 5,709, **7,122**, 7,843 |

The recorded session/h60 digests occur at *no* row count of main's files, so this is not an
off-by-N in the count either: those bytes were produced somewhere else.

At the contaminating commit `55d267539a7a` itself, main's episode ledger blobs were still the
2026-09-01 generation (`outcomes_session.jsonl` = `55621d67af4e`, 20,364 rows), while the
checkpoint that commit published already described 23,771 session outcomes and 8,872 episodes -
a generation main did not reach until `685d1143251d` on 2026-09-04. A canonical writer at
2026-09-03 could not have observed it.

Both campaign OUTPUT receipts in that checkpoint (campaigns 8,385 and outcomes 28,423) verify
exactly against main's committed campaign files, so the contaminated generation was published
whole and self-consistent - which is why the defect survives an outputs-only integrity check
and only fails when the outputs are re-derived against their declared sources.
