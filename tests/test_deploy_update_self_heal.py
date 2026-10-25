"""Regression guards for production deploy reconciliation."""
from __future__ import annotations

import ast
import os
import shlex
import subprocess
import urllib.parse
from collections import deque
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "app" / "deploy" / "update.sh"
SCRIPT = SCRIPT_PATH.read_text(encoding="utf-8")

# BEGIN MOVERS_SEO_REDIRECT_CADDY_GUARD_REGRESSIONS
#
# Executable regressions for the fail-closed Movers guard inside update.sh's
# Caddy reconciliation block. Every case runs the REAL extracted bash: the
# guarded block is lifted verbatim out of app/deploy/update.sh (marker scan +
# if/fi depth walk) and executed under a throwaway APP_DIR with fake
# caddy/install/systemctl shims that only append to an action log. No case
# touches a host path — /etc/caddy/Caddyfile is remapped inside the harness.

MOVERS_GUARD_BEGIN = "# BEGIN MOVERS_SEO_REDIRECT_CADDY_GUARD"
MOVERS_GUARD_END = "# END MOVERS_SEO_REDIRECT_CADDY_GUARD"
MOVERS_MATCHER_NAME = "@movers_seo_redirect"
CADDY_DIFF_LINE = 'if ! cmp -s "$APP_DIR/app/deploy/Caddyfile" /etc/caddy/Caddyfile || [ -n "${CADDY_SOURCE_BASELINE:-}" ] || { { [ -e /var/lib/macro-caddy-publication ] || [ -L /var/lib/macro-caddy-publication ]; } && python3 "$APP_DIR/app/deploy/reconcile-caddy-autosave.py" --pending-check; }; then'
CADDY_VALIDATE_LINE = 'caddy validate --config "$APP_DIR/app/deploy/Caddyfile"'
CADDY_INSTALL_LINE = 'install -m 0644 "$APP_DIR/app/deploy/Caddyfile"'

COHERENT_MOVERS_BODY = (
    "<!doctype html>\n"
    '<html lang="en" data-mmx-movers-redirect="1">\n'
    "<body>Movers, coherent generated body.</body>\n"
    "</html>\n"
)
STALE_MOVERS_BODY = (
    "<!doctype html>\n"
    '<html lang="en">\n'
    "<body>Movers — stale Aug 7 body.</body>\n"
    "</html>\n"
)
INSTALLED_BASELINE_CADDY = (
    "# installed before the Movers cutover\n"
    "example.com {\n"
    "\troot * /opt/macro/site.served\n"
    "\tfile_server\n"
    "}\n"
)
CANDIDATE_CADDY_WITH_MATCHER = (
    "example.com {\n"
    "\t@movers_seo_redirect {\n"
    "\t\tpath /movers\n"
    "\t}\n"
    "\tredir @movers_seo_redirect /movers-updates{uri} 301\n"
    "\troot * /opt/macro/site.served\n"
    "\tfile_server\n"
    "}\n"
)
CANDIDATE_CADDY_WITHOUT_MATCHER = (
    "example.com {\n"
    "\troot * /opt/macro/site.served\n"
    "\tencode gzip\n"
    "\tfile_server\n"
    "}\n"
)
CANDIDATE_CADDY_WITH_LONGER_NAME_DECOY = (
    "example.com {\n"
    "\t@movers_seo_redirect_v2 {\n"
    "\t\tpath /movers-v2\n"
    "\t}\n"
    "\troot * /opt/macro/site.served\n"
    "\tfile_server\n"
    "}\n"
)

HARNESS_TEMPLATE = """\
set -u
APP_DIR=__APP_DIR__
FAKE_ETC_CADDY=__FAKE_ETC_CADDY__
FAKE_LOG=__FAKE_LOG__
caddy() { printf 'caddy %s\\n' "$*" >> "$FAKE_LOG"; }
install() {
	local destination="${@: -1}"
	[ "$destination" = /etc/caddy/Caddyfile ] && destination=$FAKE_ETC_CADDY
	printf 'install %s\\n' "$destination" >> "$FAKE_LOG"
	command cp "$APP_DIR/app/deploy/Caddyfile" "$destination"
}
systemctl() { printf 'systemctl %s\\n' "$*" >> "$FAKE_LOG"; }
cmp() {
	local flag="" left="" right=""
	while [ "$#" -gt 0 ]; do
		case $1 in
			-s) flag=-s ;;
			/etc/caddy/Caddyfile) right=$FAKE_ETC_CADDY ;;
			*) if [ -z "$left" ]; then left=$1; else right=$1; fi ;;
		esac
		shift
	done
	command cmp $flag "$left" "$right"
}
__BLOCK__
printf 'BLOCK_COMPLETED\\n' >> "$FAKE_LOG"
"""


def _script_line_index(needle: str) -> int:
    for index, line in enumerate(SCRIPT.splitlines()):
        if line.strip() == needle:
            return index
    raise AssertionError(f"update.sh is missing the anchored line: {needle!r}")


def _extract_movers_guard_block() -> str:
    start = SCRIPT.index(MOVERS_GUARD_BEGIN)
    end = SCRIPT.index(MOVERS_GUARD_END, start)
    return SCRIPT[start : end + len(MOVERS_GUARD_END)]


def _extract_caddy_reconcile_block() -> str:
    """Lift the whole Caddyfile reconciliation block out of update.sh verbatim."""
    lines = SCRIPT.splitlines()
    depth = 0
    block: list[str] = []
    for line in lines[_script_line_index(CADDY_DIFF_LINE) :]:
        stripped = line.strip()
        block.append(line)
        if stripped.startswith("if ") and stripped.endswith(" then"):
            depth += 1
        elif stripped == "fi":
            depth -= 1
            if depth == 0:
                break
    assert depth == 0, "if/fi scan did not close the Caddy reconciliation block"
    return "\n".join(block) + "\n"


