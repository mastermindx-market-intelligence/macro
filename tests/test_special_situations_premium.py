"""Tests for engine/special_situations_premium.py (packet B-F09-4).

No network, no `data/` reads — every fixture is self-contained under
tests/fixtures/special_situations/premium_*.json.
"""
from __future__ import annotations

import inspect
import json
import re
from pathlib import Path

import pandas as pd
import pytest

from engine import special_situations_premium as prem

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "special_situations"


def _load(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _closes_series(closes: dict) -> pd.Series:
    idx = pd.to_datetime(list(closes.keys()))
    s = pd.Series(list(closes.values()), index=idx).sort_index()
    return s


def _run_fixture(name: str) -> dict:
    fx = _load(name)
    closes = _closes_series(fx["closes"])
    return prem.premium_for_event(
        fx["event"], closes=closes, lifecycle_row=fx["lifecycle_row"],
        ledger=fx["ledger"], asof="2026-09-06 00:00 UTC")


def test_premium_is_anchored_to_the_announcement_not_the_filing_being_read():
    fx = _load("premium_computed_deal.json")
    row = _run_fixture("premium_computed_deal.json")
    assert row["status"] == "computed"
    # first_date is 2026-06-02; the trading day strictly before it in the fixture IS
    # 2026-06-01 (present in the series at 24.10), reached via a 1-row lag from the
    # searchsorted position. Assert the anchor is NOT the filing-being-read's own
    # 30-rows-back value (2026-05-20, which is what a filing-anchored proxy on
    # date_filed=2026-09-04 would return), and pin every computed value against the
    # fixture's own `expected` block so a wrong-clock regression cannot ship silently.
    assert row["unaffected_price_date"] != "2026-05-20"
    assert row["announcement_filing_date"] == "2026-06-02"
    filing_anchored_price = 21.50  # the 30-rows-back-from-date_filed value in this fixture
    assert row["unaffected_price"] != filing_anchored_price
    expected = fx["expected"]
    assert row["status"] == expected["status"]
    assert row["ticker"] == expected["ticker"]
    assert row["unaffected_price"] == expected["unaffected_price"]
    assert row["unaffected_price_date"] == expected["unaffected_price_date"]
    assert row["premium_pct"] == expected["premium_pct"]


def test_thin_history_announcement_refuses_rather_than_using_the_filing_itself():
    # Blocker-1 regression: a deal with only ONE stored filing has lifecycle()
    # first_date == that filing's own date_filed — never a valid unaffected clock.
    fx = _load("premium_computed_deal.json")
    event = dict(fx["event"])
    lifecycle_row = dict(fx["lifecycle_row"])
    lifecycle_row["n_filings"] = 1
    lifecycle_row["first_date"] = event["date_filed"]
    row = prem.premium_for_event(
        event, closes=_closes_series(fx["closes"]), lifecycle_row=lifecycle_row,
        ledger=fx["ledger"], asof="2026-09-06 00:00 UTC")
    assert row["status"] == "refused"
    assert row["refusal"] == "announcement_not_prior_to_filing"


def test_missing_currency_refuses_rather_than_defaulting_to_usd():
    fx = _load("premium_computed_deal.json")
    event = dict(fx["event"])
    event["llm_terms"] = json.dumps({"price_per_share": 35.0, "consideration": "cash"})
    row = prem.premium_for_event(
        event, closes=_closes_series(fx["closes"]), lifecycle_row=fx["lifecycle_row"],
        ledger=fx["ledger"], asof="2026-09-06 00:00 UTC")
    assert row["status"] == "refused"
    assert row["refusal"] == "currency_mismatch"


def test_computed_premium_names_and_dates_every_input():
    row = _run_fixture("premium_computed_deal.json")
    for key in ("offer_price", "offer_accession", "offer_filing_date", "offer_form_type",
                "announcement_filing_date", "unaffected_price", "unaffected_price_date",
                "amendment_vintage", "currency", "source_url"):
        assert row.get(key) not in (None, ""), f"missing/blank {key}"


def test_absent_offer_terms_refuses_in_plain_words():
    row = _run_fixture("premium_terms_absent.json")
    assert row["status"] == "refused"
    assert row["refusal"] == "offer_terms_absent"
    assert "premium_pct" not in row
    assert row["null_en"]
    assert row["null_zh"]


def test_issuer_join_is_cik_only():
    params = inspect.signature(prem.resolve_issuer).parameters
    assert "company" not in params
    assert set(params) == {"cik", "ledger"}
    # the join body never reads event["company"]/["name"] — it only compares the ledger's
    # CIK values against the supplied cik.
    join_body = "\n".join(inspect.getsource(prem.resolve_issuer).splitlines()[1:])
    assert '"company"' not in join_body and "'company'" not in join_body
    assert '.get("company"' not in join_body
    with pytest.raises(prem.PremiumRefusal) as exc:
        prem.resolve_issuer("not-a-cik", ledger={"SMTI": 714256})
    assert exc.value.reason == "issuer_join_unresolved"


def test_ambiguous_cik_refuses_rather_than_picking_a_share_class():
    row = _run_fixture("premium_join_ambiguous.json")
    assert row["status"] == "refused"
    assert row["refusal"] == "issuer_join_ambiguous"


def test_announcement_before_price_coverage_refuses():
    row = _run_fixture("premium_no_unaffected.json")
    assert row["status"] == "refused"
    assert row["refusal"] == "unaffected_price_unavailable"


def test_module_is_display_only():
    assert prem.SCORED is False
    src = inspect.getsource(prem)
    assert not re.search(r"^\s*(from|import)\s+.*\b(conditions|regime|run)\b", src, re.M)
    banned = re.compile(r"\b(rank|score|expected_return|annualized|signal|target|position|size|edge)\b")
    for name in ("premium_computed_deal", "premium_terms_absent",
                 "premium_join_ambiguous", "premium_no_unaffected"):
        row = _run_fixture(f"{name}.json")
        assert not any(banned.search(str(k)) for k in row.keys())


def test_rights_gated_concepts_are_absent():
    src = inspect.getsource(prem)
    assert not re.search(r"break_fee|financing|antitrust|hsr", src, re.I)
    for name in ("premium_computed_deal", "premium_terms_absent",
                 "premium_join_ambiguous", "premium_no_unaffected"):
        row = _run_fixture(f"{name}.json")
        blob = json.dumps(row)
        assert not re.search(r"break_fee|financing|antitrust|hsr", blob, re.I)


def test_refusal_enum_is_closed():
    for name in ("premium_terms_absent", "premium_join_ambiguous", "premium_no_unaffected"):
        row = _run_fixture(f"{name}.json")
        assert row["refusal"] in prem.REFUSALS
    with pytest.raises(ValueError):
        prem.PremiumRefusal("not_a_real_reason")


def test_snapshot_contract_is_extended_not_forked(monkeypatch):
    from engine import special_situations as ss

    monkeypatch.setattr(ss, "build_situations", lambda: pd.DataFrame())
    snap = ss.snapshot()
    assert snap["scored"] is False
    assert snap["is_context_only"] is True
    assert "disclaimer" in snap
    assert "counts" in snap and "coverage" in snap and "situations" in snap
    assert "premium" in snap


def test_snapshot_exception_fallback_carries_plain_word_nulls(monkeypatch):
    """RED-first (h2 MINOR 2): the snapshot() except fallback used to be
    ``{"status": "refused", "refusal": "computation_unavailable"}`` with no
    ``null_en``/``null_zh``, so the JSON carried a bare machine reason. The
    fallback must be the full ``_refused()`` shape the rendered block already
    uses.
    """
    from engine import special_situations as ss
    from engine import special_situations_premium as prem_mod

    monkeypatch.setattr(ss, "build_situations", lambda: pd.DataFrame())

    def _boom(*_a, **_k):
        raise RuntimeError("forced computation failure")

    monkeypatch.setattr(prem_mod, "featured_premium", _boom)
    snap = ss.snapshot()
    premium = snap["premium"]
    assert premium["status"] == "refused"
    assert premium["refusal"] == "computation_unavailable"
    assert premium.get("null_en"), premium
    assert premium.get("null_zh"), premium
    assert "computation_unavailable" not in premium["null_en"]
    assert "computation_unavailable" not in premium["null_zh"]
    expected = prem_mod._refused("computation_unavailable")
    assert premium["null_en"] == expected["null_en"]
    assert premium["null_zh"] == expected["null_zh"]


def test_receipt_round_trips_the_template_contract(tmp_path, monkeypatch):
    fx = _load("premium_computed_deal.json")
    expected = prem.premium_for_event(
        fx["event"], closes=_closes_series(fx["closes"]), lifecycle_row=fx["lifecycle_row"],
        ledger=fx["ledger"], asof="2026-09-06 00:00 UTC")
    monkeypatch.setattr(prem, "featured_premium", lambda: expected)
    target = tmp_path / "premium_featured.json"
    out = prem.write_receipt(target)
    assert out == target
    from scripts.build_capital_structure_page import _featured_premium
    root = tmp_path
    (root / "data" / "special_situations").mkdir(parents=True, exist_ok=True)
    (root / "data" / "special_situations" / "premium_featured.json").write_text(
        target.read_text(encoding="utf-8"), encoding="utf-8")
    payload = _featured_premium(root)
    assert payload["schema"] == "special_situations.premium.v1"
    assert payload["ticker"] == expected["ticker"]


def _render_premium(premium=None, **kwargs):
    from jinja2 import Environment, FileSystemLoader, StrictUndefined
    repo_root = Path(__file__).parent.parent
    env = Environment(loader=FileSystemLoader(str(repo_root / "templates")),
                       autoescape=True, undefined=StrictUndefined)
    render_kw = dict(active_section="research", active_page="capital_structure",
                     **kwargs)
    if premium is not None:
        render_kw["premium"] = premium
    html = env.get_template("capital_structure.html.j2").render(**render_kw)
    after = html.split('id="cs-premium"', 1)[1]
    if 'id="cs-policy"' in after:
        block = after.split('id="cs-policy"', 1)[0]
    else:
        block = after.split('class="cs-workspace"', 1)[0]
    return html, block


def test_desk_shell_renders_the_premium_block_in_both_languages(tmp_path):
    fx = _load("premium_computed_deal.json")
    premium = prem.premium_for_event(
        fx["event"], closes=_closes_series(fx["closes"]), lifecycle_row=fx["lifecycle_row"],
        ledger=fx["ledger"], asof="2026-09-06 00:00 UTC")
    html, block = _render_premium(premium)
    assert 'id="cs-premium"' in html
    assert premium["unaffected_price_date"] in html
    assert premium["announcement_filing_date"] in html
    assert premium["offer_filing_date"] in html
    assert premium["offer_accession"] in html
    assert f"{premium['premium_pct']:+.1f}%" in html
    assert "SEC accession number" in block
    assert "SEC 文件编号" in block
    assert "SEC filing type" in block
    assert "SEC 披露文件类型" in block
    assert "申报" not in block
    assert "offer_price_provenance" not in block
    assert "None" not in block
    assert "<style" not in html
    repo_root = Path(__file__).parent.parent
    css = (repo_root / "templates" / "capital_structure.css").read_text(encoding="utf-8")
    for cls in re.findall(r'class="([^"]+)"', block):
        for token in cls.split():
            if token.startswith("cs-"):
                assert f".{token}" in css, f"class {token} not defined in capital_structure.css"


def _premium_block_source() -> str:
    src = (Path(__file__).parent.parent / "templates" / "capital_structure.html.j2").read_text(
        encoding="utf-8")
    start = src.index("B-F09-4 PREMIUM BLOCK START")
    end = src.index("B-F09-4 PREMIUM BLOCK END")
    return src[start:end]


def test_premium_block_keeps_ascii_stop_punctuation_inside_t():
    """RED-first (h2 MINOR 1): ``</strong>.`` after ``premium.ticker`` sat
    outside ``t()``, so the ZH sentence closed with an English period.
    """
    block = _premium_block_source()
    assert "</strong>." not in block
    assert "</strong>:" not in block
    assert "{{ t('.', '。') }}" in block
    # Any remaining `.` / `:` / `,` in the block must sit inside a t() call
    # (or a jinja comment / interpolation / HTML attribute), never as a
    # user-facing stop after a value.
    user_bits = re.sub(r"\{#.*?#\}", "", block, flags=re.S)
    user_bits = re.sub(r"\{\{\s*t\((?:.|\n)*?\)\s*\}\}", "", user_bits)
    user_bits = re.sub(r"\{%.*?%\}", "", user_bits, flags=re.S)
    user_bits = re.sub(r"\{\{.*?\}\}", "", user_bits, flags=re.S)
    user_bits = re.sub(r"<[^>]+>", " ", user_bits)
    assert not re.search(r"[.:]", user_bits), user_bits


def test_computed_premium_zh_sentence_closes_with_ideographic_full_stop():
    fx = _load("premium_computed_deal.json")
    premium = prem.premium_for_event(
        fx["event"], closes=_closes_series(fx["closes"]), lifecycle_row=fx["lifecycle_row"],
        ledger=fx["ledger"], asof="2026-09-06 00:00 UTC")
    _, block = _render_premium(premium)
    ticker = premium["ticker"]
    assert f"<strong>{ticker}</strong>." not in block
    assert re.search(
        rf"<strong>{re.escape(ticker)}</strong>"
        r'<span class="l-en">\.</span><span class="l-zh">。</span>',
        block,
    )
    _, null_block = _render_premium(_run_fixture("premium_no_unaffected.json"))
    assert "目前没有可展示的交易。" in null_block or "我们没有该交易公布之前的股价数据。" in null_block
    assert re.search(r"class=\"l-zh\">[^<]*[.:][^<]*</span>", null_block) is None


def test_desk_shell_renders_without_a_receipt():
    html, block = _render_premium(None)
    assert "No deal is ready to show right now." in block
    assert "目前没有可展示的交易。" in block
    assert "申报" not in block
    assert "None" not in block


def test_desk_shell_refuses_ambiguous_join_in_plain_words():
    row = _run_fixture("premium_join_ambiguous.json")
    assert row["status"] == "refused"
    assert "premium_pct" not in row
    _, block = _render_premium(row)
    assert row["null_en"] in block
    assert row["null_zh"] in block
    assert "申报" not in block
    assert "None" not in block
    assert re.search(r"[+\-]?\d+\.\d+%", block) is None


def test_desk_shell_refuses_missing_unaffected_price_in_plain_words():
    row = _run_fixture("premium_no_unaffected.json")
    assert row["status"] == "refused"
    assert "premium_pct" not in row
    _, block = _render_premium(row)
    assert row["null_en"] in block
    assert row["null_zh"] in block
    assert "申报" not in block
    assert "None" not in block
    assert re.search(r"[+\-]?\d+\.\d+%", block) is None


def test_builder_tolerates_a_missing_or_corrupt_receipt(tmp_path):
    from scripts.build_capital_structure_page import _featured_premium
    assert _featured_premium(tmp_path) is None
    d = tmp_path / "data" / "special_situations"
    d.mkdir(parents=True)
    (d / "premium_featured.json").write_text("not json", encoding="utf-8")
    assert _featured_premium(tmp_path) is None
    (d / "premium_featured.json").write_text(json.dumps({"schema": "wrong"}), encoding="utf-8")
    assert _featured_premium(tmp_path) is None


# ── nightly receipt path (MO-B F09-14, MO-PAID-064 live proof) ──────────────
# On origin/main write_receipt() was reachable only from engine/special_situations.py
# main(), which no workflow runs, so the capital-structure panel always printed its
# no-receipt empty state. These tests pin the production shape: the nightly
# build(refresh=True) writes the receipt, build(refresh=False) never does, and the
# write lands after desk_payload() so it reflects tonight's sweep. No network, no
# data/ or site/ writes — tmp_path only.


class _Stop(Exception):
    """Private: aborts build() right after the receipt call, before any render."""


def test_nightly_build_path_writes_the_premium_receipt(tmp_path, monkeypatch, capsys):
    from lib import config
    import scripts.build_special_situations as bss
    fx = _load("premium_computed_deal.json")
    expected = prem.premium_for_event(
        fx["event"], closes=_closes_series(fx["closes"]), lifecycle_row=fx["lifecycle_row"],
        ledger=fx["ledger"], asof="2026-09-06 00:00 UTC")
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path / "data")
    monkeypatch.setattr(prem, "featured_premium", lambda: expected)
    out = bss._write_premium_receipt()
    target = tmp_path / "data" / "special_situations" / "premium_featured.json"
    assert out == target
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema"] == "special_situations.premium.v1"
    assert payload["ticker"] == expected["ticker"]
    lines = [ln for ln in capsys.readouterr().out.splitlines()
             if ln.startswith("[premium-receipt]")]
    assert len(lines) == 1 and lines[0].startswith("[premium-receipt] wrote ")


