"""Deployment contract for the dark-by-default VPS ticker-news daemon."""
from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
UNIT = ROOT / "app" / "deploy" / "macro-ticker-news.service"
API_UNIT = ROOT / "app" / "deploy" / "macro-api.service"
SETUP = ROOT / "app" / "deploy" / "api-setup.sh"
UPDATE = ROOT / "app" / "deploy" / "update.sh"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_ticker_news_unit_is_reviewed_dark_single_writer_with_exact_paths():
    text = _text(UNIT)

    assert "Description=Mastermind low-latency ticker news single writer" in text
    assert "WorkingDirectory=/opt/macro" in text
    assert "EnvironmentFile=/etc/macro-ticker-news.env" in text
    assert "StateDirectory=macro-ticker-news" in text
    assert "StateDirectoryMode=0700" in text
    assert (
        "ExecStartPre=/opt/macro-api/.venv/bin/python "
        "scripts/build_qbus_news_universe.py "
        "--output /var/lib/macro-ticker-news/news_universe.json --write"
    ) in text
    assert (
        "ExecStart=/opt/macro-api/.venv/bin/python scripts/run_qbus_news.py --run "
        "--database /var/lib/macro-ticker-news/qbus.sqlite3 "
        "--universe-snapshot /var/lib/macro-ticker-news/news_universe.json "
        "--rights-receipt /etc/macro-ticker-news-rights.json "
        "--health-path /var/lib/macro-ticker-news/health.json"
    ) in text
    assert "Restart=on-failure" in text
    assert "RestartPreventExitStatus=2" in text
    assert "WantedBy=multi-user.target" in text


def test_ticker_news_unit_never_embeds_provider_secret_or_auto_enables_itself():
    text = _text(UNIT)

    assert "BENZINGA_API_KEY=" not in text
    assert "MASSIVE_API_KEY=" not in text
    assert "POLYGON_API_KEY=" not in text
    assert "Environment=BENZINGA" not in text
    assert "systemctl enable" not in text
    assert "systemctl start" not in text


def test_ticker_news_unit_has_network_service_hardening_and_private_state():
    text = _text(UNIT)

    for required in (
        "After=network-online.target",
        "Wants=network-online.target",
        "NoNewPrivileges=true",
        "PrivateTmp=true",
        "PrivateDevices=true",
        "ProtectSystem=full",
        "ProtectHome=true",
        "ProtectKernelTunables=true",
        "ProtectKernelModules=true",
        "ProtectControlGroups=true",
        "RestrictSUIDSGID=true",
        "LockPersonality=true",
        "UMask=0077",
    ):
        assert required in text


def test_macro_api_gets_only_read_paths_not_provider_credential_file():
    text = _text(API_UNIT)

    for line in (
        "Environment=MM_TICKER_NEWS_DB=/var/lib/macro-ticker-news/qbus.sqlite3",
        "Environment=MM_TICKER_NEWS_UNIVERSE=/var/lib/macro-ticker-news/news_universe.json",
        "Environment=MM_TICKER_NEWS_RIGHTS=/etc/macro-ticker-news-rights.json",
        "Environment=MM_TICKER_NEWS_HEALTH=/var/lib/macro-ticker-news/health.json",
        "ReadOnlyPaths=/var/lib/macro-ticker-news",
        "InaccessiblePaths=-/etc/macro-ticker-news.env",
    ):
        assert line in text
    assert "BENZINGA_API_KEY" not in text


def test_initial_api_setup_provisions_state_root_without_installing_or_arming_news():
    text = _text(SETUP)

    assert "install -d -m 0700 /var/lib/macro-ticker-news" in text
    assert 'install -m 0644 "$APP_DIR/app/deploy/macro-ticker-news.service"' not in text
    assert not re.search(
        r"systemctl\s+(?:enable|start|enable --now)\s+macro-ticker-news",
        text,
    )


def test_update_reconciles_only_an_already_installed_news_unit():
    text = _text(UPDATE)

    assert '[ -f /etc/systemd/system/macro-ticker-news.service ]' in text
    assert (
        'systemd-analyze verify "$APP_DIR/app/deploy/macro-ticker-news.service"'
        in text
    )
    assert (
        'install -m 0644 "$APP_DIR/app/deploy/macro-ticker-news.service" '
        '/etc/systemd/system/macro-ticker-news.service'
    ) in text
    assert "systemctl is-active --quiet macro-ticker-news.service" in text
    assert "systemctl restart macro-ticker-news.service" in text
    assert "systemctl enable --now macro-ticker-news.service" not in text
    assert "systemctl enable macro-ticker-news.service" not in text


def test_update_restarts_active_writer_for_all_import_cached_news_dependencies():
    text = _text(UPDATE)

    for token in (
        r"scripts/run_qbus_news\.py",
        r"scripts/build_qbus_news_universe\.py",
        r"collectors/benzinga_news\.py",
        r"engine/qbus_news_.*\.py",
        r"engine/qkernel\.py",
        r"lib/dataos/identity\.py",
        r"data/breadth/(constituents|sp1500_pit_membership)\.parquet",
        r"data/reference/(security_master|vendor_aliases)\.parquet",
    ):
        assert token in text


def test_api_restart_trigger_includes_qbus_news_engine_dependencies():
    text = _text(UPDATE)
    start = text.index("# BEGIN MACRO_API_RESTART_TRIGGER")
    end = text.index("# END MACRO_API_RESTART_TRIGGER")
    block = text[start:end]

    assert r"engine/qbus_news_.*\.py" in block
    assert r"engine/qkernel\.py" in block

def test_api_runtime_pins_sync_websocket_dependency():
    requirements = _text(ROOT / "app" / "requirements.txt")
    assert "websockets>=17.1,<18" in requirements
