# Frozen negative cases and execution

The source fixture specification is the immutable F01-F16 table at Macro
`1f21fb74735d826a37d5e1925b1d06af6feb6fda`. All sixteen identifiers are executable
in `tests/test_slr_local_source_qualification.py`; F06 includes three separate
2016/2018/2023 synthetic taxonomy boundaries. None is a market observation.

| ID | Executed assertion |
|---|---|
| F01 | D+20 H7 risk set ignores future C; four-case covariance 0, selected covariance 1 |
| F02 | $100 to $99 with $1 dividend yields 0 total return, not -1%; double adjustment refused |
| F03 | All subject-issuer listings excluded; peer count is distinct other issuers |
| F04 | Old/new owners separated across ticker-reuse gap |
| F05 | Alias end exclusive; undated mapping refused |
| F06 | Dated GICS transition retained; pre-inception benchmark refused |
| F07 | SEC report-period value unavailable until public clock |
| F08 | Missing scheduled session refused; no compressed return window |
| F09 | Earlier unknown candidate prevents later-shock replacement |
| F10 | Singleton and constant-Z date-sector cells nonidentifying |
| F11 | Measurement starts C+1; unknown terminal cash refused |
| F12 | Future U rejected at C; B reanchors the later window |
| F13 | Unknown/nonordinary/ambiguous peers do not satisfy twenty-issuer coverage |
| F14 | Documentation without delivered source and rights stays NOT_ADMITTED |
| F15 | Later earnings announcement cannot become known C-1 schedule |
| F16 | Raw/adjusted price or issuer splice refused |

Supplementary tests cover all ten source families and failed/unknown receipts,
source digests, protected paths/outcome columns, deterministic finite hashes,
restated/first-seen clocks, multipage/duplicate/missing actions, lagged $25m/$5
selection, D+21..D+63 with same-D continuation, 200-of-252 complete baskets,
504-session lookbacks, fixed-effect variation, occupied blocks, full-prefix
Detector-D cooldown/static parity, last-five watch override and benchmark gaps,
frozen lagged factor math and input-only CLI errors. Actual first-shock incidence,
real calendar qualification and historical taxonomy parity are **not executed**
because historical source gates did not pass. Their counts remain null.
