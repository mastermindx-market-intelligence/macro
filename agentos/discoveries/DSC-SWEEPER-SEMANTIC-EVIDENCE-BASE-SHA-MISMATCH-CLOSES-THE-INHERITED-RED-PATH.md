---
key: SWEEPER-SEMANTIC-EVIDENCE-BASE-SHA-MISMATCH-CLOSES-THE-INHERITED-RED-PATH
claim: "When an armed PR's ci-authority semantic evidence was produced against a base main has since left, the sweeper refuses to downgrade to legacy name-matched reasoning ('semantic evidence base_sha mismatch; marker already present', sweep 37054443462 on #8287) and so does NOT merge it on an inherited red."
falsifier: "A later merge-on-green.yml sweep (`gh run view <id> --log`) merging such a PR on an inherited red without a fresh ci-authority run; scripts/merge_on_green.py base_sha-mismatch branch removed."
so_what: "On a fast-moving main the sweeper's inherited-red path is closed for any PR older than the last main move; the lawful exits are a re-run against the fresh base or a hand merge on concluded checks with the red attributed by logical job + test + tuple \u2014 never --admin."
kind: runtime
verified_at: 2026-10-02
verified_by: "sweep run 37054443462 log 19:29:45Z on #8287; hand merge 19:43:07Z with --match-head-commit cb6656f0369c after REST pulls/8287 answered mergeable=true"
scope:
  - "macro"
  - "WS:MARKET-OS"
  - "scripts/merge_on_green.py"
  - ".github/workflows/ci-authority.yml"
confidence: verified
---

This is deliberate fail-closed behaviour, not a defect: stale evidence may not excuse a red. It means an armed PR can sit `merge-blocked` forever while main moves every minute; the seat owns the exit.
