#!/usr/bin/env python3
"""Build private Catalyst partner distribution previews; no outbound actions.

Normal:
  python3 scripts/build_catalyst_partner_pack.py \
    --packet /path/to/verified-public-event.json \
    --event-id evt_123 --partner /path/to/reviewed-partner.json \
    --tickers NVDA,AMD --out /path/to/private/review-pack

Three SYNTHETIC, non-publishable preview examples (fixed time/inputs):
  python3 scripts/build_catalyst_partner_pack.py --demo \
    --out /path/to/private/demo-previews

Scan route and first-touch attribution remain owned by Session 00. Without an
explicit confirmed route receipt, every link targets the reserved .invalid
placeholder. This tool writes local files only; it cannot send or publish.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Pin this checkout before ANY repo import (scripts/** import-hygiene law).
# Conditional path insertion cannot defend against a foreign installed package.
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from engine.marketing.catalyst_partner_pack import (
    PackRejected, build_partner_pack, write_partner_pack,
)

# No real market event, ticker/partner approval, or rights receipt is claimed by
# these fixtures. They demonstrate the full private asset path only.
DEMO_NOW = datetime(2026, 10, 9, 4, 30, tzinfo=timezone.utc)
DEMO_EVENT = {
    "schema_version": "catalyst.public_event.fixture.v1",
    "demo_only": True,
    "verification": {
        "status": "SYNTHETIC_FIXTURE",
        "source_owner": "fixture.only",
        "receipt_id": "fixture-no-legal-authority",
    },
    "public_safe": "PUBLIC_SAFE",
    "event_id": "synthetic-semis-brief",
    "event_kind": "earnings",
    "primary_subject": "Illustrative semiconductor earnings event",
    "headline_evidence_ids": ["source-synthetic-001"],
    "status": "active",
    "event_time_utc": "2026-10-09T02:00:00Z",
    "first_observed_at_utc": "2026-10-09T02:10:00Z",
    "as_of_utc": "2026-10-09T03:30:00Z",
    "expires_at_utc": "2026-10-10T02:00:00Z",
    "correction_generation": 0,
    "missing_data": [
        "Every issuer, affected symbol and claim is synthetic.",
        "The scan destination is an unregistered placeholder.",
    ],
    "sources": [{
        "source_id": "source-synthetic-001",
        "title": "Synthetic event exhibit (NOT an actual filing)",
        "url": "https://example.invalid/filing/CaseSensitive/Exhibit",
        "published_at_utc": "2026-10-09T02:00:00Z",
        "tier": "unverified",
        "rights": {
            "public_display": True, "public_link": True,
            "public_rehost": True,
            "receipt_id": "synthetic-fixture-no-permission",
        },
    }],
    "claims": [
        {
            "claim_id": "fixture-claim-exa",
            "text": "In the synthetic scenario, EXA discusses a shift in product demand.",
            "tickers": ["EXA"], "source_ids": ["source-synthetic-001"],
            "topics": ["earnings"],
        },
        {
            "claim_id": "fixture-claim-exb",
            "text": "In the synthetic scenario, EXB describes supplier lead times as an uncertainty.",
            "tickers": ["EXB"], "source_ids": ["source-synthetic-001"],
            "topics": ["supply-chain"],
        },
        {
            "claim_id": "fixture-claim-exc",
            "text": "In the synthetic scenario, EXC reports no quantified delivery schedule.",
            "tickers": ["EXC"], "source_ids": ["source-synthetic-001"],
            "topics": ["portfolio-risk"],
        },
    ],
    "affected_tickers": [
        {"ticker": "EXA", "relationship": "DIRECT",
         "evidence_ids": ["fixture-claim-exa"]},
        {"ticker": "EXB", "relationship": "EVIDENCED_INDIRECT",
         "evidence_ids": ["fixture-claim-exb"]},
        {"ticker": "EXC", "relationship": "EVIDENCED_INDIRECT",
         "evidence_ids": ["fixture-claim-exc"]},
    ],
}

DEMO_PROFILES = (
    ({
        "name": "Illustrative earnings-letter audience (demo only)",
        "slug": "demo-earnings-letter",
        "status": "candidate",
        "channel": "newsletter",
        "audience": "quarterly earnings coverage",
        "profile_url": "https://example.invalid/profiles/earnings-letter",
        "profile_verified_at_utc": "2026-10-09T03:30:00Z",
    }, ["EXA"]),
    ({
        "name": "Illustrative chip-supply audience (demo only)",
        "slug": "demo-chip-community",
        "status": "candidate",
        "channel": "community",
        "audience": "supplier capacity and indirect exposure",
        "profile_url": "https://example.invalid/profiles/chip-community",
        "profile_verified_at_utc": "2026-10-09T03:30:00Z",
    }, ["EXA", "EXB"]),
    ({
        "name": "Illustrative portfolio-risk audience (demo only)",
        "slug": "demo-portfolio-risk",
        "status": "candidate",
        "channel": "research",
        "audience": "exposure coverage and missing forward disclosures",
        "profile_url": "https://example.invalid/profiles/portfolio-risk",
        "profile_verified_at_utc": "2026-10-09T03:30:00Z",
    }, ["EXA", "EXB", "EXC"]),
)


def _read_json(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size > 1_000_000:
        raise PackRejected("MISSING_OR_OVERSIZED_INPUT")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise PackRejected("INVALID_JSON_OBJECT")
    return raw


def _now(text: str | None) -> datetime:
    if text is None:
        return datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PackRejected("INVALID_NOW") from exc
    if dt.tzinfo is None or dt.utcoffset().total_seconds() != 0:
        raise PackRejected("INVALID_NOW")
    return dt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path,
                        help="Existing approved event public-read packet JSON")
    parser.add_argument("--event-id",
                        help="Fail if the packet does not contain this exact event ID")
    parser.add_argument("--partner", type=Path,
                        help="Legitimate reviewed partner profile JSON")
    parser.add_argument("--tickers", help="1 to 3 comma-separated supported tickers; defaults to reviewed partner descriptor selection")
    parser.add_argument("--angle-plan", type=Path,
                        help="Optional AI-assisted list of selected existing claim IDs")
    parser.add_argument("--out", type=Path, required=True,
                        help="Private local directory to receive review-only files")
    parser.add_argument("--scan-url",
                        help="Only with a route receipt; owned by scan integrator")
    parser.add_argument("--route-receipt",
                        help="Exact non-secret scan route approval reference")
    parser.add_argument("--now-utc",
                        help="Optional UTC test clock; omitted means current time")
    parser.add_argument("--demo", action="store_true",
                        help="Generate three synthetic, explicitly non-publishable examples")
    args = parser.parse_args(argv)
    try:
        manifests: list[dict] = []
        if args.demo:
            if any((args.packet, args.partner, args.tickers, args.event_id,
                    args.angle_plan, args.scan_url, args.route_receipt,
                    args.now_utc)):
                raise PackRejected("DEMO_CANNOT_USE_LIVE_INPUTS")
            work = [(DEMO_EVENT, p, t, DEMO_NOW, None) for p, t in DEMO_PROFILES]
        else:
            if not args.packet or not args.partner:
                raise PackRejected("PACKET_AND_PARTNER_REQUIRED")
            event = _read_json(args.packet)
            if args.event_id and event.get("event_id") != args.event_id:
                raise PackRejected("EVENT_ID_MISMATCH")
            work = [(event, _read_json(args.partner),
                     args.tickers.split(",") if args.tickers else None,
                     _now(args.now_utc),
                     _read_json(args.angle_plan) if args.angle_plan else None)]
        for event, partner, tickers, now, angle_plan in work:
            result = build_partner_pack(
                event, partner, tickers, now_utc=now, angle_plan=angle_plan,
                scan_url=args.scan_url, route_receipt=args.route_receipt,
            )
            location = args.out / result["partner"]["slug"] if args.demo else args.out
            written = write_partner_pack(result, location)
            manifests.append({
                "pack_id": result["pack_id"],
                "partner": result["partner"]["slug"],
                "event_id": result["event"]["event_id"],
                "status": result["publication_status"],
                "media": result["media_status"],
                "scan_destination_verified": not result["link_is_placeholder"],
                "files": [str(f) for f in written],
            })
        print(json.dumps({"generated": manifests}, indent=2))
        return 0
    except (PackRejected, ValueError, OSError) as exc:
        # Never echo raw packet/profile data or personally identifying contact info.
        code = exc.code if isinstance(exc, PackRejected) else "INVALID_INPUT_OR_OUTPUT"
        print("CATALYST_PACK_REFUSED: " + code, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
