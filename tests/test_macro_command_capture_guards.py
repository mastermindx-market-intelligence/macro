"""Pure-function tests for Macro Command P5 v16 capture guards."""
from __future__ import annotations

import pytest

from scripts.macro_command_capture_guards import (
    CaptureGeometryError,
    _assert_crop_geometry,
    _filter_locale_nodes,
    _judge_occlusion,
    grid_sample_points,
)


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


def test_assert_crop_geometry_passes_on_fitting_rect() -> None:
    _assert_crop_geometry(
        {"x": 10, "y": 20, "width": 300, "height": 400},
        viewport_width=390, doc_height=2000, name="ok.png",
        crop_box_doc={"x": 10, "y": 120, "width": 300, "height": 400})


def test_judge_occlusion_raises_on_foreign_hit() -> None:
    samples = [
        {"x": 1, "y": 1, "ok": True, "hitSelector": ".mq-axis-method"},
        {"x": 2, "y": 2, "ok": True, "hitSelector": ".mq-axis-method"},
        {"x": 3, "y": 3, "ok": True, "hitSelector": ".mq-axis-method"},
        {"x": 4, "y": 4, "ok": True, "hitSelector": ".mq-axis-method"},
        {"x": 5, "y": 5, "ok": False, "hitSelector": ".nav-links"},
    ]
    with pytest.raises(RuntimeError, match="occlusion guard failed"):
        _judge_occlusion(samples, min_samples=5)


def test_judge_occlusion_raises_on_too_few_samples() -> None:
    samples = [{"x": i, "y": i, "ok": True} for i in range(4)]
    with pytest.raises(RuntimeError, match="≥5"):
        _judge_occlusion(samples, min_samples=5)


def test_judge_occlusion_passes_on_five_clean() -> None:
    samples = [
        {"x": i, "y": i, "ok": True, "hitSelector": ".mq-axis-method"}
        for i in range(5)
    ]
    out = _judge_occlusion(samples, min_samples=5)
    assert len(out) == 5


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


def test_grid_sample_points_is_3x4() -> None:
    pts = grid_sample_points(
        {"x": 0, "y": 100, "width": 390, "height": 800}, cols=3, rows=4)
    assert len(pts) == 12
    ys = sorted({round(y, 1) for _, y in pts})
    assert ys[0] >= 104 - 0.1
    assert ys[-1] <= 900 - 4 + 0.1
