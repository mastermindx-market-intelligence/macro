# OIF P1-P6 family preregistration V1: inputs addendum

Status: DISCLOSURE ONLY. This addendum changes no requirement, member, target,
feature, algorithm, loss, block length, margin, seal, multiplicity rule, holdout
boundary, gate, falsifier or prohibition of the preregistration. It corrects the
record of what the authoring lane received and of what the framing orchestrator
(ORCH-1) read before the seal. `OIF_P1_P6_FAMILY_PREREG_V1.md`,
`OIF_P1_P6_FAMILY_PREREG_V1.seal.json` and `OIF_P1_P6_FAMILY_PREREG_V1.audit.md`
are not edited.

Cite the seal only together with the audit and this addendum:

| Artifact | Identity |
| --- | --- |
| Sealed document `OIF_P1_P6_FAMILY_PREREG_V1.md` | document_sha256 `aea58e59bf9d2af190a603640a7039c35bed5dcb842fc6ec6e77cb0b613fb0cd`, 35641 bytes, sealed_at_utc 2026-11-01T08:40:21Z |
| Seal record `OIF_P1_P6_FAMILY_PREREG_V1.seal.json` | sha256 `f68d28089e5e8aba79f4f219db57b4b0690259bb2dc95d0c379a4e08c851812d`; seal commit `2a97665844be80c8a52a829c26dfb9511b139c0f` |
| Audit `OIF_P1_P6_FAMILY_PREREG_V1.audit.md` | sha256 `e86d5fa5b0837910ef3510b2beb1010bde0805f9b4e69f19671d381ca0c120df` at commit `a34f3ec28a387711e2e44b285f540c159709d476` |
| This addendum | sha256 recorded in the PR #10390 description and in the source research census of PR #10395 (a file cannot carry its own hash) |

Every repository input is at commit `021af584204c9fb00ad516c2dbc9467503a84083`.

## A. What the authoring lane received (EXACT bytes)

### A.1 Identity and byte sources

OBSERVED. The authoring lane `oi1-l3a-r1` (Mastermind Fabric, task_class
`fix_build`, root `a1c77f0e-56b9-4edf-8d4f-3d31a338a8ed`, parent
`oi-a1c77f0e-orch1`) received exactly one packet. Its Fabric request artifact
(schema `mastermind.fabric_request_artifact.v1`, created
2026-11-01T08:30:34.879518Z) records packet_sha256
`89fa190bbcb98cc003ef23e7f11767285b115e3f179af35fa6aa458dd897e6ae`. Two
independently held copies of the packet bytes hash to that value:

1. Fabric's retained request packet `oi1-l3a-r1.request.packet` in the Fabric
   adapter's remote_sub state directory on the M2 host (outside the repository).
2. ORCH-1's scratch copy `packets/oi1-l3a-r1.txt`, written when the packet was
   built (session scratch, outside the repository).

Both copies: sha256 `89fa190bbcb98cc003ef23e7f11767285b115e3f179af35fa6aa458dd897e6ae`,
145680 bytes, 631 lines. Neither copy is committed. The packet is a
deterministic function of the header in A.3 and three repository blobs, and
section E rebuilds it byte for byte from this file and the repository.

The ORCH-1 rulings F1-F14 and the lane frame are therefore EXACT, not
reconstructed.

### A.2 Packet layout

| Packet lines | Content | Identity |
| --- | --- | --- |
| 1-119 | Lane frame and ORCH-1 rulings (the header); line 119 is blank | sha256 `664c610ef83d6c0e3d1b4fae20dcf0d587e8450e8784391e922c4465b1c309fa`, 15636 bytes |
| 34 | Heading "FROZEN SPEC (ORCH-1 rulings; binding; do not re-decide them):" | inside the header |
| 36-96 | Rulings F1-F14 (F1 :36, F2 :41, F3 :43, F4 :45, F5 :54, F6 :64, F7 :66, F8 :73, F9 :75, F10 :77, F11 :86, F12 :88, F13 :94, F14 :96) | sha256 `35f1cc2d6cfcdd4c79eaf1f68084aeef1cb7475bd5256eee09cbc274a89ba463`, 9965 bytes |
| 120 | BEGIN marker for R21 | |
| 121-550 | R21 bytes, verbatim | blob `db8c9ce40b46a1e5cefc7983ded5c6faedc3cfb0` |
| 551-552 | blank separator line; END marker for R21 | |
| 553 | BEGIN marker for R22 | |
| 554 | R22 re-serialised on one line (JSON separators `,` and `:`, non-ASCII kept), same JSON value as the blob | this line with its newline: sha256 `511050c4204f72df78ff0b2666aba50855de208e9ce31cfa059c9980e7a83738`, 57344 bytes |
| 555-556 | blank separator line; END marker for R22 | |
| 557 | BEGIN marker for R23 | |
| 558-629 | R23 bytes, verbatim | blob `5b5c6e5770481d568f458f867629d6b9ad58465e` |
| 630-631 | blank separator line; END marker for R23 | |

