"""RIC F3 W3 — credit_momentum consumes the live yield_momentum organ.

Coverage (RED-first, pinned to fixture shape at
`tests/fixtures/transmission/yield_momentum_latest.json`):
  1. live tenors + null tenors: block mirrors values, as_of copied, null_reason
     verbatim, state=="live".
  2. artifact missing -> accruing note, no raise, interim_tlt unchanged.
  3. all-null artifact -> state=="accruing", no numbers.
  4. no ledger event minted for any yield tenor (forward log / ledger_events
     count unchanged with the artifact present).
  5. authority is False; yield_momentum absent from credit_market_turn legs and
     theme tags.
  6. determinism (two builds identical).
  7. no clock read in the new function's source.

Zero network calls. All inputs are synthetic (tmp_path fixtures). The fixture
artificial-tenor order is 2y/5y/10y/20y/30y (RIC F3 spec §"Per tenor").
"""
from __future__ import annotations

import inspect
import json
import shutil
from pathlib import Path

import pytest

from engine import credit_momentum


# ---------------------------------------------------------------------------
# Paths / fixtures
# ---------------------------------------------------------------------------

_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "transmission" / "yield_momentum_latest.json"


def _install_artifact(root: Path, fixture: Path | None = _FIXTURE_PATH) -> None:
    """Drop a `data/transmission/latest.json` into the synthetic root."""
    dest = root / "data" / "transmission" / "latest.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if fixture is None:
        return
    shutil.copy(fixture, dest)


def _build_all_null_artifact(root: Path) -> None:
    """Write an all-null yield_momentum artifact (every tenor null)."""
    dest = root / "data" / "transmission" / "latest.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "yield_momentum": {
            "asof": "2026-09-25",
            "authority": False,
            "calculation_version": "fixed_grid_origin.v4",
            "can_score": False,
            "can_size": False,
            "can_trade": False,
            "display_only": True,
            "schema": "yield_momentum.v1",
            "measurement_origin": None,
            "series": {
                t: {
                    "as_of": None,
                    "velocity_bp": {"5d": None, "22d": None, "63d": None},
                    "turn_watch": None,
                    "measurement_origin": "last_captured_source_row",
                    "trailing_publication_lag_rows": None,
                    "path_qualified": False,
                    "null_reason": f"all-null fixture — tenor {t} absent",
                    "status": "missing",
                    "level": None,
                }
                for t in ("2y", "5y", "10y", "20y", "30y")
            },
        }
    }
    dest.write_text(json.dumps(payload, indent=2))


def _read_fixture_payload() -> dict:
    with open(_FIXTURE_PATH) as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Test 1 — live tenors + null tenors mirror, as_of copied, null_reason verbatim
# ---------------------------------------------------------------------------

def test_block_mirrors_live_and_null_tenors(tmp_path: Path) -> None:
    _install_artifact(tmp_path)
    fixture = _read_fixture_payload()["yield_momentum"]

    block = credit_momentum._build_yield_momentum_block(tmp_path)

    # Header
    assert block["calculation_version"] == fixture["calculation_version"]
    assert block["asof"] == fixture["asof"]
    assert block["authority"] is False
    assert "rates program yield organ" in block["_label"]
    # state is live because at least one tenor has a non-null velocity_bp.22d
    assert block["state"] == "live"

    # Tenor order is 2y/5y/10y/20y/30y (RIC F3 spec); only tenors present appear
    tenors = block["tenors"]
    assert list(tenors.keys()) == ["2y", "5y", "10y", "20y", "30y"]

    # Live tenor: as_of copied verbatim from artifact (per-series, not frame)
    live_2y = fixture["series"]["2y"]
    assert tenors["2y"]["as_of"] == live_2y["as_of"]  # '2026-09-24', NOT the frame date
    assert tenors["2y"]["velocity_bp"] == live_2y["velocity_bp"]
    assert tenors["2y"]["turn_watch"] == live_2y["turn_watch"]
    assert tenors["2y"]["measurement_origin"] == live_2y["measurement_origin"]
    assert tenors["2y"]["trailing_publication_lag_rows"] == live_2y["trailing_publication_lag_rows"]
    assert tenors["2y"]["path_qualified"] == live_2y["path_qualified"]
    assert tenors["2y"]["null_reason"] is None  # live tenor has no null_reason

    # Null tenor: null_reason verbatim
    null_10y = fixture["series"]["10y"]
    assert tenors["10y"]["as_of"] is None
    assert tenors["10y"]["velocity_bp"] == {"5d": None, "22d": None, "63d": None}
    assert tenors["10y"]["null_reason"] == null_10y["null_reason"]
    assert "path_qualified" in tenors["10y"]


