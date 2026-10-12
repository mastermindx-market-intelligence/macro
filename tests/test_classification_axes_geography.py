"""Geography classification-axis reader (WS:GMI-THEME-GRAPH Taxonomy V2, lane L06).

The reader wraps ``engine.theme_graph.identity_resolution.resolve_graph_node_identity``
and the house security master (``data/reference/security_master.parquet``) and answers
"where is this company node's graph listing listed (country + MIC), as of date D?".
Display/context tier only. Every test injects the resolver — the real resolver is
never called from this file — and every returned cell must pass ``cell.validate_cell``.
"""
from __future__ import annotations

import inspect
from pathlib import Path

import pandas as pd
import pytest

import engine.classification_axes.geography as geography_mod
from engine.classification_axes import cell
from engine.classification_axes.geography import read_geography
from engine.theme_graph.identity_resolution import UnknownGraphNodeError

AS_OF = "2026-10-11"

SUBJECT = "co:us:AAPL"
SECURITY_ID = "SEC:US-XNAS-AAPL"
LISTING_KEY = "US-XNAS-AAPL"


# ---------------------------------------------------------------------------
# Fixtures — in-memory master frames and fake resolvers. No data/** reads.
# ---------------------------------------------------------------------------

def _master_row(**over):
    row = {
        "security_id": SECURITY_ID,
        "listing_key": LISTING_KEY,
        "country": "US",
        "mic": "XNAS",
        "effective_at": "2020-01-01",
        "ingested_at": "2026-10-01T00:00:00Z",
        "security_state": None,
        "superseded_by": None,
    }
    row.update(over)
    return row


def _master_frame(rows=None, drop=None):
    frame = pd.DataFrame(list(rows) if rows is not None else [_master_row()])
    if drop is not None:
        frame = frame.drop(columns=[drop])
    return frame


def _resolver_row(**over):
    row = {
        "node_id": SUBJECT,
        "resolution_state": "RESOLVED",
        "join_method": "master_inception_exact",
        "security_id": SECURITY_ID,
        "listing_key": LISTING_KEY,
        "issuer_id": None,
        "market_scope": "us",
    }
    row.update(over)
    return row


def _resolver(row=None, error=None):
    calls = []

    def _resolve(subject_id, *, asof=None):
        calls.append((subject_id, asof))
        if error is not None:
            raise error
        return dict(row if row is not None else _resolver_row())

    _resolve.calls = calls
    return _resolve


def _read(subject_id=SUBJECT, *, as_of=AS_OF, resolve=None, master=None, root=None):
    got = read_geography(
        subject_id, as_of=as_of, resolve=resolve, master=master, root=root
    )
    assert cell.validate_cell(got) == []
    return got


# ---------------------------------------------------------------------------
# (1) constants + single public callable
# ---------------------------------------------------------------------------

def test_constants_and_single_public_callable():
    assert geography_mod.AXIS == "geography"
    assert geography_mod.SOURCE_OWNER == "scripts/build_security_master.py"
    assert geography_mod.SOURCE_ARTIFACT == "data/reference/security_master.parquet"
    assert geography_mod.MAX_AGE_DAYS is None
    assert geography_mod.SUBJECT_KINDS == ("co",)
    assert geography_mod.RIGHTS_CONTEXT is None
    public = sorted(
        name
        for name, obj in inspect.getmembers(geography_mod, inspect.isfunction)
        if getattr(obj, "__module__", None) == geography_mod.__name__
        and not name.startswith("_")
    )
    assert public == ["read_geography"]


# ---------------------------------------------------------------------------
# (2) RESOLVED + master row <= as_of -> available
# ---------------------------------------------------------------------------

def test_resolved_and_listed_is_available():
    got = _read(resolve=_resolver(), master=_master_frame())
    assert got["status"] == "available"
    assert got["reason_code"] is None
    assert got["value"] == {
        "listing_country": "US",
        "listing_mic": "XNAS",
        "listing_key": LISTING_KEY,
        "domicile": None,
    }
    assert got["unit"] is None
    assert got["observed_at"] == "2020-01-01"
    assert got["effective_at"] == "2020-01-01"
    assert got["as_of"] == AS_OF
    assert got["freshness"] is None
    assert got["labels"] == ["source_local"]
    assert got["provenance"] == [
        "resolution_state:RESOLVED",
        "domicile:no_owner",
        "join_method:master_inception_exact",
    ]
    assert got["source"] == {
        "owner": "scripts/build_security_master.py",
        "artifact": "data/reference/security_master.parquet",
        "field": "country",
    }
    assert got["rights_context"] is None


