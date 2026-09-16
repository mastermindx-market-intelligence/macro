"""Live committed-archive regeneration proof for RPH-1 sector control."""
from __future__ import annotations

from pathlib import Path

from scripts.research.rotation_persistence.sector_control import ALL_SYMBOLS
from scripts.research.run_sector_control_rph1 import OUTPUT_FILENAMES, main


def test_committed_real_archive_result_regenerates_byte_for_byte(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    committed = repo_root / "research" / "rotation_persistence" / "sector_control_rph1"
    isolated_root = tmp_path / "repo"
    isolated_data = isolated_root / "data" / "yahoo"
    isolated_data.mkdir(parents=True)
    for symbol in ALL_SYMBOLS:
        (isolated_data / f"{symbol}.parquet").symlink_to(
            repo_root / "data" / "yahoo" / f"{symbol}.parquet"
        )

    exit_code = main(
        [
            "--data-dir",
            "data/yahoo",
            "--output-dir",
            "research/regenerated",
            "--produced-at",
            "2026-09-12T21:00:00Z",
        ],
        repo_root=isolated_root,
    )

    assert exit_code == 0
    output = isolated_root / "research" / "regenerated"
    for filename in OUTPUT_FILENAMES:
        assert (output / filename).read_bytes() == (committed / filename).read_bytes()
