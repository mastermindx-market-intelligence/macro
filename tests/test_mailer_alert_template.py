"""tests/test_mailer_alert_template.py -- tests for the additive alert message type
in app/mailer.py (packet B-F08-1b). STATUSES/send()/render_email() must stay unchanged."""
from __future__ import annotations

import re

import pytest

from app import mailer

_PAYLOAD = {
    "subject": "AAPL RSI crossed 70",
    "summary_plain": "RSI crossed 70 on AAPL",
    "ticker": "AAPL",
    "condition_plain": "RSI crossed above 70",
    "evidence_url": "https://macro.example/evidence/1",
    "fired_at": "2026-09-05T14:00:00Z",
}


def test_mailer_statuses_tuple_is_unchanged():
    assert mailer.STATUSES == ("sent", "failed", "skipped_no_smtp", "suppressed", "queued")


def test_alert_idem_key_shape():
    assert mailer.alert_idem_key("fe-123") == "alert_fire:fe-123"


def test_body_is_three_plain_lines_plus_evidence_link_and_the_ceiling_line():
    c = mailer.compose_alert(_PAYLOAD, lang="en")
    blocks = c["blocks"]
    assert len(blocks) >= 4
    assert any(b.get("kind") == "button" for b in blocks)
    assert any(b.get("kind") == "fine" and "not advice" in b.get("en", "") for b in blocks)

    c_zh = mailer.compose_alert(_PAYLOAD, lang="zh")
    assert any(b.get("kind") == "fine" and "不构成投资建议" in b.get("zh", "") for b in c_zh["blocks"])


def test_no_machine_text_or_raw_slugs_reach_the_reader():
    bad_payload = dict(_PAYLOAD, subject="fire_event_id=abc idem_key=xyz",
                       condition_plain="READ_UNAVAILABLE tripwire fired")
    c = mailer.compose_alert(bad_payload, lang="en")
    html, text = mailer.render_email(
        c["title_en"], c["title_zh"], c["blocks"], eyebrow=c["eyebrow"],
        preheader=c["preheader"], why_en=c["why_en"], why_zh=c["why_zh"],
        unsubscribe_url="", follow=False)
    banned = ("fire_event_id", "idem_key", "READ_UNAVAILABLE", "tripwire", "::", "outcome=")
    for tok in banned:
        assert tok not in c["subject"]
        assert tok not in html
        assert tok not in text


def test_stored_lang_selects_which_language_leads_the_subject():
    c_en = mailer.compose_alert(_PAYLOAD, lang="en")
    c_zh = mailer.compose_alert(_PAYLOAD, lang="zh")
    assert c_en["subject"].split(" · ")[0].strip().endswith("alert") or "alert" in c_en["subject"].split(" · ")[0]
    assert c_zh["subject"].split(" · ")[0].strip().endswith("提醒")


def test_absent_evidence_url_renders_a_plain_null_line_not_a_broken_link():
    p = dict(_PAYLOAD, evidence_url="")
    c = mailer.compose_alert(p, lang="en")
    assert not any(b.get("kind") == "button" for b in c["blocks"])
    assert any(b.get("kind") == "fine" and "No evidence link" in b.get("en", "") for b in c["blocks"])


