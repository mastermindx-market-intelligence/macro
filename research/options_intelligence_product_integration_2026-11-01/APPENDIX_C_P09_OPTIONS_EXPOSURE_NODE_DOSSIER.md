# Appendix C — P09 `options_exposure_node`: activation-OFF switch dossier

Every switch is **OFF**, and this record changes none of them. It describes what each switch gates, who owns it, what evidence activation needs, and the plumbing behind it. ORCH-2 takes no activation decision.

- Pins: Terminal `mastermindx-market-intelligence/mastermind-terminal` master `db6168c20ce42217ed99d9fa53e6048683505da5` (TERM). Macro `820f33b539c39f21f48f5e57a799cdbb5c196c6e` (MACRO).
- Method: ORCH-2 read the source directly. Three L4 Fabric lanes (oi2-l4-r1/r2/r3) were refused at admission before any worker started, and those ids are burned (DEVIATION in the main record). Blob ids are `git hash-object` values from the pinned trees.
- Claim classes: **observed** = read in source or on a GitHub record at the stated pin. **interpreted** = ORCH-2's reading of what the source implies.

## C.1 Switch census

| # | Switch | Where it is read | What it gates | Default | Class |
|---|---|---|---|---|---|
| S1 | `NEXT_PUBLIC_MM_OPTIONS_FROZEN_ENTRY_ENABLED` | TERM `terminal/lib/frozenNodeEntryProtocol.ts:8` → `FROZEN_ENTRY_CLIENT_ENABLED` | The client entry control. `terminal/components/exposure-map/FrozenNodeEntry.tsx:25-27` (blob 9968adb8) renders `EnabledFrozenNodeEntry` only when the flag is on, `metric === "gamma"`, and every shock value is 0. Otherwise it returns `null`. | OFF: no entry control renders under the selected Exposure node (`ExposureMap.tsx:271`). | observed |
| S2 | `MM_OPTIONS_FROZEN_ENTRY_ENABLED` | TERM `terminal/lib/frozenNodeEntryServer.ts:18` | The server half of the same entry. With the flag off, the frozen-entry request behind `POST /api/alerts` answers 409 `frozen_entry_disabled`. | OFF | observed |
| S3 | `OPTIONS_FROZEN_READER_ENABLED` | TERM `ingest/options_frozen_assembly.py:56` (blob d97d2964) | Assembly of the frozen-node reader: reading frozen exposure nodes for evaluation. | OFF | observed |
| S4 | `OPTIONS_FROZEN_PUBLISHER_ENABLED` | TERM `ingest/options_frozen_assembly.py:28-31` | The publisher. It also needs `OPTIONS_FROZEN_READER_ENABLED=1` and a lifecycle adapter, so it cannot be turned on alone. | OFF | observed |
| S5 (fifth gate) | `OPTIONS_FROZEN_DELIVERY_ENABLED` | TERM `ingest/options_frozen_delivery_cli.py:13` (blob 5564e225). MACRO `lib/frozen_delivery_client.py:93-99` (blob 4c281e6c), wired at `scripts/drain_alert_outbox.py:35,66,69`. | Delivery of a frozen-node alert through the Macro alert drain. | OFF in source. The **observed production value is UNKNOWN** (see C.5). | observed / UNKNOWN |

The canonical enrollment document is TERM `docs/OPTIONS_FROZEN_ENROLLMENT_SOURCE_2026-10-29.md` (blob 22737a26). L224-225 and L328-329 list the switches and their activation order. Its `frozenWebhookDelivery.test.ts:146` asserts "keeps default activation off". (observed)

## C.2 Macro plumbing the delivery path already has (observed @MACRO)

| Piece | Locator | Role |
|---|---|---|
| Preference model | `lib/user_prefs.py:73-80` | Holds the alert-delivery category preference that the Settings chip writes. |
| Drain | `engine/alert_delivery_drain.py` (blob df75e316) L60, L320-328, L498-504 | Outbox read and category routing. |
| Tier floor | `engine/alert_delivery_drain.py:519-534` | `essential` is the delivery floor. |
| Email admission | `engine/alert_delivery_drain.py:540-545` | `FrozenEmailAdmission`. |
| Dispatch / receipt | `engine/alert_delivery_drain.py:825-834, 889-900` | Dispatch and receipt writes. |
| Tests | `tests/test_alert_delivery_drain.py:1199-1247` | Frozen-category admission and refusal cases. |
| Schema | Terminal migrations 0045 (blob b786a8e3) and 0046 (blob daab6c21) | Applied 2026-10-31 per the owner record (#599). |

## C.3 Owners and current acceptance (observed on the GitHub records named)

| Owner surface | Record | State |
|---|---|---|
| Deployment and ledger of the frozen path | Terminal #599, comment 6540472904 | Deployment `b1ba8e7c` accepted. The **authenticated UI is not accepted**; refusal recorded in comment 6540385685. |
| Lab1183 ledger writer | Terminal #1182, comment 6540467931 | Writer accepted at `b1ba8e7c` (AC50 = DO_NOT_REDO_ACCEPTED). |
| ExposureMap `returnCheck` fix | #599 comment 6333686799 (R2 owner) | Owner answer still open. Out of scope for ORCH-2; not touched. |

## C.4 Evidence each activation step would need (interpreted from the enrollment doc order plus the gates above)

Every step below is a seat or Chairman act. ORCH-2 performs none of them.

1. **S3 reader on.** Needs a dated reader receipt showing frozen nodes assembled from a named Exposure snapshot (snapshot asof, node count, no future clocks). The receipt must come with the reader's refusal cases still passing.
2. **S4 publisher on.** Needs S3 on, a named lifecycle adapter, and one admitted canary publish whose effect can be read back (an exactly-once publish id). The publisher must never run without its reader.
3. **S1 + S2 entry on together.** Turning on only one is a split-brain state. S1 alone shows a control that the server refuses with 409; S2 alone leaves a server path with no UI. Activation needs:
   - the signed-in entitled-render proof of the Exposure tab with the entry control present (gamma, zero shock);
   - the 409 path proven gone for an entitled user;
   - unentitled and signed-out denial still proven.
4. **S5 delivery on.** Needs:
   - the observed production value of `OPTIONS_FROZEN_DELIVERY_ENABLED` read on the drain host (C.5);
   - one delivery canary to an operator-owned address, with the receipt row read back;
   - the `essential` floor and `FrozenEmailAdmission` refusal paths re-run.
5. **Copy.** The Settings note "Exposure-level alerts are not available yet." (`terminal/components/settings/SectionAlertDelivery.tsx:474`, blob 0a683ced) must stay until steps 1–4 are proven. Removing it earlier would claim an alert that cannot fire.

## C.5 GAP

- `OPTIONS_FROZEN_DELIVERY_ENABLED`: the observed value in receipt 48179 is **UNKNOWN**. ORCH-2 cannot read host environment, and no public receipt states the value. Resolution: an operator or seat read on the drain host, recorded once.
