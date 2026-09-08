"""tests/test_measurement_research_implications.py — F10-X1 Research Implication
cards, human projection only.

Scope of THIS file (visual child `marketontology-f10-x1-visual-cards-20260904-001`):
the `templates/measurement.html.j2` Research Implications section. The adapter
(`engine/research_implication_card.py`) and its contract tests
(`tests/test_research_implication_card.py`) are owned elsewhere and are read-only
here — these tests consume the frozen envelope, they never re-derive it.

What is pinned:
1.  Absent/empty envelope renders no section at all (no empty shell, no zero).
2.  Both real frozen cards render with stable, card-unique semantic anchors.
3.  Glance shows a plain-word state; typed quality/tier/family/authority
    codes live in Receipts, never as header chips.
4.  The exact required stance line is present in EN and ZH.
5.  All five authority booleans are disclosed as withheld; no ranking language.
6.  A null is typed — never rendered as 0 — and carries its null reason.
7.  An ordered effect path renders ONLY when the owner marked it ordered.
8.  EN/ZH parity: every EN label has a ZH sibling carrying real Chinese.
9.  BC-2: no "validated"/"已验证" in this section's copy.
10. Card ids in the HTML equal the card ids in the machine contract.
11. Filters are non-ranking: DOM order equals contract order.

House rules obeyed: no network, no git, no ledger writes, no estimator run.
"""

from __future__ import annotations

import copy
import json
import re
import sys
from datetime import date
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

CONTRACT_PATH = REPO / "site" / "measurementdata" / "research_implication_cards.json"

# The exact stance the F10-X1 product freeze requires on this section.
STANCE_EN = "Research context — do not use as a trading signal"
STANCE_ZH = "研究背景 — 请勿作为交易信号使用"

AUTHORITY_KEYS = (
    "forecast_authority",
    "gating_authority",
    "ranking_authority",
    "sizing_authority",
    "trading_authority",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _render(**overrides) -> str:
    """Render measurement.html.j2 with an all-absent context.

    Mirrors the render kwargs in scripts.build_measurement.run(); each test
    overrides only `research_implications`. autoescape=False matches the
    builder exactly, so an escaping regression shows up here rather than in
    the browser.
    """
    from jinja2 import Environment, FileSystemLoader, meta

    templates_dir = REPO / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=False)
    try:
        from engine import i18n

        env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    except Exception:
        env.globals.update(td=lambda en: en, tr=lambda en: en, t=lambda en, zh="": en)

    context = {
        "page_title": "Test",
        "engines": [],
        "gate_ledger": [],
        "accruing_experiments": [],
        "cone_recalibration": {},
        "collinearity": {},
        "sync_gauge": {"available": False},
        "provenance": {"epochs": {}, "fingerprint_consistent": True},
        "build_date": date.today().isoformat(),
        "generated_at": "2026-07-06T00:00:00Z",
        "n_stamps_grand_total": 0,
        "truth_ledger": {"available": False},
        "accrual_clocks": [],
        "prediction_layer": {"available": False},
        "coverage_matrix": {"available": False, "rows": []},
        "grading_closure": {"available": False},
        "trial_budgets": {"available": False},
        "rule_experiments": {"available": False},
        "qledger_reliability": {"available": False},
        "research_implications": {
            "schema": "mastermind.research_implication_cards/v1",
            "cards": [],
        },
        "imce_prospective": {"available": False},
        "seasonality_record": {
            "available": False,
            "registered": 0,
            "graded": 0,
            "next_close": None,
        },
    }
    context.update(overrides)

    source = (templates_dir / "measurement.html.j2").read_text(encoding="utf-8")
    needed = meta.find_undeclared_variables(env.parse(source))
    internal_sets = set(re.findall(r"\{%-?\s*set\s+([A-Za-z_]\w*)", source))
    missing = sorted(needed - set(context) - set(env.globals) - internal_sets)
    assert not missing, (
        f"measurement.html.j2 requires template variables with no absent-state "
        f"default here: {missing} — mirror scripts.build_measurement.run()."
    )
    return env.get_template("measurement.html.j2").render(**context)


def _section(html: str) -> str:
    """Slice out just the Research Implications section.

    Every copy assertion is scoped to this slice so an unrelated section on this
    very long page can neither satisfy nor break a claim about our own copy.
    """
    start = html.find('id="ric-section"')
    if start == -1:
        return ""
    open_tag = html.rfind("<section", 0, start)
    end = html.find("</section>", start)
    assert end != -1, "ric-section is not closed"
    return html[open_tag : end + len("</section>")]


def _stable_anchor(card: dict) -> str:
    """Mirror the semantic (non-digest) card anchor contract."""
    parts = (
        card["method_family"],
        card["study_run_id"],
        card["selected_result_id"],
    )
    slug = "-".join(parts).replace("_", "-").replace("/", "-").replace("@", "-")
    return f"ric-{slug}"


def _metric_markup(card_html: str, code: str) -> str:
    marker = f'data-ric-code="{code}"'
    start = card_html.find(marker)
    assert start != -1, f"metric {code!r} has no dedicated rendered node"
    open_tag = card_html.rfind("<", 0, start)
    tag = re.match(r"<([a-z0-9]+)\b", card_html[open_tag:])
    assert tag
    end = card_html.find(f"</{tag.group(1)}>", start)
    assert end != -1
    return card_html[open_tag : end + len(tag.group(1)) + 3]


def _expected_metric_value(metric: dict) -> str:
    value = metric["value"]
    unit = metric["unit"]
    if unit == "boolean":
        return "Yes" if value else "No"
    if unit == "return_fraction_interval":
        return f"{value[0] * 100:.2f}% … {value[2] * 100:.2f}%"
    if unit in {"return_fraction", "fraction"}:
        return f"{value * 100:.3f}%"
    if unit in {"months", "events", "episodes", "draws", "tickers"}:
        return str(value)
    if unit == "probability" and isinstance(value, (int, float)) and not isinstance(value, bool):
        if value < 0.0001:
            return "below 0.0001"
        return f"{value:.4f}"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{value:.4f}"
    return str(value)