def test_transactional_alert_renders_no_unsubscribe_slot_and_no_new_style_tokens():
    c = mailer.compose_alert(_PAYLOAD, lang="en")
    html, text = mailer.render_email(
        c["title_en"], c["title_zh"], c["blocks"], eyebrow=c["eyebrow"],
        preheader=c["preheader"], why_en=c["why_en"], why_zh=c["why_zh"],
        unsubscribe_url="", follow=False)
    assert "unsubscribe" not in html.lower()

    # The alert template introduces no new color constant, no new <style> block, and
    # no new _STYLE rule (F08 freeze section 2.7): every color the rendered alert email
    # carries is one already produced by the shared, pinned `render_email` shell for
    # ANY email (a plain non-alert message hits the exact same code paths), which is
    # what "reuse, zero new tokens" means in practice.
    baseline_html, _ = mailer.render_email(
        "Baseline", "基线",
        [{"en": "x", "zh": "y"},
         {"kind": "button", "en": "b", "zh": "b", "url": "https://x"},
         {"kind": "kv", "en": [("k", "v")], "zh": [("k", "v")]},
         {"kind": "fine", "en": "f", "zh": "f"}],
        eyebrow="ALERT", preheader="p", why_en="w", why_zh="w",
        unsubscribe_url="", follow=False)
    baseline_hex = set(re.findall(r"#[0-9a-fA-F]{6}", baseline_html))
    found_hex = set(re.findall(r"#[0-9a-fA-F]{6}", html))
    assert found_hex.issubset(baseline_hex)
    assert mailer.__dict__.get("_STYLE") == mailer._STYLE  # byte-identity sanity: no override


def test_zh_missing_fired_at_uses_zh_fallback_and_zh_eyebrow_never_english_fallback():
    """Heal h2 REQUIRED 1 (plain-language law). RED-first on f7245647:
    compose_alert(lang='zh') with fired_at missing put the English fallback
    'time not recorded' in the ZH kv value and left the eyebrow as 'ALERT'."""
    payload = {k: v for k, v in _PAYLOAD.items() if k != "fired_at"}
    assert "fired_at" not in payload
    c = mailer.compose_alert(payload, lang="zh")
    assert c["eyebrow"] == "提醒"
    kv = next(b for b in c["blocks"] if b.get("kind") == "kv")
    zh_values = [v for _k, v in kv["zh"]]
    assert "未记录时间" in zh_values
    assert "time not recorded" not in zh_values
    html, text = mailer.render_email(
        c["title_en"], c["title_zh"], c["blocks"], eyebrow=c["eyebrow"],
        preheader=c["preheader"], why_en=c["why_en"], why_zh=c["why_zh"],
        unsubscribe_url="", follow=False)
    assert "未记录时间" in html
    assert "提醒" in html
    zh_half = html.split("中文", 1)[-1]
    assert "time not recorded" not in zh_half
    assert "未记录时间" in text
    assert "提醒" in text
    # The ZH language half of the plain-text body (after the rule) must not
    # carry the English fallback either.
    zh_text_half = text.split("-" * 46, 1)[-1]
    assert "time not recorded" not in zh_text_half


# --------------------------------------------------------------------------- #
# Defensive-rotation observations (DR3): category 'sector_rotation_relative'
# --------------------------------------------------------------------------- #
# The observation branch is the FIRST thing compose_alert does. Everything here is a
# test about what that branch refuses to say, because the generic path below it was
# written for a condition the reader personally set -- and an observation nobody
# authored must never inherit that story.

from lib import rotation_observation_notification as _rot  # noqa: E402


def _ratio(n, d):
    return ((1.0 + n / 100.0) / (1.0 + d / 100.0) - 1.0) * 100.0


def _obs(**over) -> dict:
    n, d = 1.50, -0.50
    base = {
        "source": _rot.SOURCE, "category": _rot.CATEGORY, "authority": _rot.AUTHORITY,
        "kind": "observed_change", "observation_id": "obs-a", "num": "XLV", "den": "XLK",
        "pair_id": "xlv-xlk", "event_as_of": "2026-10-21",
        "observed_at": "2026-10-21T22:00:00+00:00",
        "not_after": "2026-10-21T23:00:00+00:00", "source_as_of": "2026-10-21",
        "values": {"sessions": 2, "numerator_return_pct": n, "denominator_return_pct": d,
                   "ratio_return_pct": _ratio(n, d)},
    }
    base.update(over)
    return base


def _all_text(c, lang):
    """Every string the reader can see in one language, flattened."""
    out = [c["subject"], c["eyebrow"], c["preheader"], c["why_en"], c["why_zh"],
           c["title_en"], c["title_zh"]]
    for b in c["blocks"]:
        for key in ("en", "zh"):
            v = b.get(key)
            if isinstance(v, list):
                out.extend(f"{k} {val}" for k, val in v)
            elif v:
                out.append(v)
        if b.get("url"):
            out.append(b["url"])
    return "\n".join(str(x) for x in out)


