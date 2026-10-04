# Seat ruling — CDV-1 Tasks 2 and 3, r3 packet erratum, 2026-09-30

Seat: CDV-1 Meta-CEO, session `251f88c8`. This record corrects `SEAT_RULING_T2_T3_R3_2026-09-30.md`. It adds rulings T2 R6, T3 R3 and one common ruling. It changes no grant, no placement and no Task 1 freeze.

## What was wrong

`SEAT_RULING_T2_T3_R3_2026-09-30.md` says: "Each commission is the 09-25 r2 packet, re-based on merged main, plus the rulings below." That is inaccurate. The r2 packets are the `ruling` fields of `args_cdv1_t2_source_currentness.json` and `args_cdv1_t3_interpretation.json`, last written 2026-09-25 01:40Z. The r3 packets were rewritten rather than derived from them, and the rewrite dropped these binding sections:

| Section | Packet | Origin | Status in r3 |
|---|---|---|---|
| FOUNDATION MAP Q6: the `PROFILE_SOURCE_FAMILY` declaration | T2 | seat fold 2026-09-24 09:35Z, from `integration/FOUNDATION_INTEGRATION_MAP_2026-09-24.md` (#7917) | **dropped; restored as T2 R6** |
| T7 CONTRACT BINDING: the §6.2 field map | T3 | ruling R13 on #7904, 2026-09-24 08:40Z | **dropped; restored as T3 R3** |
| Evidence response (Task 6) note | T3 | the same R13 block | dropped. It binds Task 6, not Task 3, so it moves to the Task 6 packet. |
| ANTI-COLLAPSE LAW | both | seat 2026-09-24, measured on T1 rounds 4–7 | **dropped; restored as the common ruling below** |
| CI DEPENDENCY LAW | both | seat 2026-09-24 08:30Z, after #7905 ci-pack-8 red | its placement is superseded by the r3 grant table; its exact-venv method is restored below |
| CI WIRING, OWNED FILES | both | r2 | superseded by the r3 grant table (intentional) |

The committed r3 packets stay byte-identical to what the lanes received, so they are not rewritten. The two lanes were already running when the drop was found, and no mid-run instruction channel exists. A running lane is never relaunched. The restored obligations therefore bind at acceptance:
- the seat's verification checks them;
- each PR's independent review treats a miss as a contract defect (bar (a));
- the lane's next fix round carries them verbatim.

## T2 R6 — the profile-to-source-family constant (restores FOUNDATION MAP Q6)

- The pure-addition section Task 2 appends to `engine/company_intelligence/pg_profile.py` declares one mapping as one constant: `PROFILE_SOURCE_FAMILY`, profile → source family, holding exactly one entry, public primary profile → `sec_edgar`.
- The key is the `RIGHTS_PROFILE` name that `pg_profile.py` already imports from `qa_exchange`, never a re-typed literal. The mapping is read-only.
- A lookup for any other profile, including the private PG token, is a typed refusal, never a `KeyError` and never `None`.
- Tests show one profile maps to one family, and that an unknown profile and the private token each raise the typed refusal.
- Task 2 does not read `config/theme_sources.yml` and gates nothing on it. Task 4 validates the mapping fail-closed and Task 6 gates on it at read, through one injectable registry-reader seam.
- `sec_edgar`, `load_registry_snapshot`, `assert_current_emission_allowed` and `engine/theme_graph/admission.py` arrive only with #7870. They are never copied here, and no parallel profile-to-rights table is minted (DEC:CDV1-FOUNDATION-INTEGRATION).

## T3 R3 — the Task 7 contract binding (restores R13 on #7904)

The design spec `design/T7_DOSSIER_DESIGN_SPEC_2026-09-24.md` §6.2 binds Tasks 3, 4 and 6. It stays PROPOSED until Task 6 merges. Task 3's interpretation output must expose these exact paths:
- `selection.currentness`;
- `findings[].rule_id`, in server order;
- `observations[]` carrying:
  - an owner metric family that separates the demand, segment and earnings rows;
  - `label.{en,zh}`;
  - `period`;
  - `basis`;
  - `value_and_unit.{en,zh}`;
  - `fact_id`;
- `missing_context`, in server order;
- `clocks.fiscal_period.{en,zh}`, `clocks.source_accepted.{en,zh}` and `clocks.source_currentness`;
- `authority`, with its six literal-false booleans.

`source_text`, where Task 3 carries any, is `{text, lang}` in the original language only; P&G filings are `en`.

The r3 freeze on `research/**` stands, so the lane may not amend §6.2. A path the lane believes cannot be exposed is reported under GAPS with its reason, and the seat decides whether to amend §6.2 in a records PR. It is never silently dropped.

## Common ruling — anti-collapse and the exact-venv proof (restored for every fix round)

- **Short steps, pushed as they land.** A long single exec degenerates: word salad, rc 0, nothing committed. So fix rounds work in short steps. After each completed step: `git add <named paths>`, commit with the trailer, and `git push origin HEAD:refs/heads/<branch>` (never force). An unfinished step is committed as `wip(...)` and pushed anyway.
- **Real probes.** Tests must probe the frozen contract, not restate the new code.
- **Exact-venv proof.** Before pushing a CI hunk, prove the suite collects and passes in a clean venv holding only its job's `pip install` list. A `ModuleNotFoundError` is fixed on that same install line.

## Discharge

| Obligation | Checked by |
|---|---|
| T2 R6 | seat verification (`PROFILE_SOURCE_FAMILY` present, one entry keyed by the imported name, typed refusal tested); the T2 review's task bar |
| T3 R3 | seat verification (a built case exposes every path above); the T3 review's task bar |
| Evidence response | the Task 6 packet |
| Common ruling | every fix-round packet, and the Task 4, 5 and 6 packets when each is re-based (none of the three carries it today) |

## Process correction

Before dispatch, every re-based or rewritten packet gets a paragraph-level diff against the packet it replaces. The dispatch record names each dropped paragraph and the ruling that supersedes it. A paragraph dropped without a named superseding ruling blocks the dispatch. That check would have caught this drop.
