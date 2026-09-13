"""Tests for engine/valuation_scenario.py (FROZEN SPEC B-F07-1)."""
from __future__ import annotations

import re
from pathlib import Path

from engine import valuation_scenario as vs

ROOT = Path(__file__).resolve().parent.parent

FIXTURE_ROW = {
    "fy": 2025,
    "period_end": "2025-09-27",
    "revenue": 4.16e11,
    "op_income": 1.28e11,
    "ni": 1.05e11,  # loader column name (collectors/edgar_facts.py FLOW["ni"]) -- not "net_income"
    "cash": 3.2e10 + 1.0e10,  # arbitrary; net_debt derived below
    "debt_lt": 8.0e10,
    "debt_cur": 1.0e10,
    "shares": 1.49e10,
}


def _rows(**overrides):
    row = dict(FIXTURE_ROW)
    row.update(overrides)
    return [row]


def test_math_matches_frozen_formula():
    blob = vs.compute(_rows(), price=319.97, asof="2026-09-05", ticker="AAPL")
    assert blob is not None
    by_key = {s["key"]: s for s in blob["scenarios"]}
    net_income = FIXTURE_ROW["ni"]
    revenue = FIXTURE_ROW["revenue"]
    shares = FIXTURE_ROW["shares"]
    net_margin_base = net_income / revenue
    for key, g, m_pp, mult in vs.SCENARIOS:
        adj = net_income * (1 + g / 100.0) * (1 + (m_pp / 100.0) / net_margin_base)
        expected = round((adj * mult) / shares, 2)
        got = by_key[key]
        assert got["computable"] is True
        assert got["per_share"] == expected, (key, got["per_share"], expected)


def test_null_propagation():
    blob = vs.compute(_rows(ni=None))
    for s in blob["scenarios"]:
        assert s["computable"] is False
        assert s["per_share"] is None
        assert s["missing"] == ["net_income"]
    assert blob["base"]["net_income"]["value"] is None
    assert blob["base"]["net_income"]["reported"] is False

    # BLOCKER B2 (review B-F07-1): net_debt is reported ONLY as an
    # informational base fact -- the frozen per_share formula never consumes
    # it (an earnings multiple already yields equity value), so a missing
    # net_debt leg must NEVER gate scenario computability. The base row still
    # correctly prints a null for net_debt itself.
    blob2 = vs.compute(_rows(cash=None))
    assert blob2["base"]["net_debt"]["value"] is None
    assert blob2["base"]["net_debt"]["reported"] is False
    for s in blob2["scenarios"]:
        assert s["computable"] is True
        assert "net_debt" not in s["missing"]
        assert s["per_share"] is not None

    # No zero substitution anywhere for the dropped inputs.
    assert blob["base"]["net_income"]["value"] != 0
    assert blob2["base"]["net_debt"]["value"] != 0


def test_share_count_identity_is_declared():
    blob = vs.compute(_rows())
    assert blob["base"]["share_count"]["identity"] == "outstanding"
    assert blob["base"]["share_count"]["identity"] != "diluted"


def test_period_and_unit_consistency():
    blob = vs.compute(_rows(revenue_fy=2024))
    for s in blob["scenarios"]:
        assert s["computable"] is False
        assert s["missing"] == ["consistent period"]
    assert blob["base"]["revenue"]["unit"] == "USD"
    assert blob["base"]["share_count"]["unit"] == "shares"


def test_negative_or_zero_earnings_is_not_a_value():
    blob = vs.compute(_rows(ni=0))
    for s in blob["scenarios"]:
        assert s["computable"] is False
        assert s["per_share"] is None
        assert "positive reported earnings" in s["missing"]

    blob2 = vs.compute(_rows(ni=-5.0))
    for s in blob2["scenarios"]:
        assert s["computable"] is False
        assert s["per_share"] is None