### A.3 Packet header, packet lines 1-119, verbatim

The fenced block below holds packet lines 1-119 exactly, including the blank
line 119. The two fence lines are not part of the packet.

```text
ROUTE: draft
MODEL/TIER: Fabric fix_build lane, complexity C1_ROUTINE_BOUNDED (router-placed). Author lane for a blind preregistration.
OPERATION KEY: options-intelligence / ORCH-1 / oi1-l3a-r1 (track E, AC28-AC35)

OPERATION IDENTITY (binding; copy into your return):
- Original root: a1c77f0e-56b9-4edf-8d4f-3d31a338a8ed (Options Intelligence CEO seat). Immediate parent: oi-a1c77f0e-orch1 (ORCH-1, Opus orchestrator). You are a LEAF worker: you may not request, spawn or delegate to any other worker, model, agent or lane.
- Repository commit of every input below: 021af584204c9fb00ad516c2dbc9467503a84083 (mastermindx-market-intelligence/macro, origin/main observed 2026-11-01T08:20Z).

BLINDNESS RULE (this lane exists to author a preregistration blind to outcomes; a violation voids the lane):
- Your ONLY sources are the INPUTS inlined at the end of this packet. You have NO repository access in this lane: do not run git, gh, curl, wget, pip, python package downloads, or any network command; do not open, cat, grep, find or list any file or directory except the temp directory you create with mktemp -d and the files you write into it.
- Allowed commands: mktemp, writing your two deliverable files (shell heredoc or a short python3 -I script that only writes inside your temp dir), wc, sha256sum or shasum -a 256, date -u, cat of YOUR OWN two files, python3 -I -c 'import json; json.load(open(<your seal file>))' to validate JSON.
- Your retained Fabric log will be audited for any other read.

FORBIDDEN EFFECTS (absolute): no write to any repository, branch, PR, issue, label, review, comment, Slack, Linear or external service; no disk reclaim (rm only inside your own temp dir); no credential act (never read .env, keychains, tokens, API keys); no ssh/scp; no host selection; no paid API call; no predictive, ranking, sizing or trade language.

CLAIM DISCIPLINE: every requirement in the document must trace to a quoted INPUT sentence (give R21 section) or to an ORCH-1 ruling in FROZEN SPEC (give F-number). Do not invent facts, dates, data availability, sample sizes or owners. Missing is not zero.

MISSION: The stage-S0 sealed family-binding preregistration for the six OIF pilots (P1-P6) as one family, plus its sha256 seal record, authored blind to outcomes.

WHY: The six pilots exist only as a PRINCIPAL_PROPOSAL design (R21). Acceptance rows AC28-AC35 need one sealed document that binds them as one family with stage-specific seals, family-wise multiplicity, a holdout boundary and per-study falsifiers, before any outcome can be read. An independent Fabric reviewer on a different pool/model will attack your document; findings come back to you or a repair lane.

AUDIENCE: research principal and the independent reviewer; later implementers of stages S1-S3.

SCOPE: Write exactly the two files in FROZEN SPEC F1, from INPUTS only, following F2-F14.

OUT OF SCOPE: Choosing or changing any numeric design value in R21 (block lengths, margins, bootstrap counts, N limits): quote them, never alter them. Filling any empirical date, N, dataset manifest or gate. Reading anything outside INPUTS. Committing, pushing or opening a PR (ORCH-1 does that).

INPUTS: inlined below between BEGIN/END markers: R21 (PILOT_STUDY_SPEC_V1.md, blob db8c9ce40b46a1e5cefc7983ded5c6faedc3cfb0), R22 (pilot-study-spec.v1.json, blob fc00aa33b11c26be9fa0ca6a4b7c0280f73dab81, minified, same content), R23 (PRINCIPAL_DECISIONS_20261003.md, blob 5b5c6e5770481d568f458f867629d6b9ad58465e). These are design documents; they contain no outcome values.

OWNED FILES: only the two files of F1 inside your own mktemp -d directory.

CONSTRAINTS: the BLINDNESS RULE above; FROZEN SPEC F1-F14.

FROZEN SPEC (ORCH-1 rulings; binding; do not re-decide them):

F1. Deliverables (exactly two files, written in a temp dir you create with mktemp -d):
    (a) OIF_P1_P6_FAMILY_PREREG_V1.md   -- the frozen prereg text (UTF-8, LF line endings, final newline).
    (b) OIF_P1_P6_FAMILY_PREREG_V1.seal.json -- the seal record.
    Their committed home will be research/options_intelligence/2026-11-01/ (ORCH-1 commits them; you do not).

F2. Stage. This document is the stage-S0 FAMILY BINDING: it fixes family identity, members, targets, eligibility rules, stage-seal protocol, multiplicity, holdout boundary, falsifiers and prohibitions. It is NOT an accepted G3 preregistration of dates, NOT fitting/evaluation authority, NOT a power claim, NOT a promotion. All empirical dates stay null (copy R21 §7 null date block). State this in a Status line at the top.

F3. Family. Family id: OIF-PILOT-FAMILY-V1. Exactly six members, fixed, never shrinking: P1 OIF01, P2 OIF04, P3 OIF19, P4 OIF22, P5 OIF13, P6 OIF35 (from R21 "Frozen proposals" table). Map each to its acceptance row: P1->AC30, P2->AC31, P3->AC32, P4->AC33, P5->AC34, P6->AC35. A blocked, unrun or invalid member keeps p=1 (R21 §8).

F4. Targets (one section per pilot). Use R21 §6 exact definitions; quote the R21 sentence that defines the target, the primary feature, the algorithm/loss, the block length (R21 §8 block lengths) and the screening margin (R21 §8 margins, keep its PRINCIPAL_PROPOSAL status). ORCH-1's row labels are:
    AC30/P1: exact interval range label (next 30-minute exact log high/low range).
    AC31/P2: signed-flow residual log-total-return target (next 30-minute market/sector residual log return).
    AC32/P3: H20 variance (matched 20-session ACT/365F variance).
    AC33/P4: borrow-adjusted call-put IV spread with a skipped (one-session skip) residual log-return target.
    AC34/P5: ETF fixed-inventory / shock-endpoint hedge-notional variance study (next ten-minute ACT/365F variance; one fixed inventory/shock scalar).
    AC35/P6: raw relative spread plus ACTUAL full-fill cost within 60 seconds, conditional on actual complete fills.
    Where a row label and R21's text differ in any substantive way (for example "log-total-return" vs "log return"), quote R21, keep R21's definition, and list the difference in GAPS. Never silently reconcile.

F5. Per-study eligibility and falsifiers. In each pilot section include the row's required witness and falsifier verbatim (table below) and state the pilot is VOID (p=1, recorded as invalid, never re-run under v1 with a changed rule) if its falsifier is observed:
    AC28 (population/history, all pilots) | witness: original PIT cohort and availability receipts | falsifier: current board used as historical universe
    AC29 (stage seals, all pilots) | witness: training, then frozen validation; mature losses; fixed test N before test outcomes | falsifier: power required before its inputs exist, or test outcomes used to plan N
    AC30/P1 | witness: eligible events or exact interval aggregate | falsifier: a boundary-overlapping bar supplies extrema
    AC31/P2 | witness: strict quote/package/Greek and sector benchmark qualification | falsifier: ask-side estimate called opening demand
    AC32/P3 | witness: causal HAR/RI forecasts, matched units, mature labels | falsifier: volatility residual treated as variance/probability
    AC33/P4 | witness: Friday/calendar rule and one-session skip | falsifier: formation-to-entry return included, or date shifted opportunistically
    AC34/P5 | witness: numerical domain and fixed ETF population | falsifier: assumed exposure relabeled actual dealer holdings
    AC35/P6 | witness: independent fills/fees for a frozen full-fill population | falsifier: NBBO or simulation used as actual fills

F6. Population and history (AC28). The historical universe at every formation clock comes only from point-in-time cohort and availability receipts (R21 §1). The current board or any current cohort (including the 26-root core cohort observed in live_flow.meta/v2 on 2026-10-30) is never the historical universe. Development, training, validation and untouched-test histories are separate and never overlap (R21 §7 purge rule with exact [label_start,label_end] intervals). Any data already observed by any party before the S3 seal (including #8286's 2017-2025 outcomes, per R21) is development evidence, never untouched holdout.

F7. Stage-specific seals (AC29). Define four seals, each a sha256 over a frozen artifact recorded BEFORE the next stage reads any data of that stage:
    S0 family binding = this document (seal in the .seal.json).
    S1 training seal = exact training window, dataset manifest, features, nuisance/scaler procedure, algorithm per R21 §4, before any fit.
    S2 frozen-model seal = fitted models/scalers frozen at training_fit_cutoff, before any validation label is read.
    S3 test seal = after ALL validation labels used for planning have matured: run R21 §8 power rule on validation losses only; fix each pilot's N inside the 126..504 NYSE-session planning limits (if required N > 504, the pilot is INFEASIBLE_UNDERPOWERED under v1, p=1); fix test_start; before any test-window outcome exists or is viewed.
    Power is never computed or required before its inputs (matured validation losses) exist; test outcomes are never used to plan N. No interim efficacy looks, no automatic refits, no post-validation refit in v1 (R21 §7). A changed algorithm is a new version with a new untouched test.

F8. Multiplicity. Holm step-down over the six one-sided p-values exactly as R21 §8: sort ascending, ties by pilot id, reject while p_(k) <= .05/(7-k), k=1..6, stop at first failure; family-wise alpha .05; unrun/blocked/invalid = p=1; the family never shrinks; the #8286 BH family is a different family; no alpha recycling. Quote R21's bootstrap/test/randomness definitions by section reference rather than restating them, and state that R21 §8 text at blob db8c9ce40b46a1e5cefc7983ded5c6faedc3cfb0 is incorporated by reference and bound by this seal.

F9. Holdout boundary. The untouched test window for each pilot begins at the first full NYSE session after BOTH its S3 seal and acceptance of all gates G0-G6 (R21 §9). No session on or before the S3 seal timestamp may enter any test window. Operational source failures during the test are recorded without viewing comparative losses; pausing cannot select days (R21 §7).

F10. Prohibitions (state each as a numbered rule):
    - No calibration floor: calibration is UNAVAILABLE under the accepted D13/Q01 O-A decision; no newly invented support floor; no derived S1 support floor is imposed on the six pilots.
    - No universal sample floor: R21 §7 fit-domain minima are carried only as per-pilot PRINCIPAL_PROPOSAL fit-domain eligibility, explicitly not a universal sample floor, not a sufficiency claim and not a power guarantee; N comes only from the S3 power rule.
    - No P6 simulated fill: catalogue quote coverage and simulated hedged markouts are diagnostics only; if actual complete fills are unavailable, P6 is unrun with p=1 and never becomes a simulation-trained cost model (R21 P6 disposition). NBBO is never a fill.
    - No promotion: no member result promotes a model, signal or product state; decision utility or policy promotion requires separate stakeholder costs and authority (R21 §8 margin status).
    - No dealer predictive claim (P5 measures an assumed fixed inventory/shock scalar, never actual dealer holdings).
    - No ranking, sizing or trade language anywhere in the document.
    - #8286 registered nulls are preserved; #8385 (REVISE) stays with its original author; this document reruns nothing.

F11. Gates. Copy R21 §9 gates G0-G6 as OPEN (owner, required evidence, blocked claim) and the "Still unbound" list verbatim. This document fills none of them.

F12. Blindness statement (a section titled "Blindness and how it was enforced"), stating as fact only what is true:
    - Authored by Mastermind Fabric lane oi1-l3a-r1 (leaf; root a1c77f0e-56b9-4edf-8d4f-3d31a338a8ed; parent oi-a1c77f0e-orch1) from INPUTS inlined in its packet: R21 PILOT_STUDY_SPEC_V1.md blob db8c9ce40b46a1e5cefc7983ded5c6faedc3cfb0, R22 pilot-study-spec.v1.json blob fc00aa33b11c26be9fa0ca6a4b7c0280f73dab81, R23 PRINCIPAL_DECISIONS_20261003.md blob 5b5c6e5770481d568f458f867629d6b9ad58465e, all at repository commit 021af584204c9fb00ad516c2dbc9467503a84083.
    - The authoring lane was forbidden from reading any repository, data store, results/outcome table, report artifact, parquet/csv file or network resource; its packet contained no outcome, untouched-test or holdout values.
    - The framing orchestrator read specification documents only and no outcome tables before this seal.
    - Enforcement is audited after the fact: ORCH-1 inspects the lane's retained Fabric log for any read outside the inlined inputs, and an independent Fabric review on a different pool/model attacks the document and the blindness claim. (Do not claim the audit result; it does not exist yet.)

F13. Seal record (.seal.json), keys exactly: schema ("oif.family_prereg_seal/v1"), family_id, stage ("S0_FAMILY_BINDING"), document ("OIF_P1_P6_FAMILY_PREREG_V1.md"), document_sha256 (lowercase hex of the exact bytes of file (a)), document_bytes (int), sealed_at_utc (from `date -u +%Y-%m-%dT%H:%M:%SZ` when you hash), repository_commit ("021af584204c9fb00ad516c2dbc9467503a84083"), inputs (list of {ref, path, blob}), authoring_lane ("oi1-l3a-r1"), blindness ({method, forbidden_reads, audit:"pending ORCH-1 log audit + independent Fabric review"}), empirical_dates_bound (false), authority_boundary (one sentence: no fitting/evaluation/promotion authority). Compute the hash with `sha256sum` or `shasum -a 256` on the final file (a) and do not edit (a) afterwards.

F14. Length and form: plain Markdown, headings numbered 0-12, no HTML, no emojis, target 250-450 lines (do not paste R21 wholesale; reference its sections). Neutral scientific language.

NOT DONE UNLESS:
  - Both files exist; the .md has numbered sections 0-12 covering F2-F12, with one section per pilot P1-P6 carrying target, feature, algorithm/loss, block length, margin, witness and falsifier.
  - Every one of the F10 prohibitions appears as a numbered rule.
  - The .seal.json parses as JSON, has exactly the F13 keys, and its document_sha256 equals the sha256 you computed on the final .md (show the command and its output).
  - The full text of BOTH files is in RESULT, each between lines "=== FILE: <name> sha256=<hex> bytes=<n> ===" and "=== END FILE ===", byte-exact (ORCH-1 recomputes the hash on what you return; any mismatch rejects the lane).
  - GAPS lists every place a row label differed from R21, and every F-rule you could not satisfy from INPUTS.

EVIDENCE REQUIRED: your full command list in order; the hash command and output; wc -l and wc -c of both files.

BUDGET: about 25 tool calls. If exhausted, return PARTIAL with whatever complete files you have.

ANSWER FIRST: the document_sha256 of the final .md and its byte count.

RETURN: your final message IS the return packet, with exactly these top-level labels in this order:
STATUS: DONE | PARTIAL | BLOCKED
RESULT: <the deliverable, in the exact shape the packet's FROZEN SPEC / QUESTIONS demand>
EVIDENCE: <every command you ran that the result depends on, with the key output line(s); paths with sha; counts>
GAPS: <everything you could not establish, with the exact observed reason; "none" only if truly none>
DEVIATIONS: <every departure from this packet; "none" if none>

Do not end a turn until you are emitting the return packet. If you catch yourself writing "now let me…" or "next I'll…", either keep going in the same turn or stop and return what you have. A partial packet with honest, specific GAPS is useful and I can act on it; another status note is not. Answer the ANSWER FIRST question before anything else.

```

