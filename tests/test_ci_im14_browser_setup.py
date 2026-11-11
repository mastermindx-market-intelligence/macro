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


@pytest.mark.parametrize("placement", ["before", "between", "after", "surround"])
def test_projection_ignores_comment_only_paragraphs_without_changing_sources(placement):
    comment = b"# Hosted image metadata\n\t# Source pockets follow"
    primary, security = SOURCES.split(b"\n\n")
    variants = {
        "before": comment + b"\n\n" + SOURCES,
        "between": primary + b"\n\n" + comment + b"\n\n" + security,
        "after": SOURCES + b"\n" + comment + b"\n",
        "surround": comment + b"\n\n" + primary + b"\n\n" + comment
        + b"\n\n" + security + b"\n" + comment + b"\n",
    }
    assert im14.project_sources(variants[placement], MIRRORS) == im14.project_sources(SOURCES, MIRRORS)


@pytest.mark.parametrize("separator", [b"\n\n\n\n", b"\n \t\n \t\n\n"])
def test_projection_ignores_empty_paragraphs_between_sources(separator):
    assert im14.project_sources(SOURCES.replace(b"\n\n", separator), MIRRORS) == im14.project_sources(SOURCES, MIRRORS)


@pytest.mark.parametrize("control", [b"\v", b"\f", b"\r", b"\x1c", b"\x1d", b"\x1e"])
def test_projection_refuses_non_deb822_paragraph_separators(control):
    malformed = SOURCES.replace(b"\n\n", b"\n\n" + control + b"\n\n")
    with pytest.raises(ValueError, match="unqualified Ubuntu source syntax"):
        im14.project_sources(malformed, MIRRORS)


@pytest.mark.parametrize("sources", [b"", b" \t\n\n", b"# No sources\n\n\t# Still no sources\n"])
def test_projection_requires_source_inventory_after_ignoring_comments(sources):
    with pytest.raises(ValueError, match="unqualified Ubuntu suite inventory"):
        im14.project_sources(sources, MIRRORS)


@pytest.mark.parametrize("field", [b"Trusted: yes", b"not-a-field", b"X-Vendor-Profile: metadata"])
def test_projection_does_not_skip_nonempty_paragraphs_starting_with_a_comment(field):
    malformed = b"# This paragraph still contains a field\n" + field + b"\n\n" + SOURCES
    with pytest.raises(ValueError):
        im14.project_sources(malformed, MIRRORS)


def test_projection_refuses_when_comments_replace_a_required_source():
    primary, security = SOURCES.split(b"\n\n")
    commented = b"\n".join(b"# " + line for line in security.splitlines())
    with pytest.raises(ValueError, match="unqualified Ubuntu suite inventory"):
        im14.project_sources(primary + b"\n\n" + commented, MIRRORS)


def test_projection_preserves_the_qualified_binary_repository_inputs():
    assert im14.project_sources(SOURCES, MIRRORS) == SOURCES.replace(
        im14.MIRROR.encode(), im14.HTTPS_ARCHIVE.encode()
    )


def test_projection_owns_private_binary_sources_independent_of_vendor_metadata():
    vendor_sources = SOURCES.replace(b"Types: deb", b"types: deb deb-src")
    vendor_sources = vendor_sources.replace(
        b"Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg",
        b"X-Vendor-Profile: Ubuntu hosted image",
    )
    vendor_sources = vendor_sources.replace(b" restricted universe multiverse", b" universe")
    projected = im14.project_sources(vendor_sources, MIRRORS)
    expected = SOURCES.replace(im14.MIRROR.encode(), im14.HTTPS_ARCHIVE.encode())
    assert projected == expected.replace(b" restricted universe multiverse", b" universe")


def test_projection_preserves_the_hosted_amd64_i386_inventory():
    sources = SOURCES.replace(
        b"Signed-By:", b"Architectures: amd64 i386\nSigned-By:", 1
    ).replace(b"Architectures: amd64\n", b"Architectures: amd64 i386\n")
    assert im14.project_sources(sources, MIRRORS) == sources.replace(
        im14.MIRROR.encode(), im14.HTTPS_ARCHIVE.encode()
    )


@pytest.mark.parametrize("uri", [
    b"http://security.ubuntu.com/ubuntu/",
    b"https://security.ubuntu.com/ubuntu/",
    b"http://security.ubuntu.com/ubuntu",
])
def test_projection_uses_tls_for_the_canonical_security_pocket(uri):
    primary, security = SOURCES.split(b"\n\n")
    security = security.replace(im14.MIRROR.encode(), uri)
    assert im14.project_sources(primary + b"\n\n" + security, MIRRORS) == (
        primary.replace(im14.MIRROR.encode(), im14.HTTPS_ARCHIVE.encode())
        + b"\n\n"
        + security.replace(uri, b"https://security.ubuntu.com/ubuntu/")
    )


@pytest.mark.parametrize("original,mirrors", [
    (SOURCES.replace(b"ubuntu-archive-keyring.gpg", b"foreign-keyring.gpg"), MIRRORS),
    (SOURCES.replace(b"Types: deb", b"Types: deb\nTrusted: yes"), MIRRORS),
    (SOURCES.replace(b"restricted universe", b"restricted foreign"), MIRRORS),
    (SOURCES.replace(b"main restricted", b"main main"), MIRRORS),
    (SOURCES.replace(b"main restricted", b"restricted"), MIRRORS),
    (SOURCES.replace(b"Types: deb", b"Types: deb\nCheck-Valid-Until: no"), MIRRORS),
    (SOURCES.replace(b"Types: deb", b"Types: deb\nEnabled: no"), MIRRORS),
    (SOURCES.replace(b"Types: deb", b"Types: deb\nArchitectures-Add: arm64"), MIRRORS),
    (SOURCES.replace(b"Types: deb", b"Types: deb\ntypes: deb"), MIRRORS),
    (SOURCES.replace(b"Architectures: amd64", b"Architectures: arm64"), MIRRORS),
    (SOURCES.replace(b"Architectures: amd64", b"Architectures: i386"), MIRRORS),
    (SOURCES.replace(b"Architectures: amd64", b"Architectures: amd64 i386 i386"), MIRRORS),
    (SOURCES.replace(b"Architectures: amd64", b"Architectures: amd64 i386 arm64"), MIRRORS),
    (SOURCES.replace(b"URIs: " + im14.MIRROR.encode(),
                     b"URIs: http://security.ubuntu.com/ubuntu/", 1), MIRRORS),
    (SOURCES.replace(b"URIs: " + im14.MIRROR.encode(),
                     b"URIs: http://security.ubuntu.com.example/ubuntu/"), MIRRORS),
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
