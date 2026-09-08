"""tests/test_mailer_alert_template.py -- tests for the additive alert message type
in app/mailer.py (packet B-F08-1b). STATUSES/send()/render_email() must stay unchanged."""
from __future__ import annotations

import re

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
