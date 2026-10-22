"""Native command/closure contracts only; no APT or network execution."""
import copy
import hashlib

import pytest

from scripts import ci_apt_native_plan as PLAN
from scripts.ci_apt_cold_acquisition import AcquisitionRefused


def transaction():
    def row(name, version, architecture, package_arch="amd64", mode="install"):
        return {"name": name, "architecture": package_arch, "mode": mode, "automatic": True,
                "versions": {"install": {"version": version, "architecture": architecture}}}
    return {"command": "install", "search-terms": list(PLAN.DIRECT_PACKAGES), "packages": [
        row("fonts-wqy-zenhei", "0.9.45-8", "all"),
        row("libnss3", "2:3.98-1ubuntu0.3", "amd64", mode="upgrade"),
        # Native resolver's extra dependency is mandatory, never trimmed to
        # just the direct Playwright names.
        row("xfonts-utils", "1:7.7+6build3", "amd64"),
    ]}


def uri_lines(tx):
    lines = []
    for row in tx["packages"]:
        selected = row["versions"]["install"]
        filename = f"{row['name']}_{selected['version'].replace(':', '%3a')}_{selected['architecture']}.deb"
        uri = f"http://azure.archive.ubuntu.com/ubuntu/pool/main/f/fixture/{filename}"
        digest = hashlib.sha256(row["name"].encode()).hexdigest()
        lines.append(f"'{uri}' {filename} 100 SHA256:{digest}")
    return ("APT summary ignored\n" + "\n".join(lines) + "\n").encode()


def test_full_native_inventory_preserves_fonts_upgrades_epoch_arch_and_extra_dependencies():
    tx = transaction()
    records = PLAN.complete_archive_inventory(tx, uri_lines(tx))
    assert [r.package for r in records] == [r["name"] for r in tx["packages"]]
    assert records[0].archive_architecture == "all" and records[0].package_architecture == "amd64"
    assert records[1].version == "2:3.98-1ubuntu0.3"
    assert records[2].selector == "xfonts-utils:amd64=1:7.7+6build3"


@pytest.mark.parametrize("case", ["missing_font", "duplicate", "changed_version", "changed_arch", "wrong_hash", "foreign", "bad_row"])
def test_missing_or_changed_archive_cannot_be_deferred_to_install_network_fallback(case):
    tx = transaction()
    lines = uri_lines(tx).decode().splitlines()
    if case == "missing_font": lines.pop(1)
    if case == "duplicate": lines.append(lines[1])
    if case == "changed_version": lines[1] = lines[1].replace("0.9.45-8", "0.9.45-7")
    if case == "changed_arch": lines[1] = lines[1].replace("_all.deb", "_arm64.deb")
    if case == "wrong_hash": lines[1] = lines[1].replace("SHA256:", "MD5Sum:")
    if case == "foreign": lines[1] = lines[1].replace("azure.archive.ubuntu.com", "foreign.invalid")
    if case == "bad_row": lines[1] = "'malformed SECRET"
    with pytest.raises(AcquisitionRefused) as caught:
        PLAN.complete_archive_inventory(tx, ("\n".join(lines) + "\n").encode())
    assert "SECRET" not in str(caught.value)


def test_original_direct_dependency_flags_and_all_required_fonts_are_preserved():
    assert len(PLAN.DIRECT_PACKAGES) == len(set(PLAN.DIRECT_PACKAGES)) == 33
    assert set(PLAN.DIRECT_PACKAGES) >= {
        "xvfb", "fonts-noto-color-emoji", "fonts-unifont", "libfontconfig1", "libfreetype6",
        "xfonts-cyrillic", "xfonts-scalable", "fonts-liberation", "fonts-ipafont-gothic",
        "fonts-wqy-zenhei", "fonts-tlwg-loma-otf", "fonts-freefont-ttf",
    }
    args = PLAN.no_download_install_argv(hook="/tmp/ci-apt-test/fence-hook", cache="/tmp/ci-apt-test/archives")
    assert args[-36:] == (*PLAN.INHERITED_INSTALL_FLAGS, *PLAN.DIRECT_PACKAGES)
    assert "--no-download" in args
    for setting in ("APT::Get::Fix-Missing=false", "APT::Get::AllowUnauthenticated=false",
                    "Debug::NoLocking=false", "Acquire::AllowInsecureRepositories=false"):
        assert setting in args
    assert not any(arg in args for arg in ("--fix-missing", "--allow-unauthenticated", "--no-upgrade", "--ignore-missing"))


def test_hooks_append_without_clearing_inherited_configuration_or_changing_other_python_hooks():
    hook = "/tmp/ci-apt-test/fence-hook"
    args = PLAN.no_download_install_argv(hook=hook, cache="/tmp/ci-apt-test/archives")
    assert f"DPkg::Pre-Install-Pkgs::={hook} preinstall" in args
    assert f"AptCli::Hooks::Install::={hook} json" in args
    assert f"DPkg::Tools::Options::{hook}::Version=3" in args
    assert not any(arg.startswith("DPkg::Pre-Install-Pkgs=") for arg in args)
    assert not any("Tools::Options::/usr/bin/python" in arg for arg in args)


def test_native_resolver_reports_sha256_and_same_full_original_install_arguments():
    args = PLAN.resolver_argv(hook="/tmp/ci-apt-test/fence-hook", cache="/tmp/ci-apt-test/archives")
    assert "--print-uris" in args and "Acquire::ForceHash=SHA256" in args
    assert args[-36:] == (*PLAN.INHERITED_INSTALL_FLAGS, *PLAN.DIRECT_PACKAGES)


@pytest.mark.parametrize("changed", ["distribution_version", "driver_version", "bundle_sha256", "os_id", "os_version", "machine"])
def test_unqualified_runtime_dependency_source_is_not_silently_adopted(changed):
    source = dict(distribution_version="1.64.1", driver_version="1.64.0-beta-1791568591000",
                  bundle_sha256=PLAN.QUALIFIED_DRIVER, os_id="ubuntu", os_version="24.04", machine="x86_64")
    assert PLAN.qualified_direct_packages(**source) == PLAN.DIRECT_PACKAGES
    source[changed] = "foreign"
    with pytest.raises(AcquisitionRefused, match="DEPENDENCY_SOURCE_UNQUALIFIED"):
        PLAN.qualified_direct_packages(**source)


def test_missing_direct_font_is_not_hidden_by_a_valid_transitive_archive_inventory():
    tx = copy.deepcopy(transaction())
    tx["search-terms"].remove("fonts-wqy-zenhei")
    with pytest.raises(AcquisitionRefused, match="DIRECT_DEPENDENCIES_CHANGED"):
        PLAN.complete_archive_inventory(tx, uri_lines(tx))


@pytest.mark.parametrize("path", ["/etc/apt/apt.conf", "/tmp/ci-apt-test/../foreign", "/tmp/ci-apt-test/path with space"])
def test_configuration_paths_cannot_select_live_global_config_or_shell_text(path):
    with pytest.raises(AcquisitionRefused):
        PLAN.no_download_install_argv(hook=path, cache="/tmp/ci-apt-test/archives")
