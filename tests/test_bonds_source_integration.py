"""R33 production mount and serving boundaries; no live services or old UI replay."""
from pathlib import Path
import fnmatch
import re
import shlex

ROOT = Path(__file__).resolve().parents[1]
R33 = ROOT / "research/bonds_transmission_r30_2026-10-18/r33"
PAYLOAD = "/macro-context-data/decision_workspaces.json"


def test_bonds_uses_the_accepted_strict_adapter_unchanged():
    assert (ROOT / "templates/_bonds_source_adapter.js.j2").read_bytes() == (
        R33 / "source-adapter.js"
    ).read_bytes()


def test_publication_uses_the_existing_default_deny_access_boundary():
    from app.paywall import classify_path

    assert classify_path(PAYLOAD) == "premium"
    caddy = (ROOT / "app/deploy/Caddyfile").read_text()
    boundary = re.search(
        r"# PUBLIC-BOUNDARY-START.*?@reg_asset\s*\{\s*not path ([^\n]+)",
        caddy, flags=re.S,
    )
    assert boundary
    assert not any(fnmatch.fnmatchcase(PAYLOAD, pattern)
                   for pattern in shlex.split(boundary.group(1)))
    handler = caddy.split("handle @reg_asset {", 1)[1].split("@gate_html", 1)[0]
    assert "rewrite /api/regwall/check" in handler
    assert "rewrite /api/paywall/check" in handler
    assert 'header Cache-Control "private, no-store"' in handler
    # This path uses the canonical served tree, not the live-data overlay.
    external = re.search(r"@vps_external\s*\{\s*path ([^\n]+)", caddy)
    assert external
    assert not any(fnmatch.fnmatchcase(PAYLOAD, pattern)
                   for pattern in shlex.split(external.group(1)))
    assert "root * /opt/macro/site.served" in caddy
    update = (ROOT / "app/deploy/update.sh").read_text()
    assert 'flock -n 9 || exit 0' in update
    assert 'rsync -a --delete --min-size=1 --exclude=/ohlc "$APP_DIR/site/" "$APP_DIR/site.served/"' in update


def test_source_mount_is_additive_to_the_existing_bonds_consumer():
    template = (ROOT / "templates/bonds.html.j2").read_text()
    assert template.count('id="bonds-source-open"') == 1
    assert template.count('id="bonds-source-dialog"') == 1
    assert '<dialog' in template
    assert 'aria-labelledby="bonds-source-title"' in template
    assert template.index("_bonds_source_adapter.js.j2") < template.index("_bonds_source_inspector.js.j2")
    assert "_bonds_source_inspector.css.j2" in template
    # No captured publication may become the public page's default payload.
    inspector = (ROOT / "templates/_bonds_source_inspector.js.j2").read_text()
    assert "captured-owner-publication" not in inspector
    assert "owner-publication" not in inspector
    assert PAYLOAD in inspector
    assert "localStorage" not in inspector
    assert "sessionStorage" not in inspector
