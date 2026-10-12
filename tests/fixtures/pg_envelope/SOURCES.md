# PG envelope fixtures (CDV-1 T1, family F1-Q)

The six `.htm.gz` files are exact public SEC EDGAR exhibits, compressed with `gzip -9` and mtime 0.

- Each one decompresses to the bytes the EDGAR archive serves at `https://www.sec.gov/Archives/edgar/data/<CIK as an integer>/<accession without dashes>/<file>`.
- The sha256 and size below pin those bytes. `tests/test_pg_envelope_f1.py` checks them on every run.

| file | issuer (CIK) | accession | accepted (UTC) | bytes | sha256 of the served bytes | role |
|---|---|---|---|---|---|---|
| `fy2425q4amj8-kexhibit991.htm` | Procter & Gamble (0000080424) | 0000080424-25-000067 | 2025-07-29T11:03:15Z | 454,203 | `6c625f3b78ba710da8a682e3ef5d5a57b157fd962f2d486154d9654ae25dcb6a` | FY25 Q4, layout F2-A (refused in v1) |
| `fy2526q1jas8-kexhibit991.htm` | Procter & Gamble (0000080424) | 0000080424-25-000240 | 2025-10-24T11:04:27Z | 305,212 | `f3c987b34434671b6cad1f09c6fd42aa10701ac3c2a1fc62644b65c44e0dad96` | FY26 Q1, F1-Q positive |
| `fy2526q2ond8-kexhibit991.htm` | Procter & Gamble (0000080424) | 0000080424-26-000006 | 2026-01-22T12:02:05Z | 296,069 | `f6d79042f16c6131100c6c6e678e96f43dd666b410356cc23cd43d7d1e032503` | FY26 Q2, F1-Q positive |
| `fy2526q3jfm8-kexhibit991.htm` | Procter & Gamble (0000080424) | 0000080424-26-000056 | 2026-04-24T11:01:47Z | 308,066 | `eeef9d0de613e44ba3e4444c084431100491dd3a28a3b6226f0e8163ca770b84` | FY26 Q3, F1-Q positive and mutation base |
| `fy2526q4amj8-kexhibit991.htm` | Procter & Gamble (0000080424) | 0000080424-26-000093 | 2026-07-29T11:03:12Z | 472,455 | `9fe6812066a4ef6a1ca8b53b394ae0dbf2796eaef0c5141d2ae60fe94521dcbc` | FY26 Q4, layout F2-A (refused in v1) |
| `q22026pressreleasetables.htm` | Colgate-Palmolive (0000021665) | 0000021665-26-000041 | 2026-07-31T11:58:00Z | 789,706 | `a04042a7d643bea6bb3dc0aea14224e3705a4c56847d6694708897444f72d40e` | near-neighbour refusal witness (same Workiva template, Ex-99) |

**Rights basis.**
- These are public filings. They are committed as exact original issuer documents under the decision owner's direction on PR #7905 (GMI Meta-CEO, comment 5825632041, 2026-09-25T02:22:28Z).
- That is the same basis as `tests/fixtures/capital_structure/document_terms/real_edgar_*`.
- They are test inputs only: the suite reads them to check the extractor and the validator, and nothing here is rendered or published.

**The oracle files.**
- `oracle_f1.json`, `oracle_f1_notes.md` and `oracle_f1_spec.md` are the independent oracle read, byte-exact as the lane returned them.
- The oracle was authored from the five P&G originals alone, on a fabric lane holding no repository.
- `seat_adjudication.json` is the seat's overlay on that read. It corrects eight locators and no value.
