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


# ---------------------------------------------------------------------------
# Nonfinite market-cap regressions: NaN / +Inf / -Inf market caps — as floats
# and as numeric strings ("nan", "inf", "-inf", "Infinity", "1e999") — must
# take the existing missing-value path everywhere:
#   engine  _mc_bucket     -> None
#   builder _mc_bucket     -> "unknown"
#   builder _usd_m         -> em dash "—"
#   engine  _compute_setup -> 0.9 missing-cap multiplier
# None and unparseable strings stay missing; zero, negative, and finite
# boundary values keep their ordinary treatment (300 / 2000 / 10000 bands).
# ---------------------------------------------------------------------------

_NONFINITE_MC_PARAMS = [
    pytest.param(float("nan"), id="nan-float"),
    pytest.param(float("inf"), id="inf-float"),
    pytest.param(float("-inf"), id="neg-inf-float"),
    pytest.param("nan", id="nan-str"),
    pytest.param("NaN", id="NaN-str"),
    pytest.param("inf", id="inf-str"),
    pytest.param("-inf", id="neg-inf-str"),
    pytest.param("Infinity", id="Infinity-str"),
    pytest.param("-Infinity", id="neg-Infinity-str"),
    pytest.param("1e999", id="overflow-1e999-str"),
]

_MISSING_MC_PARAMS = [
    pytest.param(None, id="none"),
    pytest.param("", id="empty-str"),
    pytest.param("abc", id="invalid-str"),
    pytest.param("N/A", id="na-str"),
]

# Grade-cross shape: raw=71 with a finite mc (grade A) vs 63.9 after the 0.9
# missing-cap (grade B). Mirrors the retained 2026-10-13 Acquisitions record.
_GRADE_CROSS_TECH  = {"tier": "T2", "tier_eligible": True, "tier_provisional": False,
                      "washout_2w": True, "washout_1m": False,
                      "w1_macd": "near", "w1_stoch": None}
_GRADE_CROSS_FAVOR = {"sector_stance": "Neutral", "rotation": None,
                      "theme_ready": None, "theme_score": None, "standout": None}
_SIMPLE_TECH       = {"tier": None, "tier_eligible": True, "tier_provisional": False,
                      "washout_2w": False, "washout_1m": False,
                      "w1_macd": "near", "w1_stoch": None}


def _grade_cross_sit(mc_musd):
    return {
        "ticker": "AAA", "company": "Test Co", "category": "Acquisitions",
        "stage": "announced", "mc_musd": mc_musd, "confidence": "high",
        "source_lane": "edgar", "live": True, "terminal": None,
        "prior": {"win_20d_pct": 65.0, "med_ret_20d_pct": 2.5, "n": 50,
                  "match_label": "Acquisitions"},
    }


# --- engine _mc_bucket -------------------------------------------------------

@pytest.mark.parametrize("bad", _NONFINITE_MC_PARAMS)
def test_engine_mc_bucket_nonfinite_is_missing(bad):
    """NaN/+Inf/-Inf (scalar or numeric string) must bucket as missing (None)."""
    from engine import special_sits_intel as ssi

    assert ssi._mc_bucket(bad) is None


@pytest.mark.parametrize("missing", _MISSING_MC_PARAMS)
def test_engine_mc_bucket_missing_stays_missing(missing):
    from engine import special_sits_intel as ssi

    assert ssi._mc_bucket(missing) is None


@pytest.mark.parametrize(
    "mc,expected",
    [
        pytest.param(0, "micro", id="zero"),
        pytest.param(-500, "micro", id="neg-finite"),
        pytest.param(299.9, "micro", id="just-under-300"),
        pytest.param(300, "small", id="at-300"),
        pytest.param(1999.9, "small", id="just-under-2000"),
        pytest.param(2000, "mid", id="at-2000"),
        pytest.param(9999.9, "mid", id="just-under-10000"),
        pytest.param(10000, "large", id="at-10000"),
        pytest.param(250000, "large", id="large-cap"),
        pytest.param("0", "micro", id="zero-str"),
        pytest.param("-500", "micro", id="neg-finite-str"),
        pytest.param("1e-999", "micro", id="underflow-to-zero-str"),
    ],
)
def test_engine_mc_bucket_zero_and_finite_boundaries_preserved(mc, expected):
    """Legitimate zero/negative/finite values keep the 300/2000/10000 bands."""
    from engine import special_sits_intel as ssi

    assert ssi._mc_bucket(mc) == expected


# --- engine _compute_setup missing-cap ----------------------------------------