def test_no_refresh_build_never_touches_the_receipt(tmp_path, monkeypatch):
    from lib import config
    import scripts.build_special_situations as bss
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path / "data")
    calls: list[int] = []

    def _receipt_spy():
        calls.append(1)
        raise AssertionError("receipt must not be written on --no-refresh")

    monkeypatch.setattr(bss, "_write_premium_receipt", _receipt_spy)
    monkeypatch.setattr(bss.sse, "desk_payload",
                        lambda *a, **k: {"situations": [], "built": "2026-09-06 00:00 UTC"})
    monkeypatch.setattr(bss, "_prior_built", lambda: "2026-09-06 00:00 UTC")
    monkeypatch.setattr(bss, "_would_thin_the_desk", lambda n: (True, 5))  # thin-guard exit
    bss.build(refresh=False)
    assert calls == []
    assert not (tmp_path / "data" / "special_situations" / "premium_featured.json").exists()


def test_refresh_build_writes_the_receipt_after_the_desk_payload(tmp_path, monkeypatch):
    import collectors.special_intl as colintl
    import collectors.special_news as colnews
    import collectors.special_prices as colpx
    import collectors.special_situations as col
    import scripts.build_special_situations as bss
    from lib import config
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path / "data")
    no_network = [(col, n) for n in ("fetch_events", "enrich_text", "enrich_filers",
                                     "enrich_classify", "enrich_summaries", "enrich_extraction")]
    no_network += [(colnews, "fetch_news_situations"), (colintl, "fetch_intl_situations"),
                   (colpx, "fetch_arb_prices")]
    for mod, name in no_network:
        monkeypatch.setattr(mod, name, lambda *a, **k: None)
    order: list[str] = []

    def _desk_payload_spy(*a, **k):
        order.append("desk_payload")
        return {"situations": [], "built": "2026-09-06 00:00 UTC"}

    def _receipt_spy():
        order.append("receipt")
        raise _Stop

    monkeypatch.setattr(bss.sse, "desk_payload", _desk_payload_spy)
    monkeypatch.setattr(bss, "_write_premium_receipt", _receipt_spy)
    with pytest.raises(_Stop):
        bss.build(refresh=True)
    assert order == ["desk_payload", "receipt"]
