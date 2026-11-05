"""macro_sensitivity classification-axis reader (WS:GMI-THEME-GRAPH, lane L07).

Pins the frozen module constants, the pass-through of the incumbent
``macro_sensitivity`` payload into AxisCell v1, the decision order, and the
determinism / read-only discipline. Every reader call asserts
``cell.validate_cell(cell) == []``. Tests never read ``site/**`` or
``data/**`` — injected dicts and ``tmp_path`` only.
"""
from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from engine.classification_axes import cell
from engine.classification_axes import macro_sensitivity as macro_mod
from engine.classification_axes.macro_sensitivity import read_macro_sensitivity

ASOF = "2026-10-09"

# Realistic shape of the incumbent payload that engine/stock_macro_sensitivity.py
# assembles per US stock (values illustrative; bilingual labels included).
FIXTURE_MS = {
    "ticker": "A",
    "rate_beta": 0.455,
    "rate_beta_se": 0.19,
    "t_stat": 2.4,
    "tier": "medium",
    "tier_label": {"en": "Medium", "zh": "中"},
    "duration": "long",
    "duration_label": {"en": "Long-duration", "zh": "长久期"},
    "duration_src": "sector",
    "name_diverges": False,
    "sector_etf": "XLV",
    "sector_beta": 0.175,
    "regime": "headwind",
    "regime_label": {"en": "rate headwind", "zh": "利率逆风"},
    "inflation": "neutral",
    "inflation_label": {"en": "Inflation-neutral", "zh": "通胀中性"},
    "headline": {"en": "x", "zh": "x"},
    "detail": {"en": "x", "zh": "x"},
    "caveat": {"en": "x", "zh": "x"},
    "rate_state": {"en": "x"},
    "infl_state": {"en": "x"},
    "calibrated": True,
    "persist": 0.8,
}
FIXTURE_DOC = {"asof": ASOF, "macro_sensitivity": FIXTURE_MS}

# Frozen table. The module constant is checked against this, not the other way
# around, so a drifted VALUE_KEYS cannot make the projection agree with itself.
FROZEN_VALUE_KEYS = (
    "rate_beta",
    "rate_beta_se",
    "t_stat",
    "tier",
    "tier_label",
    "duration",
    "duration_label",
    "duration_src",
    "name_diverges",
    "sector_etf",
    "sector_beta",
    "regime",
    "regime_label",
    "inflation",
    "inflation_label",
    "calibrated",
    "persist",
    "caveat",
)
FROZEN_SOURCE = {
    "owner": "engine/stock_macro_sensitivity.py",
    "artifact": "site/stockdata/<symbol>.json",
    "field": "macro_sensitivity",
}
EXCLUDED_KEYS = ("ticker", "headline", "detail", "rate_state", "infl_state")


def _expected_value() -> dict:
    return {key: FIXTURE_MS[key] for key in FROZEN_VALUE_KEYS if key in FIXTURE_MS}


def _write_stock(tmp_path: Path, name: str, payload: bytes) -> Path:
    directory = tmp_path / "site" / "stockdata"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.json"
    path.write_bytes(payload)
    return path


# --------------------------------------------------------------------------- #
# frozen surface
# --------------------------------------------------------------------------- #
def test_module_constants_match_the_frozen_spec():
    assert macro_mod.AXIS == "macro_sensitivity"
    assert macro_mod.SOURCE_OWNER == "engine/stock_macro_sensitivity.py"
    assert macro_mod.SOURCE_ARTIFACT == "site/stockdata/<symbol>.json"
    assert macro_mod.MAX_AGE_DAYS == 7
    assert macro_mod.SUBJECT_KINDS == ("co",)
    assert macro_mod.RIGHTS_CONTEXT is None
    assert macro_mod.VALUE_KEYS == FROZEN_VALUE_KEYS
    assert macro_mod.AXIS in cell.AXES


def test_single_public_callable():
    public = {
        name
        for name, obj in inspect.getmembers(macro_mod, inspect.isfunction)
        if not name.startswith("_")
    }
    assert public == {"read_macro_sensitivity"}


