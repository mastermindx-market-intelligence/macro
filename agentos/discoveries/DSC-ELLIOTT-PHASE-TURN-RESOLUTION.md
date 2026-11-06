---
key: ELLIOTT-PHASE-TURN-RESOLUTION
claim: >
  At macro commit 4b1f8fddcc4eb6f36133fca4d42018678b74d30b, the existing
  detect_turns output has date-only timestamps and month/kind turn identifiers;
  it cannot, without an owner-approved representation change, serve as distinct
  timestamped intraday wave endpoints merely by reducing its reversal threshold.
falsifier: >
  Reproduce the frozen function ASTs from Git blob
  9e726868f6c218a84cd50a9f976c77c3a347ac6c and run the synthetic contract fixtures.
  Distinct intraday timestamps and collision-free IDs in those exact outputs
  would disprove the claim. A subsequent owner change may supersede this
  version-scoped finding but does not alter the historical result.
so_what: >
  Reuse the existing turn owner and its turn-epoch law, but do not plug the coarse
  payload directly into a four-hour Elliott confirmation or event-alignment
  study. Preserve source-bar precision, provisional status, initialization and
  actual availability in the existing owners' contracts. Do not create another
  swing, event, identity, replay or trial plane. This discovery is absorbed into
  WS:TECHNICAL-OPPORTUNITY-INTELLIGENCE W1/W2-0; it admits no market effect test,
  and generic Elliott/Fibonacci triage and protected studies stand.
kind: constraint
verified_at: 2026-09-11
verified_by: >
  engine/cycle_ontology.py:592-711 at
  4b1f8fddcc4eb6f36133fca4d42018678b74d30b; full source blob checked on the
  authorized Mac; isolated TurnParams/_yf/detect_turns AST hashes matched;
  research/technical_opportunity/elliott_phase/source_contract_probe.py and
  research/technical_opportunity/elliott_phase/source_contract_probe_results_2026-09-11.json;
  full characterization archive retained with the conversation research packet.
