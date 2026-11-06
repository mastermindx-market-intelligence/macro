# D03 W07 canonical Winner Health availability capture

The changed source is `templates/winner_health.html.j2`; `EVIDENCE.yml` binds it
to this directory's unmodified canonical capture manifest. This is a synthetic
source-state fixture, not deployment, user acceptance or a live market read.

## Exact source binding

The real normal builder generated the stale page at frozen day 2026-11-04 from
source `asof=2026-10-28`. It did not use the historical fixture bypass. The served
page was copied byte-for-byte from the final 144-case behavior proof:

- Lossless `stale.html.gz`, decompressed HTML SHA-256:
  `05f9f82d7d9df7043903b14a65e03fe56c1d00f07fe34952983ff2f27f3603a8`.
- Builder SHA-256:
  `c6f12a4371f691da904a6cbd7ee05bc867a544c975c70301ed8f91521097b7ab`.
- Template SHA-256:
  `4048a4ec1b08a935a11e1b31d8ff213cacb822a87225ff3d9ddf5915ea7856bf`.
- Full 32-file source/asset binding and browser runner live under
  `research/design_candidates/production_design_20261102/evidence/d03-winner-health-w07-20261104/`.

The temporary served site is not a Git checkout. The manifest therefore does
not invent Git metadata; the explicit source/HTML hash linkage above is the
receipt. The canonical tool is unmodified **v1.4.0**, SHA-256
`9b6e643c1c784eb81b584be4cb063092ae71c4a16fe01498130891e84cd0de42`.

The generated HTML retains inherited Jinja whitespace. It is stored as a
deterministic lossless gzip, not trimmed after capture: decompressing it yields
the exact bytes hashed by the actual-builder proof. The raw generated copy
tripped `git diff --check` before compression; no product or captured byte was
altered to suppress that check. The active temporary served fixture is unchanged.

## Captured and checked

**16/16 captures**: desktop 1440×900 and mobile 390×844 × light/dark × EN/ZH ×
rest/native Terminal-header focus. Eight rest cells form the complete canonical
matrix; eight extra captures show real focus rather than a painted simulation.
No console errors or failed responses were recorded.

Self-QA checked hierarchy, neutral unavailable state, readable bilingual copy,
validated source date, narrow wrapping and visible keyboard focus. The desktop
Light EN rest and mobile Dark ZH focus images were inspected directly. The
separate 144-case behavior proof includes the 320px layout and all source states.

The repository's actual `check_ui_visual_evidence.py` gate passed for the
template delta. All measured metadata remains in `manifest.json` / `smells.json`;
retained-shell layout shift is not reclassified as a passing whole-page
performance benchmark. Shared shell, nav, auth and live routing were not changed.

**Draft evidence only. No merge, deployment or production acceptance.**