def test_tiny_margin_base_is_not_computable():
    """MINOR-2 (review round 2): net_margin_base = net_income / revenue with no
    floor lets a thin-margin issuer's margin_delta_pp swamp the base margin --
    e.g. margin ~=0.1% makes the Cautious factor 1 + (-1.5/0.1) = -14, printing
    a negative dollar per-share as a computed value. A margin base this small
    is not a usable denominator, so it must gate computability (same as a
    missing net_margin_base) rather than silently produce a nonsense number."""
    revenue = 1.0e11
    tiny_ni = revenue * 0.001  # 0.1% margin -- reported, but unusable as a base
    blob = vs.compute(_rows(ni=tiny_ni, revenue=revenue))
    for s in blob["scenarios"]:
        assert s["computable"] is False
        assert s["per_share"] is None
        assert "net_margin_base" in s["missing"]
    assert blob["base"]["net_income"]["value"] == tiny_ni
    assert blob["base"]["net_income"]["reported"] is True

    # A normal margin (AAPL-scale, ~24%) stays fully computable -- the floor
    # must not touch any realistic issuer.
    normal = vs.compute(_rows())
    for s in normal["scenarios"]:
        assert s["computable"] is True
        assert s["per_share"] is not None
        assert s["per_share"] > 0


def test_margin_1_2_percent_gates_cautious_only():
    """MAJOR-1 (review round 3): round 2's MINOR-2 fix floored net_margin_base
    at 1%, but that floor alone left every margin in [1.0%, 1.5%) still
    producing a NEGATIVE per_share for Cautious -- e.g. at margin=1.2%
    (0.012), Cautious's factor is 1 + (-1.5/100)/0.012 = 1 + (-0.015/0.012),
    which is still negative, so `computable=True` with `per_share=-4.12` on
    the pre-fix module (confirmed by running it directly). The real gate is
    PER SCENARIO: computable only when net_margin_base + margin_delta_pp/100
    is strictly positive for THAT scenario. At margin=1.2%:
      cautious (m_pp=-1.5): 0.012 + (-0.015) = -0.003 <= 0 -> NOT computable
      base     (m_pp=0.0):  0.012 + 0.0      =  0.012 >  0 -> computable
      upbeat   (m_pp=+1.5): 0.012 + 0.015    =  0.027 >  0 -> computable
    Other scenarios must still render even though Cautious is gated -- this
    is a per-scenario gate, not a global one."""
    revenue = 1.0e11
    ni_1_2_pct = revenue * 0.012
    blob = vs.compute(_rows(ni=ni_1_2_pct, revenue=revenue), ticker="TEST")
    by_key = {s["key"]: s for s in blob["scenarios"]}

    cautious = by_key["cautious"]
    assert cautious["computable"] is False
    assert cautious["per_share"] is None
    assert "margin_too_thin" in cautious["missing"]
    # And NOT gated by the (different, global) net_margin_base-missing
    # reason -- the margin base itself is available at this magnitude, it is
    # only too thin for Cautious's own delta.
    assert "net_margin_base" not in cautious["missing"]

    for key in ("base", "upbeat"):
        s = by_key[key]
        assert s["computable"] is True, (key, s)
        assert s["per_share"] is not None
        assert s["per_share"] > 0
        assert "margin_too_thin" not in s["missing"]

    # Belt-and-braces: the rendered HTML contains no bare "$-" (a negative
    # dollar figure) anywhere -- the non-computable Cautious card must never
    # leak a computed negative value.
    import jinja2

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT / "templates")))
    env.globals["t"] = lambda en, zh: en
    tmpl = env.from_string("{% include '_valuation_scenario.html.j2' %}")
    html = tmpl.render(valuation_scenario=blob, deep_ids=[])
    assert "$-" not in html
    assert "Margins are too thin to run the cautious case" in html


def test_fixture_keys_are_real_statement_columns():
    """Review B-F07-1 BLOCKER B1: engine/valuation_scenario.py previously read
    latest.get("net_income"), a key that does not exist anywhere in the real
    engine.stock_fundamentals._load_statements() schema -- every AAPL row
    silently produced net_income=None against live data, and no test caught
    it because the fixture used the same wrong key the module read. Ground
    the fixture in the loader's own declared column set (collectors/
    edgar_facts.py FLOW/BALANCE/BALANCE_SHARES -- the concept tables
    _load_statements()'s parquet is built from) so a fixture key that doesn't
    exist in the real schema fails here instead of passing silently."""
    from collectors.edgar_facts import BALANCE, BALANCE_SHARES, FLOW

    declared = set(FLOW) | set(BALANCE) | set(BALANCE_SHARES) | {"fy", "period_end"}
    fixture_keys = set(FIXTURE_ROW)
    assert fixture_keys <= declared, fixture_keys - declared
    # And the specific field this bug hinged on: real net income lives at "ni",
    # never "net_income" (which is only ever an OUTPUT/display key in this module).
    assert "ni" in fixture_keys
    assert "net_income" not in fixture_keys


