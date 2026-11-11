"""AI-brief consumer-freshness v2: the dashboard / China / HK builders consume the
machine-readable receipt site/aibrief_freshness.json (written by scripts/build_aibrief.py)
and their AI-brief dialogs render a truthful freshness chip -- or NO chip when the age
cannot be verified. No network, no full site build: the real loaders are called with tmp
site dirs and the real template chip fragments are rendered standalone."""
from __future__ import annotations

import inspect
import json
import re
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"


def _loaders():
    from scripts import build_china, build_hk, build_site
    return {
        "site": build_site._aibrief_lens_freshness,
        "china": build_china._aibrief_lens_freshness,
        "hk": build_hk._aibrief_lens_freshness,
    }


def _lens_of(which: str) -> str:
    return "macro" if which == "site" else "china"


def _receipt(**lens_overrides):
    base = {"generated_at": "2026-11-09T06:30:00+00:00", "refresh_days": 1, "stale": False,
            "state_asof": "2026-11-09", "source": "site"}
    lenses = {lens: {**base, **lens_overrides.get(lens, {})} for lens in ("macro", "china", "btc")}
    return {"built_at": "2026-11-09T07:00:00+00:00", "lenses": lenses}


def _both(**kw):
    return _receipt(macro=dict(kw), china=dict(kw))


def _write(site: Path, payload) -> None:
    site.mkdir(parents=True, exist_ok=True)
    (site / "aibrief_freshness.json").write_text(
        payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")


_BAD_CASES = {
    "missing_receipt": None,
    "malformed_json": "{not json",
    "not_an_object": "[1, 2]",
    "missing_lenses_key": {"built_at": "x"},
    "stale_none": _both(stale=None),
    "stale_string": _both(stale="yes"),
    "refresh_zero": _both(refresh_days=0),
    "refresh_negative": _both(refresh_days=-1),
    "refresh_too_big": _both(refresh_days=8),
    "refresh_bool": _both(refresh_days=True),
    "refresh_float": _both(refresh_days=1.5),
    "refresh_string": _both(refresh_days="1"),
    "refresh_huge_int": _both(refresh_days=10 ** 309),
    "refresh_missing": {"lenses": {k: {"stale": False, "generated_at": "2026-11-09T00:00:00Z"}
                                   for k in ("macro", "china")}},
    "date_none": _both(generated_at=None),
    "date_garbage": _both(generated_at="not-a-date"),
    "date_impossible": _both(generated_at="2026-13-45T00:00:00Z"),
    "date_not_str": _both(generated_at=20261109),
    "lens_not_object": {"lenses": {"macro": "x", "china": 7}},
    "lens_absent": {"lenses": {"btc": _receipt()["lenses"]["btc"]}},
}


@pytest.mark.parametrize("which", ["site", "china", "hk"])
def test_loader_fresh_lens_returns_verified_entry(tmp_path, which):
    _write(tmp_path, _both(refresh_days=3))
    assert _loaders()[which](tmp_path, _lens_of(which)) == {
        "stale": False, "generated_date": "2026-11-09", "refresh_days": 3}


@pytest.mark.parametrize("which", ["site", "china", "hk"])
def test_loader_stale_lens_carries_generated_date(tmp_path, which):
    _write(tmp_path, _both(stale=True, generated_at="2026-11-01T05:00:00+00:00"))
    assert _loaders()[which](tmp_path, _lens_of(which)) == {
        "stale": True, "generated_date": "2026-11-01", "refresh_days": 1}


@pytest.mark.parametrize("case", sorted(_BAD_CASES))
@pytest.mark.parametrize("which", ["site", "china", "hk"])
def test_loader_unverifiable_receipt_is_none_never_raises(tmp_path, which, case):
    payload = _BAD_CASES[case]
    if payload is not None:
        _write(tmp_path, payload)
    assert _loaders()[which](tmp_path, _lens_of(which)) is None


def test_json_nan_cadence_is_none(tmp_path):
    # json.loads accepts NaN; a float cadence is rejected by the int rule.
    _write(tmp_path, '{"lenses": {"macro": {"stale": false, "generated_at": "2026-11-09", '
                     '"refresh_days": NaN}}}')
    assert _loaders()["site"](tmp_path, "macro") is None


def test_the_three_loader_copies_are_identical_source():
    src = {k: inspect.getsource(f) for k, f in _loaders().items()}
    assert src["site"] == src["china"] == src["hk"]


# --- _master_brief_vm (build_site): real loader, tmp site/data dirs ---------------------

def _brief_vm(tmp_path):
    from scripts.build_site import _master_brief_vm
    return _master_brief_vm(site_dir=tmp_path / "site", data_dir=tmp_path / "data")


def test_master_brief_vm_carries_macro_freshness(tmp_path):
    site = tmp_path / "site"
    _write(site, _receipt(macro={"refresh_days": 2}, china={"stale": True}))
    (site / "master_brief.json").write_text(json.dumps({"summary": "s"}), encoding="utf-8")
    vm = _brief_vm(tmp_path)
    assert vm["master_brief"] == {"summary": "s"}
    assert vm["master_brief_freshness"] == {
        "stale": False, "generated_date": "2026-11-09", "refresh_days": 2}


@pytest.mark.parametrize("case", ["missing_receipt", "malformed_json", "lens_absent",
                                  "refresh_zero", "refresh_too_big", "stale_none"])
def test_master_brief_vm_freshness_none_but_brief_survives(tmp_path, case):
    site = tmp_path / "site"
    site.mkdir()
    if _BAD_CASES[case] is not None:
        _write(site, _BAD_CASES[case])
    (site / "master_brief.json").write_text(json.dumps({"summary": "s"}), encoding="utf-8")
    vm = _brief_vm(tmp_path)
    assert vm["master_brief"] == {"summary": "s"}
    assert vm["master_brief_freshness"] is None


def test_master_brief_vm_missing_brief_is_still_empty_fail_open(tmp_path):
    assert _brief_vm(tmp_path) == {}


# --- the real chip fragments, rendered standalone -------------------------------------

_CASES = [("dashboard.html.j2", "master_brief_freshness"),
          ("china.html.j2", "china_brief_freshness"),
          ("hk.html.j2", "china_brief_freshness")]


def _chip_fragment(template: str) -> str:
    src = (TEMPLATES / template).read_text(encoding="utf-8")
    m = re.search(r"\{% set _bf = .*?\n\s*\{% endif %\}\n", src, re.S)
    assert m, f"{template}: freshness chip block not found"
    return m.group(0)


def _render(template: str, key: str, value, define: bool = True) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)))
    ctx = {key: value} if define else {}
    return env.from_string(_chip_fragment(template)).render(**ctx)


