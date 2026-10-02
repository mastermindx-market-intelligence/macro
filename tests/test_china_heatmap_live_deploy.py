from __future__ import annotations

import configparser
import re
import shlex
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "app" / "deploy"
SERVICE = DEPLOY / "macro-live-china-heatmap.service"
SETUP = (DEPLOY / "live-setup.sh").read_text(encoding="utf-8")
UPDATE = (DEPLOY / "update.sh").read_text(encoding="utf-8")
CADDY = (DEPLOY / "Caddyfile").read_text(encoding="utf-8")
POLICY = yaml.safe_load((ROOT / "config" / "site_access.yml").read_text(encoding="utf-8"))
DOC = (ROOT / "docs" / "ops" / "site-access.md").read_text(encoding="utf-8")
PUBLIC_PATH = "/live/china_heatmap.json"


def _unit(path: Path) -> configparser.ConfigParser:
    cp = configparser.ConfigParser(strict=False, interpolation=None)
    cp.optionxform = str
    cp.read_string(path.read_text(encoding="utf-8"))
    return cp


def _matcher(name: str) -> str:
    match = re.search(rf"@{re.escape(name)}\s*\{{(.*?)^\s*\}}", CADDY, flags=re.S | re.M)
    assert match, f"Caddy matcher @{name} missing"
    return match.group(1)


def test_service_is_persistent_capped_and_writes_only_the_live_root() -> None:
    service = _unit(SERVICE)["Service"]
    assert service["Type"] == "simple"
    assert service["WorkingDirectory"] == "/opt/macro"
    assert service["EnvironmentFile"] == "-/etc/macro-live.env"
    assert service["ExecStart"].endswith("-m scripts.build_china_heatmap_live --loop")
    assert service["Restart"] == "always"
    assert float(service["RestartSec"].rstrip("s")) <= 3
    assert int(service["CPUQuota"].rstrip("%")) <= 100
    assert service["MemoryMax"] == "512M"
    assert service["NoNewPrivileges"] == "true"
    assert service["PrivateTmp"] == "true"
    assert service["ProtectSystem"] == "strict"
    assert service["ProtectHome"] == "true"
    assert service["ReadWritePaths"] == "-/var/lib/macro-live/public/live"


def test_live_setup_installs_enables_and_fail_safe_stops_the_service() -> None:
    assert "macro-live-china-heatmap.service" in SETUP
    assert re.search(r"systemctl enable --now[\s\\\n]+(?:.*[\s\\\n]+)*?macro-live-china-heatmap\.service", SETUP)
    assert re.search(r"systemctl stop[\s\\\n]+(?:.*[\s\\\n]+)*?macro-live-china-heatmap\.service", SETUP)
    assert "test -s \"$LIVE_DIR/china_heatmap.json\"" in SETUP


def test_update_restarts_only_the_china_heatmap_service_for_owned_paths() -> None:
    marker = "CHINA HEATMAP LIVE"
    assert marker in UPDATE
    block = UPDATE.split(marker, 1)[1].split("PROPHET LIVE", 1)[0]
    normalized_block = block.replace("\\.", ".")
    for path in (
        "app/deploy/macro-live-china-heatmap.service",
        "scripts/build_china_heatmap_live.py",
        "engine/china_heatmap_live.py",
        "collectors/tushare_client.py",
        "engine/live_quotes.py",
        "templates/heatmap.js",
        "site/heatmap.js",
    ):
        assert path in normalized_block
    assert "systemd-analyze verify" in block
    assert "systemctl restart macro-live-china-heatmap.service" in block
    assert "systemctl enable --now macro-live-china-heatmap.service" in block
    assert "macro-live-fast.service" not in block
    assert "macro-live-snapshot.service" not in block


def test_public_route_is_explicit_no_store_and_policy_registered() -> None:
    public_live = _matcher("vps_public_live")
    assert PUBLIC_PATH in shlex.split(re.search(r"path\s+([^\n]+)", public_live).group(1))
    handle = re.search(r"handle @vps_public_live\s*\{(.*?)^\s*\}", CADDY, flags=re.S | re.M)
    assert handle and 'header Cache-Control "no-store"' in handle.group(1)
    assert PUBLIC_PATH in set(POLICY["public"]["exact"])
    assert PUBLIC_PATH in _matcher("reg_asset")
    assert PUBLIC_PATH in DOC


def test_live_overlay_is_public_market_context_not_a_prefix_widening() -> None:
    public = POLICY["public"]
    assert PUBLIC_PATH in set(public["exact"])
    assert "/live/" not in set(public["prefixes"])
    assert PUBLIC_PATH not in set(POLICY["free_registered"].get("exact") or [])


WORKFLOW = ROOT / ".github" / "workflows" / "deploy-china-heatmap-live.yml"


def test_secret_workflow_is_manual_minimal_and_uses_a_specific_runner_pool() -> None:
    assert WORKFLOW.is_file()
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert re.search(r"permissions:\s*\n\s+contents:\s*read", text)
    assert re.search(r"runs-on:\s*\[self-hosted,\s*macstudio-light\]", text)
    assert "secrets.VPS_DEPLOY_KEY" in text
    assert "secrets.TUSHARE_TOKEN" in text
    assert "pull-requests: write" not in text
    assert "actions/checkout" not in text


def test_secret_workflow_delivers_token_only_over_stdin_and_preserves_env() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "printf '%s\\n' \"$TUSHARE_TOKEN\" | ssh" in text
    assert "IFS= read -r TOKEN" in text
    assert re.search(r"grep -v [\"']\^TUSHARE_TOKEN=[\"'] /etc/macro-live\.env", text)
    assert "TUSHARE_TOKEN=%s" in text
    assert "chmod 600 /etc/macro-live.env.new" in text
    assert "mv /etc/macro-live.env.new /etc/macro-live.env" in text
    assert 'echo "$TUSHARE_TOKEN"' not in text
    assert "set -x" not in text


def test_secret_workflow_restarts_only_owned_service_and_proves_public_path() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    restart_lines = [line.strip() for line in text.splitlines() if "systemctl restart" in line]
    assert restart_lines == ["systemctl restart macro-live-china-heatmap.service"]
    assert "systemctl is-active macro-live-china-heatmap.service" in text
    assert "/var/lib/macro-live/public/live/china_heatmap.json" in text
    assert 'schema") == "china_heatmap_live.v1"' in text
    assert "/opt/macro/site/marketdata/china_heatmap.json" in text
    assert "https://www.mastermind-x.com/live/china_heatmap.json" in text
    assert "cache-control: no-store" in text.lower()
