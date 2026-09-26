# R15 — Search answer and recovery states

**Status: native Paper design evidence only. Mission incomplete. Production unchanged.**

R15 completes the interaction story that R14 deliberately left open: what happens *after* a user uses the Market Guide search box.

The old production route responds to uncertainty with a long glossary. The R15 design instead treats search as an answer workflow.

## Exact match

Query example: `Risk Radar`.

Desktop and mobile both replace the home questions/featured explainer with a single primary answer:

- Risk Radar title and one-line pullback-risk meaning;
- its categorical basis (`calm / watch / caution / elevated / risk-off`);
- one dominant **Open explanation** action;
- related explanations demoted to small secondary chips.

This makes the answer the destination instead of making the user scan an index after already naming what they want.

## No match

Query example: `risk 56 today`.

The recovery state does not pretend natural-language/live-value lookup exists when it does not. It says there is no matching explanation yet, tells the user to try the signal name instead of the live value, proposes likely signal names (`Risk Radar`, `Market State Score`), and retains a `Browse all signals` fallback.

That design preserves a useful exit without returning to the old taxonomy dump or fabricating a match.

## Native boards

- `244-1` — R14 · Search Answer · EN · Desktop
- `26W-1` — R14 · Search Answer · EN · Mobile
- `2AP-1` — R14 · No Match Recovery · EN · Mobile

The boards are additional duplicates in the same Paper file; all earlier R14 and original baseline boards remain intact. Exact screenshot/JSX hashes are in `r15-paper/manifest.json`. Paper working indicators were released after editing.

## Implementation boundary

R15 does **not** reinstate the rejected natural-language search experiment. It is a UX contract for exact-match and no-match behavior using the existing search model. The previously refused source write remains EFFECT_NONE and is not retried.

The intended production sequence remains:

1. exact names/aliases resolve cleanly to one answer where unambiguous;
2. ambiguous names expose a real choice rather than silently picking one;
3. zero-match states recover gracefully;
4. broader natural-language questions are admitted only after a separately validated source implementation exists.

No R15 board is production proof and no live market value appears in this packet.
