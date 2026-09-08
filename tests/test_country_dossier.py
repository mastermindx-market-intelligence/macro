"""Country policy dossier leaf — schema, typed nulls, fail-closed contract."""

from __future__ import annotations

import ast
import copy
import re
from datetime import date, timedelta
from pathlib import Path

import pytest
import yaml

from engine.country_dossier import (
    SCHEMA,
    STANCE_KEYS,
    build_dossier_block,
    dossier_path,
    normalize_dossier,
)
from engine.international_macro_dashboard import (
    REGIONS,
    build_country_view,
    validate_view,
)

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "engine" / "country_dossier.py"
TODAY = date(2026, 9, 6)


def _minimal_ok_yaml(**overrides) -> dict:
    base = {
        "dossier": "xx",
        "schema": SCHEMA,
        "rev": 1,
        "region": "XX",
        "tier": "context_only",
        "reviewed_at": "2026-09-01",
        "review_interval_days": 180,
        "rights": "public",
        "stance": {
            "key": "on_hold",
            "claim": "INFERENCE",
            "known_at": "2026-07-31",
            "evidence": {
                "source_url": "https://example.com/policy",
                "publisher": {"en": "Example Bank", "zh": "示例银行"},
                "document": {"en": "Policy statement", "zh": "政策声明"},
                "version": "2026-07-31",
            },
        },
        "seats": [
            {
                "key": "central_bank",
                "role": {"en": "Governor", "zh": "行长"},
                "institution": {"en": "Example Bank", "zh": "示例银行"},
                "holder": {"en": "A Person", "zh": "某人"},
                "since": "2023-04-10",
                "note": {
                    "en": "Sets the policy rate for the economy.",
                    "zh": "决定政策利率。",
                },
                "claim": "FACT",
                "known_at": "2026-09-01",
                "jurisdiction": "settled",
                "rights": "public",
                "evidence": {
                    "source_url": "https://example.com/board",
                    "publisher": {"en": "Example Bank", "zh": "示例银行"},
                    "document": {"en": "Board members", "zh": "委员会名单"},
                    "version": "2026-09-01",
                },
            }
        ],
    }
    base.update(overrides)
    return base


def _write_yaml(tmp_path: Path, cc: str, data: dict | str | bytes) -> Path:
    d = tmp_path.joinpath("knowledge", "policy_geo", "country_dossier")
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{cc.lower()}.yaml"
    if isinstance(data, bytes):
        path.write_bytes(data)
    elif isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def _jp_record() -> dict:
    spec = REGIONS["JP"]
    return {
        "cc": "JP",
        "name": "Japan",
        "name_zh": "日本",
        "flag": "🇯🇵",
        "date": "2026-07-30",
        "quad": "Q2",
        "quad_name": "Reflation",
        "growth_score": 0.4,
        "inflation_score": 0.25,
        "confidence": 0.55,
        "liquidity": "neutral",
        "recession_score": 20.0,
        "recession_band": "low",
        "data_limited": False,
        "macro": {
            "cpi_yoy": 2.4,
            "gdp_yoy": 1.8,
            "unemployment": 4.1,
            "yield_10y": 3.2,
            "policy_rate": 2.5,
            "curve": 0.7,
            "fx": 100.25,
            "fx_strength_3m": -1.2,
            "drawdown": -5.0,
            "realvol": 18.0,
        },
        "macro_asof": {
            "cpi_yoy": "2026-06",
            "gdp": "2026-04",
            "unemployment": "2026-06",
            "yield_10y": "2026-07",
        },
        "equity": {"drawdown_risk": 32.0},
        "risk_radar": {
            "state": "caution",
            "top_score": 62,
            "dominant_label_en": "Rate shock",
            "dominant_label_zh": "利率冲击",
            "drawdown_prob": {
                "h21": 0.21,
                "measure": ">=5% pullback within 21 business days",
            },
            "scares": [],
        },
        "scope_zh_hint": spec.scope_zh[:2],
    }


