# R14 — Native Paper usability refinement

**Status: design evidence only. Mission incomplete. Production unchanged.**

R14 refines the existing editable Paper file **Mastermind · Market Guide · Re-envisioning** (`01M32XYWDYSFTNDZVJKQ5QHT33`) after comparing the R13 candidate with the live production routes. The original twenty artboards remain untouched. Six duplicate R14 artboards were created so the baseline stays available for comparison.

## Why this pass exists

The live route still presents a taxonomy-first **Market Reference** and the live Macro dashboard still relegates six explanations to a small **LOOK UP** footer row. R13 made the standalone candidate dramatically clearer, but its native Paper boards still carried older copy and its quick-help concept did not foreground the live reading strongly enough.

R14 tightens the job to three seconds:

1. **Know what this page is.** `Market Guide / 市场指南` is now the explicit product identity, with the promise “Ask what a score or signal means. Get the answer in seconds.”
2. **Start from a user question.** The three entry cards remain visually light, but now disclose the answer they lead to: Market State Score, Risk Radar, or Regime Quadrant. Mobile keeps the arrow plus a small destination label.
3. **See the current read before the definition.** The Risk Radar quick explanation now starts with a visually distinct current-reading block (`Risk 56 · Watch` / `风险 56 · 观察`, dated Sep 23 as a design example), then shows how to read it and the essential limitation.
4. **Keep state and copy coherent.** The Watch example visually selects `Calm / watch` rather than Caution. The explanation calls it an early heads-up and keeps the “not a timing/exit signal” limitation immediately visible.
5. **Preserve progressive depth.** The user can still open the full guide, but no long methodology block is forced into quick help.

The current-reading value is **illustrative design data only**. R14 does not claim that 56/Watch is the live Risk Radar reading and does not alter any engine threshold, score, alert, gate or policy.

## R14 native artboards

- `1RQ-1` — R14 · Guide · Light · EN · Desktop
- `1UC-1` — R14 · Guide · Dark · EN · Desktop
- `1WO-1` — R14 · Guide · Light · EN · Mobile
- `1Z0-1` — R14 · Guide · Light · ZH · Mobile
- `21C-1` — R14 · Risk Help · Light · EN
- `224-1` — R14 · Risk Help · Dark · ZH

The exact native screenshot and JSX hashes are in `r14-paper/manifest.json`. Paper working indicators were released after the edits.

## Material-source reconciliation

Protected procedure for this wave: `Mastermind/master@622d128d64a79c3e4dd45f748b8a8db7ec2e2741`, Skillpack 1.0.1 / bootstrap 1.

Paper was re-entered only after a material platform recovery signal: protected Mastermind had merged the Paper bridge requalification (#951). The existing file reopened successfully and exposed the full read/write Paper tool surface; this was not a blind retry of the earlier refusal.

Current Macro main at capture close: `ad38f308945cdcd36a01111e88009ab895f9367c`. A current-base merge-tree of `origin/main` with PR #7647 head `b5a250eb20b98712637e02565d4c8f08e96f108c` produced tree `71cd1ba6dff2b583a172ad6ea2c1fd72b316a896` with no conflict output.

New main movement includes merged #7935, which adds **neutral issued-warning duration context** to Risk Radar after five consecutive caution/elevated/risk-off issued sessions. Calm/watch renders no duration. Therefore the R14 Watch example remains compatible. A future contextual consumer may show duration only when the canonical producer supplies it; the guide must never synthesize persistence.

PR #7859 has merged, clearing the former same-file dashboard dependency. PR #6792 remains an old OPEN/DRAFT/HOLD reference implementation with unresolved independent REQUEST_CHANGES and no movement since 2026-09-04; R14 does not overwrite its source paths or accept its evidence contract.

## Proof boundary

R14 is **visual/native-design evidence**, not a new source implementation. The previously published R13 exact-head source still owns the working guide behavior and has terminal hosted `fences` + `ci` success on head `b5a250eb20b98712637e02565d4c8f08e96f108c` (runs `35957027216` and `35957027329`).

Independent design/reference acceptance is still absent. Actual Macro Lens integration, the stale caller-state repair, source migration, merge, deployment and live before/after proof remain required.

## Production design ruling preserved

Do not restyle the bottom LOOK UP row as the destination. Move explanations beside the real dashboard instrument using the existing Lens interaction, keep normal `reference.html#<id>` fallback links, and remove the row only after all six explanations have verified in-context replacements.
