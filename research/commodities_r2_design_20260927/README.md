# Commodities R2 design packet — 2026-09-27

This directory is a **documentation-only handoff** for the existing Commodities R2 redesign study. It does not change production code, data, model thresholds, alert behavior or release state.

Canonical live/durable owners:
- Cumulative redesign checkpoint: Macro issue **#8049**
- Direct Paper app/runtime acceptance: Mastermind issue **#1011**
- Paper catalog/runtime repair: Mastermind PR **#1012**
- Target Paper file: MASTERMIND PAGES `01M2WGNCX9475G79JRKJTCM08P`
- Target Paper page: `p-L-0`

Files:
- `DIRECT_PAPER_APPLICATION_HANDOFF.md` — exact fresh-session startup and native application order.
- `SOURCE_PRESERVATION_AUDIT.md` — current-product capabilities the redesign must preserve without replacing the frozen analytical snapshot.
- `PRODUCTION_ACCEPTANCE_MATRIX.md` — design-to-production proof matrix.

Important boundary:
- the current originating Sol chat still exposes legacy Studio Direct gateway0.1.7 and must not dispatch Paper writes;
- Ryan Business **Mastermind Paper** direct app has passed a real bounded write canary through explicit-file runtime v6 (#1011 comment5854808901);
- actual Commodities canvas application therefore resumes only in a fresh Ryan Business chat with that private app selected, unless the original Studio consumer itself later becomes write-qualified;
- do not replay historical Paper canary operation IDs or rebuild the25 R2 boards.

Read protected Mastermind procedure fresh before any modifying action. Current procedure at the time this packet was created was `deed35f6b0d8794987ab9692dd8d46b1549a720f`, but moving protected `master` remains the authority.