def test_real_jp_dossier_is_ok() -> None:
    block = build_dossier_block("JP", today=TODAY)
    assert block["state"] in {"ok", "stale"}
    assert block["schema"] == SCHEMA
    assert 1 <= len(block["seats"]) <= 4
    assert block["stance"]["key"] in STANCE_KEYS
    for seat in block["seats"]:
        assert seat.get("known_at")
        assert seat.get("claim") in {"FACT", "INFERENCE"}
        ev = seat.get("evidence") or {}
        assert str(ev.get("source_url", "")).startswith("https://")


def test_missing_file_is_a_typed_null_not_a_raise(tmp_path: Path) -> None:
    block = build_dossier_block("ZZ", today=TODAY, root=tmp_path)
    assert block["state"] == "no_coverage"
    assert block["stance"] is None
    assert block["seats"] == []
    assert block["reason"] == "file_absent"


def test_malformed_schema_fails_closed(tmp_path: Path) -> None:
    cases = [
        (
            "missing_source_url",
            lambda d: d["seats"][0]["evidence"].pop("source_url"),
        ),
        ("bad_claim", lambda d: d["stance"].__setitem__("claim", "GUESS")),
        (
            "future_known_at",
            lambda d: d["stance"].__setitem__("known_at", "2099-01-01"),
        ),
        (
            "duplicate_seat",
            lambda d: d["seats"].append(copy.deepcopy(d["seats"][0])),
        ),
        ("wrong_schema", lambda d: d.__setitem__("schema", "other.v1")),
        ("bad_tier", lambda d: d.__setitem__("tier", "authority")),
    ]
    for name, mut in cases:
        data = _minimal_ok_yaml()
        mut(data)
        _write_yaml(tmp_path, "XX", data)
        block = build_dossier_block("XX", today=TODAY, root=tmp_path)
        assert block["state"] == "invalid", name
        assert block.get("reason"), name
        assert block["degraded"] is True, name

    _write_yaml(tmp_path, "YY", "{ this is: [not: valid")
    bad = build_dossier_block("YY", today=TODAY, root=tmp_path)
    assert bad["state"] == "invalid"
    assert bad.get("reason")
    assert bad["degraded"] is True


def test_more_than_max_seats_fails_as_seats_reason(tmp_path: Path) -> None:
    """SEAT_KEYS has four members, so a fifth seat cannot be unique.

    The length rule fires before the duplicate-key walk, and that is the
    rule this case exists to pin.
    """
    data = _minimal_ok_yaml()
    seat0 = copy.deepcopy(data["seats"][0])
    data["seats"] = []
    for key in ("head_of_government", "central_bank", "finance", "legislature"):
        seat = copy.deepcopy(seat0)
        seat["key"] = key
        data["seats"].append(seat)
    extra = copy.deepcopy(seat0)
    extra["key"] = "central_bank"
    data["seats"].append(extra)
    assert len(data["seats"]) == 5
    _write_yaml(tmp_path, "XX", data)
    block = build_dossier_block("XX", today=TODAY, root=tmp_path)
    assert block["state"] == "invalid"
    assert block["reason"] == "seats"


def test_validate_view_warns_but_does_not_mutate_invalid(capsys) -> None:
    view = build_country_view(_jp_record(), today=TODAY)
    broken = {
        "schema": SCHEMA,
        "state": "invalid",
        "cc": "JP",
        "reason": "unreadable",
        "degraded": True,
        "review_interval_days": None,
        "stance": None,
        "seats": [],
    }
    view["dossier"] = broken
    before = copy.deepcopy(view["dossier"])
    validate_view(view)
    assert view["dossier"] == before
    assert view["dossier"]["state"] == "invalid"
    assert view["dossier"]["reason"] == "unreadable"
    warning = next(
        line
        for line in capsys.readouterr().out.splitlines()
        if "country-dossier-invalid" in line
    )
    assert warning.startswith("::warning title=country-dossier-invalid::")
    assert "unreadable" in warning


