"""Gates for the producer's per-file issuer row reader (row-cache change).

``_issuer_rows`` used to call ``pd.read_parquet`` once PER ISSUER; it now
groups each (file, json_column) pair once per file version through
``_issuer_payloads`` (bounded cache ``_ISSUER_PAYLOAD_CACHE``), and every
observable result must stay byte-identical to the old algorithm:

* the same rows in the same per-issuer order (equivalence against a copy of
  the old function, kept here as :func:`_old_issuer_rows`);
* the same lazy parsing — rows of issuers that are never asked for are never
  parsed, and ``json.loads`` stays per call;
* the same exceptions with the same messages, including the issuer-local row
  index and the KeyError a missing json_column raises;
* cache behavior: one read per (file, json_column) per file version, bounded
  to 8 keys, and returned rows are fresh objects every call.

Fixtures are self-contained: small parquet files written with pandas into
``tmp_path``.  No digest, id or count is hard-coded — expectations are derived
from the rows written.
"""
from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from engine.capital_structure.scenario_inputs import ScenarioInputsError
from scripts import build_capital_structure_capacity_inputs as mod


@pytest.fixture(autouse=True)
def _clear_payload_cache():
    """Every test starts from an empty row cache (and leaves it empty)."""
    mod._ISSUER_PAYLOAD_CACHE.clear()
    yield
    mod._ISSUER_PAYLOAD_CACHE.clear()


def _old_issuer_rows(path: Path, json_column: str, issuer_id: str, label: str) -> tuple[dict[str, Any], ...]:
    """The pre-cache algorithm, copied verbatim from the producer region it replaced."""
    import pandas as pd

    frame = pd.read_parquet(path)
    if "issuer_id" not in frame.columns:
        raise ScenarioInputsError(f"{label} carries no issuer_id column")
    mask = frame["issuer_id"].astype(str) == issuer_id
    selected = frame.loc[mask]
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(selected[json_column].tolist()):
        if not isinstance(raw, str) or not raw:
            raise ScenarioInputsError(f"{label} row {index} lacks a {json_column} payload")
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ScenarioInputsError(f"{label} row {index} has malformed {json_column}") from exc
        if not isinstance(value, Mapping):
            raise ScenarioInputsError(f"{label} row {index} {json_column} must be an object")
        rows.append(dict(value))
    return tuple(rows)


def _write_ledger(path: Path, rows: list[dict[str, Any]]) -> None:
    pd.DataFrame(rows).to_parquet(path, index=False)


