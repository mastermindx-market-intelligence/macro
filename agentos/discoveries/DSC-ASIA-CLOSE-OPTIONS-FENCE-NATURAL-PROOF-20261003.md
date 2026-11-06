---
key: ASIA-CLOSE-OPTIONS-FENCE-NATURAL-PROOF-20261003
claim: >-
  After #8320 merged as 380cf203e3aa8886385c825c1237a30d8886f4bc, the next
  scheduled asia-close run 37118772460 completed successfully from pre-run head
  ee78db7c6d83c5544392f12de6cc4cc9e8b5efe8. Its observed Asia collection and
  dashboard commits, 1bd90df664d77ceb106c92d8e832e1d598cee88b and
  17e04b792d5aebb996f30f647c8bc4f73172a2ca, changed neither
  data/options_signal_episode nor data/options_signal_campaign nor
  options_alpha paths. This is one natural nonsweep observation of the #8320
  asia-close broad-staging fence, not a publication, durability, or activation proof.
falsifier: >-
  Re-read run 37118772460 and the complete changed-file lists for the two named
  commits through the GitHub API. This discovery is false if the scheduled run
  did not succeed from ee78db7c6d83c5544392f12de6cc4cc9e8b5efe8, either commit
  includes a protected Options path, or the merged #8320 workflow lacks the
  existing exclude-broad calls bracketing each asia-close broad git-add. A later
  scheduled asia-close observation that sweeps either protected root disproves
  the fence's observed runtime behavior and requires a new incident record.
so_what: >-
  Treat this one natural run as evidence that the #8320 broad-staging fence was
  exercised; do not rerun a synthetic sweep or weaken the narrow-root guard.
  It does not satisfy #7193 eligible-owner attestation, #7263/#7265 durability
  acceptance, candidate activation, receipt minting, or any scoring or trading
  authority gate. Future acceptance reads retain those independent prerequisites.
kind: runtime
verified_at: 2026-10-03
verified_by: >-
  GitHub API reads of #8320: commits/380cf203e3aa8886385c825c1237a30d8886f4bc;
  actions/runs/37118772460 and jobs (scheduled 2026-10-03T11:09:49Z,
  conclusion success; asia job mac-builder-light/macstudio); and
  commits/1bd90df664d77ceb106c92d8e832e1d598cee88b plus
  commits/17e04b792d5aebb996f30f647c8bc4f73172a2ca changed-file lists.
scope:
  - macro
  - "WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY"
  - ".github/workflows/asia-close.yml"
  - scripts/ci/options_signal_nightly.sh
  - data/options_signal_episode
  - data/options_signal_campaign
confidence: verified
---

# Asia close naturally exercised the Options broad-staging fence

#8320 places the existing `exclude-broad` helper immediately before and after
both Asia broad staging sites. The first observed scheduled run after that
merge was therefore a bounded runtime check of the existing protection: its
collection and dashboard commits were broad Asia outputs, yet neither touched
either protected Options root or an Options Alpha path.

The evidence is deliberately narrow. The run started from the stated pre-run
head and the two observed output commits are descendants of that head; it does
not establish the state of unrelated publishers, a durable Options publication,
or the still-separate #7193 eligible-owner attestation.