def test_stale_is_a_state_not_an_error(tmp_path: Path) -> None:
    data = _minimal_ok_yaml(reviewed_at=(TODAY - timedelta(days=200)).isoformat())
    _write_yaml(tmp_path, "XX", data)
    block = build_dossier_block("XX", today=TODAY, root=tmp_path)
    assert block["state"] == "stale"
    assert block["stance"] is not None
    assert block["seats"]


def test_rights_suppressed_drops_detail(tmp_path: Path) -> None:
    data = _minimal_ok_yaml(rights="suppressed")
    _write_yaml(tmp_path, "XX", data)
    block = build_dossier_block("XX", today=TODAY, root=tmp_path)
    assert block["state"] == "rights_suppressed"
    assert block["review_interval_days"] == 180
    assert block["degraded"] is False
    assert "holder" not in str(block)

    data2 = _minimal_ok_yaml()
    data2["dossier"] = "xz"
    data2["region"] = "XZ"
    data2["seats"][0]["rights"] = "suppressed"
    data2["seats"][0]["evidence"] = {
        "source_url": "https://example.com/board",
        "publisher": {"en": "Example Bank", "zh": "示例银行"},
        "document": None,
        "version": None,
    }
    _write_yaml(tmp_path, "XZ", data2)
    block2 = build_dossier_block("XZ", today=TODAY, root=tmp_path)
    assert block2["state"] in {"ok", "stale"}
    seat = block2["seats"][0]
    assert seat["state"] == "rights_suppressed"
    assert "holder" not in seat
    assert "note" not in seat


def test_ambiguous_jurisdiction_drops_the_holder(tmp_path: Path) -> None:
    data = _minimal_ok_yaml()
    data["seats"][0]["jurisdiction"] = "ambiguous"
    _write_yaml(tmp_path, "XX", data)
    block = build_dossier_block("XX", today=TODAY, root=tmp_path)
    seat = block["seats"][0]
    assert seat["state"] == "ambiguous_jurisdiction"
    assert "holder" not in seat
    assert seat["role"]["en"]
    assert seat["institution"]["en"]


def test_human_dates_are_formatted_by_the_producer() -> None:
    block = build_dossier_block("JP", today=TODAY)
    assert block["reviewed_at_human_en"]
    assert not re.fullmatch(r"\d{4}-\d{2}-\d{2}", block["reviewed_at_human_en"])
    assert "年" in block["reviewed_at_human_zh"]
    assert block["stance"]["known_at_human_en"]
    assert not re.fullmatch(r"\d{4}-\d{2}-\d{2}", block["stance"]["known_at_human_en"])
    for seat in block["seats"]:
        assert seat["known_at_human_en"]
        assert "年" in seat["known_at_human_zh"]
        if seat.get("since"):
            assert seat["since_human_en"]
            assert not re.fullmatch(r"\d{4}-\d{2}-\d{2}", seat["since_human_en"])


def test_producer_never_raises(tmp_path: Path) -> None:
    hostile = [
        "",
        "[]",
        "42",
        "null",
        b"\x00\x01\xff",
        "seats: null\ndossier: xx\n",
        yaml.safe_dump({**_minimal_ok_yaml(), "reviewed_at": 20260901}),
        yaml.safe_dump({**_minimal_ok_yaml(), "stance": None}),
        yaml.safe_dump({**_minimal_ok_yaml(), "seats": None}),
        "{: broken",
    ]
    for i, payload in enumerate(hostile):
        _write_yaml(tmp_path, f"h{i}", payload)
        block = build_dossier_block(f"H{i}", today=TODAY, root=tmp_path)
        assert isinstance(block, dict)
        assert "state" in block