@pytest.fixture(scope="module")
def contract() -> dict:
    assert CONTRACT_PATH.exists(), (
        f"frozen contract missing at {CONTRACT_PATH} — the adapter owner writes "
        f"this file; this suite consumes it read-only."
    )
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def real_html(contract) -> str:
    return _render(research_implications=copy.deepcopy(contract))


@pytest.fixture(scope="module")
def real_section(real_html) -> str:
    return _section(real_html)


# ---------------------------------------------------------------------------
# 1. Absent / empty states
# ---------------------------------------------------------------------------


def test_visual_evidence_receipt_binds_the_template_and_eight_rest_cells():
    """BLOCKER 1/2: frames live in the governed receipt, bound to this template."""
    import yaml

    receipt_path = REPO / "mockups/evidence/f10x1-research-implication-card/EVIDENCE.yml"
    assert receipt_path.is_file(), "governed EVIDENCE.yml receipt is missing"
    receipt = yaml.safe_load(receipt_path.read_text(encoding="utf-8"))
    assert set(receipt) == {"schema", "changed_paths", "manifest"}
    assert receipt["schema"] == "mastermind.page_evidence_receipt.v1"
    assert receipt["changed_paths"] == ["templates/measurement.html.j2"]
    manifest_path = REPO / receipt["manifest"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema"] == "mastermind.p0_evidence.v2"
    assert manifest["totals"]["states_captured"] == 40
    assert len(manifest["pages"]) == 5
    measurement = next(
        page
        for page in manifest["pages"]
        if str(page.get("route", "")).endswith("measurement.html")
    )
    rest = [
        state
        for state in measurement["states"]
        if state.get("force_state") is None and state.get("captured") is True
    ]
    keys = {(state["viewport"], state["locale"], state["theme"]) for state in rest}
    required = {
        (viewport, locale, theme)
        for viewport in ("desktop", "mobile")
        for locale in ("en", "zh")
        for theme in ("dark", "light")
    }
    assert keys == required
    for state in rest:
        png = manifest_path.parent / state["file"]
        assert png.is_file() and png.stat().st_size > 1000
        assert state["applied_theme"] == state["theme"]
        assert state["applied_locale"] == state["locale"]
        assert state["viewport_width"] == (1440 if state["viewport"] == "desktop" else 390)
    samples = manifest.get("rail_samples", {}).get("frames", [])
    assert samples, "rail_samples.frames must record mode + mechanism per state"
    by_key = {
        (row["quality"], row["theme"], row["locale"]): row
        for row in samples
    }
    required_qualities = {
        "COMPLETE": "solid",
        "DIAGNOSTIC_ONLY": "dashed",
        "STALE": "hatched",
        "ARTIFACT_MISSING": "solid",
        "DIAGNOSTIC_FAILED": "solid",
    }
    for quality, mechanism in required_qualities.items():
        for theme in ("dark", "light"):
            for locale in ("en", "zh"):
                row = by_key.get((quality, theme, locale))
                assert row, f"missing rail sample {quality}/{theme}/{locale}"
                assert row["mechanism"] == mechanism, (
                    f"{quality} mechanism must be {mechanism}, got {row['mechanism']}"
                )
                assert "mode_rgb" in row and len(row["mode_rgb"]) == 3
                assert "mean_rgb" not in row
    for theme in ("dark", "light"):
        for locale in ("en", "zh"):
            complete = tuple(by_key[("COMPLETE", theme, locale)]["mode_rgb"])
            failed = tuple(by_key[("DIAGNOSTIC_FAILED", theme, locale)]["mode_rgb"])
            assert complete != failed, (
                f"COMPLETE rail must not equal DIAGNOSTIC_FAILED in {theme}/{locale}: "
                f"{complete} == {failed}"
            )
    stale_mech = {row["mechanism"] for row in samples if row["quality"] == "STALE"}
    other_mech = {row["mechanism"] for row in samples if row["quality"] == "UNKNOWN_FALLBACK"}
    if other_mech:
        assert stale_mech != other_mech or any(
            tuple(a["mode_rgb"]) != tuple(b["mode_rgb"])
            for a in samples if a["quality"] == "STALE"
            for b in samples if b["quality"] == "UNKNOWN_FALLBACK"
            if a["theme"] == b["theme"] and a["locale"] == b["locale"]
        )


def test_stale_ungoverned_ric_verify_shots_are_gone():
    leftovers = sorted((REPO / "verify_shots").glob("ric_*.png"))
    assert leftovers == [], f"stale ungoverned frames still tracked: {leftovers}"


def test_empty_envelope_renders_no_section():
    """Zero cards must render nothing — not an empty shell promising content."""
    html = _render(
        research_implications={
            "schema": "mastermind.research_implication_cards/v1",
            "cards": [],
        }
    )
    assert 'id="ric-section"' not in html


def test_missing_envelope_key_does_not_crash_the_page():
    """A wholly absent envelope must degrade, not raise."""
    html = _render(research_implications={})
    assert 'id="ric-section"' not in html
    assert "<html" in html


# ---------------------------------------------------------------------------
# 2. The two real frozen cards
# ---------------------------------------------------------------------------


def test_both_real_cards_render_with_stable_unique_anchors(contract, real_section):
    assert real_section, "Research Implications section did not render"
    families = [c["method_family"] for c in contract["cards"]]
    assert set(families) == {"synthetic_control", "event_study"}
    anchors = [_stable_anchor(card) for card in contract["cards"]]
    assert len(anchors) == len(set(anchors))
    for card, anchor in zip(contract["cards"], anchors, strict=True):
        assert (
            f'id="{anchor}"' in real_section
        ), f"no stable card-unique anchor for {card['method_family']}"


def test_anchor_is_semantic_not_card_digest(contract, real_section):
    """card_id changes whenever the artifact changes; an anchor must not.

    A deep link into this page has to survive a re-run of the estimator, so the
    anchor is keyed on stable method/run/selection semantics and the volatile
    card_id is disclosed as a receipt instead.
    """
    for card in contract["cards"]:
        assert f'id="ric-{card["card_id"]}"' not in real_section


def test_typed_quality_code_is_shown_verbatim(contract, real_section):
    """The machine's own word stays visible — in Receipts, not as a glance chip."""
    for card in contract["cards"]:
        receipts = _isolate_receipts(_isolate_card(real_section, card["method_family"]))
        assert card["quality"] in receipts, (
            f"typed quality {card['quality']} not surfaced in Receipts"
        )


def test_evidence_tier_is_disclosed(contract, real_section):
    for card in contract["cards"]:
        receipts = _isolate_receipts(_isolate_card(real_section, card["method_family"]))
        assert card["evidence_tier"] in receipts, (
            f"evidence_tier {card['evidence_tier']} not disclosed in Receipts"
        )


def test_card_ids_in_html_match_the_machine_contract(contract, real_section):
    """Human and machine projections must name the same objects."""
    for card in contract["cards"]:
        assert card["card_id"] in real_section, (
            "card_id absent from the human projection — human and machine "
            "projections must be traceable to the same card object"
        )


def test_every_contract_metric_has_an_exact_rendered_value(contract, real_section):
    """Projection identity includes values, not only object/card identifiers."""
    for card in contract["cards"]:
        card_html = _isolate_card(real_section, card["method_family"])
        metrics = (
            card["outputs"]
            + card["uncertainty"]
            + [item for item in card["diagnostics"] if "value" in item]
            + card["placebos_or_counterexamples"]
        )
        for metric in metrics:
            markup = _metric_markup(card_html, metric["code"])
            assert _expected_metric_value(metric) in markup, (
                f"{card['method_family']}.{metric['code']} does not render its "
                "contract value in the declared unit"
            )


def test_owner_interval_uses_outer_quantiles_and_discloses_median(
    contract, real_section
):
    card = next(c for c in contract["cards"] if c["method_family"] == "event_study")
    interval = next(item for item in card["uncertainty"] if item["code"] == "mean_ci90")
    markup = _metric_markup(_isolate_card(real_section, "event_study"), "mean_ci90")

    assert (
        f"{interval['value'][0] * 100:.2f}% … {interval['value'][2] * 100:.2f}%"
        in markup
    )
    assert f"{interval['value'][1] * 100:.2f}%" in markup
    assert "bootstrap median" in markup.lower()
    assert "自助法中位数" in markup


# ---------------------------------------------------------------------------
# 3. Stance and authority
# ---------------------------------------------------------------------------


def test_required_stance_line_present_in_both_languages(real_section):
    assert STANCE_EN in real_section
    assert STANCE_ZH in real_section


def test_all_five_authority_booleans_are_false_in_the_contract(contract):
    """Guard the input: this section may only ever render a zero-authority card."""
    for card in contract["cards"]:
        for key in AUTHORITY_KEYS:
            assert card["authority"][key] is False, f"{key} is not literal false"


def test_authority_is_disclosed_as_withheld(contract, real_section):
    """Zero authority is a claim the user must be able to read, not an omission."""
    for card in contract["cards"]:
        receipts = _isolate_receipts(_isolate_card(real_section, card["method_family"]))
        for key in AUTHORITY_KEYS:
            assert f"{key}=false" in receipts, (
                f"{key} not disclosed as withheld in Receipts"
            )


def test_no_ranking_or_trade_language_in_section(real_section):
    """Non-ranking by contract: no scores, ranks, or calls to act."""
    banned = [
        "rank #",
        "top pick",
        "buy signal",
        "sell signal",
        "best performing",
        "conviction score",
    ]
    low = real_section.lower()
    for phrase in banned:
        assert phrase not in low, f"ranking/trade language leaked: {phrase!r}"


# ---------------------------------------------------------------------------
# 4. Null discipline — typed, never zero
# ---------------------------------------------------------------------------


def test_null_effective_n_is_not_rendered_as_zero(contract, real_section):
    """The synthetic-control card has effective_n=null with a stated reason.

    Rendering that as 0 would invent an sample size the owner explicitly
    declined to define, so the null must survive to the page as a null.
    """
    sc = next(c for c in contract["cards"] if c["method_family"] == "synthetic_control")
    assert sc["effective_n"] is None, "fixture drift: effective_n is no longer null"

    card_html = _isolate_card(real_section, "synthetic_control")
    assert re.search(r"effective[^<]{0,40}</\w+>\s*<[^>]*>\s*0\s*<", card_html) is None
    assert ">0<" not in card_html.replace(
        " ", ""
    ), "a null effective_n appears to have been rendered as 0"
    assert "—" in card_html, "null not rendered with an explicit em-dash placeholder"


def test_null_reason_is_surfaced(contract, real_section):
    sc = next(c for c in contract["cards"] if c["method_family"] == "synthetic_control")
    assert sc["null_reasons"], "fixture drift: expected a stated null reason"
    reason_en = sc["null_reasons"][0]["detail"]["en"]
    assert reason_en[:40] in real_section, "null reason not shown to the reader"


def test_synthetic_null_is_never_coerced_to_zero():
    """Hostile fixture: an explicitly null output value must not become 0."""
    card = _minimal_card(
        family="synthetic_control",
        quality="DIAGNOSTIC_FAILED",
        outputs=[
            {
                "code": "cumulative_abnormal_return",
                "label": {"en": "CAR", "zh": "累计异常收益"},
                "source": "x",
                "unit": "return_fraction",
                "value": None,
            }
        ],
    )
    section = _section(_render(research_implications=_envelope([card])))
    assert "0.00%" not in section
    assert "—" in section


# ---------------------------------------------------------------------------
# 5. Ordered effect path — only where the owner marked it ordered
# ---------------------------------------------------------------------------


def test_ordered_path_renders_only_for_the_owner_supplied_card(contract, real_section):
    es = next(c for c in contract["cards"] if c["method_family"] == "event_study")
    sc = next(c for c in contract["cards"] if c["method_family"] == "synthetic_control")
    assert es["ordered_effect_path"]["owner_supplied"] is True
    assert sc["ordered_effect_path"] is None

    es_html = _isolate_card(real_section, "event_study")
    sc_html = _isolate_card(real_section, "synthetic_control")
    assert "ric-path" in es_html, "event-study ordered path did not render"
    assert "ric-path" not in sc_html, (
        "an ordered path was drawn for a card whose contract says the owner "
        "supplied none — that would be an invented effect curve"
    )


def test_ordered_path_plots_every_owner_point(contract, real_section):
    es = next(c for c in contract["cards"] if c["method_family"] == "event_study")
    es_html = _isolate_card(real_section, "event_study")
    points = es["ordered_effect_path"]["points"]
    m = re.search(r'class="ric-path-line"[^>]*\bd="([^"]+)"', es_html)
    assert m, "no ordered path polyline emitted"
    drawn = m.group(1).count(",")
    assert drawn == len(points), (
        f"ordered path drew {drawn} points but the owner supplied {len(points)} — "
        f"the curve must be complete or absent, never truncated"
    )


def test_ordered_path_axes_are_labelled_with_owner_units(contract, real_section):
    es = next(c for c in contract["cards"] if c["method_family"] == "event_study")
    es_html = _isolate_card(real_section, "event_study")
    path = es["ordered_effect_path"]
    assert str(path["points"][0]["horizon"]) in es_html
    assert str(path["points"][-1]["horizon"]) in es_html


def test_ordered_path_preserves_exploratory_and_sample_semantics(
    contract, real_section
):
    es = next(c for c in contract["cards"] if c["method_family"] == "event_study")
    path = es["ordered_effect_path"]
    es_html = _isolate_card(real_section, "event_study")
    selected = next(
        point
        for point in path["points"]
        if point["horizon"] == path["selected_horizon"]
    )

    assert "Exploratory — not gated" in es_html
    assert "探索性 — 未门控" in es_html
    assert path["evidence_status"] in _isolate_receipts(es_html)
    assert path["sample_basis"]["en"] in es_html
    assert path["comparison_note"]["en"] in es_html
    assert f"{selected['value'] * 100:.2f}%" in es_html
    assert f"n={selected['n']}" in es_html


def test_ordered_path_has_a_localized_accessible_name(contract, real_section):
    es = next(c for c in contract["cards"] if c["method_family"] == "event_study")
    es_html = _isolate_card(real_section, "event_study")
    path = es["ordered_effect_path"]
    assert path["accessible_name"]["en"] in es_html
    assert path["accessible_name"]["zh"] in es_html
    assert "<title>event_curve_announce</title>" not in es_html


def test_ordered_path_is_not_described_as_causal(real_section):
    """Descriptive event study — causal language would be an overclaim."""
    low = real_section.lower()
    for phrase in ("causal effect", "caused by", "treatment effect of", "因果效应导致"):
        assert phrase not in low, f"causal overclaim: {phrase!r}"


# ---------------------------------------------------------------------------
# 6. Receipts and provenance
# ---------------------------------------------------------------------------


def test_source_artifact_digests_are_shown(contract, real_section):
    for card in contract["cards"]:
        for artifact in card["source_artifacts"]:
            assert artifact["path"] in real_section, f"{artifact['path']} not cited"
            assert artifact["sha256"][:16] in real_section, (
                f"digest for {artifact['path']} not shown — a receipt without a "
                f"digest is not a receipt"
            )


def test_cutoff_is_shown_for_each_card(contract, real_section):
    for card in contract["cards"]:
        assert card["cutoff"] in real_section, "point-in-time cutoff not disclosed"


def test_null_artifact_as_of_is_typed_and_never_python_none(contract, real_section):
    roster = next(
        artifact
        for card in contract["cards"]
        for artifact in card["source_artifacts"]
        if artifact["role"] == "event_roster"
    )
    assert roster["as_of"] is None
    assert roster["as_of_reason"]["en"] in real_section
    assert roster["as_of_reason"]["zh"] in real_section
    assert "as of None" not in real_section


def test_missingness_is_visible_for_the_incomplete_card(contract, real_section):
    es = next(c for c in contract["cards"] if c["method_family"] == "event_study")
    assert es["missingness"], "fixture drift: expected a stated missing input"
    detail = es["missingness"][0]["detail"]["en"]
    assert detail[:40] in real_section, (
        "the missing hk_stocks_ext receipt is why this card is incomplete — it "
        "must be readable, not buried"
    )


def test_unresolved_historical_hsi_receipt_is_visible_without_claiming_snapshot(
    contract, real_section
):
    es = next(c for c in contract["cards"] if c["method_family"] == "event_study")
    missing = {item["code"]: item for item in es["missingness"]}
    receipt_gap = missing["hsi_benchmark_digest"]

    assert receipt_gap["reason"] == "INPUT_DIGEST_MISSING"
    assert receipt_gap["detail"]["en"] in real_section
    assert receipt_gap["detail"]["zh"] in real_section
    assert all(item["role"] != "benchmark" for item in es["source_artifacts"])
    assert "data/hk/_HSI.parquet" not in json.dumps(es, ensure_ascii=False)
    assert all(
        digest not in json.dumps(es, ensure_ascii=False)
        for digest in (
            "184cbdcf2437c9d8de172535cd87515b020708c9c441406391faa4aa895a1e45",
            "31a4e6d27653484458265b86cfcac3c7d9cd79da047d8509e4f0e0ec64302eac",
        )
    )


def test_limitations_are_rendered(contract, real_section):
    for card in contract["cards"]:
        for limitation in card["limitations"]:
            assert limitation["en"][:40] in real_section


# ---------------------------------------------------------------------------
# 7. Bilingual parity and house copy rules
# ---------------------------------------------------------------------------


def test_every_en_label_has_a_zh_sibling(real_section):
    en = len(re.findall(r'class="l-en"', real_section))
    zh = len(re.findall(r'class="l-zh"', real_section))
    assert en == zh, f"EN/ZH parity broken in this section: {en} EN vs {zh} ZH"
    assert en > 0


def test_zh_spans_contain_real_chinese(real_section):
    """A ZH span echoing English is worse than none — it looks translated."""
    spans = re.findall(r'<span class="l-zh">(.*?)</span>', real_section, re.DOTALL)
    assert spans
    han = re.compile(r"[一-鿿]")
    for span in spans:
        text = re.sub(r"<[^>]+>", "", span).strip()
        if not text or text.replace("—", "").strip() == "":
            continue
        # Numeric/mono receipts legitimately carry no Han characters.
        if re.fullmatch(r"[\d\s.,:%+\-—/()a-fA-F]*", text):
            continue
        assert han.search(text), f"ZH span carries no Chinese: {text[:60]!r}"


def test_no_validated_claim_in_section(real_section):
    """BC-2 house rule, CI-enforced elsewhere; pinned here for our own copy."""
    assert "validated" not in real_section.lower()
    assert "已验证" not in real_section


def test_no_falsifier_vocabulary_as_a_state_chip(contract, real_section):
    """Glance never carries falsifier/refutation vocabulary; owner labels stay in Receipts."""
    glance = _glance_outside_details(real_section)
    for token in ("证伪", "falsif", "refut", "FALSIFIED"):
        haystack = glance if token == "证伪" else glance.lower()
        needle = token if token == "证伪" else token.lower()
        assert needle not in haystack, f"{token!r} leaked onto the RIC glance tier"
    assert 'class="ric-state-code"' not in real_section
    for card in contract["cards"]:
        receipts = _isolate_receipts(_isolate_card(real_section, card["method_family"]))
        assert card["quality"] in receipts
        for gate in card["diagnostics"]:
            if "passed" not in gate:
                continue
            assert gate["label"]["en"] in receipts, (
                f"{gate['code']} owner label missing from Receipts"
            )
            if gate["label"].get("zh"):
                assert gate["label"]["zh"] in receipts


# ---------------------------------------------------------------------------
# 8. Filters are non-ranking
# ---------------------------------------------------------------------------


def test_filter_controls_exist_for_family_and_state(real_section):
    assert "ric-filter" in real_section, "no method/state filter controls"


def test_filter_controls_exist_for_evidence_tier(contract, real_section):
    """The frozen spec commits to an evidence-tier filter alongside family/state."""
    for tier in {card["evidence_tier"] for card in contract["cards"]}:
        assert f'data-ric-f="tier:{tier}"' in real_section, (
            f"no filter control for evidence_tier={tier!r}"
        )
        assert f'data-ric-tier="{tier}"' in real_section, (
            f"card article carries no data-ric-tier={tier!r} for JS filtering"
        )


def test_real_pair_lede_is_derived_from_card_states(contract, real_section):
    """Production pair: two cards, neither COMPLETE — the lede must say so."""
    n = len(contract["cards"])
    k = sum(1 for card in contract["cards"] if card["quality"] == "COMPLETE")
    assert n == 2 and k == 0
    assert "Neither card below is usable today." in real_section
    assert "下方两张卡片今天均不可用。" in real_section
    assert "None of the 2 cards below is usable today." not in real_section
    assert "下方 2 张卡片今天均不可用。" not in real_section


def test_dom_order_equals_contract_order(contract, real_section):
    """Filters may hide, never reorder — reordering would imply a ranking."""
    positions = []
    for card in contract["cards"]:
        idx = real_section.find(f'id="{_stable_anchor(card)}"')
        assert idx != -1
        positions.append(idx)
    assert positions == sorted(
        positions
    ), "cards are not in the contract's fixed non-ranking order"


def test_glance_header_is_plain_word_only(contract, real_section):
    """FRONT-END CLARITY LAW: the glance chip is a sentence, not a slug."""
    expected = {
        "DIAGNOSTIC_FAILED": ("Diagnostic failed", "诊断未通过"),
        "ARTIFACT_INCOMPLETE": ("Receipts incomplete", "凭证不完整"),
    }
    for card in contract["cards"]:
        header = _isolate_header(_isolate_card(real_section, card["method_family"]))
        en, zh = expected[card["quality"]]
        assert en in header
        assert zh in header
        assert card["quality"] not in header
        assert f'tier: {card["evidence_tier"]}' not in header
        assert card["method_family"] not in header
        assert "forecast_authority" not in header
        assert 'class="ric-state-code"' not in header


def test_machine_codes_live_only_in_receipts(contract, real_section):
    """Quality, tier, family, and authority flags are receipt facts."""
    for card in contract["cards"]:
        card_html = _isolate_card(real_section, card["method_family"])
        header = _isolate_header(card_html)
        receipts = _isolate_receipts(card_html)
        assert card["quality"] in receipts
        assert card["evidence_tier"] in receipts
        assert card["method_family"] in receipts
        assert card["quality"] not in header
        assert card["method_family"] not in header
        for key in AUTHORITY_KEYS:
            assert f"{key}=false" in receipts
            assert key not in header


def test_gate_quant_sits_inside_details(contract, real_section):
    """Per-gate numbers are behind a details row; the glance keeps the label."""
    found = 0
    for card in contract["cards"]:
        card_html = _isolate_card(real_section, card["method_family"])
        for gate in card["diagnostics"]:
            if "passed" not in gate:
                continue
            detail = gate["detail"]["en"]
            assert detail, f"{card['method_family']} gate {gate['code']} has empty detail"
            needle = (
                detail.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&#34;")
                .replace("'", "&#39;")
            )
            idx = card_html.find(needle)
            assert idx != -1, f"{gate['code']} detail missing from the card"
            details_open = card_html.rfind("<details", 0, idx)
            gate_open = card_html.rfind('class="ric-gate"', 0, idx)
            assert details_open > gate_open, (
                f"{gate['code']} quant sits in the glance gate row, not in <details>"
            )
            assert gate["label"]["en"] in card_html
            found += 1
    assert found >= 2, f"expected several gated diagnostics, found {found}"


def test_tier_filter_uses_a_plain_word_gloss(real_section):
    assert 'data-ric-f="tier:DIAGNOSTIC"' in real_section
    start = real_section.find('data-ric-f="tier:DIAGNOSTIC"')
    end = real_section.find("</button>", start)
    button = real_section[start:end]
    assert "Diagnostic only" in button
    assert "仅诊断" in button
    assert "Tier: DIAGNOSTIC" not in real_section
    assert "证据层级：DIAGNOSTIC" not in real_section


def test_cutoff_names_the_through_date(contract, real_section):
    """A glance date is a through-date, not a bare ISO timestamp."""
    for card in contract["cards"]:
        fig = _metric_markup(
            _isolate_card(real_section, card["method_family"]), "cutoff"
        )
        en, zh = _plain_cutoff(card["cutoff"])
        assert en in fig, f"{card['method_family']} cutoff glance is not {en}"
        assert zh in fig, f"{card['method_family']} cutoff glance is not {zh}"
        assert card["cutoff"] not in fig, (
            f"{card['method_family']} still prints the raw ISO {card['cutoff']}"
        )
        assert "Data through" in fig
        assert "数据截至" in fig


def test_filters_are_not_sort_controls(real_section):
    """No sort *control* may exist — but saying "never reordered" is required.

    Banning the bare word would forbid the disclaimer itself, so this targets
    the affordance: an ordering control, or copy offering one.
    """
    low = real_section.lower()
    for phrase in ("sort by", "排序方式", "highest first", "rank by", "order by"):
        assert phrase not in low, f"a sort control implies ranking: {phrase!r}"
    assert "<select" not in low, "a <select> in this section would offer ordering"
    assert "data-ric-sort" not in low


# ---------------------------------------------------------------------------
# 9. Hostile fixtures — states the real pair does not cover
# ---------------------------------------------------------------------------


def test_unknown_quality_state_degrades_without_inventing_a_verdict():
    """An unrecognised typed state must still render, neutrally.

    Fail-open on display, fail-closed on meaning: the glance is a generic
    owner-reported gloss and the raw code lives in Receipts. An unglossed
    quality still gets an Other-states filter chip so the bar cannot
    silently under-count the card set.
    """
    card = _minimal_card(family="event_study", quality="SOMETHING_NEW")
    section = _section(_render(research_implications=_envelope([card])))
    assert section
    header = _isolate_header(_isolate_card(section, "event_study"))
    assert "State not recognised" in header
    assert "状态未识别" in header
    assert "SOMETHING_NEW" not in header
    assert 'data-ric-f="q:other"' in section
    start = section.find('data-ric-f="q:other"')
    end = section.find("</button>", start)
    button = section[start:end]
    assert "Other states" in button
    assert "其他状态" in button
    receipts = _isolate_receipts(_isolate_card(section, "event_study"))
    assert "SOMETHING_NEW" in receipts


def test_card_with_no_outputs_renders_an_honest_empty_state():
    card = _minimal_card(
        family="event_study", quality="ARTIFACT_INCOMPLETE", outputs=[]
    )
    section = _section(_render(research_implications=_envelope([card])))
    assert section
    assert "0.00%" not in section


def test_html_in_artifact_text_is_escaped():
    """autoescape is off in this builder — free text must be escaped explicitly."""
    card = _minimal_card(family="event_study", quality="ARTIFACT_INCOMPLETE")
    card["limitations"] = [
        {"en": "<script>alert(1)</script>", "zh": "<script>x</script>"}
    ]
    section = _section(_render(research_implications=_envelope([card])))
    assert "<script>alert(1)</script>" not in section
    assert "&lt;script&gt;" in section


def test_single_card_envelope_renders(contract):
    one = {"schema": contract["schema"], "cards": [copy.deepcopy(contract["cards"][0])]}
    section = _section(_render(research_implications=one))
    assert f'id="{_stable_anchor(one["cards"][0])}"' in section
    assert "event-study-hincl2-event-study" not in section


def test_derived_lede_n1_usable():
    card = _minimal_card(family="event_study", quality="COMPLETE")
    section = _section(_render(research_implications=_envelope([card])))
    assert "The card below is usable today." in section
    assert "下方卡片今天可用。" in section


def test_derived_lede_n1_unusable():
    card = _minimal_card(family="event_study", quality="STALE")
    section = _section(_render(research_implications=_envelope([card])))
    assert "The card below is not usable today." in section
    assert "下方卡片今天不可用。" in section


def test_derived_lede_n2_k0():
    cards = [
        _minimal_card(family="event_study", quality="STALE"),
        _minimal_card(family="synthetic_control", quality="ARTIFACT_MISSING"),
    ]
    section = _section(_render(research_implications=_envelope(cards)))
    assert "Neither card below is usable today." in section
    assert "下方两张卡片今天均不可用。" in section


def test_derived_lede_n2_k1():
    cards = [
        _minimal_card(family="event_study", quality="COMPLETE"),
        _minimal_card(family="synthetic_control", quality="STALE"),
    ]
    section = _section(_render(research_implications=_envelope(cards)))
    assert "1 of 2 cards below are usable today." in section
    assert "下方 2 张卡片中有 1 张今天可用。" in section


def test_derived_lede_n2_k2():
    cards = [
        _minimal_card(family="event_study", quality="COMPLETE"),
        _minimal_card(family="synthetic_control", quality="COMPLETE"),
    ]
    section = _section(_render(research_implications=_envelope(cards)))
    assert "2 of 2 cards below are usable today." in section
    assert "下方 2 张卡片中有 2 张今天可用。" in section


def test_card_state_class_maps_quality():
    """Each typed quality gets its own rail class on the rendered card."""
    mapping = {
        "COMPLETE": "ric-s-complete",
        "DIAGNOSTIC_ONLY": "ric-s-diagnostic",
        "STALE": "ric-s-stale",
        "ARTIFACT_MISSING": "ric-s-missing",
        "DIAGNOSTIC_FAILED": "ric-s-failed",
        "ARTIFACT_INCOMPLETE": "ric-s-incomplete",
    }
    for quality, cls in mapping.items():
        card = _minimal_card(family="event_study", quality=quality)
        section = _section(_render(research_implications=_envelope([card])))
        article = _isolate_card(section, "event_study")
        assert f'class="ric-card {cls}"' in article, (
            f"{quality} must render class={cls!r}"
        )
        assert "ric-s-other" not in article


def test_state_rail_css_uses_distinct_semantic_tokens():
    """Rail colours come from existing theme tokens — never --up/--down."""
    css = (REPO / "templates" / "measurement.html.j2").read_text(encoding="utf-8")
    style_end = css.find("</style>")
    ric_css = css[css.find(".ric-rail") : style_end]
    assert "grid-template-columns:5px minmax(0,1fr)" in css[css.find(".ric-card{") : style_end]
    assert ".ric-card.ric-s-complete .ric-rail{background:var(--ink-ok)}" in ric_css
    assert (
        ".ric-card.ric-s-diagnostic .ric-rail{background:repeating-linear-gradient("
        "180deg,var(--muted) 0 10px,transparent 10px 16px)}"
    ) in ric_css
    assert (
        ".ric-card.ric-s-stale .ric-rail{background:repeating-linear-gradient("
        "135deg, var(--muted) 0 3px, transparent 3px 6px)}"
    ) in ric_css
    assert ".ric-card.ric-s-stale .ric-state{color:var(--muted)}" in ric_css
    assert ".ric-card.ric-s-missing .ric-rail{background:var(--warn)}" in ric_css
    assert ".ric-card.ric-s-failed  .ric-rail{background:var(--act)}" in ric_css
    assert ".ric-card.ric-s-incomplete .ric-rail{background:var(--warn)}" in ric_css
    assert "var(--ink-act)" not in ric_css
    assert "var(--up)" not in ric_css
    assert "var(--down)" not in ric_css
    assert "var(--ink-up)" not in ric_css
    assert "var(--ink-down)" not in ric_css


def test_glance_gate_is_plain_word_result(contract, real_section):
    """Glance leads with the result; a token dot marks met / not-met. Codes stay in Receipts."""
    glance = _glance_outside_details(real_section)
    glance_text = re.sub(r"<[^>]+>", "", glance)
    assert "Met — Positive control survives" in glance_text
    assert "Not met — Estimators unbiased" in glance_text
    assert "Met — Synthetic control not noisier" in glance_text
    assert "Met — Watch condition holds" in glance_text
    assert "已成立——正向对照成立" in glance_text
    assert "未成立——估计量无偏" in glance_text
    assert "已成立——合成对照噪声不高于基准" in glance_text
    assert "已成立——观察条件成立" in glance_text
    assert glance_text.index("Not met —") < glance_text.index("Estimators unbiased")
    assert glance_text.index("未成立——") < glance_text.index("估计量无偏")
    assert '<span class="ric-g-lead">Not met</span> — Estimators unbiased' in glance
    assert '<span class="ric-g-lead">未成立</span>——估计量无偏' in glance
    sc = _isolate_card(real_section, "synthetic_control")
    sc_glance = _glance_outside_details(sc)
    gate_rows = re.findall(r'class="ric-gate ric-g-(met|not)"', sc_glance)
    assert gate_rows == ["met", "not", "met", "met"]
    assert len(re.findall(r"\.ric-gate::before", (REPO / "templates" / "measurement.html.j2").read_text(encoding="utf-8"))) == 1
    gate_copy = " ".join(re.findall(r'class="ric-gate-b">\s*<span class="l-(?:en|zh)">(.*?)</span>', glance))
    for token in ("PC1", "PC2", "PC3", "F1", "PASS", "FAIL", "falsif", "证伪"):
        assert token not in gate_copy, f"{token!r} leaked onto the RIC glance gate row"
    assert 'class="ric-gate-m' not in glance
    assert ">PASS<" not in glance
    assert ">FAIL<" not in glance
    assert "F1 falsifier holds" not in glance
    assert "证伪条件成立" not in glance
    receipts = _isolate_receipts(sc)
    assert "PC1_positive_control_survives" in receipts
    assert "F1_falsifier_holds" in receipts
    assert "F1 falsifier holds" in receipts
    assert "F1 证伪条件成立" in receipts


def test_glance_gate_dot_uses_existing_tokens():
    """One 8px token dot per row: --ink-ok when met, --act when not met."""
    css = (REPO / "templates" / "measurement.html.j2").read_text(encoding="utf-8")
    style_end = css.find("</style>")
    ric_css = css[css.find(".ric-gates{") : style_end]
    assert ".ric-gate::before{content:\"\";flex:0 0 8px;width:8px;height:8px;" in ric_css
    assert "border-radius:var(--r-pill)" in ric_css[ric_css.find(".ric-gate::before") :]
    assert ".ric-gate.ric-g-met::before{background:var(--ink-ok)}" in ric_css
    assert ".ric-gate.ric-g-not::before{background:var(--act)}" in ric_css
    assert ".ric-gate.ric-g-not .ric-g-lead{font-weight:600}" in ric_css
    assert "ric-gate-m" not in ric_css
    assert "ric-gate-pass" not in ric_css
    assert "ric-gate-fail" not in ric_css


def test_probability_never_prints_a_rounded_zero():
    """Tiny p uses a floor; p at or above 0.0001 uses four decimals; never scientific notation."""
    tiny = _minimal_card(
        family="event_study",
        quality="DIAGNOSTIC_FAILED",
        outputs=[
            {
                "code": "p_tiny",
                "label": {"en": "Tiny p", "zh": "极小 p"},
                "unit": "probability",
                "value": 1e-7,
            },
            {
                "code": "p_below_floor",
                "label": {"en": "Just below floor", "zh": "略低于下限"},
                "unit": "probability",
                "value": 0.00006,
            },
            {
                "code": "p_above_floor",
                "label": {"en": "Just above floor", "zh": "略高于下限"},
                "unit": "probability",
                "value": 0.00012,
            },
            {
                "code": "p_ordinary",
                "label": {"en": "Ordinary p", "zh": "普通 p"},
                "unit": "probability",
                "value": 0.0123,
            },
            {
                "code": "p_absent",
                "label": {"en": "Absent p", "zh": "缺失 p"},
                "unit": "probability",
                "value": None,
            },
        ],
    )
    section = _section(_render(research_implications=_envelope([tiny])))
    tiny_fig = _metric_markup(section, "p_tiny")
    below_fig = _metric_markup(section, "p_below_floor")
    above_fig = _metric_markup(section, "p_above_floor")
    ordinary_fig = _metric_markup(section, "p_ordinary")
    absent_fig = _metric_markup(section, "p_absent")
    assert "below 0.0001" in tiny_fig
    assert "小于 0.0001" in tiny_fig
    assert "0.0000" not in tiny_fig
    assert "1e-7" not in tiny_fig
    assert "below 0.0001" in below_fig
    assert "小于 0.0001" in below_fig
    assert "6e-05" not in below_fig
    assert "0.00006" not in below_fig
    assert "0.0001" in above_fig
    assert "小于 0.0001" not in above_fig
    assert "below 0.0001" not in above_fig
    assert "1.2e-04" not in above_fig
    assert "0.0123" in ordinary_fig
    assert "0.0000" not in ordinary_fig
    assert '<span class="ric-null">—</span>' in absent_fig


def test_production_zero_p_is_a_computed_underflow(contract, real_section):
    """MINOR 3: owner Newey-West p is round(2*(1-Φ(|t|)), 4). t=8.291 underflows to 0.0.

    That is a real computation, not a not-computed sentinel (those are None when n<8).
    The front therefore prints the tiny-p floor, not “p-value not computed”.
    """
    sc = next(c for c in contract["cards"] if c["method_family"] == "synthetic_control")
    p_metric = next(m for m in sc["outputs"] if m["code"] == "monthly_newey_west_p")
    assert p_metric["value"] == 0.0
    markup = _metric_markup(_isolate_card(real_section, "synthetic_control"), "monthly_newey_west_p")
    assert "below 0.0001" in markup
    assert "小于 0.0001" in markup
    assert "p-value not computed" not in markup
    assert "p 值未计算" not in markup


def test_stale_state_text_is_the_window_sentence():
    card = _minimal_card(family="event_study", quality="STALE")
    header = _isolate_header(
        _isolate_card(_section(_render(research_implications=_envelope([card]))), "event_study")
    )
    assert "Out of date — receipt older than its window" in header
    assert "已过期——回执早于其窗口" in header


def test_unknown_qualities_share_one_other_states_chip():
    cards = [
        _minimal_card(family="event_study", quality="SOMETHING_NEW"),
        _minimal_card(family="synthetic_control", quality="ALSO_NEW"),
    ]
    section = _section(_render(research_implications=_envelope(cards)))
    assert section.count('data-ric-f="q:other"') == 1
    assert 'data-ric-f="q:SOMETHING_NEW"' not in section
    assert 'data-ric-unglossed="1"' in section


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _envelope(cards: list[dict]) -> dict:
    return {"schema": "mastermind.research_implication_cards/v1", "cards": cards}


def _minimal_card(*, family: str, quality: str, outputs=None) -> dict:
    """A contract-shaped card with only the keys the template may rely on."""
    return {
        "schema": "mastermind.research_implication_card/v1",
        "card_id": f"ric_test_{family}",
        "adapter_version": f"{family}/v1",
        "method_family": family,
        "method_revision": "sha256:" + "0" * 64,
        "study_run_id": f"{family}@2026-01-01",
        "selected_result_id": "test/result",
        "quality": quality,
        "evidence_tier": "DIAGNOSTIC",
        "cutoff": "2026-01-01",
        "question": {"en": "Test question?", "zh": "测试问题？"},
        "estimand": {"en": "Test estimand.", "zh": "测试估计量。"},
        "population": {"family": "test"},
        "sample_n": 10,
        "effective_n": None,
        "outputs": [] if outputs is None else outputs,
        "uncertainty": [],
        "diagnostics": [],
        "placebos_or_counterexamples": [],
        "exclusions": [],
        "missingness": [],
        "null_reasons": [
            {
                "code": "effective_n",
                "detail": {"en": "Not defined by the owner.", "zh": "所有者未定义。"},
            }
        ],
        "limitations": [{"en": "Test limitation.", "zh": "测试限制。"}],
        "ordered_effect_path": None,
        "source_artifacts": [
            {
                "as_of": "2026-01-01",
                "as_of_reason": None,
                "path": "data/experiments/test.json",
                "rights": "REPOSITORY_INTERNAL",
                "role": "result",
                "sha256": "a" * 64,
            }
        ],
        "code_identity": [
            {
                "as_of": "2026-01-01",
                "as_of_reason": None,
                "path": "scripts/test.py",
                "rights": "REPOSITORY_INTERNAL",
                "role": "generator",
                "sha256": "b" * 64,
            }
        ],
        "authority": {key: False for key in AUTHORITY_KEYS},
    }


def _isolate_card(section: str, family: str) -> str:
    """Return just one card's markup, so a claim about card A cannot be
    accidentally satisfied by card B's copy."""
    start = section.find(f'data-ric-family="{family}"')
    assert start != -1, f"card {family} not found in section"
    open_tag = section.rfind("<article", 0, start)
    assert open_tag != -1, f"card {family} is not an <article>"
    end = section.find("</article>", start)
    assert end != -1, f"card {family} is not closed"
    return section[open_tag : end + len("</article>")]


def _isolate_header(card_html: str) -> str:
    start = card_html.find('class="ric-hd"')
    assert start != -1, "card has no glance header"
    open_tag = card_html.rfind("<", 0, start)
    end = card_html.find("</div>", start)
    assert end != -1
    return card_html[open_tag : end + len("</div>")]


def _glance_outside_details(section: str) -> str:
    """The glance tier is everything in the RIC section outside <details>."""
    html = section
    innermost = re.compile(
        r"<details\b[^>]*>((?:(?!<details\b).)*?)</details>", re.DOTALL
    )
    previous = None
    while previous != html:
        previous = html
        html = innermost.sub("", html)
    return html


def _isolate_receipts(card_html: str) -> str:
    marker = 'class="ric-rc"'
    start = card_html.find(marker)
    assert start != -1, "card has no Receipts block"
    open_tag = card_html.rfind("<", 0, start)
    end = card_html.find("</dl>", start)
    assert end != -1
    return card_html[open_tag : end + len("</dl>")]


def _plain_cutoff(iso: str) -> tuple[str, str]:
    year, month, day = iso.split("-")
    months = (
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    )
    en = f"{int(day)} {months[int(month) - 1]} {year}"
    zh = f"{year}年{int(month)}月{int(day)}日"
    return en, zh
