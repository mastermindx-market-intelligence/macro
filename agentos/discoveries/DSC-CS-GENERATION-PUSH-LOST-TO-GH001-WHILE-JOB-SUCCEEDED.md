---
key: CS-GENERATION-PUSH-LOST-TO-GH001-WHILE-JOB-SUCCEEDED
claim: >
  From 2026-09-27 to 2026-10-08 the daily.yml capital_structure job concluded
  success on eight nights while no Capital Structure generation commit landed on
  origin/main, because the push of data/capital_structure/source_manifest.jsonl
  was rejected by GitHub's 100 MB file limit (GH001); on 2026-10-09 (run
  37874656026, job 113680083720) the same rejection surfaced as an explicit push
  failure at 101.47 MB after every compile step had passed.
falsifier: >
  git log origin/main --since=2026-09-27 -- data/capital_structure/health.json
  showing a generation commit between 24ab0b613f89 (2026-09-26) and the first
  nightly that runs with sharded parts, or the job 113680083720 log not
  containing 'GH001'. Commands:
  git log --format='%h %ad %s' --date=short origin/main -- data/capital_structure/health.json;
  gh run view --job 113680083720 --log | grep GH001.
so_what: >
  Never read a capital_structure job conclusion as a publication receipt. Proof
  of a landed generation is a commit on origin/main that changes
  data/capital_structure/health.json (generated_at advances) — check that
  first when the product looks stale. The R2 repair is byte-exact part sharding
  (DEC:CS-V2-SOURCE-LEDGER-SHARDS-BYTE-EXACTLY); after it merges, the first
  natural nightly must show a new generation commit carrying
  source_manifest.part-0002.jsonl. Do not dispatch daily.yml to prove it.
kind: landmine
verified_at: 2026-10-13
verified_by: >
  R1 census 2026-10-13 (seat a9559a4c): gh run list --workflow daily.yml over
  2026-09-24..10-13 cross-checked against git log origin/main --
  data/capital_structure/; run 37874656026 job 113680083720 push step log
  'GH001: File data/capital_structure/source_manifest.jsonl is 101.47 MB;
  exceeds GitHub's file size limit of 100.00 MB'. Last landed generation
  24ab0b613f89 with health.json degraded_discovery, filing horizon 2026-09-17.
scope:
  - macro
  - capital-structure-intelligence
  - data/capital_structure/
  - .github/workflows/daily.yml
confidence: verified
---

The job's own steps succeeded; only the remote rejected the result, and on the
earlier nights the retry wrapper's outcome did not fail the job. A stale
product with a green nightly is therefore not evidence that the compilers are
healthy — it is the signature of a lost push. Since 2026-10-10 the collect job
has additionally been cancelled mid-run by the runner-listener outage (a
runner-broker Chairman blocker), so the capital_structure job has been skipped
entirely; that is a separate, operator-owned condition.
