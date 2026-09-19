# B-F07-3 capture observations

CODE_HEAD: `8dc43cbf5bd393506a481f566881320fb72b3891`.

Three hosts were regenerated from `templates/_valuation_assumptions.html.j2`
and `templates/theme.css`. The host shell retains its existing panel geometry;
the unnecessary full-site theme script was removed from these isolated fixtures.
The template's own slider behavior remains active. Financial figures in the
hosts are synthetic and are visibly labeled as such.

All 24 cells were captured sequentially: Tender Offers, Restructuring and null,
each in dark/light, EN/ZH, at desktop 1440×900 and mobile 390×844. Every crop is
`#va-event-bridge`; `capture-metrics.json` records the exact visible sentence.

- Tender Offers: “Latest filing on file (Tender Offers) usually lifts the multiple people pay.” / “最新备案（要约收购）通常推升市盈率倍数。”
- Restructuring: “Latest filing on file (Restructuring) usually presses margin.” / “最新备案（重组）通常压缩利润率。”
- Null: “No filing on file yet for this company.” / “该公司暂无备案。”

The event line is 11px, below the FY footnote's 11.5px. Both the class and
direction use the shared muted text color. Dark has a dark material background
and cool muted ink; light has a white material background and darker slate ink.
The event line adds no new theme-specific material or interaction.

Capture checks: 0 page errors; 0 event-line overflows; one language visible per
cell. Representative dark and light crops were visually inspected. No visual
smell was observed in those crops; this does not claim independent taste approval.

The functional suite passed. The separate CI dependency audit still reports
62 introduced path entries across eight jobs at the prior head (hosted run
35421325082, job 105839492389). This round preserves the same engine and CI
bytes; no all-green or production-deployment claim is made. See `r2/heal-r2.md`.