scope:
  - engine/cycle_ontology.py
  - research/technical_opportunity/elliott_phase/**
  - WS:TECHNICAL-OPPORTUNITY-INTELLIGENCE
confidence: verified
---

# Elliott phase turn resolution

**Active interpretation, qualified 2026-11-05.** This is a version-scoped constraint
on the existing turn owner. It is not a finding that any production consumer loses
rows, and it is not a program. The front matter above is the live record header
required by `agentos/schema/discovery.schema.yml`; it states the finding as it was
verified on 2026-09-11 against macro commit
`4b1f8fddcc4eb6f36133fca4d42018678b74d30b`, and it is deliberately **not** restamped
as a fresh November measurement. The complete original file is preserved
byte-for-byte exactly once, in the historical appendix at the end of this record.

## What the finding still says

At the pinned historical source, `engine/cycle_ontology.py::detect_turns` emitted
date-only pivot and confirmation timestamps together with month/kind turn
identifiers, so its payload could not serve as distinct timestamped intraday wave
endpoints without an owner-approved representation change. Lowering the reversal
threshold does not fix that. The detector was characterized as a broader-cycle
primitive rather than a complete Elliott parser, and its completed synthetic
geometry was stable as valid observations were appended, so the existing turn owner
and its turn-epoch law remain the right home.

Three distinctions stay live and are not weakened by this qualification:

- a dense daily fixture produced many confirmed turns under very few identifiers,
  which is a compatibility fact about the payload, **not** evidence that a current
  production consumer drops observations;
- structural endpoints may differ from price extrema under the published wave
  method, and a wave reading additionally needs its own supporting subdivision and
  parent evidence, each with a truthful available-at time — a necessary six-point
  constraint is not a complete wave count; and
- initialization, missing-row dropping, caller-supplied ordering, declared
  frequency and declared price basis are material parts of the available-at
  contract, and a provisional tail must be tested on its `provisional` flag rather
  than on field presence.

No production impact was measured, no shared source or identity migration was
applied, and no additional swing, event, identity, replay or trial plane is
authorized. The characterization probe, its archived result and its two accepted
tests remain byte-exact as published; they are not re-run, re-measured or
refreshed by this qualification, and no market price or outcome is read.

## Current owner routing as of 2026-11-05

The continuation below is read from the current canonical owners rather than from
the September packet. The frozen 20-passport wording carried by the original
record is historical.

- **TOI W1** remains Macro PR #7107 (branch `sol/toi-w1-evidence-census-20260913`),
  still Draft at inspected head `bad9ac6e93375c2132671330f7faaceae6a8c430`. Its
  October 7 grouped inventory reads **24 exact / 3 partial / 5 missing** across
  32 passports and 10 residual families, with P0 reconciling as **9 exact +
  3 partial**. The earlier frozen 20-passport review wording in the original
  record is historical, and the Connors/RVOL source study is accepted-stopped at
  review comment `5865508898` — it is not to be reopened. No current grouped
  acceptance and no source-writer transfer is proved. `toi.ordered_path_elliott`
  remains `P2 / toi_later_context / missing`, governed by causal pivots with
  `extreme_time` distinct from `known_at`, multiple preregistered candidate parses
  or abstention under ambiguity, no post-outcome relabeling, an equal-budget
  generic causal swing geometry baseline, and Fibonacci specificity as a separate
  hypothesis. Elliott is therefore **not admitted for audition**.
- **TOI W2-0** remains Macro PR #7094 (branch `sol/toi-w2-0-data-clock-20260912`),
  still Draft at inspected head `5bb1bc68c99146fab040aade04bbf1903c51e5b7`.
  Source-linked comments `5985434217` and `5985471173` accept one specific served
  construction — 4H built from stored 5m on the demonstrated SPY early-close case
  — and they do **not** accept the hourly 09:30 construction, `live_tail`, raw
  `Daily`, a point-in-time or correction law, a universal time bar, or full
  historical outcome admission.
- **The Daily-first narrowing** in comment `6011225572` and the committed
  `W2_DAILY_FIRST_SOURCE_RULING_2026-10-06` at inspected head
  `2ada944b30759ef8ffcc32e635a271ef477ccd2e` cover 22 slots on Daily plus
  completed-Weekly. Those slots do not universally require 4H. Later
  source-coverage qualifications remain real, and this narrowing admits neither
  Elliott E0 nor any W3 outcome.
- **W2's own release gap is not absorbed here.** Earlier compatibility packs
  passing did not make the failed plan/relays green; comment `5985335714` calls
  for a fresh current-base composition, and that W2 repair stays on its own
  carrier.

The two continuation records named below carry the same current routing in full:

- `research/technical_opportunity/elliott_phase/ELLIOTT_SOURCE_COMPATIBILITY_FINDING_2026-09-11.md`
- `research/technical_opportunity/elliott_phase/ELLIOTT_E0_ADMISSION_PROPOSAL_2026-09-11.md`

## Scope and continuation

The sole current E0 question stays anticipation before later confirmation;
continuation and entry remain separate future trials. W1 must qualify the method
and the local estate; W2-0 must qualify data, clocks, corrections, coverage,
rights, identity and Terminal parity. Compression Release stays TOI's first
proving vertical. This discovery creates no predictive outcome read, no source
refresh, no standalone Elliott workstream and no signal authority.

## Release boundary

Accepted history for this carrier is dated source evidence and is not re-run here:
the semantic `PASS / RELEASE_BLOCKED` review `5192078898` at head `3aa54c…`, and
the accepted fence-equivalence receipt `5655813982`. The detached historical
integration `617072daa5c18a1878a10067f9008246c9a77ee8` / tree
`f7381db1840ffc8574dc7f4f0b1ac0fdc442445a` is **not** a current integration and
**not** a merge. The old CI run `34773837272` ended with cancelled packs and the
`103791269465` gate failure; that dated terminal outcome replaces the older
"queued" wording rather than implying a blanket product failure.

The explicit `HOLD-FOR-SOL` on PR #7069 remains in force. This qualification does
not clear it, does not mark the PR Ready, does not arm or satisfy live admission,
and adds no generic independent reviewer under the current attended-Web policy.
The parent adjudicates the final exact-head source, CI and release decision.
Publication of these records confers no source, research, workflow execution or
trading authority.

## Historical appendix: complete original discovery as published on 2026-09-11

The block below is the **complete original file** — front matter, body and
newlines — copied byte-for-byte from Git blob `97314539c344932bcff40d4cf59e370dff086d60` at original head
`3aa54c741aa6218379ca9498069219f84d876d2b` (PR #7069, branch `sol/research-elliott-phase-contract-20260911`). It is preserved here exactly
once, so that qualifying the active reading above erases no original evidence.

| Property | Value |
|---|---|
| Original Git blob | `97314539c344932bcff40d4cf59e370dff086d60` |
| Original byte count | `3584` |
| Original SHA-256 | `0a61cfbc1576a9123f85866ddb1ad61604047c6282572a6f662ddbf2d45ff523` |
| Original head | `3aa54c741aa6218379ca9498069219f84d876d2b` |
| Archived copy count in this file | exactly one |

Exact extraction: the archive is the byte range starting immediately after the
opening `````text` line and ending at and including the newline that precedes
the closing ````` fence line. Extracting that range from the current file
reproduces the original bytes exactly — same byte count, same SHA-256, and the
same Git blob identity — including the original front matter and the original
trailing newline.

```sh
python3 - <<'PY'
import hashlib, pathlib
p = pathlib.Path("agentos/discoveries/DSC-ELLIOTT-PHASE-TURN-RESOLUTION.md")
b = p.read_bytes()
start = b.index(b"````text\n") + len(b"````text\n")
end = b.index(b"\n````\n", start) + 1
archive = b[start:end]
print(len(archive), hashlib.sha256(archive).hexdigest())
PY
```
````text
---
key: ELLIOTT-PHASE-TURN-RESOLUTION
claim: >
  At macro commit 4b1f8fddcc4eb6f36133fca4d42018678b74d30b, the existing
  detect_turns output has date-only timestamps and month/kind turn identifiers;
  it cannot, without an owner-approved representation change, serve as distinct
  timestamped intraday wave endpoints merely by reducing its reversal threshold.
falsifier: >
  Reproduce the frozen function ASTs from Git blob
  9e726868f6c218a84cd50a9f976c77c3a347ac6c and run the synthetic contract fixtures.
  Distinct intraday timestamps and collision-free IDs in those exact outputs
  would disprove the claim. A subsequent owner change may supersede this
  version-scoped finding but does not alter the historical result.
so_what: >
  Reuse the existing turn owner and its turn-epoch law, but do not plug the coarse
  payload directly into a four-hour Elliott confirmation or event-alignment
  study. Preserve source-bar precision, provisional status, initialization and
  actual availability in the existing owners' contracts. Do not create another
  swing, event, identity, replay or trial plane. This discovery is absorbed into
  WS:TECHNICAL-OPPORTUNITY-INTELLIGENCE W1/W2-0; it admits no market effect test,
  and generic Elliott/Fibonacci triage and protected studies stand.
kind: constraint
verified_at: 2026-09-11
verified_by: >
  engine/cycle_ontology.py:592-711 at
  4b1f8fddcc4eb6f36133fca4d42018678b74d30b; full source blob checked on the
  authorized Mac; isolated TurnParams/_yf/detect_turns AST hashes matched;
  research/technical_opportunity/elliott_phase/source_contract_probe.py and
  research/technical_opportunity/elliott_phase/source_contract_probe_results_2026-09-11.json;
  full characterization archive retained with the conversation research packet.
scope:
  - engine/cycle_ontology.py
  - research/technical_opportunity/elliott_phase/**
  - WS:TECHNICAL-OPPORTUNITY-INTELLIGENCE
confidence: verified
---

## Evidence and limits

The dense daily fixture contains 29 confirmed turns but only two distinct IDs.
The list retains all rows; mapping it by ID would retain two. This is NOT a
finding that a current production consumer loses 27 observations. No production
impact was measured and no shared source or identity migration was applied.

The intraday fixture contains distinct five-minute observations whose serialized
pivot/confirmation dates are identical. The detector is a broader-cycle primitive,
not a full Elliott parser. Its completed geometry was stable across the synthetic
prefix-extension checks. That existing causal capability should be retained.

Structural endpoints can differ from price extrema under the published wave
method. A full wave interpretation additionally needs its own supporting
subdivision and parent evidence, each with a truthful available-at time. A
necessary six-point constraint is not a complete wave count.

## Continuation

See:

- `research/technical_opportunity/elliott_phase/ELLIOTT_SOURCE_COMPATIBILITY_FINDING_2026-09-11.md`
- `research/technical_opportunity/elliott_phase/ELLIOTT_E0_ADMISSION_PROPOSAL_2026-09-11.md`

The sole current proposal is anticipation-first and remains
`NOT_ADMITTED / HOLD_FOR_TOI_W1_AND_W2_0`. Continuation and entry are separate
future trials. TOI W1 must qualify the method and local estate; TOI W2-0 must
qualify data, clocks, corrections, coverage, rights, identity, and Terminal
parity. Compression Release remains TOI's first proving vertical. No predictive
outcome read, source refresh, standalone Elliott workstream, or signal authority
is created by this discovery.
````
