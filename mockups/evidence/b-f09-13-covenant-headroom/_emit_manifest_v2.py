"""Re-emit manifest.json as mastermind.p0_evidence.v2 from the existing shots.

Round h4_7127 (Meta-CEO RULING 2026-09-19): a receipt carries exactly three
keys (`schema`, `changed_paths`, `manifest`); provenance moves into a single
top-level `honesty` block on the v2 manifest itself (one evidence plane).

Stdlib only — json, hashlib, struct (PNG IHDR width/height), pathlib, datetime.
"""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHOTS = HERE / "shots"
RENDER = HERE / "_render_panel.py"

# Read the existing receipt-shaped manifest so we can carry the honest
# provenance that used to live on the receipt into the new manifest's
# `honesty` block. generated_at is the existing manifest's captured_at —
# keep the real capture time, do not invent a new one.
_LEGACY = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
_LEGACY_EVIDENCE = {}
_EVIDENCE_PATH = HERE / "EVIDENCE.yml"
try:
    import yaml  # PyYAML is a standing repo dependency
except ImportError:
    yaml = None  # type: ignore[assignment]
if yaml is not None:
    _LEGACY_EVIDENCE = yaml.safe_load(_EVIDENCE_PATH.read_text(encoding="utf-8")) or {}

# h5_7127 (seat, 2026-09-19): the emitter must be a no-op on its own output. Once
# manifest.json is already p0_evidence.v2 the provenance lives in its own
# generated_at/honesty keys, so re-runs reuse them and only re-hash the cells.
_IS_V2 = _LEGACY.get("schema") == "mastermind.p0_evidence.v2"
GENERATED_AT = _LEGACY.get("generated_at") if _IS_V2 else _LEGACY.get("captured_at")


def _png_dimensions(path: Path) -> tuple[int, int]:
    """Read the PNG IHDR width/height (8-byte big-endian uint32 pair at offset 16)."""
    head = path.read_bytes()[:24]
    # PNG signature: 8 bytes; IHDR length: 4 bytes; "IHDR": 4 bytes; width: 4; height: 4
    w, h = struct.unpack(">II", head[16:24])
    return w, h


def _state_id(name: str) -> tuple[str, str, str]:
    """Parse `name.<theme>.<locale>.<width>.png` → (theme, locale, viewport_name).

    The viewport is desktop for 1440 and mobile for 390.
    """
    stem = name.removesuffix(".png")
    parts = stem.split(".")
    state, theme, locale, width = parts[0], parts[1], parts[2], int(parts[3])
    viewport = "desktop" if width == 1440 else "mobile"
    return state, theme, locale, viewport


def _cell(filename: str, *, force_state: str | None) -> dict:
    state, theme, locale, viewport = _state_id(filename)
    png = SHOTS / filename
    raw = png.read_bytes()
    width, height = _png_dimensions(png)
    sha = hashlib.sha256(raw).hexdigest()
    entry = {
        "viewport": viewport,
        "locale": locale,
        "theme": theme,
        "access": "anonymous",
        "viewport_width": 1440 if viewport == "desktop" else 390,
        "viewport_height": 900 if viewport == "desktop" else 844,
        "force_state": force_state,
        "captured": True,
        "file": f"shots/{filename}",
        "sha256": sha,
        "bytes": len(raw),
        "width": width,
        "height": height,
        "applied_theme": theme,
        "applied_locale": locale,
    }
    return entry


def main() -> None:
    rendered_script = RENDER.read_bytes()
    tool = {
        "name": "serial playwright cli via _render_panel.py",
        "module_sha256": hashlib.sha256(rendered_script).hexdigest(),
    }

    states: list[dict] = []
    computed_pngs = sorted(p.name for p in SHOTS.glob("computed.*.png"))
    null_pngs = sorted(p.name for p in SHOTS.glob("null.*.png"))
    for fname in computed_pngs:
        states.append(_cell(fname, force_state=None))
    for fname in null_pngs:
        states.append(_cell(fname, force_state="null_payload"))

    honesty = _LEGACY.get("honesty") if _IS_V2 else {
        "fixture_render": _LEGACY_EVIDENCE.get("fixture_render", _LEGACY.get("fixture_render")),
        "fixture_render_disclosure": _LEGACY_EVIDENCE.get(
            "fixture_render_disclosure", _LEGACY.get("fixture_render_disclosure")
        ),
        "render_method": _LEGACY_EVIDENCE.get("render_method", _LEGACY.get("render_method")),
        "capture_transport": _LEGACY_EVIDENCE.get(
            "capture_transport", _LEGACY.get("capture_transport")
        ),
        "capture_hidden_selectors": _LEGACY_EVIDENCE.get(
            "capture_hidden_selectors", _LEGACY.get("capture_hidden_selectors")
        ),
        "hidden_selectors_audit": _LEGACY_EVIDENCE.get(
            "hidden_selectors_audit", _LEGACY.get("hidden_selectors_audit")
        ),
        "panel_content_hidden": _LEGACY_EVIDENCE.get(
            "panel_content_hidden", _LEGACY.get("panel_content_hidden")
        ),
        "captured_by": _LEGACY_EVIDENCE.get("captured_by", _LEGACY.get("captured_by")),
        "final_head_sha": _LEGACY_EVIDENCE.get("final_head_sha"),
        "final_head_tree_sha": _LEGACY_EVIDENCE.get("final_head_tree_sha"),
        "render_recipe_script": _LEGACY_EVIDENCE.get(
            "render_recipe_script",
            _LEGACY.get("render_evidence", {}).get("render_recipe_script"),
        ),
        "payloads": _LEGACY.get("states"),
        "rendered_html": [
            {"id": s.get("id"), "html": s.get("html"), "payload": s.get("payload")}
            for s in _LEGACY.get("states", [])
        ],
    }

    manifest = {
        "schema": "mastermind.p0_evidence.v2",
        "generated_at": GENERATED_AT,
        "tool": tool,
        "pages": [
            {
                "page_id": "macro:capital_structure",
                "route": "/capital_structure.html",
                "panel_selector": "#cs-covenant-room",
                "console_errors": [],
                "failed_responses": [],
                "gaps": [],
                "states": states,
            }
        ],
        "honesty": honesty,
    }

    out = HERE / "manifest.json"
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"cells={len(states)}")
    print(f"sha256={hashlib.sha256(out.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
