# C01 real STAGE evidence and protected adoption

The assigned GMI source owner accepted a real retained-input STAGE publication on 2026-10-12. This evidence supports the registry transition from `PROPOSED` to `PRODUCED`; it does not claim a serving current pointer or production acceptance.

## Observed effect

- Original operation: `gmi-c01-stage-20261012-001`. The initial 08:10 refusal and original metadata remain retained. After repair #8991 was installed and independently qualified, an explicit same-operation recovery adjudication allowed one invocation with new immutable expected-deployment metadata.
- Source: `82c63351fa8c7dae219f01a833704724bb5aff8f`. Recovery invocation: 15:20:51–15:21:06 UTC, exit 0, empty stderr. The final producer preflight used a 130.546475-second-old F04 census and bound the actual producer and qualified API process.
- Result: `MEMBERS_OBSERVED_NOT_ADOPTED`; four native conditional objects observed, generation manifest written, current pointer not written. The journal is an immutable STARTED reservation; the separately retained outcome records its terminal result.
- Generation: `05811e172eda94d6d07e63ad151284317d68af3781c6635150a586dfedbb22d0`. Original fact, edition, rights ruling, review, correction decision and clocks remain unchanged.
- Independent same-host bounded readback at 15:21:40.804490 UTC read the retained operation, outcome, manifest and both members; the current pointer was absent before and after the member capture. The source and historical metadata remained unchanged.

## Evidence custody

The JSON files below are exact retained bytes, not reconstructed receipts. The parent independently checked their bindings against qualified source and authentic runtime capture. The offline checker adds input-consistency validation only; it supplies no store, runtime, adoption or retry authority.

| File | SHA-256 |
| --- | --- |
| `gmi-stage-real-operation.json` | `73046bef0f8004e0209e27f8842c709b9a3528fbf414f3405cab8571bbf6f53d` |
| `gmi-stage-real-outcome.json` | `e73c7476ab7208a08c1e4429fdc2bc03700d126e5a27e3f2411f4cd4fac23d0e` |
| `gmi-stage-real-manifest.json` | `05811e172eda94d6d07e63ad151284317d68af3781c6635150a586dfedbb22d0` |
| `gmi-stage-real-parent-acceptance.json` | `440de75c9e2dc71b35a263b00b6066f3a41f1b2f8e170a2fd35959d444934ca7` |

The full authentic capture remains in the original parent evidence directory as `gmi-stage-success-authentic-capture.stdout.json` (SHA-256 `4ca65cebaad45405c55464159e76758ec5fa7138a423b360d01c217c948fbe42`). The acceptance receipt binds that capture, its transport, the independent expected bindings, and exact edition/fact bytes. The source body remains private; this adoption does not republish it.

The failed metadata-placement wrapper was a Python compile error before execution; its stderr is preserved. The corrected wrapper created the same new metadata path once with O_EXCL and fsync/readback. It did not replay publication.

## Remaining release and serving gates

This commit changes only the protected dataset adoption and makes the existing PROPOSED refusal test independent of the current registry status. After protected release and installation, the original F04 owner must qualify the staged runtime and provide a fresh census. GMI must prepare a **NEW** adoption-bound `PROMOTE_CURRENT` operation, intent, manifest and generation. The old STAGE manifest is bound to the PROPOSED adoption and must never be reused or restamped. Authenticated API and matching Terminal evidence are still required for production acceptance. Neither this source decision nor any private pointer grants broader rights, PIT admission, commercial magnitude or trade authority.