## B. Corrected inputs list

### B.1 Full paths for the bare file names in the seal record

The seal record's `inputs` entries (`ref` at seal.json:12, :17 and :22) carry
bare file names in `path` (seal.json:13, :18 and :23). The blob ids there are
correct. Full repository paths at commit `021af584204c9fb00ad516c2dbc9467503a84083`:

| Ref | Full path | Blob | sha256 of the blob bytes | Lines / bytes | As delivered |
| --- | --- | --- | --- | --- | --- |
| R21 | `research/options_intelligence/2026-10-03/PILOT_STUDY_SPEC_V1.md` | `db8c9ce40b46a1e5cefc7983ded5c6faedc3cfb0` | `f439d6df16f5437ce6bf996fefe1df891927f5539ece368d44cbe9098bf971f8` | 430 / 60165 | verbatim |
| R22 | `research/options_intelligence/2026-10-03/pilot-study-spec.v1.json` | `fc00aa33b11c26be9fa0ca6a4b7c0280f73dab81` | `e30796c158da18cffe1b581463ba6820ff33e9acbe8a4248b3fc068e67f70317` | 400 / 60313 | re-serialised on one line, same JSON value (A.2) |
| R23 | `research/options_intelligence/2026-10-03/PRINCIPAL_DECISIONS_20261003.md` | `5b5c6e5770481d568f458f867629d6b9ad58465e` | `3e39c6a8e01bcf3200f810aa7273a0d28efa4f595af188f76a2da61919615895` | 72 / 12136 | verbatim |