def test_leaf_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    forbidden_roots = {"engine", "collectors", "pandas", "numpy", "scripts"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                assert root not in forbidden_roots, alias.name
                assert "score" not in alias.name
                assert "regime" not in alias.name
                assert "market_state" not in alias.name
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            root = mod.split(".", 1)[0]
            assert root not in forbidden_roots, mod
            assert "score" not in mod
            assert "regime" not in mod
            assert "market_state" not in mod


def test_no_llm_and_no_network() -> None:
    src = MODULE_PATH.read_text(encoding="utf-8")
    for token in ("requests", "urllib", "httpx", "openai", "anthropic", "socket"):
        assert token not in src


def test_dossier_path_joins_region_stem() -> None:
    assert dossier_path("JP").name == "jp.yaml"


def test_normalize_dossier_marks_invalid_without_mutating() -> None:
    raw = {
        "schema": SCHEMA,
        "state": "invalid",
        "cc": "XX",
        "reason": "schema",
        "degraded": False,
    }
    snapshot = copy.deepcopy(raw)
    out = normalize_dossier(raw)
    assert raw == snapshot
    assert out is not raw
    assert out["state"] == "invalid"
    assert out["degraded"] is True
    assert out["reason"] == "schema"
    covered = normalize_dossier({"schema": SCHEMA, "state": "no_coverage"})
    assert covered["degraded"] is False
    assert covered["state"] == "no_coverage"


def test_jp_chinese_holder_uses_han_not_kana() -> None:
    data = yaml.safe_load(
        (ROOT / "knowledge" / "policy_geo" / "country_dossier" / "jp.yaml").read_text(
            encoding="utf-8"
        )
    )
    finance = next(seat for seat in data["seats"] if seat["key"] == "finance")
    assert finance["holder"]["zh"] == "片山皋月"
    assert not re.search(r"[\u3040-\u30ff]", finance["holder"]["zh"])
    assert not re.search(r"[\u3040-\u30ff]", finance["evidence"]["document"]["zh"])


def _render_view(view: dict) -> str:
    from jinja2 import Environment, FileSystemLoader

    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env.get_template("international_macro.html.j2").render(D=view, RADAR=None)


def _dossier_section(html: str) -> str:
    return html.split('class="imd-section imd-dossier"', 1)[1].split(
        'class="imd-section"', 1
    )[0]


def _assert_en_zh_balance(section: str) -> None:
    en = re.findall(r'<span class="l-en">', section)
    zh = re.findall(r'<span class="l-zh">', section)
    assert len(en) == len(zh)
    assert len(en) >= 2


def test_typed_null_and_degraded_copy_renders_exact_sentences(tmp_path: Path) -> None:
    view = build_country_view(_jp_record(), today=TODAY)

    view["dossier"] = build_dossier_block("ZZ", today=TODAY, root=tmp_path)
    section = _dossier_section(_render_view(view))
    assert (
        "Not tracked yet — we haven't published a policy dossier for this country."
        in section
    )
    assert "尚未收录 — 我们还没有发布该国的政策档案。" in section
    assert "Being re-checked" not in section
    _assert_en_zh_balance(section)

    _write_yaml(tmp_path, "YY", "{ this is: [not: valid")
    view["dossier"] = normalize_dossier(
        build_dossier_block("YY", today=TODAY, root=tmp_path)
    )
    section = _dossier_section(_render_view(view))
    assert "Being re-checked — we're updating this dossier" in section
    assert "正在复核 — 我们正在更新这份档案。" in section
    assert "Not tracked yet" not in section
    assert 'class="imd-card imd-dos-stance s-"' not in section
    _assert_en_zh_balance(section)

    rights = _minimal_ok_yaml(rights="suppressed")
    _write_yaml(tmp_path, "XX", rights)
    view["dossier"] = build_dossier_block("XX", today=TODAY, root=tmp_path)
    section = _dossier_section(_render_view(view))
    assert "We can't republish this source's detail — read it at the publisher." in section
    assert "我们无权转载该来源的细节 — 请前往发布方查看。" in section
    _assert_en_zh_balance(section)

    view["dossier"] = {
        "schema": SCHEMA,
        "state": "mystery",
        "degraded": False,
        "stance": None,
        "seats": [],
    }
    section = _dossier_section(_render_view(view))
    assert "This policy brief isn't ready to show — we're not guessing." in section
    assert "这份政策简报尚未可展示 — 我们不会臆造。" in section
    assert 'class="imd-card imd-dos-stance s-"' not in section
    _assert_en_zh_balance(section)


def test_ambiguous_seat_and_null_since_render_exact_sentences(tmp_path: Path) -> None:
    data = _minimal_ok_yaml()
    data["seats"][0]["jurisdiction"] = "ambiguous"
    _write_yaml(tmp_path, "XX", data)
    view = build_country_view(_jp_record(), today=TODAY)
    view["dossier"] = build_dossier_block("XX", today=TODAY, root=tmp_path)
    section = _dossier_section(_render_view(view))
    assert (
        "Who holds this seat is unsettled right now — we're not naming one office."
        in section
    )
    assert "目前该职位归属尚未明确 — 我们不指定单一机构。" in section
    _assert_en_zh_balance(section)

    legislature = _minimal_ok_yaml()
    legislature["dossier"] = "xl"
    legislature["region"] = "XL"
    seat = copy.deepcopy(legislature["seats"][0])
    seat["key"] = "legislature"
    seat["since"] = None
    legislature["seats"] = [seat]
    _write_yaml(tmp_path, "XL", legislature)
    view["dossier"] = build_dossier_block("XL", today=TODAY, root=tmp_path)
    assert view["dossier"]["seats"][0]["since"] is None
    section = _dossier_section(_render_view(view))
    assert "Start date not published" in section
    assert "未公布任职起始日期" in section
    _assert_en_zh_balance(section)


def test_stale_sentence_is_a_caption_not_a_pill(tmp_path: Path) -> None:
    data = _minimal_ok_yaml(reviewed_at=(TODAY - timedelta(days=200)).isoformat())
    _write_yaml(tmp_path, "XX", data)
    view = build_country_view(_jp_record(), today=TODAY)
    view["dossier"] = build_dossier_block("XX", today=TODAY, root=tmp_path)
    assert view["dossier"]["state"] == "stale"
    html = _render_view(view)
    section = _dossier_section(html)
    chips = section.split('class="imd-dos-chips"', 1)[1].split("</div>", 1)[0]
    assert "Background only" in chips
    assert "仅作背景" in chips
    assert "read it as background" not in chips
    assert "请仅作背景参考" not in chips
    assert 'class="imd-chip fresh"' not in section
    cap = section.split('class="imd-dos-stale-cap"', 1)[1].split("</p>", 1)[0]
    assert "read it as background" in cap
    assert "请仅作背景参考" in cap
    _assert_en_zh_balance(section)


def test_ok_confirmed_chip_keeps_fresh_class() -> None:
    view = build_country_view(_jp_record(), today=TODAY)
    if view["dossier"]["state"] != "ok":
        pytest.skip("live JP dossier is not in the ok state on this pin date")
    section = _dossier_section(_render_view(view))
    assert 'class="imd-chip fresh"' in section
    assert "Background only" not in section


def test_new_dossier_css_has_no_blocking_literals() -> None:
    text = (ROOT / "templates" / "international_macro.html.j2").read_text(encoding="utf-8")
    start = text.index("/* Policy dossier")
    end = text.index(".imd-calendar{")
    chunk = text[start:end]
    assert "#0b1220" not in chunk
    assert "rgba(" not in chunk
    assert "--dos-ink" not in chunk
    assert "border-radius:4px" not in chunk
    assert "border-radius:var(--imd-radius) var(--imd-radius)" not in chunk
    import scripts.check_design_system as ds

    blocking = [
        finding
        for finding in ds.scan_text("templates/international_macro.html.j2", chunk)
        if finding.rule in ds.ADDED_BLOCKING_RULES
    ]
    assert blocking == [], blocking
    assert "var(--r-" in chunk
    assert "var(--imd-shadow)" in chunk
    assert "var(--text)" in chunk