def test_module_is_pure():
    src = (ROOT / "engine" / "valuation_scenario.py").read_text()
    for banned in ("open(", "requests", "read_parquet", "datetime.now", "Path("):
        assert banned not in src, banned


BANNED_VOCAB = [
    "probability", "confidence", "likely", "odds", "expected value",
    "fair value", "price target", "consensus", "analyst", "estimate",
    "forecast", "validated",
    "概率", "置信", "目标价", "共识", "预测",
]


def test_no_banned_vocabulary():
    partial = ROOT / "templates" / "_valuation_scenario.html.j2"
    text = partial.read_text().lower()
    for word in BANNED_VOCAB:
        assert word.lower() not in text, f"banned word {word!r} found in partial"


def test_bilingual_parity():
    partial = ROOT / "templates" / "_valuation_scenario.html.j2"
    text = partial.read_text()
    # Heal h1: widen the regex to also match double-quoted t("en", 'zh') /
    # t("en", "zh") pairs (heal h1 uses double quotes around vs_period_en),
    # not only the original single-quoted form.
    for pattern in (
        r"""t\(\s*'([^']*)'\s*,\s*'([^']*)'\s*\)""",
        r'''t\(\s*"([^"]*)"\s*,\s*'([^']*)'\s*\)''',
        r'''t\(\s*"([^"]*)"\s*,\s*"([^"]*)"\s*\)''',
    ):
        for m in re.finditer(pattern, text):
            en, zh = m.group(1), m.group(2)
            assert zh.strip() != "", f"empty ZH for en={en!r}"
    for m in re.finditer(r'title="[^"]*[一-鿿][^"]*"', text):
        raise AssertionError(f"ZH text found in a title= attribute: {m.group(0)!r}")
    # Heal h1: the five base-row <small> tags used to print b.<field>.period
    # (engine output "FY2025") raw, which is untranslated in the ZH render
    # while the panel's own hint already translated "FY" via t(). Render the
    # partial under a ZH-only t() and assert no bare "FY<digits>" token
    # surfaces in any of the five rows -- the EN shape must come through
    # t() so a locale switch actually translates it.
    import jinja2

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT / "templates")))
    env.globals["t"] = lambda en, zh: zh
    tmpl = env.from_string("{% include '_valuation_scenario.html.j2' %}")
    blob = vs.compute(_rows(), price=319.97, asof="2026-09-05", ticker="AAPL")
    html = tmpl.render(valuation_scenario=blob, deep_ids=[])
    assert not re.search(r"FY\d{4}", html), (
        "bare FY<digits> token leaked into the ZH render -- the panel must "
        "route the period through t() like its own hint at :120 does"
    )


def test_h2_ruler_and_gap_marks_have_bilingual_aria_labels():
    """Heal h2: the ruler's role=img aria-label and every m-gap mark's
    aria-label must carry BOTH an ASCII run and a CJK run -- a screen
    reader user on the ZH locale was previously hearing only English
    (the role=img label IS the whole text equivalent). Static "EN · ZH"
    strings, never t() inside an attribute (the t() macro's <span> markup
    would break attribute quoting and leak the rest of the string as
    visible page text -- the original comment on :126-:131)."""
    import jinja2

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT / "templates")))
    env.globals["t"] = lambda en, zh: en
    tmpl = env.from_string("{% include '_valuation_scenario.html.j2' %}")

    # All-computable fixture: ruler has only one role=img aria-label.
    blob = vs.compute(_rows(), price=319.97, asof="2026-09-05", ticker="AAPL")
    html = tmpl.render(valuation_scenario=blob, deep_ids=[])

    ruler = re.search(r'<div class="vs-ruler"[^>]*aria-label="([^"]+)"', html)
    assert ruler, "ruler role=img not found"
    ruler_lbl = ruler.group(1)
    assert re.search(r"[A-Za-z]", ruler_lbl), f"ruler aria-label has no ASCII run: {ruler_lbl!r}"
    assert re.search(r"[一-鿿]", ruler_lbl), f"ruler aria-label has no CJK run: {ruler_lbl!r}"

    # Margin-1.2% fixture: only base and upbeat are computable, so cautious
    # renders as an m-gap mark with its own aria-label.
    revenue = 1.0e11
    ni_1_2_pct = revenue * 0.012
    blob2 = vs.compute(_rows(ni=ni_1_2_pct, revenue=revenue), ticker="TEST")
    html2 = tmpl.render(valuation_scenario=blob2, deep_ids=[])

    gap_aria_labels = re.findall(
        r'<div class="vs-mark m-gap"[^>]*aria-label="([^"]+)"', html2,
    )
    assert gap_aria_labels, "no m-gap aria-labels found in the 1.2%-margin render"
    for lbl in gap_aria_labels:
        assert re.search(r"[A-Za-z]", lbl), f"m-gap aria-label has no ASCII run: {lbl!r}"
        assert re.search(r"[一-鿿]", lbl), f"m-gap aria-label has no CJK run: {lbl!r}"