The seal is not re-issued; this table is the authoritative path record.

### B.2 Everything the lane received, with upstream sources and classes

The lane had no repository access. The packet is the whole of the
Mastermind-supplied input (see F for the limit of this statement).

Classes used below:
- SPECIFICATION: design text, rules, definitions, or acceptance witness and
  falsifier text.
- DATA-MEMBERSHIP: a fact about which instruments are in a current data set.

| # | Packet part | Upstream source of the bytes | Class | Outcome, untouched-test or holdout value? |
| --- | --- | --- | --- | --- |
| 1 | Lane frame (header lines 1-33 and 98-118) | written by ORCH-1 | SPECIFICATION | none |
| 2 | Rulings F1-F3 and F7-F14 | written by ORCH-1 from R21, R23 and the seat commission. The seat commission supplied the P-to-AC mapping in F3 and, in F10, the D13/Q01 O-A, #8286 and #8385 references | SPECIFICATION | none |
| 3 | F4 row labels (header lines 45-51) | ORCH-1 transcription of the acceptance-matrix `capability` cells for AC30-AC35, plus ORCH-1 glosses (B.3) | SPECIFICATION | none |
| 4 | F5 witness and falsifier table (header lines 55-62) | ORCH-1 transcription of the `required_witness` and `falsifier` cells for AC28-AC35 (B.3) | SPECIFICATION | none |
| 5 | F6 phrase "the 26-root core cohort observed in live_flow.meta/v2 on 2026-10-30" (header line 64), restated at .md:287-288 | a count derived from an incumbent capture (B.4) | DATA-MEMBERSHIP (count only) | none |
| 6 | R21 | repository blob (B.1) | SPECIFICATION | none |
| 7 | R22 | repository blob (B.1) | SPECIFICATION | none |
| 8 | R23 | repository blob (B.1) | SPECIFICATION | none |