# ---------------------------------------------------------------------------
# Test 2 — artifact missing -> accruing note, no raise, interim_tlt unchanged
# ---------------------------------------------------------------------------

def test_missing_artifact_yields_accruing_note_and_does_not_touch_interim_tlt(
    tmp_path: Path,
) -> None:
    """Snapshot with no artifact yields `note: yield_momentum artifact not available`
    AND the interim_tlt block is byte-identical to a snapshot without the
    artifact path at all."""
    # Run 1 — artifact present (use the pinned fixture, but the consumer should
    # NOT alter interim_tlt regardless of which path runs).
    root_with = tmp_path / "with"
    root_with.mkdir()
    _install_artifact(root_with)

    # Run 2 — artifact absent (use a fresh root; we only build interim_tlt,
    # which depends on Yahoo parquet, so we mock by isolating the interim
    # block from the rest of the snapshot — direct comparison).
    root_without = tmp_path / "without"
    root_without.mkdir()

    block_missing = credit_momentum._build_yield_momentum_block(root_without)
    assert block_missing["state"] == "accruing"
    assert block_missing["authority"] is False
    assert "rates program yield organ" in block_missing["_label"]
    assert block_missing["note"] == "yield_momentum artifact not available"

    # interim_tlt is built independently of yield_momentum. Call it with an
    # empty all_events list — it does not touch the yield_momentum block.
    interim_tlt_a = credit_momentum._build_interim_tlt(root_with, [])
    interim_tlt_b = credit_momentum._build_interim_tlt(root_without, [])
    assert interim_tlt_a == interim_tlt_b
    # The interim block is byte-identical: the interim label is preserved.
    assert interim_tlt_a["_label"] == credit_momentum._INTERIM_LABEL


# ---------------------------------------------------------------------------
# Test 3 — all-null artifact -> state=="accruing", no numbers
# ---------------------------------------------------------------------------

def test_all_null_artifact_yields_accruing_state_with_no_numbers(
    tmp_path: Path,
) -> None:
    _build_all_null_artifact(tmp_path)

    block = credit_momentum._build_yield_momentum_block(tmp_path)

    assert block["state"] == "accruing"
    assert block["authority"] is False
    # Every tenor shows null velocity_bp; no fabricated numbers
    for tenor, body in block["tenors"].items():
        assert body["velocity_bp"] == {"5d": None, "22d": None, "63d": None}, tenor
        assert body["as_of"] is None
        assert body.get("level") is None  # level is not in the spec's per-tenor field set; no fabrication
    # null_reasons carried verbatim from artifact
    null_reasons = block.get("null_reasons", [])
    assert any("all-null fixture" in r for r in null_reasons), null_reasons


# ---------------------------------------------------------------------------
# Test 4 — no ledger event minted for any yield tenor
# ---------------------------------------------------------------------------

