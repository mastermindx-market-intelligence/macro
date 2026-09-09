"""Pure-function tests for Macro Command P5 v17 capture guards."""
from __future__ import annotations

import pytest

from scripts.macro_command_capture_guards import (
    GEOMETRY_TOLERANCE_PX,
    CaptureGeometryError,
    _assert_crop_geometry,
    _filter_locale_nodes,
    _judge_occlusion,
    grid_sample_points,
    y_coverage,
)


def test_geometry_tolerance_is_half_pixel() -> None:
    assert GEOMETRY_TOLERANCE_PX == 0.5


def test_assert_crop_geometry_raises_on_negative_x() -> None:
    with pytest.raises(CaptureGeometryError):
        _assert_crop_geometry(
            {"x": -1, "y": 0, "width": 472, "height": 100},
            viewport_width=390, doc_height=2000, name="planted.png",
            locale="en")


def test_assert_crop_geometry_raises_on_overflow_right() -> None:
    with pytest.raises(CaptureGeometryError):
        _assert_crop_geometry(
            {"x": 0, "y": 0, "width": 392, "height": 100},
            viewport_width=390, doc_height=2000, name="planted.png")


def test_assert_crop_geometry_raises_on_point_six_overflow() -> None:
    """E-m1: 0.6 px overflow must raise under the declared 0.5 px tolerance."""
    with pytest.raises(CaptureGeometryError):
        _assert_crop_geometry(
            {"x": 0, "y": 0, "width": 390.6, "height": 100},
            viewport_width=390, doc_height=2000, name="tol.png")


def test_assert_crop_geometry_passes_within_half_pixel() -> None:
    _assert_crop_geometry(
        {"x": 0, "y": 0, "width": 390.4, "height": 100},
        viewport_width=390, doc_height=2000, name="ok-tol.png",
        crop_box_doc={"x": 0, "y": 10, "width": 390.4, "height": 100})


def test_assert_crop_geometry_passes_on_fitting_rect() -> None:
    _assert_crop_geometry(
        {"x": 10, "y": 20, "width": 300, "height": 400},
        viewport_width=390, doc_height=2000, name="ok.png",
        crop_box_doc={"x": 10, "y": 120, "width": 300, "height": 400})


def test_judge_occlusion_raises_on_foreign_hit() -> None:
    samples = [
        {"x": i, "y": i, "ok": True, "hitSelector": ".mq-axis-method"}
        for i in range(14)
    ] + [{"x": 99, "y": 99, "ok": False, "hitSelector": ".nav-links"}]
    with pytest.raises(RuntimeError, match="occlusion guard failed"):
        _judge_occlusion(samples, min_samples=15)


def test_judge_occlusion_raises_on_too_few_samples() -> None:
    samples = [{"x": i, "y": i, "ok": True} for i in range(14)]
    with pytest.raises(RuntimeError, match="≥15"):
        _judge_occlusion(samples)


def test_judge_occlusion_passes_on_fifteen_clean_default() -> None:
    samples = [
        {"x": i, "y": i, "ok": True, "hitSelector": ".mq-axis-method"}
        for i in range(15)
    ]
    out = _judge_occlusion(samples)
    assert len(out) == 15


def test_judge_occlusion_allowlist_exact_match_only() -> None:
    """C-n1: substring must NOT clear a foreign hit."""
    samples = [
        {"x": i, "y": i, "ok": True, "hitSelector": ".mq-axis-method"}
        for i in range(14)
    ] + [{"x": 99, "y": 99, "ok": False, "hitSelector": "nav.mq-suitenav-pill"}]
    with pytest.raises(RuntimeError, match="occlusion guard failed"):
        _judge_occlusion(samples, allowed_selectors=[".mq-suitenav"])
    samples2 = [
        {"x": i, "y": i, "ok": True, "hitSelector": ".mq-axis-method"}
        for i in range(14)
    ] + [{"x": 99, "y": 99, "ok": False, "hitSelector": ".mq-suitenav"}]
    out = _judge_occlusion(samples2, allowed_selectors=[".mq-suitenav"])
    assert out[-1]["ok"] is True


def test_filter_locale_nodes_excludes_other_locale() -> None:
    nodes = [
        {"class": "l-en", "text": "Weights law", "display": "block",
         "visibility": "visible", "opacity": 1},
        {"class": "l-zh", "text": "权重法则", "display": "block",
         "visibility": "visible", "opacity": 1},
        {"class": "mq-row", "text": "shared", "display": "block",
         "visibility": "visible", "opacity": 1},
    ]
    en = _filter_locale_nodes(nodes, "en")
    assert all("l-zh" not in str(n.get("class")) for n in en)
    assert any("Weights law" in str(n.get("text")) for n in en)
    zh = _filter_locale_nodes(nodes, "zh")
    assert all("l-en" not in str(n.get("class")) for n in zh)


def test_grid_sample_points_inclusive_fifteen() -> None:
    box = {"x": 0, "y": 100, "width": 390, "height": 800}
    pts = grid_sample_points(box)
    assert len(pts) == 15
    xs = sorted({round(x, 4) for x, _ in pts})
    ys = sorted({round(y, 4) for _, y in pts})
    assert xs[0] == pytest.approx(4.0)
    assert xs[-1] == pytest.approx(386.0)
    assert ys[0] == pytest.approx(104.0)
    assert ys[-1] == pytest.approx(896.0)
    assert ys[0] <= float(box["y"]) + 8
    cov = y_coverage([{"y": y} for _, y in pts], box)
    assert cov >= 0.95


def test_no_element_text_alias_assignment_in_capture() -> None:
    """C-M2: grep receipt — no alias of element_text_sha256 from extra[."""
    from pathlib import Path
    src = Path("scripts/capture_macro_command_p5.py").read_text(encoding="utf-8")
    assert 'element_text_sha256"] = extra[' not in src
    assert "element_text_sha256'] = extra[" not in src


def test_scroll_clear_requires_crop_box() -> None:
    """C-m2: crop_box is a required positional argument."""
    import inspect
    from scripts.capture_macro_command_p5 import _scroll_clear_of_chrome
    params = list(inspect.signature(_scroll_clear_of_chrome).parameters)
    assert "crop_box" in params
    # No default on crop_box.
    assert (
        inspect.signature(_scroll_clear_of_chrome).parameters["crop_box"].default
        is inspect.Parameter.empty
    )
