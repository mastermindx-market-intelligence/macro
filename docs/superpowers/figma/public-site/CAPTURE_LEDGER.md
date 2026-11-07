# MastermindX Public-Site Figma Capture Ledger

- Frozen source: `macro@15c01bd991f35d0bb2185ee1e608a05df0805803`
- Source-identical local head: `e0e3fda2fa2a44d8d64c3f0a52b9d56c1de3653b`
- Browser: system Google Chrome through Playwright, DPR 1
- Dynamic offer endpoint: deterministic source-default response (`active=true`, `claimed=null`, `cap=2000`)
- Static method: exact-width CDP full-document capture with `?still=1`
- Motion method: fresh 1440×900 viewport per semantic wait

## Coverage

- Static reference cells: **20 / 20**
- Motion-state cells: **16 / 16**

## Static matrix

| Page | Variant | Pixels | Document width | SHA-256 |
|---|---:|---:|---:|---|
| homepage | 1440-en | 1440×10526 | 1440 | `bc7b0fbf373a6505…` |
| homepage | 1440-zh | 1440×10438 | 1440 | `a6d5e7169cea8672…` |
| homepage | 1024-en | 1024×12325 | 1024 | `b5901e381143e11f…` |
| homepage | 390-en | 390×13463 | 406 | `9e65f527ad11eb5c…` |
| homepage | 390-zh | 390×12913 | 390 | `53dcc62fbf5dc660…` |
| market-terminal | 1440-en | 1440×8670 | 1440 | `d11f8e7276f31af9…` |
| market-terminal | 1440-zh | 1440×8423 | 1440 | `fa0ed2f24961215f…` |
| market-terminal | 1024-en | 1024×10859 | 1024 | `4a35cd35f3583c6b…` |
| market-terminal | 390-en | 390×11580 | 406 | `f0ebbf85bdba3408…` |
| market-terminal | 390-zh | 390×10296 | 390 | `5f9b5aa595907360…` |
| mastermind-ai | 1440-en | 1440×7390 | 1440 | `449f4b5b0f76ea22…` |
| mastermind-ai | 1440-zh | 1440×7030 | 1440 | `d9996eae6594b611…` |
| mastermind-ai | 1024-en | 1024×8666 | 1024 | `e3ca6996871d7bb5…` |
| mastermind-ai | 390-en | 390×9764 | 406 | `789b5f5b204e91f7…` |
| mastermind-ai | 390-zh | 390×8858 | 390 | `2750fbc44f47bc4e…` |
| market-dashboards | 1440-en | 1440×9504 | 1440 | `097adf890d932a76…` |
| market-dashboards | 1440-zh | 1440×9363 | 1440 | `0819c7aab1e4e9c3…` |
| market-dashboards | 1024-en | 1024×10927 | 1024 | `3b03378127401e5f…` |
| market-dashboards | 390-en | 390×13054 | 425 | `cab223495a027e14…` |
| market-dashboards | 390-zh | 390×11963 | 425 | `ef7bbe12a32df1d7…` |

## Motion matrix

| Page | Phase | Pixels | Δ from prior | SHA-256 |
|---|---:|---:|---:|---|
| homepage | observe | 1440×900 | 0 | `e1da5a8e3a6bea44…` |
| homepage | reason | 1440×900 | 997245558 | `2237528169945f50…` |
| homepage | resolve | 1440×900 | 996931983 | `26de0f49bcafca68…` |
| homepage | hold | 1440×900 | 999125242 | `5d6c6712a6c20edc…` |
| market-terminal | observe | 1440×900 | 0 | `9418d72da8323d3a…` |
| market-terminal | reason | 1440×900 | 995406012 | `e9cd4e9593a5196c66bacd6627824604983d9b5ba616415eb23015836b16e59b` |
| market-terminal | resolve | 1440×900 | 995726596 | `3bf0dde39c1f8e57…` |
| market-terminal | hold | 1440×900 | 995464003 | `193748c1b8b724f1…` |
| mastermind-ai | observe | 1440×900 | 0 | `0b8b0b1e39cad4d8…` |
| mastermind-ai | reason | 1440×900 | 995380239 | `4081485e5d24d660…` |
| mastermind-ai | resolve | 1440×900 | 995504176 | `0c4fa35cdc7ed825…` |
| mastermind-ai | hold | 1440×900 | 995440171 | `3551b9c4ea54d3e1…` |
| market-dashboards | observe | 1440×900 | 0 | `00c8b0c19bab030c…` |
| market-dashboards | reason | 1440×900 | 995382502 | `9711ef11416f4a6b…` |
| market-dashboards | resolve | 1440×900 | 996496257 | `454f6f5c9043add3…` |
| market-dashboards | hold | 1440×900 | 996493230 | `5c34bcc4046bb801…` |

The motion waits are representative evidence; source runtime phases and timing remain authoritative.