def _counting_read_parquet(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    """Route ``pandas.read_parquet`` through a counter; returns the counter."""
    calls = {"n": 0}
    real = pd.read_parquet

    def counting(*args: Any, **kwargs: Any):
        calls["n"] += 1
        return real(*args, **kwargs)

    monkeypatch.setattr(pd, "read_parquet", counting)
    return calls


def test_equivalence_with_old_algorithm(tmp_path: Path) -> None:
    """Three issuers with 0, 1 and 3 rows, interleaved in file order: the
    cached reader returns exactly what the old algorithm returns, per issuer,
    including per-issuer order and an unknown issuer returning ()."""
    path = tmp_path / "covenant_term_observations.parquet"
    payloads = {
        "ISSUER-A": [],
        "ISSUER-B": [{"kind": "lien", "amount": 1}],
        "ISSUER-C": [
            {"kind": "lien", "amount": 2, "terms": {"x": 1}},
            {"kind": "sweep", "accounts": ["a", "b"]},
            {"kind": "covenant", "nested": {"deep": [1, 2, {"k": "v"}]}},
        ],
    }
    # Interleaved file order: C0, B0, C1, C2 (A has no rows; a fourth issuer's
    # row is never requested and must stay unparsed by both sides).
    ordered = [
        ("ISSUER-C", json.dumps(payloads["ISSUER-C"][0])),
        ("ISSUER-B", json.dumps(payloads["ISSUER-B"][0])),
        ("ISSUER-C", json.dumps(payloads["ISSUER-C"][1])),
        ("ISSUER-C", json.dumps(payloads["ISSUER-C"][2])),
        ("ISSUER-D", "{never parsed"),  # malformed, but ISSUER-D is never asked
    ]
    rows = [{"issuer_id": issuer, "observation_json": raw} for issuer, raw in ordered]
    _write_ledger(path, rows)

    for issuer_id in ("ISSUER-A", "ISSUER-B", "ISSUER-C", "ISSUER-UNKNOWN"):
        assert mod._issuer_rows(path, "observation_json", issuer_id, "label") == _old_issuer_rows(
            path, "observation_json", issuer_id, "label"
        )
    # per-issuer order is the file order, not a grouped sort
    assert [r["kind"] for r in mod._issuer_rows(path, "observation_json", "ISSUER-C", "label")] == [
        "lien",
        "sweep",
        "covenant",
    ]
    assert mod._issuer_rows(path, "observation_json", "ISSUER-UNKNOWN", "label") == ()


def test_one_read_per_file_and_json_column(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """50 issuer ids on one file read the file exactly once; a second
    json_column on the same file performs exactly 1 more read."""
    path = tmp_path / "instrument_candidate_terms.parquet"
    rows = [
        {
            "issuer_id": f"ISSUER-{i:03d}",
            "candidate_term_json": json.dumps({"n": i}),
            "extra_json": json.dumps({"e": i * 2}),
        }
        for i in range(50)
    ]
    _write_ledger(path, rows)
    calls = _counting_read_parquet(monkeypatch)

    for i in range(50):
        assert mod._issuer_rows(path, "candidate_term_json", f"ISSUER-{i:03d}", "label") == ({"n": i},)
    assert calls["n"] == 1

    assert mod._issuer_rows(path, "extra_json", "ISSUER-007", "label") == ({"e": 14},)
    assert calls["n"] == 2

    # a repeat call hits the cache: still no further read
    assert mod._issuer_rows(path, "candidate_term_json", "ISSUER-000", "label") == ({"n": 0},)
    assert calls["n"] == 2


def test_rewritten_file_is_reread(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A file rewritten with different content (forced fresh mtime/size) is
    re-read exactly once and the next call reflects the new content."""
    path = tmp_path / "covenant_term_observations.parquet"
    _write_ledger(path, [{"issuer_id": "ISSUER-A", "observation_json": json.dumps({"v": 1})}])
    calls = _counting_read_parquet(monkeypatch)

    assert mod._issuer_rows(path, "observation_json", "ISSUER-A", "label") == ({"v": 1},)
    assert calls["n"] == 1

    _write_ledger(path, [{"issuer_id": "ISSUER-A", "observation_json": json.dumps({"v": 2})}])
    st = os.stat(path)
    os.utime(path, ns=(st.st_atime_ns + 1_000_000, st.st_mtime_ns + 1_000_000))

    assert mod._issuer_rows(path, "observation_json", "ISSUER-A", "label") == ({"v": 2},)
    assert calls["n"] == 2


def test_errors_are_unchanged(tmp_path: Path) -> None:
    """The same exceptions with the same messages as the old algorithm."""
    label = "covenant_term_observations"
    column = "observation_json"

    # no issuer_id column
    path = tmp_path / "no_issuer_id.parquet"
    _write_ledger(path, [{column: json.dumps({"v": 1})}])
    with pytest.raises(ScenarioInputsError, match=f"{label} carries no issuer_id column"):
        mod._issuer_rows(path, column, "ISSUER-A", label)

    # non-string payload, at issuer-local index 1 (row 0 of this issuer is fine)
    path = tmp_path / "non_string.parquet"
    _write_ledger(
        path,
        [
            {"issuer_id": "ISSUER-B", column: json.dumps({"ok": 1})},
            {"issuer_id": "ISSUER-B", column: None},
        ],
    )
    with pytest.raises(ScenarioInputsError, match=f"row 1 lacks a {column} payload"):
        mod._issuer_rows(path, column, "ISSUER-B", label)

    # empty payload
    path = tmp_path / "empty_payload.parquet"
    _write_ledger(path, [{"issuer_id": "ISSUER-B", column: ""}])
    with pytest.raises(ScenarioInputsError, match=f"row 0 lacks a {column} payload"):
        mod._issuer_rows(path, column, "ISSUER-B", label)

    # malformed JSON
    path = tmp_path / "malformed.parquet"
    _write_ledger(path, [{"issuer_id": "ISSUER-B", column: "{not json"}])
    with pytest.raises(ScenarioInputsError, match=f"row 0 has malformed {column}"):
        mod._issuer_rows(path, column, "ISSUER-B", label)

    # valid JSON that is not an object
    path = tmp_path / "not_object.parquet"
    _write_ledger(path, [{"issuer_id": "ISSUER-B", column: "[1, 2]"}])
    with pytest.raises(ScenarioInputsError, match=f"row 0 {column} must be an object"):
        mod._issuer_rows(path, column, "ISSUER-B", label)

    # a malformed row of issuer B does NOT raise when only issuer A is requested
    path = tmp_path / "lazy.parquet"
    _write_ledger(
        path,
        [
            {"issuer_id": "ISSUER-A", column: json.dumps({"v": 1})},
            {"issuer_id": "ISSUER-B", column: "{broken"},
        ],
    )
    assert mod._issuer_rows(path, column, "ISSUER-A", label) == ({"v": 1},)

    # a missing json_column raises KeyError — for the requested issuer and,
    # as before the change, even when the requested issuer has no rows
    path = tmp_path / "missing_column.parquet"
    _write_ledger(path, [{"issuer_id": "ISSUER-A", "other": "{}"}])
    with pytest.raises(KeyError):
        mod._issuer_rows(path, column, "ISSUER-A", label)
    with pytest.raises(KeyError):
        mod._issuer_rows(path, column, "ISSUER-UNKNOWN", label)


def test_returned_rows_are_isolated(tmp_path: Path) -> None:
    """Mutating a returned dict never changes what the next call returns."""
    path = tmp_path / "covenant_term_observations.parquet"
    _write_ledger(path, [{"issuer_id": "ISSUER-A", "observation_json": json.dumps({"v": 1})}])

    first = mod._issuer_rows(path, "observation_json", "ISSUER-A", "label")
    first[0]["v"] = "mutated"
    first[0]["extra"] = "mutated"

    second = mod._issuer_rows(path, "observation_json", "ISSUER-A", "label")
    assert second == ({"v": 1},)
    assert second[0] is not first[0]


def test_cache_is_bounded_to_eight_keys(tmp_path: Path) -> None:
    """Nine distinct (file, json_column) pairs leave at most 8 cache keys, and
    the evicted oldest key still reads correctly when asked again."""
    paths = []
    for i in range(9):
        path = tmp_path / f"ledger_{i}.parquet"
        _write_ledger(path, [{"issuer_id": "ISSUER-A", "observation_json": json.dumps({"i": i})}])
        paths.append(path)
        assert mod._issuer_rows(path, "observation_json", "ISSUER-A", "label") == ({"i": i},)

    assert len(mod._ISSUER_PAYLOAD_CACHE) == 8
    assert str(paths[0].resolve()) not in {key[0] for key in mod._ISSUER_PAYLOAD_CACHE}

    # the evicted first file still answers correctly on a fresh read
    assert mod._issuer_rows(paths[0], "observation_json", "ISSUER-A", "label") == ({"i": 0},)
