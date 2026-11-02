---
key: FINANCE-PAGE-LABELFOR-RETURNS-ONE-LOCALIZED-STRING
claim: >-
  In templates/finance_intelligence.js, labelFor(map, key) returns ONE string already
  localized to the current language (copyPair(labelRow(map, key))), not an [en, zh] pair.
  Indexing its result with [0] or [1] yields single characters. At T11 head dc93fca9 this
  produced accessible names such as "Open evidence for O step" and "打开约束证据：本". The
  [en, zh] pair comes from labelRow(map, key), and that pair is what ariaPair(en, zh)
  expects.
falsifier: >-
  Read the labelFor, labelRow, copyPair and ariaPair definitions in
  templates/finance_intelligence.js. The claim is false if labelFor returns an array.
so_what: >-
  Every bilingual accessible name or data-aria-* pair must be built from labelRow(...)[0]
  and labelRow(...)[1], or from a literal pair, and never from labelFor(...)[i].
  Reviewers should grep for "labelFor(" followed by "[" in any Finance page diff.
kind: landmine
verified_at: 2026-09-25
verified_by: "headless probe of PR #8009 @dc93fca9 (check 4); templates/finance_intelligence.js helper definitions"
scope:
  - macro
  - templates/finance_intelligence.js
confidence: verified
---
