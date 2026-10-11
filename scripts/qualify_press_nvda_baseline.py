"""One fixed, artifact-only analytical qualification; never a collector or writer."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess

from engine.close_pass import massive_close
from engine.press.adjusted_baseline import BaselineRefused, PATH, PARAMS, canonical_payload, qualify
from lib import config

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "scripts/qualify_press_nvda_baseline.py", "engine/press/adjusted_baseline.py",
    "engine/stock_technicals.py", "engine/technicals.py", "engine/indicators.py",
    "engine/close_pass/massive_close.py", "lib/nyse_calendar.py", "lib/config.py",
    "engine/prophet_live/interval.py", "config.yml",
    ".github/workflows/press-source-qualification.yml",
    "research/licenses/MASSIVE_ENTITLEMENT_RECORD.md",
)
ENTITLEMENT_SHA256 = "82ad971b46d4159739117d3defe19a25a2a24ede45e5e8d28494c5849e757891"


def source_binding() -> dict:
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    hashes = {}
    for name in SOURCES:
        committed = subprocess.check_output(["git", "show", f"{revision}:{name}"], cwd=ROOT,
                                            stderr=subprocess.DEVNULL)
        if (ROOT / name).read_bytes() != committed:
            raise BaselineRefused("working_source_not_bound")
        hashes[name] = hashlib.sha256(committed).hexdigest()
    if hashes[SOURCES[-1]] != ENTITLEMENT_SHA256:
        raise BaselineRefused("entitlement_record_changed")
    return {"revision": revision, "sha256": hashes}


def _write(path: Path, obj: dict) -> None:
    raw = json.dumps(obj, sort_keys=True, indent=2, allow_nan=False).encode() + b"\n"
    _write_bytes(path, raw)


def _write_bytes(path: Path, raw: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def run(output: Path) -> int:
    # Exclusive output directory is also the attempt marker. A rerun never
    # overwrites evidence or replays a fetch whose outcome was interrupted.
    output = output.absolute()
    if any(p.is_symlink() for p in (output, *output.parents)):
        raise BaselineRefused("output_must_be_outside_checkout_without_symlinks")
    output = output.resolve(strict=False)
    if output.is_relative_to(ROOT.resolve()) or any(
            (p / ".git").exists() or (p / ".git").is_symlink()
            for p in (output, *output.parents)):
        raise BaselineRefused("output_must_be_outside_checkout_without_symlinks")
    binding = source_binding()
    if massive_close._base_url() not in ("https://api.polygon.io", "https://api.massive.com"):
        raise BaselineRefused("unqualified_api_origin")
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    _write(output / "attempt.json", {
        "kind": "press_fixed_nvda_baseline_attempt/v1", "source": binding,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "logical_fetch_budget": 1, "incumbent_http_attempt_cap": massive_close.ATTEMPTS,
        "path": PATH, "params": PARAMS, "allow_stage": False, "allow_emit": False,
    })
    # Resolve one key before effects. Never switch identities after a failed fetch.
    key = config.secret("MASSIVE_API_KEY") or config.secret("POLYGON_API_KEY")
    try:
        if not key:
            raise BaselineRefused("configured_market_data_credential_absent")
        payload = massive_close._default_fetch(key, allow_redirects=False)(PATH, dict(PARAMS))
        result = qualify(payload)
        raw = canonical_payload(payload)
        if key.encode() in raw:
            raise BaselineRefused("credential_echo_refused")
        # Store exactly the canonical parsed bytes whose digest is in the receipt.
        # This is not raw HTTP capture: the incumbent client returns parsed JSON.
        _write_bytes(output / "canonical_parsed_payload.json", raw)
        result.update({"source": binding, "captured_at": datetime.now(timezone.utc).isoformat(),
                       "runtime": {"python": platform.python_version(), **{
                           name: importlib.metadata.version(name)
                           for name in ("numpy", "pandas", "requests")}},
                       "input_rights": "operator-confirmed daily-bar and derived-research scope",
                       "completion": "qualified_analytical_artifact_only"})
        _write(output / "qualification.json", result)
        print("Fixed NVIDIA baseline artifact qualified; Press admission remains false.")
        return 0
    except BaselineRefused as exc:
        reason = str(exc)
    except Exception:
        reason = "capture_or_qualification_failed"
    _write(output / "failure.json", {"reason": reason, "allow_stage": False,
                                      "allow_emit": False, "publication_approved": False})
    print("Fixed NVIDIA baseline refused: " + reason)
    return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        raise SystemExit(run(args.output_dir))
    except (BaselineRefused, FileExistsError, subprocess.CalledProcessError):
        raise SystemExit("Qualification preflight refused; no fetch attempted") from None