@pytest.mark.parametrize("bad", _NONFINITE_MC_PARAMS)
def test_engine_compute_setup_nonfinite_mc_takes_missing_cap(bad):
    """Nonfinite mc must apply the 0.9 missing-cap: 71 raw -> 63.9 (A drops to B)."""
    from engine import special_sits_intel as ssi

    tech  = dict(_GRADE_CROSS_TECH)
    ident = {"sector": None, "sub_industry": None, "themes": [], "mc_bucket": None}
    favor = dict(_GRADE_CROSS_FAVOR)
    setup = ssi._compute_setup(_grade_cross_sit(bad), tech, ident, favor)

    assert setup["score"] == 63.9, f"Expected 63.9 (0.9 x 71), got {setup['score']}"
    assert setup["grade"] == "B",  f"Expected grade B, got {setup['grade']}"


def test_engine_compute_setup_finite_mc_keeps_full_score_and_grade():
    from engine import special_sits_intel as ssi

    ident = {"sector": None, "sub_industry": None, "themes": [], "mc_bucket": "large"}
    setup = ssi._compute_setup(_grade_cross_sit(250000), dict(_GRADE_CROSS_TECH),
                               ident, dict(_GRADE_CROSS_FAVOR))

    assert setup["score"] == 71.0, f"Expected 71.0, got {setup['score']}"
    assert setup["grade"] == "A",  f"Expected grade A, got {setup['grade']}"


def test_engine_compute_setup_nonfinite_mc_matches_none_baseline():
    """Flip ONLY mc_musd None -> nonfinite: every returned token must be unchanged.

    Pins the retained 2026-10-13 record values (score 63.9 / grade B) through
    the None-missing baseline without assuming any raw transport object.
    """
    from engine import special_sits_intel as ssi

    ident = {"sector": None, "sub_industry": None, "themes": [], "mc_bucket": None}
    base  = ssi._compute_setup(_grade_cross_sit(None), dict(_GRADE_CROSS_TECH),
                               dict(ident), dict(_GRADE_CROSS_FAVOR))
    assert base["score"] == 63.9 and base["grade"] == "B"

    for bad in (float("nan"), float("inf"), float("-inf"), "nan", "-inf"):
        got = ssi._compute_setup(_grade_cross_sit(bad), dict(_GRADE_CROSS_TECH),
                                 dict(ident), dict(_GRADE_CROSS_FAVOR))
        assert got == base, f"mc_musd={bad!r} diverged from None baseline: {got} vs {base}"


def test_engine_compute_setup_simple_event_nonfinite_mc_takes_missing_cap():
    """Simple untickered event: 15 raw -> 13.5 under the missing cap; why intact."""
    from engine import special_sits_intel as ssi

    favor = {"sector_stance": None, "rotation": None, "theme_ready": None,
             "theme_score": None, "standout": None}
    for bad in (None, float("nan"), float("inf"), float("-inf"), "nan"):
        s = {"ticker": None, "company": "Beretta Holding", "category": "Tender Offers",
             "stage": "announced", "mc_musd": bad, "confidence": None,
             "source_lane": "newswire", "live": False, "terminal": None}
        setup = ssi._compute_setup(s, dict(_SIMPLE_TECH),
                                   {"sector": None, "sub_industry": None,
                                    "themes": [], "mc_bucket": None}, dict(favor))

        assert setup["score"] == 13.5, f"mc={bad!r}: expected 13.5, got {setup['score']}"
        assert setup["grade"] is None
        assert setup["why"] == ["Setup approaching entry level"]
        assert setup["why_zh"] == ["设置趋近入场条件"]


def test_engine_compute_setup_simple_event_finite_mc_keeps_full_score():
    from engine import special_sits_intel as ssi

    favor = {"sector_stance": None, "rotation": None, "theme_ready": None,
             "theme_score": None, "standout": None}
    s = {"ticker": None, "company": "Beretta Holding", "category": "Tender Offers",
         "stage": "announced", "mc_musd": 1200, "confidence": None,
         "source_lane": "newswire", "live": False, "terminal": None}
    setup = ssi._compute_setup(s, dict(_SIMPLE_TECH),
                               {"sector": None, "sub_industry": None,
                                "themes": [], "mc_bucket": "micro"}, dict(favor))

    assert setup["score"] == 15.0, f"Expected 15.0, got {setup['score']}"
    assert setup["grade"] is None


