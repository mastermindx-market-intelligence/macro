"""Capture exact API bytes from a clean, explicitly pinned owner source checkout.

All source, identity and account inputs remain synthetic owner test fixtures.
This proves consumer compatibility, never source intake or production admission.
The historical default stays pinned; newer heads require a separate fresh output.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import runpy
import subprocess
import sys

PIN = "430234957531693b6b13f026a161e28542086a82"
HISTORICAL_OUTPUT = Path(__file__).with_name("fixtures") / "company_evidence_r2"


def _owner_head(owner_root: Path, expected_head: str) -> str:
    if not isinstance(expected_head, str) or not re.fullmatch(r"[0-9a-f]{40}", expected_head):
        raise ValueError("Capture requires a full 40-character immutable source head")

    def git(*args: str) -> str:
        return subprocess.check_output(
            ["git", *args], cwd=owner_root, text=True, timeout=30
        ).strip()

    if Path(git("rev-parse", "--show-toplevel")).resolve() != owner_root:
        raise ValueError("Capture requires the exact owner repository root")
    head = git("rev-parse", "HEAD")
    if head != expected_head:
        raise ValueError("Capture requires the pinned owner source head " + expected_head)
    if git("status", "--porcelain", "--untracked-files=normal"):
        raise ValueError("Capture requires a clean owner source checkout")
    return head


def validate_capture_request(
    owner_root: Path, expected_head: str, output_dir: Path
) -> tuple[Path, Path]:
    """Read-only preflight; no output, checkout, source or admission is created."""
    owner_root, output = Path(owner_root).resolve(), Path(output_dir).resolve()
    if output == owner_root or output.is_relative_to(owner_root):
        raise ValueError("Capture output cannot write into the owner checkout")
    historical = HISTORICAL_OUTPUT.resolve()
    if output == historical or output.is_relative_to(historical):
        raise ValueError("The historical fixture corpus must remain unchanged")
    if output.exists():
        raise ValueError("Capture output already exists; reconcile it rather than overwrite")
    _owner_head(owner_root, expected_head)
    return owner_root, output


def capture(
    owner_root: Path, *, expected_head: str = PIN, output_dir: Path | None = None
) -> dict:
    owner_root = Path(owner_root).resolve()
    if output_dir is None:
        if expected_head != PIN:
            raise ValueError("A different owner head requires a separate explicit output directory")
        out = HISTORICAL_OUTPUT.resolve()
        if out == owner_root or out.is_relative_to(owner_root):
            raise ValueError("Capture output cannot write into the owner checkout")
        _owner_head(owner_root, expected_head)
    else:
        owner_root, out = validate_capture_request(owner_root, expected_head, output_dir)
    head = _owner_head(owner_root, expected_head)
    old_path, old_bytecode = sys.path[:], sys.dont_write_bytecode
    api, original_now = None, None
    # Reading another owner's source must not emit __pycache__ in that checkout.
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(owner_root))
    try:
        # These are the same owner's existing test fixtures and API harness,
        # never substituted live inputs or a new implementation of its producer.
        owner = runpy.run_path(str(owner_root / "tests/test_company_catalyst_public_evidence.py"))
        serving = runpy.run_path(str(owner_root / "tests/test_biocatalyst_wmn_api.py"))
        import app.biocatalyst as api

        if Path(api.__file__).resolve() != owner_root / "app/biocatalyst.py":
            raise ValueError("Loaded API module is not from the pinned owner checkout")
        case = owner["_case"]()
        evidence = owner["_project"](case)
        event = owner["attach_catalyst_public_evidence"](
            case[0], [evidence], generation_cutoff=owner["CUTOFF"]
        )
        inputs = owner["_api_inputs"](event)
        # Existing explicit targets are refused; historical default retains its
        # original behavior and is never used for a changed owner revision.
        out.mkdir(parents=True, exist_ok=output_dir is None)
        original_now = api._wmn_now
        api._wmn_now = lambda: datetime(2026, 10, 19, tzinfo=timezone.utc)
        responses = []

        def save(name, response):
            if response.status_code != 200:
                raise ValueError(f"{name}: HTTP {response.status_code}: {response.text[:300]}")
            if response.headers.get("cache-control") != "private, no-store" or response.headers.get("vary") != "Authorization":
                raise ValueError(f"{name}: owner private-response headers changed")
            raw = response.content
            (out / name).write_bytes(raw)
            responses.append({
                "file": name, "status": response.status_code,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "cache_control": response.headers.get("cache-control"),
                "vary": response.headers.get("vary"),
            })
            return response.json()

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
        _owner_head(owner_root, expected_head)
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
        if output_dir is not None:
            receipt.update({
                "historical_fixture_head": PIN,
                "owner_checkout_unchanged": True,
                "bytecode_writes_disabled": True,
                "native_admission_verified": False,
                "final_disk_publication_recheck_verified": False,
                "harness_limit": "Existing owner _app may replace _recheck_wmn_current; this is handler/composer wire proof only.",
                "source_files": [
                    {"path": str(path), "sha256": hashlib.sha256((owner_root / path).read_bytes()).hexdigest()}
                    for path in [
                        Path("app/biocatalyst.py"),
                        Path("engine/biocatalyst/what_matters_next.py"),
                        Path("engine/biocatalyst/company_event_adapter.py"),
                        Path("tests/test_company_catalyst_public_evidence.py"),
                        Path("tests/test_biocatalyst_wmn_api.py"),
                    ]
                ],
            })
        (out / "capture-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        return receipt
    finally:
        if api is not None and original_now is not None:
            api._wmn_now = original_now
        sys.path[:] = old_path
        sys.dont_write_bytecode = old_bytecode


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner-root", required=True, type=Path)
    parser.add_argument("--expected-head", default=PIN)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    receipt = capture(args.owner_root, expected_head=args.expected_head, output_dir=args.output_dir)
    print(json.dumps({"candidate_head": receipt["candidate_head"], "responses": len(receipt["responses"]),
                      "source_admission": receipt["source_admission"]}, indent=2))
