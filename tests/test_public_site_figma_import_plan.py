import json
import subprocess
from pathlib import Path

import pytest

from tools.figma.public_site_baseline.build_import_plan import (
    PHASES,
    STATIC_VARIANTS,
    SURFACES,
    build_upload_order,
    render_finalize_script,
    render_prepare_script,
    write_import_plan,
)


def _matrix(tmp_path: Path) -> dict:
    static = []
    motion = []
    source = {
        "local_head": "local-head",
        "frozen_source": "15c01bd991f35d0bb2185ee1e608a05df0805803",
    }
    for surface in SURFACES:
        for variant in STATIC_VARIANTS:
            file_path = tmp_path / "static" / f"{surface}-{variant}.png"
            static.append({
                "page": surface,
                "variant": variant,
                "kind": "static",
                "verified": True,
                "file": str(file_path),
                "sha256": (surface + variant).encode().hex().ljust(64, "0")[:64],
                "image_width": int(variant.split("-", 1)[0]),
                "image_height": 1000,
                "console_errors": [],
            })
        for phase in PHASES:
            file_path = tmp_path / "motion" / f"{surface}-hero-{phase}.png"
            motion.append({
                "page": surface,
                "phase": phase,
                "kind": "motion",
                "verified": True,
                "file": str(file_path),
                "sha256": (surface + phase).encode().hex().ljust(64, "0")[:64],
                "image_width": 1440,
                "image_height": 900,
                "console_errors": [],
            })
    return {
        "schema": "mastermindx.public_site_figma_reference_matrix.v1",
        "operation": "public-site-figma-baseline-20260915-sol-001",
        "source": source,
        "static": static,
        "motion": motion,
    }


def _node_parse(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", "-e", f"new Function({json.dumps(script)}); console.log('JS_OK')"],
        text=True,
        capture_output=True,
        check=False,
    )


def test_build_upload_order_is_complete_and_canonical(tmp_path: Path) -> None:
    order = build_upload_order(_matrix(tmp_path))

    assert len(order["items"]) == 36
    assert [item["index"] for item in order["items"]] == list(range(36))
    assert order["items"][0]["target_name"] == "MMX/RefTarget/homepage/1440-en"
    assert order["items"][19]["target_name"] == "MMX/RefTarget/market-dashboards/390-zh"
    assert order["items"][20]["target_name"] == "MMX/MotionTarget/homepage/observe"
    assert order["items"][-1]["target_name"] == "MMX/MotionTarget/market-dashboards/hold"


def test_build_upload_order_rewrites_files_under_asset_root(tmp_path: Path) -> None:
    order = build_upload_order(_matrix(tmp_path), asset_root=Path("/portable/assets"))

    assert order["items"][0]["file"] == "/portable/assets/static/homepage-1440-en.png"
    assert order["items"][20]["file"] == "/portable/assets/motion/homepage-hero-observe.png"


def test_build_upload_order_rejects_missing_or_unverified_evidence(tmp_path: Path) -> None:
    missing = _matrix(tmp_path)
    missing["static"].pop()
    with pytest.raises(ValueError, match="missing static"):
        build_upload_order(missing)

    unverified = _matrix(tmp_path)
    unverified["motion"][0]["verified"] = False
    with pytest.raises(ValueError, match="not verified"):
        build_upload_order(unverified)


def test_generated_scripts_parse_and_enforce_image_fill_gate(tmp_path: Path) -> None:
    order = build_upload_order(_matrix(tmp_path))
    prepare = render_prepare_script(order)
    finalize = render_finalize_script(expected_count=36)

    forbidden = ("loadAllPagesAsync", "setPluginData", "createImageAsync", "figma.currentPage =")
    assert not any(term in prepare + finalize for term in forbidden)
    assert "await figma.setCurrentPageAsync" in prepare
    assert "Expected 36 upload targets" in finalize
    assert 'fill.type === "IMAGE"' in finalize
    assert _node_parse(prepare).returncode == 0
    assert _node_parse(finalize).returncode == 0


def test_write_import_plan_emits_three_consistent_artifacts(tmp_path: Path) -> None:
    matrix_path = tmp_path / "reference-matrix.json"
    matrix_path.write_text(json.dumps(_matrix(tmp_path)), encoding="utf-8")
    output_dir = tmp_path / "out"

    receipt = write_import_plan(
        matrix_path,
        output_dir,
        asset_root=Path("/portable/assets"),
    )

    assert receipt["target_count"] == 36
    order_path = output_dir / "figma_upload_order.json"
    prepare_path = output_dir / "figma_prepare_import_targets.js"
    finalize_path = output_dir / "figma_finalize_import_targets.js"
    assert order_path.is_file()
    assert prepare_path.is_file()
    assert finalize_path.is_file()

    order = json.loads(order_path.read_text(encoding="utf-8"))
    assert len(order["items"]) == receipt["target_count"]
    assert order["items"][0]["file"].startswith("/portable/assets/")
    assert _node_parse(prepare_path.read_text(encoding="utf-8")).returncode == 0
    assert _node_parse(finalize_path.read_text(encoding="utf-8")).returncode == 0