def test_no_ledger_event_minted_for_yield_momentum(monkeypatch, tmp_path: Path) -> None:
    """The yield_momentum block must not extend `ledger_events` or call
    `_upsert_forward_log`. Verified by snapshotting once with the artifact and
    once without; the ledger event count is the same in both."""
    import engine.credit_momentum as cm

    captured: dict[str, int] = {}

    real_upsert = cm._upsert_forward_log

    def spy_upsert(events, root, sessions):
        captured["events"] = len(events)
        return 0  # never write

    monkeypatch.setattr(cm, "_upsert_forward_log", spy_upsert)

    # Run 1: with artifact
    root_with = tmp_path / "with"
    root_with.mkdir()
    _install_artifact(root_with)
    cm.snapshot(root=root_with)
    with_events = captured["events"]

    # Run 2: without artifact
    root_without = tmp_path / "without"
    root_without.mkdir()
    cm.snapshot(root=root_without)
    without_events = captured["events"]

    assert with_events == without_events, (
        f"yield_momentum changed ledger event count: with={with_events} "
        f"without={without_events}"
    )

    # And: yield_momentum block must NOT be in the ledger events payload. The
    # block does not produce any "yield_momentum" or "yield_<tenor>" series_id.
    # The snapshot itself never added such an event.
    snapshot_payload = cm.snapshot(root=root_with)
    forward_log_path = root_with / "corp_bonds" / "forward_log.jsonl"
    if forward_log_path.exists():
        ids = [
            json.loads(line).get("series_id")
            for line in forward_log_path.read_text().splitlines()
            if line.strip()
        ]
    else:
        ids = []
    assert not any("yield" in (s or "") for s in ids), (
        f"yield_momentum bled into forward log series_id: {ids}"
    )

    # The snapshot's reported ledger new count is also unchanged.
    assert snapshot_payload.get("_n_ledger_new") == 0

    monkeypatch.setattr(cm, "_upsert_forward_log", real_upsert)


# ---------------------------------------------------------------------------
# Test 5 — authority is False; yield_momentum absent from tags / K-of-N inputs
# ---------------------------------------------------------------------------

def test_authority_is_false_and_block_is_isolated_from_tags(tmp_path: Path) -> None:
    _install_artifact(tmp_path)

    # Direct call
    block = credit_momentum._build_yield_momentum_block(tmp_path)
    assert block["authority"] is False

    # The yield_momentum block does not appear as a series_id in any tag legs
    # of the snapshot's tag assembly. We don't run the full snapshot because
    # that needs many inputs; we instead grep the source for any reference to
    # yield_momentum in the tag paths.
    src = inspect.getsource(credit_momentum)
    # The new function is the only place that mentions yield_momentum except
    # for the assembly/wiring block. Slice on the tag-computing functions.
    for fn_name in (
        "_compute_credit_market_turn_tag",
        "_compute_credit_theme_stress_tag",
        "_build_series_state",
    ):
        fn_src = inspect.getsource(getattr(credit_momentum, fn_name))
        assert "yield_momentum" not in fn_src, (
            f"{fn_name} references yield_momentum — block must not bleed into tags"
        )


# ---------------------------------------------------------------------------
# Test 6 — determinism: two builds are identical
# ---------------------------------------------------------------------------

def test_deterministic_build_is_byte_identical(tmp_path: Path) -> None:
    _install_artifact(tmp_path)

    block_a = credit_momentum._build_yield_momentum_block(tmp_path)
    block_b = credit_momentum._build_yield_momentum_block(tmp_path)
    assert block_a == block_b


# ---------------------------------------------------------------------------
# Test 7 — no clock read in the new function's source
# ---------------------------------------------------------------------------

def test_no_clock_read_in_new_function_source() -> None:
    src = inspect.getsource(credit_momentum._build_yield_momentum_block)
    # Forbidden: wall-clock reads of any kind
    assert ".now(" not in src, "yield_momentum block must not call .now()"
    assert ".today(" not in src, "yield_momentum block must not call .today()"
    assert "datetime.now" not in src
    assert "date.today" not in src
    assert "time.time()" not in src
    assert "datetime." not in src  # no datetime import either