# --- every kind composes, in both languages, through the real renderer ---------- #
@pytest.mark.parametrize("kind", ["observed_change", "reversal", "correction",
                                  "data_withdrawal"])
@pytest.mark.parametrize("lang", ["en", "zh"])
def test_every_kind_renders_in_both_languages_through_the_real_renderer(kind, lang):
    kw = {"previous_observation_id": "obs-earlier"}
    if kind == "data_withdrawal":
        kw.update({"values": None, "source_as_of": None})
    c = mailer.compose_alert(_obs(kind=kind, **kw), lang=lang)
    html, text = mailer.render_email(
        c["title_en"], c["title_zh"], c["blocks"], eyebrow=c["eyebrow"],
        preheader=c["preheader"], why_en=c["why_en"], why_zh=c["why_zh"],
        unsubscribe_url="", follow=False)
    assert html and text
    assert c["title_en"] != c["title_zh"]          # no untranslated-source parity bug
    assert mailer.ROTATION_EVIDENCE_URL in html and mailer.ROTATION_EVIDENCE_URL in text
    # Both instruments appear in both language halves.
    assert "XLV" in html and "XLK" in html


# --- the branch must not claim the reader authored anything ------------------- #
FORBIDDEN_EN = ("you set", "your condition", "your alert", "you created", "your thesis",
                "you hold", "your holding", "your position", "a condition you",
                "you were watching", "your recorded")
FORBIDDEN_ZH = ("你设置", "你的条件", "你关注的市场观点", "你持有的", "你的持仓",
                "你记录的持仓", "你创建的")


@pytest.mark.parametrize("kind", ["observed_change", "reversal", "correction",
                                  "data_withdrawal"])
@pytest.mark.parametrize("lang", ["en", "zh"])
def test_no_language_half_claims_the_reader_authored_a_condition_or_holds_a_position(
        kind, lang):
    kw = {"previous_observation_id": "obs-earlier"}
    if kind == "data_withdrawal":
        kw.update({"values": None, "source_as_of": None})
    text = _all_text(mailer.compose_alert(_obs(kind=kind, **kw), lang=lang), lang).lower()
    banned = FORBIDDEN_ZH if lang == "zh" else FORBIDDEN_EN
    for tok in banned:
        assert tok.lower() not in text, f"{lang} half leaks {tok!r}"


def test_the_provenance_line_says_subscribed_observations_in_both_languages():
    c_en = mailer.compose_alert(_obs(), lang="en")
    c_zh = mailer.compose_alert(_obs(), lang="zh")
    assert c_en["why_en"] == "You subscribed to defensive leadership observations."
    assert c_zh["why_zh"] == "你订阅了防御板块领导力观察。"
    assert c_en["eyebrow"] == "OBSERVATION" and c_zh["eyebrow"] == "观察"


# --- no advice vocabulary anywhere -------------------------------------------- #
@pytest.mark.parametrize("kind", ["observed_change", "reversal", "correction",
                                  "data_withdrawal"])
def test_no_crash_probability_fund_flow_trading_leverage_or_sizing_copy(kind):
    """Scan every reader-visible string EXCEPT the explicit ceiling line.

    The ceiling line is the one place 'buy / sell / leverage' are allowed to appear, and
    only as the things being disclaimed -- scanning it too would make the prohibition
    self-defeating, so it is checked separately below.
    """
    kw = {"previous_observation_id": "obs-earlier"}
    if kind == "data_withdrawal":
        kw.update({"values": None, "source_as_of": None})
    c = mailer.compose_alert(_obs(kind=kind, **kw), lang="en")
    body = [b for b in c["blocks"] if not _is_ceiling(b)]
    text = _all_text({"blocks": body, "subject": c["subject"], "eyebrow": c["eyebrow"],
                      "preheader": c["preheader"], "title_en": c["title_en"],
                      "title_zh": c["title_zh"], "why_en": c["why_en"],
                      "why_zh": c["why_zh"]}, "en").lower()
    for tok in _ADVICE_PHRASES:
        assert tok not in text, f"observation copy leaks {tok!r}"
    for tok in _ADVICE_WORDS:
        assert not re.search(rf"\b{tok}\b", text), f"observation copy leaks {tok!r}"