# ---------------------------------------------------------------------------
# (3) the injected resolver always receives asof=as_of, never None
# ---------------------------------------------------------------------------

def test_resolver_receives_the_caller_asof():
    res = _resolver()
    _read(resolve=res, master=_master_frame())
    assert res.calls == [(SUBJECT, AS_OF)]


# ---------------------------------------------------------------------------
# (4) every effective_at after as_of -> history_not_supported
# ---------------------------------------------------------------------------

def test_effective_after_as_of_is_history_not_supported():
    rows = [_master_row(effective_at="2026-10-12")]
    got = _read(resolve=_resolver(), master=_master_frame(rows))
    assert got["status"] == "unknown"
    assert got["reason_code"] == "history_not_supported"
    assert got["value"] is None
    assert got["labels"] == []
    assert got["provenance"] == ["effective_after_as_of"]


# ---------------------------------------------------------------------------
# (5) two master rows for one security -> the latest row <= as_of wins
# ---------------------------------------------------------------------------

def test_latest_effective_row_at_or_before_as_of_wins():
    rows = [
        _master_row(effective_at="2020-01-01", mic="XNAS"),
        _master_row(effective_at="2024-06-01", mic="XNGS"),
    ]
    got = _read(resolve=_resolver(), master=_master_frame(rows))
    assert got["status"] == "available"
    assert got["value"]["listing_mic"] == "XNGS"
    assert got["observed_at"] == "2024-06-01"
    earlier = _read(as_of="2023-01-01", resolve=_resolver(), master=_master_frame(rows))
    assert earlier["value"]["listing_mic"] == "XNAS"
    assert earlier["observed_at"] == "2020-01-01"
    assert earlier["effective_at"] == "2020-01-01"


# ---------------------------------------------------------------------------
# (6) superseded master rows -> not_applicable/superseded_entity
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "overrides,provenance",
    [
        (
            {"security_state": "SUPERSEDED_DUPLICATE_MINT"},
            ["security_state:SUPERSEDED_DUPLICATE_MINT"],
        ),
        (
            {"superseded_by": "SEC:US-XNAS-OTHER"},
            ["superseded_by:SEC:US-XNAS-OTHER"],
        ),
        (
            {
                "security_state": "SUPERSEDED_DUPLICATE_MINT",
                "superseded_by": "SEC:US-XNAS-OTHER",
            },
            ["security_state:SUPERSEDED_DUPLICATE_MINT", "superseded_by:SEC:US-XNAS-OTHER"],
        ),
    ],
)
def test_superseded_master_row_is_not_applicable(overrides, provenance):
    got = _read(resolve=_resolver(), master=_master_frame([_master_row(**overrides)]))
    assert got["status"] == "not_applicable"
    assert got["reason_code"] == "superseded_entity"
    assert got["value"] is None
    assert got["labels"] == []
    assert got["provenance"] == provenance


# ---------------------------------------------------------------------------
# (7) non-RESOLVED states
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "state",
    [
        "NOT_IN_MASTER",
        "AMBIGUOUS",
        "INVALID_SOURCE_ID",
        "DEFERRED_IDENTITY_EXCEPTION",
        "ENTITY_TYPE_CONFLICT",
        "SOME_FUTURE_STATE",
    ],
)
def test_non_resolved_state_is_value_missing(state):
    got = _read(resolve=_resolver(row=_resolver_row(resolution_state=state)),
                master=_master_frame())
    assert got["status"] == "unknown"
    assert got["reason_code"] == "value_missing"
    assert got["value"] is None
    assert got["labels"] == []
    assert got["provenance"] == [f"resolution_state:{state}"]


def test_unsupported_market_is_not_applicable():
    got = _read(resolve=_resolver(row=_resolver_row(resolution_state="UNSUPPORTED_MARKET")),
                master=_master_frame())
    assert got["status"] == "not_applicable"
    assert got["reason_code"] == "not_applicable"
    assert got["value"] is None
    assert got["labels"] == []
    assert got["provenance"] == ["resolution_state:UNSUPPORTED_MARKET"]


# ---------------------------------------------------------------------------
# (8) resolver raises
# ---------------------------------------------------------------------------

def test_unknown_graph_node_is_value_missing():
    got = _read(resolve=_resolver(error=UnknownGraphNodeError(f"{SUBJECT!r} absent")),
                master=_master_frame())
    assert got["status"] == "unknown"
    assert got["reason_code"] == "value_missing"
    assert got["value"] is None
    assert got["labels"] == []
    assert got["provenance"] == ["graph_node_absent"]