About R21 and R22: they carry design values (block lengths, margins, bootstrap
counts and N limits) and name earlier studies by number. ORCH-1's 08:29:46Z scan
of R21, R22 and R23 for outcome values found none.

Statement. No input delivered to the authoring lane held any outcome value,
untouched-test value or holdout value. The only DATA-MEMBERSHIP item is the
size of a current cohort. The packet names no member of that cohort: F6 gives
only the count, and any individual ticker that appears in the packet appears
inside R21 or R23 text.

### B.3 Acceptance-matrix rows (upstream of F4 and F5)

Source: the Chairman package file `09_ACCEPTANCE_MATRIX.csv` (package
`Options_Intelligence_Fable_2026-10-31`; not in the repository), sha256
`376f81629b51f27542481295bd549a6062b749f8500a1fdd5310d0705411648a`, 13416
bytes. ORCH-1 read it at 08:07:40Z and 08:21:56Z.

The rows below are copied byte for byte: file line 1 (the header) and lines
29-36. The lane did not receive the matrix. It received only the F4 and F5
transcriptions, and the `census_state`, `evidence_refs` and `refresh_trigger`
cells were not transcribed.

```csv
"assertion_ref","existing_owner_refs","capability","census_state","required_witness","falsifier","evidence_refs","refresh_trigger"
"AC28","Q03;P1-P6","Causal population/history","EMPIRICAL_BINDING_OPEN","Original PIT cohort and availability receipts","Current board used as historical universe","R21 R22 R23","New qualified history"
"AC29","Q03;P1-P6","Stage-specific power/test seal","NOT_EXECUTED_HERE","Training then frozen validation; mature losses; fixed testN before test outcomes","Power required before its inputs exist or test outcomes used to planN","R21 R23","Designated stage admission"
"AC30","Q04;P1","Exact interval range label","NOT_EXECUTED_HERE","Eligible events or exact interval aggregate","Boundary-overlapping bar supplies extrema","R21 R22","Qualified label source"
"AC31","Q04;P2","Signed-flow residual log-total-return target","NOT_EXECUTED_HERE","Strict quote/package/Greek and sector benchmark qualification","Ask-side estimate called opening demand","R21 R22 W01 W03","Source/empirical seal"
"AC32","Q04;P3","H20 variance","NOT_EXECUTED_HERE","Causal HAR/RI forecasts matched units and mature labels","Volatility residual treated as variance/probability","R21 R22 R23","Qualified history and seal"
"AC33","Q04;P4","Borrow-adjusted call-put IV spread and skipped residual log-return target","NOT_EXECUTED_HERE","Friday/calendar rule and one-session skip","Formation-to-entry return included or date shifted opportunistically","R21 R22","Qualified cohort and seal"
"AC34","Q04;P5","ETF fixed-inventory/shock endpoint hedge-notional variance study","NOT_EXECUTED_HERE","Numerical domain and fixed ETF population","Assumed exposure relabeled actual dealer holdings","R21 R22 W04","Qualified model/source and seal"
"AC35","Q04;P6","Raw relative-spread and actual fill-cost study","NO_ACTUAL_FILL_EVIDENCE_ADDED","Independent fills/fees for frozen full-fill population","NBBO or simulation used as actual fills","R21 R22 R23","Qualified execution records"
```

