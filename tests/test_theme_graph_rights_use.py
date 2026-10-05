"""W-C per-use capture verdict (fresh registry snapshot, fail-closed)."""
from __future__ import annotations

import copy
import datetime as dt
from pathlib import Path
from unittest import mock

import pytest

from engine.theme_graph import rights
from engine.theme_graph.rights_use import (
    PURPOSE,
    PHASES,
    CaptureCapability,
    UseRefusal,
    capture_capability,
    current_use_verdict,
    registry_snapshot,
)

_FROZEN_VERDICT_KEYS = frozenset({
    "verdict",
    "reason_codes",
    "purpose",
    "phase",
    "market",
    "source_ref",
    "source_sha256",
    "generation_id",
    "source_family",
    "rights_class",
    "auth_class",
    "registry_revision",
    "registry_path",
    "evaluated_at",
})

REPO = Path(__file__).resolve().parents[1]
REAL_REGISTRY = REPO / "config" / "theme_sources.yml"


def _registry_bytes(
    *,
    mastermind_class: str = "direct_display_ok",
    extra_families: dict | None = None,
    families_override: dict | None = None,
) -> bytes:
    if families_override is not None:
        fams = families_override
    else:
        fams = {
            "mastermind_curated": {
                "rights_class": mastermind_class,
                "auth_class": "house",
            },
            "finviz_themes": {
                "rights_class": "unresolved",
                "auth_class": "keyless_public",
            },
        }
        if extra_families:
            fams.update(extra_families)
    if not fams:
        return b"version: 1\nfamilies: {}\n"
    text = "version: 1\nfamilies:\n"
    for name, row in fams.items():
        text += f"  {name}:\n"
        for k, v in row.items():
            text += f"    {k}: {v}\n"
    return text.encode("utf-8")


def _valid_request(**overrides) -> dict:
    base = {
        "phase": "capture_write",
        "market": "us_today",
        "source_sha256": "a" * 64,
        "source_ref": "data/baskets/anything.json",
        "purpose": PURPOSE,
        "generation_id": "gen-1",
    }
    base.update(overrides)
    return base


def _write_registry(tmp_path: Path, data: bytes) -> Path:
    p = tmp_path / "theme_sources.yml"
    p.write_bytes(data)
    return p


@pytest.fixture
def reg_path(tmp_path):
    return _write_registry(tmp_path, _registry_bytes())


def test_allowed_direct_display_ok_all_phases(reg_path):
    for phase in PHASES:
        v = current_use_verdict(_valid_request(phase=phase), path=reg_path)
        assert v["verdict"] == "ALLOWED"
        assert v["reason_codes"] == []
        assert v["source_family"] == "mastermind_curated"
        assert v["rights_class"] == "direct_display_ok"


def test_allowed_internal_only(reg_path):
    data = _registry_bytes(mastermind_class="internal_only")
    p = reg_path.parent / "internal.yml"
    p.write_bytes(data)
    v = current_use_verdict(_valid_request(), path=p)
    assert v["verdict"] == "ALLOWED"
    assert v["rights_class"] == "internal_only"


def test_refused_rights_unresolved(reg_path):
    data = _registry_bytes()
    p = reg_path.parent / "finviz_ref.yml"
    p.write_bytes(data)
    req = _valid_request(source_ref="finviz_themes/foo.json")
    # finviz prefix maps to finviz_themes
    req["source_ref"] = "finviz_themes/chunk.json"
    v = current_use_verdict(req, path=p)
    assert v["verdict"] == "REFUSED"
    assert v["reason_codes"] == ["RIGHTS_UNRESOLVED"]


def test_refused_family_not_enrolled(reg_path):
    data = _registry_bytes(families_override={"other_family": {"rights_class": "internal_only", "auth_class": "house"}})
    p = reg_path.parent / "no_mastermind.yml"
    p.write_bytes(data)
    v = current_use_verdict(_valid_request(), path=p)
    assert v["verdict"] == "REFUSED"
    assert v["reason_codes"] == ["FAMILY_NOT_ENROLLED"]
    assert v["source_family"] == "mastermind_curated"


def test_refused_source_family_unresolved_real_registry():
    v = current_use_verdict(
        _valid_request(source_ref="site/factordata/us_standouts.json"),
        path=REAL_REGISTRY,
    )
    assert v["verdict"] == "REFUSED"
    assert v["reason_codes"] == ["SOURCE_FAMILY_UNRESOLVED"]
    assert v["source_family"] is None


def test_registry_missing_between_phases(tmp_path):
    p = _write_registry(tmp_path, _registry_bytes())
    cap = capture_capability(path=p)
    req_write = _valid_request(phase="capture_write")
    assert cap(req_write) is True
    p.unlink()
    req_read = _valid_request(phase="read_use")
    assert cap(req_read) is False
    assert cap.last_verdict["reason_codes"] == ["REGISTRY_MISSING"]


def test_registry_malformed_not_mapping(tmp_path):
    p = tmp_path / "bad.yml"
    p.write_bytes(b"[]\n")
    with pytest.raises(UseRefusal) as exc:
        registry_snapshot(p)
    assert exc.value.code == "REGISTRY_MALFORMED"


