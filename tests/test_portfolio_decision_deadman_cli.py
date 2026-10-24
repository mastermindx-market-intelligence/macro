from __future__ import annotations

from scripts import portfolio_decision_deadman as deadman


def test_collect_cli_uses_the_supplied_argument_vector(monkeypatch) -> None:
    snapshot = {"schema": "fixture"}
    writes: list[tuple[dict, str | None]] = []

    monkeypatch.setattr(deadman, "collect_snapshot", lambda: snapshot)
    monkeypatch.setattr(
        deadman,
        "_write_json",
        lambda value, path: writes.append((dict(value), path)),
    )

    assert deadman.main(["collect"]) == 0
    assert writes == [(snapshot, None)]
