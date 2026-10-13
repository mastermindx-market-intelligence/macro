"""MUT5A killing tests for stress_set.py survivors after IDRFIX (2026-10-13).

SNI-local DRAFT contract tests. They consume owner-supplied opaque identity
strings (Stock Identity / Data OS) and never mint, derive, or guess issuer
or security identifiers. HISTORICAL-DESCRIPTIVE only: rank_authority,
gate_authority, size_authority, signal_authority, escalation_authority and
trade_authority stay false. Fixtures are synthetic. Residuals are
descriptive, never causal, never a news-impact claim.

Each test_mut5a_stress_set_<function>_<n> docstring names one non-equivalent
mutant that survived the pre-existing importer suite (file:line, original
-> mutated).
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
    check_profile,
    load_profiles,
    _ticker_refusal_key,
)


SYN_NAME = "SyntheticAlpha"


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


def _ok_profile(**kwargs):
    payload = {
        "ticker": "TME",
        "display_name": SYN_NAME,
        "canonical_issuer_id": None,
        "issuer_link": "UNRESOLVED",
        "authority": _authority(),
    }
    payload.update(kwargs)
    return payload


@pytest.fixture(autouse=True)
def _reset_listings_cache():
    ss._REFERENCE_ISSUER_LISTINGS = None
    yield
    ss._REFERENCE_ISSUER_LISTINGS = None


def test_mut5a_stress_set_check_profile_02():
    """stress_set.py:212, `profile.get("authority") or {}` -> `and {}` (bool_swap)."""
    profile = {
        "ticker": "TME",
        "display_name": SYN_NAME,
        "canonical_issuer_id": None,
        "issuer_link": "UNRESOLVED",
    }
    out = check_profile(profile)
    assert out is profile
    assert "authority" not in profile


def test_mut5a_stress_set__ticker_refusal_key_09(tmp_path):
    """stress_set.py:386, `rsplit(".", 1)` -> `rsplit(".", 2)` (const_int 1 -> 2)."""
    assert _ticker_refusal_key("0700.HK.X") == "0700.HK"
    assert _ticker_refusal_key("0700.HK.X") != "0700"
    alias_dir = tmp_path / "pair"
    alias_dir.mkdir()
    _write_profile(alias_dir, "left", ticker="0700", display_name=SYN_NAME)
    _write_profile(alias_dir, "right", ticker="0700.HK.X", display_name=SYN_NAME)
    loaded = load_profiles(alias_dir)
    assert set(loaded) == {"left", "right"}


def test_mut5a_stress_set_load_profiles_11(tmp_path):
    """stress_set.py:457, `p.is_file() and suffix in yml` -> `or` (bool_swap)."""
    d = tmp_path / "profs"
    d.mkdir()
    _write_profile(d, "ok", ticker="TME", display_name=SYN_NAME)
    extra = d / "extra.txt"
    extra.write_text(
        _synthetic_profile_yaml(ticker="ZZZ", display_name=SYN_NAME),
        encoding="utf-8",
    )
    loaded = load_profiles(d)
    assert set(loaded) == {"ok"}
    assert "extra" not in loaded


def test_mut5a_stress_set_check_profile_14():
    """stress_set.py:213, delete `if not isinstance(auth, dict): raise` (del_raise_guard)."""
    with pytest.raises(ValueError, match="authority must be a mapping"):
        check_profile(
            {
                "ticker": "TME",
                "display_name": SYN_NAME,
                "canonical_issuer_id": None,
                "authority": "not-a-mapping",
            }
        )


def test_mut5a_stress_set__reference_issuer_listings_16(monkeypatch):
    """stress_set.py:423, `not isinstance(name, str) or not name.strip()` -> `and` (bool_swap)."""

    def _blank_name(_text):
        return {
            "display_name": "   ",
            "counters": {"c": {"local_code": "ZZZ1"}},
        }

    monkeypatch.setattr(ss, "_load_yaml", _blank_name)
    ss._REFERENCE_ISSUER_LISTINGS = None
    got = ss._reference_issuer_listings()
    assert "" not in got
    assert all(isinstance(k, str) and k.strip() for k in got)


def test_mut5a_stress_set_load_profiles_17(tmp_path):
    """stress_set.py:461, delete `if not isinstance(payload, dict): raise` (del_raise_guard)."""
    d = tmp_path / "bad"
    d.mkdir()
    (d / "scalar.yml").write_text("42\n", encoding="utf-8")
    with pytest.raises(ValueError, match="profile must be a mapping"):
        load_profiles(d)


def test_mut5a_stress_set_check_profile_19():
    """stress_set.py:210, delete `if not isinstance(profile, dict): raise` (del_raise_guard)."""
    with pytest.raises(ValueError, match="profile must be a mapping"):
        check_profile(["not", "a", "mapping"])


def test_mut5a_stress_set_check_profile_27():
    """stress_set.py:227, `return profile` -> `return None` (return_none)."""
    profile = _ok_profile()
    out = check_profile(profile)
    assert out is profile
    assert out["ticker"] == "TME"
    assert out["display_name"] == SYN_NAME


def test_mut5a_stress_set__reference_issuer_listings_28(tmp_path, monkeypatch):
    """stress_set.py:414, `not is_file() or suffix not in yml` -> `and` (bool_swap)."""
    extra = tmp_path / "notes.txt"
    extra.write_text(
        "display_name: %s\n"
        "counters:\n"
        "  c:\n"
        "    local_code: FAKE1\n" % json.dumps(SYN_NAME),
        encoding="utf-8",
    )
    real_iterdir = Path.iterdir

    def _iterdir(self):
        items = list(real_iterdir(self))
        if self.name == "coverage_profiles":
            items.append(extra)
        return iter(items)

    monkeypatch.setattr(Path, "iterdir", _iterdir)
    ss._REFERENCE_ISSUER_LISTINGS = None
    listings = ss._reference_issuer_listings()
    assert SYN_NAME.strip().casefold() not in listings
    check_profile(_ok_profile())