F5 against the matrix. These are wording and punctuation differences only.
None changes a witness or falsifier condition.
- The leading capital of each cell is lowercased, except "Friday" and "NBBO".
- AC29 witness: "Training then frozen validation ... fixed testN" became
  "training, then frozen validation ... fixed test N".
- AC29 falsifier: "planN" became "plan N", and a comma was added before
  "or test outcomes".
- AC30 falsifier: "Boundary-overlapping" became "a boundary-overlapping".
- AC32 witness: "Causal HAR/RI forecasts matched units and mature labels"
  became "causal HAR/RI forecasts, matched units, mature labels".
- AC33 falsifier: a comma was added before "or date shifted opportunistically".
- AC35 witness: "for frozen full-fill population" became "for a frozen
  full-fill population".
- AC28, AC31 and AC34 differ from the matrix only in the leading capital.

F4 against the matrix `capability` cells.
- AC33: "and skipped" became "with a skipped (one-session skip)".
- AC34: "fixed-inventory/shock endpoint" became "fixed-inventory /
  shock-endpoint".
- AC35: "Raw relative-spread and actual fill-cost study" became "raw relative
  spread plus ACTUAL full-fill cost within 60 seconds, conditional on actual
  complete fills".
- The parenthetical glosses on AC30-AC34 were written by ORCH-1.