def test_h3_ruler_label_for_margin_too_thin_is_honest():
    """Heal h3: a scenario gated only by margin_too_thin gets a short truthful
    visible label on the ruler -- EN 'Too thin to run', ZH '利润率过低' --
    rather than the generic 'No data' / '无数据' that fits an UNREPORTED input
    but not a reported-but-too-thin margin. The vs_null_* priority rule still
    governs: the FIRST element of s.missing wins, so a scenario gated only
    by margin_too_thin gets the thin wording, while one gated by a more
    fundamental reason (e.g. 'consistent period') keeps the missing-input
    phrasing -- already covered by test_null_reason_prioritizes_consistent_period_over_margin_too_thin."""
    import jinja2

    revenue = 1.0e11
    ni_1_2_pct = revenue * 0.012
    blob = vs.compute(_rows(ni=ni_1_2_pct, revenue=revenue), ticker="TEST")

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT / "templates")))
    env.globals["t"] = lambda en, zh: f"{en}|{zh}"
    tmpl = env.from_string("{% include '_valuation_scenario.html.j2' %}")
    html = tmpl.render(valuation_scenario=blob, deep_ids=[])

    # Locate the cautious m-gap label (the only gated scenario at 1.2%).
    # The visible label is in a <div class="vs-lbl ...">...<b>...</b></div>
    # sitting on the cautious gap position. The "Cautious" word is emitted
    # by t('Cautious','保守') which the test t() joins as 'Cautious|保守'.
    # Note: the class attr may end with a single trailing space (the
    # loop.index0 conditional collapses to "vs-lbl " with no extra class),
    # so use [^"]* (zero or more) not [^"]+ for the class-value capture.
    cautious_block = re.search(
        r'class="vs-lbl [^"]*"[^>]*>(?:Cautious\|保守).*?</div>',
        html, flags=re.DOTALL,
    )
    assert cautious_block, "could not locate the cautious gap-mark <b> block"
    cautious_lbl = cautious_block.group(0)
    assert "Too thin to run|利润率过低" in cautious_lbl, (
        f"cautious ruler label did not switch to the thin wording: {cautious_lbl!r}"
    )
    # And it must NOT have been left as the generic 'No data' phrasing --
    # the gated-but-reported-input distinction is the whole point of h3.
    assert "No data|无数据" not in cautious_lbl, (
        f"cautious ruler label still says 'No data' for a reported-but-thin margin: {cautious_lbl!r}"
    )


