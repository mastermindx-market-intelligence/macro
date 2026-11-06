"""A03/A04 identity-refusal tests (SNI-local DRAFT contract).

Consumes owner-supplied opaque identity strings from Data OS / Stock
Identity. This module never mints, derives, or guesses issuer or security
ids from a ticker, name, code, or CIK. Unknown identity stays UNRESOLVED
or null. It does not re-implement Data OS identity, Company Event/Earnings,
FIF, Capital Structure, Stock Identity, Options, Research Vault, or
qledger/Evaluation.

Nothing here feeds a ranker, gate, sizer, signal, escalation, or trade
path. rank_authority, gate_authority, size_authority, signal_authority,
escalation_authority and trade_authority stay literal False. Fixtures are
synthetic. Refuse-probe values use the placeholder MINTED-FAKE-1.
"""
from __future__ import annotations

import ast
import json
import re
import socket
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(
    0,
    str(ROOT / "research" / "single_name_intelligence" / "us_stress"),
)

from stress_set import (  # noqa: E402
    AUTHORITY_FLAG_NAMES,
    check_profile,
    load_profiles,
    _IDENTITY_ID_KEYS,
    _load_yaml,
)

SNI_RESEARCH = ROOT / "research" / "single_name_intelligence"
SNI_CONFIG = ROOT / "config" / "single_name_intelligence"
TENCENT_PROFILE = SNI_CONFIG / "coverage_profiles" / "tencent.yml"
ALIBABA_PROFILE = SNI_CONFIG / "coverage_profiles" / "alibaba.yml"

IDENTITY_FOLDED = {name.casefold() for name in _IDENTITY_ID_KEYS}
ISSUER_LEVEL_FOLDED = {
    "canonical_issuer_id",
    "issuer_id",
    "cik",
    "lei",
    "permid",
    "perm_id",
}
NULL_LIKE = {None, "UNRESOLVED"}
# Owner-shaped ISS:/SEC: strings already recorded by Data OS and copied into
# SNI qualification files. Copied from tests/test_single_name_coverage_profiles.py.
# They are recorded owner values, not null sentinels, and not minted here.
OWNER_ISS_RE = re.compile(r"^ISS:[A-Z]{2}-[A-Z]{4}-[A-Z0-9.]+$")
OWNER_SEC_RE = re.compile(r"^SEC:[A-Z]{2}-[A-Z]{4}-[A-Z0-9.]+$")
TICKERISH_RE = re.compile(r"^(?:[A-Z]{1,5}|\d{3,5}(?:\.HK)?|0*\d{6,10})$")

REFUSE_VALUE = "MINTED-FAKE-1"
CYRILLIC_I_ISSUER = "\u0456ssuer_id"  # lookalike of issuer_id; not casefold-equal

IDENTITY_VARIANT_KEYS = (
    " issuer_id ",
    "Issuer_ID",
    "ISSUER_ID",
    "issuer_id\t",
    "canonical_Security_Id",
    "CIK",
    "Isin",
    " figi",
)
ISSUER_LINK_BAD_VALUES = (
    "HK-0700",
    "tencent",
    "0700.HK",
    "",
)
NEST_KINDS = ("depth1", "depth3", "list")

_AUTHORITY_FALSE = {name: False for name in AUTHORITY_FLAG_NAMES}


def _load_structured(path: Path):
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    return _load_yaml(text)


def _iter_committed_structured():
    """JSON/YAML under research/ and config/ SNI trees. data/ is out of scope."""
    for root in (SNI_RESEARCH, SNI_CONFIG):
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".json", ".yml", ".yaml"}:
                continue
            yield path