@pytest.mark.parametrize("template,key", _CASES)
def test_chip_fresh_daily_and_multi_day(template, key):
    out = _render(template, key, {"stale": False, "generated_date": "2026-11-09", "refresh_days": 1})
    assert "Updates daily" in out and 'data-aibrief-freshness="fresh"' in out
    assert "Last generated" not in out and "aib2-cadence--stale" not in out
    out = _render(template, key, {"stale": False, "generated_date": "2026-11-09", "refresh_days": 3})
    assert "Updates every 3 days" in out and "Updates daily" not in out


@pytest.mark.parametrize("template,key", _CASES)
def test_chip_stale_shows_last_generated_date_and_no_cadence_claim(template, key):
    out = _render(template, key, {"stale": True, "generated_date": "2026-11-01", "refresh_days": 1})
    assert "Last generated 2026-11-01" in out and "上次生成 2026-11-01" in out
    assert "aib2-cadence--stale" in out and 'data-aibrief-freshness="stale"' in out
    assert "Updates daily" not in out and "Updates every" not in out


@pytest.mark.parametrize("template,key", _CASES)
@pytest.mark.parametrize("value", [None, "", 0, [], "stale"])
def test_chip_absent_when_unverified(template, key, value):
    out = _render(template, key, value)
    assert "aib2-cadence" not in out and "Updates" not in out and "Last generated" not in out


@pytest.mark.parametrize("template,key", _CASES)
def test_chip_absent_when_key_undefined_does_not_raise(template, key):
    assert "aib2-cadence" not in _render(template, key, None, define=False)


@pytest.mark.parametrize("template,key", _CASES)
def test_template_wires_chip_and_blanks_raw_cadence(template, key):
    src = (TEMPLATES / template).read_text(encoding="utf-8")
    assert key in src and "refresh_days=none" in src
    # the raw (unverified) brief is no longer passed straight to the shared macro
    assert not re.search(r"aib\.aibrief_body\((master_brief|china_brief),", src)


@pytest.mark.parametrize("lens", ["macro", "china"])
def test_macro_with_blanked_refresh_days_emits_no_raw_cadence_chip(lens):
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)))
    tpl = env.from_string(
        "{% import '_aibrief_body.html.j2' as aib %}"
        "{% call aib.aibrief_body(dict(b, refresh_days=none), lens) %}{% endcall %}")
    brief = {"summary": "s", "refresh_days": 1, "generated_at": "2020-01-01T00:00:00+00:00"}
    out = tpl.render(b=brief, lens=lens)
    assert "Updated daily" not in out and "Updated every" not in out
