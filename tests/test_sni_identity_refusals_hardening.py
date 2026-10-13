"""Hardening tests for SNI identity-refusal findings IDR-F1..F4.

SNI-local DRAFT contract tests. They consume owner-supplied opaque identity
strings from Data OS / Stock Identity. This module never mints, derives, or
guesses issuer or security ids. Fixtures are synthetic. Authority flags stay
literal false.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(
    0,
    str(ROOT / "research" / "single_name_intelligence" / "us_stress"),
)

import stress_set as ss  # noqa: E402
from stress_set import (  # noqa: E402
    AUTHORITY_FLAG_NAMES,
    AuthorityMap,
    check_profile,
    load_profiles,
    _load_yaml,
)

PROFILES_DIR = ROOT / "research" / "single_name_intelligence" / "us_stress" / "profiles"
REAL_STEMS = ("AAPL", "AMZN", "GOOGL", "META", "MSFT", "NVDA", "TSLA")
CYRILLIC_I_ISSUER = "\u0456ssuer_id"
REFUSE_VALUE = "MINTED-FAKE-1"
SYN_NAME = "SyntheticAlpha"
REF_NAME = "Tencent Holdings Ltd"


def _authority():
    return {name: False for name in AUTHORITY_FLAG_NAMES}


def _authority_yaml():
    lines = ["authority:"]
    for name in AUTHORITY_FLAG_NAMES:
        lines.append("  %s: false" % name)
    return "\n".join(lines) + "\n"


def _synthetic_profile_yaml(*, ticker, display_name, extra=""):
    return (
        "ticker: %s\n"
        "display_name: %s\n"
        "canonical_issuer_id: null\n"
        "issuer_link: UNRESOLVED\n"
        "%s"
        "%s"
    ) % (json.dumps(ticker), json.dumps(display_name), extra, _authority_yaml())


def _write_profile(directory, stem, **kwargs):
    path = Path(directory) / ("%s.yml" % stem)
    path.write_text(_synthetic_profile_yaml(**kwargs), encoding="utf-8")
    return path


def _idrh_01_payloads():
    key = CYRILLIC_I_ISSUER
    return (
        {key: REFUSE_VALUE, "authority": _authority()},
        {"layer": {key: REFUSE_VALUE}, "authority": _authority()},
        {"layer1": {"layer2": {key: REFUSE_VALUE}}, "authority": _authority()},
        {"bucket": [{key: REFUSE_VALUE}], "authority": _authority()},
    )


def assert_idrh_01():
    for payload in _idrh_01_payloads():
        with pytest.raises(ValueError, match="non-ASCII profile key refused"):
            check_profile(payload)


def assert_idrh_02(tmp_path, pair, collide):
    alias_dir = tmp_path / "pair"
    alias_dir.mkdir(parents=True, exist_ok=True)
    for child in alias_dir.iterdir():
        if child.is_file():
            child.unlink()
    _write_profile(alias_dir, "left", ticker=pair[0], display_name=SYN_NAME)
    _write_profile(alias_dir, "right", ticker=pair[1], display_name=SYN_NAME)
    if collide:
        with pytest.raises(ValueError, match="ticker alias collision refused"):
            load_profiles(alias_dir)
    else:
        loaded = load_profiles(alias_dir)
        assert set(loaded) == {"left", "right"}


def assert_idrh_03(tmp_path):
    bad_dir = tmp_path / "f3_bad"
    bad_dir.mkdir(exist_ok=True)
    _write_profile(bad_dir, "tme", ticker="TME", display_name=REF_NAME)
    with pytest.raises(ValueError, match="display_name listing mismatch refused"):
        load_profiles(bad_dir)
    good_dir = tmp_path / "f3_good"
    good_dir.mkdir(exist_ok=True)
    _write_profile(good_dir, "syn0700", ticker="0700", display_name=REF_NAME)
    loaded = load_profiles(good_dir)
    assert "syn0700" in loaded
    assert loaded["syn0700"]["ticker"] == "0700"


def assert_idrh_04(tmp_path):
    for value in ("ADMITTED", "admitted", " ADMITTED ", "RESOLVED"):
        with pytest.raises(ValueError, match="identity_state must be null or UNRESOLVED"):
            check_profile(
                {
                    "ticker": "TME",
                    "display_name": SYN_NAME,
                    "identity_state": value,
                    "canonical_issuer_id": None,
                    "authority": _authority(),
                }
            )
    check_profile(
        {
            "ticker": "TME",
            "display_name": SYN_NAME,
            "identity_state": "UNRESOLVED",
            "canonical_issuer_id": None,
            "authority": _authority(),
        }
    )
    check_profile(
        {
            "ticker": "TME",
            "display_name": SYN_NAME,
            "canonical_issuer_id": None,
            "authority": _authority(),
        }
    )
    ok_dir = tmp_path / "id_ok"
    ok_dir.mkdir(parents=True, exist_ok=True)
    _write_profile(
        ok_dir, "ok", ticker="TME", display_name=SYN_NAME, extra="identity_state: UNRESOLVED\n"
    )
    loaded = load_profiles(ok_dir)
    assert loaded["ok"]["identity_state"] == "UNRESOLVED"
    bad_dir = tmp_path / "id_bad"
    bad_dir.mkdir(parents=True, exist_ok=True)
    _write_profile(
        bad_dir, "bad", ticker="TME", display_name=SYN_NAME, extra="identity_state: ADMITTED\n"
    )
    with pytest.raises(ValueError, match="identity_state must be null or UNRESOLVED"):
        load_profiles(bad_dir)


def test_idrh_01():
    assert_idrh_01()


@pytest.mark.parametrize(
    "left,right",
    [
        ("0700", "700"),
        ("0700", " 0700.HK"),
        ("0700", "0700.hk"),
        ("700", " 0700.HK"),
        ("700", "0700.hk"),
        (" 0700.HK", "0700.hk"),
    ],
)
def test_idrh_02(tmp_path, left, right):
    assert_idrh_02(tmp_path, (left, right), collide=True)


def test_idrh_02_non_collision(tmp_path):
    assert_idrh_02(tmp_path, ("0700", "TME"), collide=False)


def test_idrh_03(tmp_path):
    assert_idrh_03(tmp_path)


def test_idrh_04(tmp_path):
    assert_idrh_04(tmp_path)


def test_idrh_05():
    loaded = load_profiles(PROFILES_DIR)
    assert tuple(sorted(loaded)) == tuple(sorted(REAL_STEMS))
    for stem in REAL_STEMS:
        raw = _load_yaml((PROFILES_DIR / ("%s.yml" % stem)).read_text(encoding="utf-8"))
        assert isinstance(raw, dict)
        auth = raw.get("authority")
        if isinstance(auth, dict):
            raw["authority"] = AuthorityMap(auth)
        else:
            raw["authority"] = AuthorityMap()
        assert json.dumps(loaded[stem], sort_keys=True, default=str) == json.dumps(
            raw, sort_keys=True, default=str
        )


def _check_failed(fn):
    try:
        fn()
    except BaseException:
        return True
    return False


@pytest.mark.parametrize("mutant", ("m1", "m2", "m3"))
def test_idrh_06_mutants_are_caught(mutant, monkeypatch, tmp_path):
    if mutant == "m1":
        monkeypatch.setattr(ss, "_REFUSE_NON_ASCII_KEYS", False)
    elif mutant == "m2":
        monkeypatch.setattr(ss, "_STRIP_LEADING_ZEROS", False)
    elif mutant == "m3":
        monkeypatch.setattr(ss, "_IDENTITY_STATE_ALLOWED", (None, "UNRESOLVED", "ADMITTED"))
    else:
        raise AssertionError(mutant)
    failed = []
    if _check_failed(assert_idrh_01):
        failed.append("idrh_01")
    if _check_failed(lambda: assert_idrh_02(tmp_path / "m2", ("0700", "700"), True)):
        failed.append("idrh_02")
    if _check_failed(lambda: assert_idrh_04(tmp_path / "m4")):
        failed.append("idrh_04")
    assert failed, "mutant %s did not make any idrh check fail" % mutant
