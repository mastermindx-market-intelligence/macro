# Principal design review — provisional

The current source and user-supplied screenshots were the baseline. The original problem is a mismatch between a user's immediate question and the page's internal taxonomy, not simply a lack of border radius or more color.

The first native desktop screenshot was captured before Paper had finished painting and showed incomplete cards. A settled recapture confirmed the native nodes were present. Subsequent checkpoints allowed the renderer to settle; frozen captures were read back after composition.

The first six arbitrary bars were rejected: they could imply quantitative component values that the reference registry does not supply. They were replaced in the native design and prototype with six named ingredients. The score's one-line description was tightened to explicitly say US stocks / 美股. A duplicate boxed navigation section was removed from quick help so it remains an explanation rather than a second page.

Light desktop, dark desktop, mobile English, the score detail and contextual explanation were visually inspected. The final browser home and native dark Chinese mobile detail were also inspected. Spacing is grouped by task; primary copy uses the body/heading scale rather than the old tiny accordion typography; the main answer and essential limitation remain visible without expanding methodology. Native Chinese mobile content wraps without clipping, and the browser matrix reports no page-level horizontal overflow.

This is a principal's candidate critique, **not independent visual acceptance**. Remaining review items: finalize instrument-specific visuals beyond the score exemplar; make the native and interactive example labels exactly uniform in the approved spec; decide how question groups route to the most useful answer versus a short candidate list; test understanding with end users; and verify the contextual component in the actual Macro page alongside shared help. The prototype toolbar and representative Paper header must not be migrated as a new global navigation family.

No user research, measured improvement in task completion, production performance win, screen-reader certification or production release is claimed.