# --------------------------------------------------------------------------- #
# the available path
# --------------------------------------------------------------------------- #
def test_injected_doc_reads_available():
    got = read_macro_sensitivity("co:us:A", as_of=ASOF, stock_doc=FIXTURE_DOC)
    assert cell.validate_cell(got) == []
    assert got["schema_version"] == "axis_cell.v1"
    assert got["quality"] == "display_only"
    assert got["axis"] == "macro_sensitivity"
    assert got["subject_id"] == "co:us:A"
    assert got["as_of"] == ASOF
    assert got["status"] == "available"
    assert got["reason_code"] is None
    assert got["value"] == _expected_value()
    assert set(got["value"]) == set(FROZEN_VALUE_KEYS)
    for banned in EXCLUDED_KEYS:
        assert banned not in got["value"]
    assert got["labels"] == ["source_local"]
    assert got["unit"] is None
    assert got["observed_at"] == ASOF
    assert got["freshness"] == {"age_days": 0, "max_age_days": 7}
    assert got["source"] == FROZEN_SOURCE
    assert got["rights_context"] is None


def test_non_finite_floats_become_none_and_the_cell_stays_valid():
    doc = {
        "asof": ASOF,
        "macro_sensitivity": {
            "rate_beta": float("nan"),
            "rate_beta_se": float("inf"),
            "tier": "low",
            "tier_label": {"en": float("-inf"), "zh": "中"},
        },
    }
    got = read_macro_sensitivity("co:us:A", as_of=ASOF, stock_doc=doc)
    assert cell.validate_cell(got) == []
    assert got["status"] == "available"
    assert got["value"]["rate_beta"] is None
    assert got["value"]["rate_beta_se"] is None
    assert got["value"]["tier_label"] == {"en": None, "zh": "中"}


# --------------------------------------------------------------------------- #
# repair r3 defect 2 — a tuple walks exactly like a list
# --------------------------------------------------------------------------- #
def test_tuple_with_nan_becomes_list_with_null():
    doc = {
        "asof": ASOF,
        "macro_sensitivity": {"tier": "medium", "persist": (1.0, float("nan"))},
    }
    got = read_macro_sensitivity("co:us:A", as_of=ASOF, stock_doc=doc)
    assert cell.validate_cell(got) == []
    assert got["status"] == "available"
    assert got["value"]["persist"] == [1.0, None]


# --------------------------------------------------------------------------- #
# freshness window
# --------------------------------------------------------------------------- #
def test_age_8_days_is_stale_with_the_value():
    doc = {"asof": "2026-10-01", "macro_sensitivity": FIXTURE_MS}
    got = read_macro_sensitivity("co:us:A", as_of=ASOF, stock_doc=doc)
    assert cell.validate_cell(got) == []
    assert got["status"] == "stale"
    assert got["reason_code"] == "owner_stale"
    assert got["value"] == _expected_value()
    assert got["freshness"] == {"age_days": 8, "max_age_days": 7}
    assert got["observed_at"] == "2026-10-01"
    assert got["labels"] == ["source_local"]


def test_age_7_days_is_still_available():
    doc = {"asof": "2026-10-02", "macro_sensitivity": FIXTURE_MS}
    got = read_macro_sensitivity("co:us:A", as_of=ASOF, stock_doc=doc)
    assert cell.validate_cell(got) == []
    assert got["status"] == "available"
    assert got["freshness"] == {"age_days": 7, "max_age_days": 7}


def test_observed_after_as_of_is_history_not_supported():
    got = read_macro_sensitivity("co:us:A", as_of="2026-10-08", stock_doc=FIXTURE_DOC)
    assert cell.validate_cell(got) == []
    assert got["status"] == "unknown"
    assert got["reason_code"] == "history_not_supported"
    assert got["value"] is None
    assert got["freshness"] is None
    assert got["labels"] == []


# --------------------------------------------------------------------------- #
# degraded / missing document variants (decision order)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "doc,status,reason,provenance",
    [
        ({"asof": ASOF}, "unknown", "value_missing", ["macro_sensitivity_missing"]),
        (
            {"asof": ASOF, "macro_sensitivity": {}},
            "unknown",
            "value_missing",
            ["macro_sensitivity_missing"],
        ),
        (
            {"asof": ASOF, "macro_sensitivity": "x"},
            "unknown",
            "value_missing",
            ["macro_sensitivity_missing"],
        ),
        (
            {"asof": ASOF, "macro_sensitivity": {"headline": {"en": "x"}}},
            "unknown",
            "value_missing",
            ["macro_sensitivity_empty"],
        ),
        (
            {"macro_sensitivity": FIXTURE_MS},
            "unavailable",
            "owner_degraded",
            ["asof_unparseable"],
        ),
        (
            {"asof": "10/09/2026", "macro_sensitivity": FIXTURE_MS},
            "unavailable",
            "owner_degraded",
            ["asof_unparseable"],
        ),
        (
            {"asof": "2026-13-45", "macro_sensitivity": FIXTURE_MS},
            "unavailable",
            "owner_degraded",
            ["asof_unparseable"],
        ),
        (
            {"asof": 20261009, "macro_sensitivity": FIXTURE_MS},
            "unavailable",
            "owner_degraded",
            ["asof_unparseable"],
        ),
        ([], "unavailable", "owner_degraded", ["document_not_object"]),
        ("garbage", "unavailable", "owner_degraded", ["document_not_object"]),
        # step 4 (macro_sensitivity) precedes step 5 (asof)
        ({}, "unknown", "value_missing", ["macro_sensitivity_missing"]),
    ],
)
def test_missing_and_degraded_variants(doc, status, reason, provenance):
    got = read_macro_sensitivity("co:us:A", as_of=ASOF, stock_doc=doc)
    assert cell.validate_cell(got) == []
    assert got["status"] == status
    assert got["reason_code"] == reason
    assert got["provenance"] == provenance
    assert got["value"] is None
    assert got["freshness"] is None
    assert got["labels"] == []


