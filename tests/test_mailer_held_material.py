"""Pure existing-composer contract; no accounts, SMTP, DB or preference effects."""
from app import mailer

PAYLOAD = {
    "source": "terminal.held_material_event.v1",
    "category": "holdings_material_change",
    "authority": "notification_only",
    "ticker": "AAPL",
    "subject": "AAPL: company results published",
    "subject_zh": "AAPL：公司业绩已发布",
    "condition_plain": "New company results are available. Review the source.",
    "condition_plain_zh": "公司发布了新业绩。请查看来源。",
    "evidence_url": "https://example.invalid/evidence",
    "fired_at": "2026-10-18T10:00:00Z",
}


def test_held_event_uses_supplied_chinese_copy_without_inventing_a_user_condition():
    message = mailer.compose_alert(PAYLOAD, lang="zh")
    assert message["title_zh"] == PAYLOAD["condition_plain_zh"]
    assert "持仓" in message["why_zh"]
    assert "设置" not in message["why_zh"]
    assert message["preheader"] == PAYLOAD["subject_zh"]
    assert any(PAYLOAD["condition_plain_zh"] in block.get("zh", "") for block in message["blocks"])


def test_held_event_english_copy_explains_existing_book_membership():
    message = mailer.compose_alert(PAYLOAD, lang="en")
    assert "hold" in message["why_en"].lower()
    assert "set an alert" not in message["why_en"]
    assert message["title_en"] == PAYLOAD["subject"]
    assert any("hold" in block.get("en", "").lower() for block in message["blocks"])


def test_missing_held_copy_has_an_implicit_event_fallback_in_both_languages():
    message = mailer.compose_alert({k: v for k, v in PAYLOAD.items() if k not in {"condition_plain", "condition_plain_zh", "subject", "subject_zh"}}, lang="zh")
    assert "results" in message["title_en"]
    assert "业绩" in message["title_zh"]
    assert "设置" not in message["title_zh"]


def test_unrecognised_producer_cannot_claim_the_implicit_held_event_copy_path():
    message = mailer.compose_alert(dict(PAYLOAD, source="other.producer"), lang="en")
    assert message["why_en"] == "You set an alert on AAPL."


def test_held_copy_preserves_the_existing_machine_text_filter_and_research_ceiling():
    message = mailer.compose_alert(dict(PAYLOAD, condition_plain_zh="READ_UNAVAILABLE fire_event_id=secret", subject_zh="idem_key=secret"), lang="zh")
    html, text = mailer.render_email(message["title_en"], message["title_zh"], message["blocks"], eyebrow=message["eyebrow"], preheader=message["preheader"], why_en=message["why_en"], why_zh=message["why_zh"], unsubscribe_url="", follow=False)
    for token in ("READ_UNAVAILABLE", "fire_event_id", "idem_key", "secret"):
        assert token not in html
        assert token not in text
    assert "不构成投资建议" in text