def _walk_identity_keys(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(key, str) and key.strip().casefold() in IDENTITY_FOLDED:
                yield key, value
            yield from _walk_identity_keys(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_identity_keys(item)


def _identity_value_allowed(value) -> bool:
    if value in NULL_LIKE:
        return True
    if isinstance(value, str) and (OWNER_ISS_RE.match(value) or OWNER_SEC_RE.match(value)):
        return TICKERISH_RE.match(value) is None
    return False


def inspect_committed_identity_keys():
    """Walk committed SNI JSON/YAML identity keys. Returns (n_files, n_keys, bad)."""
    n_files = 0
    n_keys = 0
    bad = []
    for path in _iter_committed_structured():
        n_files += 1
        obj = _load_structured(path)
        for key, value in _walk_identity_keys(obj):
            n_keys += 1
            if not _identity_value_allowed(value):
                rel = path.relative_to(ROOT).as_posix()
                bad.append((rel, key, value))
    return n_files, n_keys, bad


def _load_yaml_file(path: Path) -> dict:
    obj = _load_structured(path)
    assert isinstance(obj, dict), path
    return obj


def assert_tencent_issuer_stays_null():
    profile = _load_yaml_file(TENCENT_PROFILE)
    assert profile["canonical_issuer_id"] == "UNRESOLVED"
    assert profile["issuer_key"] == "tencent"
    counters = profile["counters"]
    assert counters["hkd_0700"]["issuer_link"] == "UNRESOLVED"
    assert counters["rmb_80700"]["issuer_link"] == "UNRESOLVED"
    assert counters["rmb_80700"]["security_id"] == "UNRESOLVED"
    hkd_sid = counters["hkd_0700"]["security_id"]
    assert hkd_sid in NULL_LIKE or (
        isinstance(hkd_sid, str)
        and OWNER_SEC_RE.match(hkd_sid)
        and TICKERISH_RE.match(hkd_sid) is None
    )
    for key, value in _walk_identity_keys(profile):
        folded = key.strip().casefold()
        if folded in ISSUER_LEVEL_FOLDED:
            assert value in NULL_LIKE, (key, value)
        if folded == "issuer_id":
            assert value in NULL_LIKE, (key, value)
    for _name, counter in counters.items():
        assert isinstance(counter, dict)
        assert counter.get("issuer_link") in NULL_LIKE
        for issuer_field in ("issuer_id", "canonical_issuer_id"):
            if issuer_field in counter:
                assert counter[issuer_field] in NULL_LIKE


def _nest(key, value, kind: str) -> dict:
    leaf = {key: value}
    if kind == "depth1":
        payload = dict(leaf)
    elif kind == "depth3":
        payload = {"layer1": {"layer2": dict(leaf)}}
    elif kind == "list":
        payload = {"bucket": [dict(leaf)]}
    else:
        raise AssertionError(kind)
    payload["authority"] = dict(_AUTHORITY_FALSE)
    return payload


def assert_variant_raises(key, value, kind: str) -> None:
    with pytest.raises(ValueError):
        check_profile(_nest(key, value, kind))


def assert_variant_none_passes(key, kind: str) -> None:
    check_profile(_nest(key, None, kind))


def _authority_yaml() -> str:
    lines = ["authority:"]
    for name in AUTHORITY_FLAG_NAMES:
        lines.append("  %s: false" % name)
    return "\n".join(lines) + "\n"


def _synthetic_profile_yaml(*, ticker: str, display_name: str, extra: str = "") -> str:
    body = (
        "ticker: %s\n"
        "display_name: %s\n"
        "canonical_issuer_id: null\n"
        "issuer_link: UNRESOLVED\n"
        "%s"
        "%s"
    ) % (json.dumps(ticker), json.dumps(display_name), extra, _authority_yaml())
    return body


def pin_alias_load_behaviour(tmp_path: Path) -> dict:
    """load_profiles keys by filename stem; colliding aliases and self-asserted identity refuse."""
    alias_dir = tmp_path / "aliases"
    alias_dir.mkdir()
    (alias_dir / "syn0700.yml").write_text(
        _synthetic_profile_yaml(ticker="0700", display_name="SyntheticAlpha"),
        encoding="utf-8",
    )
    (alias_dir / "syn700.yml").write_text(
        _synthetic_profile_yaml(ticker="700", display_name="SyntheticAlpha"),
        encoding="utf-8",
    )
    (alias_dir / "syn0700hk.yml").write_text(
        _synthetic_profile_yaml(ticker=" 0700.HK", display_name="SyntheticAlpha"),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_profiles(alias_dir)

    tme_dir = tmp_path / "tme"
    tme_dir.mkdir()
    (tme_dir / "tme.yml").write_text(
        _synthetic_profile_yaml(
            ticker="TME",
            display_name="Tencent Holdings Ltd",
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_profiles(tme_dir)

    tcehy_dir = tmp_path / "tcehy"
    tcehy_dir.mkdir()
    (tcehy_dir / "tcehy.yml").write_text(
        _synthetic_profile_yaml(
            ticker="TCEHY",
            display_name="Tencent Holdings Ltd",
            extra="identity_state: ADMITTED\n",
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_profiles(tcehy_dir)
    return {"aliases": None, "tme": None, "tcehy": None}


def assert_currency_venue_pairs():
    alibaba = _load_yaml_file(ALIBABA_PROFILE)
    hkd = alibaba["counters"]["hkd_9988"]
    adr = alibaba["counters"]["adr_baba"]
    assert hkd["currency"] == "HKD"
    assert hkd["venue_mic"] == "XHKG"
    assert adr["currency"] == "USD"
    assert adr["venue_mic"] == "XNYS"
    tencent = _load_yaml_file(TENCENT_PROFILE)
    hkd_0700 = tencent["counters"]["hkd_0700"]
    assert hkd_0700["currency"] == "HKD"
    assert hkd_0700["venue_mic"] == "XHKG"


def _rhs_is_constructed(node: ast.AST) -> bool:
    if isinstance(node, ast.JoinedStr):
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr == "format":
            return True
    return False


def _assigned_identity_names(node: ast.AST) -> list[str]:
    names: list[str] = []
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                names.append(target.id)
            elif isinstance(target, ast.Attribute):
                names.append(target.attr)
    elif isinstance(node, ast.AnnAssign):
        target = node.target
        if isinstance(target, ast.Name):
            names.append(target.id)
        elif isinstance(target, ast.Attribute):
            names.append(target.attr)
    return names


def scan_identity_minting(source: str) -> list[dict]:
    """Return assignments of f-string/concat values to identity-key names."""
    tree = ast.parse(source)
    hits: list[dict] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        if value is None or not _rhs_is_constructed(value):
            continue
        for name in _assigned_identity_names(node):
            if name.strip().casefold() in IDENTITY_FOLDED:
                hits.append(
                    {
                        "name": name,
                        "lineno": node.lineno,
                    }
                )
    return hits


def scan_sni_python_for_id_minting():
    hits = []
    n_files = 0
    for path in sorted(SNI_RESEARCH.rglob("*.py")):
        if not path.is_file():
            continue
        n_files += 1
        source = path.read_text(encoding="utf-8")
        for hit in scan_identity_minting(source):
            rel = path.relative_to(SNI_RESEARCH).as_posix()
            hits.append({**hit, "path": rel})
    return n_files, hits


def run_idr_01_through_06(tmp_path: Path) -> None:
    n_files, n_keys, bad = inspect_committed_identity_keys()
    assert n_files > 0
    assert n_keys > 0
    assert bad == []
    assert_tencent_issuer_stays_null()
    for key in IDENTITY_VARIANT_KEYS:
        for kind in NEST_KINDS:
            assert_variant_raises(key, REFUSE_VALUE, kind)
            assert_variant_none_passes(key, kind)
    for value in ISSUER_LINK_BAD_VALUES:
        for kind in NEST_KINDS:
            assert_variant_raises("issuer_link", value, kind)
    for kind in NEST_KINDS:
        assert_variant_none_passes("issuer_link", kind)
        check_profile(_nest("issuer_link", "UNRESOLVED", kind))
    with pytest.raises(ValueError):
        check_profile(_nest(CYRILLIC_I_ISSUER, REFUSE_VALUE, "depth1"))
    pin_alias_load_behaviour(tmp_path)
    assert_currency_venue_pairs()
    n_py, mint_hits = scan_sni_python_for_id_minting()
    assert n_py > 0
    assert mint_hits == []
    control = (
        "ticker = 'ZZZQ'\n"
        "issuer_id = f'HK-{ticker}'\n"
        "canonical_issuer_id = 'X-' + ticker\n"
    )
    control_hits = scan_identity_minting(control)
    assert any(h["name"] == "issuer_id" for h in control_hits)
    assert any(h["name"] == "canonical_issuer_id" for h in control_hits)


def test_idr_01_committed_artifacts_hold_no_minted_id():
    n_files, n_keys, bad = inspect_committed_identity_keys()
    print(
        "IDR-01 inspected %d files and %d identity keys "
        "(roots research/single_name_intelligence, "
        "config/single_name_intelligence)" % (n_files, n_keys)
    )
    assert n_files > 0, "no committed JSON/YAML under SNI research/config roots"
    assert n_keys > 0, "no identity keys found; walker is vacuous"
    assert bad == [], "minted or non-allowed identity values:\n" + "\n".join(
        "%s %s=%r" % row for row in bad
    )


def test_idr_02_tencent_issuer_stays_null():
    assert_tencent_issuer_stays_null()


@pytest.mark.parametrize("kind", NEST_KINDS)
@pytest.mark.parametrize("key", IDENTITY_VARIANT_KEYS)
def test_idr_03_key_variants_refused(key, kind):
    assert_variant_raises(key, REFUSE_VALUE, kind)
    assert_variant_none_passes(key, kind)


@pytest.mark.parametrize("kind", NEST_KINDS)
@pytest.mark.parametrize("value", ISSUER_LINK_BAD_VALUES)
def test_idr_03_issuer_link_variants_refused(value, kind):
    assert_variant_raises("issuer_link", value, kind)
    assert_variant_none_passes("issuer_link", kind)
    check_profile(_nest("issuer_link", "UNRESOLVED", kind))


def test_idr_03_unicode_lookalike_refused():
    with pytest.raises(ValueError):
        check_profile(_nest(CYRILLIC_I_ISSUER, REFUSE_VALUE, "depth1"))


def test_idr_04_alias_cannot_cross_bind(tmp_path):
    pin_alias_load_behaviour(tmp_path)


def test_idr_04_leading_zero_aliases_refused(tmp_path):
    alias_dir = tmp_path / "aliases"
    alias_dir.mkdir()
    (alias_dir / "syn0700.yml").write_text(
        _synthetic_profile_yaml(ticker="0700", display_name="SyntheticAlpha"),
        encoding="utf-8",
    )
    (alias_dir / "syn700.yml").write_text(
        _synthetic_profile_yaml(ticker="700", display_name="SyntheticAlpha"),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_profiles(alias_dir)


def test_idr_04_tme_tencent_refused(tmp_path):
    tme_dir = tmp_path / "tme"
    tme_dir.mkdir()
    (tme_dir / "tme.yml").write_text(
        _synthetic_profile_yaml(
            ticker="TME",
            display_name="Tencent Holdings Ltd",
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_profiles(tme_dir)


def test_idr_04_tcehy_admitted_issuer_refused(tmp_path):
    tcehy_dir = tmp_path / "tcehy"
    tcehy_dir.mkdir()
    (tcehy_dir / "tcehy.yml").write_text(
        _synthetic_profile_yaml(
            ticker="TCEHY",
            display_name="Tencent Holdings Ltd",
            extra="identity_state: ADMITTED\n",
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_profiles(tcehy_dir)


def test_idr_05_currency_venue_mismatch():
    assert_currency_venue_pairs()


def test_idr_06_no_id_minting_helpers():
    n_py, hits = scan_sni_python_for_id_minting()
    print("IDR-06 scanned %d Python files under research/single_name_intelligence" % n_py)
    assert n_py > 0
    assert hits == [], "identity-id minting assignments:\n" + "\n".join(
        "%s:%s %s" % (h["path"], h["lineno"], h["name"]) for h in hits
    )
    control = (
        "ticker = 'ZZZQ'\n"
        "issuer_id = f'HK-{ticker}'\n"
        "canonical_issuer_id = 'X-' + ticker\n"
    )
    control_hits = scan_identity_minting(control)
    assert control_hits, "positive control must detect constructed identity assignments"
    names = {h["name"] for h in control_hits}
    assert "issuer_id" in names
    assert "canonical_issuer_id" in names


def test_idr_07_pure(monkeypatch, tmp_path):
    def boom(*_args, **_kwargs):
        raise RuntimeError("IDR-07: subprocess/socket forbidden")

    monkeypatch.setattr(subprocess, "run", boom)
    monkeypatch.setattr(socket, "socket", boom)
    run_idr_01_through_06(tmp_path)