def _run_caddy_block(
    tmp_path: Path,
    block: str,
    *,
    candidate: str,
    installed: str,
    source_body: str | None,
    generated_body: str | None,
    served_body: str | None,
    symlink_page: str | None = None,
    autosave_mode: bool = False,
    fresh_updater: bool = True,
):
    app = tmp_path / "opt" / "macro"
    for relative in ("app/deploy", "templates", "site", "site.served"):
        (app / relative).mkdir(parents=True, exist_ok=True)
    (app / "app" / "deploy" / "Caddyfile").write_text(candidate, encoding="utf-8")
    etc_caddy = tmp_path / "etc" / "caddy" / "Caddyfile"
    etc_caddy.parent.mkdir(parents=True, exist_ok=True)
    etc_caddy.write_text(installed, encoding="utf-8")
    for relative, body in (
        ("templates/movers.html", source_body),
        ("site/movers.html", generated_body),
        ("site.served/movers.html", served_body),
    ):
        if body is not None:
            (app / relative).write_text(body, encoding="utf-8")
    if symlink_page:
        page = app / symlink_page
        retained = tmp_path / "external-body.html"
        retained.write_text(COHERENT_MOVERS_BODY, encoding="utf-8")
        page.unlink()
        page.symlink_to(retained)
    log = tmp_path / "actions.log"
    harness = (
        HARNESS_TEMPLATE.replace("__APP_DIR__", str(app))
        .replace("__FAKE_ETC_CADDY__", str(etc_caddy))
        .replace("__FAKE_LOG__", str(log))
        .replace("__BLOCK__", block.replace("/etc/caddy/Caddyfile", str(etc_caddy)))
    )
    harness_path = tmp_path / "caddy_block_harness.sh"
    if autosave_mode:
        harness = harness.replace(
            'systemctl() { printf \'systemctl %s\\n\' "$*" >> "$FAKE_LOG"; }',
            'systemctl() { printf \'systemctl %s\\n\' "$*" >> "$FAKE_LOG"; '
            'printf "%s\\n" "/usr/bin/caddy reload --config /var/lib/caddy/.config/caddy/autosave.json --force"; }',
        )
        # The shell boundary runs verbatim; only native side effects and its
        # predecessor FD are controlled fixture capabilities.
        harness = 'CADDY_RECONCILE_ARGS=()\n' + harness
        harness = harness.replace(
            'command cmp $flag "$left" "$right"',
            'case "$left" in /proc/*/fd/255) return '
            + ('0' if fresh_updater else '1') + ' ;; esac\n'
            '\tcommand cmp $flag "$left" "$right"',
        )
        harness = harness.replace('caddy() {',
            'python3() { printf \'API_PUBLICATION %s\\n\' "$*" >> "$FAKE_LOG"; }\ncaddy() {', 1)
    harness_path.write_text(harness, encoding="utf-8")
    completed = subprocess.run(
        ["bash", str(harness_path)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    return completed, app, etc_caddy, log


@pytest.mark.parametrize("fresh_updater", [True, False])
def test_autosave_caddy_uses_publication_only_from_fresh_updater(tmp_path, fresh_updater):
    completed, _, etc_caddy, log = _run_caddy_block(
        tmp_path, _extract_caddy_reconcile_block(),
        candidate=CANDIDATE_CADDY_WITH_MATCHER,
        installed=INSTALLED_BASELINE_CADDY,
        source_body=COHERENT_MOVERS_BODY,
        generated_body=COHERENT_MOVERS_BODY,
        served_body=COHERENT_MOVERS_BODY,
        autosave_mode=True, fresh_updater=fresh_updater,
    )
    actions = _action_lines(log)
    assert completed.returncode == (0 if fresh_updater else 1), completed.stderr
    assert sum(line.startswith("API_PUBLICATION ") for line in actions) == int(fresh_updater)
    assert not any(line.startswith(("caddy ", "install ", "systemctl reload", "systemctl restart"))
                   for line in actions)
    assert etc_caddy.read_text() == INSTALLED_BASELINE_CADDY
    if not fresh_updater:
        assert "predecessor updater inode" in completed.stderr


def _action_lines(log: Path) -> list[str]:
    if not log.exists():
        return []
    return [line for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]


def _assert_guard_refused(completed, log) -> None:
    assert completed.returncode != 0, completed.stdout + completed.stderr
    assert "refusing Caddyfile update" in completed.stderr
    # Fail closed BEFORE validate/install/reload: no side effect at all, and the
    # harness never reaches its post-block completion marker.
    assert _action_lines(log) == []


def test_movers_seo_guard_sits_inside_caddy_diff_path_before_validate_install_reload():
    """The guard is additive, uniquely marked and ordered ahead of the install."""
    assert SCRIPT.count(MOVERS_GUARD_BEGIN) == 1
    assert SCRIPT.count(MOVERS_GUARD_END) == 1
    guard = _extract_movers_guard_block()
    block = _extract_caddy_reconcile_block()
    diff_at = block.index(CADDY_DIFF_LINE)
    begin_at = block.index(MOVERS_GUARD_BEGIN)
    end_at = block.index(MOVERS_GUARD_END)
    validate_at = block.index(CADDY_VALIDATE_LINE)
    install_at = block.index(CADDY_INSTALL_LINE)
    assert diff_at < begin_at < end_at < validate_at < install_at
    # The matcher is activated only by the guard: the rest of the Caddy block
    # is byte-for-byte the pre-guard reconciliation shell.
    assert MOVERS_MATCHER_NAME not in block.replace(guard, "")
    # The guard only reads and refuses — no publishing, repair or permission
    # side effect in its executable lines.
    guard_code = "\n".join(
        line
        for line in guard.splitlines()
        if line.strip() and not line.strip().startswith("#")
    )
    for forbidden in (
        "rsync",
        "mkdir ",
        "chmod",
        "chown",
        "mv ",
        "cp ",
        "install ",
        "systemctl",
        "caddy validate",
    ):
        assert forbidden not in guard_code


def test_movers_guard_rollout_preserves_self_update_before_caddy_block():
    """Approved two-stage delivery: self-install ordering is untouched."""
    self_update_at = next(
        index
        for index, line in enumerate(SCRIPT.splitlines())
        if line.startswith("# Self-update:")
    )
    assert self_update_at < _script_line_index(CADDY_DIFF_LINE)
    assert "OPTIONS_DEFER_REARM_FOR_SELF_UPDATE=1" in SCRIPT


def test_movers_caddy_guard_admits_matching_nonempty_triple_and_keeps_ordering(tmp_path):
    completed, app, etc_caddy, log = _run_caddy_block(
        tmp_path,
        _extract_caddy_reconcile_block(),
        candidate=CANDIDATE_CADDY_WITH_MATCHER,
        installed=INSTALLED_BASELINE_CADDY,
        source_body=COHERENT_MOVERS_BODY,
        generated_body=COHERENT_MOVERS_BODY,
        served_body=COHERENT_MOVERS_BODY,
    )
    assert completed.returncode == 0, completed.stderr
    candidate_path = f"{app}/app/deploy/Caddyfile"
    assert _action_lines(log) == [
        "systemctl show caddy -p ExecReload --value",
        f"caddy validate --config {candidate_path} --adapter caddyfile",
        f"install {etc_caddy}",
        "systemctl reload caddy",
        "BLOCK_COMPLETED",
    ]


@pytest.mark.parametrize("relative", ["templates/movers.html", "site/movers.html", "site.served/movers.html"])
def test_movers_caddy_guard_refuses_symlinked_page(tmp_path, relative):
    completed, _, _, log = _run_caddy_block(
        tmp_path, _extract_caddy_reconcile_block(),
        candidate=CANDIDATE_CADDY_WITH_MATCHER, installed=INSTALLED_BASELINE_CADDY,
        source_body=COHERENT_MOVERS_BODY, generated_body=COHERENT_MOVERS_BODY,
        served_body=COHERENT_MOVERS_BODY, symlink_page=relative,
    )
    _assert_guard_refused(completed, log)


def test_movers_caddy_guard_is_inert_without_the_named_matcher(tmp_path):
    """No named matcher: exact pre-guard behavior even with absent/stale trees."""
    for case_index, candidate in enumerate(
        (
            CANDIDATE_CADDY_WITHOUT_MATCHER,
            CANDIDATE_CADDY_WITH_LONGER_NAME_DECOY,
        )
    ):
        completed, app, etc_caddy, log = _run_caddy_block(
            tmp_path / f"case{case_index}",
            _extract_caddy_reconcile_block(),
            candidate=candidate,
            installed=INSTALLED_BASELINE_CADDY,
            source_body=None,
            generated_body=None,
            served_body=None,
        )
        assert completed.returncode == 0, completed.stderr
        candidate_path = f"{app}/app/deploy/Caddyfile"
        assert _action_lines(log) == [
            "systemctl show caddy -p ExecReload --value",
            f"caddy validate --config {candidate_path} --adapter caddyfile",
            f"install {etc_caddy}",
            "systemctl reload caddy",
            "BLOCK_COMPLETED",
        ]
        assert "refusing" not in completed.stderr


@pytest.mark.parametrize(
    ("label", "source_body", "generated_body", "served_body"),
    [
        ("missing_source", None, COHERENT_MOVERS_BODY, COHERENT_MOVERS_BODY),
        ("empty_source", "", COHERENT_MOVERS_BODY, COHERENT_MOVERS_BODY),
        ("missing_generated", COHERENT_MOVERS_BODY, None, COHERENT_MOVERS_BODY),
        ("empty_generated", COHERENT_MOVERS_BODY, "", COHERENT_MOVERS_BODY),
        ("missing_served", COHERENT_MOVERS_BODY, COHERENT_MOVERS_BODY, None),
        ("empty_served", COHERENT_MOVERS_BODY, COHERENT_MOVERS_BODY, ""),
        (
            "stale_served_after_failed_rsync",
            COHERENT_MOVERS_BODY,
            COHERENT_MOVERS_BODY,
            STALE_MOVERS_BODY,
        ),
        (
            "source_generated_mismatch",
            COHERENT_MOVERS_BODY,
            "<html>different</html>\n",
            COHERENT_MOVERS_BODY,
        ),
        (
            "generated_served_mismatch",
            COHERENT_MOVERS_BODY,
            COHERENT_MOVERS_BODY,
            "<html>different</html>\n",
        ),
        ("stale_source_missing_marker", STALE_MOVERS_BODY, STALE_MOVERS_BODY, STALE_MOVERS_BODY),
    ],
)
def test_movers_caddy_guard_fails_closed_before_validate_install_reload(
    tmp_path, label, source_body, generated_body, served_body
):
    completed, _, _, log = _run_caddy_block(
        tmp_path,
        _extract_caddy_reconcile_block(),
        candidate=CANDIDATE_CADDY_WITH_MATCHER,
        installed=INSTALLED_BASELINE_CADDY,
        source_body=source_body,
        generated_body=generated_body,
        served_body=served_body,
    )
    _assert_guard_refused(completed, log)


def test_stale_served_body_from_failed_rsync_still_refuses_caddy_install_on_next_tick(
    tmp_path,
):
    """Tick 1: reset+failed rsync leaves the served body stale. Tick 2: OLD ==
    NEW takes the cheap no-op repo path, but the Caddy diff STILL exists because
    the install was refused — so this block runs again and refuses again."""
    block = _extract_caddy_reconcile_block()
    for tick in range(2):
        completed, _, _, log = _run_caddy_block(
            tmp_path / f"tick{tick}",
            block,
            candidate=CANDIDATE_CADDY_WITH_MATCHER,
            installed=INSTALLED_BASELINE_CADDY,
            source_body=COHERENT_MOVERS_BODY,
            generated_body=COHERENT_MOVERS_BODY,
            served_body=STALE_MOVERS_BODY,
        )
        _assert_guard_refused(completed, log)


def test_negative_control_pre_guard_caddy_block_installs_stale_movers_redirect(tmp_path):
    """Strip only the marked guard: the same state reaches validate+install+
    reload over the stale body — the ordering hazard the guard closes."""
    block = _extract_caddy_reconcile_block()
    guard = _extract_movers_guard_block()
    assert guard in block
    old_block = block.replace(guard, "")
    completed, _, _, log = _run_caddy_block(
        tmp_path,
        old_block,
        candidate=CANDIDATE_CADDY_WITH_MATCHER,
        installed=INSTALLED_BASELINE_CADDY,
        source_body=COHERENT_MOVERS_BODY,
        generated_body=COHERENT_MOVERS_BODY,
        served_body=STALE_MOVERS_BODY,
    )
    assert completed.returncode == 0, completed.stderr
    lines = _action_lines(log)
    assert lines[-1] == "BLOCK_COMPLETED"
    assert any(line.startswith("caddy validate ") for line in lines)
    assert any(line.startswith("install ") for line in lines)
    assert "systemctl reload caddy" in lines


def test_patched_update_script_still_passes_bash_syntax_check(tmp_path):
    """bash -n over the real guarded script: the guard stays syntax-clean."""
    script_copy = tmp_path / "update.sh"
    script_copy.write_text(SCRIPT, encoding="utf-8")
    completed = subprocess.run(
        ["bash", "-n", str(script_copy)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
def _movers_before_mirror_block():
    begin = SCRIPT.index("# BEGIN MOVERS_BEFORE_MIRROR_GUARD")
    end = SCRIPT.index("# END MOVERS_BEFORE_MIRROR_GUARD", begin)
    return SCRIPT[begin:end] + "\nprintf 'MIRROR_ADMITTED\\n' >> \"$FAKE_LOG\"\n"


@pytest.mark.parametrize("candidate_active,installed_active", [(True, True), (True, False), (False, True)])
def test_movers_stale_generated_pair_cannot_mirror_over_trusted_route(tmp_path, candidate_active, installed_active):
    # Includes unchanged installed Caddy: its normal diff block would be skipped.
    candidate = CANDIDATE_CADDY_WITH_MATCHER if candidate_active else CANDIDATE_CADDY_WITHOUT_MATCHER
    installed = candidate if installed_active and candidate_active else (CANDIDATE_CADDY_WITH_MATCHER if installed_active else INSTALLED_BASELINE_CADDY)
    result, app, _, log = _run_caddy_block(
        tmp_path, _movers_before_mirror_block(), candidate=candidate, installed=installed,
        source_body=COHERENT_MOVERS_BODY, generated_body=STALE_MOVERS_BODY,
        served_body=COHERENT_MOVERS_BODY,
    )
    assert result.returncode != 0
    assert "refusing site mirror" in result.stderr
    assert _action_lines(log) == []
    assert (app / "site.served/movers.html").read_text() == COHERENT_MOVERS_BODY


@pytest.mark.parametrize("active", [True, False])
def test_movers_pre_mirror_pair_admission_preserves_good_and_unrelated_updates(tmp_path, active):
    candidate = CANDIDATE_CADDY_WITH_MATCHER if active else CANDIDATE_CADDY_WITHOUT_MATCHER
    body = COHERENT_MOVERS_BODY if active else STALE_MOVERS_BODY
    result, _, _, log = _run_caddy_block(
        tmp_path, _movers_before_mirror_block(), candidate=candidate, installed=candidate,
        source_body=body, generated_body=body, served_body=STALE_MOVERS_BODY,
    )
    assert result.returncode == 0, result.stderr
    assert _action_lines(log) == ["MIRROR_ADMITTED", "BLOCK_COMPLETED"]


def test_movers_pre_mirror_guard_precedes_every_site_rsync():
    start = SCRIPT.index("# BEGIN MOVERS_BEFORE_MIRROR_GUARD")
    end = SCRIPT.index("# END MOVERS_BEFORE_MIRROR_GUARD", start)
    rsync = SCRIPT.index('rsync -a --delete --min-size=1 --exclude=/ohlc "$APP_DIR/site/" "$APP_DIR/site.served/"')
    assert start < end < rsync < SCRIPT.index(CADDY_DIFF_LINE)


# END MOVERS_SEO_REDIRECT_CADDY_GUARD_REGRESSIONS


def test_full_site_builder_guards_help_as_an_additive_public_page() -> None:
    """The deployment lane already owns build_site.py's builder closure."""
    tree = ast.parse((ROOT / "scripts" / "build_site.py").read_text(encoding="utf-8"))

    guarded_calls = [
        call
        for node in ast.walk(tree)
        if isinstance(node, ast.Try)
        for statement in node.body
        for call in ast.walk(statement)
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Name)
        and call.func.id == "build_help_page"
    ]

    assert len(guarded_calls) == 1


def test_deployed_regwall_keeps_help_public() -> None:
    """Execute the regwall's public-path policy without its FastAPI runtime."""
    source = ROOT / "app" / "regwall.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    contract_nodes: list[ast.stmt] = []
    assignment_counts = {"PUBLIC_PATHS": 0, "PUBLIC_PREFIXES": 0}

    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {
                target.id for target in node.targets if isinstance(target, ast.Name)
            }
            for name in assignment_counts.keys() & names:
                assignment_counts[name] += 1
                contract_nodes.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name == "_is_public":
            contract_nodes.append(node)

    assert assignment_counts == {"PUBLIC_PATHS": 1, "PUBLIC_PREFIXES": 1}
    assert sum(
        isinstance(node, ast.FunctionDef) and node.name == "_is_public"
        for node in contract_nodes
    ) == 1

    namespace = {"urllib": urllib}
    exec(compile(ast.Module(contract_nodes, []), source, "exec"), namespace)

    assert "/help.html" in namespace["PUBLIC_PATHS"]
    assert namespace["_is_public"]("/help.html") is True


def test_update_script_has_valid_shell_syntax():
    subprocess.run(["bash", "-n", str(SCRIPT_PATH)], check=True)


def test_codex_runtime_setup_has_valid_shell_syntax():
    runtime_setup = ROOT / "app" / "deploy" / "codex-runtime-setup.sh"
    subprocess.run(["bash", "-n", str(runtime_setup)], check=True)
    text = runtime_setup.read_text(encoding="utf-8")
    assert '@openai/codex@$CODEX_CLI_VERSION' in text
    assert "CODEX_STATE_DIRS" in text
    assert '$state_dir/auth.json' in text
    assert (
        "/var/lib/macro-codex:/var/lib/macro-codex-2:"
        "/var/lib/macro-codex-3"
    ) in text


def test_live_setup_installs_press_scoring_backend():
    live_setup = ROOT / "app" / "deploy" / "live-setup.sh"
    subprocess.run(["bash", "-n", str(live_setup)], check=True)
    assert "datasketch" in live_setup.read_text(encoding="utf-8")


def test_deployed_services_share_root_only_codex_state():
    for relative in (
        "app/deploy/macro-api.service",
        "admin/deploy/admin.service",
    ):
        unit = (ROOT / relative).read_text(encoding="utf-8")
        assert "Environment=CODEX_HOME=/var/lib/macro-codex" in unit
        assert (
            "Environment=CODEX_ACCOUNT_HOMES="
            "/var/lib/macro-codex:/var/lib/macro-codex-2:"
            "/var/lib/macro-codex-3"
        ) in unit
        assert "Environment=CODEX_PROVIDER_ENABLED=1" in unit
        assert "StateDirectory=macro-codex macro-codex-2 macro-codex-3" in unit
        assert "StateDirectoryMode=0700" in unit


def test_update_reconciles_codex_runtime_and_admin_unit():
    assert 'bash "$APP_DIR/app/deploy/codex-runtime-setup.sh" --quiet' in SCRIPT
    assert 'cmp -s "$APP_DIR/admin/deploy/admin.service"' in SCRIPT
    assert "ADMIN_UNIT_UPDATED=1" in SCRIPT


def test_admin_import_closure_generation_forces_same_cycle_restart():
    unit = (ROOT / "admin" / "deploy" / "admin.service").read_text(
        encoding="utf-8"
    )
    assert (
        "Environment=MMX_ADMIN_IMPORT_CLOSURE_GENERATION="
        "2026-10-11-billing-catalog-v1"
    ) in unit

    reconcile = SCRIPT.index('cmp -s "$APP_DIR/admin/deploy/admin.service"')
    updated = SCRIPT.index("ADMIN_UNIT_UPDATED=1", reconcile)
    restart_guard = SCRIPT.index('if [ "$ADMIN_UNIT_UPDATED" -eq 1 ]', updated)
    restart = SCRIPT.index("systemctl restart admin", restart_guard)
    assert reconcile < updated < restart_guard < restart


def test_update_reconciles_api_requirements_with_retryable_content_stamp():
    assert 'sha256sum "$APP_DIR/app/requirements.txt"' in SCRIPT
    assert '/opt/macro-api/.venv/bin/pip install -q -r "$APP_DIR/app/requirements.txt"' in SCRIPT
    assert "API_REQ_STAMP=/opt/macro-api/.requirements.sha256" in SCRIPT
    assert 'if [ "$API_DEPS_OK" -ne 1 ]; then' in SCRIPT


def test_repository_noop_does_not_skip_reconciliation():
    assert '[ "$OLD" = "$NEW" ] && exit 0' not in SCRIPT
    assert 'if [ "$OLD" != "$NEW" ]; then' in SCRIPT
    assert SCRIPT.index("# Self-update:") < SCRIPT.index("API_UNIT_UPDATED=0")


def test_caddy_source_is_validated_before_install():
    validate = 'caddy validate --config "$APP_DIR/app/deploy/Caddyfile"'
    install = 'install -m 0644 "$APP_DIR/app/deploy/Caddyfile" /etc/caddy/Caddyfile'
    assert validate in SCRIPT
    assert SCRIPT.index(validate) < SCRIPT.index(install)


def test_changed_systemd_unit_forces_api_restart():
    assert "API_UNIT_UPDATED=1" in SCRIPT
    trigger = SCRIPT.split("# BEGIN MACRO_API_RESTART_TRIGGER\n", 1)[1].split(
        "# END MACRO_API_RESTART_TRIGGER", 1
    )[0]
    assert 'if [ "$API_UNIT_UPDATED" -eq 1 ] ||' in trigger
    assert "! mm_api_fence_marker_ready" in trigger
    assert "grep -qE" in trigger
    assert '<<<"$CHANGED"' in trigger


def test_api_restart_transaction_precedes_w2c_runtime_attestation():
    restart = SCRIPT.index("# BEGIN MACRO_API_RESTART_TRANSACTION")
    trigger = SCRIPT.index("# BEGIN MACRO_API_RESTART_TRIGGER")
    fence = SCRIPT.index("mm_write_api_fence_marker")
    w2c = SCRIPT.index("# BEGIN W2C_RUNTIME_ATTESTATION")
    fence_ready = SCRIPT.index("OPTIONS_API_FENCE_READY=0")
    assert restart < trigger < fence < w2c < fence_ready
    transaction = SCRIPT.split("# BEGIN MACRO_API_RESTART_TRANSACTION\n", 1)[1].split(
        "# END MACRO_API_RESTART_TRANSACTION", 1
    )[0]
    assert 'if [ "$API_UNIT_READY" -ne 1 ]; then' in transaction
    assert 'elif [ "$API_DEPS_OK" -ne 1 ]; then' in transaction
    assert "API_RESTART_CONFIRMED=1" in transaction
    assert "mm_write_api_fence_marker" in transaction
    assert "w2c_start_owner_chain" not in transaction


@pytest.mark.parametrize(
    ("unit_differs", "changed", "unit_valid", "expected_restart"),
    [
        (True, "", True, True),
        (False, "config/plans.yml", True, True),
        (False, "app/billing.py", True, True),
        (False, "site/news.html", True, False),
        (True, "", False, False),
    ],
)
def test_admin_adopts_before_unrelated_w2c_failure(
    tmp_path: Path, unit_differs, changed, unit_valid, expected_restart
):
    """Run the actual admin transaction and W2C exit in their source order.

    The old updater exits before installing the admin unit, even on a later
    empty-CHANGED tick. Keep that W2C refusal while allowing admin to adopt.
    Only systemd is simulated; comparison and unit installation use real files.
    """
    app = tmp_path / "app"
    source = app / "admin/deploy/admin.service"
    source.parent.mkdir(parents=True)
    source.write_text("reviewed admin generation\n")
    installed = tmp_path / "installed-admin.service"
    installed.write_text("old generation\n" if unit_differs else source.read_text())
    events = tmp_path / "events"
    start = SCRIPT.index("ADMIN_UNIT_UPDATED=0")
    restart = SCRIPT.index("\tsystemctl is-enabled admin ", start)
    end = SCRIPT.index("\nfi", restart) + len("\nfi")
    admin = SCRIPT[start:end].replace(
        "/etc/systemd/system/admin.service", shlex.quote(str(installed))
    )
    failure_start = SCRIPT.index('if [ "${MARKET_MEMORY_EXPERIENCE_ATTESTED:-1}" -ne 1 ]; then')
    failure_end = SCRIPT.index("# END W1B5_TIMER_FINALIZATION", failure_start)
    refusal = SCRIPT[failure_start:failure_end]
    freeze_start = SCRIPT.index("# BEGIN W2C_LANE_FREEZE\n")
    freeze = SCRIPT[freeze_start : SCRIPT.index("# END W2C_LANE_FREEZE", freeze_start)]
    exit_start = SCRIPT.index("# BEGIN DEPLOY_EXIT_STATUS\n")
    exit_status = SCRIPT[exit_start : SCRIPT.index("# END DEPLOY_EXIT_STATUS", exit_start)]
    ordered = "\n".join(
        block
        for _, block in sorted(
            [
                (start, admin),
                (freeze_start, freeze),
                (failure_start, refusal),
                (exit_start, exit_status),
            ]
        )
    )
    harness = f"""
set -eu
APP_DIR={shlex.quote(str(app))}
RECONCILED=0
MARKET_MEMORY_EXPERIENCE_ATTESTED=0
OPTIONS_RECONCILIATION_COMPLETE=0
trap 'echo "exit-options-complete=$OPTIONS_RECONCILIATION_COMPLETE" >> "$EVENTS"' EXIT
systemctl() {{ echo "$*" >> "$EVENTS"; }}
systemd-analyze() {{ [ "$UNIT_VALID" = 1 ]; }}
{ordered}
"""
    result = subprocess.run(
        ["bash", "-c", harness], text=True, capture_output=True,
        env={**os.environ, "EVENTS": str(events), "CHANGED": changed,
             "UNIT_VALID": "1" if unit_valid else "0"},
    )
    assert result.returncode == 1
    assert "W2C installation and terminal state were not authenticated" in result.stderr
    observed = events.read_text().splitlines()
    assert observed[-1] == "exit-options-complete=0"
    assert ("restart admin" in observed) is expected_restart
    assert not any("market-memory" in event or "timer" in event for event in observed)
    assert installed.read_text() == (
        source.read_text() if unit_valid or not unit_differs else "old generation\n"
    )
    if unit_differs and unit_valid:
        assert observed.index("daemon-reload") < observed.index("restart admin")


# --------------------------------------------------------------------------
# macro-api restart trigger: a module import-cached by uvicorn but missing from
# the trigger regex deploys to the VPS and never goes live (sys.modules pins the
# old object).  These guards pin the regex's behaviour, not its spelling.
# --------------------------------------------------------------------------

_GREP = "grep -qE "


def _ere_on_line(line: str) -> str:
    """Pull the single-quoted ERE out of a `grep -qE '...'` shell line."""
    body = line.split(_GREP, 1)[1]
    assert body.startswith("'"), body
    return body[1: body.index("'", 1)]


def _api_restart_regex() -> str:
    """The ERE from the macro-api restart line in update.sh."""
    trigger = SCRIPT.split("# BEGIN MACRO_API_RESTART_TRIGGER\n", 1)[1].split(
        "# END MACRO_API_RESTART_TRIGGER", 1
    )[0]
    return _ere_on_line(
        next(
            line
            for line in trigger.splitlines()
            if _GREP in line and line.lstrip().startswith("if ")
        )
    )


def _admin_restart_regex() -> str:
    """The ERE guarding `systemctl restart admin`.

    Anchored on the restart it guards rather than on the regex's own spelling, so
    reordering the alternation can never silently point this at another line.
    """
    lines = SCRIPT.splitlines()
    restart = next(i for i, ln in enumerate(lines)
                   if "systemctl is-enabled admin " in ln)
    guard = next(i for i in range(restart - 1, -1, -1) if _GREP in lines[i])
    return _ere_on_line(lines[guard])


def _press_restart_regex() -> str:
    """The ERE guarding the long-running PRESS-FEEDS daemon restart."""
    lines = SCRIPT.splitlines()
    restart = next(i for i, ln in enumerate(lines)
                   if "systemctl restart marketing-press-feeds" in ln)
    guard = next(i for i in range(restart - 1, -1, -1) if _GREP in lines[i])
    return _ere_on_line(lines[guard])


def _matches(regex: str, path: str) -> bool:
    """Run the real grep so the test sees POSIX ERE semantics, not Python's."""
    return subprocess.run(
        ["grep", "-qE", regex], input=path, text=True, check=False,
    ).returncode == 0


def _triggers_restart(path: str) -> bool:
    """Exercise the complete production trigger, including separate conditions."""
    trigger = SCRIPT.split("# BEGIN MACRO_API_RESTART_TRIGGER\n", 1)[1].split(
        "# END MACRO_API_RESTART_TRIGGER", 1
    )[0]
    probe = (
        "set -eu\n"
        "API_RESTART_NEEDED=0\nAPI_UNIT_UPDATED=0\nAPI_DEPS_UPDATED=0\n"
        "CHANGED=$1\nmm_api_fence_marker_ready() { return 0; }\n"
        + trigger
        + '\nprintf "%s" "$API_RESTART_NEEDED"\n'
    )
    result = subprocess.run(
        ["bash", "-c", probe, "restart-contract", path],
        text=True, capture_output=True, check=True,
    )
    assert result.stdout in {"0", "1"}, result.stdout
    return result.stdout == "1"


def _triggers_admin_restart(path: str) -> bool:
    return _matches(_admin_restart_regex(), path)


def _triggers_press_restart(path: str) -> bool:
    return _matches(_press_restart_regex(), path)


# Import-cached by the macro-api process -> a change here MUST restart it.
MUST_RESTART = [
    # Private dated-reference Plan: load-time identity/terms plus request-time math.
    "app/options_plan.py",
    "app/options_plan_source.py",
    "engine/options_nbbo_cohort.py",
    "lib/options_source_receipts.py",
    "engine/options_plan_expiry.py",
    "engine/options_payoff.py",
    "engine/greeks.py",
    "engine/intraday_greeks.py",
    # Native supplier conditional research imports and cached K3 validators.
    'app/company_supplier_research.py',
    'engine/company_intelligence/h20_reported_event.py',
    'engine/earnings_release/__init__.py',
    'engine/earnings_release/receipts.py',
    'engine/theme_graph/native_disclosure_propagation.py',
    'lib/economic_propagation.py',
    'lib/economic_propagation_v2.py',
    'contracts/economic_propagation/propagation_hypothesis.v1.schema.json',
    'contracts/economic_propagation/propagation_hypothesis.v2.schema.json',
    'contracts/economic_propagation/generator_registry.v1.json',
    # F04 captured/native research and published Radar validation: request-time
    # imports also stay cached. The three JSON resources have lru-cached readers.
    'engine/entry_radar/c5_adapter.py',
    'engine/entry_radar/challengers.py',
    'engine/entry_radar/detectors.py',
    'engine/entry_radar/earnings_context.py',
    'engine/entry_radar/entry_events.py',
    'engine/entry_radar/four_hour.py',
    'engine/entry_radar/g0_adapter.py',
    'engine/entry_radar/indicator_core.py',
    'engine/entry_radar/indicator_ingest.py',
    'engine/entry_radar/live_ledger.py',
    'engine/entry_radar/live_pack.py',
    'engine/entry_radar/quote_context.py',
    'engine/entry_radar/readings.py',
    'engine/entry_radar/replay/identity_observation_snapshot.py',
    'engine/entry_radar/research_read.py',
    'lib/quote_native_metadata.py',
    'engine/price_pressure/__init__.py',
    'engine/price_pressure/research.py',
    'lib/evidence_foundation.py',
    'lib/opportunity_case.py',
    'lib/opportunity_evidence.py',
    'contracts/opportunity_evidence/vector.v1.schema.json',
    'contracts/opportunity_evidence/slot_registry.v1.json',
    'contracts/evidence_foundation/reference.v1.schema.json',

    # Today contract validator caches the source schema across requests.
    "contracts/market_os/macro_workspace_snapshot.v1.schema.json",
    # app/ routers (all import-cached by uvicorn)
    "app/main.py",
    "app/research.py",
    "app/regwall.py",
    "app/paywall.py",
    "app/tape.py",
    "app/biocatalyst.py",
    "app/requirements.txt",
    "app/deploy/macro-api.service",
    "config/site_access.yml",
    # app.billing holds the issuer's plan/features catalog for the process life.
    "config/plans.yml",
    "engine/neuralweb/market_memory_playback.py",
    "engine/neuralweb/market_memory_retained_catalog.py",
    "engine/neuralweb/market_memory_retained_saved.py",
    "engine/neuralweb/market_memory_retained_legacy_guard.py",
    # Private Issue Desk router import-caches both its engine and strict schemas.
    "engine/options_issue_desk.py",
    "contracts/options/options.issue_desk.v1.schema.json",
    "contracts/options/options.issue_desk_proposal.v1.schema.json",
    "contracts/options/options.issue_desk_decision.v1.schema.json",
    "contracts/options/options.issue_receipt.v1.schema.json",
    "lib/nyse_calendar.py",
    "lib/us_cash_calendar.py",  # Request-time US settle-window import in live_quotes.
    # research vault serving layer — imported at MODULE level by app/research.py.
    # These were the 2026-07-26 gap: download caps / anti-scrape limits / watermark
    # policy deployed to the VPS and stayed dead until an unrelated app/ change.
    "engine/research_vault/download_quota.py",
    "engine/research_vault/view_ratelimit.py",
    "engine/research_vault/watermark.py",
    "engine/research_vault/catalog.py",
    "engine/research_vault/corpus.py",
    "engine/research_vault/r2_store.py",
    "engine/research_vault/sidecar.py",
    # BioCatalyst serving validates and projects the immutable public generation.
    "engine/biocatalyst/publication.py",
    "engine/biocatalyst/trials.py",
    "engine/sector_intelligence/__init__.py",
    "engine/sector_intelligence/contracts.py",

    # Capital Structure serving closure — imported by app/capital_structure.py.
    "engine/capital_structure/__init__.py",
    "engine/capital_structure/event_spine.py",
    "engine/capital_structure/projection.py",
    # Government Revenue serving modules are imported by app/government_revenue.py.
    "engine/government_revenue/budget_program.py",
    "engine/government_revenue/candidates.py",
    "engine/government_revenue/idv_dossiers.py",
    "engine/government_revenue/subaward_dossiers.py",
    "engine/government_revenue/sbir_progression.py",
    "engine/government_revenue/defense_economics.py",
    "engine/government_revenue/defense_interpretation.py",
    "engine/government_revenue/research_state.py",
    "engine/government_revenue/candidate_grader.py",
    "engine/government_revenue/program_theme_publication.py",
    "engine/government_revenue/program_theme_context.py",
    "engine/government_revenue/program_theme_disclosure.py",
    "engine/government_revenue/program_ontology.py",
    "engine/government_revenue/budget_allocation_context.py",
    "engine/government_revenue/identity_atlas.py",
    "contracts/government_revenue/government_revenue_identity_atlas.v1.schema.json",
    "contracts/government_revenue/government_revenue_candidate.v1.schema.json",
    "contracts/government_revenue/government_revenue_candidate_historical_suppressions.v1.schema.json",
    "contracts/government_revenue/government_revenue_candidate_issuance_corrections.v1.schema.json",
    "contracts/government_revenue/government_revenue_candidate_queue.v1.schema.json",
    # ...and the schemas their validators pin with lru_cache(maxsize=1): read
    # once, held for the life of the process, so a merged schema-only change
    # never goes live until macro-api restarts (the Wave 8 merged-but-dead shape).
    "contracts/government_revenue/government_revenue_dossiers.v1.schema.json",
    "contracts/government_revenue/government_idv_dossiers.v1.schema.json",
    "contracts/government_revenue/government_subaward_dossiers.v1.schema.json",
    "contracts/government_revenue/government_procurement_event.v2.schema.json",
    "contracts/government_revenue/government_procurement_workspace.v2.schema.json",
    "contracts/government_revenue/government_entity_coverage.v1.schema.json",
    "contracts/government_revenue/government_recipient_resolution_coverage.v1.schema.json",
    # The public Company Intelligence API imports the reader plus this
    # non-inert package at process startup (contracts, health, and views).
    "engine/neuralweb/company_intelligence_reader.py",
    "engine/company_intelligence/__init__.py",
    "engine/company_intelligence/contracts.py",
    "engine/company_intelligence/health.py",
    "engine/company_intelligence/views.py",
    # /api/ask + /api/brain engine closure
    "engine/neuralweb/ask_brain.py",
    "engine/neuralweb/chat_plain_words.py",
    "engine/neuralweb/brain_gateway.py",
    "engine/risk_envelope.py",
    "engine/neuralweb/brain_native_inputs.py",
    "engine/neuralweb/native_facts.py",
    # T11's native request lazily imports and then caches its numeric checker.
    "engine/neuralweb/response_eval.py",
    # W1-B imports this typed-fact package on the first native request.  From
    # then on its modules and lru-cached registry/schema validators are pinned.
    "engine/intelligence_workspace/runtime.py",
    "engine/intelligence_workspace/resolver.py",
    "engine/intelligence_workspace/registry.py",
    "engine/intelligence_workspace/adapters/quote.py",
    "config/intelligence_workspace/datapoints.v1.json",
    "contracts/intelligence_workspace/datapoint_registry.schema.json",
    "contracts/intelligence_workspace/datapoint_value.schema.json",
    # W1-C: the visible-context compiler + its schema (contract:
    # research/DEEPVUE_W1C_CONTEXT_ENVELOPE_CONTRACT_2026-08-25.md). The compiler
    # is a pure module but lives in the W1-A package, so it is pulled in on the
    # same first-request path; the schema is read (not lru-cached) but is still
    # named here for symmetry with the sibling datapoint schemas above.
    "engine/intelligence_workspace/context_compiler.py",
    "contracts/intelligence_workspace/ai_context_envelope.v1.schema.json",
    # W1-B request-time transitive closure. These modules/configs are imported
    # or lru-cached by the frozen runtime after the first native request.
    "lib/dataos/__init__.py",
    "lib/dataos/identity.py",
    "lib/dataos/registry.py",
    "config/dataset_registry.yml",
    "engine/theme_graph/store.py",
    "engine/theme_graph/rights.py",
    "config/theme_sources.yml",
    "collectors/equity_earnings.py",
    "engine/earnings_catalyst.py",
    "config.yml",
    "engine/neuralweb/cortex.py",
    "engine/neuralweb/earnings_context_reader.py",
    "engine/neuralweb/chart_perception.py",
    "engine/neuralweb/doctrine.py",
    "engine/neuralweb/envelope.py",
    "engine/neuralweb/synapse.py",
    "engine/neuralweb/key_pool.py",
    "engine/codex_lane/runner.py",
    "engine/llm_auth.py",
    "engine/portfolio_brief.py",
    "engine/tushare_freshness.py",
    # Exact earnings evidence validator closure, lazily reached by Brain.
    "engine/earnings_narrative/__init__.py",
    "engine/earnings_narrative/context_packets.py",
    "engine/earnings_narrative/contracts.py",
    "engine/earnings_narrative/digest.py",
    "engine/earnings_narrative/private_publication.py",
    "engine/earnings_narrative/promotion.py",
    "engine/earnings_narrative/public_wire.py",
    "engine/earnings_narrative/story.py",
    "engine/earnings_narrative/story_packets.py",
    "engine/press/__init__.py",
    "engine/press/earnings_adapter.py",
    # CXI packet build reached from brain_gateway (+ its module-level siblings)
    "engine/context_index/packet.py",
    "engine/context_index/fusion.py",
    "engine/context_index/gitinfo.py",
    "engine/context_index/lexical.py",
    "engine/context_index/structured.py",
    # brain_gateway chart path
    "engine/marketing/chart_render.py",
    "engine/marketing/confluence_source.py",
    # ...plus the substrate the PACKAGE __init__ drags in: importing any
    # engine.marketing submodule runs __init__ -> state -> these ten.  Invisible
    # to an import-line scan; confirmed against a live interpreter's sys.modules.
    "engine/marketing/__init__.py",
    "engine/marketing/state.py",
    "engine/marketing/authority.py",
    "engine/marketing/charter.py",
    "engine/marketing/claims.py",
    "engine/marketing/cmo.py",
    "engine/marketing/departments.py",
    "engine/marketing/economics.py",
    "engine/marketing/events.py",
    "engine/marketing/ledgers.py",
    "engine/marketing/opportunity_bus.py",
    "engine/marketing/publication.py",
    # app/tape.py REST quotes, and lib modules on the chat path
    "engine/live_quotes.py",
    "lib/config.py",
    "lib/ai_costs.py",
    "lib/mastermind_response_log.py",
]

# NOT import-cached by macro-api -> restarting would blip /api for nothing.
MUST_NOT_RESTART = [
    # Research readers do not import nightly/writer siblings; exact lookalikes
    # and uncached vocabulary changes must not widen the serving-plane trigger.
    'engine/price_pressure/pipeline.py',
    'engine/price_pressure/artifact.py',
    'engine/entry_radar/live_eval.py',
    'engine/entry_radar/earnings_contexts.py',
    'engine/entry_radar/replay/identity_observation_snapshot.py.bak',
    'scripts/entry_radar_live.py',
    'contracts/opportunity_evidence/vector.v1.schema.json.bak',
    'contracts/opportunity_evidence/slot_registry.v1.json.bak',
    'contracts/evidence_foundation/vocabulary.v1.json',

    "site/macrodata/workspaces/manifest.json",
    # doctrine prose hot-reloads on mtime; only doctrine.py is cached
    "engine/neuralweb/doctrine/00_identity.md",
    # rendered site + data artifacts are read from disk per request
    "site/index.html",
    "site/feeds/risk_radar.json",
    "data/qbus/items.parquet",
    "research/DO_NOT_REBUILD.md",
    "docs/DESIGN_DOCTRINE.md",
    # nightly-only closure behind cortex.run() — never in the API's sys.modules
    "engine/master_brain.py",
    "engine/ai_desk.py",
    "engine/qledger.py",
    "engine/china_radar.py",
    "engine/neuralweb/constitution.py",
    # nightly-only builders inside packages whose serving modules ARE listed
    "engine/context_index/ingest.py",
    "engine/context_index/chunking.py",
    "engine/context_index/health.py",
    # schemas read WITHOUT lru_cache re-read the file per call and self-heal
    # without a restart; the v1 procurement generation is nightly-only
    "contracts/government_revenue/government_budget_program_graph.v1.schema.json",
    "contracts/government_revenue/government_program_theme_context.v1.schema.json",
    "contracts/government_revenue/government_program_theme_public_disclosure.v1.schema.json",
    "contracts/government_revenue/government_program_ontology.v1.schema.json",
    "contracts/government_revenue/government_budget_program_graph.v1_1.schema.json",
    "contracts/government_revenue/government_program_ontology.v1_1.schema.json",
    "contracts/government_revenue/defense_economics.v1.schema.json",
    "contracts/government_revenue/government_procurement_event.v1.schema.json",
    # API candidate cache includes this exact path's mtime/size and re-hashes
    # the manifest on every cache miss; config review does not need a restart.
    "config/government_revenue/candidate_historical_suppressions.v1.json",
    "config/government_revenue/candidate_issuance_corrections.v1.json",
    # nightly-only marketing modules — the package is named, not globbed
    "engine/marketing/seo_director.py",
    "engine/marketing/social_publisher.py",
    # outbox/rejections back the ADMIN outbox endpoints and sit on no API path
    "engine/marketing/outbox.py",
    "engine/marketing/rejections.py",
    # other lanes
    "scripts/build_site.py",
    "scripts/marketing_publisher.py",
    "engine/spine.py",
    "admin/server.py",
    "templates/index.html.j2",
    # Hostile lookalikes must not widen the exact W1-A restart closure.
    "config/intelligence_workspace/datapoints.v1.json.bak",
    "contracts/intelligence_workspace/datapoint_value.schema.json.bak",
    "contracts/intelligence_workspace/ai_context_envelope.v1.schema.json.bak",
    "engine/intelligence_workspaces/resolver.py",
    "lib/dataoses/registry.py",
    "config/dataset_registry.yml.bak",
    "config/theme_sources.yml.bak",
    "engine/theme_graph/stores.py",
    "engine/theme_graph/materialize.py",
    "collectors/equity_earnings.py.bak",
    "engine/earnings_catalysts.py",
    "engine/neuralweb/response_eval.py.bak",
    "engine/neuralweb/response_evaluation.py",
    "scripts/run_brain_eval.py",
]


@pytest.mark.parametrize("path", MUST_RESTART)
def test_import_cached_module_triggers_api_restart(path):
    assert (ROOT / path).exists(), f"stale test fixture: {path} no longer exists"
    assert _triggers_restart(path), (
        f"{path} is import-cached by macro-api but does not match the restart "
        "regex in app/deploy/update.sh — a change would deploy and never go live"
    )


@pytest.mark.parametrize("path", MUST_NOT_RESTART)
def test_non_api_path_does_not_trigger_api_restart(path):
    assert not _triggers_restart(path), (
        f"{path} is not import-cached by macro-api; restarting on it blips /api "
        "for nothing and defeats the narrow-restart intent"
    )


# --------------------------------------------------------------------------
# admin console restart trigger.  Same trap, separate (narrower) regex: the
# panel is a long-running process, so sys.modules pins whatever a request-time
# import loaded and an engine-side fix stays dead until something restarts it.
# --------------------------------------------------------------------------

# Import-cached by the admin process -> a change here MUST restart it.
ADMIN_MUST_RESTART = [
    # panel code (all import-cached by the running process)
    "admin/server.py",
    "templates/theme.css",  # derived token response is process-pinned
    "engine/qledger_store.py",  # A1 selected request scope is import-cached
    "admin/marketing.py",
    "admin/metabolism_panel.py",
    "admin/neural_web.py",
    "admin/orchestrator_chat.py",
    "admin/ai_cost.py",
    "admin/mastermind_logs.py",
    "admin/prophet.py",
    "admin/trade_memory.py",
    # The authenticated entitlement panel lazily imports the existing billing
    # writer, including its process-cached catalog; an API restart is separate.
    "app/billing.py",
    "config/plans.yml",
    # outbox approve / reject / decide endpoints (admin/marketing.py).  This was
    # the 2026-07-26 gap: an outbox.py fix deployed to the VPS and the running
    # panel kept serving the previous module, with no signal.
    "engine/marketing/outbox.py",
    "engine/marketing/rejections.py",
    # ...and the substrate `from engine.marketing import outbox` executes on the
    # way in (package __init__ -> state -> these ten)
    "engine/marketing/__init__.py",
    "engine/marketing/state.py",
    "engine/marketing/authority.py",
    "engine/marketing/charter.py",
    "engine/marketing/claims.py",
    "engine/marketing/cmo.py",
    "engine/marketing/departments.py",
    "engine/marketing/economics.py",
    "engine/marketing/events.py",
    "engine/marketing/ledgers.py",
    "engine/marketing/opportunity_bus.py",
    "engine/marketing/publication.py",
    # publish dry-run report (admin/marketing.py)
    "scripts/marketing_publisher.py",
    # ...and one module further, since 2026-08-08: the publisher imports
    # social_publisher's subscription-lock predicates at MODULE scope, on the
    # same "must fail loudly" reasoning as copywriter — a lazily-imported lock
    # predicate that failed to import would read as "no lock" and silently
    # restore the requeue loop it exists to stop. Moved here from
    # ADMIN_MUST_NOT_RESTART, where it sat as a nightly-only module.
    "engine/marketing/social_publisher.py",
    # deliberation-spend panel (admin/prophet.py)
    "engine/codex_provider.py",
    "engine/codex_lane/runner.py",
    "engine/llm_auth.py",
    # private episode validator imported by admin/trade_memory.py
    "engine/neuralweb/trade_memory.py",
    # reached via importlib.import_module("...") string literals — a grep for
    # `from engine`/`from lib` does not see these at all
    "engine/neuralweb/support_map.py",
    "engine/neuralweb/orchestrator_log.py",
    "engine/neuralweb/ask_brain.py",
    "lib/ai_costs.py",
    # static request-time imports
    "engine/neuralweb/key_pool.py",
    "engine/metabolism/throttle.py",
    "engine/metabolism/budget_gate.py",
    "lib/mastermind_response_log.py",
    "lib/project_runtime_state.py",
]

# NOT import-cached by admin -> restarting would blip the panel for nothing.
ADMIN_MUST_NOT_RESTART = [
    # rendered site + data artifacts are read from disk per request
    "site/index.html",
    "data/qbus/items.parquet",
    "engine/neuralweb/doctrine/00_identity.md",
    # the panel's only entry into ask_brain is _post_filter_advice(); the
    # tool-schema / dispatch paths that lazily import cortex are never called
    # from admin, which ships its own tool dispatcher
    "engine/neuralweb/cortex.py",
    "engine/master_brain.py",
    "engine/china_radar.py",
    # nightly-only marketing modules — the package is named, not globbed
    "engine/marketing/seo_director.py",
    "engine/marketing/breaking_feed.py",
    # macro-api's chart path, on no panel path
    "engine/marketing/chart_render.py",
    "engine/marketing/confluence_source.py",
    # the API and site-build lanes
    "app/main.py",
    "app/research.py",
    "lib/config.py",
    "scripts/build_site.py",
    "engine/research_codegen/transport.py",
    "engine/experiments_registry.py",
    "data/research_factory/review/queue.json",
    "templates/index.html.j2",
]


@pytest.mark.parametrize("path", ADMIN_MUST_RESTART)
def test_import_cached_module_triggers_admin_restart(path):
    assert (ROOT / path).exists(), f"stale test fixture: {path} no longer exists"
    assert _triggers_admin_restart(path), (
        f"{path} is import-cached by the admin panel but does not match the "
        "admin restart regex in app/deploy/update.sh — a change would deploy "
        "and never go live"
    )


@pytest.mark.parametrize("path", ADMIN_MUST_NOT_RESTART)
def test_non_admin_path_does_not_trigger_admin_restart(path):
    assert not _triggers_admin_restart(path), (
        f"{path} is not import-cached by admin; restarting on it blips the panel "
        "for nothing and defeats the narrow-restart intent"
    )


def test_api_and_admin_regexes_are_distinct():
    """Guard the extractor: both helpers must not resolve to the same line."""
    assert _api_restart_regex() != _admin_restart_regex()
    assert _admin_restart_regex().startswith("^(admin/")


# --------------------------------------------------------------------------
# PRESS-FEEDS deployment lifecycle. The service is intentionally operator-armed,
# but once active it is a long-running Python process and must not keep stale
# import-cached code after the checkout advances.
# --------------------------------------------------------------------------

PRESS_MUST_RESTART = [
    "app/deploy/marketing-press-feeds.service",
    "scripts/marketing_fastlane_daemon.py",
    "engine/news_translate.py",
    "engine/marketing/breaking_feed.py",
    "engine/marketing/press_providers.py",
    "engine/marketing/press_lane.py",
    "engine/marketing/story_spine.py",
    "engine/marketing/sentinel.py",
    "engine/marketing/__init__.py",
    "engine/codex_provider.py",
    "engine/llm_auth.py",
    "engine/codex_lane/runner.py",
    "lib/ai_costs.py",
    "lib/config.py",
]

PRESS_MUST_NOT_RESTART = [
    # Re-read on every tick.
    "config/marketing.yml",
    "config/press_sources.yml",
    # Artifacts/templates never enter the daemon interpreter.
    "site/news.html",
    "templates/news.html.j2",
    "data/qbus/items.parquet",
    "scripts/build_site.py",
    "admin/server.py",
]


def test_update_reconciles_only_an_installed_press_unit():
    assert '[ -f /etc/systemd/system/marketing-press-feeds.service ]' in SCRIPT
    assert 'systemd-analyze verify "$APP_DIR/app/deploy/marketing-press-feeds.service"' in SCRIPT
    assert "systemctl enable marketing-press-feeds" not in SCRIPT
    assert "systemctl start marketing-press-feeds" not in SCRIPT
    assert "systemctl is-active --quiet marketing-press-feeds" in SCRIPT


@pytest.mark.parametrize("path", PRESS_MUST_RESTART)
def test_press_import_cached_path_triggers_daemon_restart(path):
    assert (ROOT / path).exists(), f"stale test fixture: {path} no longer exists"
    assert _triggers_press_restart(path), (
        f"{path} is import-cached by marketing-press-feeds but does not match "
        "the restart regex in app/deploy/update.sh"
    )


@pytest.mark.parametrize("path", PRESS_MUST_NOT_RESTART)
def test_non_press_path_does_not_restart_daemon(path):
    assert not _triggers_press_restart(path), (
        f"{path} is re-read or unused by marketing-press-feeds; restarting on it "
        "would defeat the narrow lifecycle contract"
    )


# --------------------------------------------------------------------------
# Drift guard: recompute the LOAD-TIME import closure of app/*.py and require
# the regex to cover it.  Load-time is objective (module-level imports always
# execute), so this can be machine-checked; request-time imports need human
# judgement about whether an API endpoint reaches them and stay in MUST_RESTART.
# --------------------------------------------------------------------------

_TRACKED_ROOTS = ("engine", "lib", "scripts")


def _tracked_modules(node: ast.AST, path: Path) -> set[str]:
    if isinstance(node, ast.Import):
        return {a.name for a in node.names
                if a.name.split(".")[0] in _TRACKED_ROOTS}
    if node.level:  # relative: resolve against the file's own package
        parts = list(path.relative_to(ROOT).parent.parts)
        for _ in range(node.level - 1):
            parts = parts[:-1]
        module = ".".join(parts) + (f".{node.module}" if node.module else "")
    else:
        module = node.module or ""
    if module.split(".")[0] not in _TRACKED_ROOTS:
        return set()
    # `from engine.research_vault import catalog` -> the submodule, too
    return {module} | {f"{module}.{a.name}" for a in node.names}


def _module_level_imports(path: Path) -> set[str]:
    """Imports that run when `path` is loaded (incl. module-level try/if guards)."""
    found: set[str] = set()
    for stmt in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(stmt, (ast.Import, ast.ImportFrom)):
            found |= _tracked_modules(stmt, path)
        elif isinstance(stmt, (ast.Try, ast.If, ast.With)):
            for inner in ast.walk(stmt):
                if isinstance(inner, (ast.Import, ast.ImportFrom)):
                    found |= _tracked_modules(inner, path)
    return found


def _dynamic_modules(tree: ast.AST) -> set[str]:
    """`importlib.import_module("engine.x")` targets, by string literal.

    An Import/ImportFrom scan is blind to these, and admin/ai_cost.py,
    admin/orchestrator_chat.py and admin/neural_web.py reach lib.ai_costs,
    engine.neuralweb.ask_brain, support_map and orchestrator_log ONLY this way —
    so without this the admin closure would silently miss half its seeds.
    """
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = (fn.attr if isinstance(fn, ast.Attribute)
                else fn.id if isinstance(fn, ast.Name) else None)
        if name != "import_module" or not node.args:
            continue
        arg = node.args[0]
        if (isinstance(arg, ast.Constant) and isinstance(arg.value, str)
                and arg.value.split(".")[0] in _TRACKED_ROOTS):
            found.add(arg.value)
    return found


def _all_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            found |= _tracked_modules(node, path)
    return found | _dynamic_modules(tree)


def _ancestor_packages(dotted: str) -> set[str]:
    """Importing a.b.c executes a/__init__.py and a/b/__init__.py first.

    engine/marketing/__init__.py is not inert — it imports state, which pulls in
    ten more modules — so every one of them is pinned in sys.modules by a single
    `from engine.marketing import outbox`.
    """
    parts = dotted.split(".")
    return {".".join(parts[:i]) for i in range(1, len(parts))}


def _module_files(dotted: str) -> list[Path]:
    rel = dotted.replace(".", "/")
    return [p for p in (ROOT / f"{rel}.py", ROOT / rel / "__init__.py")
            if p.exists()]


def _is_inert_package_init(path: Path) -> bool:
    """A docstring-only __init__.py holds no behaviour that can go stale."""
    if path.name != "__init__.py":
        return False
    body = ast.parse(path.read_text(encoding="utf-8")).body
    return all(
        (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant)
         and isinstance(s.value.value, str))
        or (isinstance(s, ast.ImportFrom) and s.module == "__future__")
        for s in body
    )


def _load_time_closure(seed_dir: str) -> set[str]:
    """engine/lib modules guaranteed present in a service's sys.modules.

    Seeded from EVERY engine/lib import in `seed_dir` — the whole directory is
    that service's own code, so even a function-level import there executes
    in-process on some request — then expanded through module-level imports
    only, plus the parent packages Python runs on the way to a submodule.
    Deeper function-level imports need human judgement about whether an endpoint
    reaches them and live in the MUST_RESTART lists instead.
    """
    queue = deque()
    for module in sorted((ROOT / seed_dir).glob("*.py")):
        queue.extend(_all_imports(module))

    seen: set[str] = set()
    reached: set[str] = set()
    while queue:
        dotted = queue.popleft()
        if dotted in seen:
            continue
        seen.add(dotted)
        queue.extend(_ancestor_packages(dotted))
        for path in _module_files(dotted):       # skips symbols (funcs/classes)
            reached.add(str(path.relative_to(ROOT)))
            queue.extend(_module_level_imports(path))
    return reached


def _api_load_time_closure() -> set[str]:
    return _load_time_closure("app")


def _admin_load_time_closure() -> set[str]:
    return _load_time_closure("admin")


def test_api_load_time_import_closure_is_covered_by_restart_regex():
    """Every module macro-api loads at import time must force a restart.

    Fails when someone adds a module-level `from engine...`/`from lib...` import
    to an app/ router (or to a module already in the closure) without extending
    the trigger regex — the 2026-07-26 engine/research_vault gap, which shipped
    dead download-cap changes to production with no signal.
    """
    uncovered = sorted(
        rel for rel in _api_load_time_closure()
        if not _triggers_restart(rel)
        and not _is_inert_package_init(ROOT / rel)
    )
    assert not uncovered, (
        "import-cached by macro-api but missing from the restart regex in "
        f"app/deploy/update.sh: {uncovered}\n"
        "Add them (or, if a path is genuinely content read per request, document "
        "the exemption in the comment above the regex)."
    )


def test_radar_research_request_import_closure_is_covered_by_restart_regex():
    """The reader's function imports execute in-process on actual requests."""
    queue = deque(_all_imports(ROOT / "engine/entry_radar/research_read.py"))
    seen, uncovered = set(), set()
    while queue:
        dotted = queue.popleft()
        if dotted in seen:
            continue
        seen.add(dotted)
        queue.extend(_ancestor_packages(dotted))
        for path in _module_files(dotted):
            rel = str(path.relative_to(ROOT))
            if not _triggers_restart(rel) and not _is_inert_package_init(path):
                uncovered.add(rel)
            queue.extend(_module_level_imports(path))
    assert not uncovered, sorted(uncovered)


def test_gmi_bea_imports_restart_api_without_restart_on_unrelated_ontology():
    """Only the GMI API's actual import-cached modules need the API restart."""
    for path in (
        "engine/market_ontology/__init__.py",
        "engine/market_ontology/exposure_map.py",
        "engine/market_ontology/bea_gvc_current.py",
    ):
        assert _triggers_restart(path), path
    # Other ontology research modules are not imported by macro-api on startup.
    # Adding a blanket directory regex would restart on research-only changes.
    assert not _triggers_restart("engine/market_ontology/mining_theme_research.py")


def test_load_time_closure_probe_is_not_vacuous():
    """Guard the guard: an AST/glob regression must not silently pass the above."""
    closure = _api_load_time_closure()
    assert "engine/research_vault/download_quota.py" in closure, closure
    assert "engine/neuralweb/brain_gateway.py" in closure, closure
    # nightly-only modules must stay OUT, else the closure is over-broad
    assert "engine/master_brain.py" not in closure
    assert "engine/china_radar.py" not in closure


def _pinned_schema_basenames(path: Path) -> set[str]:
    """contracts *.schema.json basenames read under functools.lru_cache in `path`.

    A schema loaded inside an lru_cache'd function is pinned in the process for
    its whole lifetime, so a merged schema-only change deploys and the API keeps
    validating against the stale cached contract until something unrelated
    restarts it.  Reads without a cache re-fetch the file per call and self-heal,
    so they must NOT widen the trigger — the narrow-restart intent stands.
    """
    src = path.read_text(encoding="utf-8")
    found: set[str] = set()
    for node in ast.walk(ast.parse(src)):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        cached = any(
            "lru_cache" in ast.unparse(dec) or ast.unparse(dec) in ("cache", "functools.cache")
            for dec in node.decorator_list
        )
        if not cached:
            continue
        for inner in ast.walk(node):
            if (isinstance(inner, ast.Constant) and isinstance(inner.value, str)
                    and inner.value.endswith(".schema.json")):
                found.add(inner.value.rsplit("/", 1)[-1])
    return found


def _pinned_contract_schema_paths() -> set[str]:
    """Repo paths of contract schemas pinned in macro-api via the app/ closure.

    Basenames are resolved against the real contracts/ tree, so both spellings
    in the wild bind to the same file: the single full-path literal
    (candidates.py) and the component build (`... / "contracts" /
    "government_revenue" / name` in the dossier validators).  A basename that
    resolves to several contract files requires them all — fail-closed.
    """
    basenames: set[str] = set()
    for rel in _api_load_time_closure():
        basenames |= _pinned_schema_basenames(ROOT / rel)
    by_name: dict[str, list[Path]] = {}
    for p in (ROOT / "contracts").rglob("*.schema.json"):
        by_name.setdefault(p.name, []).append(p)
    return {
        str(p.relative_to(ROOT))
        for name in basenames if "*" not in name and "?" not in name
        for p in by_name.get(name, ())
    }


def test_contract_schema_pinned_by_api_closure_triggers_restart():
    """Every contract schema an api-closure module lru_caches must force a restart.

    The Wave 8 shape: engine/government_revenue validators pin their
    contracts/government_revenue schemas with lru_cache(maxsize=1), so a merged
    schema change shipped without a restart and the API served the stale cached
    contract until something unrelated restarted it.  Derived from the closure
    rather than enumerated, so the next lru_cache'd schema read joins the
    requirement the day it is written.
    """
    uncovered = sorted(
        rel for rel in _pinned_contract_schema_paths()
        if not _triggers_restart(rel)
    )
    assert not uncovered, (
        "pinned in macro-api by an lru_cache'd schema read in the app/ import "
        f"closure but missing from the restart regex in app/deploy/update.sh: {uncovered}\n"
        "A merged change to these files deploys and never goes live — add them "
        "to the contracts alternation on the macro-api restart line."
    )


def test_pinned_schema_probe_is_not_vacuous():
    """Guard the guard: both path spellings must parse, and un-cached reads stay out."""
    pinned = _pinned_contract_schema_paths()
    # component-style path build in the lru_cache'd dossier validators
    assert "contracts/government_revenue/government_revenue_dossiers.v1.schema.json" in pinned
    assert "contracts/government_revenue/government_idv_dossiers.v1.schema.json" in pinned
    assert "contracts/government_revenue/government_subaward_dossiers.v1.schema.json" in pinned
    # single full-path literal (candidates.py) — the pair the regex carried first
    assert "contracts/government_revenue/government_revenue_candidate.v1.schema.json" in pinned
    assert "contracts/government_revenue/government_revenue_candidate_historical_suppressions.v1.schema.json" in pinned
    assert "contracts/government_revenue/government_revenue_candidate_issuance_corrections.v1.schema.json" in pinned
    # workspace validators pin the current (v2) procurement generation
    assert "contracts/government_revenue/government_procurement_workspace.v2.schema.json" in pinned
    # un-cached reads self-heal per call and must stay OUT, else the narrow
    # trigger grows into restart-on-every-contract-commit
    assert "contracts/government_revenue/government_budget_program_graph.v1.schema.json" not in pinned
    assert not any(p.endswith("capital_structure_projection.schema.json") for p in pinned)


def test_admin_load_time_import_closure_is_covered_by_restart_regex():
    """Every module the admin panel import-caches must force a restart.

    Fails when someone adds an `engine`/`lib` import to an admin/ panel (or a
    module-level import to something already in the closure) without extending
    the admin trigger regex — the 2026-07-26 engine/marketing/outbox.py gap,
    which shipped dead outbox approve/reject/decide code to the running panel.
    """
    uncovered = sorted(
        rel for rel in _admin_load_time_closure()
        if not _triggers_admin_restart(rel)
        and not _is_inert_package_init(ROOT / rel)
    )
    assert not uncovered, (
        "import-cached by the admin panel but missing from the admin restart "
        f"regex in app/deploy/update.sh: {uncovered}\n"
        "Add them (or, if a path is genuinely content read per request, document "
        "the exemption in the comment above the regex)."
    )


def test_admin_closure_probe_is_not_vacuous():
    """Guard the guard: each seed form the admin closure depends on must work."""
    closure = _admin_load_time_closure()
    # static function-level import (admin/marketing.py)
    assert "engine/marketing/outbox.py" in closure, closure
    # importlib.import_module("...") literals — invisible to an import-line scan
    assert "engine/neuralweb/support_map.py" in closure, closure
    assert "lib/ai_costs.py" in closure, closure
    # package __init__ side effect: `from engine.marketing import outbox` runs
    # __init__ -> state -> the substrate
    assert "engine/marketing/__init__.py" in closure, closure
    assert "engine/marketing/state.py" in closure, closure
    # Read-only diagnostic validation loads the bridge and its direct contracts.
    assert "engine/research_codegen/bridge.py" in closure
    assert "engine/research_codegen/input_contract.py" in closure
    assert "engine/research_codegen/evaluation.py" in closure
    assert "engine/research_codegen/transport.py" not in closure
    # nightly-only lanes must stay OUT, else the closure is over-broad and the
    # narrow-restart intent is lost
    assert "engine/neuralweb/cortex.py" not in closure
    assert "engine/marketing/seo_director.py" not in closure
    assert "engine/master_brain.py" not in closure


def test_dotted_import_still_reaches_the_package_init():
    """A dotted-only import names no package, but Python still runs its __init__.

    Tested directly because today both spellings appear in admin/marketing.py, so
    `engine.marketing` is seeded either way and the closure probe above cannot
    tell the ancestor walk apart from the plain seed.  It becomes load-bearing the
    moment the last `from engine.marketing import outbox` form goes away — as is
    already the case for macro-api, where brain_gateway only ever writes
    `from engine.marketing.chart_render import ...` and the package __init__ (and
    the twelve-module substrate behind it) is reachable no other way.
    """
    assert _ancestor_packages("engine.marketing.outbox") == {
        "engine", "engine.marketing",
    }
    assert _ancestor_packages("lib") == set()


@pytest.mark.parametrize(
    ("helper_status", "prior_status", "expected_status"),
    [(0, 0, 0), (37, 0, 37), (37, 19, 19)],
)
def test_ohlc_delivery_refusal_is_deferred_without_erasing_other_failures(
    tmp_path, helper_status, prior_status, expected_status
):
    """Execute the real shell wrapper; a later success cannot erase a refusal."""
    app = tmp_path / "app"
    scripts = app / "scripts"
    scripts.mkdir(parents=True)
    helper = scripts / "publish_ohlc.py"
    helper.write_text(
        "import pathlib, sys\n"
        "assert sys.argv[1:] == ['reconcile', '--lock-fd', '9']\n"
        "root = pathlib.Path(__file__).parent\n"
        "calls = root / 'calls'\n"
        "number = int(calls.read_text()) if calls.exists() else 0\n"
        "calls.write_text(str(number + 1))\n"
        f"sys.exit({helper_status} if number == 0 else 0)\n"
    )
    wrapper = SCRIPT.split("# BEGIN OHLC_DELIVERY_RECONCILE\n", 1)[1].split(
        "# END OHLC_DELIVERY_RECONCILE", 1
    )[0]
    final_status = SCRIPT.split("# BEGIN OHLC_DELIVERY_EXIT_STATUS\n", 1)[1].split(
        "# END OHLC_DELIVERY_EXIT_STATUS", 1
    )[0]
    completed = tmp_path / "unrelated-completed"
    command = (
        "set -euo pipefail\n"
        f"APP_DIR={shlex.quote(str(app))}\n"
        f"DEPLOY_EXIT_STATUS={prior_status}\n"
        + wrapper
        + "\nreconcile_ohlc_delivery\n"
        + f"printf completed > {shlex.quote(str(completed))}\n"
        + "reconcile_ohlc_delivery\n"
        + final_status
        + '\nexit "${DEPLOY_EXIT_STATUS:-0}"\n'
    )
    result = subprocess.run(
        ["bash", "-c", command], capture_output=True, text=True, check=False
    )
    assert result.returncode == expected_status, result.stderr
    assert completed.read_text() == "completed"
    assert (scripts / "calls").read_text() == "2"
    if helper_status:
        assert "OHLC reconciliation refused (status 37)" in result.stderr


@pytest.mark.parametrize("held_path", ["managed_link", "foreign_directory", "foreign_link"])
def test_ohlc_delivery_rsync_preserves_selected_or_refused_paths(tmp_path, held_path):
    """Run the production rsync command against disposable trees."""
    import shutil

    if shutil.which("rsync") is None:
        pytest.skip("rsync is unavailable")
    app = tmp_path / "app"
    source = app / "site"
    served = app / "site.served"
    source.mkdir(parents=True)
    served.mkdir()
    (source / "index.html").write_text("new rendered page")
    (served / "index.html").write_text("old")
    (served / "unrelated-stale.txt").write_text("delete me")
    target = app / "held"
    target.mkdir()
    (target / "SPY.json").write_text("retained bytes")
    if held_path == "foreign_directory":
        (served / "ohlc").mkdir()
        (served / "ohlc" / "SPY.json").write_text("retained bytes")
    elif held_path == "foreign_link":
        (served / "ohlc").symlink_to("../held", target_is_directory=True)
    else:
        generations = app / "ohlc.served"
        generations.mkdir()
        (generations / "current").symlink_to("../held", target_is_directory=True)
        (source / "ohlc").symlink_to("../ohlc.served/current", target_is_directory=True)
        (served / "ohlc").symlink_to("../ohlc.served/current", target_is_directory=True)
    rsync_line = next(
        line.strip() for line in SCRIPT.splitlines()
        if line.strip().startswith("rsync ")
        and '"$APP_DIR/site/" "$APP_DIR/site.served/"' in line
    )
    result = subprocess.run(
        ["bash", "-e", "-c", f"APP_DIR={shlex.quote(str(app))}\n{rsync_line}"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert (served / "index.html").read_text() == "new rendered page"
    assert not (served / "unrelated-stale.txt").exists()
    assert (served / "ohlc" / "SPY.json").read_text() == "retained bytes"
    if held_path == "foreign_link":
        assert os.readlink(served / "ohlc") == "../held"
    elif held_path == "managed_link":
        assert os.readlink(served / "ohlc") == "../ohlc.served/current"


def test_ohlc_delivery_reconciles_before_copy_and_on_repository_noop():
    changed = SCRIPT.index('if [ "$OLD" != "$NEW" ]; then')
    copy = SCRIPT.index('rsync -a --delete --min-size=1 --exclude=/ohlc ')
    before_copy = SCRIPT.index("\treconcile_ohlc_delivery\n", changed)
    noop = SCRIPT.index(
        "# Reconcile artifact selection even when the repository did not change."
    )
    after_copy = SCRIPT.index("\nreconcile_ohlc_delivery\n", noop)
    assert changed < before_copy < copy < noop < after_copy
    assert SCRIPT[noop - 4:noop] == "fi\n\n"
    assert "--delete-excluded" not in SCRIPT[before_copy:copy + 120]


def test_admin_restart_expectations_are_disjoint():
    assert not (set(ADMIN_MUST_RESTART) & set(ADMIN_MUST_NOT_RESTART))