F4 instructs the lane to quote R21, to keep R21's definition wherever a label
differs, and to list each difference. The sealed document follows R21.

### B.4 Source of the F6 cohort count (.md:287-288)

OBSERVED. The count comes from a capture written by the incumbent Options
Intelligence session (f77d3f70) in its own scratch area:

| Property | Value |
| --- | --- |
| File | `flow_meta_20261101T043626Z.json` |
| Schema | `live_flow.meta/v2` |
| asof | 2026-10-30T20:11:27.962419Z |
| sha256 | `c03eab46584b0c5ddd9efee32834b61c2423bd1952002dfe536164e0d77dd9db` |
| Size | 193559 bytes |
| Read by ORCH-1 | 2026-11-01T08:11:17Z |

That read printed only the following:
- schema and asof;
- roots_configured;
- the length and keys of root_catalog;
- the core list;
- the tier counts (core 27, rotating 3).

A byte-exact copy is committed in PR #10395 at
`research/receipts/options_intelligence/flow_meta_20261101T043626Z.json`.

CALCULATED. 26 is the 27 core-tier entries minus QQQ. This follows the
incumbent's cohort definition, which ORCH-1 found by grep at 08:11:07Z in the
incumbent's `falsify.py` (line 54; file sha256
`0491ec3b68895bfe6fd37af12d941b0a0ae77e4c3432015ded2edbc190d0287d`):
`core = [r["root"] for r in meta["root_catalog"] if r.get("tier") == "core" and r["root"] != "QQQ"]`.

The capture also holds per-root `observed_statistics` for the 2026-10-30
session, such as print counts and contract volumes. The 08:11:17Z read did not
print them, and nothing from them entered the packet. They count observations in
the current session; they are not P1-P6 outcome, test or holdout values.

## C. Correction to .md:439 (what the framing orchestrator read before the seal)

.md:439 reads: "The framing orchestrator read specification documents only and
no outcome tables before this seal." That sentence is incomplete. The corrected
record follows; the sealed bytes are not edited.

Before the seal (sealed_at_utc 2026-11-01T08:40:21Z), ORCH-1 read
specification documents and the non-outcome items listed below. It read no
outcome value, untouched-test value or holdout value.

The 08:39:17Z schema and row-count reads recorded at audit.md:43-52 are
non-outcome reads. They are the `flow_signals` gate.json fields and the parquet
column schemas and row counts. The seal is cited only together with that audit
and this addendum.

The statement at .md:438 still holds: "its packet contained no outcome,
untouched-test or holdout values". It is qualified by B.2: the packet also
carried one DATA-MEMBERSHIP count (item 5).