def test_h4_plain_word_read_renders_for_computable_and_omits_for_null():
    """Heal h4: one plain-word sentence below the ruler, above .vs-cards,
    stating where today's price sits relative to the computable scenarios.
    Renders for the computable fixture (both EN and ZH halves non-empty
    when t() emits both), and is ABSENT entirely for vs.compute(_rows(),
    price=None) and for the all-null blob.

    MINOR-5 (review round 2): the EN/ZH pairs are routed through t() with
    variables (vs_read_en_text, vs_read_zh_text), so the widened literal-pair
    regex at test_bilingual_parity cannot match them -- this used to leave
    the parity gate one layer narrower than the law. Parametrize over price
    below / between / above × 1 / 2 / 3 computable to put every emitted
    pair on the same audit hook as the literal-pair regex."""
    import jinja2

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT / "templates")))
    env.globals["t"] = lambda en, zh: f"{en}|{zh}"
    tmpl = env.from_string("{% include '_valuation_scenario.html.j2' %}")

    def _render(blob):
        return tmpl.render(valuation_scenario=blob, deep_ids=[])

    def _lede(html):
        lede_blocks = re.findall(
            r'<p class="vs-lede" data-vs-read="1"[^>]*>(.*?)</p>',
            html, flags=re.DOTALL,
        )
        if not lede_blocks:
            return None
        return lede_blocks[0]

    def _en_zh(text):
        # t() joined halves with '|' -- strip any t()-emitted <span>s first
        # so the assertion sees only the visible text and works even if the
        # t() macro later evolves to wrap each half in <span class="l-en">/
        # <span class="l-zh"> (the variant used by the partial's own hint).
        clean = re.sub(r"<[^>]+>", "", text or "")
        en_part, _, zh_part = clean.partition("|")
        return en_part.strip(), zh_part.strip()

    def _with_per_share(blob, *, cautious=None, base=None, upbeat=None):
        """Mutate per_share on a copy of the engine's blob so the panel's
        Jinja branch logic can be exercised independently of the engine's
        own math. computable stays True only where per_share is set."""
        import copy
        out = copy.deepcopy(blob)
        for s in out["scenarios"]:
            k = s["key"]
            override = {"cautious": cautious, "base": base, "upbeat": upbeat}.get(k)
            if override is None:
                s["per_share"] = None
                s["computable"] = False
                s.setdefault("missing", [])
                s["missing"].append("test_override")
                s.setdefault("missing_plain", [])
                s["missing_plain"].append({"en": "a reported input", "zh": "一项披露数据"})
            else:
                s["per_share"] = override
                s["computable"] = True
        any_comp = any(s["computable"] for s in out["scenarios"])
        out["any_computable"] = any_comp
        return out

    # 1. Three-computable fixture with price between Base and Upbeat --
    #    AAPL defaults give per_share ~ 90.94 / 130.65 / 175.74, so price
    #    319.97 sits above all three. Override per_share to a tighter
    #    band so the test is deterministic and decoupled from the engine's
    #    frozen-formula math.
    blob = vs.compute(_rows(), price=319.97, asof="2026-09-05", ticker="AAPL")
    assert blob["any_computable"] is True

    three_bands = [
        # (price, per_share overrides, expected en phrase, expected zh phrase)
        (50.0,   (90.94, 130.65, 175.74), "below all three cases",    "低于全部三档情景"),
        (150.0,  (90.94, 130.65, 175.74), "sits between Base and Upbeat", "位于基准与乐观之间"),
        (130.65, (90.94, 130.65, 175.74), "sits at Base",             "位于基准情景"),
        (110.0,  (90.94, 130.65, 175.74), "sits between Cautious and Base", "位于保守与基准之间"),
        (500.0,  (90.94, 130.65, 175.74), "above all three cases",    "高于全部三档情景"),
    ]
    for price, (c, b, u), en_phrase, zh_phrase in three_bands:
        mut = _with_per_share(blob, cautious=c, base=b, upbeat=u)
        mut["price"] = {"value": price}
        html = _render(mut)
        lede = _lede(html)
        assert lede is not None, (
            f"h4 lede missing for 3-computable price={price} (expected {en_phrase!r})"
        )
        en, zh = _en_zh(lede)
        assert en != "" and zh != "", (
            f"empty half in h4 lede for price={price}: en={en!r} zh={zh!r} lede={lede!r}"
        )
        assert en_phrase in en, (
            f"3-computable h4 phrase mismatch for price={price}: "
            f"got en={en!r}, expected ~{en_phrase!r}"
        )
        assert zh_phrase in zh, (
            f"3-computable h4 phrase mismatch for price={price}: "
            f"got zh={zh!r}, expected ~{zh_phrase!r}"
        )

    # 2. Two-computable fixture (margin=1.2% gates Cautious only). Override
    #    Base and Upbeat per_share to deterministic values so the branches
    #    below/middle/above are exercisable.
    revenue = 1.0e11
    ni_1_2_pct = revenue * 0.012
    blob_2 = vs.compute(_rows(ni=ni_1_2_pct, revenue=revenue), ticker="TEST")
    by_key_2 = {s["key"]: s for s in blob_2["scenarios"]}
    assert by_key_2["cautious"]["computable"] is False
    for k in ("base", "upbeat"):
        assert by_key_2[k]["computable"] is True, (k, by_key_2[k])

    two_bands = [
        (50.0,  (130.65, 175.74), "below both computable cases", "低于两档可计算的情景"),
        (150.0, (130.65, 175.74), "sits between Base and Upbeat", "位于基准与乐观之间"),
        (500.0, (130.65, 175.74), "above both computable cases", "高于两档可计算的情景"),
    ]
    for price, (b, u), en_phrase, zh_phrase in two_bands:
        mut = _with_per_share(blob_2, base=b, upbeat=u)
        mut["price"] = {"value": price}
        html = _render(mut)
        lede = _lede(html)
        assert lede is not None, (
            f"h4 lede missing for 2-computable price={price} (expected {en_phrase!r})"
        )
        en, zh = _en_zh(lede)
        assert en != "" and zh != "", (
            f"empty half in h4 lede for 2-computable price={price}: en={en!r} zh={zh!r}"
        )
        assert en_phrase in en, (
            f"2-computable h4 phrase mismatch for price={price}: got en={en!r}"
        )
        assert zh_phrase in zh, (
            f"2-computable h4 phrase mismatch for price={price}: got zh={zh!r}"
        )

    # 3. Two-computable pair: cautious + upbeat (base gated by another
    #    reason). Force the blob so only cautious + upbeat are computable.
    blob_cb = vs.compute(_rows(), price=200.0, asof="2026-09-05", ticker="AAPL")
    blob_cb_mut = _with_per_share(blob_cb, cautious=90.94, upbeat=175.74)
    blob_cb_mut["price"] = {"value": 130.0}  # between cautious and upbeat
    html_cb = _render(blob_cb_mut)
    lede_cb = _lede(html_cb)
    assert lede_cb is not None, "h4 lede missing for cautious+upbeat 2-computable"
    en_cb, zh_cb = _en_zh(lede_cb)
    assert "sits between Cautious and Upbeat" in en_cb, en_cb
    assert "位于保守与乐观之间" in zh_cb, zh_cb

    # 4. One-computable fixture: only base is computable.
    blob_1 = vs.compute(_rows(), price=100.0, asof="2026-09-05", ticker="AAPL")
    blob_1_mut = _with_per_share(blob_1, base=130.65)
    blob_1_mut["price"] = {"value": 90.0}
    html_1 = _render(blob_1_mut)
    lede_1 = _lede(html_1)
    assert lede_1 is not None, "h4 lede missing for 1-computable"
    en_1, zh_1 = _en_zh(lede_1)
    assert "below the computable case" in en_1, en_1
    assert "低于唯一可计算的情景" in zh_1, zh_1

    blob_1_mut["price"] = {"value": 200.0}
    html_1b = _render(blob_1_mut)
    lede_1b = _lede(html_1b)
    assert lede_1b is not None, "h4 lede missing for 1-computable above"
    en_1b, zh_1b = _en_zh(lede_1b)
    assert "above the computable case" in en_1b, en_1b
    assert "高于唯一可计算的情景" in zh_1b, zh_1b

    # 5. Computable fixture with price=None -- the lede must be omitted
    #    entirely (no <p class="vs-lede" data-vs-read="1"> in the render).
    blob2 = vs.compute(_rows(), price=None, asof="2026-09-05", ticker="AAPL")
    assert blob2["any_computable"] is True
    html2 = _render(blob2)
    assert 'data-vs-read="1"' not in html2, (
        "h4 lede rendered despite price=None -- it must omit entirely"
    )

    # 6. All-null blob -- any_computable is False; lede must omit.
    blob3 = vs.compute(_rows(ni=None), ticker="AAPL")
    assert blob3["any_computable"] is False
    html3 = _render(blob3)
    assert 'data-vs-read="1"' not in html3, (
        "h4 lede rendered despite any_computable=False -- it must omit entirely"
    )


