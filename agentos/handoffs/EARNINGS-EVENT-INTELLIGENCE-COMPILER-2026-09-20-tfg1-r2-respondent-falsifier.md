---
workstream: "WS:EARNINGS-EVENT-INTELLIGENCE-COMPILER"
session: opus/tfg1-r2-transcript-format-hardening-20260920
model: opus
ended_because: blocked
mission: >
  Implement the frozen TFG-1 R2 source-native separator/proxy/role law generically, prove it
  against the ratified 16-call development truth without weakening source-supported identity,
  and stop before the sealed holdout if any development gate fails.
state_before: >
  TFG-1 v1 terminated at an accepted development-gold falsifier; its closeout PR #6555 merged as
  0b839e1926d9b8c9423cb6bf232b719bbeedd4db. TFG-1 R2 was NOT_BUILT with no open successor PR.
  The ratified R2 truth is 113 separators / 97 direct / 6 proxy / 103 supported / 10 unresolved,
  9 source-clean calls and 7 expected-refusal calls. The eight holdout revisions (ranks 17-24)
  were sealed with holdout_bodies_inspected = 0.
prs:
  - 7530
decisions:
  - DEC:E3FMT-STRUCTURAL-SEPARATORS-PROXY-IDENTITY-AND-SOURCE-CONDITIONED-HOLDOUT
  - DEC:E3FMT-DEVELOPMENT-GOLD-R2-FIRST-HANDOFF-OMISSIONS
  - DEC:E3C-GOOGL-OOS-REFUSAL-SPENDS-EVENT
changed:
  - path: engine/company_intelligence/qa_source_identity.py
    what: >
      New internal helper carrying the frozen source-native law: question-bearing named handoff
      separators with zero terminal-cue authority, three-state questioner resolution
      (direct / explicit full-name proxy / unresolved), and same-revision participant/title
      evidence for respondent roles. No ticker, issuer, provider or boundary-index literal.
  - path: engine/company_intelligence/qa_reconstruction.py
    what: >
      Boundary detection now delegates to the R2 separator law instead of the literal "go ahead"
      cue; questioner identity uses the three-state resolver and refuses speaker_unresolvable;
      management may be roleless when the same revision declares a title, emitting the frozen
      extended respondent with qa_respondent_identity_evidence.v1 role_source_spans; explicit
      segment-role vs declared-title contradiction refuses management_identity_conflict.
  - path: tests/test_company_intelligence_qa_source_identity_tfg1_r2.py
    what: 32 hostile-format discriminators for the R2 law (dialects, proxies, title bleed, aliases, pathology).
  - path: research/earnings_intelligence/e3/tfg1_r2_development_respondent_falsifier_receipt.json
    what: The measured negative result and both findings.
verified:
  - claim: "The R2 separator and questioner law reproduces the ratified development truth exactly."
    command: "Per-call index-set comparison of all 16 held revisions against the R2 gold."
    result: >
      113/113 separators, 97/97 direct, 6/6 proxy, 103/103 supported, 10/10 unresolved — exact set
      equality per call, not merely matching totals. Canonical-JSON replay 16/16.
  - claim: "AAPL production behaviour is unchanged."
    command: "reconstruct_qa on the held AAPL FY2026 Q3 revision at the frozen oracle SHA."
    result: >
      Boundaries [32,42,52,63,76,84,97]; 7 exchanges / 26 answer turns / 68 replay spans; zero
      extended respondents. Identical to the E3-A2 receipt.
  - claim: "The 9/7 publish-refuse partition is derived from source, not asserted."
    command: "Refuse iff any separator has an unresolved questioner or any answering speaker's segment role contradicts a declared title."
    result: "Derives exactly the ratified nine-call clean set. No ticker or index literal is involved."
  - claim: "FANG/2026Q2 cannot produce a full-call reconstruction under the frozen respondent law."
    command: "Exhaustive search of the FANG revision for any declaration binding the segment-92 speaker."
    result: >
      The IR roster at segment 1 names exactly four participants. Chad McAllaster answers at
      segment 92 with an empty segment role, and the only two mentions of him anywhere in the
      revision are first-name-only with no title. Refusal is mandatory.
  - claim: "FANG is the only source-clean call with this property."
    command: "Audit of undeclared management answerers inside Q&A windows across all 16 calls."
    result: "One collision. The other eight source-clean calls have zero undeclared answerers."
unverified:
  - claim: "The eight-slot holdout passes the R2 compiler."
    what_would_verify: >
      Only a corrected, Sol-ratified development bar that is fully green against a frozen
      implementation head, followed by the single-use holdout protocol.
unresolved:
  - >
    Whether FANG/2026Q2 leaves the source-clean set (making the development bar 8/8) exactly as
    MBLY/2026Q2 left it under the v1 amendment, or whether the respondent contract changes instead.
  - >
    Whether qa_exchange.v1 needs an explicit unresolved-respondent state. FANG exchange 8 and the
    GOOGL regression share one root cause: a management speaker with neither a segment role nor
    any same-revision title declaration.
  - >
    The frozen gold's management_role_conflict count of 2 appears to undercount; segment-role
    metadata contradicts declared titles on 6 of 16 calls. The partition is unaffected.
next_actions:
  - Sol rules on the FANG source-clean label, the role-conflict under-count, and the unresolved-respondent contract question.
  - >
    Only after a corrected development bar is green against a frozen head may the eight holdout
    revisions be opened under the unchanged single-use protocol.
  - Do not start E3-OOS2 or E3-P. Method acceptance has not occurred.
do_not_redo:
  - "Do not re-derive the 113-separator R2 truth; it is reproduced exactly and pinned by tests."
  - "Do not weaken the respondent role law, make role nullable, or invent a Management role to make FANG pass."
  - "Do not repair Chad McAllaster's identity by first-name, nickname or external lookup."
  - "Do not open the holdout; holdout_bodies_inspected remains 0."
  - "Do not treat the GOOGL regression as OOS evidence; it is spent."
  - "Do not re-run the 16-call development adjudication expecting a different answer; it is deterministic."
danger_areas:
  - >
    The separator/questioner half is green and genuinely generic. It is tempting to call R2 built
    and spend the holdout. The respondent half is not green, and the holdout is single-use.
  - >
    Transcript participant declarations appear in BOTH orders — name-first ("Kevin Hostetler, our
    CEO") and title-first ("our CEO, Matt Salem"). Reading the wrong order silently inverts roles.
    Multi-word titles are themselves capitalized and will be read as person names unless excluded.
  - >
    A declared participant who never speaks must still terminate the previous person's title
    clause, or titles bleed between people.
---

# TFG-1 R2 — implemented, stopped at the development gate on a respondent-identity falsifier

The frozen source-native separator and questioner law is implemented and reproduces the ratified
R2 development truth exactly, with AAPL untouched. The operation stops before the holdout because
one of the nine calls the gold labels source-clean cannot produce a source-supported respondent.

This is the same shape of stop as TFG-1 v1: an internally inconsistent development label found by
faithfully implementing the frozen method, rather than a method tuned to reach a desired outcome.
