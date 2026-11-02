# P19 — independent verification packet (2026-11-02)

Three READ_ONLY Opus verifiers (ROUTE: review, MODE: READ_ONLY; commissions in `COMMISSIONS.md`) attacked the seat's claim
packet at the merged head `ec1f1ea694d5`. None read another's return; none edited a file. Returns are stored byte-exact
(final assistant text, extracted from the agent transcript by the seat's `extract_return.py`; nothing rewritten).

| file | sha256 | scope | verdicts |
|---|---|---|---|
| `verifier_A_R3A-01-46.md` | `1cac9dd8abe0926fb939ce5ec7f08d601046b90dc1cc785bb48c293800f23292` | R3A-01..46 | 42 CONFIRMED · 3 UNSUPPORTED (R3A-20, -25, -31) · 1 PARTIAL (R3A-35) · R3A-27 contract caveat |
| `verifier_B_R3A-47-92.md` | `bb12e30e03c015c5a2fc96098fcf40c80f92c2c92461ee82aea70074053ee90a` | R3A-47..92 | 39 CONFIRMED · 5 UNSUPPORTED (R3A-47, -52, -66 major, -75, -86) · 1 PARTIAL (R3A-89) · 1 BLOCK_CONFIRMED (R3A-92) |
| `verifier_C_C-U-journeys.md` | `50b0025cee9391261d216d3107a90cd0fa4a5a4a5b9f79dcc3b195eef7645288` | C01–C28, U01–U14, J01–J15 | 0 CONFIRMED · 22 PARTIAL · 13 NOT_DELIVERED · 7 UNSUPPORTED; 14 journeys UPHELD, J04 BLOCKED |
| `COMMISSIONS.md` | `fbb2d9a00f3cb9a3b7467297173d4837c46c5f3cc0657bb1608b439eaaad2d60` | the three commissions | — |

Consumers: `../P19_CAPABILITY_DISPOSITION_2026-11-02.csv` (`verifier_verdict` / `verifier_note` copied verbatim from the
row lines by `fill_verdicts.py`; 134 of 134 filled), `../P19_ACCEPTANCE_2026-11-02.md` §B/§C/§E, and the ledger block
`p19_p20_dispositions_20261102` in `research/reference_integrity/sector-intelligence-cycles-20261021/proposal.yml`.

Run notes: each verifier hit the native 24-turn limit once or twice before producing a packet and was resumed by message
("at most eight more tool calls, batched, then the full return; UNSUPPORTED 'not reached in budget' is acceptable"); every
UNSUPPORTED row carries its reason. A P20 reviewer receipt (`verifier_D_P20_source_review.md`) is added when the fresh
review of the P20 source diff returns.
