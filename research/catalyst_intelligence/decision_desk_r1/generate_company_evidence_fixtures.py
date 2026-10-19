"""Capture exact R2 API bytes from a clean, immutable owner source checkout.

The source, identity and account inputs are synthetic test fixtures. This is
consumer contract proof, not source intake or production admission.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys

PIN = "430234957531693b6b13f026a161e28542086a82"


def capture(owner_root: Path) -> dict:
    owner_root = owner_root.resolve()

    def fence() -> str:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=owner_root, text=True).strip()
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=no"], cwd=owner_root, text=True
        ).strip()
        if head != PIN or dirty:
            raise ValueError("Capture requires the clean pinned Company source head " + PIN)
        return head

    head = fence()
    # This fixture belongs to the separately checked owner source, not the
    # frontend tree. Resolve it only after the exact source/custody fence.
    sys.path.insert(0, str(owner_root))
    owner = runpy.run_path(str(owner_root / "tests/test_company_catalyst_public_evidence.py"))
    serving = runpy.run_path(str(owner_root / "tests/test_biocatalyst_wmn_api.py"))
    import app.biocatalyst as api

    case = owner["_case"]()
    evidence = owner["_project"](case)
    event = owner["attach_catalyst_public_evidence"](
        case[0], [evidence], generation_cutoff=owner["CUTOFF"]
    )
    inputs = owner["_api_inputs"](event)
    out = Path(__file__).with_name("fixtures") / "company_evidence_r2"
    out.mkdir(parents=True, exist_ok=True)
    original_now = api._wmn_now
    api._wmn_now = lambda: datetime(2026, 10, 19, tzinfo=timezone.utc)
    responses = []

    def save(name, response):
        if response.status_code != 200:
            raise ValueError(f"{name}: HTTP {response.status_code}: {response.text}")
        raw = response.content
        (out / name).write_bytes(raw)
        responses.append({
            "file": name, "status": response.status_code,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "cache_control": response.headers.get("cache-control"),
            "vary": response.headers.get("vary"),
        })
        return response.json()

    try:
        with serving["_app"](lambda: (serving["_projection"](inputs), {})) as client:
            page = save("company-page.json", client.get("/api/biocatalyst/v1/what-matters-next"))
            for view in ["upcoming", "reconcile", "history"]:
                for horizon in ([7, 30, 90, 180, 365] if view == "upcoming" else [None]):
                    save(f"page-{view}-{horizon}.json", client.get(
                        "/api/biocatalyst/v1/what-matters-next",
                        params={"view": view, "limit": 50, **(
                            {"horizon_days": horizon} if horizon is not None else {}
                        )},
                    ))
            detail = save("company-detail.json", client.get(
                "/api/biocatalyst/v1/what-matters-next/detail",
                params={"generation_id": serving["GENERATION"],
                        "event_fact_ref": event["event_id"],
                        "issuer_id": page["rows"][0]["issuer"]["issuer_id"]},
            ))
        if page["rows"][0]["evidence"] != detail["event"]["evidence"]:
            raise ValueError("List/detail source context does not match")
        fence()
        receipt = {
            "candidate_head": head,
            "fixture_kind": "synthetic Company source context through actual owner functions and API",
            "capture_method": "TestClient; existing test auth override; fixed _wmn_now; synthetic _read_bundle",
            "source_admission": False, "entitled_runtime_verified": False,
            "production_publication_verified": False,
            "evaluation_cutoff": owner["CUTOFF"],
            "source_body_kind": "fictional SEC-location synthetic filing, not an observed issuer disclosure",
            "responses": responses,
        }
        (out / "capture-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        return receipt
    finally:
        api._wmn_now = original_now
        sys.path.remove(str(owner_root))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner-root", required=True, type=Path)
    receipt = capture(parser.parse_args().owner_root)
    print(json.dumps({"candidate_head": receipt["candidate_head"], "responses": len(receipt["responses"]),
                      "source_admission": receipt["source_admission"]}, indent=2))
