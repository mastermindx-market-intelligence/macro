"""Produce a narrow, read-only witness of generated AI Brief outputs.

The nightly's existing main writer consumes this manifest through
daily_engine_aibrief_checkpoint.sh; this module never commits or pushes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import date, datetime
from pathlib import Path

LENSES = {"macro": "master_brief.json", "china": "china_brief.json", "btc": "btc_brief.json"}
MAX_BYTES = 4_000_000


class CheckpointRefused(ValueError):
    """An early brief snapshot is incomplete or less trustworthy than main."""


def _read_path(root: Path, rel: str) -> bytes:
    path = root / rel
    if path.is_symlink() or not path.is_file():
        raise CheckpointRefused(f"missing or symlinked generated file: {rel}")
    if path.stat().st_size > MAX_BYTES:
        raise CheckpointRefused(f"oversize generated file: {rel}")
    return path.read_bytes()


def _accepted(root: Path, base: str, rel: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(root), "show", f"{base}:{rel}"],
        capture_output=True, check=False,
    )
    # Every allowed brief path is already tracked on main. A missing object,
    # permission problem or fetch failure is not permission to invent a baseline.
    if result.returncode:
        raise CheckpointRefused(f"unreadable accepted source: {rel} at {base}")
    return result.stdout


def _valid_json(raw: bytes, rel: str, lens: str) -> tuple[date, datetime, dict]:
    try:
        doc = json.loads(raw)
        if not isinstance(doc, dict) or doc.get("lens") != lens:
            raise ValueError("wrong or missing lens")
        asof = date.fromisoformat(doc["state_asof"])
        generated = datetime.fromisoformat(doc["generated_at"].replace("Z", "+00:00"))
        if generated.tzinfo is None:
            raise ValueError("generated_at lacks timezone")
        # A fresh timestamp with an empty parsed LLM response is NOT a usable
        # new brief.  Match the downstream publication contract before the
        # earliest durable writer can replace a last-good narrative.
        if not any(doc.get(k) for k in ("summary", "tldr", "regime_read")):
            raise ValueError("brief has no rendered narrative")
        return asof, generated, doc
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise CheckpointRefused(f"invalid {lens} generated brief {rel}: {exc}") from exc


def generated_manifest(root: Path, source_head: str) -> list[tuple[str, str]]:
    """Return closed-path SHA256 witnesses; never stage unbuilt or degraded briefs."""
    root = root.resolve(strict=True)
    staged: list[tuple[str, str]] = []
    for lens, name in LENSES.items():
        data_rel, site_rel = f"data/regime/{name}", f"site/{name}"
        data, site = _read_path(root, data_rel), _read_path(root, site_rel)
        if data != site:
            raise CheckpointRefused(f"regime/site brief pair differs: {name}")
        old_data, old_site = _accepted(root, source_head, data_rel), _accepted(root, source_head, site_rel)
        if old_data != old_site:
            raise CheckpointRefused(f"accepted source contains divergent brief pair: {name}")
        if data == old_data:
            continue  # BTC's configured 3-day interval legitimately skips some nights.
        new_asof, new_when, payload = _valid_json(data, data_rel, lens)
        if payload.get("degraded_reason"):
            raise CheckpointRefused(f"provider-degraded {lens} brief cannot replace last-good data")
        old_asof, old_when, _ = _valid_json(old_data, data_rel, lens)
        if new_asof < old_asof or new_when < old_when:
            raise CheckpointRefused(f"regressed {lens} brief provenance clock")
        for rel, raw in ((data_rel, data), (site_rel, site)):
            staged.append((rel, hashlib.sha256(raw).hexdigest()))

    # The existing render owner rebuilds page HTML, shared assets and China/HK
    # modals from accepted JSON. Publishing those here would ship partial panels.
    return staged


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--source-head", required=True)
    p.add_argument("--manifest", type=Path, required=True)
    args = p.parse_args()
    try:
        rows = generated_manifest(args.root, args.source_head)
    except CheckpointRefused as exc:
        print(f"::error title=AI Brief checkpoint refused::{exc}", flush=True)
        return 1
    args.manifest.write_text(
        "".join(f"{rel}\t{digest}\n" for rel, digest in rows),
        encoding="utf-8",
    )
    print(f"AI Brief checkpoint: {len(rows)} proven source files", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
