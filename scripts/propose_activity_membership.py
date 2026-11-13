"""Write ONLY the activity proposal ledger for one owner-read company activity.

This CLI is a ledger writer for the existing probation owner. It writes only
``data/theme_graph/probation/activity_proposals.jsonl`` (or an explicit
``--ledger`` path): never a data/theme_graph store file, never the legacy
``proposals.jsonl`` mapping queue. It ratifies nothing by itself and grants no
graph-membership use; a row leaves PROPOSED status only through a later named
curator act recorded with its receipt.

Evidence comes from the native owners through their default readers:
``engine.theme_graph.membership_evidence.build_activity_membership_evidence``
reads the identity owner and the company-intelligence disclosure owner, and
``engine.theme_graph.probation.make_activity_membership_proposal`` wraps that
evidence as a PROPOSED row. A segment packet's pinned source is replayed (form
and every figure span, whole document) before any ledger write. Every refusal is typed and printed as one
``REFUSED: <code>: <detail>`` line with exit 2 — never a traceback.

Run:
  python3 scripts/propose_activity_membership.py propose --issuer co:us:MU \
      --theme theme:hbm_packaging --role component_supplier \
      --knowledge-cutoff 2026-10-21T00:00:00Z --created 2026-10-21T05:00:00Z
  python3 scripts/propose_activity_membership.py curate --proposal-id actprop:... \
      --curator <name> --decision ACCEPT --decided-at <zoned> --receipt <file>
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.theme_graph import probation  # noqa: E402
from engine.theme_graph.membership_evidence import (  # noqa: E402
    ActivityAdmissionRefusal,
    build_activity_membership_evidence,
)

ROOT = Path(__file__).resolve().parent.parent
_ROLES = ("component_supplier", "platform_owner", "operator")


def _default_code_version() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"error: git rev-parse HEAD failed: {exc.stderr.strip()}",
              file=sys.stderr)
        raise SystemExit(2) from None
    return out.stdout.strip()


def _segment_source_authority(snapshot):
    # Mirrors scripts/publish_company_disclosure.py::_pinned_supplier_source: reuse
    # the incumbent private Research store and native pinned-source reader; never
    # copy raw sources into a second local store.
    from engine.company_intelligence import issuer_disclosures as native
    from engine.fundamental_forensics import filing_attestation
    from engine.research_vault import r2_store
    native._require(not os.environ.get("RESEARCH_LOCAL_STORE"), "SEC_LOCAL_SOURCE_OVERRIDE_REFUSED")
    store = r2_store.build_store()
    native._require(type(store) is r2_store.R2Store and store.available,
                    "SEC_NATIVE_SOURCE_STORE_UNAVAILABLE")
    native._require(snapshot.spec["edition"]["schema"] == native.SEC_EDITION_SCHEMA,
                    "SEC_SOURCE_BINDING_MISMATCH")
    return filing_attestation.PinnedSourceAuthority(
        store=store, snapshot_id=snapshot.spec["edition"]["sec_source"]["snapshot_id"])


def _cmd_propose(args: argparse.Namespace) -> int:
    code_version = args.code_version or _default_code_version()
    disclosure_reader = None
    exposure_role = None
    profit_driver = None
    if args.segment_packet:
        # Explicit deployment-owned segment packet selection, exactly the way
        # CommittedDisclosureSource(sec_supplier_paths=...) selects a supplier
        # packet: no discovery, no default activation. The pinned source is
        # replayed (form and every figure span, whole document) before any
        # ledger write: the disclosure store does not admit a segment fact.
        from engine.company_intelligence import issuer_disclosure_owner as owner
        from engine.company_intelligence import issuer_disclosures as native
        from engine.company_intelligence import sec_segment_adoption as segment
        source = owner.CommittedDisclosureSource(ROOT, sec_segment_paths=tuple(args.segment_packet))
        try:
            snapshot = source.snapshot()
            segment.replay_segment_source(snapshot, _segment_source_authority(snapshot))
        except ActivityAdmissionRefusal:
            raise
        except native.DisclosureError as exc:
            raise ActivityAdmissionRefusal(
                "SOURCE_OWNER_REFUSED", f"segment source replay: {exc.code}") from None
        except Exception as exc:
            raise ActivityAdmissionRefusal("SOURCE_OWNER_REFUSED", type(exc).__name__) from None

        def disclosure_reader(root, cv):
            return snapshot

        exposure_role = args.exposure_role
        profit_driver = args.profit_driver
    elif args.exposure_role is not None or args.profit_driver is not None:
        raise ActivityAdmissionRefusal(
            "EXPOSURE_SPECIES_MISMATCH",
            "--exposure-role/--profit-driver require --segment-packet")
    evidence = build_activity_membership_evidence(
        issuer_node_id=args.issuer, target_theme_id=args.theme, role=args.role,
        knowledge_cutoff=args.knowledge_cutoff, code_version=code_version, root=ROOT,
        disclosure_reader=disclosure_reader,
        exposure_role=exposure_role, profit_driver=profit_driver)
    row = probation.make_activity_membership_proposal(evidence, created=args.created)
    result = probation.append_activity_proposals([row], args.ledger)
    print(f'{{"proposal_id": "{row["proposal_id"]}", "status": "{row["status"]}", '
          f'"appended": {result["appended"]}, "unchanged": {result["unchanged"]}, '
          f'"ledger": "{result["path"]}"}}')
    return 0


def _cmd_curate(args: argparse.Namespace) -> int:
    receipt_path = Path(args.receipt)
    if not receipt_path.exists():
        raise probation.ActivityProposalRefusal(
            "CURATION_RECEIPT_MISSING", f"{receipt_path} does not exist")
    proposed = None
    for row in probation.read_activity_proposals(args.ledger):
        if row.get("proposal_id") == args.proposal_id and row.get("status") == "PROPOSED":
            proposed = row
            break
    if proposed is None:
        raise probation.ActivityProposalRefusal(
            "CURATION_REQUIRES_PROPOSED",
            f"no PROPOSED row {args.proposal_id} in {args.ledger or probation.ACTIVITY_PROPOSALS_PATH}")
    curated = probation.curate_activity_proposal(
        proposed, curator=args.curator, decision=args.decision,
        decided_at=args.decided_at, receipt_bytes=receipt_path.read_bytes())
    result = probation.append_activity_proposals([curated], args.ledger)
    print(f'{{"proposal_id": "{curated["proposal_id"]}", "status": "{curated["status"]}", '
          f'"receipt_sha256": "{curated["curation"]["receipt_sha256"]}", '
          f'"appended": {result["appended"]}, "unchanged": {result["unchanged"]}}}')
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    propose = sub.add_parser("propose", help="append one PROPOSED activity row")
    propose.add_argument("--issuer", required=True, help="company node, e.g. co:us:MU")
    propose.add_argument("--theme", required=True, help="micro-theme node, e.g. theme:hbm_packaging")
    propose.add_argument("--role", required=True, choices=_ROLES)
    propose.add_argument("--knowledge-cutoff", required=True, help="zoned ISO-8601 instant")
    propose.add_argument("--created", required=True, help="zoned ISO-8601 instant")
    propose.add_argument("--code-version", default=None,
                         help="source code version (default: git rev-parse HEAD)")
    propose.add_argument("--ledger", default=None, help=f"default: {probation.ACTIVITY_PROPOSALS_PATH}")
    propose.add_argument("--segment-packet", nargs=3, default=None,
                         metavar=("SPEC", "POLICY", "THEME_SOURCES"),
                         help="explicit protected segment packet paths (owner decision, "
                              "source-use policy, theme_sources); selects the "
                              "principal_business_activity species, no default activation")
    propose.add_argument("--exposure-role", default=None, choices=("primary", "secondary"),
                         help="segment only: the proposer's exposure role judgment")
    propose.add_argument("--profit-driver", action=argparse.BooleanOptionalAction, default=None,
                         help="segment only: whether the disclosed line is a profit driver")
    propose.set_defaults(func=_cmd_propose)

    curate = sub.add_parser("curate", help="append one curator decision for a PROPOSED row")
    curate.add_argument("--proposal-id", required=True)
    curate.add_argument("--curator", required=True)
    curate.add_argument("--decision", required=True, choices=("ACCEPT", "REJECT"))
    curate.add_argument("--decided-at", required=True, help="zoned ISO-8601 instant")
    curate.add_argument("--receipt", required=True, help="receipt file; its bytes are hashed")
    curate.add_argument("--ledger", default=None, help=f"default: {probation.ACTIVITY_PROPOSALS_PATH}")
    curate.set_defaults(func=_cmd_curate)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ActivityAdmissionRefusal, probation.ActivityProposalRefusal) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
