# Outlook section for `transmission.html` — mockup v1

**Status: waiting for operator ratification.** The state, path and science contract
(`research/macro_regime_intelligence/STATE_PATH_AND_SCIENCE_CONTRACT_2026-10-03.md`, §6) says the
section's exact markup and styles are pinned in a committed mockup and ratified by the operator
before the section itself merges. Ratification gates the page slice (E2) only.

Open `transmission_outlook_section_v1.html` in a browser. The dark bar at the top switches theme,
language and state; it is not part of the page. The same switches work as URL parameters:
`?theme=dark&lang=zh&state=previous&chrome=0`.

## What the section is

One section, six parts, in the contract's order: **Now → What changed → Paths → History →
Exposures → Watch**. It renders only from the outlook projection. It has no script of its own.

Each path card is a two-sided ledger. Evidence that fits the path today sits on the left, evidence
that does not fit sits on the right at the same weight, and evidence that points both ways sits on
the line between them. What is not known yet is listed underneath as what we are watching.

## Rules the design holds

- Paths are in the contract's fixed order and are never ranked, sorted or totalled across cards.
- No green or red. Readings are told apart by the shape of their mark, because "fits" is not "good".
- Every evidence row can be traced to its source and its date from the card, by keyboard and touch.
- A date is only called the date of a reading when the owner publishes one; otherwise it is labelled
  as the snapshot that carried the value.
- What has no published read says so. Nothing is filled in.
- No stock, theme or position size is named under Exposures until that link has been measured.

## Two art directions

**Light — research workspace.** White cards on the page's cool grey canvas, hairline borders, a soft
shadow for depth. The ledger sits on white with a hairline centre line. Marks are ink, told apart by
fill and stroke.

**Dark — command centre.** No shadows; depth comes from luminance. The card carries a faint top
light, the ledger is a recessed well darker than the card, the centre line fades at both ends, and
filled marks carry a faint halo so they hold against the dark ground.

**What differs on purpose:** how depth is made (shadow vs luminance), the ledger ground (white vs
recessed), the centre line (hairline vs fading), mark emphasis (stroke vs halo), the colour of the
"running behind" stamps.

**What is shared:** structure, order, wording, spacing and type scale, mark shapes and their
meanings, every state.

**Baseline:** the transmission page's own palette, section heading, chip and help-tip idioms
(`scripts/build_transmission.py`, `templates/transmission.html.j2`). The section adds no colour of
its own; new classes are under `.mx-ol-*`.

## States

| State | What shows |
|---|---|
| Current read | the full section, stamped with when the read was prepared |
| First read | "What changed" says there is nothing to compare with yet |
| Previous read | a banner with that read's own date and "a newer read is being prepared"; dashed borders, no shadow |
| Being updated | only the notice — no stale content underneath |
| Inputs running behind | listed under Watch with their own last-updated dates |

## Evidence (in `mockups/refs/regime_outlook/`)

Light and dark × English and Chinese × 1440 and 390 wide: `light_en_1440`, `light_en_390`,
`light_zh_1440`, `light_zh_390`, `dark_en_1440`, `dark_en_390`, `dark_zh_1440`, `dark_zh_390`.
States: `state_previous_light_en_1440`, `state_updating_light_en_1440`, `state_first_light_en_1440`.
Evidence panel open: `evidence_open_light_en`. No horizontal scroll at either width in any of the
eight.

## Real and sample content

- **Real:** every reading in "Now" and on the nine cards is the 2 October 2026 read of the frozen
  table (`config/regime_outlook_mapping_v2.json` — version 1 when the mockup was read; version 2 keeps every reading, contract Appendix A).
- **Sample:** the "What changed" chips, the release dates under Watch, and the previous read's date.

## Cut on purpose

A row of summary marks in each card's corner. It made the nine cards easy to compare at a glance,
which is the one thing this section must not invite.

## For the operator to decide

1. Position on the page: proposed after "How a shock travels", before "If this holds for three months".
2. The title "Where this could go" / 「接下来可能怎么走」.
3. Whether "What changed" lives in this section or only in the page's existing strip.
