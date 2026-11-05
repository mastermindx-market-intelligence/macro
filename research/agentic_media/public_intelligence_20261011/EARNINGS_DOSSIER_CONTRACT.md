# Earnings dossier contract — source acceptance

Operation: `mmx-public-intelligence-delivery-20261011-local-ceo-001`.
Source base: `488cb027751ee644c681e2579c6fcc23ca9b3e9f`.
This slice continues the Press staging work in Macro PR #8786. It preserves
`WS:EARNINGS-INTELLIGENCE-OS` source ownership; Commission 19 and Catalyst
PR #8678 are unchanged. No live story, rights approval or publication is claimed.

## Implemented consumer capability

The existing offline compiler can explicitly construct a newly sourced or
source-corrected Tier B `earnings.story_packet/v2` with one immutable canonical
stock dossier link. It derives the URL from the validated event ticker, verifies
a committed regular dossier page through the existing rendered-page inventory,
and freezes the Git commit/blob receipt before hashing the packet. The existing
admission and staging path replays that exact versioned slot.

Legacy v1 bytes, IDs and generation hashes remain unchanged. Unchanged source
packets remain exact no-ops even when the new option is supplied; this change
does not rewrite an existing event merely to add a link. Historical replay does
not consult today's mutable pages. Current staging checks the route before the
model boundary and after generation; disappearance quarantines the artifact,
separately recording dossier availability and earnings-root currency.

`canonical_emit_allowed=false` and admission `allow_emit=false` remain intact.
The unattended projector and publisher keep their existing legacy defaults.
The Git receipt proves committed local route existence, not public deployment,
article rights or an editorial decision.

## Verification

The feature tests initially failed in nine cases with one legacy case passing.
The post-generation route-disappearance test separately failed with
`DID NOT RAISE` before the quarantine repair.

Final command, executed from the owned source worktree:

```sh
python3 -m pytest tests/test_earnings_dossier_link_contract.py tests/test_earnings_story_packets.py tests/test_earnings_canonical_story.py tests/test_earnings_story_promotion.py tests/test_earnings_story_press_admission.py tests/test_earnings_story_press_ingress.py tests/test_earnings_story_press_stage_workflow.py tests/test_earnings_story_press_workflow.py tests/test_earnings_public_wire.py tests/test_refresh_earnings_story_packets.py tests/test_publish_earnings_story_packets_r2.py -q --tb=short --basetemp=../mmx-dossier-suite-fixtures
```

Result: **154 passed in 19.55 seconds**. The earlier 12 public-wire verification
failures were resolved by moving fixture output outside the repository and
materializing the committed `site` tree with the existing sparse helper.
They are not waived failures. No real provider, R2 or credential call occurred.

Independent source review accepted the six implementation/test files and the
two existing-CI registration lines. Additional offline probes exited zero for:
v2 ancestor to default-v1 correction; frozen receipt tampering; rejection of
old admission reuse after rehashing; admission schema downgrade; and invalid
Git IDs or dossier-binding schema. `git diff --check` passed. The new regression
is registered in the existing `publish-r2-client` job and CI trigger inventory.

## Existing compiler invocation

With owner-qualified local evidence and an appropriate local packet output
store, run from the intended source checkout:

```sh
python3 - "${EARNINGS_EVIDENCE_DIR:?}" "${EARNINGS_PACKET_OUT_DIR:?}" <<'PY'
from pathlib import Path
import sys
from engine.earnings_narrative.story_store import write_story_packet_generation

write_story_packet_generation(
    Path(sys.argv[2]), Path(sys.argv[1]), dossier_root=Path.cwd(),
)
PY
```

This writes local immutable objects, a generation and marker through the
existing compiler. It does not invoke a model or publish to R2. Linked Press validation is integrated with PR #8786's `/stocks/` configuration and validators on the same carrier.

## Remaining live dependencies

[Fable's reply](https://github.com/mastermindx-market-intelligence/Mastermind/issues/1243#issuecomment-6108389713)
correctly routes the story dependency to Earnings Intelligence OS. Current
source recovery found no distinct competing adapter edit or verified live
adapter writer; the historical workstream owner label is not a live lease.
The carrier census was bounded and does not prove exhaustive absence.

The owner-qualified return still needs an actual current generation and
manifest hash/ETag, finalized journal chain, manifest packet-index entry and
immutable object receipt/body carrying packet/revision/source identities,
story-specific public-article rights, and the permitted read-only admission
path. Credentials remain with the existing owner/runtime. Journal receipts
alone do not carry the packet/revision pair, and evidence integrity alone is
not full-article rights clearance. The earlier anonymous R2 403 is preserved;
no alternate identity or carrier retry is authorized by this source change.

The next live action is to admit that exact qualified new/source-corrected
packet through `scripts/stage_earnings_story_press.py`. An unchanged existing
event needs a separately qualified contract upgrade. D14 staging acceptance,
editorial approval, publication release, domain readiness and the authenticated
signup/follow journey remain separate obligations.

## Parent integration repair

The parent consolidated both slices on PR #8786 and added an integration check through the actual `check_link_allowlist` and current Press configuration. The initial new adapter used the apex host while existing canonical dossier links use `www.mastermind-x.com`; the regression failed with `assert False is True`. The adapter now derives exactly `https://www.mastermind-x.com/stocks/<ticker>.html`, and an apex-host binding is rejected. No generic validator was weakened.

The final command is the 11-file command above plus `tests/test_press_validators.py`, using `--basetemp=../mmx-dossier-integrated-fixtures`. Result: **248 passed in 19.85 seconds**, exit 0. The integration check admits the immutable event-ticker link and rejects an additional unplanned ticker. This supersedes the pre-integration hostname in the original build receipt.