def test_panel_renders_and_omits():
    import jinja2

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT / "templates")))
    env.globals["t"] = lambda en, zh: en

    tmpl_src = (
        "{% include '_valuation_scenario.html.j2' %}"
    )
    tmpl = env.from_string(tmpl_src)

    computable_blob = vs.compute(_rows(), price=319.97, asof="2026-09-05", ticker="AAPL")
    html = tmpl.render(valuation_scenario=computable_blob, deep_ids=[])
    assert 'id="valuation-scenario"' in html
    assert 'data-valuation-scenario="v1"' in html

    null_blob = vs.compute(_rows(ni=None), ticker="AAPL")
    assert null_blob["any_computable"] is False
    html2 = tmpl.render(valuation_scenario=null_blob, deep_ids=[])
    assert 'id="valuation-scenario"' in html2
    assert "Can't be computed without reported net income" in html2
    assert "not reported" in html2
    # No raw internal field slug leaked into the null copy.
    for raw_slug in ("net_income", "net_debt", "net_margin_base", "share_count"):
        assert raw_slug not in html2

    # A blob with nothing computed AND no base data at all still must not
    # render an empty/broken section -- compute() only returns None when
    # there is no dated row at all, which the template also guards.
    assert vs.compute([]) is None


def test_null_reason_prioritizes_consistent_period_over_margin_too_thin():
    """Review round 4 MINOR-4: vs_null_en/vs_null_zh in
    templates/_valuation_scenario.html.j2 used to test
    `'margin_too_thin' in s.missing` (membership), so a scenario carrying
    BOTH a more fundamental reason ("consistent period") and margin_too_thin
    always got the scenario-named margin sentence, silently suppressing the
    mixed-period reason. engine/valuation_scenario.py always appends
    "consistent period" FIRST and "margin_too_thin" LAST to a scenario's
    `missing` list (guard order), so testing s.missing[0] instead of
    membership restores the correct priority: the more fundamental reason
    wins whenever more than one applies."""
    import jinja2

    # margin=1.2% drives Cautious's own factor negative (margin_too_thin),
    # same fixture as test_margin_1_2_percent_gates_cautious_only -- but this
    # fixture ALSO breaks period consistency (a debt_lt row tagged to a
    # different fiscal year), which the engine appends first and unconditionally.
    revenue = 1.0e11
    ni_1_2_pct = revenue * 0.012
    blob = vs.compute(
        _rows(ni=ni_1_2_pct, revenue=revenue, debt_lt_fy=2024), ticker="TEST"
    )
    by_key = {s["key"]: s for s in blob["scenarios"]}
    cautious = by_key["cautious"]
    assert cautious["missing"][0] == "consistent period", cautious["missing"]
    assert "margin_too_thin" in cautious["missing"]  # still recorded, just not first

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT / "templates")))
    env.globals["t"] = lambda en, zh: en
    tmpl = env.from_string("{% include '_valuation_scenario.html.j2' %}")
    html = tmpl.render(valuation_scenario=blob, deep_ids=[])
    assert "Can't be computed without a consistent reporting period" in html
    assert "Margins are too thin to run the cautious case" not in html