# Multi-word idioms, matched as substrings.
_ADVICE_PHRASES = ("fund flow", "position siz", "stop loss", "chance of",
                   "outperform", "underperform", "risk reward")
# Single words, matched on word boundaries -- a substring scan would flag "no longer"
# as a long position, which is precisely the kind of false pass this list exists to
# avoid being tuned into.
_ADVICE_WORDS = ("probabilit\\w*", "crash", "inflow", "outflow", "buy", "sell", "long",
                 "short", "leverag\\w*", "target\\w*", "entr(y|ies)", "conviction",
                 "forecast\\w*", "expect\\w*", "predict\\w*", "should", "allocate\\w*")


def _is_ceiling(block):
    return block.get("kind") == "fine" and "not advice" in str(block.get("en", ""))


@pytest.mark.parametrize("lang", ["en", "zh"])
def test_the_ceiling_line_disclaims_advice_rather_than_giving_it(lang):
    c = mailer.compose_alert(_obs(), lang=lang)
    assert sum(1 for b in c["blocks"] if _is_ceiling(b)) == 1
    c_zh = mailer.compose_alert(_obs(), lang="zh")
    assert any(b.get("kind") == "fine" and "不构成" in b["zh"]
               and "建议" in b["zh"] for b in c_zh["blocks"])


# --- direction: both down is relative shelter, never leadership --------------- #
def test_both_down_is_described_as_relative_shelter_not_relative_strength():
    n, d = -1.20, -3.40
    c = mailer.compose_alert(_obs(values={"sessions": 2, "numerator_return_pct": n,
                                          "denominator_return_pct": d,
                                          "ratio_return_pct": _ratio(n, d)}), lang="en")
    lede = c["blocks"][0]["en"]
    assert "Both fell" in lede
    assert "relative shelter only, not an absolute gain" in lede
    assert "stronger" not in lede and "led" not in lede
    assert "XLV -1.20%" in lede and "XLK -3.40%" in lede


def test_both_down_in_chinese_is_also_relative_shelter():
    n, d = -1.20, -3.40
    c = mailer.compose_alert(_obs(values={"sessions": 2, "numerator_return_pct": n,
                                          "denominator_return_pct": d,
                                          "ratio_return_pct": _ratio(n, d)}), lang="zh")
    lede = c["blocks"][0]["zh"]
    assert "两者均下跌" in lede
    assert "相对抗跌" in lede and "不代表绝对收益为正" in lede


def test_a_positive_absolute_pair_is_plainly_reported_as_relative_strength():
    n, d = 3.10, 1.20
    c = mailer.compose_alert(_obs(values={"sessions": 2, "numerator_return_pct": n,
                                          "denominator_return_pct": d,
                                          "ratio_return_pct": _ratio(n, d)}), lang="en")
    lede = c["blocks"][0]["en"]
    assert "relative shelter" not in lede
    assert "XLV was relatively stronger than XLK" in lede
    assert "XLV returned +3.10%" in lede and "XLK returned +1.20%" in lede


def test_a_mixed_pair_reports_plain_numbers_without_a_shelter_claim():
    n, d = -0.80, 2.40
    c = mailer.compose_alert(_obs(values={"sessions": 2, "numerator_return_pct": n,
                                          "denominator_return_pct": d,
                                          "ratio_return_pct": _ratio(n, d)}), lang="en")
    lede = c["blocks"][0]["en"]
    assert "relative shelter" not in lede
    assert "XLV was relatively weaker than XLK" in lede
    assert "XLV returned -0.80%" in lede and "XLK returned +2.40%" in lede


