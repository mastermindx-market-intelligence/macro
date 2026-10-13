---
key: W3C-COHORT-CAPTURE-IS-REFUSED-BY-THE-RIGHTS-GATE-BY-DESIGN
claim: >
  Every production W3C selection-cohort capture (U.S. and China) is refused by the rights
  gate, and that is intended. `default_capture_capability()`
  (engine/theme_graph/selection_cohort_publication.py:46) asks `rights_use.capture_capability()`,
  which resolves each source ref through `rights.family_for_source_ref` against
  `rights.SOURCE_PREFIX_FAMILY` (rights.py:73). The refs are `site/factordata/us_standouts.json`
  (publication.py:382/387), `site/factordata/china_standouts.json` (l.442) and
  `build_china:served-wide-buy` (l.446). The standout board is deliberately not a family
  (rights.py:70-72; Chairman gate #3, PR #8499). So capture refuses with
  `SOURCE_FAMILY_UNRESOLVED` (rights_use.py:172), and publish/consume return
  `CAPTURE_RIGHTS_UNAVAILABLE` (publication.py:260/330/338). The builders' internal
  selection-cohort bindings stay None. Until PR #8554 the product projections
  `site/neuralwebdata/selection_cohort/{us,cn}.json` reported `WRAPPER_MISSING`, which looks
  like a wiring bug but is not one.
falsifier: >
  A production render whose `site/neuralwebdata/selection_cohort/us.json` or `cn.json` reports
  `availability.status` AVAILABLE; or a render log without
  `W3C capture refused: ['SOURCE_FAMILY_UNRESOLVED']`; or
  `git grep -n standouts origin/main -- engine/theme_graph/rights.py` showing a
  `SOURCE_PREFIX_FAMILY` row that matches these refs.
so_what: >
  An UNAVAILABLE W3C projection is a rights decision, not a wiring defect. Do not "fix" it by
  adding the standout board or `#buy` to `SOURCE_PREFIX_FAMILY` or `theme_sources.yml`; that
  reverses gate #3. AVAILABLE capture needs a Chairman ruling. The open option is a
  purpose-scoped, capture-only house family with exact or W3C-namespaced refs. It would leave
  `#buy` and theme_coverage_gaps fail-closed, and the CN THS lineage stays under gate #2.
  Until then, W3C production proof means typed fail-closed proof. Read `unavailable_reason`:
  after PR #8554 it should read `SOURCE_UNAVAILABLE:CAPTURE_RIGHTS_UNAVAILABLE`, and a
  `WRAPPER_MISSING` there again means the builder lost the typed refusal.
kind: constraint
verified_at: 2026-10-06
verified_by: >
  Render run 37457399012 (2026-10-06): log lines 1103-1106, 1246-1247, 1280-1283 and
  1502-1503 at 13:51:39Z and 14:12:19Z show `W3C capture refused: ['SOURCE_FAMILY_UNRESOLVED']`,
  then `W3C US qualified reads refused (['CAPTURE_RIGHTS_UNAVAILABLE']); receipt-only` and
  `W3C China source unavailable: ['CAPTURE_RIGHTS_UNAVAILABLE']`.
  `git show origin/main:site/neuralwebdata/selection_cohort/us.json` (and cn.json) at
  aafb9e25b0c1 shows `unavailable_reason` WRAPPER_MISSING with n_selected 0, last written by
  fe808d00b77 (render, scope=all). `git grep -n` at origin/main 3d7a6f86e810 confirms every
  line cited in `claim`.
scope:
  - macro
  - engine/theme_graph/rights.py
  - engine/theme_graph/rights_use.py
  - engine/theme_graph/selection_cohort_publication.py
  - scripts/build_site.py
  - scripts/build_china.py
confidence: verified
---

Found on 2026-10-06 while proving W3C (#8417) for WS:GMI-THEME-GRAPH Wave G. The seat
classified capture enrollment as an exact human gate, because a seat cannot overrule an
explicit Chairman rights ruling. The seat recommends the capture-only family option above.
PR #8554 makes the refusal reason visible on the product projection, per gate #8
("preserve source order/reasons"). It does not change rights.