def test_full_detail_dialog_requires_positive_per_share_not_just_computable():
    """Review round 4 MINOR-1: scripts/build_ticker_pages.py's Full-detail
    dialog (`_deep_valuation_scenario`) is a fourth render site for
    `per_share` and used to gate on `s.get("computable")` alone -- the PR's
    belt-and-braces claim (every render site requires computable AND
    per_share is not none AND per_share > 0) was true of the Jinja partial
    but one file short of true. Hand-craft a scenario dict the real engine
    could never emit (computable=True, per_share<=0) to prove the dialog
    itself refuses to print a dollar figure for it -- this is exactly the
    defence a real engine regression would need. Also asserts a
    margin_too_thin null now carries a plain-word reason instead of a bare
    "Not computable" with no explanation."""
    from scripts.build_ticker_pages import _deep_valuation_scenario

    blob = {
        "valuation_scenario": {
            "v1": {
                "fy": 2025,
                "period_end": "2025-09-27",
                "base": {
                    "revenue": {"value": 1e11}, "op_income": {"value": 1e10},
                    "net_income": {"value": 1e9},
                    "share_count": {"value": 1e9, "identity": "outstanding"},
                    "net_debt": {"value": None, "reported": False},
                },
                "scenarios": [
                    # Adversarial: engine can never emit this (belt-and-braces
                    # forecloses it), but the dialog must defend independently.
                    {"key": "cautious", "assumptions": {"sales_growth_pct": -2, "margin_delta_pp": -1.5, "earnings_multiple": 14},
                     "per_share": -4.12, "computable": True, "missing": [], "missing_plain": []},
                    {"key": "base", "assumptions": {"sales_growth_pct": 3, "margin_delta_pp": 0, "earnings_multiple": 18},
                     "per_share": None, "computable": False,
                     "missing": ["margin_too_thin"],
                     "missing_plain": [{"en": "a margin base wide enough for this case", "zh": "利润率基数不足以支撑该情景"}]},
                    {"key": "upbeat", "assumptions": {"sales_growth_pct": 7, "margin_delta_pp": 1.5, "earnings_multiple": 22},
                     "per_share": 55.0, "computable": True, "missing": [], "missing_plain": []},
                ],
            }
        }
    }
    dialog = _deep_valuation_scenario(blob)
    panels = dialog["panels"]
    by_title = {p["title_en"]: p for p in panels if p.get("kind") == "kv" and p.get("title_en") in ("Cautious", "Base", "Upbeat")}

    cautious_ps_row = next(r for r in by_title["Cautious"]["rows"] if r["k_en"] == "Per-share (computed)")
    assert cautious_ps_row["v"] == "", cautious_ps_row  # never a dollar figure for per_share<=0
    assert "$" not in cautious_ps_row["v_en"]

    base_ps_row = next(r for r in by_title["Base"]["rows"] if r["k_en"] == "Per-share (computed)")
    assert base_ps_row["v"] == ""
    assert base_ps_row["v_en"] != "Not computable"  # a reason, not a bare unexplained label
    assert "too thin" in base_ps_row["v_en"]
    assert base_ps_row["v_zh"] != "无法计算"
    assert "利润率过低" in base_ps_row["v_zh"]

    upbeat_ps_row = next(r for r in by_title["Upbeat"]["rows"] if r["k_en"] == "Per-share (computed)")
    assert upbeat_ps_row["v"] == "$55.00"


