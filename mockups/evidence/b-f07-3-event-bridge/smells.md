# B-F07-3 capture observations

CODE_HEAD: `f374431cdb9f5368745311f69edbe23c19c491da`.

Three hosts were regenerated from `templates/_valuation_assumptions.html.j2`
and `templates/theme.css` at this CODE_HEAD. Hosts and the 24 crops were
byte-identical to the previous capture; they were recaptured anyway so the
receipt names this CODE_HEAD.

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

The functional suite is 28 passed on Python 3.12.10. Hosted contract-delta at
CODE_HEAD concluded SUCCESS with `0 introduced, 0 inherited (base f986ecb2d6f9)`
(run 35426829901, job 105856382629). Live generated pages remain AAPL-only by
the MO-PAID-020 census gate. See `r3/`.