def test_resolver_runtime_failure_is_owner_degraded():
    got = _read(resolve=_resolver(error=RuntimeError("boom")), master=_master_frame())
    assert got["status"] == "unavailable"
    assert got["reason_code"] == "owner_degraded"
    assert got["value"] is None
    assert got["labels"] == []
    assert got["provenance"] == ["resolver_error:RuntimeError"]


# ---------------------------------------------------------------------------
# (9) master access failures
# ---------------------------------------------------------------------------

def test_absent_default_master_file_is_owner_missing(tmp_path):
    res = _resolver()
    got = _read(resolve=res, root=tmp_path)
    assert got["status"] == "unavailable"
    assert got["reason_code"] == "owner_missing"
    assert got["value"] is None
    assert got["labels"] == []
    assert got["provenance"] == ["master_file_absent"]
    assert res.calls == []  # decision order: the master gate precedes the resolver


def test_garbage_master_bytes_are_owner_degraded(tmp_path):
    ref_dir = tmp_path / "data" / "reference"
    ref_dir.mkdir(parents=True)
    (ref_dir / "security_master.parquet").write_bytes(b"definitely not parquet")
    got = _read(resolve=_resolver(), root=tmp_path)
    assert got["status"] == "unavailable"
    assert got["reason_code"] == "owner_degraded"
    assert got["value"] is None
    assert got["labels"] == []
    assert got["provenance"][0].startswith("read_error:")


@pytest.mark.parametrize("column", ["mic", "superseded_by"])
def test_missing_required_master_column_is_owner_degraded(column):
    got = _read(resolve=_resolver(), master=_master_frame(drop=column))
    assert got["status"] == "unavailable"
    assert got["reason_code"] == "owner_degraded"
    assert got["value"] is None
    assert got["labels"] == []
    assert got["provenance"] == [f"missing_column:{column}"]


# ---------------------------------------------------------------------------
# (10) RESOLVED security absent from the master
# ---------------------------------------------------------------------------

def test_security_id_absent_from_master_is_value_missing():
    res = _resolver(row=_resolver_row(security_id="SEC:NOT-THERE", listing_key=None))
    got = _read(resolve=res, master=_master_frame())
    assert got["status"] == "unknown"
    assert got["reason_code"] == "value_missing"
    assert got["value"] is None
    assert got["labels"] == []
    assert got["provenance"] == ["security_id_absent_from_master"]


# ---------------------------------------------------------------------------
# (11) subject kinds the axis does not cover
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("subject_id", ["etf:SPY", "theme:ai_compute"])
def test_uncovered_subject_kind_is_not_applicable(subject_id):
    res = _resolver()
    got = _read(subject_id, resolve=res, master=_master_frame())
    assert got["status"] == "not_applicable"
    assert got["reason_code"] == "not_applicable"
    assert got["value"] is None
    assert got["labels"] == []
    assert res.calls == []


# ---------------------------------------------------------------------------
# (12) determinism
# ---------------------------------------------------------------------------

def test_reader_output_is_byte_stable():
    first = read_geography(SUBJECT, as_of=AS_OF, resolve=_resolver(),
                           master=_master_frame())
    second = read_geography(SUBJECT, as_of=AS_OF, resolve=_resolver(),
                            master=_master_frame())
    assert cell.validate_cell(first) == []
    assert cell.validate_cell(second) == []
    assert cell.to_json(first) == cell.to_json(second)


# ---------------------------------------------------------------------------
# NaN master cells become typed nulls; a null resolver listing_key does not
# narrow the join
# ---------------------------------------------------------------------------

def test_nan_master_cells_become_nulls():
    rows = [_master_row(mic=float("nan"), listing_key=float("nan"))]
    res = _resolver(row=_resolver_row(listing_key=None))
    got = _read(resolve=res, master=_master_frame(rows))
    assert got["status"] == "available"
    assert got["value"] == {
        "listing_country": "US",
        "listing_mic": None,
        "listing_key": None,
        "domicile": None,
    }
    assert got["provenance"] == ["resolution_state:RESOLVED", "domicile:no_owner"]


# ---------------------------------------------------------------------------
# (13) source-text guards
# ---------------------------------------------------------------------------

def test_source_text_guards():
    src = Path(geography_mod.__file__).read_text(encoding="utf-8")
    for banned in (
        "engine.intelligence_workspace",
        "engine.market_ontology",
        "engine.company_intelligence",
        "import scripts",
        "from scripts",
        "datetime.now",
        "date.today",
        "requests",
        "asof=None",
    ):
        assert banned not in src, banned
    for sibling in (
        "sic_industry",
        "macro_sensitivity",
        "business_model",
        "lifecycle",
        "value_chain",
    ):
        assert f"classification_axes.{sibling}" not in src
        assert f"classification_axes import {sibling}" not in src
