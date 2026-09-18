"""Source-contract proof for the existing targeted Quiver backfill owner."""
from pathlib import Path


def test_backfill_workflow_can_supply_quiver_secret_to_targeted_collect():
    text = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "backfill.yml").read_text()
    assert "python -m scripts.collect --full-history --only" in text
    assert "QUIVER_API_KEY: ${{ secrets.QUIVER_API_KEY }}" in text