# --------------------------------------------------------------------------- #
# default file path (root=tmp_path; site/ is never read from the repo)
# --------------------------------------------------------------------------- #
def test_default_path_without_site_dir_is_owner_missing(tmp_path):
    got = read_macro_sensitivity("co:us:A", as_of=ASOF, root=tmp_path)
    assert cell.validate_cell(got) == []
    assert (got["status"], got["reason_code"]) == ("unavailable", "owner_missing")
    assert got["value"] is None


def test_default_path_without_the_file_is_value_missing(tmp_path):
    (tmp_path / "site" / "stockdata").mkdir(parents=True)
    got = read_macro_sensitivity("co:us:A", as_of=ASOF, root=tmp_path)
    assert cell.validate_cell(got) == []
    assert (got["status"], got["reason_code"]) == ("unknown", "value_missing")


def test_default_path_garbage_file_is_owner_degraded(tmp_path):
    _write_stock(tmp_path, "A", b"{not json")
    got = read_macro_sensitivity("co:us:A", as_of=ASOF, root=tmp_path)
    assert cell.validate_cell(got) == []
    assert (got["status"], got["reason_code"]) == ("unavailable", "owner_degraded")
    assert got["provenance"] == ["read_error:JSONDecodeError"]


def test_default_path_empty_file_is_owner_degraded(tmp_path):
    _write_stock(tmp_path, "A", b"")
    got = read_macro_sensitivity("co:us:A", as_of=ASOF, root=tmp_path)
    assert cell.validate_cell(got) == []
    assert (got["status"], got["reason_code"]) == ("unavailable", "owner_degraded")
    assert got["provenance"] == ["read_error:JSONDecodeError"]


def test_default_path_unreadable_bytes_are_owner_degraded(tmp_path):
    _write_stock(tmp_path, "A", b"\xff\xfe\x00bad")
    got = read_macro_sensitivity("co:us:A", as_of=ASOF, root=tmp_path)
    assert cell.validate_cell(got) == []
    assert (got["status"], got["reason_code"]) == ("unavailable", "owner_degraded")
    assert got["provenance"] == ["read_error:UnicodeDecodeError"]


def test_default_path_valid_file_is_available(tmp_path):
    _write_stock(tmp_path, "A", json.dumps(FIXTURE_DOC).encode("utf-8"))
    got = read_macro_sensitivity("co:us:A", as_of=ASOF, root=tmp_path)
    assert cell.validate_cell(got) == []
    assert got["status"] == "available"
    assert got["value"] == _expected_value()


def test_default_path_maps_the_symbol_name_verbatim(tmp_path):
    _write_stock(tmp_path, "BRK.B", json.dumps(FIXTURE_DOC).encode("utf-8"))
    got = read_macro_sensitivity("co:us:BRK.B", as_of=ASOF, root=tmp_path)
    assert cell.validate_cell(got) == []
    assert got["status"] == "available"
    assert got["subject_id"] == "co:us:BRK.B"


