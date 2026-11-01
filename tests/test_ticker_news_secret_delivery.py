"""Operator setup contract for the dark ticker-news service."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / "app" / "deploy" / "ticker-news-setup.sh"
RUNBOOK = ROOT / "docs" / "ops" / "ticker-news.md"


def test_setup_script_defaults_to_check_and_serializes_with_macro_update():
    text = SETUP.read_text(encoding="utf-8")

    assert 'ACTION="${1:---check}"' in text
    assert "exec 9>/var/lock/macro-update.lock" in text
    assert "flock 9" in text
    assert "scripts/run_qbus_news.py --check-activation" in text
    assert "scripts/build_qbus_news_universe.py" in text
    assert "/etc/macro-ticker-news.env" in text
    assert "/etc/macro-ticker-news-rights.json" in text
    assert "/var/lib/macro-ticker-news" in text


def test_setup_check_and_install_never_start_or_enable_service():
    text = SETUP.read_text(encoding="utf-8")

    check_block = text[text.index("check_activation() {"):text.index("install_unit() {")]
    install_block = text[text.index("install_unit() {"):text.index("arm_unit() {")]

    assert "systemctl enable" not in check_block
    assert "systemctl start" not in check_block
    assert "systemctl restart" not in check_block

    assert "systemd-analyze verify" in install_block
    assert "install -m 0644" in install_block
    assert "systemctl daemon-reload" in install_block
    assert "systemctl enable" not in install_block
    assert "systemctl start" not in install_block
    assert "systemctl restart" not in install_block


def test_setup_arm_is_the_only_path_that_enables_and_starts_writer():
    text = SETUP.read_text(encoding="utf-8")
    arm_block = text[text.index("arm_unit() {"):text.index("disarm_unit() {")]

    assert "systemctl enable --now macro-ticker-news.service" in arm_block
    assert "systemctl is-active --quiet macro-ticker-news.service" in arm_block
    assert text.count("systemctl enable --now macro-ticker-news.service") == 1


def test_setup_disarm_has_explicit_disable_stop_path():
    text = SETUP.read_text(encoding="utf-8")
    block = text[text.index("disarm_unit() {"):text.index('case "$ACTION" in')]

    assert "systemctl disable --now macro-ticker-news.service" in block
    assert "systemctl is-active --quiet macro-ticker-news.service" in block


def test_setup_never_echoes_secret_values():
    text = SETUP.read_text(encoding="utf-8")

    assert 'echo "$BENZINGA_API_KEY"' not in text
    assert 'printf "%s" "$BENZINGA_API_KEY"' not in text
    assert "set -x" not in text
    assert "cat /etc/macro-ticker-news.env" not in text


def test_setup_requires_root_owned_private_secret_files():
    text = SETUP.read_text(encoding="utf-8")

    assert 'owner=$(stat -c "%u" "$path")' in text
    assert '[ "$owner" = 0 ]' in text
    assert '600|400)' in text
    assert "required regular file missing" in text


def test_setup_check_imports_websocket_runtime_without_connecting():
    text = SETUP.read_text(encoding="utf-8")
    block = text[text.index("check_activation() {"):text.index("install_unit() {")]

    assert 'from websockets.sync.client import connect' in block
    assert "scripts/run_qbus_news.py --check-activation" in block
    assert "scripts/run_qbus_news.py --run" not in block


def test_setup_install_refuses_to_replace_an_active_writer():
    text = SETUP.read_text(encoding="utf-8")
    block = text[text.index("install_unit() {"):text.index("arm_unit() {")]

    assert "systemctl is-active --quiet macro-ticker-news.service" in block
    assert "disarm before installing a reviewed unit" in block


def test_setup_requires_exactly_one_provider_token_line():
    text = SETUP.read_text(encoding="utf-8")
    block = text[text.index("load_provider_token() {"):text.index("check_activation() {")]

    assert 'grep -c -E "^BENZINGA_API_KEY="' in block
    assert "expected exactly one BENZINGA_API_KEY line" in block


def test_setup_status_is_observational_not_activation_check():
    text = SETUP.read_text(encoding="utf-8")
    block = text[text.index("status_unit() {"):text.index('case "$ACTION" in')]

    assert "check_activation" not in block
    assert "scripts/build_qbus_news_universe.py" not in block
    assert "systemctl is-enabled" in block
    assert "systemctl is-active" in block


def test_operator_runbook_preserves_rights_and_activation_boundaries():
    text = RUNBOOK.read_text(encoding="utf-8")

    for token in (
        "internal_ingestion",
        "historical_retention",
        "headline_display",
        "source_link_display",
        "teaser_display",
        "derivative_processing",
        "ticker-news-setup.sh --check",
        "ticker-news-setup.sh --install",
        "ticker-news-setup.sh --arm",
        "ticker-news-setup.sh --disarm",
        "RestartPreventExitStatus=2",
        "at least five",
        "actual trading sessions",
    ):
        assert token in text
    assert "API possession alone" in text
    assert "Organization-level" in text
    assert "secret presence" in text
    assert "remains **unknown**" in text
