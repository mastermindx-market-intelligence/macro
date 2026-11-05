# F02 Visual / Taste Critic — Narrow Final Follow-up

**Scoped disposition: VTC-007 RESOLVED in the supplied static evidence.**

**Advisory adoption verdict: PASS_WITH_CONDITIONS, retaining the qualification conditions from the frozen repair pass.**

**Follow-up review freeze:** 2026-11-03 02:51:50 UTC

No reviewed VTC visual finding remains open. This is a narrow static follow-up, not a fresh broad review, executed browser result, editable Paper qualification, admitted Opus RIG receipt or design-authority approval.

## Exact identity and validation

| Identity | Value |
| --- | --- |
| Supplied commit | `d68d5ecfbcd7e29094f59af3f44e7ae2a0f7f940` |
| Candidate | `F02-SYSTEM/1.0.0-candidate.2` |
| Artifact freeze | `2026-11-03T02:48:47.284785+00:00` |
| Current artifact-set SHA256 | `38b19c087b0639b728f37d015c939e7abbccf95722b72730f6f5fce84e025324` |
| Manifest | `reviews/final-followup-artifacts.json` |
| Manifest file SHA256 | `f1c0ed1ff54da7dcbc4cc9f14d57609df8a37375e0c51cc1192e86263d947ccb` |
| Predecessor repair commit | `1253a647d193e1eacd1eb6f523a7a031529d2150` |
| Predecessor artifact-set SHA256 | `6c1f8ba6937c620a306644764d69d7adef5672d27f6c512a080dcb35063f9ca3` |

All **55 manifest members** matched their listed byte counts and SHA256 hashes. Independently hashing the lexical path + U+0000 + lowercase file SHA256 + U+000A sequence reproduced the current artifact-set SHA256.

Of the 24 PNG/SVG sheet files, exactly **three SVGs and two PNGs changed**. The other **19 are byte-identical** to the frozen repair set. The supplied commit was not independently queried through Git hosting.

### Affected static files

| File | Current SHA256 |
| --- | --- |
| `sheets/macro-dark-390.png` | `126c3d3c47f87cccc6cc1f742afe982d48483d410f4cada2447f4f17fb9d9f43` |
| `sheets/macro-dark-390.svg` | `dc08f2e539dda259c604470a545475f2fceb1f1095123e7a15cb0ffb6872d4da` |
| `sheets/macro-light-zh-390.svg` | `31053440313b44abd1489a4ef40780ea104cbe141605599dc62b3c80f60c989b` |
| `sheets/mobile-comparison.png` | `90c3485ee8a2ea68259bc7003dc5854196ca42a27ee643498c5c58d8282d8c38` |
| `sheets/mobile-comparison.svg` | `59ec902c09eb380cc86cedb1a91fdcfe24a4b2f21212dbeadc7a01b5244e023e` |

## VTC-007 closure

**Original issue:** The narrow static reference did not announce its additional coverage columns until after all ten rows. The first comparison view looked complete, making horizontal overflow difficult to discover. The supporting HTML already put its hint before the table.

**Observed repair:** The English frame now says **“Scroll → for coverage and all columns”** directly under the Sector comparison heading and before the table header. In the 390px frame, its origin is x=16 and its baseline is y=320. The first row's text baseline remains y=398, preserving the early access that resolved VTC-002.

I visually inspected both changed PNGs. The new hint is legible and clearly associated with the table. It does not overlap the comparison heading, adjacent View chart button or table header. The lower row-count/scroll summary can remain without interfering with the new early cue. The inspector side of the combined mobile plate remains visually undisturbed.

I also inspected the three changed SVGs. Their cue text and coordinates agree with this intended placement. The ZH SVG supplies **“横向滚动查看覆盖率和全部列 →”** at the same x=16 / y=320 location, with the first row still at y=398. The coordinates are local to the narrow frame; the combined plate adds its placement offset.

**Scope of closure:** The discoverability and static-reference consistency defect is resolved. This does not prove actual table scrolling or rendered Chinese glyph metrics. The existing CJK render qualification remains open; it is not a reason to leave the English static placement defect unresolved.

No new overlap or other local visual defect was observed in the changed English frames. No broader visual re-audit was performed.

## Retained dispositions and conditions

- **VTC-001 through VTC-006:** Retain their frozen repair-pass dispositions, resolved in the supplied static visual evidence within the stated scope.
- **VTC-007:** Now resolved as described above.
- **T01:** Retains its improved static comparison judgment; the narrow overflow-cue condition is now closed.
- **T05:** Remains UNKNOWN for actual keyboard, touch, scrolling, virtualization and 400% zoom operation. This static cue repair does not change that qualification.
- All other task judgments and limits remain as recorded in `taste-repair-pass.md`.

**PASS_WITH_CONDITIONS remains the overall advisory adoption verdict.** Its remaining conditions are qualification and integration conditions, not an open VTC visual correction:

1. Editable Paper construction/readback and the jointly versioned F01/F02 composition remain separate required evidence.
2. Browser rendering, real input, focus/scroll return, responsive behavior, true 400% zoom, CJK typography and the relevant accessibility modes remain unverified.
3. Complete domain capability preservation and real source, entitlement, save/readback and export behavior remain with their existing owners and require their own evidence.
4. Admitted independent RIG review and the designated design-authority verdict remain required; this native advisory report does not supply them.

The separate Options CSS density correction is outside this taste follow-up's scope. It was included in manifest identity validation but was not interpreted or executed here. No disposition from another critic is adopted.

## Preservation and review boundary

The three earlier reports were rechecked and remain unchanged:

| Report | SHA256 |
| --- | --- |
| `taste-first-pass.md` | `6a63ee8bb01d1b37634712ce2d5986ee26b04d906df647bdbb85aee225e3efc3` |
| `taste-rationale-pass.md` | `1b1e80990431ca337bb27ee5aeca738b0b9dbfd1205816a15c269ee1546ba8d7` |
| `taste-repair-pass.md` | `8bf57d9891d6f38aba45a3d6f840cfbd1e5211d92fcb633f432879d25671b3fd` |

Only the follow-up packet, manifest identity, affected mobile frames/coordinates and prior-report hashes were inspected for this pass. No peer report was read, no browser/Paper/HTML rendering or real-service operation was run, and no candidate file was edited.

**Final scoped result: VTC-007 is closed. The improved first-row position is preserved. No VTC visual finding remains open; mandatory qualification conditions remain.**