def test_engine_compute_setup_existing_caps_untouched_by_mc_fix():
    """Low-confidence 0.75, terminal cap 25, and de-escalation cap 49 all still hold."""
    from engine import special_sits_intel as ssi

    tech  = {"tier": "T2", "tier_eligible": True, "tier_provisional": False,
             "washout_2w": False, "washout_1m": True,
             "w1_macd": None, "w1_stoch": None}
    ident = {"sector": None, "sub_industry": None, "themes": [], "mc_bucket": None}
    favor = {"sector_stance": None, "rotation": None, "theme_ready": None,
             "theme_score": None, "standout": None}

    low = ssi._compute_setup({"ticker": "L", "mc_musd": 5000, "confidence": "low",
                              "source_lane": "newswire", "live": False, "terminal": None},
                             dict(tech), dict(ident), dict(favor))
    assert low["score"] == 31.5, f"low-confidence cap changed: {low['score']}"

    term = ssi._compute_setup({"ticker": "T", "mc_musd": float("nan"), "confidence": "high",
                               "source_lane": "edgar", "live": True, "terminal": "closed"},
                              dict(tech), dict(ident), dict(favor))
    assert term["score"] == 25.0 and term["grade"] is None

    deesc = ssi._compute_setup(dict(_grade_cross_sit(250000), v1_direction=-1),
                               dict(_GRADE_CROSS_TECH), dict(ident), dict(_GRADE_CROSS_FAVOR))
    assert deesc["score"] == 49.0 and deesc["grade"] == "C"


# --- engine enrich() end-to-end on the isolated tmp_path ----------------------

@pytest.mark.parametrize("bad", [float("nan"), float("inf"), "-inf"])
def test_enrich_nonfinite_mc_matches_none_baseline_end_to_end(tmp_path, bad):
    """Real enrich() on an isolated store: nonfinite mc must equal the None run."""
    from engine import special_sits_intel as ssi

    def _run(mc_musd):
        sits = [_grade_cross_sit(mc_musd)]
        sits[0]["ticker"] = None          # keep it off the (empty) synthetic panel
        ssi.enrich(sits, root=tmp_path)
        return sits[0]

    base = _run(None)
    got  = _run(bad)

    assert base["ident"]["mc_bucket"] is None
    assert got["ident"]["mc_bucket"]  is None, (
        f"nonfinite mc bucketed as {got['ident']['mc_bucket']!r}, must be missing")
    assert got["setup"] == base["setup"], (
        f"setup diverged from None baseline: {got['setup']} vs {base['setup']}")


# --- builder _usd_m / fallback _mc_bucket --------------------------------------

@pytest.mark.parametrize("bad", _NONFINITE_MC_PARAMS)
def test_builder_usd_m_nonfinite_renders_emdash(bad):
    """Nonfinite mc must render the em dash, never '$inf B' / '$-inf M'."""
    from scripts.build_special_situations import _usd_m

    assert _usd_m(bad) == "—"


@pytest.mark.parametrize("missing", _MISSING_MC_PARAMS)
def test_builder_usd_m_missing_stays_emdash(missing):
    from scripts.build_special_situations import _usd_m

    assert _usd_m(missing) == "—"


@pytest.mark.parametrize(
    "mc,expected",
    [
        pytest.param(0, "$0M", id="zero"),
        pytest.param(-500, "$-500M", id="neg-finite"),
        pytest.param(999, "$999M", id="just-under-1b"),
        pytest.param(1000, "$1.0B", id="at-1b"),
        pytest.param(1234.5, "$1.2B", id="above-1b"),
        pytest.param(250000, "$250.0B", id="large-cap"),
        pytest.param("0", "$0M", id="zero-str"),
        pytest.param("-500", "$-500M", id="neg-finite-str"),
        pytest.param("1e-999", "$0M", id="underflow-to-zero-str"),
    ],
)
def test_builder_usd_m_zero_and_finite_values_preserved(mc, expected):
    from scripts.build_special_situations import _usd_m

    assert _usd_m(mc) == expected


@pytest.mark.parametrize("bad", _NONFINITE_MC_PARAMS)
def test_builder_mc_bucket_nonfinite_is_unknown(bad):
    """Nonfinite mc must fall back to the 'unknown' bucket."""
    from scripts.build_special_situations import _mc_bucket

    assert _mc_bucket(bad) == "unknown"


@pytest.mark.parametrize("missing", _MISSING_MC_PARAMS)
def test_builder_mc_bucket_missing_stays_unknown(missing):
    from scripts.build_special_situations import _mc_bucket

    assert _mc_bucket(missing) == "unknown"


@pytest.mark.parametrize(
    "mc,expected",
    [
        pytest.param(0, "micro", id="zero"),
        pytest.param(-500, "micro", id="neg-finite"),
        pytest.param(49.9, "micro", id="just-under-50"),
        pytest.param(50, "micro", id="at-50"),
        pytest.param(299.9, "micro", id="just-under-300"),
        pytest.param(300, "small", id="at-300"),
        pytest.param(1999.9, "small", id="just-under-2000"),
        pytest.param(2000, "mid", id="at-2000"),
        pytest.param(9999.9, "mid", id="just-under-10000"),
        pytest.param(10000, "large", id="at-10000"),
        pytest.param("0", "micro", id="zero-str"),
        pytest.param("-500", "micro", id="neg-finite-str"),
    ],
)
def test_builder_mc_bucket_zero_and_finite_boundaries_preserved(mc, expected):
    from scripts.build_special_situations import _mc_bucket

    assert _mc_bucket(mc) == expected