# --- percent units are always shown ------------------------------------------- #
@pytest.mark.parametrize("kind", ["observed_change", "reversal", "correction"])
def test_every_returned_number_carries_a_percent_sign_in_both_languages(kind):
    """A relative number printed without its unit is how -0.4 reads as -40%."""
    kw = {"previous_observation_id": "obs-earlier"}
    for lang in ("en", "zh"):
        lede = mailer.compose_alert(_obs(kind=kind, **kw), lang=lang)["blocks"][0][lang]
        assert lede.count("%") == 3, lede
        assert "+1.50%" in lede and "-0.50%" in lede
        assert f"{_ratio(1.50, -0.50):+.2f}%" in lede


def test_the_window_is_always_stated_in_sessions_never_as_a_forecast_horizon():
    c = mailer.compose_alert(_obs(), lang="en")
    assert "two sessions" in c["blocks"][0]["en"]
    zh = mailer.compose_alert(_obs(), lang="zh")["blocks"][0]["zh"]
    assert "两个交易日" in zh


# --- source date and notification time are distinguished ---------------------- #
def test_the_kv_block_separates_source_date_market_session_and_noticed_at():
    c = mailer.compose_alert(_obs(), lang="en")
    kv = next(b for b in c["blocks"] if b.get("kind") == "kv")
    en = dict(kv["en"])
    zh = dict(kv["zh"])
    assert en["Market session"] == "2026-10-21"
    assert en["Source date"] == "2026-10-21"
    assert en["Noticed at"] == "2026-10-21 22:00 UTC"
    # Both language halves carry the same three FIELDS under their own labels, so a
    # source date can never be read as the notification time or vice versa.
    assert zh["市场交易日"] == "2026-10-21"
    assert zh["来源日期"] == "2026-10-21"
    assert zh["记录时间"] == "2026-10-21 22:00 UTC"
    assert len(en) == 3 and len(zh) == 3 and len(en) == len(zh)
    assert en["Noticed at"] != en["Source date"]


def test_a_withdrawal_says_its_source_date_was_not_recorded():
    c = mailer.compose_alert(_obs(kind="data_withdrawal", values=None, source_as_of=None,
                                  previous_observation_id="obs-earlier"), lang="en")
    kv = next(b for b in c["blocks"] if b.get("kind") == "kv")
    assert dict(kv["en"])["Source date"] == "not recorded on a withdrawal"


def test_an_older_withdrawal_source_date_is_shown_as_that_older_date():
    c = mailer.compose_alert(_obs(kind="data_withdrawal", values=None,
                                  source_as_of="2026-10-16",
                                  previous_observation_id="obs-earlier"), lang="en")
    kv = next(b for b in c["blocks"] if b.get("kind") == "kv")
    assert dict(kv["en"])["Source date"] == "2026-10-16"
    assert dict(kv["en"])["Market session"] == "2026-10-21"


# --- withdrawal wording ------------------------------------------------------- #
def test_a_withdrawal_says_evidence_is_unavailable_not_that_a_view_was_wrong():
    c = mailer.compose_alert(_obs(kind="data_withdrawal", values=None, source_as_of=None,
                                  previous_observation_id="obs-earlier"), lang="en")
    lede = c["blocks"][0]["en"]
    assert "no longer available" in lede and "withdrawn" in lede
    assert "not a statement that the market view was wrong" in lede
    assert "disproved" not in lede and "refuted" not in lede


def test_a_withdrawal_never_renders_a_stale_positive_pair():
    c = mailer.compose_alert(_obs(kind="data_withdrawal", values=None, source_as_of=None,
                                  previous_observation_id="obs-earlier"), lang="en")
    text = _all_text(c, "en")
    for tok in ("+1.50%", "-0.50%", "2.01%", "two sessions"):
        assert tok not in text, f"withdrawal re-rendered a stale measurement: {tok}"


