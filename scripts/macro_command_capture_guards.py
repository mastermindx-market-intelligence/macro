"""Pure capture-guard helpers for Macro Command P5 (v17 falsifiability).

These are intentionally browser-free so unit tests can plant violations and
see raises. The capture script imports the same functions used in production.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

# Sub-pixel rounding only — written into the evidence manifest as
# geometry_tolerance_px and pinned by tests (0.6 px overflow must raise).
GEOMETRY_TOLERANCE_PX = 0.5


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
        tolerance_px: float = GEOMETRY_TOLERANCE_PX,
        ) -> None:
    """Assert RAW viewport geometry. Never clamps; raises CaptureGeometryError."""
    x = float(crop_box["x"])
    y = float(crop_box["y"])
    w = float(crop_box["width"])
    h = float(crop_box["height"])
    raw = {"x": x, "y": y, "width": w, "height": h}
    tol = float(tolerance_px)
    if x < -0.01 or y < -0.01:
        raise CaptureGeometryError(
            f"{name}: raw_box origin out of range x={x} y={y}",
            page=page, state=state or name, locale=locale,
            width=viewport_width, raw_box=raw)
    if x + w > float(viewport_width) + tol:
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
        min_samples: int = 15,
        ) -> list[dict[str, Any]]:
    """Raise if too few samples or any foreign hit. Returns the samples list.

    Allowed selectors match by exact equality on ``hitSelector`` only —
    never substring (C-n1).
    """
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
            if hit and hit in allowed:
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
        box: Mapping[str, Any], *, cols: int = 3, rows: int = 5,
        inset: float = 4.0) -> list[tuple[float, float]]:
    """Inclusive 15-point grid (default): edges at ±inset + 25/50/75 % interiors.

    Rows: top+inset, 25 %, 50 %, 75 %, bottom−inset.
    Columns: left+inset, centre, right−inset.
    """
    x0 = float(box["x"]) + inset
    y0 = float(box["y"]) + inset
    x1 = float(box["x"]) + float(box["width"]) - inset
    y1 = float(box["y"]) + float(box["height"]) - inset
    if x1 <= x0 or y1 <= y0:
        cx = float(box["x"]) + float(box["width"]) / 2.0
        cy = float(box["y"]) + float(box["height"]) / 2.0
        return [(cx, cy)]
    # Fixed inclusive edge fractions for the ratified 5-row / 3-col grid.
    if rows == 5 and cols == 3:
        y_fracs = (0.0, 0.25, 0.50, 0.75, 1.0)
        x_fracs = (0.0, 0.50, 1.0)
    else:
        y_fracs = tuple(
            0.0 if ri == 0 else (
                1.0 if ri == rows - 1 else ri / (rows - 1))
            for ri in range(rows)
        )
        x_fracs = tuple(
            0.0 if ci == 0 else (
                1.0 if ci == cols - 1 else ci / (cols - 1))
            for ci in range(cols)
        )
    pts: list[tuple[float, float]] = []
    for fy in y_fracs:
        y = y0 + (y1 - y0) * fy
        for fx in x_fracs:
            x = x0 + (x1 - x0) * fx
            pts.append((x, y))
    return pts


def y_coverage(
        samples: Sequence[Mapping[str, Any]],
        crop_box: Mapping[str, Any],
        ) -> float:
    """Fraction of crop height spanned by sample ys (0..1).

    Inclusive edge sampling (±4 px inset) cannot reach (h−8)/h ≥ 0.95 on short
    crops. When the first/last samples land within 8 px of the sample-box
    top/bottom, treat coverage as complete (1.0) — the edges were probed.
    """
    ys = [float(s["y"]) for s in samples if "y" in s]
    h = float(crop_box.get("height") or 0)
    if not ys or h <= 0:
        return 0.0
    top = float(crop_box.get("y") or 0.0)
    bottom = top + h
    if min(ys) <= top + 8.0 and max(ys) >= bottom - 8.0:
        return 1.0
    return max(0.0, min(1.0, (max(ys) - min(ys)) / h))