# --------------------------------------------------------------------------- #
# repair r3 defect 1 (R-root) — a falsy root falls back to the repo root
# --------------------------------------------------------------------------- #
def test_empty_root_falls_back_to_repo_root(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    directory = repo / "site" / "stockdata"
    directory.mkdir(parents=True)
    (directory / "A.json").write_bytes(json.dumps(FIXTURE_DOC).encode("utf-8"))
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.setattr(macro_mod, "_REPO_ROOT", repo)
    monkeypatch.chdir(elsewhere)
    got = read_macro_sensitivity("co:us:A", as_of=ASOF, root="")
    assert cell.validate_cell(got) == []
    assert got["status"] != "unavailable"
    reference = read_macro_sensitivity("co:us:A", as_of=ASOF, root=repo)
    assert cell.to_json(got) == cell.to_json(reference)


# --------------------------------------------------------------------------- #
# the AxisCellError fallback
# --------------------------------------------------------------------------- #
def test_nested_forbidden_key_degrades_to_invalid_record():
    doc = {"asof": ASOF, "macro_sensitivity": dict(FIXTURE_MS, caveat={"weight": 1})}
    got = read_macro_sensitivity("co:us:A", as_of=ASOF, stock_doc=doc)
    assert cell.validate_cell(got) == []
    assert (got["status"], got["reason_code"]) == ("unavailable", "owner_degraded")
    assert got["provenance"] == ["invalid_record"]
    assert got["value"] is None
    assert got["freshness"] is None
    assert got["labels"] == []


# --------------------------------------------------------------------------- #
# subject-kind / market / epoch gates
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "subject_id",
    ["co:hk:0700", "theme:ai_compute", "etf:SMH", "basket:baskets:semis"],
)
def test_non_us_or_non_company_subjects_are_not_applicable(subject_id):
    got = read_macro_sensitivity(subject_id, as_of=ASOF, stock_doc=FIXTURE_DOC)
    assert cell.validate_cell(got) == []
    assert (got["status"], got["reason_code"]) == ("not_applicable", "not_applicable")
    assert got["value"] is None
    assert got["freshness"] is None
    assert got["labels"] == []


def test_market_provenance_and_identity_epoch_reasons():
    got = read_macro_sensitivity("co:hk:0700", as_of=ASOF, stock_doc=FIXTURE_DOC)
    assert got["provenance"] == ["market:hk"]
    epoch = read_macro_sensitivity("co:us:A#2", as_of=ASOF, stock_doc=FIXTURE_DOC)
    assert cell.validate_cell(epoch) == []
    assert (epoch["status"], epoch["reason_code"]) == ("unknown", "value_missing")
    assert epoch["provenance"] == ["identity_epoch_not_supported"]


@pytest.mark.parametrize(
    "subject_id",
    ["ltheme:finviz:x", "ltheme:ths:885001", "co:us:", "nope:1", "", None, 7],
)
def test_invalid_subjects_propagate_the_contract_error(subject_id):
    with pytest.raises(cell.AxisCellError):
        read_macro_sensitivity(subject_id, as_of=ASOF, stock_doc=FIXTURE_DOC)


# --------------------------------------------------------------------------- #
# repair r3 defect 3 — an invalid as_of is an AxisCellError on every path
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("subject_id", ["co:us:A", "theme:ai_compute"])
@pytest.mark.parametrize("as_of", ["not-a-date", "2026-13-01", "20261012", None])
def test_invalid_as_of_raises_axis_cell_error(subject_id, as_of):
    with pytest.raises(cell.AxisCellError):
        read_macro_sensitivity(subject_id, as_of=as_of, stock_doc=FIXTURE_DOC)


# --------------------------------------------------------------------------- #
# determinism and discipline
# --------------------------------------------------------------------------- #
def test_reader_output_is_byte_deterministic():
    first = cell.to_json(
        read_macro_sensitivity("co:us:A", as_of=ASOF, stock_doc=FIXTURE_DOC)
    )
    second = cell.to_json(
        read_macro_sensitivity("co:us:A", as_of=ASOF, stock_doc=dict(FIXTURE_DOC))
    )
    assert first == second
    stale = cell.to_json(
        read_macro_sensitivity(
            "co:us:A", as_of=ASOF, stock_doc={"asof": "2026-10-01", "macro_sensitivity": FIXTURE_MS}
        )
    )
    assert stale == cell.to_json(
        read_macro_sensitivity(
            "co:us:A", as_of=ASOF, stock_doc={"asof": "2026-10-01", "macro_sensitivity": FIXTURE_MS}
        )
    )


def test_module_source_guard():
    source = Path(macro_mod.__file__).read_text(encoding="utf-8")
    banned = (
        "engine.stock_macro_sensitivity",
        "engine.intelligence_workspace",
        "engine.market_ontology",
        "engine.company_intelligence",
        "classification_axes.geography",
        "classification_axes.sic_industry",
        "classification_axes.business_model",
        "classification_axes.lifecycle",
        "classification_axes.value_chain",
        "import scripts",
        "from scripts",
        "datetime.now",
        "date.today",
        "utcnow",
        "requests",
        "urllib",
        "httpx",
        "socket",
    )
    for needle in banned:
        assert needle not in source, needle
