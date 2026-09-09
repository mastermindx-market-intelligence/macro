"""Pure capture-guard helpers for Macro Command P5 (v16 falsifiability).

These are intentionally browser-free so unit tests can plant violations and
see raises. The capture script imports the same functions used in production.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence


class CaptureGeometryError(RuntimeError):
    """Raw crop geometry overflow — never clamp; raise with the measured box."""

    def __init__(
            self, message: str, *, page: str = "", state: str = "",
            locale: str = "", width: float | int | None = None,
            raw_box: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.page = page
        self.state = state
        self.locale = locale
        self.width = width
        self.raw_box = dict(raw_box) if raw_box else None


def _filter_locale_nodes(
        nodes: Sequence[Mapping[str, Any]], locale: str
        ) -> list[dict[str, Any]]:
    """Keep nodes for the active locale; drop the other-locale class."""
    prefer = "l-zh" if locale == "zh" else "l-en"
    other = "l-en" if locale == "zh" else "l-zh"
    kept: list[dict[str, Any]] = []
    for node in nodes:
        classes = set(str(node.get("class") or "").split())
        if other in classes and prefer not in classes:
            continue
        if node.get("display") == "none" or node.get("visibility") == "hidden":
            continue
        if float(node.get("opacity") or 1) == 0:
            continue
        kept.append(dict(node))
    return kept


def _assert_crop_geometry(
        crop_box: Mapping[str, Any], *,
        viewport_width: float, doc_height: float, name: str,
        crop_box_doc: Mapping[str, Any] | None = None,
        page: str = "", state: str = "", locale: str = "",
        ) -> None:
    """Assert RAW viewport geometry. Never clamps; raises CaptureGeometryError."""
    x = float(crop_box["x"])
    y = float(crop_box["y"])
    w = float(crop_box["width"])
    h = float(crop_box["height"])
    raw = {"x": x, "y": y, "width": w, "height": h}
    if x < -0.01 or y < -0.01:
        raise CaptureGeometryError(
            f"{name}: raw_box origin out of range x={x} y={y}",
            page=page, state=state or name, locale=locale,
            width=viewport_width, raw_box=raw)
    if x + w > float(viewport_width) + 0.51:
        raise CaptureGeometryError(
            f"{name}: raw_box overflows viewport width "
            f"x+w={x + w} vw={viewport_width}",
            page=page, state=state or name, locale=locale,
            width=viewport_width, raw_box=raw)
    doc = crop_box_doc or crop_box
    dy = float(doc["y"])
    dh = float(doc["height"])
    if dy < -0.01:
        raise CaptureGeometryError(
            f"{name}: crop_box_doc.y={dy} < 0",
            page=page, state=state or name, locale=locale,
            width=viewport_width, raw_box=raw)
    if dy + dh > float(doc_height) + 1.0:
        raise CaptureGeometryError(
            f"{name}: crop_box_doc overflows document height "
            f"y+h={dy + dh} doc_h={doc_height}",
            page=page, state=state or name, locale=locale,
            width=viewport_width, raw_box=raw)


def _boxes_intersect(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    ax0 = float(a.get("x", a.get("left", 0)))
    ay0 = float(a.get("y", a.get("top", 0)))
    aw = float(a.get("width", (a.get("right", 0) - ax0)))
    ah = float(a.get("height", (a.get("bottom", 0) - ay0)))
    bx0 = float(b.get("x", b.get("left", 0)))
    by0 = float(b.get("y", b.get("top", 0)))
    bw = float(b.get("width", (b.get("right", 0) - bx0)))
    bh = float(b.get("height", (b.get("bottom", 0) - by0)))
    if aw <= 0 or ah <= 0 or bw <= 0 or bh <= 0:
        return False
    return not (
        ax0 + aw <= bx0 or bx0 + bw <= ax0
        or ay0 + ah <= by0 or by0 + bh <= ay0
    )


def _judge_occlusion(
        samples: Sequence[Mapping[str, Any]],
        allowed_selectors: Sequence[str] | None = None,
        *,
        min_samples: int = 5,
        ) -> list[dict[str, Any]]:
    """Raise if too few samples or any foreign hit. Returns the samples list."""
    rows = [dict(s) for s in samples]
    if len(rows) < int(min_samples):
        raise RuntimeError(
            f"occlusion guard needs ≥{min_samples} samples, got {len(rows)}")
    allowed = {str(s) for s in (allowed_selectors or ()) if s}
    bad: list[dict[str, Any]] = []
    for row in rows:
        ok = bool(row.get("ok"))
        if allowed and not ok:
            hit = str(row.get("hitSelector") or "")
            if hit and any(
                    hit == sel or hit.startswith(sel + " ")
                    or sel in hit for sel in allowed):
                row["ok"] = True
                ok = True
        if not ok:
            bad.append(row)
    if bad:
        raise RuntimeError(
            f"occlusion guard failed on {len(bad)}/{len(rows)} samples: "
            f"{bad[:3]}")
    return rows


def grid_sample_points(
        box: Mapping[str, Any], *, cols: int = 3, rows: int = 4,
        inset: float = 4.0) -> list[tuple[float, float]]:
    """3×4 (default) grid inset inside the crop box."""
    x0 = float(box["x"]) + inset
    y0 = float(box["y"]) + inset
    x1 = float(box["x"]) + float(box["width"]) - inset
    y1 = float(box["y"]) + float(box["height"]) - inset
    if x1 <= x0 or y1 <= y0:
        cx = float(box["x"]) + float(box["width"]) / 2.0
        cy = float(box["y"]) + float(box["height"]) / 2.0
        return [(cx, cy)]
    pts: list[tuple[float, float]] = []
    for ri in range(rows):
        fy = (ri + 0.5) / rows
        y = y0 + (y1 - y0) * fy
        for ci in range(cols):
            fx = (ci + 0.5) / cols
            x = x0 + (x1 - x0) * fx
            pts.append((x, y))
    return pts
