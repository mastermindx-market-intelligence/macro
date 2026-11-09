# Frozen source fixture

rates_command.json is the existing production producer payload from macro commit 9a13c64bf69f782332afa29efb09fe48ee30b857, path data/rates_command/latest.json. Used only to render the full existing Fed detail template in deterministic UX tests; no assertion promotes its market outlook to current truth.

## Full-page view-model seed

`view_model.json` is a frozen representative test seed serialized from
`tests.test_macro_risk_dialog._vm()` at source base
`9a13c64bf69f782332afa29efb09fe48ee30b857` on 2026-11-09.
`workspace_vm()` explicitly supplies the dated illustrative history, event labels,
market state and sentiment used by this UI proof. No account or production feed
is accessed. Freezing this seed keeps the UI suite independent of the unrelated
Stocks build/collector import chain; the existing canonical full-template suites
continue to exercise the complete production rendering environment.

`alert.json` is frozen from `tests.test_macro_w9_r1._alert()` at the same base.
The default workspace supplies three explicitly illustrative bilingual headlines,
three heating and three cooling sectors, and a populated briefing so the visual
matrix exercises populated cards as well as the separate unavailable route.
These are test inputs; they are not published market observations.