| Time (UTC, 2026-11-01) | Read | Class | Reached the lane? |
| --- | --- | --- | --- |
| 08:06-08:10 | incumbent programme ledger copy, by line range (programme status text) | SPECIFICATION (status text) | no |
| 08:07:40, 08:21:56 | acceptance-matrix rows (B.3) | SPECIFICATION | as the F4 and F5 transcriptions |
| 08:11:07 | grep of the incumbent `falsify.py` for the cohort definition (B.4) | SPECIFICATION (code) | no |
| 08:11:17 | live_flow.meta/v2 capture: schema, asof, roots_configured, catalog length and keys, core list, tier counts (B.4) | DATA-MEMBERSHIP | the count only, through F6 |
| 08:14:01 | identification of the Theta host and terms-source code | SPECIFICATION (code) | no |
| 08:26:16 | headings and blob ids of R21, R22 and R23 | SPECIFICATION | these are the inputs |
| 08:29:46 | scan of R21, R22 and R23 for outcome values (none found) | SPECIFICATION | these are the inputs |
| 08:30:34.879518 | packet fixed: request artifact created with packet_sha256 `89fa190b...` | - | - |
| 08:38:37 | listing of baseline file names (names only) | metadata | no |
| 08:38:48-08:38:54 | OA3 runbook text; top-level keys of `gate.json` | SPECIFICATION; metadata | no |
| 08:39:17 | `flow_signals` gate.json schema, asof, status, elapsed_sec and key layout; parquet column schemas and row counts (audit.md:43-52) | metadata | no |
| 08:40:21 | seal (the lane's own hash time) | - | - |

INTERPRETED. Reads after 08:30:34.879518Z could not reach the lane, for two
reasons:
- The packet was fixed at that time: its hash was recorded at creation and both
  copies match it.
- ORCH-1 sent the lane nothing after the packet, and the lane had no repository
  access.

## D. Transcription differences against R21

| .md line | R21 location | Difference | Classification |
| --- | --- | --- | --- |
| 300 | R21 line 22, paraphrased through F6 (header line 64) | "2017-2025" uses U+002D HYPHEN-MINUS; R21 has U+2013 EN DASH ("2017–2025"). The paraphrase follows F6, which used a hyphen | transcription difference |
| 301 | R21 line 22, quoted | the quoted "2017-2025" uses U+002D where R21 has U+2013 | transcription difference |
| 296 | R21 line 338 ("Purge"), quoted | "[label_start, label_end]" has a space after the comma; R21 has "[label_start,label_end]" | transcription difference |

None of these differences changes a requirement. Under the document's own rule
(F4: keep R21's definition), the R21 bytes govern.

Mechanical quote check (a heuristic, not a complete audit; whitespace, dashes
and backticks normalised). The pairing heuristic splits the quoted spans in the
sealed document into three groups:
- 58 match R21, R22 or R23 exactly.
- 11 match only after normalisation. These are the quotes beginning at .md lines
  23, 98, 128, 160, 185, 218, 244, 254, 284, 293 and 301; the causes are dash
  normalisation, inserted backticks and comma spacing.
- 33 are unmatched and not adjudicated, because the heuristic mispairs quotation
  marks and also captures row labels and paraphrase.

No exactness claim is made beyond the 58.

## E. Reproduction

From a checkout that contains commit `021af584204c9fb00ad516c2dbc9467503a84083`,
save the script below as `rebuild_packet.py` outside the repository and run:

`python3 -I rebuild_packet.py <path to this addendum> <repository path>`

Expected output:

```
header 664c610ef83d6c0e3d1b4fae20dcf0d587e8450e8784391e922c4465b1c309fa 15636
f1_f14 35f1cc2d6cfcdd4c79eaf1f68084aeef1cb7475bd5256eee09cbc274a89ba463 9965
packet 89fa190bbcb98cc003ef23e7f11767285b115e3f179af35fa6aa458dd897e6ae 145680
```

```python
import hashlib, json, subprocess, sys

addendum, repo = sys.argv[1], sys.argv[2]
C = "021af584204c9fb00ad516c2dbc9467503a84083"

lines = open(addendum, encoding="utf-8").read().split("\n")
s = lines.index("```text")
e = lines.index("```", s + 1)
header = ("\n".join(lines[s + 1:e]) + "\n").encode("utf-8")
print("header", hashlib.sha256(header).hexdigest(), len(header))
f1_f14 = ("\n".join(header.decode("utf-8").split("\n")[35:96]) + "\n").encode("utf-8")
print("f1_f14", hashlib.sha256(f1_f14).hexdigest(), len(f1_f14))


def blob(path):
    return subprocess.run(["git", "-C", repo, "show", C + ":" + path],
                          check=True, capture_output=True).stdout


base = "research/options_intelligence/2026-10-03/"
r21 = blob(base + "PILOT_STUDY_SPEC_V1.md")
r22 = json.dumps(json.loads(blob(base + "pilot-study-spec.v1.json")),
                 separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
r23 = blob(base + "PRINCIPAL_DECISIONS_20261003.md")

out = header
out += (b"===== BEGIN INPUT R21 PILOT_STUDY_SPEC_V1.md (blob db8c9ce40b46a1e5cefc7983ded5c6faedc3cfb0) =====\n"
        + r21 + b"\n===== END INPUT R21 =====\n")
out += (b"===== BEGIN INPUT R22 pilot-study-spec.v1.json (blob fc00aa33b11c26be9fa0ca6a4b7c0280f73dab81; minified) =====\n"
        + r22 + b"\n===== END INPUT R22 =====\n")
out += (b"===== BEGIN INPUT R23 PRINCIPAL_DECISIONS_20261003.md (blob 5b5c6e5770481d568f458f867629d6b9ad58465e) =====\n"
        + r23 + b"\n===== END INPUT R23 =====\n")
print("packet", hashlib.sha256(out).hexdigest(), len(out))
```

## F. Limits

- The authoring lane's remote model also received its Fabric harness and
  provider-side instructions. Those bytes are not retained in the request
  artifacts named in A.1. "Everything the lane received" in B.2 therefore means
  everything Mastermind supplied, which is the packet.
- The acceptance matrix (B.3) is a package file outside the repository. It is
  identified by sha256, and its relevant rows are copied above.
- The audit's limits on the lane-log review stand as stated in the audit; this
  addendum does not restate or widen them.
- This addendum is not a review. It adds no review verdict, and the blindness
  audit field in the seal record is unchanged.
