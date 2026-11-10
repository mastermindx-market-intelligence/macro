import subprocess
from types import SimpleNamespace

import pytest

from scripts import ci_im14_browser_setup as im14


MIRRORS = b"""http://azure.archive.ubuntu.com/ubuntu/\tpriority:1
https://archive.ubuntu.com/ubuntu/\tpriority:2
https://security.ubuntu.com/ubuntu/\tpriority:3
"""
SOURCES = b"""Types: deb
URIs: mirror+file:/etc/apt/apt-mirrors.txt
Suites: noble noble-updates noble-backports
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg

Types: deb
URIs: mirror+file:/etc/apt/apt-mirrors.txt
Suites: noble-security
Components: main restricted universe multiverse
Architectures: amd64
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
"""
PRIVATE = "/var/tmp/mm-im14-apt.Abc123deFG"


def test_projection_preserves_every_field_except_the_qualified_uri():
    assert im14.project_sources(SOURCES, MIRRORS) == SOURCES.replace(
        im14.MIRROR.encode(), im14.HTTPS_ARCHIVE.encode()
    )


@pytest.mark.parametrize("original,mirrors", [
    (SOURCES.replace(b"ubuntu-archive-keyring.gpg", b"foreign-keyring.gpg"), MIRRORS),
    (SOURCES.replace(b"Types: deb", b"Types: deb\nTrusted: yes"), MIRRORS),
    (SOURCES.replace(b"Architectures: amd64", b"Architectures: arm64"), MIRRORS),
    (SOURCES.replace(b"noble-security", b"noble-updates"), MIRRORS),
    (SOURCES.replace(b"URIs: mirror", b"URIs: mirror+file:/extra mirror"), MIRRORS),
    (SOURCES, MIRRORS.replace(b"https://archive.ubuntu.com", b"https://example.invalid")),
])
def test_projection_refuses_unqualified_source_or_mirror(original, mirrors):
    with pytest.raises(ValueError):
        im14.project_sources(original, mirrors)


def future_deadline():
    return im14.time.monotonic() + 20


def fake_apt(monkeypatch, failure=None):
    calls = []

    def run(deadline, *argv, **kwargs):
        assert deadline > im14.time.monotonic() and kwargs["privileged"] is True
        calls.append((argv, kwargs))
        if argv[0] == "/usr/bin/mktemp":
            return SimpleNamespace(stdout=PRIVATE + "\n")
        if argv[0] == "/usr/bin/apt-get" and failure in argv:
            raise subprocess.CalledProcessError(100, argv)
        return SimpleNamespace(stdout="")

    monkeypatch.setattr(im14, "_run", run)
    return calls


def test_apt_uses_one_private_authenticated_update_and_exact_install(monkeypatch):
    calls = fake_apt(monkeypatch)
    other = b"deb [signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/ubuntu/24.04/prod noble main\n"
    im14._apt_install(future_deadline(), {"": b"", "ubuntu.sources": b"qualified Ubuntu source", "ms.list": other}, b"")
    apt = [args for args, _ in calls if args[0] == "/usr/bin/apt-get"]
    update, install = apt
    assert update[-1] == "update"
    assert install == (*update[:-1], "install", "-y", "--no-install-recommends", *im14.PACKAGES)
    assert len(im14.PACKAGES) == len(set(im14.PACKAGES)) == 33
    assert f"Dir::State::lists={PRIVATE}/lists" in update
    assert f"Dir::Etc::sourceparts={PRIVATE}/parts" in update
    assert f"Dir::Cache::archives={PRIVATE}/archives" in update
    assert "APT::Update::Error-Mode=any" in update
    assert "Acquire::https::Verify-Peer=true" in update
    assert "APT::Get::AllowUnauthenticated=false" in update
    assert next(kwargs["input"] for args, kwargs in calls if args[-1] == f"{PRIVATE}/parts/ms.list") == other
    assert calls[-1][0] == ("/usr/bin/rm", "-rf", "--", PRIVATE)


def test_unsettled_update_blocks_install_and_preserves_original_state(monkeypatch):
    calls = fake_apt(monkeypatch, failure="update")
    with pytest.raises(subprocess.CalledProcessError):
        im14._apt_install(future_deadline(), {"": b"", "ubuntu.sources": b"qualified Ubuntu source"}, b"")
    assert [args[-1] for args, _ in calls if args[0] == "/usr/bin/apt-get"] == ["update"]
    assert all(args[0] != "/usr/bin/rm" for args, _ in calls)


def test_failed_install_never_cleans_state_or_restarts(monkeypatch):
    calls = fake_apt(monkeypatch, failure="install")
    with pytest.raises(subprocess.CalledProcessError):
        im14._apt_install(future_deadline(), {"": b"", "ubuntu.sources": b"qualified Ubuntu source"}, b"")
    assert sum(args[0] == "/usr/bin/apt-get" for args, _ in calls) == 2
    assert all(args[0] != "/usr/bin/rm" for args, _ in calls)