def test_registry_malformed_families_list(tmp_path):
    p = tmp_path / "bad2.yml"
    p.write_bytes(b"version: 1\nfamilies: []\n")
    with pytest.raises(UseRefusal) as exc:
        registry_snapshot(p)
    assert exc.value.code == "REGISTRY_MALFORMED"


def test_refused_rights_class_unreadable(reg_path):
    data = _registry_bytes(mastermind_class="typo_class")
    p = reg_path.parent / "typo.yml"
    p.write_bytes(data)
    v = current_use_verdict(_valid_request(), path=p)
    assert v["verdict"] == "REFUSED"
    assert v["reason_codes"] == ["RIGHTS_CLASS_UNREADABLE"]


def test_family_removed_between_phases(tmp_path):
    p = _write_registry(tmp_path, _registry_bytes())
    cap = capture_capability(path=p)
    assert cap(_valid_request(phase="capture_write")) is True
    p.write_bytes(_registry_bytes(families_override={}))
    assert cap(_valid_request(phase="read_use")) is False
    assert cap.last_verdict["reason_codes"] == ["FAMILY_NOT_ENROLLED"]


def test_registry_revision_changes_with_bytes(tmp_path):
    p1 = _write_registry(tmp_path, _registry_bytes())
    r1, _ = registry_snapshot(p1)
    assert r1.startswith("rights_")
    assert len(r1) == len("rights_") + 32
    p1.write_bytes(_registry_bytes(mastermind_class="internal_only"))
    r2, _ = registry_snapshot(p1)
    assert r1 != r2


def test_invalid_use_request_fields_never_raise(reg_path):
    base = _valid_request()
    cases = [
        {"phase": "bogus"},
        {"market": "eu_today"},
        {"source_sha256": "ABC"},
        {"source_sha256": "a" * 63},
        {"source_ref": ""},
        {"purpose": "other"},
        {"generation_id": ""},
        {"generation_id": "../unsafe"},
    ]
    for patch in cases:
        req = {**base, **patch}
        v = current_use_verdict(req, path=reg_path)
        assert v["verdict"] == "REFUSED"
        assert v["reason_codes"] == ["INVALID_USE_REQUEST"]


def test_invalid_non_mapping_request(reg_path):
    v = current_use_verdict("not-a-dict", path=reg_path)
    assert v["verdict"] == "REFUSED"
    assert v["reason_codes"] == ["INVALID_USE_REQUEST"]


def test_capture_capability_bool_never_raises(reg_path):
    cap = capture_capability(path=reg_path)
    assert cap(_valid_request()) is True
    assert cap.last_verdict["verdict"] == "ALLOWED"
    assert cap(42) is False
    assert cap.last_verdict["reason_codes"] == ["INVALID_USE_REQUEST"]


def test_capture_capability_wraps_unexpected_exception(reg_path):
    cap = capture_capability(path=reg_path)
    with mock.patch(
        "engine.theme_graph.rights_use.current_use_verdict",
        side_effect=RuntimeError("boom"),
    ):
        assert cap(_valid_request()) is False
    assert cap.last_verdict["reason_codes"] == ["CAPABILITY_ERROR"]


def test_verdict_dict_key_set_exact(reg_path):
    v = current_use_verdict(_valid_request(), path=reg_path)
    assert set(v.keys()) == _FROZEN_VERDICT_KEYS


def test_determinism_same_bytes(reg_path):
    fixed = dt.datetime(2026, 10, 5, 12, 0, 0, tzinfo=dt.timezone.utc)
    a = current_use_verdict(_valid_request(), path=reg_path, now=fixed)
    b = current_use_verdict(_valid_request(), path=reg_path, now=fixed)
    assert a == b


def test_registry_snapshot_missing(tmp_path):
    p = tmp_path / "missing.yml"
    with pytest.raises(UseRefusal) as exc:
        registry_snapshot(p)
    assert exc.value.code == "REGISTRY_MISSING"


def test_current_use_verdict_registry_malformed_via_path(tmp_path):
    p = tmp_path / "broken.yml"
    p.write_bytes(b"not: [valid\n")
    v = current_use_verdict(_valid_request(), path=p)
    assert v["reason_codes"] == ["REGISTRY_MALFORMED"]


def test_authorize_protocol_end_to_end(reg_path):
    # The D1 seams (PR #8417) consume this module; until they land the cross-wave
    # check skips. importorskip keeps the static first-party-import scanner honest
    # (a `from ... import` inside try/except is still flagged as a swallowed ImportError).
    publication = pytest.importorskip(
        "engine.theme_graph.selection_cohort_publication",
        reason="selection_cohort_publication not on main — see PR #8417",
    )
    _authorize = publication._authorize
    cap = capture_capability(path=reg_path)
    req = _valid_request()
    assert _authorize(cap, copy.deepcopy(req)) is True
    bad = copy.deepcopy(req)
    bad["purpose"] = "wrong"
    with pytest.raises(Exception):
        _authorize(cap, bad)