def test_research_display_only_line_present():
    import jinja2

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT / "templates")))
    env.globals["t"] = lambda en, zh: f"{en}|{zh}"
    tmpl = env.from_string("{% include '_valuation_scenario.html.j2' %}")
    blob = vs.compute(_rows(), price=319.97, asof="2026-09-05", ticker="AAPL")
    html = tmpl.render(valuation_scenario=blob, deep_ids=[])
    assert "Research display only" in html
    assert "仅供研究展示" in html


def test_sec_filings_zh_uses_disclosure_not_tax_declaration():
    """Heal h1: 'SEC filings' must pair with 披露, never 申报.

    申报 is a tax/customs self-declaration. An SEC 10-K this panel cites is a
    披露 (disclosure). The zh-filing-term job failed on six unlicensed 申报
    hits in this PR's own copy (5x the panel source line, 1x the Full-detail
    dialog). RED-first against the pre-heal strings: those files used
    'SEC申报文件' and this test fails on that phrasing.
    """
    import jinja2
    from scripts.build_ticker_pages import _deep_valuation_scenario

    banned = "申报"
    expected_zh = "SEC披露文件"

    partial = (ROOT / "templates" / "_valuation_scenario.html.j2").read_text(encoding="utf-8")
    assert banned not in partial
    assert f"t('Source: SEC filings','来源：{expected_zh}')" in partial

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT / "templates")))
    env.globals["t"] = lambda en, zh: f"{en}|{zh}"
    tmpl = env.from_string("{% include '_valuation_scenario.html.j2' %}")
    blob = vs.compute(_rows(), price=319.97, asof="2026-09-05", ticker="AAPL")
    html = tmpl.render(valuation_scenario=blob, deep_ids=[])
    assert banned not in html
    assert f"Source: SEC filings|来源：{expected_zh}" in html

    dialog = _deep_valuation_scenario({"valuation_scenario": {"v1": blob}})
    source_row = next(r for r in dialog["panels"][0]["rows"] if r["k_en"] == "Source")
    assert source_row["v_zh"] == expected_zh
    assert banned not in source_row["v_zh"]