def prepare_node(monkeypatch, tmp_path, *, match):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(im14.platform, "freedesktop_os_release", lambda: {"ID": "ubuntu", "VERSION_ID": "24.04"})
    monkeypatch.setattr(im14.platform, "machine", lambda: "x86_64")
    monkeypatch.setenv("RUNNER_ENVIRONMENT", "github-hosted")
    monkeypatch.delenv("APT_CONFIG", raising=False)
    monkeypatch.delenv("PLAYWRIGHT_HOST_PLATFORM_OVERRIDE", raising=False)
    monkeypatch.setattr(im14, "_source_profile", lambda: {"ubuntu.sources": b"approved"})
    for name in ("playwright", "playwright-core"):
        folder = tmp_path / "node_modules" / name
        folder.mkdir(parents=True)
        (folder / "package.json").write_text(f'{{"name":"{name}","version":"1.63.0"}}')
    driver = tmp_path / "node_modules/playwright-core/lib/coreBundle.js"
    driver.parent.mkdir()
    driver.write_bytes(b"test-owned driver")
    cli = tmp_path / "node_modules/playwright/cli.js"
    cli.write_bytes(b"test-owned cli")
    if match:
        monkeypatch.setattr(im14, "DRIVER_SHA256", im14.hashlib.sha256(driver.read_bytes()).hexdigest())
    monkeypatch.setattr(im14, "PLAYWRIGHT_CLI_SHA256", im14.hashlib.sha256(cli.read_bytes()).hexdigest())
    registry = tmp_path / "node_modules/playwright-core/browsers.json"
    registry.write_bytes(b"test-owned registry")
    monkeypatch.setattr(im14, "BROWSER_REGISTRY_SHA256", im14.hashlib.sha256(registry.read_bytes()).hexdigest())


def fake_node(monkeypatch):
    calls = []

    def run(deadline, *args, **kwargs):
        assert deadline > im14.time.monotonic()
        calls.append(args)
        if args[0] == "/usr/bin/apt-config":
            assert kwargs["privileged"] is True
        return SimpleNamespace(stdout="")

    monkeypatch.setattr(im14, "_run", run)
    return calls


def test_driver_mismatch_refuses_before_privileged_setup(monkeypatch, tmp_path):
    prepare_node(monkeypatch, tmp_path, match=False)
    calls = fake_node(monkeypatch)
    monkeypatch.setattr(im14, "_apt_install", lambda *_: pytest.fail("must refuse before APT"))
    with pytest.raises(ValueError, match="driver mismatch"):
        im14.main(future_deadline())
    assert calls == [("/usr/bin/apt-config", "dump"),
                     ("npm", "install", "--no-save", "--package-lock=false", "playwright@1.63.0")]


def test_pinned_browser_installs_only_after_qualified_os_dependencies(monkeypatch, tmp_path):
    prepare_node(monkeypatch, tmp_path, match=True)
    calls = fake_node(monkeypatch)
    monkeypatch.setattr(im14, "_apt_install", lambda deadline, sources, config: calls.append(("apt", sources)))
    im14.main(future_deadline())
    assert calls == [
        ("/usr/bin/apt-config", "dump"),
        ("npm", "install", "--no-save", "--package-lock=false", "playwright@1.63.0"),
        ("apt", {"ubuntu.sources": b"approved"}),
        ("node", "node_modules/playwright/cli.js", "install", "chromium"),
    ]


def test_install_failure_does_not_launch_browser(monkeypatch, tmp_path):
    prepare_node(monkeypatch, tmp_path, match=True)
    calls = fake_node(monkeypatch)

    def fail(*_):
        raise subprocess.CalledProcessError(100, ("apt-get", "install"))

    monkeypatch.setattr(im14, "_apt_install", fail)
    with pytest.raises(subprocess.CalledProcessError):
        im14.main(future_deadline())
    assert calls == [("/usr/bin/apt-config", "dump"),
                     ("npm", "install", "--no-save", "--package-lock=false", "playwright@1.63.0")]

def test_private_apt_config_omits_only_exact_cache_cleanup():
    inherited = ('APT::Default-Release "noble";\nAPT::Update::Post-Invoke "";\n'
                 f'APT::Update::Post-Invoke:: "{im14.CACHE_CLEANUP}";\n')
    assert im14.private_apt_config(inherited) == b"#clear APT::Update::Post-Invoke;\n"
    assert im14.private_apt_config('APT::Default-Release "noble";') == b""


@pytest.mark.parametrize("line", [
    'DPkg::Post-Invoke:: "/usr/bin/other-policy";',
    'APT::Update::Post-Invoke-Success::keeper "/usr/bin/other-policy";',
    'APT::Update::Post-Invoke "unexpected-direct-value";',
])
def test_unknown_invoke_policy_refuses_instead_of_dropping(line):
    with pytest.raises(ValueError, match="post-invoke policy"):
        im14.private_apt_config(line)


def test_privileged_supervisor_uses_same_absolute_deadline(monkeypatch):
    monkeypatch.setattr(im14.time, "monotonic", lambda: 100.0)
    calls = []

    def invoke(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 124)

    monkeypatch.setattr(im14.subprocess, "run", invoke)
    with pytest.raises(im14.DeadlineExpired, match="did not settle"):
        im14._run(112.0, "/usr/bin/apt-get", "update", privileged=True)
    assert calls == [(("sudo", "-n", "--", "/usr/bin/timeout", "--signal=TERM", "--kill-after=1s",
                       "9.000000s", "/usr/bin/apt-get", "update"), {"timeout": 12.0})]
    with pytest.raises(im14.DeadlineExpired, match="before stage launch"):
        im14._run(103.0, "/usr/bin/apt-get", "install", privileged=True)
    assert len(calls) == 1