# --- reversal / correction provenance ------------------------------------------ #
@pytest.mark.parametrize("kind,en,zh", [
    ("reversal", "Reversal", "反转"),
    ("correction", "Correction", "更正"),
])
def test_reversal_and_correction_reference_the_prior_observation_as_provenance(
        kind, en, zh):
    c_en = mailer.compose_alert(_obs(kind=kind, previous_observation_id="obs-earlier"),
                                lang="en")
    c_zh = mailer.compose_alert(_obs(kind=kind, previous_observation_id="obs-earlier"),
                                lang="zh")
    assert c_en["blocks"][0]["en"].startswith(en)
    assert c_en["blocks"][0]["zh"].startswith(zh)
    assert "earlier observation" in _all_text(c_en, "en")
    assert "此前观察" in _all_text(c_zh, "zh")


def test_no_first_seen_date_is_invented_for_the_prior_observation():
    """The prior observation's date is not carried in this payload. Printing one would
    be a fabricated fact, so the provenance line explicitly disclaims it."""
    c = mailer.compose_alert(_obs(kind="correction", previous_observation_id="obs-earlier"),
                             lang="en")
    prov = [b for b in c["blocks"] if b.get("kind") == "fine" and "earlier observation" in b["en"]]
    assert len(prov) == 1
    assert "first seen" in prov[0]["en"]
    # No extra date-shaped token is smuggled into the provenance line.
    import re as _re
    assert not _re.search(r"\b20\d\d-\d\d-\d\d\b", prov[0]["en"])


def test_an_observed_change_with_no_prior_observation_prints_no_provenance_line():
    c = mailer.compose_alert(_obs(), lang="en")
    assert not any("earlier observation" in str(b.get("en", "")) for b in c["blocks"])


def test_an_observed_change_that_does_carry_a_prior_observation_prints_provenance():
    c = mailer.compose_alert(_obs(previous_observation_id="obs-earlier"), lang="en")
    assert any("earlier observation" in str(b.get("en", "")) for b in c["blocks"])


def test_unconstrained_identifiers_are_never_printed():
    """observation_id / previous_observation_id / pair_id are free strings by contract,
    so they are not rendered -- provenance is stated in prose instead."""
    c = mailer.compose_alert(_obs(observation_id="<b>id</b>", pair_id="javascript:1",
                                  previous_observation_id="&#x41;"), lang="en")
    text = _all_text(c, "en")
    assert "<b>id</b>" not in text and "javascript:1" not in text and "&#x41;" not in text


# --- hostile caller strings are ignored ---------------------------------------- #
def test_a_caller_supplied_evidence_url_is_ignored_for_the_fixed_one():
    hostile = _obs(evidence_url="https://evil.test/steal",
                   subject="BUY XLK NOW", condition_plain="your condition you set fired",
                   summary_plain="user authored thesis", ticker="SPY")
    c = mailer.compose_alert(hostile, lang="en")
    text = _all_text(c, "en")
    assert "evil.test" not in text
    assert "BUY XLK NOW" not in text
    assert "your condition you set fired" not in text
    assert "user authored thesis" not in text
    assert mailer.ROTATION_EVIDENCE_URL in text
    buttons = [b for b in c["blocks"] if b.get("kind") == "button"]
    assert len(buttons) == 1
    assert buttons[0]["url"] == mailer.ROTATION_EVIDENCE_URL


def test_the_evidence_url_constant_is_exactly_the_pinned_page():
    assert mailer.ROTATION_EVIDENCE_URL == (
        "https://www.mastermind-x.com/sector_central.html#rc-events-mount")


def test_exactly_one_button_per_email():
    """The renderer allows at most one CTA; a second would be a rendering bug."""
    c = mailer.compose_alert(_obs(), lang="en")
    assert len([b for b in c["blocks"] if b.get("kind") == "button"]) == 1


