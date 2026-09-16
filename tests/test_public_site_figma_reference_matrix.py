from pathlib import Path

import pytest

from tools.figma.public_site_baseline.reference_matrix import (
    MOTION_PHASES,
    STATIC_VARIANTS,
    SURFACES,
    build_reference_matrix,
)


def _records(tmp_path: Path) -> list[dict]:
    records: list[dict] = []
    for surface in SURFACES:
        for variant in STATIC_VARIANTS:
            width = int(variant.split("-", 1)[0])
            document_width = 425 if surface == "market-dashboards" and width == 390 else width
            records.append({
                "kind": "static",
                "page": surface,
                "variant": variant,
                "file": str(tmp_path / "static" / f"{surface}-{variant}.png"),
                "sha256": (surface + variant).encode().hex().ljust(64, "0")[:64],
                "bytes": 100,
                "image_width": width,
                "image_height": 1000,
                "viewport_width": width,
                "viewport_height": 900 if width > 390 else 844,
                "document_width": document_width,
                "document_height": 1000,
                "full_page": True,
                "wait_ms": 1400,
                "url": f"http://127.0.0.1/{surface}?still=1",
                "console_errors": [],
            })
        for phase in MOTION_PHASES:
            records.append({
                "kind": "motion",
                "page": surface,
                "phase": phase,
                "file": str(tmp_path / "motion" / f"{surface}-hero-{phase}.png"),
                "sha256": (surface + phase).encode().hex().ljust(64, "0")[:64],
                "bytes": 100,
                "image_width": 1440,
                "image_height": 900,
                "viewport_width": 1440,
                "viewport_height": 900,
                "document_width": 1440,
                "document_height": 1000,
                "full_page": False,
                "wait_ms": 900,
                "url": f"http://127.0.0.1/{surface}",
                "console_errors": [],
            })
    return records


def _build(tmp_path: Path, records: list[dict]) -> dict:
    return build_reference_matrix(
        records,
        operation="public-site-figma-baseline-20260915-sol-001",
        source={
            "local_head": "local-head",
            "frozen_source": "15c01bd991f35d0bb2185ee1e608a05df0805803",
        },
    )


def test_build_reference_matrix_seals_complete_canonical_evidence(tmp_path: Path) -> None:
    matrix = _build(tmp_path, _records(tmp_path))

    assert matrix["schema"] == "mastermindx.public_site_figma_reference_matrix.v1"
    assert matrix["counts"] == {"static": 20, "motion": 16, "total": 36}
    assert all(item["verified"] is True for item in matrix["static"] + matrix["motion"])
    assert matrix["static"][0]["page"] == "homepage"
    assert matrix["static"][0]["variant"] == "1440-en"
    assert matrix["motion"][-1]["page"] == "market-dashboards"
    assert matrix["motion"][-1]["phase"] == "hold"


def test_build_reference_matrix_preserves_authored_overflow_metadata(tmp_path: Path) -> None:
    matrix = _build(tmp_path, _records(tmp_path))
    target = next(
        item
        for item in matrix["static"]
        if item["page"] == "market-dashboards" and item["variant"] == "390-en"
    )
    assert target["image_width"] == 390
    assert target["document_width"] == 425
    assert target["horizontal_overflow_px"] == 35


def test_build_reference_matrix_rejects_missing_and_duplicate_states(tmp_path: Path) -> None:
    missing = _records(tmp_path)
    missing.pop()
    with pytest.raises(ValueError, match="missing motion"):
        _build(tmp_path, missing)

    duplicate = _records(tmp_path)
    duplicate.append(dict(duplicate[0]))
    with pytest.raises(ValueError, match="duplicate static"):
        _build(tmp_path, duplicate)


def test_build_reference_matrix_rejects_console_errors_or_wrong_dimensions(tmp_path: Path) -> None:
    errored = _records(tmp_path)
    errored[0]["console_errors"] = ["404"]
    with pytest.raises(ValueError, match="console errors"):
        _build(tmp_path, errored)

    wrong = _records(tmp_path)
    wrong[0]["image_width"] = 1439
    with pytest.raises(ValueError, match="static image width"):
        _build(tmp_path, wrong)
