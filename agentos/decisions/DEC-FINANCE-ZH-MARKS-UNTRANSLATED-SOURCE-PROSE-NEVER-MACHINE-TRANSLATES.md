---
key: FINANCE-ZH-MARKS-UNTRANSLATED-SOURCE-PROSE-NEVER-MACHINE-TRANSLATES
question: >-
  In Chinese mode, how should the Finance Intelligence page show payload prose (mechanisms,
  statements, implications, drawer business scope and limitations) that owners publish
  only in English?
answer: >-
  Show the owner's prose verbatim and put lang="en" on exactly the element holding it
  (payload prose only; page-language fallback placeholders never sit inside lang="en").
  Page placeholders, translated labels, ids, dates and enum words stay unmarked Chinese.
  Each section whose painted body holds at least one such element gets ONE plain-word
  note, carrying no lang attribute, as the first body line directly after the section's
  .fi-section-head: <p class="fi-srclang-note l-zh">本节部分文字为英文原文，未经翻译。</p>.
  (The T11 packet anchored this on a .fi-sowhat line that exists nowhere in the frozen
  spec or the page; the seat corrected the anchor in round 2.)
  The evidence drawer gets <p class="fi-srclang-note l-zh">此记录部分文字为英文原文，未经翻译。</p>
  at the top of its body, only when the open record shows such prose; in the drawer only
  scope, excerpt and limitations are marked lang="en". Notes are recomputed
  on every repaint, are never italic, and use the chip type token. The page never
  machine-translates.
rationale: >-
  Machine-translating evidence prose at render time would publish unaudited claims under
  the owner's name, and LLMs may never originate or alter calibrated content (A7).
  Hiding English prose in Chinese mode would remove evidence and break the rule that a
  missing state is rendered as words. Correct lang marking gives screen readers the right
  pronunciation and fonts the right fallback. The note states the language gap plainly
  instead of letting a bilingual reader discover it.
alternatives:
  - option: machine-translate prose at render or at bake time
    why_not: unaudited claims presented as the owner's evidence; translations drift from the source and cannot be grounded
  - option: hide English-only prose in Chinese mode
    why_not: removes evidence; violates missing-state-as-words and EN/ZH parity of substance
  - option: a badge on every English element
    why_not: visual noise over the density budget; one note per section carries the same fact
evidence:
  - "T11 packet item 10 (seat 938d17d6), repaired by lane fin_t11_repair on PR #8009 (ruling F7)"
  - "seat headless probe checks 10, 10b, 10c and 10d (scratchpad probe_t11.py) against the T11 heads"
  - "PR #8009 round 2 (seat commit 6ad670ae): probe 122 PASS / 0 FAIL / 4 INFO over 126 checks; the negative control (pre-erratum anchor) fails 10c in all four ZH cells"
  - "tests/test_finance_intelligence_page.py::test_source_language_notes_follow_the_section_header_without_a_lang_attribute and ::test_fallback_placeholders_never_render_inside_lang_en"
affects:
  - WS:GMI-FINANCE-INTELLIGENCE
  - templates/finance_intelligence.js
  - templates/finance_intelligence.css
confidence: high
reversibility: easy
decided_by: "seat 938d17d6 (Finance Intelligence CEO seat, operation gmi-finance-fable-ceo-e2e-20260924-chairman-001)"
decided_at: 2026-09-25
---