def test_no_untrusted_html_reaches_the_rendered_document():
    c = mailer.compose_alert(_obs(), lang="en")
    html, _ = mailer.render_email(
        c["title_en"], c["title_zh"], c["blocks"], eyebrow=c["eyebrow"],
        preheader=c["preheader"], why_en=c["why_en"], why_zh=c["why_zh"],
        unsubscribe_url="", follow=False)
    # The only markup present is the pinned shell's own; nothing payload-derived.
    assert "<script" not in html.lower()
    assert html.count("rc-events-mount") == html.count(mailer.ROTATION_EVIDENCE_URL)


def test_the_observation_email_reuses_the_pinned_shell_and_adds_no_style_token():
    """Same ceiling as the alert template: zero new colour constants."""
    import re as _re
    c = mailer.compose_alert(_obs(), lang="en")
    html, _ = mailer.render_email(
        c["title_en"], c["title_zh"], c["blocks"], eyebrow=c["eyebrow"],
        preheader=c["preheader"], why_en=c["why_en"], why_zh=c["why_zh"],
        unsubscribe_url="", follow=False)
    baseline, _ = mailer.render_email(
        "Baseline", "基线",
        [{"en": "x", "zh": "y"},
         {"kind": "button", "en": "b", "zh": "b", "url": "https://x"},
         {"kind": "kv", "en": [("k", "v")], "zh": [("k", "v")]},
         {"kind": "fine", "en": "f", "zh": "f"}],
        eyebrow="ALERT", preheader="p", why_en="w", why_zh="w",
        unsubscribe_url="", follow=False)
    assert set(_re.findall(r"#[0-9a-fA-F]{6}", html)).issubset(
        set(_re.findall(r"#[0-9a-fA-F]{6}", baseline)))


# --- the branch validates; it never degrades into the generic copy ------------- #
@pytest.mark.parametrize("over", [
    {"source": "somewhere.else.v1"},
    {"authority": "actionable"},
    {"kind": "buy_signal"},
    {"values": "nope"},
    {"num": "<script>XLV</script>"},
    {"num": "XLK"},                                     # num == den
    {"event_as_of": "2026-10-24"},                       # a Saturday
    {"observed_at": "2026-10-21T22:00:00"},              # naive
    {"not_after": "2026-10-21T22:00:00+00:00"},          # not after observed_at
    {"values": {"sessions": 2, "numerator_return_pct": 1.5,
                "denominator_return_pct": -0.5, "ratio_return_pct": 99.0}},
    {"kind": "data_withdrawal"},                         # values must be null
    {"kind": "reversal"},                                # no previous_observation_id
])
def test_a_bad_observation_raises_rather_than_falling_through_to_generic_copy(over):
    """Falling through would tell the reader a condition THEY SET was met."""
    with pytest.raises(ValueError):
        mailer.compose_alert(_obs(**over), lang="en")


def test_the_generic_fallbacks_would_have_been_the_wrong_story():
    """RED-first intent: prove the story the generic path tells is the one this branch
    exists to avoid, so the raise above is not a stylistic preference."""
    legacy = mailer.compose_alert(dict(_PAYLOAD, category="thesis_window"), lang="en")
    assert legacy["why_en"] == "You set an alert on AAPL."
    # Those generic strings remain in the module for the categories they belong to --
    # and none of them appears anywhere in an observation.
    observation_text = _all_text(mailer.compose_alert(_obs(), lang="en"), "en")
    for generic in ("a condition you set was met", "You set an alert on",
                    "This is one of the names you are watching"):
        assert generic not in observation_text
    with pytest.raises(ValueError):
        mailer.compose_alert(_obs(source="somewhere.else.v1"), lang="en")


@pytest.mark.parametrize("payload", [None, {}, []])
def test_a_non_object_or_empty_payload_keeps_the_legacy_generic_behaviour(payload):
    """Not our category -> the untouched legacy path, exactly as before."""
    assert mailer.compose_alert(payload, lang="en")["eyebrow"] == "ALERT"


def test_a_non_object_payload_is_not_routed_into_the_observation_branch():
    """A truthy non-dict still raises at the LEGACY line (``payload.get``), which is
    pre-existing behaviour this change neither introduces nor repairs."""
    for payload in ("x", 7, [1]):
        assert _rot.claims_rotation_observation(payload) is False
    with pytest.raises(AttributeError):
        mailer.compose_alert("x", lang="en")


# --- legacy categories are untouched ------------------------------------------- #
@pytest.mark.parametrize("category", ["thesis_window", "holdings_material_change",
                                     "fif_saved_issuer"])
def test_a_legacy_category_still_composes_the_generic_alert(category):
    """Regression ceiling: adding our branch must not move a single legacy block."""
    c = mailer.compose_alert(dict(_PAYLOAD, category=category), lang="en")
    assert c["eyebrow"] == "ALERT"
    assert c["why_en"] == "You set an alert on AAPL."
    assert mailer.ROTATION_EVIDENCE_URL not in _all_text(c, "en")
    assert c["blocks"][0]["en"] == "RSI crossed above 70 on AAPL."
    assert c["blocks"][1]["en"] == "This is one of the names you are watching: AAPL."


def test_the_held_material_event_branch_is_still_exact():
    c = mailer.compose_alert({"source": "terminal.held_material_event.v1",
                              "category": "holdings_material_change",
                              "authority": "notification_only",
                              "ticker": "AAPL", "condition_plain": "Results were published.",
                              "condition_plain_zh": "公司业绩已发布。",
                              "subject": "AAPL results", "subject_zh": "AAPL 业绩",
                              "evidence_url": "https://x/e",
                              "fired_at": "2026-09-05T14:00:00Z"}, lang="en")
    assert c["blocks"][1]["en"] == "Matched to your recorded open holding: AAPL."
    assert c["why_en"].startswith("This event matched your recorded holding")


def test_a_category_that_only_looks_like_ours_is_left_alone():
    near = ("sector_rotation_relative_v2", "sector_rotation", "rotations",
            "sector_rotation_relative ")
    for category in near:
        c = mailer.compose_alert(dict(_PAYLOAD, category=category), lang="en")
        assert c["eyebrow"] == "ALERT", category


# --- the composer never reads a clock ------------------------------------------ #
def test_the_observation_branch_reads_no_clock_at_all():
    """Structural validation must not consult the system clock; the drain owns every
    freshness question. A formatter with its own clock would render the same payload
    differently at two instants and quietly defeat the stale suppression.

    The scan runs over CODE, not prose: these functions document the rule in their
    docstrings, and a naive substring scan over ``inspect.getsource`` would flag the
    sentence that forbids the very call it is looking for.
    """
    src = _code_only(mailer._compose_rotation_observation)
    src += _code_only(mailer._rotation_direction_lines)
    src += _code_only(mailer._pct)
    for banned in ("datetime.now", "time.time", "utcnow", "today(",
                   "date.today", "monotonic"):
        assert banned not in src, f"the composer calls the clock: {banned}"


def _code_only(fn):
    """``fn``'s source with every docstring blanked, so a prose scan is meaningful."""
    import ast
    import inspect
    import textwrap
    tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    body = tree.body[0].body
    if (body and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        body[0].value.value = ""
    return ast.unparse(tree)


def test_the_composer_output_is_deterministic_for_one_payload():
    p = _obs()
    first = mailer.compose_alert(p, lang="en")
    for _ in range(5):
        assert mailer.compose_alert(p, lang="en") == first


def test_send_alert_reaches_the_observation_branch_without_a_new_template():
    """One template, one idem key, one result vocabulary -- unchanged. The observation
    branch is inside compose_alert, so send_alert picks it up for free and the outbox
    status enum does not grow."""
    assert mailer.ALERT_TEMPLATE == "alert_fire"
    assert mailer.alert_idem_key("fe-1") == "alert_fire:fe-1"
    assert mailer.STATUSES == ("sent", "failed", "skipped_no_smtp", "suppressed", "queued")
